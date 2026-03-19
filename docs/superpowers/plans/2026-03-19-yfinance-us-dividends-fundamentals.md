# YFinance US Dividends & Fundamentals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Finnhub with yfinance for US stock dividends and fundamentals data, unifying dividend storage across US and BR stocks.

**Architecture:** New `YFinanceProvider` handles US dividends and fundamentals. `DividendRecord` dataclass extracted to shared `providers/common.py`. Dividend scheduler handles both BR (DadosDeMercado) and US (yfinance). Portfolio dividends endpoint simplified to single DB query for all countries.

**Tech Stack:** Python 3.12, yfinance, FastAPI, SQLAlchemy, pytest

**Spec:** `docs/superpowers/specs/2026-03-19-yfinance-us-dividends-fundamentals-design.md`

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/providers/common.py` | Shared `DividendRecord` dataclass |
| Create | `app/providers/yfinance.py` | YFinance API wrapper (dividends + fundamentals) |
| Create | `tests/test_providers/test_yfinance.py` | Unit tests for YFinanceProvider |
| Modify | `app/providers/dados_de_mercado.py` | Import `DividendRecord` from `common.py` instead of defining it |
| Modify | `app/services/dividend_scraper_scheduler.py` | Rename to `DividendScheduler`, handle BR + US |
| Modify | `tests/test_services/test_dividend_scraper_scheduler.py` | Update for renamed class + US flow |
| Modify | `app/services/fundamentals_scheduler.py` | Replace `finnhub_provider` with `yfinance_provider` |
| Modify | `tests/test_services/test_fundamentals_scheduler.py` | Swap Finnhub mock for yfinance mock |
| Modify | `app/routers/portfolio.py` | Unified DB query for dividends (remove Finnhub calls, cache, ThreadPoolExecutor) |
| Modify | `app/routers/fundamentals.py` | Use YFinanceProvider instead of FinnhubProvider |
| Modify | `app/providers/finnhub.py` | Remove `get_dividend_metric()`, `get_dividends_for_year()`, `get_fundamentals()` |
| Modify | `app/main.py` | Wire YFinanceProvider into schedulers |
| Modify | `app/config.py` | Add `dividend_us_delay` setting |
| Modify | `requirements.txt` | Add `yfinance` |

---

### Task 1: Extract DividendRecord to shared module + add yfinance dependency

**Files:**
- Create: `backend/app/providers/common.py`
- Modify: `backend/app/providers/dados_de_mercado.py:14-20` (remove class, add import)
- Modify: `backend/requirements.txt` (add yfinance)

- [ ] **Step 1: Create `providers/common.py`**

```python
from dataclasses import dataclass
from datetime import date


@dataclass
class DividendRecord:
    dividend_type: str
    value: float
    record_date: date
    ex_date: date
    payment_date: date | None
```

- [ ] **Step 2: Update `dados_de_mercado.py` to import from common**

Replace the `DividendRecord` class definition (lines 14-20) with:
```python
from app.providers.common import DividendRecord
```

Remove the `from dataclasses import dataclass` import (line 2) since it's no longer needed here.

- [ ] **Step 3: Add yfinance to requirements.txt**

Append `yfinance` to `backend/requirements.txt`.

- [ ] **Step 4: Install and run existing tests to verify no regressions**

Run: `cd backend && pip install yfinance && pytest tests/test_services/test_dividend_scraper_scheduler.py tests/test_providers/test_dados_de_mercado.py -v`
Expected: All existing tests PASS (DividendRecord import path changed but behavior identical).

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/common.py backend/app/providers/dados_de_mercado.py backend/requirements.txt
git commit -m "refactor: extract DividendRecord to providers/common.py, add yfinance dep"
```

---

### Task 2: Create YFinanceProvider — dividends

**Files:**
- Create: `backend/app/providers/yfinance.py`
- Create: `backend/tests/test_providers/test_yfinance.py`

- [ ] **Step 1: Write failing test for `get_dividends()`**

