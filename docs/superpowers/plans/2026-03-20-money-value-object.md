# Money Value Object Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all float-based monetary values with a `Money` value object backed by `Decimal` and a `Currency` enum, ensuring currency safety and precision across the entire stack.

**Architecture:** A frozen `Money` dataclass + `Currency` enum in `backend/app/money.py` serve as the domain primitive. Models store `Numeric` + `String` columns; conversion to/from `Money` happens at service boundaries. API responses use nested `{amount, currency}` objects. Frontend gets a matching `Money` TypeScript interface.

**Tech Stack:** Python `decimal.Decimal`, SQLAlchemy `Numeric(19,8,asdecimal=True)`, Pydantic v2 custom serializers, TypeScript interfaces.

**Spec:** `docs/superpowers/specs/2026-03-20-money-value-object-design.md`

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/money.py` | **NEW** — `Currency` enum, `Money` dataclass, `CurrencyMismatchError` |
| `backend/tests/test_money.py` | **NEW** — Unit tests for Money + Currency |
| `backend/app/models/transaction.py` | Modify Float→Numeric columns |
| `backend/app/models/market_quote.py` | Modify Float→Numeric columns |
| `backend/app/models/dividend_history.py` | Modify Float→Numeric, add currency column |
| `backend/app/providers/common.py` | Modify `DividendRecord.value` float→Decimal |
| `backend/app/providers/finnhub.py` | Return Money from `get_quote`, Decimal in history |
| `backend/app/providers/brapi.py` | Return Money from `get_quote`/`get_dividend_data`, Decimal in history |
| `backend/app/providers/dados_de_mercado.py` | Add `_parse_monetary_value()→Decimal` |
| `backend/app/providers/yfinance.py` | DividendRecord with Decimal value |
| `backend/app/services/market_data.py` | Cache Money objects, return Money from quotes |
| `backend/app/services/market_data_scheduler.py` | Extract Money values before writing to DB |
| `backend/app/services/portfolio.py` | Money arithmetic for holdings |
| `backend/app/services/recommendation.py` | Money arithmetic for asset values |
| `backend/app/services/dividend_scraper_scheduler.py` | Set currency on DividendHistory records |
| `backend/app/schemas/transaction.py` | MoneyResponse/MoneyInput types |
| `backend/app/routers/portfolio.py` | Serialize Money in responses |
| `backend/app/routers/stocks.py` | Serialize Money in responses |
| `backend/app/routers/crypto.py` | Serialize Money in responses |
| `backend/app/routers/dividends.py` | Serialize Money in responses |
| `backend/app/routers/transactions.py` | Deserialize MoneyInput |
| `backend/scripts/migrate_to_decimal.py` | **NEW** — One-time migration script |
| `frontend/src/types/index.ts` | Money interface, update Holding/Transaction/etc |
| `frontend/src/components/HoldingsTable.tsx` | Update formatCurrency for Money |
| `frontend/src/components/DividendHistoryModal.tsx` | Update formatCurrency for Money |
| `frontend/src/components/TransactionForm.tsx` | Money input handling |
| `frontend/src/utils/money.ts` | **NEW** — `formatMoney()`, `moneyToNumber()` helpers |
| `frontend/src/hooks/usePortfolio.ts` | Money-aware aggregation |
| `frontend/src/hooks/useTransactions.ts` | Send MoneyInput payloads |
| `frontend/src/pages/Dashboard.tsx` | Money type for dividend data |
| `frontend/src/pages/AssetClassHoldings.tsx` | Money-aware value display |

---

### Task 1: Currency Enum and Money Value Object

**Files:**
- Create: `backend/app/money.py`
- Test: `backend/tests/test_money.py`

- [ ] **Step 1: Write tests for Currency enum**

```python
# backend/tests/test_money.py
from decimal import Decimal
import pytest
from app.money import Currency, Money, CurrencyMismatchError


class TestCurrency:
    def test_usd_properties(self):
        assert Currency.USD.code == "USD"
        assert Currency.USD.symbol == "$"
        assert Currency.USD.symbol_position == "before"
        assert Currency.USD.thousands_sep == ","
        assert Currency.USD.decimal_sep == "."

    def test_brl_properties(self):
        assert Currency.BRL.code == "BRL"
        assert Currency.BRL.symbol == "R$"

    def test_eur_properties(self):
        assert Currency.EUR.code == "EUR"
        assert Currency.EUR.symbol == "€"

    def test_from_code(self):
        assert Currency.from_code("USD") is Currency.USD
        assert Currency.from_code("BRL") is Currency.BRL
        assert Currency.from_code("EUR") is Currency.EUR

    def test_from_code_invalid(self):
        with pytest.raises(ValueError, match="Unknown currency code"):
            Currency.from_code("XYZ")
```

- [ ] **Step 2: Write tests for Money construction and display**

```python
# append to backend/tests/test_money.py
class TestMoneyConstruction:
    def test_create(self):
        m = Money(Decimal("10.50"), Currency.USD)
        assert m.amount == Decimal("10.50")
        assert m.currency is Currency.USD

    def test_from_db(self):
        m = Money.from_db(Decimal("10.50"), "USD")
        assert m.amount == Decimal("10.50")
        assert m.currency is Currency.USD

    def test_to_db(self):
        m = Money(Decimal("10.50"), Currency.USD)
        amount, code = m.to_db()
        assert amount == Decimal("10.50")
        assert code == "USD"

    def test_zero(self):
        m = Money.zero(Currency.USD)
        assert m.amount == Decimal("0")
        assert m.currency is Currency.USD


