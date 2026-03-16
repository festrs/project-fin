# Brazilian Dividends Scraper Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape Brazilian stock dividend history from dadosdemercado.com.br and store in a `DividendHistory` table, running 2x/week via APScheduler.

**Architecture:** New `DadosDeMercadoProvider` scrapes HTML tables using httpx + BeautifulSoup. A `DividendScraperScheduler` orchestrates scraping for all BR portfolio symbols, upserting results into a new `DividendHistory` model. Independent APScheduler cron job runs Tuesday/Friday at 6 UTC.

**Tech Stack:** Python, httpx, beautifulsoup4, SQLAlchemy, APScheduler

**Spec:** `docs/superpowers/specs/2026-03-16-brazilian-dividends-scraper-design.md`

---

## Chunk 1: Model + Config

### Task 1: DividendHistory Model

**Files:**
- Create: `backend/app/models/dividend_history.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_models/test_dividend_history.py`

- [ ] **Step 1: Write the failing test**

Verify `backend/tests/test_models/__init__.py` exists (create if missing), then create:

```python
# backend/tests/test_models/test_dividend_history.py
from datetime import date

from app.models.dividend_history import DividendHistory


class TestDividendHistoryModel:
    def test_create_dividend_history(self, db):
        record = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=1.50,
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="PETR4.SA").first()
        assert saved is not None
        assert saved.dividend_type == "Dividendo"
        assert saved.value == 1.50
        assert saved.record_date == date(2025, 10, 22)
        assert saved.ex_date == date(2025, 10, 23)
        assert saved.payment_date == date(2025, 11, 28)
        assert saved.id is not None
        assert saved.created_at is not None
        assert saved.updated_at is not None

    def test_payment_date_nullable(self, db):
        record = DividendHistory(
            symbol="VALE3.SA",
            dividend_type="JCP",
            value=0.75,
            record_date=date(2025, 6, 15),
            ex_date=date(2025, 6, 16),
            payment_date=None,
        )
        db.add(record)
        db.commit()

        saved = db.query(DividendHistory).filter_by(symbol="VALE3.SA").first()
        assert saved.payment_date is None

    def test_unique_constraint_prevents_duplicates(self, db):
        from sqlalchemy.exc import IntegrityError
        import pytest

        record1 = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=1.50,
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
        )
        db.add(record1)
        db.commit()

        record2 = DividendHistory(
            symbol="PETR4.SA",
            dividend_type="Dividendo",
            value=1.50,
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 24),
        )
        db.add(record2)
        with pytest.raises(IntegrityError):
            db.commit()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_models/test_dividend_history.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.dividend_history'`

- [ ] **Step 3: Write the DividendHistory model**

```python
# backend/app/models/dividend_history.py
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import String, Float, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DividendHistory(Base):
    __tablename__ = "dividend_history"
    __table_args__ = (
        UniqueConstraint("symbol", "record_date", "dividend_type", "value", name="uq_dividend_record"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    dividend_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 4: Export from models __init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.dividend_history import DividendHistory
```
And add `"DividendHistory"` to the `__all__` list.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_models/test_dividend_history.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/dividend_history.py backend/app/models/__init__.py backend/tests/test_models/test_dividend_history.py
git commit -m "feat: add DividendHistory model with unique constraint"
```

### Task 2: Configuration Settings

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_config.py`:

```python
class TestDividendScraperConfig:
    def test_default_values(self):
        from app.config import Settings
        s = Settings(
            finnhub_api_key="x", brapi_api_key="x",
            _env_file=None,
        )
        assert s.enable_dividend_scraper is True
        assert s.dividend_scraper_days == "tue,fri"
        assert s.dividend_scraper_hour == 6
        assert s.dividend_scraper_delay == 2.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_config.py::TestDividendScraperConfig -v`
Expected: FAIL with `ValidationError` (unknown fields)

- [ ] **Step 3: Add settings to config.py**

Add these fields to the `Settings` class in `backend/app/config.py`:

```python
    enable_dividend_scraper: bool = True
    dividend_scraper_days: str = "tue,fri"
    dividend_scraper_hour: int = 6
    dividend_scraper_delay: float = 2.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_config.py::TestDividendScraperConfig -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat: add dividend scraper configuration settings"
```

### Task 3: Add beautifulsoup4 dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add dependency**

Add `beautifulsoup4==4.12.3` to `backend/requirements.txt`.

- [ ] **Step 2: Install it**

Run: `cd backend && pip install beautifulsoup4==4.12.3`

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add beautifulsoup4 dependency for HTML scraping"
```

---

## Chunk 2: Provider (Scraper)

### Task 4: DadosDeMercadoProvider

**Files:**
- Create: `backend/app/providers/dados_de_mercado.py`
- Test: `backend/tests/test_providers/test_dados_de_mercado.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_providers/test_dados_de_mercado.py
from datetime import date
from unittest.mock import MagicMock, patch