```python
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.providers.yfinance import YFinanceProvider


class TestGetDividends:
    def test_returns_dividend_records(self):
        provider = YFinanceProvider()

        index = pd.DatetimeIndex([pd.Timestamp("2025-02-07"), pd.Timestamp("2025-05-09")])
        mock_dividends = pd.Series([0.25, 0.25], index=index)

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.dividends = mock_dividends
            mock_yf.Ticker.return_value = mock_ticker

            records = provider.get_dividends("AAPL")

        assert len(records) == 2
        assert records[0].dividend_type == "Dividend"
        assert records[0].value == 0.25
        assert records[0].ex_date == date(2025, 2, 7)
        assert records[0].record_date == date(2025, 2, 7)
        assert records[0].payment_date is None

    def test_returns_empty_on_error(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            records = provider.get_dividends("BAD")

        assert records == []

    def test_returns_empty_for_no_dividends(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.dividends = pd.Series([], dtype=float)
            mock_yf.Ticker.return_value = mock_ticker

            records = provider.get_dividends("BRK-B")

        assert records == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_providers/test_yfinance.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement `get_dividends()` in `providers/yfinance.py`**

```python
import logging

import yfinance as yf

from app.providers.common import DividendRecord

logger = logging.getLogger(__name__)


class YFinanceProvider:
    def get_dividends(self, symbol: str) -> list[DividendRecord]:
        """Fetch full dividend history for a US stock."""
        try:
            ticker = yf.Ticker(symbol)
            dividends = ticker.dividends

            if dividends.empty:
                return []

            records = []
            for ts, amount in dividends.items():
                ex_date = ts.date()
                records.append(DividendRecord(
                    dividend_type="Dividend",
                    value=round(float(amount), 6),
                    record_date=ex_date,
                    ex_date=ex_date,
                    payment_date=None,
                ))
            return records
        except Exception:
            logger.warning("Failed to fetch dividends for %s", symbol, exc_info=True)
            return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_providers/test_yfinance.py::TestGetDividends -v`
Expected: All 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/yfinance.py backend/tests/test_providers/test_yfinance.py
git commit -m "feat: add YFinanceProvider.get_dividends()"
```

---

### Task 3: YFinanceProvider — fundamentals

**Files:**
- Modify: `backend/app/providers/yfinance.py`
- Modify: `backend/tests/test_providers/test_yfinance.py`

- [ ] **Step 1: Write failing test for `get_fundamentals()`**

Append to `test_yfinance.py`:

```python
class TestGetFundamentals:
    def _make_mock_ticker(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"firstTradeDateEpochUtc": 1072915200}  # 2004-01-01

        dates = pd.DatetimeIndex([
            pd.Timestamp("2024-12-31"),
            pd.Timestamp("2023-12-31"),
            pd.Timestamp("2022-12-31"),
        ])
        mock_ticker.financials = pd.DataFrame({
            dates[0]: {"Diluted EPS": 6.0, "Net Income": 95000, "EBITDA": 130000},
            dates[1]: {"Diluted EPS": 5.0, "Net Income": 80000, "EBITDA": 120000},
            dates[2]: {"Diluted EPS": 4.0, "Net Income": 70000, "EBITDA": 110000},
        })
        mock_ticker.balance_sheet = pd.DataFrame({
            dates[0]: {"Long Term Debt": 100000},
            dates[1]: {"Long Term Debt": 95000},
            dates[2]: {"Long Term Debt": 90000},
        })
        return mock_ticker

    def test_returns_fundamentals_dict(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.return_value = self._make_mock_ticker()
            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] is not None
        assert result["ipo_years"] > 20
        assert len(result["eps_history"]) == 3
        assert result["eps_history"] == [4.0, 5.0, 6.0]  # chronological
        assert len(result["net_income_history"]) == 3
        assert len(result["debt_history"]) == 3
        assert result["current_net_debt_ebitda"] is not None
        assert len(result["raw_data"]) == 3

    def test_returns_empty_on_error(self):
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            result = provider.get_fundamentals("BAD")

        assert result["ipo_years"] is None
        assert result["eps_history"] == []
        assert result["net_income_history"] == []
        assert result["debt_history"] == []
        assert result["current_net_debt_ebitda"] is None
        assert result["raw_data"] == []

    def test_fallback_ipo_key(self):
        """Uses firstTradeDate when firstTradeDateEpochUtc missing."""
        provider = YFinanceProvider()

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = self._make_mock_ticker()
            mock_ticker.info = {"firstTradeDate": 1072915200}
            mock_yf.Ticker.return_value = mock_ticker

            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] is not None
        assert result["ipo_years"] > 20

    def test_fallback_row_labels(self):
        """Uses Basic EPS when Diluted EPS missing, Total Debt when Long Term Debt missing."""
        provider = YFinanceProvider()
        dates = pd.DatetimeIndex([pd.Timestamp("2024-12-31")])

        with patch("app.providers.yfinance.yf") as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.info = {"firstTradeDateEpochUtc": 1072915200}
            mock_ticker.financials = pd.DataFrame({
                dates[0]: {"Basic EPS": 5.0, "Net Income": 80000, "Operating Income": 100000},
            })
            mock_ticker.balance_sheet = pd.DataFrame({
                dates[0]: {"Total Debt": 90000},
            })
            mock_yf.Ticker.return_value = mock_ticker

            result = provider.get_fundamentals("TEST")

        assert result["eps_history"] == [5.0]
        assert result["debt_history"][0] == pytest.approx(90000 / 100000, rel=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_providers/test_yfinance.py::TestGetFundamentals -v`