class TestMoneyDisplay:
    def test_usd_display(self):
        m = Money(Decimal("1234.56"), Currency.USD)
        assert m.display() == "$1,234.56"

    def test_brl_display(self):
        m = Money(Decimal("1234.56"), Currency.BRL)
        assert m.display() == "R$ 1.234,56"

    def test_eur_display(self):
        m = Money(Decimal("1234.56"), Currency.EUR)
        assert m.display() == "€1.234,56"

    def test_large_amount(self):
        m = Money(Decimal("1234567.89"), Currency.USD)
        assert m.display() == "$1,234,567.89"

    def test_small_amount(self):
        m = Money(Decimal("0.50"), Currency.USD)
        assert m.display() == "$0.50"

    def test_negative_amount(self):
        m = Money(Decimal("-100.00"), Currency.USD)
        assert m.display() == "-$100.00"

    def test_str_delegates_to_display(self):
        m = Money(Decimal("10.50"), Currency.USD)
        assert str(m) == m.display()

    def test_repr(self):
        m = Money(Decimal("10.50"), Currency.USD)
        assert repr(m) == "Money(10.50, USD)"
```

- [ ] **Step 3: Write tests for Money arithmetic**

```python
# append to backend/tests/test_money.py
class TestMoneyArithmetic:
    def test_add_same_currency(self):
        a = Money(Decimal("10.00"), Currency.USD)
        b = Money(Decimal("5.50"), Currency.USD)
        assert a + b == Money(Decimal("15.50"), Currency.USD)

    def test_add_different_currency_raises(self):
        a = Money(Decimal("10.00"), Currency.USD)
        b = Money(Decimal("5.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            a + b

    def test_sub(self):
        a = Money(Decimal("10.00"), Currency.USD)
        b = Money(Decimal("3.00"), Currency.USD)
        assert a - b == Money(Decimal("7.00"), Currency.USD)

    def test_mul_scalar_int(self):
        m = Money(Decimal("10.00"), Currency.USD)
        assert m * 3 == Money(Decimal("30.00"), Currency.USD)

    def test_mul_scalar_decimal(self):
        m = Money(Decimal("10.00"), Currency.USD)
        assert m * Decimal("1.5") == Money(Decimal("15.00"), Currency.USD)

    def test_rmul(self):
        m = Money(Decimal("10.00"), Currency.USD)
        assert 3 * m == Money(Decimal("30.00"), Currency.USD)

    def test_neg(self):
        m = Money(Decimal("10.00"), Currency.USD)
        assert -m == Money(Decimal("-10.00"), Currency.USD)

    def test_per_unit(self):
        m = Money(Decimal("100.00"), Currency.USD)
        assert m.per_unit(Decimal("3")) == Money(Decimal("100.00") / Decimal("3"), Currency.USD)

    def test_ratio_same_currency(self):
        a = Money(Decimal("50.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a.ratio(b) == Decimal("0.5")

    def test_ratio_different_currency_raises(self):
        a = Money(Decimal("50.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            a.ratio(b)


class TestMoneyComparison:
    def test_eq(self):
        a = Money(Decimal("10.00"), Currency.USD)
        b = Money(Decimal("10.00"), Currency.USD)
        assert a == b

    def test_lt(self):
        a = Money(Decimal("5.00"), Currency.USD)
        b = Money(Decimal("10.00"), Currency.USD)
        assert a < b

    def test_compare_different_currency_raises(self):
        a = Money(Decimal("10.00"), Currency.USD)
        b = Money(Decimal("10.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            a < b
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_money.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.money'`

- [ ] **Step 5: Implement Currency enum**

```python
# backend/app/money.py
from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal


class CurrencyMismatchError(ValueError):
    """Raised when arithmetic is attempted between different currencies."""
    pass


class Currency(enum.Enum):
    USD = ("USD", "$", "before", ",", ".", "")    # $1,234.56
    BRL = ("BRL", "R$", "before", ".", ",", " ")   # R$ 1.234,56
    EUR = ("EUR", "€", "before", ".", ",", "")      # €1.234,56

    def __init__(self, code: str, symbol: str, symbol_position: str, thousands_sep: str, decimal_sep: str, symbol_spacing: str):
        self.code = code
        self.symbol = symbol
        self.symbol_position = symbol_position
        self.thousands_sep = thousands_sep
        self.decimal_sep = decimal_sep
        self.symbol_spacing = symbol_spacing  # space between symbol and number (e.g., "R$ 1.234")

    @classmethod
    def from_code(cls, code: str) -> Currency:
        for member in cls:
            if member.code == code:
                return member
        raise ValueError(f"Unknown currency code: {code}")
```

- [ ] **Step 6: Implement Money dataclass**

```python
# append to backend/app/money.py

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    @classmethod
    def from_db(cls, amount: Decimal, currency_code: str) -> Money:
        return cls(amount=amount, currency=Currency.from_code(currency_code))

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        return cls(amount=Decimal("0"), currency=currency)

    def to_db(self) -> tuple[Decimal, str]:
        return self.amount, self.currency.code

    def _check_currency(self, other: Money) -> None:
        if self.currency is not other.currency:
            raise CurrencyMismatchError(
                f"Cannot operate on {self.currency.code} and {other.currency.code}"
            )

    def display(self) -> str:
        sign = "-" if self.amount < 0 else ""
        abs_amount = abs(self.amount)
        integer_part = int(abs_amount)
        fractional = abs_amount - integer_part
        frac_str = f"{fractional:.2f}"[1:]  # ".56"

        # Format integer part with thousands separator
        int_str = ""
        s = str(integer_part)
        for i, ch in enumerate(reversed(s)):
            if i > 0 and i % 3 == 0:
                int_str = self.currency.thousands_sep + int_str
            int_str = ch + int_str

        formatted = int_str + frac_str.replace(".", self.currency.decimal_sep)

        sp = self.currency.symbol_spacing
        if self.currency.symbol_position == "before":
            return f"{sign}{self.currency.symbol}{sp}{formatted}"
        return f"{sign}{formatted}{sp}{self.currency.symbol}"

    def __str__(self) -> str:
        return self.display()

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency.code})"

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int) -> Money:
        if isinstance(factor, Money):
            raise TypeError("Cannot multiply Money by Money")
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __rmul__(self, factor: Decimal | int) -> Money:
        return self.__mul__(factor)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def per_unit(self, quantity: Decimal | int) -> Money:
        return Money(self.amount / Decimal(str(quantity)), self.currency)

    def ratio(self, other: Money) -> Decimal:
        self._check_currency(other)
        return self.amount / other.amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency is other.currency

    def __lt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._check_currency(other)
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_money.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/money.py backend/tests/test_money.py
git commit -m "feat: add Currency enum and Money value object with arithmetic and display"
```

---

### Task 2: Update DividendRecord and Provider Common

**Files:**
- Modify: `backend/app/providers/common.py`
- Modify: `backend/tests/test_providers/test_dados_de_mercado.py`
- Modify: `backend/tests/test_providers/test_yfinance.py`

- [ ] **Step 1: Update DividendRecord to use Decimal**

```python
# backend/app/providers/common.py
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class DividendRecord:
    dividend_type: str
    value: Decimal
    record_date: date
    ex_date: date
    payment_date: date | None
```

- [ ] **Step 2: Update YFinanceProvider to create DividendRecord with Decimal**

In `backend/app/providers/yfinance.py`, change line 57:
```python
# Before:
value=round(float(amount), 6)
# After:
value=Decimal(str(amount)).quantize(Decimal("0.000001"))
```

Add `from decimal import Decimal` to imports.

- [ ] **Step 3: Update DadosDeMercadoProvider — add _parse_monetary_value**

In `backend/app/providers/dados_de_mercado.py`:

Add `from decimal import Decimal` to imports.

Add new function alongside `_parse_value`:
```python
def _parse_monetary_value(text: str) -> Decimal:
    """Parse a Brazilian-formatted monetary value string to Decimal."""
    raw = _parse_value(text)
    return Decimal(str(raw))
```

Update the DividendRecord creation (around line 348) to use `_parse_monetary_value` instead of `_parse_value` for the `value` field:
```python
value=_parse_monetary_value(cells[1].get_text(strip=True))
```

- [ ] **Step 4: Update tests that create DividendRecord with float values**

In test files that construct `DividendRecord`, change `value=1.5` to `value=Decimal("1.5")` etc. Search test files for `DividendRecord(` and update.

- [ ] **Step 5: Run provider tests**

Run: `cd backend && python -m pytest tests/test_providers/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/providers/common.py backend/app/providers/yfinance.py backend/app/providers/dados_de_mercado.py backend/tests/test_providers/
git commit -m "feat: update DividendRecord to use Decimal instead of float"
```

---

### Task 3: Update SQLAlchemy Models

**Files:**
- Modify: `backend/app/models/transaction.py:4,18-22`
- Modify: `backend/app/models/market_quote.py:2,14,16`
- Modify: `backend/app/models/dividend_history.py:4,19` (add currency column)
- Modify: `backend/tests/test_models/test_transaction.py`
- Modify: `backend/tests/test_models/test_market_quote.py`
- Modify: `backend/tests/test_models/test_dividend_history.py`

- [ ] **Step 1: Update Transaction model**

```python
# backend/app/models/transaction.py
from sqlalchemy import String, Float, Numeric, DateTime, Date, Enum, ForeignKey

# Change lines 18-22:
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)  # stays Float
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=True, default=None)
```

Add `from decimal import Decimal` to imports.

- [ ] **Step 2: Update MarketQuote model**

```python
# backend/app/models/market_quote.py
from sqlalchemy import String, Numeric, DateTime

    current_price: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    market_cap: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), default=0)
```

Add `from decimal import Decimal` to imports.

- [ ] **Step 3: Update DividendHistory model — add currency column**

```python
# backend/app/models/dividend_history.py
from sqlalchemy import String, Numeric, DateTime, Date, UniqueConstraint

    value: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
```

Add `from decimal import Decimal` to imports.

- [ ] **Step 4: Update model tests to use Decimal values**

In test files that create Transaction, MarketQuote, or DividendHistory objects, replace float literals with `Decimal("...")` for monetary fields.

- [ ] **Step 5: Run model tests**

Run: `cd backend && python -m pytest tests/test_models/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/transaction.py backend/app/models/market_quote.py backend/app/models/dividend_history.py backend/tests/test_models/
git commit -m "feat: update SQLAlchemy models to use Numeric for monetary fields"
```

---

### Task 4: Migration Script

**Files:**
- Create: `backend/scripts/migrate_to_decimal.py`

- [ ] **Step 1: Create migration script**

```python
# backend/scripts/migrate_to_decimal.py
"""
One-time migration: convert Float columns to Numeric (TEXT in SQLite)
and add currency column to dividend_history.

Usage: cd backend && python -m scripts.migrate_to_decimal
"""
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path


def migrate(db_path: str = "portfolio.db"):
    if not Path(db_path).exists():
        print(f"Database {db_path} not found, skipping migration (fresh DB will use new schema)")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if migration already applied (currency column exists on dividend_history)
    cur.execute("PRAGMA table_info(dividend_history)")
    columns = [row[1] for row in cur.fetchall()]
    if "currency" in columns:
        print("Migration already applied (dividend_history.currency exists)")
        conn.close()
        return

    print("Starting migration...")

    # 1. Convert float values in transactions
    cur.execute("SELECT id, unit_price, total_value, tax_amount FROM transactions")
    rows = cur.fetchall()
    for row_id, unit_price, total_value, tax_amount in rows:
        cur.execute(
            "UPDATE transactions SET unit_price=?, total_value=?, tax_amount=? WHERE id=?",
            (
                str(Decimal(str(unit_price))) if unit_price is not None else None,
                str(Decimal(str(total_value))) if total_value is not None else None,
                str(Decimal(str(tax_amount))) if tax_amount is not None else None,
                row_id,
            ),
        )
    print(f"  Migrated {len(rows)} transactions")

    # 2. Convert float values in market_quotes
    cur.execute("SELECT symbol, current_price, market_cap FROM market_quotes")
    rows = cur.fetchall()
    for symbol, price, mcap in rows:
        cur.execute(
            "UPDATE market_quotes SET current_price=?, market_cap=? WHERE symbol=?",
            (str(Decimal(str(price))), str(Decimal(str(mcap))), symbol),
        )
    print(f"  Migrated {len(rows)} market quotes")

    # 3. Add currency column to dividend_history and populate it
    cur.execute("ALTER TABLE dividend_history ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")

    # Infer currency from asset class country via transactions
    cur.execute("""
        UPDATE dividend_history SET currency = 'BRL'
        WHERE symbol IN (
            SELECT DISTINCT t.asset_symbol
            FROM transactions t
            JOIN asset_classes ac ON t.asset_class_id = ac.id
            WHERE ac.country = 'BR'
        )
    """)

    # Convert dividend float values
    cur.execute("SELECT id, value FROM dividend_history")
    rows = cur.fetchall()
    for row_id, value in rows:
        cur.execute(
            "UPDATE dividend_history SET value=? WHERE id=?",
            (str(Decimal(str(value))), row_id),
        )
    print(f"  Migrated {len(rows)} dividend history records")

    conn.commit()
    conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "portfolio.db"
    migrate(db_path)
```

- [ ] **Step 2: Create `backend/scripts/__init__.py`**

```python
# empty file
```

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/
git commit -m "feat: add migration script for float-to-decimal conversion"
```

---

### Task 5: Update Dividend Scraper Scheduler

**Files:**
- Modify: `backend/app/services/dividend_scraper_scheduler.py`
- Modify: `backend/tests/test_services/test_dividend_scraper_scheduler.py`

- [ ] **Step 1: Update scheduler to set currency on DividendHistory**

When creating `DividendHistory` records from `DividendRecord`, the scheduler needs to set the `currency` field. The currency is known from the symbol context (BR symbols → BRL, US symbols → USD).

Find where `DividendHistory` objects are created and add `currency=` parameter. Use `"BRL"` for symbols ending in `.SA` or symbols processed through the BR provider, `"USD"` for US symbols.

- [ ] **Step 2: Ensure DividendRecord.value (now Decimal) is properly stored**

The `value` field on `DividendHistory` is now `Numeric` and `DividendRecord.value` is now `Decimal` — these should be compatible without conversion.

- [ ] **Step 3: Update tests**

In `backend/tests/test_services/test_dividend_scraper_scheduler.py`, update any `DividendRecord` construction to use `Decimal` values and verify that created `DividendHistory` records have the correct `currency` field.

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_dividend_scraper_scheduler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dividend_scraper_scheduler.py backend/tests/test_services/test_dividend_scraper_scheduler.py
git commit -m "feat: dividend scraper sets currency on DividendHistory records"
```

---

### Task 6: Update Providers to Return Money

**Files:**
- Modify: `backend/app/providers/finnhub.py:50-56,90-97`
- Modify: `backend/app/providers/brapi.py:37-43,63-87,148-155`
- Modify: `backend/app/services/market_data.py:55-61,77-79,121-127,140-145`
- Modify: `backend/tests/test_providers/test_finnhub.py`
- Modify: `backend/tests/test_providers/test_brapi.py`

- [ ] **Step 1: Update FinnhubProvider.get_quote to return Money**

```python
# backend/app/providers/finnhub.py
# Add imports:
from decimal import Decimal
from app.money import Money, Currency

# Change get_quote return (lines 50-56):
        currency = Currency.from_code(profile_data.get("currency", "USD"))
        return {
            "symbol": symbol,
            "name": profile_data.get("name", ""),
            "current_price": Money(Decimal(str(quote_data.get("c", 0))), currency),
            "currency": currency,
            "market_cap": Money(
                Decimal(str(profile_data.get("marketCapitalization", 0))) * Decimal("1000000"),
                currency,
            ),
        }
```

- [ ] **Step 2: Update FinnhubProvider.get_history to return Decimal close prices**

```python
# Change get_history return (lines 90-97):
        return [
            {
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": Decimal(str(close)),
                "volume": int(volume),
            }
            for ts, close, volume in zip(data["t"], data["c"], data["v"])
        ]
```

- [ ] **Step 3: Update BrapiProvider.get_quote to return Money**

```python
# backend/app/providers/brapi.py
# Add imports:
from decimal import Decimal
from app.money import Money, Currency

# Change get_quote return (lines 37-43):
        currency = Currency.from_code(data.get("currency", "BRL"))
        return {
            "symbol": symbol,
            "name": data.get("shortName", ""),
            "current_price": Money(Decimal(str(data.get("regularMarketPrice", 0))), currency),
            "currency": currency,
            "market_cap": Money(Decimal(str(data.get("marketCap", 0))), currency),
        }
```

- [ ] **Step 4: Update BrapiProvider.get_dividend_data to use Decimal**

```python
# Change get_dividend_data (lines 63-87):
        price = Decimal(str(data.get("regularMarketPrice", 0)))
        # ...
        annual_dps = Decimal("0")
        # in loop:
                    annual_dps += Decimal(str(d.get("rate", 0)))
        # ...
        dividend_yield = (annual_dps / price * 100) if price > 0 and annual_dps > 0 else Decimal("0")

        return {
            "symbol": symbol,
            "dividend_per_share_annual": annual_dps,
            "dividend_yield_annual": dividend_yield,
        }
```

- [ ] **Step 5: Update BrapiProvider.get_history to return Decimal close prices**

```python
# Change get_history return (lines 148-155):
        return [
            {
                "date": datetime.fromtimestamp(item["date"], tz=timezone.utc).strftime("%Y-%m-%d"),
                "close": Decimal(str(item["close"])),
                "volume": int(item.get("volume", 0)),
            }
            for item in history
        ]
```

- [ ] **Step 6: Update MarketDataService to handle Money objects**

In `backend/app/services/market_data.py`:

Add imports:
```python
from decimal import Decimal
from app.money import Money, Currency
```

Update `get_stock_quote` (lines 55-61) — when reading from DB, construct Money:
```python
                result = {
                    "symbol": stored.symbol,
                    "name": stored.name,
                    "current_price": Money.from_db(stored.current_price, stored.currency),
                    "currency": Currency.from_code(stored.currency),
                    "market_cap": Money.from_db(stored.market_cap, stored.currency),
                }
```

Update DB write (lines 76-80) — extract from Money:
```python
            quote.name = result["name"]
            price_amount, price_currency = result["current_price"].to_db()
            quote.current_price = price_amount
            quote.currency = price_currency
            mcap_amount, _ = result["market_cap"].to_db()
            quote.market_cap = mcap_amount
```

Update `get_quote_safe` return type (line 98) from `float | None` to `Money | None`.

Update `get_crypto_quote` (lines 121-127):
```python
        result = {
            "coin_id": coin_id,
            "current_price": Money(Decimal(str(data["usd"])), Currency.USD),
            "currency": Currency.USD,
            "market_cap": Money(Decimal(str(data["usd_market_cap"])), Currency.USD),
            "change_24h": data["usd_24h_change"],  # stays float (percentage)
        }
```

Update `get_crypto_history` (lines 140-145):
```python
        result = [
            {
                "date": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "price": Decimal(str(price)),
            }
            for ts, price in data["prices"]
        ]
```

- [ ] **Step 7: Update MarketDataScheduler**

In `backend/app/services/market_data_scheduler.py`, the scheduler writes `quote_data["current_price"]` directly to `MarketQuote.current_price`. After this task, `quote_data["current_price"]` is a `Money` object. Extract the Decimal before writing:

```python
# Around line 43:
price_amount, price_currency = quote_data["current_price"].to_db()
quote.current_price = price_amount
quote.currency = price_currency
mcap_amount, _ = quote_data["market_cap"].to_db()
quote.market_cap = mcap_amount
```

- [ ] **Step 8: Update provider tests**

Update mock return values and assertions in:
- `backend/tests/test_providers/test_finnhub.py`
- `backend/tests/test_providers/test_brapi.py`
- `backend/tests/test_services/test_market_data.py`
- `backend/tests/test_services/test_market_data_scheduler.py`

Change assertions from `== 150.0` to checking Money objects: `assert result["current_price"].amount == Decimal("150")`.

- [ ] **Step 9: Run tests**

Run: `cd backend && python -m pytest tests/test_providers/ tests/test_services/test_market_data.py tests/test_services/test_market_data_scheduler.py -v`
Expected: All tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/providers/ backend/app/services/market_data.py backend/app/services/market_data_scheduler.py backend/tests/test_providers/ backend/tests/test_services/test_market_data.py backend/tests/test_services/test_market_data_scheduler.py
git commit -m "feat: providers and market data service return Money objects"
```

---

### Task 7: Update PortfolioService

**Files:**
- Modify: `backend/app/services/portfolio.py`
- Modify: `backend/tests/test_services/test_portfolio.py`
- Modify: `backend/tests/test_services/test_portfolio_splits.py`

- [ ] **Step 1: Update get_holdings to return Money values**

In `backend/app/services/portfolio.py`, add imports:
```python
from decimal import Decimal
from app.money import Money, Currency
```

Update value-based holdings (lines 56-90):
```python
            if buy_qty is None:
                buy_value_raw = buy_agg.total_value or Decimal("0")
                sell_value_raw = (...) or Decimal("0")
                net_value_raw = buy_value_raw - sell_value_raw
                if net_value_raw <= 0:
                    continue
                tx_currency = (...)
                currency_code = tx_currency[0] if tx_currency else "BRL"
                currency = Currency.from_code(currency_code)
                holdings.append({
                    "symbol": symbol,
                    "asset_class_id": asset_class_id,
                    "quantity": None,
                    "avg_price": None,
                    "total_cost": Money(net_value_raw, currency),
                    "currency": currency,
                })
```

Update quantity-based fast path (lines 98-116):
```python
                if not symbol_splits:
                    buy_qty = buy_qty or 0
                    buy_value_raw = buy_agg.total_value or Decimal("0")
                    # ...
                    net_qty = buy_qty - sell_qty
                    if net_qty <= 0:
                        continue
                    avg_price_raw = buy_value_raw / Decimal(str(buy_qty)) if buy_qty > 0 else Decimal("0")
                    total_cost_raw = avg_price_raw * Decimal(str(net_qty))
```

Update quantity-based slow path (splits, lines 129-154) similarly.

Wrap final values in Money:
```python
                tx_currency = (...)
                currency_code = tx_currency[0] if tx_currency else "BRL"
                currency = Currency.from_code(currency_code)
                holdings.append({
                    "symbol": symbol,
                    "asset_class_id": asset_class_id,
                    "quantity": net_qty,
                    "avg_price": Money(avg_price_raw, currency),
                    "total_cost": Money(total_cost_raw, currency),
                    "currency": currency,
                })
```

- [ ] **Step 2: Update enrich_holdings for Money**

In `enrich_holdings` (lines 228-316):

Update total_value calculation:
```python
        total_value = Decimal("0")
        for h in qty_holdings:
            price = prices.get(h["symbol"])  # Now Money | None
            if price is not None:
                total_value += price.amount * Decimal(str(h["quantity"]))
        for h in val_holdings:
            total_value += h["total_cost"].amount
```

Update enrichment for quantity-based holdings:
```python
                if price is not None:
                    current_value = price * Decimal(str(h["quantity"]))  # Money * scalar
                    gain_loss = (price - h["avg_price"]) * Decimal(str(h["quantity"]))  # Money arithmetic
                    actual_weight = float(current_value.amount / total_value * 100) if total_value > 0 else 0.0
```

Update enrichment for value-based holdings:
```python
                current_value = h["total_cost"]  # already Money
                actual_weight = float(current_value.amount / total_value * 100) if total_value > 0 else 0.0
```

- [ ] **Step 3: Update get_allocation for Money**

The `get_allocation` method (lines 180-226) passes through `total_cost` which is now a Money object — this should work without changes since it's just passed in dicts. Verify.

- [ ] **Step 4: Update portfolio tests**

In `backend/tests/test_services/test_portfolio.py` and `test_portfolio_splits.py`:
- Transaction fixtures use `Decimal` for `total_value`, `unit_price`, `tax_amount`
- Assertions check Money objects: `assert h["total_cost"].amount == Decimal("...")`
- Assertions check currency: `assert h["total_cost"].currency is Currency.USD`

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_portfolio.py tests/test_services/test_portfolio_splits.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/portfolio.py backend/tests/test_services/test_portfolio.py backend/tests/test_services/test_portfolio_splits.py
git commit -m "feat: PortfolioService uses Money for holdings calculations"
```

---

### Task 8: Update RecommendationService

**Files:**
- Modify: `backend/app/services/recommendation.py:17,60-68,86`
- Modify: `backend/tests/test_services/test_recommendation.py`

- [ ] **Step 1: Update RecommendationService for Money**

In `backend/app/services/recommendation.py`:

Add imports:
```python
from decimal import Decimal
```

Update `_get_current_price` return type annotation to `Money`.

Update `get_recommendations` (lines 59-68):
```python
        asset_values: dict[str, Decimal] = {}
        for h in holdings:
            ac = class_map.get(h["asset_class_id"])
            class_name = ac.name if ac else ""
            country = ac.country if ac else "US"
            if h["quantity"] is None:
                # Value-based holding: use total_cost
                asset_values[h["symbol"]] = h["total_cost"].amount
                continue
            price = self._get_current_price(h["symbol"], class_name, country=country, db=self.db)
            asset_values[h["symbol"]] = price.amount * Decimal(str(h["quantity"]))

        total_value = sum(asset_values.values())
```

Update weight calculation (line 86):
```python
            actual_weight = float(asset_values.get(h["symbol"], Decimal("0")) / total_value * 100)
```

- [ ] **Step 2: Update recommendation tests**

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_recommendation.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/recommendation.py backend/tests/test_services/test_recommendation.py
git commit -m "feat: RecommendationService uses Money/Decimal for asset values"
```

---

### Task 9: Update Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas/transaction.py`
- Create or modify: `backend/app/schemas/money.py` (or add MoneyResponse/MoneyInput to transaction.py)

- [ ] **Step 1: Create MoneyResponse and MoneyInput schemas**

```python
# backend/app/schemas/money.py
from pydantic import BaseModel, field_validator
from decimal import Decimal


class MoneyResponse(BaseModel):
    amount: str
    currency: str


class MoneyInput(BaseModel):
    amount: str
    currency: str

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        Decimal(v)  # raises InvalidOperation if not a valid decimal string
        return v
```

- [ ] **Step 2: Update TransactionCreate schema**

```python
# backend/app/schemas/transaction.py
from app.schemas.money import MoneyInput

class TransactionCreate(BaseModel):
    asset_class_id: str
    asset_symbol: str
    type: Literal["buy", "sell", "dividend"]
    quantity: Optional[float] = None
    unit_price: Optional[MoneyInput] = None
    total_value: MoneyInput
    currency: Optional[str] = None  # DEPRECATED: kept for backward compat, currency comes from MoneyInput now
    tax_amount: Optional[MoneyInput] = None
    date: dt.date
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_field_consistency(self):
        fields = [self.quantity, self.unit_price]
        all_set = all(f is not None for f in fields)
        none_set = all(f is None for f in fields)
        if not (all_set or none_set):
            raise ValueError("quantity and unit_price must be all provided or all None")
        return self
```

- [ ] **Step 3: Update TransactionUpdate and TransactionResponse schemas**

```python
class TransactionUpdate(BaseModel):
    quantity: Optional[float] = None
    unit_price: Optional[MoneyInput] = None
    total_value: Optional[MoneyInput] = None
    tax_amount: Optional[MoneyInput] = None
    date: Optional[dt.date] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    asset_class_id: str
    asset_symbol: str
    type: str
    quantity: float | None
    unit_price: MoneyResponse | None
    total_value: MoneyResponse
    tax_amount: MoneyResponse | None
    date: dt.date
    notes: Optional[str]
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
```

Note: `from_attributes` won't auto-convert Decimal+String columns to MoneyResponse. A custom serializer or manual construction in the router is needed.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add MoneyResponse/MoneyInput schemas, update transaction schemas"
```

---

### Task 10: Update Routers

**Files:**
- Modify: `backend/app/routers/transactions.py`
- Modify: `backend/app/routers/portfolio.py`
- Modify: `backend/app/routers/stocks.py`
- Modify: `backend/app/routers/crypto.py`
- Modify: `backend/app/routers/dividends.py`
- Modify: associated test files

- [ ] **Step 1: Update transactions router**

In `backend/app/routers/transactions.py`, update the create endpoint to extract Money values from MoneyInput:

```python
from decimal import Decimal
from app.money import Money, Currency

# In create handler:
    currency = Currency.from_code(data.total_value.currency)
    transaction = Transaction(
        # ...
        unit_price=Decimal(data.unit_price.amount) if data.unit_price else None,
        total_value=Decimal(data.total_value.amount),
        currency=data.total_value.currency,
        tax_amount=Decimal(data.tax_amount.amount) if data.tax_amount else None,
        # ...
    )
```

Update the **update handler** — the current pattern uses `model_dump`/`setattr` which won't work with MoneyInput objects. Replace with explicit field extraction:
```python
# In update handler (around line 76):
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in ("unit_price", "total_value", "tax_amount") and value is not None:
            setattr(tx, field, Decimal(value["amount"]))
            if field == "total_value":
                tx.currency = value["currency"]
        else:
            setattr(tx, field, value)
```

Update response construction to build MoneyResponse:
```python
from app.schemas.money import MoneyResponse

def _tx_to_response(tx: Transaction) -> dict:
    return {
        # ... other fields ...
        "unit_price": MoneyResponse(amount=str(tx.unit_price), currency=tx.currency) if tx.unit_price is not None else None,
        "total_value": MoneyResponse(amount=str(tx.total_value), currency=tx.currency),
        "tax_amount": MoneyResponse(amount=str(tx.tax_amount), currency=tx.currency) if tx.tax_amount is not None else None,
        # ...
    }
```

- [ ] **Step 2: Update portfolio router**

In `backend/app/routers/portfolio.py`:

Add helper to serialize Money:
```python
def _money_to_dict(m: Money | None) -> dict | None:
    if m is None:
        return None
    return {"amount": str(m.amount), "currency": m.currency.code}
```

Update `/summary` — enrich already returns Money objects, serialize them:
```python
    enriched_serialized = []
    for h in enriched:
        enriched_serialized.append({
            "symbol": h["symbol"],
            "asset_class_id": h["asset_class_id"],
            "quantity": h["quantity"],
            "avg_price": _money_to_dict(h["avg_price"]),
            "total_cost": _money_to_dict(h["total_cost"]),
            "current_price": _money_to_dict(h.get("current_price")),
            "current_value": _money_to_dict(h.get("current_value")),
            "gain_loss": _money_to_dict(h.get("gain_loss")),
            "target_weight": h.get("target_weight"),
            "actual_weight": h.get("actual_weight"),
        })
    return {"holdings": enriched_serialized}
```

Update `/performance` — serialize Money:
```python
    total_cost = sum((h["total_cost"].amount for h in holdings), Decimal("0"))
    holdings_serialized = [
        {**h, "total_cost": _money_to_dict(h["total_cost"]), "avg_price": _money_to_dict(h.get("avg_price"))}
        for h in holdings
    ]
    return {"holdings": holdings_serialized, "total_cost": {"amount": str(total_cost), "currency": "mixed"}}
```

Update `/dividends` — dividend_per_share and annual_income as Money:
```python
        annual_income = Money(dps * Decimal(str(holding["quantity"])), Currency.from_code(currency))
        results.append({
            "symbol": symbol,
            "asset_class_id": holding["asset_class_id"],
            "quantity": holding["quantity"],
            "dividend_per_share": {"amount": str(dps), "currency": currency},
            "dividend_yield": 0,
            "annual_income": _money_to_dict(annual_income),
        })
```

Update class aggregation and total to serialize as Money dicts.

Update `/allocation` — `total_cost` is now a Money object, serialize it:
```python
    for ac_data in allocation:
        for asset in ac_data["assets"]:
            asset["total_cost"] = _money_to_dict(asset["total_cost"])
    return {"allocation": allocation}
```

- [ ] **Step 3: Update stocks router**

In `backend/app/routers/stocks.py`, quotes now contain Money objects:
```python
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": _money_to_dict(quote["current_price"]),
        "currency": quote["currency"].code,
        "market_cap": _money_to_dict(quote["market_cap"]),
    }
```

For history endpoints, `close` is now Decimal:
```python
    return [{"date": h["date"], "price": {"amount": str(h["close"]), "currency": currency_code}} for h in history]
```

Note: currency_code must be inferred from the country parameter. Add a helper or pass it through.

- [ ] **Step 4: Update crypto router**

In `backend/app/routers/crypto.py`, the quote response returns `quote["current_price"]` and `quote["market_cap"]` which are now Money objects. Import `_money_to_dict` (or define locally) and serialize:

```python
from app.money import Money

def _money_to_dict(m: Money | None) -> dict | None:
    if m is None:
        return None
    return {"amount": str(m.amount), "currency": m.currency.code}

# In quote endpoint (around line 20-22):
    return {
        "coin_id": coin_id,
        "price": _money_to_dict(quote["current_price"]),
        "currency": quote["currency"].code if hasattr(quote["currency"], "code") else quote["currency"],
        "market_cap": _money_to_dict(quote["market_cap"]),
        "change_24h": quote.get("change_24h"),
    }
```

For history endpoint, `price` is now Decimal:
```python
    return [{"date": h["date"], "price": {"amount": str(h["price"]), "currency": "USD"}} for h in history]
```

- [ ] **Step 5: Update dividends router**

In `backend/app/routers/dividends.py`, line 108-110:
```python
        value = r.value  # now Decimal
        qty = Decimal(str(qty_map.get(r.symbol, 0)))
        total = value * qty
        currency = r.currency  # now available from model
        {
            "symbol": r.symbol,
            "dividend_type": r.dividend_type,
            "value": {"amount": str(value), "currency": currency},
            "quantity": float(qty),
            "total": {"amount": str(total.quantize(Decimal("0.01"))), "currency": currency},
            "ex_date": r.ex_date.isoformat(),
            "payment_date": r.payment_date.isoformat() if r.payment_date else None,
        }
```

- [ ] **Step 6: Update router tests**

Update all router test files to expect nested Money objects in responses:
- `backend/tests/test_routers/test_transactions.py`
- `backend/tests/test_routers/test_portfolio.py`
- `backend/tests/test_routers/test_stocks.py`
- `backend/tests/test_routers/test_crypto.py`
- `backend/tests/test_e2e.py`
- `backend/tests/test_portfolio_enriched.py`

For example:
```python
# Before:
assert response.json()["price"] == 150.0
# After:
assert response.json()["price"]["amount"] == "150"
assert response.json()["price"]["currency"] == "USD"
```

For transaction create/update tests, send MoneyInput format:
```python
# Before:
{"total_value": 100.0, "currency": "USD", ...}
# After:
{"total_value": {"amount": "100.0", "currency": "USD"}, ...}
```

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/ backend/tests/test_routers/ backend/tests/test_e2e.py backend/tests/test_portfolio_enriched.py
git commit -m "feat: routers serialize Money as nested {amount, currency} objects"
```

---

### Task 11: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add Money interface and update types**

```typescript
// frontend/src/types/index.ts

// Add at top:
export interface Money {
  amount: string;
  currency: string;
}

// Update Transaction:
export interface Transaction {
  id: string;
  user_id: string;
  asset_class_id: string;
  asset_symbol: string;
  type: "buy" | "sell" | "dividend";
  quantity: number | null;
  unit_price: Money | null;
  total_value: Money;
  tax_amount: Money | null;
  date: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Update Holding:
export interface Holding {
  symbol: string;
  asset_class_id: string;
  quantity: number | null;
  avg_price: Money | null;
  total_cost: Money;
  current_price?: Money;
  current_value?: Money;
  gain_loss?: Money;
  target_weight?: number;
  actual_weight?: number;
}

// Update DividendHistoryItem:
export interface DividendHistoryItem {
  symbol: string;
  dividend_type: string;
  value: Money;
  quantity: number;
  total: Money;
  ex_date: string;
  payment_date: string | null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add Money TypeScript interface, update types for nested money"
```

---

### Task 12: Update Frontend Components

**Files:**
- Create: `frontend/src/utils/money.ts`
- Modify: `frontend/src/components/HoldingsTable.tsx`
- Modify: `frontend/src/components/DividendHistoryModal.tsx`
- Modify: `frontend/src/components/TransactionForm.tsx`
- Modify: `frontend/src/hooks/usePortfolio.ts`
- Modify: `frontend/src/hooks/useTransactions.ts`
- Modify: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/pages/AssetClassHoldings.tsx`

- [ ] **Step 1: Create Money utility helper**

Add a utility function to parse Money objects for display. This can go in a new file or inline:

```typescript
// frontend/src/utils/money.ts
import type { Money } from "../types";

const CURRENCY_CONFIG: Record<string, { symbol: string; spacing: string; thousandsSep: string; decimalSep: string }> = {
  USD: { symbol: "$", spacing: "", thousandsSep: ",", decimalSep: "." },
  BRL: { symbol: "R$", spacing: " ", thousandsSep: ".", decimalSep: "," },
  EUR: { symbol: "€", spacing: "", thousandsSep: ".", decimalSep: "," },
};

export function formatMoney(money: Money | null | undefined, decimals: number = 2): string {
  if (!money) return "—";
  const config = CURRENCY_CONFIG[money.currency] ?? { symbol: money.currency, spacing: "", thousandsSep: ",", decimalSep: "." };
  const num = parseFloat(money.amount);
  const isNegative = num < 0;
  const abs = Math.abs(num);
  const [intPart, fracPart] = abs.toFixed(decimals).split(".");
  const formatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, config.thousandsSep);
  const result = `${config.symbol}${config.spacing}${formatted}${config.decimalSep}${fracPart}`;
  return isNegative ? `-${result}` : result;
}

export function moneyToNumber(money: Money | null | undefined): number {
  if (!money) return 0;
  return parseFloat(money.amount);
}
```

- [ ] **Step 2: Update HoldingsTable.tsx**

Replace the existing `formatCurrency` function with `formatMoney` from the utility. Update all references:
- `formatCurrency(h.avg_price, cur)` → `formatMoney(h.avg_price)`
- `formatCurrency(h.current_price, cur)` → `formatMoney(h.current_price)`
- `h.current_value ?? h.total_cost` → use `formatMoney(h.current_value ?? h.total_cost)`
- `h.gain_loss?.toFixed(2)` → `formatMoney(h.gain_loss)`
- Transaction display: `t.unit_price.toFixed(2)` → `formatMoney(t.unit_price)`
- `t.total_value.toFixed(2)` → `formatMoney(t.total_value)`
- Currency-based BRL conversion: update `toBRL` to work with Money objects

For arithmetic (e.g., portfolio totals, BRL conversion), use `moneyToNumber()` to extract the numeric value.

- [ ] **Step 3: Update DividendHistoryModal.tsx**

Replace `formatCurrency` with `formatMoney`:
- `formatCurrency(r.value, currency, 4)` → `formatMoney(r.value, 4)`
- `formatCurrency(r.total, currency)` → `formatMoney(r.total)`
- Totals: `records.reduce((sum, r) => sum + r.total, 0)` → `records.reduce((sum, r) => sum + moneyToNumber(r.total), 0)`

- [ ] **Step 4: Update TransactionForm.tsx**

Update form submission to send nested Money objects:
```typescript
const payload = {
  // ...
  unit_price: unitPrice ? { amount: unitPrice.toString(), currency: selectedCurrency } : null,
  total_value: { amount: totalValue.toString(), currency: selectedCurrency },
  tax_amount: taxAmount ? { amount: taxAmount.toString(), currency: selectedCurrency } : null,
};
```

When editing existing transactions, parse Money objects back to form values.

- [ ] **Step 5: Update usePortfolio.ts**

Update aggregation logic to use `moneyToNumber()`:
```typescript
const classTotal = holdings.reduce((sum, h) => sum + moneyToNumber(h.total_cost), 0);
```

- [ ] **Step 6: Update useTransactions.ts**

Update `createTransaction` and `updateTransaction` to send MoneyInput payloads. The form components should build the nested `{amount, currency}` objects before passing to the hook. Verify the hook's type signatures match the new `TransactionCreate`/`TransactionUpdate` schemas.

- [ ] **Step 7: Update AssetClassHoldings.tsx**

This page uses `h.current_value ?? h.total_cost` for BRL conversion calculations. After the type changes, these are Money objects. Update:
- `totalValueBRL` calculation to use `moneyToNumber()`
- Any allocation-related interfaces that have `total_cost: number` → `total_cost: Money`

- [ ] **Step 8: Update Dashboard.tsx**

Update DividendClassData interface and any monetary field access to use Money objects.

- [ ] **Step 9: Run frontend build to check for type errors**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 10: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: All tests PASS

- [ ] **Step 11: Commit**

```bash
git add frontend/src/
git commit -m "feat: frontend uses Money interface for all monetary values"
```

---

### Task 13: Final Integration Test

**Files:**
- Modify: `backend/tests/test_e2e.py` (if needed)
- Modify: `backend/tests/test_portfolio_enriched.py`

- [ ] **Step 1: Run full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Run full frontend build and test**

Run: `cd frontend && npm run build && npm run test`
Expected: Both PASS

- [ ] **Step 3: Manual smoke test**

Run: `cd backend && python -m uvicorn app.main:app --reload`

Verify endpoints return nested Money objects:
- `GET /api/stocks/AAPL` → `{"price": {"amount": "...", "currency": "USD"}, ...}`
- `GET /api/portfolio/summary` (with X-User-Id header) → holdings with Money objects

- [ ] **Step 4: Commit any remaining fixes**

Stage only the specific files that were fixed (avoid `git add -A`):
```bash
git add <specific-files-that-were-fixed>
git commit -m "fix: integration fixes for Money value object refactor"
```