from app.providers.dados_de_mercado import DadosDeMercadoProvider, DividendRecord


SAMPLE_HTML = """
<html><body>
<table>
<thead><tr><th>Tipo</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th><th>Valor</th></tr></thead>
<tbody>
<tr><td>Dividendo</td><td>22/10/2025</td><td>23/10/2025</td><td>28/11/2025</td><td>0,752895</td></tr>
<tr><td>JCP</td><td>15/06/2025</td><td>16/06/2025</td><td>—</td><td>1,234567</td></tr>
</tbody>
</table>
</body></html>
"""


class TestDadosDeMercadoProvider:
    def test_scrape_dividends_parses_html_table(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("AGRO3.SA")

        assert len(results) == 2

        assert results[0].dividend_type == "Dividendo"
        assert results[0].value == 0.752895
        assert results[0].record_date == date(2025, 10, 22)
        assert results[0].ex_date == date(2025, 10, 23)
        assert results[0].payment_date == date(2025, 11, 28)

        assert results[1].dividend_type == "JCP"
        assert results[1].value == 1.234567
        assert results[1].payment_date is None

    def test_strips_sa_suffix_in_url(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table><thead><tr><th>Tipo</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th><th>Valor</th></tr></thead><tbody></tbody></table></body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp) as mock_get:
            provider.scrape_dividends("PETR4.SA")

        call_url = mock_get.call_args[0][0]
        assert "petr4" in call_url.lower()
        assert ".SA" not in call_url
        assert "/dividendos" in call_url

    def test_handles_http_error(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("INVALID.SA")

        assert results == []

    def test_handles_empty_table(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table><thead><tr><th>Tipo</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th><th>Valor</th></tr></thead><tbody></tbody></table></body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("AGRO3.SA")

        assert results == []


class TestDividendRecord:
    def test_dataclass_fields(self):
        record = DividendRecord(
            dividend_type="Dividendo",
            value=1.50,
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        assert record.dividend_type == "Dividendo"
        assert record.value == 1.50
        assert record.payment_date == date(2025, 11, 28)

    def test_payment_date_optional(self):
        record = DividendRecord(
            dividend_type="JCP",
            value=0.75,
            record_date=date(2025, 6, 15),
            ex_date=date(2025, 6, 16),
            payment_date=None,
        )
        assert record.payment_date is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_providers/test_dados_de_mercado.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.providers.dados_de_mercado'`

- [ ] **Step 3: Write the provider implementation**

```python
# backend/app/providers/dados_de_mercado.py
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
    """Parse Brazilian number format (comma as decimal separator)."""
    return float(text.strip().replace(".", "").replace(",", "."))


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
                dividend_type = cells[0].get_text(strip=True)
                record_date = _parse_date(cells[1].get_text(strip=True))
                ex_date = _parse_date(cells[2].get_text(strip=True))
                payment_date = _parse_date(cells[3].get_text(strip=True))
                value = _parse_value(cells[4].get_text(strip=True))

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_providers/test_dados_de_mercado.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/dados_de_mercado.py backend/tests/test_providers/test_dados_de_mercado.py
git commit -m "feat: add DadosDeMercadoProvider for dividend HTML scraping"
```

---

## Chunk 3: Scheduler + Integration

### Task 5: DividendScraperScheduler

**Files:**
- Create: `backend/app/services/dividend_scraper_scheduler.py`
- Test: `backend/tests/test_services/test_dividend_scraper_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_services/test_dividend_scraper_scheduler.py
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.dados_de_mercado import DividendRecord
from app.services.dividend_scraper_scheduler import DividendScraperScheduler


@pytest.fixture
def provider():
    return MagicMock()


@pytest.fixture
def scheduler(provider):
    return DividendScraperScheduler(provider=provider, delay=0.0)


def _setup_br_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US")
    db.add_all([ac_br, ac_us])
    db.flush()

    tx_br1 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    tx_br2 = Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="VALE3.SA",
        type="buy", quantity=50, unit_price=60.0, total_value=3000.0,
        currency="BRL", date=date(2025, 1, 1),
    )
    tx_us = Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
        type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
        currency="USD", date=date(2025, 1, 1),
    )
    db.add_all([tx_br1, tx_br2, tx_us])
    db.commit()


class TestDividendScraperScheduler:
    def test_scrapes_only_br_symbols(self, scheduler, provider, db):
        _setup_br_holdings(db)

        provider.scrape_dividends.return_value = []

        scheduler.scrape_all(db)

        # Should only scrape BR symbols, not AAPL
        scraped_symbols = [call.args[0] for call in provider.scrape_dividends.call_args_list]
        assert "AAPL" not in scraped_symbols
        assert set(scraped_symbols) == {"PETR4.SA", "VALE3.SA"}

    def test_stores_scraped_dividends(self, scheduler, provider, db):
        _setup_br_holdings(db)

        provider.scrape_dividends.side_effect = lambda sym: [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ] if sym == "PETR4.SA" else []

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1
        assert records[0].value == 1.50
        assert records[0].dividend_type == "Dividendo"

    def test_skips_existing_duplicates(self, scheduler, provider, db):
        _setup_br_holdings(db)

        # Pre-existing record
        existing = DividendHistory(
            symbol="PETR4.SA", dividend_type="Dividendo", value=1.50,
            record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        db.add(existing)
        db.commit()

        provider.scrape_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1  # No duplicate inserted

    def test_continues_on_individual_failure(self, scheduler, provider, db):
        _setup_br_holdings(db)

        def side_effect(sym):
            if sym == "PETR4.SA":
                raise Exception("Network error")
            return [
                DividendRecord(
                    dividend_type="Dividendo", value=2.00,
                    record_date=date(2025, 5, 10), ex_date=date(2025, 5, 11),
                    payment_date=date(2025, 6, 1),
                ),
            ]

        provider.scrape_dividends.side_effect = side_effect

        scheduler.scrape_all(db)

        # PETR4.SA failed, but VALE3.SA should still be stored
        petr = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(petr) == 0

        vale = db.query(DividendHistory).filter_by(symbol="VALE3.SA").all()
        assert len(vale) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_services/test_dividend_scraper_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.dividend_scraper_scheduler'`

- [ ] **Step 3: Write the scheduler implementation**

```python
# backend/app/services/dividend_scraper_scheduler.py
import logging
import time

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.providers.dados_de_mercado import DadosDeMercadoProvider

logger = logging.getLogger(__name__)


class DividendScraperScheduler:
    def __init__(self, provider: DadosDeMercadoProvider, delay: float = 2.0):
        self._provider = provider
        self._delay = delay

    def scrape_all(self, db: Session) -> None:
        symbols = (
            db.query(Transaction.asset_symbol)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.country == "BR")
            .distinct()
            .all()
        )

        for (symbol,) in symbols:
            try:
                records = self._provider.scrape_dividends(symbol)
                new_count = 0

                for rec in records:
                    exists = (
                        db.query(DividendHistory)
                        .filter_by(
                            symbol=symbol,
                            record_date=rec.record_date,
                            dividend_type=rec.dividend_type,
                            value=rec.value,
                        )
                        .first()
                    )
                    if exists:
                        continue

                    entry = DividendHistory(
                        symbol=symbol,
                        dividend_type=rec.dividend_type,
                        value=rec.value,
                        record_date=rec.record_date,
                        ex_date=rec.ex_date,
                        payment_date=rec.payment_date,
                    )
                    db.add(entry)
                    new_count += 1

                db.commit()
                logger.info(f"Scraped dividends for {symbol}: {new_count} new records")
            except Exception:
                logger.exception(f"Failed to scrape dividends for {symbol}")
                db.rollback()
            finally:
                if self._delay > 0:
                    time.sleep(self._delay)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_services/test_dividend_scraper_scheduler.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dividend_scraper_scheduler.py backend/tests/test_services/test_dividend_scraper_scheduler.py
git commit -m "feat: add DividendScraperScheduler for periodic dividend scraping"
```

### Task 6: Register in main.py lifespan

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add the _run_dividend_scrape function**

Add this function to `backend/app/main.py` after `_run_scheduled_fetch`:

```python
def _run_dividend_scrape():
    from app.database import SessionLocal
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.services.dividend_scraper_scheduler import DividendScraperScheduler

    provider = DadosDeMercadoProvider()
    scheduler = DividendScraperScheduler(provider=provider, delay=settings.dividend_scraper_delay)

    db = SessionLocal()
    try:
        scheduler.scrape_all(db)
    except Exception:
        logger.exception("Scheduled dividend scrape failed")
    finally:
        db.close()
```

- [ ] **Step 2: Register the APScheduler job in the lifespan**

Inside the `if settings.enable_scheduler:` block in the `lifespan` function, between the existing `bg_scheduler.add_job(...)` call (line 47-51) and `bg_scheduler.start()` (line 52), add:

```python
        if settings.enable_dividend_scraper:
            bg_scheduler.add_job(
                _run_dividend_scrape, "cron",
                day_of_week=settings.dividend_scraper_days,
                hour=settings.dividend_scraper_hour,
                id="dividend_scrape",
            )
            logger.info(
                f"Dividend scraper scheduled ({settings.dividend_scraper_days} at {settings.dividend_scraper_hour}:00 UTC)"
            )
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest -v`
Expected: All existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: register dividend scraper in APScheduler lifespan"
```

### Task 7: Full Integration Test

- [ ] **Step 1: Run the full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Manual smoke test (optional)**

Start the server and verify the scheduler logs:
```bash
cd backend && python -m uvicorn app.main:app --reload
```

Look for log line: `Dividend scraper scheduled (tue,fri at 6:00 UTC)`

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address any integration issues from dividend scraper"
```