Expected: FAIL (method not found)

- [ ] **Step 3: Implement `get_fundamentals()`**

Add to `YFinanceProvider` in `providers/yfinance.py`:

```python
    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental financial data for scoring."""
        empty = {
            "ipo_years": None,
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # IPO years
            epoch = info.get("firstTradeDateEpochUtc") or info.get("firstTradeDate")
            if epoch:
                from datetime import datetime, timezone
                ipo_date = datetime.fromtimestamp(epoch, tz=timezone.utc)
                ipo_years = (datetime.now(timezone.utc) - ipo_date).days // 365
            else:
                ipo_years = None

            financials = ticker.financials
            balance_sheet = ticker.balance_sheet

            if financials is None or financials.empty:
                empty["ipo_years"] = ipo_years
                return empty

            # Sort columns chronologically (oldest first)
            sorted_cols = sorted(financials.columns)

            def _get_row(df, *labels):
                """Get row values for first matching label."""
                if df is None or df.empty:
                    return {}
                for label in labels:
                    if label in df.index:
                        return {col: df.loc[label, col] for col in sorted_cols if col in df.columns}
                return {}

            eps_row = _get_row(financials, "Diluted EPS", "Basic EPS")
            ni_row = _get_row(financials, "Net Income")
            ebitda_row = _get_row(financials, "EBITDA", "Operating Income")
            debt_row = _get_row(balance_sheet, "Long Term Debt", "Total Debt")

            eps_history = []
            net_income_history = []
            debt_history = []
            raw_data = []

            for col in sorted_cols:
                eps = float(eps_row.get(col, 0) or 0)
                ni = float(ni_row.get(col, 0) or 0)
                ebitda = float(ebitda_row.get(col, 0) or 0)
                debt = float(debt_row.get(col, 0) or 0)
                debt_ratio = (debt / ebitda) if ebitda != 0 else 0

                eps_history.append(eps)
                net_income_history.append(ni)
                debt_history.append(debt_ratio)

                year = col.year if hasattr(col, "year") else None
                raw_data.append({
                    "year": year,
                    "eps": eps,
                    "net_income": ni,
                    "net_debt_ebitda": round(debt_ratio, 4),
                })

            current_net_debt_ebitda = debt_history[-1] if debt_history else None

            return {
                "ipo_years": ipo_years,
                "eps_history": eps_history,
                "net_income_history": net_income_history,
                "debt_history": debt_history,
                "current_net_debt_ebitda": current_net_debt_ebitda,
                "raw_data": raw_data,
            }
        except Exception:
            logger.warning("Failed to fetch fundamentals for %s", symbol, exc_info=True)
            return empty
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_providers/test_yfinance.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/yfinance.py backend/tests/test_providers/test_yfinance.py
git commit -m "feat: add YFinanceProvider.get_fundamentals()"
```

