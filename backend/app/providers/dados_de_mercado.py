import logging
from dataclasses import dataclass
from datetime import date

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dadosdemercado.com.br"
USER_AGENT = "ProjectFin/1.0"


@dataclass
class DividendRecord:
    dividend_type: str
    value: float
    record_date: date
    ex_date: date
    payment_date: date | None


def _strip_sa(symbol: str) -> str:
    return symbol.removesuffix(".SA")


def _parse_date(text: str) -> date | None:
    """Parse dd/mm/yyyy date string, return None if unparseable."""
    text = text.strip()
    if not text or text == "—" or text == "-":
        return None
    try:
        parts = text.split("/")
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, IndexError):
        return None


def _parse_value(text: str) -> float:
    """Parse Brazilian number format (comma as decimal separator).

    Handles optional '* ' prefix used for older adjusted values.
    """
    cleaned = text.strip().lstrip("* ")
    return float(cleaned.replace(".", "").replace(",", "."))


class DadosDeMercadoProvider:
    def __init__(self, base_url: str = BASE_URL):
        self._base_url = base_url

    def scrape_dividends(self, symbol: str) -> list[DividendRecord]:
        ticker = _strip_sa(symbol).lower()
        url = f"{self._base_url}/acoes/{ticker}/dividendos"

        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch dividends page for {symbol}")
            return []

        try:
            return self._parse_html(resp.text)
        except Exception:
            logger.exception(f"Failed to parse dividends HTML for {symbol}")
            return []

    def _scrape_financial_table(self, url: str) -> dict:
        """Fetch a financial HTML table and return a dict of row labels to year-keyed values.

        Returns: {"years": [2025, 2024, ...], "Row Label": {2025: val, ...}, ...}
        Returns empty dict on any error.
        """
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch financial table from {url}")
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if table is None:
            return {}

        # Parse header row to get years
        thead = table.find("thead")
        if thead is None:
            return {}

        header_row = thead.find("tr")
        if header_row is None:
            return {}

        header_cells = header_row.find_all(["th", "td"])
        # First cell is label column; remaining are years
        years = []
        for cell in header_cells[1:]:
            text = cell.get_text(strip=True)
            try:
                years.append(int(text))
            except ValueError:
                years.append(text)

        result: dict = {"years": years}

        tbody = table.find("tbody")
        if tbody is None:
            return result

        for row in tbody.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            label = cells[0].get_text(strip=True)
            row_data: dict = {}
            for i, year in enumerate(years):
                if i + 1 < len(cells):
                    raw = cells[i + 1].get_text(strip=True)
                    try:
                        row_data[year] = _parse_value(raw)
                    except (ValueError, AttributeError):
                        row_data[year] = None
                else:
                    row_data[year] = None
            result[label] = row_data

        return result

    def scrape_fundamentals(self, symbol: str) -> dict:
        """Scrape fundamental financial data from dadosdemercado.com.br.

        Fetches balance sheet (balanco) for net debt and income statement
        (resultado) for EPS, net income, and EBITDA.
        """
        empty = {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }

        ticker = _strip_sa(symbol).lower()
        balanco_url = f"{self._base_url}/acoes/{ticker}/balanco"
        resultado_url = f"{self._base_url}/acoes/{ticker}/resultado"

        balanco = self._scrape_financial_table(balanco_url)
        resultado = self._scrape_financial_table(resultado_url)

        if not balanco and not resultado:
            return empty

        years = resultado.get("years") or balanco.get("years") or []

        eps_row = resultado.get("LPA", {})
        net_income_row = resultado.get("Lucro Líquido", {})
        ebitda_row = resultado.get("EBITDA", {})
        net_debt_row = balanco.get("Dívida Líquida", {})

        eps_history = [eps_row[y] for y in years if y in eps_row and eps_row[y] is not None]
        net_income_history = [net_income_row[y] for y in years if y in net_income_row and net_income_row[y] is not None]
        debt_history = [net_debt_row[y] for y in years if y in net_debt_row and net_debt_row[y] is not None]

        # Build raw_data for charts (year-keyed records)
        raw_data = []
        for y in years:
            eps = eps_row.get(y)
            ni = net_income_row.get(y)
            nd = net_debt_row.get(y)
            ebitda = ebitda_row.get(y)
            nde = round(nd / ebitda, 4) if nd is not None and ebitda is not None and ebitda != 0 else None
            if eps is not None or ni is not None:
                raw_data.append({"year": y, "eps": eps or 0, "net_income": ni or 0, "net_debt_ebitda": nde or 0})

        # Compute most recent net_debt / ebitda
        current_net_debt_ebitda = None
        for y in years:
            net_debt = net_debt_row.get(y)
            ebitda = ebitda_row.get(y)
            if net_debt is not None and ebitda is not None and ebitda != 0:
                current_net_debt_ebitda = round(net_debt / ebitda, 4)
                break  # use most recent year that has both values

        return {
            "ipo_years": None,
            "eps_history": eps_history,
            "net_income_history": net_income_history,
            "debt_history": debt_history,
            "current_net_debt_ebitda": current_net_debt_ebitda,
            "raw_data": raw_data,
        }

    def _parse_html(self, html: str) -> list[DividendRecord]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[DividendRecord] = []

        table = soup.find("table")
        if table is None:
            return records

        tbody = table.find("tbody")
        if tbody is None:
            return records

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            try:
                # Real column order: Tipo, Valor, Data Com, Data Ex, Pagamento
                dividend_type = cells[0].get_text(strip=True)
                value = _parse_value(cells[1].get_text(strip=True))
                record_date = _parse_date(cells[2].get_text(strip=True))
                ex_date = _parse_date(cells[3].get_text(strip=True))
                payment_date = _parse_date(cells[4].get_text(strip=True))

                if record_date is None or ex_date is None:
                    continue

                records.append(DividendRecord(
                    dividend_type=dividend_type,
                    value=value,
                    record_date=record_date,
                    ex_date=ex_date,
                    payment_date=payment_date,
                ))
            except (ValueError, IndexError):
                logger.warning(f"Skipping unparseable dividend row: {row}")
                continue

        return records
