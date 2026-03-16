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