---

### Task 4: Update dividend scheduler for BR + US

**Files:**
- Modify: `backend/app/services/dividend_scraper_scheduler.py`
- Modify: `backend/tests/test_services/test_dividend_scraper_scheduler.py`

- [ ] **Step 1: Update tests for renamed class + US support**

Replace `test_dividend_scraper_scheduler.py` entirely:

```python
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.models.user import User
from app.providers.common import DividendRecord
from app.services.dividend_scraper_scheduler import DividendScheduler


@pytest.fixture
def dados_provider():
    return MagicMock()


@pytest.fixture
def yfinance_provider():
    return MagicMock()


@pytest.fixture
def scheduler(dados_provider, yfinance_provider):
    return DividendScheduler(
        dados_provider=dados_provider,
        yfinance_provider=yfinance_provider,
        br_delay=0.0,
        us_delay=0.0,
    )


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=30.0, country="US")
    ac_crypto = AssetClass(user_id=user.id, name="Crypto", target_weight=20.0, country="US")
    db.add_all([ac_br, ac_us, ac_crypto])
    db.flush()

    db.add_all([
        Transaction(
            user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
            type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
            currency="BRL", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
            type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
            currency="USD", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_crypto.id, asset_symbol="BTC",
            type="buy", quantity=1, unit_price=50000.0, total_value=50000.0,
            currency="USD", date=date(2025, 1, 1),
        ),
    ])
    db.commit()


class TestDividendScheduler:
    def test_scrapes_br_with_dados_and_us_with_yfinance(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        br_symbols = [c.args[0] for c in dados_provider.scrape_dividends.call_args_list]
        us_symbols = [c.args[0] for c in yfinance_provider.get_dividends.call_args_list]

        assert set(br_symbols) == {"PETR4.SA"}
        assert set(us_symbols) == {"AAPL"}
        # Crypto excluded
        assert "BTC" not in br_symbols + us_symbols

    def test_stores_us_dividends(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=0.25,
                record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
                payment_date=None,
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="AAPL").all()
        assert len(records) == 1
        assert records[0].value == 0.25
        assert records[0].dividend_type == "Dividend"
        assert records[0].payment_date is None

    def test_stores_br_dividends(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        dados_provider.scrape_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividendo", value=1.50,
                record_date=date(2025, 10, 22), ex_date=date(2025, 10, 23),
                payment_date=date(2025, 11, 28),
            ),
        ]
        yfinance_provider.get_dividends.return_value = []

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="PETR4.SA").all()
        assert len(records) == 1

    def test_skips_existing_duplicates(self, scheduler, dados_provider, yfinance_provider, db):
        _setup_holdings(db)

        db.add(DividendHistory(
            symbol="AAPL", dividend_type="Dividend", value=0.25,
            record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
            payment_date=None,
        ))
        db.commit()

        dados_provider.scrape_dividends.return_value = []
        yfinance_provider.get_dividends.return_value = [
            DividendRecord(
                dividend_type="Dividend", value=0.25,
                record_date=date(2025, 2, 7), ex_date=date(2025, 2, 7),
                payment_date=None,
            ),
        ]

        scheduler.scrape_all(db)

        records = db.query(DividendHistory).filter_by(symbol="AAPL").all()
        assert len(records) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_services/test_dividend_scraper_scheduler.py -v`
Expected: FAIL (DividendScheduler not found)

- [ ] **Step 3: Rewrite `dividend_scraper_scheduler.py`**

