import logging
from datetime import date
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from app.providers.common import DividendRecord, Symbol

logger = logging.getLogger(__name__)

BASE_URL = "https://www.dadosdemercado.com.br"
USER_AGENT = "ProjectFin/1.0"


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

    Handles optional '* ' prefix used for older adjusted values,
    and suffixes like 'mi' (millions), 'B' (billions), 'M' (millions), '%'.
    """
    cleaned = text.strip().lstrip("* ")
    if not cleaned or cleaned in ("--", "—", "-"):
        raise ValueError(f"empty value: {text!r}")

    # Strip percentage sign (return as fraction-like value, not multiplied)
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1].strip()
        num = float(cleaned.replace(".", "").replace(",", "."))
        return num / 100.0

    # Handle suffixes: 'mi' (milhões), 'B' (bilhões), 'M' (milhões)
    multiplier = 1.0
    # \u202f is narrow no-break space often before 'mi'
    cleaned = cleaned.replace("\u202f", " ")
    if cleaned.lower().endswith(" mi"):
        cleaned = cleaned[:-3].strip()
        multiplier = 1_000_000
    elif cleaned.upper().endswith(" B"):
        cleaned = cleaned[:-2].strip()
        multiplier = 1_000_000_000
    elif cleaned.upper().endswith(" M"):
        cleaned = cleaned[:-2].strip()
        multiplier = 1_000_000
    elif cleaned.lower().endswith("mi"):
        cleaned = cleaned[:-2].strip()
        multiplier = 1_000_000
    elif cleaned.endswith("B"):
        cleaned = cleaned[:-1].strip()
        multiplier = 1_000_000_000
    elif cleaned.endswith("M"):
        cleaned = cleaned[:-1].strip()
        multiplier = 1_000_000

    num = float(cleaned.replace(".", "").replace(",", "."))
    return num * multiplier


def _parse_monetary_value(text: str) -> Decimal:
    """Parse a Brazilian-formatted monetary value string to Decimal."""
    raw = _parse_value(text)
    return Decimal(str(raw))


class DadosDeMercadoProvider:
    def __init__(self, base_url: str = BASE_URL):
        self._base_url = base_url

    def scrape_dividends(self, symbol: str) -> list[DividendRecord]:
        ticker = Symbol.strip_sa(symbol).lower()
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

    def _parse_tables_from_html(self, html: str) -> dict[str, dict]:
        """Parse all financial tables from the main stock page.

        Returns a dict keyed by table type: 'indicadores', 'resultados'.
        Each value has {"years": [...], "RowLabel": {year: value, ...}, ...}.
        """
        soup = BeautifulSoup(html, "html.parser")
        tables: dict[str, dict] = {}

        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue
            header_row = thead.find("tr")
            if not header_row:
                continue

            header_cells = header_row.find_all(["th", "td"])
            headers = [c.get_text(strip=True) for c in header_cells]

            # Extract integer years from header, skip TTM/quarterly columns
            years: list[int] = []
            year_indices: list[int] = []
            for i, h in enumerate(headers[1:], start=1):
                try:
                    years.append(int(h))
                    year_indices.append(i)
                except ValueError:
                    continue

            if not years:
                continue

            tbody = table.find("tbody")
            if not tbody:
                continue

            parsed: dict = {"years": years}
            row_labels: set[str] = set()
            for row in tbody.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                label = cells[0].get_text(strip=True)
                row_labels.add(label)
                row_data: dict[int, float | None] = {}
                for yi, year in zip(year_indices, years):
                    if yi < len(cells):
                        raw = cells[yi].get_text(strip=True)
                        try:
                            row_data[year] = _parse_value(raw)
                        except (ValueError, AttributeError):
                            row_data[year] = None
                    else:
                        row_data[year] = None
                parsed[label] = row_data

            # Identify table type by characteristic row labels
            if "LPA" in row_labels and "P/L" in row_labels:
                tables["indicadores"] = parsed
            elif "Lucro líquido" in row_labels and "Receita líquida" in row_labels:
                # Only take the annual table (has integer year columns)
                if "resultados" not in tables:
                    tables["resultados"] = parsed

        return tables

    def scrape_fundamentals(self, symbol: str) -> dict:
        """Scrape fundamental financial data from dadosdemercado.com.br.

        Fetches the main stock page which embeds Indicadores (LPA, EBITDA,
        Dívida líquida) and Resultados (Lucro líquido) tables.
        """
        empty: dict = {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }

        ticker = Symbol.strip_sa(symbol).lower()
        url = f"{self._base_url}/acoes/{ticker}"

        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch main page for {symbol}")
            return empty

        try:
            tables = self._parse_tables_from_html(resp.text)
        except Exception:
            logger.exception(f"Failed to parse tables from main page for {symbol}")
            return empty

        indicadores = tables.get("indicadores", {})
        resultados = tables.get("resultados", {})

        if not indicadores and not resultados:
            return empty

        years = indicadores.get("years") or resultados.get("years") or []

        eps_row = indicadores.get("LPA", {})
        ebitda_row = indicadores.get("EBITDA", {})
        net_debt_row = indicadores.get("Dívida líquida", {})
        net_income_row = resultados.get("Lucro líquido", {})

        eps_history = [eps_row[y] for y in years if y in eps_row and eps_row[y] is not None]
        net_income_history = [net_income_row[y] for y in years if y in net_income_row and net_income_row[y] is not None]

        # Build raw_data and debt_history (net_debt / ebitda ratio per year)
        raw_data = []
        debt_history: list[float] = []
        current_net_debt_ebitda = None

        for y in years:
            eps = eps_row.get(y)
            ni = net_income_row.get(y)
            nd = net_debt_row.get(y)
            ebitda = ebitda_row.get(y)

            nde: float | None = None
            if nd is not None and ebitda is not None and ebitda != 0:
                nde = round(nd / ebitda, 4)
                debt_history.append(nde)
                if current_net_debt_ebitda is None:
                    current_net_debt_ebitda = nde

            if eps is not None or ni is not None:
                raw_data.append({
                    "year": y,
                    "eps": eps or 0,
                    "net_income": ni or 0,
                    "net_debt_ebitda": nde or 0,
                })

        return {
            "ipo_years": len(years) if len(years) >= 5 else None,
            "eps_history": eps_history,
            "net_income_history": net_income_history,
            "debt_history": debt_history,
            "current_net_debt_ebitda": current_net_debt_ebitda,
            "raw_data": raw_data,
        }

    def scrape_splits(self, symbol: str) -> list[dict]:
        """Scrape stock splits (desdobramentos) from dadosdemercado.com.br."""
        ticker = Symbol.strip_sa(symbol).lower()
        url = f"{self._base_url}/acoes/{ticker}/desdobramentos"

        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch splits page for {symbol}")
            return []

        try:
            return self._parse_splits_html(resp.text, symbol)
        except Exception:
            logger.exception(f"Failed to parse splits HTML for {symbol}")
            return []

    def _parse_splits_html(self, html: str, symbol: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        splits: list[dict] = []

        for table in soup.find_all("table"):
            thead = table.find("thead")
            if not thead:
                continue
            headers = [th.get_text(strip=True) for th in thead.find_all(["th", "td"])]
            if "Evento" not in headers or "Razão" not in headers:
                continue

            tbody = table.find("tbody")
            if not tbody:
                continue

            for row in tbody.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 5:
                    continue

                evento = cells[0]
                if evento not in ("Desdobramento", "Bonificação"):
                    continue

                ex_date_str = cells[3]
                razao = cells[4]

                ex_date = _parse_date(ex_date_str)
                if not ex_date:
                    continue

                # Parse ratio like "1:2" -> fromFactor=1, toFactor=2
                try:
                    parts = razao.split(":")
                    from_factor = int(parts[0])
                    to_factor = int(parts[1])
                except (ValueError, IndexError):
                    continue

                event_type = "bonificacao" if evento == "Bonificação" else "split"
                splits.append({
                    "symbol": symbol,
                    "date": ex_date.isoformat(),
                    "fromFactor": from_factor,
                    "toFactor": to_factor,
                    "eventType": event_type,
                })

        return splits

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
                value = _parse_monetary_value(cells[1].get_text(strip=True))
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