```python
import logging
import time

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Note: matches fundamentals_scheduler.py. market_data.py uses a different set
# that includes "Stablecoins" and "Cryptos". This is a pre-existing inconsistency.
CRYPTO_CLASS_NAMES = {"Crypto", "Criptomoedas"}


class DividendScheduler:
    def __init__(self, dados_provider, yfinance_provider, br_delay: float = 2.0, us_delay: float = 1.0):
        self._dados = dados_provider
        self._yfinance = yfinance_provider
        self._br_delay = br_delay
        self._us_delay = us_delay

    def scrape_all(self, db: Session) -> None:
        rows = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(
                AssetClass.country.in_(["BR", "US"]),
                AssetClass.name.notin_(CRYPTO_CLASS_NAMES),
            )
            .distinct()
            .all()
        )

        for symbol, country in rows:
            try:
                if country == "BR":
                    records = self._dados.scrape_dividends(symbol)
                    delay = self._br_delay
                else:
                    records = self._yfinance.get_dividends(symbol)
                    delay = self._us_delay

                new_count = 0
                seen = set()

                for rec in records:
                    key = (symbol, rec.record_date, rec.dividend_type, rec.value)
                    if key in seen:
                        continue
                    seen.add(key)

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
                if delay > 0:
                    time.sleep(delay)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_services/test_dividend_scraper_scheduler.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dividend_scraper_scheduler.py backend/tests/test_services/test_dividend_scraper_scheduler.py
git commit -m "feat: unified DividendScheduler handles BR + US dividends"
```

---

### Task 5: Update fundamentals scheduler to use yfinance

**Files:**
- Modify: `backend/app/services/fundamentals_scheduler.py:17-19,51-53`
- Modify: `backend/tests/test_services/test_fundamentals_scheduler.py`

- [ ] **Step 1: Update tests — replace finnhub mocks with yfinance**

In `test_fundamentals_scheduler.py`:

1. Rename `finnhub_provider` fixture to `yfinance_provider`
2. Update scheduler fixture: `yfinance_provider=yfinance_provider` instead of `finnhub_provider=finnhub_provider`
3. Update all test method signatures and mock references: `finnhub_provider` → `yfinance_provider`, `.get_fundamentals` stays the same method name
4. In `test_discovers_us_and_br_stocks_only`: check `yfinance_provider.get_fundamentals.call_args_list`
5. In `test_continues_on_individual_failure`: set `yfinance_provider.get_fundamentals.side_effect`

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_services/test_fundamentals_scheduler.py -v`
Expected: FAIL (constructor parameter mismatch)

- [ ] **Step 3: Update `fundamentals_scheduler.py`**

In `__init__` (line 18): replace `finnhub_provider` with `yfinance_provider`, store as `self._yfinance`.

In `_fetch_fundamentals` (line 52-53): replace `self._finnhub.get_fundamentals(symbol)` with `self._yfinance.get_fundamentals(symbol)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_services/test_fundamentals_scheduler.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fundamentals_scheduler.py backend/tests/test_services/test_fundamentals_scheduler.py
git commit -m "feat: fundamentals scheduler uses yfinance instead of finnhub"
```

---

### Task 6: Simplify portfolio dividends endpoint (unified DB query)

**Files:**
- Modify: `backend/app/routers/portfolio.py:1-233`

- [ ] **Step 1: Rewrite the dividends endpoint**

Replace the entire `portfolio_dividends` function and remove `_div_cache`, `_DIV_CACHE_TTL`, `ThreadPoolExecutor` import, `as_completed` import.

Key changes:
- Remove `concurrent.futures` imports (`ThreadPoolExecutor`, `as_completed`) — **keep `time`** (used by `_fetch_exchange_rate`)
- Remove lines 103-104: `_div_cache` and `_DIV_CACHE_TTL`
- Remove line 122: `finnhub = market_data._finnhub`
- Replace BR-only query (lines 129-146) with unified query for all stock symbols (BR + US)
- Filter on `ex_date` instead of `payment_date`
- Remove `fetch_dividend` inner function and `ThreadPoolExecutor` block (lines 148-211)
- Replace with simple loop over holdings

Simplified dividends endpoint:

```python
@router.get("/dividends")
@limiter.limit(CRUD_LIMIT)
def portfolio_dividends(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    """Get estimated annual dividends per holding from dividend_history table."""
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)

    asset_classes = db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()
    class_map = {ac.id: ac for ac in asset_classes}

    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    # Collect all stock symbols (BR + US), excluding crypto
    stock_symbols = [
        h["symbol"] for h in holdings
        if class_map.get(h["asset_class_id"])
        and class_map[h["asset_class_id"]].name not in CRYPTO_CLASS_NAMES
        and class_map[h["asset_class_id"]].name != "Stablecoins"
        and class_map[h["asset_class_id"]].country in ("BR", "US")
    ]

    # Single batch query for all dividends (unified BR + US)
    div_map: dict[str, float] = {}
    if stock_symbols:
        rows = (
            db.query(DividendHistory.symbol, func.sum(DividendHistory.value))
            .filter(
                DividendHistory.symbol.in_(stock_symbols),
                DividendHistory.ex_date >= year_start,
                DividendHistory.ex_date <= year_end,
            )
            .group_by(DividendHistory.symbol)
            .all()
        )
        for symbol, total in rows:
            div_map[symbol] = float(total)

    results = []
    for holding in holdings:
        symbol = holding["symbol"]
        ac = class_map.get(holding["asset_class_id"])
        if not ac or holding["quantity"] is None:
            continue
        if ac.name in CRYPTO_CLASS_NAMES or ac.name == "Stablecoins":
            continue

        dps = div_map.get(symbol, 0)
        if dps <= 0:
            continue

        annual_income = dps * holding["quantity"]
        currency = "BRL" if ac.country == "BR" else "USD"

        results.append({
            "symbol": symbol,
            "asset_class_id": holding["asset_class_id"],
            "quantity": holding["quantity"],
            "dividend_per_share": round(dps, 6),
            "dividend_yield": 0,
            "annual_income": round(annual_income, 2),
            "currency": currency,
        })

    # Aggregate by asset class
    class_totals: dict[str, dict] = {}
    for r in results:
        cid = r["asset_class_id"]
        if cid not in class_totals:
            ac = class_map.get(cid)
            class_totals[cid] = {
                "asset_class_id": cid,
                "class_name": ac.name if ac else cid,
                "annual_income": 0,
                "currency": r["currency"],
                "assets": [],
            }
        class_totals[cid]["annual_income"] += r["annual_income"]
        class_totals[cid]["annual_income"] = round(class_totals[cid]["annual_income"], 2)
        class_totals[cid]["assets"].append(r)

    return {
        "dividends": list(class_totals.values()),
        "total_annual_income": round(sum(ct["annual_income"] for ct in class_totals.values()), 2),
    }
```

- [ ] **Step 2: Clean up unused imports**

Remove from top of file: `concurrent.futures` imports (`ThreadPoolExecutor`, `as_completed`). **Keep `time`** (used by `_fetch_exchange_rate`). Keep `date` (from datetime), `func` (from sqlalchemy), `httpx`.

- [ ] **Step 3: Run full test suite**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/portfolio.py
git commit -m "refactor: unified dividend query from DB for both US and BR stocks"
```

---

### Task 7: Update fundamentals router + remove Finnhub dead methods

**Files:**
- Modify: `backend/app/routers/fundamentals.py:34-51,61-77`
- Modify: `backend/app/providers/finnhub.py:58-174`

- [ ] **Step 1: Update `_refresh_score()` in `routers/fundamentals.py`**

Replace the full `_refresh_score` function (lines 34-58):

```python
def _refresh_score(symbol: str, db: Session) -> None:
    from app.providers.yfinance import YFinanceProvider
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    yfinance = YFinanceProvider()
    brapi = BrapiProvider(api_key=settings.brapi_api_key)
    dados = DadosDeMercadoProvider()

    country = "BR" if symbol.endswith(".SA") else "US"

    scheduler = FundamentalsScoreScheduler(
        yfinance_provider=yfinance,
        brapi_provider=brapi,
        dados_provider=dados,
        delay=0,
    )

    raw = scheduler._fetch_fundamentals(symbol, country)
    from app.services.fundamentals_scorer import score_fundamentals
    result = score_fundamentals(raw)
    raw_data = raw.get("raw_data")
    scheduler._upsert_score(db, symbol, result, raw_data)
    db.commit()
```

- [ ] **Step 2: Update `refresh_all_scores()` in `routers/fundamentals.py`**

Replace the provider instantiation block (lines 67-77):

```python
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.yfinance import YFinanceProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    scheduler = FundamentalsScoreScheduler(
        yfinance_provider=YFinanceProvider(),
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
        dados_provider=DadosDeMercadoProvider(),
        delay=1.0,
    )
```

Remove the `from app.providers.finnhub import FinnhubProvider` import (line 69 in original).

- [ ] **Step 2: Remove dead Finnhub methods**

In `providers/finnhub.py`: delete `get_dividend_metric()` (lines 58-71), `get_dividends_for_year()` (lines 73-99), `get_fundamentals()` (lines 101-174).

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_routers/test_fundamentals.py tests/test_providers/test_finnhub.py -v`
Expected: PASS (if Finnhub tests reference removed methods, those tests should be removed too)

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/fundamentals.py backend/app/providers/finnhub.py
git commit -m "refactor: use YFinanceProvider in fundamentals router, remove dead Finnhub methods"
```

---

### Task 8: Wire everything in main.py + config

**Files:**
- Modify: `backend/app/main.py:36-72`
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add `dividend_us_delay` to config**

In `config.py`, add after `dividend_scraper_delay` (line 17):
```python
    dividend_us_delay: float = 1.0
```

- [ ] **Step 2: Update `_run_dividend_scrape()` in main.py**

```python
def _run_dividend_scrape():
    from app.database import SessionLocal
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.yfinance import YFinanceProvider
    from app.services.dividend_scraper_scheduler import DividendScheduler

    scheduler = DividendScheduler(
        dados_provider=DadosDeMercadoProvider(),
        yfinance_provider=YFinanceProvider(),
        br_delay=settings.dividend_scraper_delay,
        us_delay=settings.dividend_us_delay,
    )

    db = SessionLocal()
    try:
        scheduler.scrape_all(db)
    except Exception:
        logger.exception("Scheduled dividend scrape failed")
    finally:
        db.close()
```

- [ ] **Step 3: Update `_run_fundamentals_score()` in main.py**

```python
def _run_fundamentals_score():
    from app.database import SessionLocal
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.yfinance import YFinanceProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    scheduler = FundamentalsScoreScheduler(
        yfinance_provider=YFinanceProvider(),
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
        dados_provider=DadosDeMercadoProvider(),
    )

    db = SessionLocal()
    try:
        scheduler.score_all(db)
    except Exception:
        logger.exception("Scheduled fundamentals scoring failed")
    finally:
        db.close()
```

- [ ] **Step 4: Run full test suite**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/config.py
git commit -m "feat: wire YFinanceProvider into dividend and fundamentals schedulers"
```

---

### Task 9: Clean up Finnhub test files for removed methods

**Files:**
- Modify: `backend/tests/test_providers/test_finnhub.py`
- Modify: `backend/tests/test_providers/test_finnhub_fundamentals.py`

- [ ] **Step 1: Remove tests for deleted Finnhub methods**

Delete `test_finnhub_fundamentals.py` entirely (fundamentals now tested via `test_yfinance.py`).

Note: `test_finnhub.py` only has tests for `search`, `get_quote`, `get_history` — no changes needed there.

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest tests/test_providers/ -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_providers/
git commit -m "chore: remove tests for deleted Finnhub dividend/fundamentals methods"
```

---

### Task 10: Final integration verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && pytest -v`
Expected: All PASS, no warnings about missing imports.

- [ ] **Step 2: Verify app starts**

Run: `cd backend && python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify no remaining references to removed Finnhub methods**

Run: `cd backend && grep -r "get_dividend_metric\|get_dividends_for_year\|finnhub.*get_fundamentals" app/ --include="*.py"`
Expected: No output (no remaining references).

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "chore: final cleanup for yfinance integration"
```
