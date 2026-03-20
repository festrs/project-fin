# Money Value Object Design

## Overview

Refactor all monetary values in the project-fin portfolio management app to use a `Money` value object backed by `Decimal`, paired with a `Currency` enum type. Eliminates float-based money arithmetic and ensures currency safety across the system.

## Goals

- All monetary values stored and computed as `Decimal`, never `float`
- Currency is a typed enum, not a raw string
- `Money` value object pairs amount + currency, with display formatting
- Arithmetic between different currencies is prevented at the type level
- API responses use nested `{ amount, currency }` objects for all monetary fields
- Non-monetary numeric fields (percentages, ratios, quantities) remain as `float`

## Currency Enum

Extensible enum starting with USD, BRL, EUR. Each member carries formatting metadata:

```python
class Currency(enum.Enum):
    USD = ("USD", "$", "before", ",", ".")   # $1,234.56
    BRL = ("BRL", "R$", "before", ".", ",")  # R$ 1.234,56
    EUR = ("EUR", "€", "before", ".", ",")   # €1.234,56

    def __init__(self, code, symbol, symbol_position, thousands_sep, decimal_sep):
        self.code = code
        self.symbol = symbol
        self.symbol_position = symbol_position
        self.thousands_sep = thousands_sep
        self.decimal_sep = decimal_sep
```

Adding a new currency means adding one line to the enum with its formatting rules. All currencies use 2 decimal places for display.

## Money Value Object

Frozen dataclass in `backend/app/money.py`:

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency
```

### Construction

- `Money(Decimal("10.50"), Currency.USD)` — direct construction
- `Money.from_db(amount: Decimal, currency_code: str)` — from database columns
- `money.to_db() -> tuple[Decimal, str]` — to database columns

### Display

- `money.display() -> str` — formatted with currency symbol and locale rules (e.g., `$1,234.56`, `R$ 1.234,56`)
- `str(money)` — delegates to `display()`
- `repr(money)` — `Money(10.50, USD)`

### Arithmetic (same currency only)

All raise `CurrencyMismatchError` if currencies differ:

- `Money + Money -> Money`
- `Money - Money -> Money`
- `Money * (Decimal | int) -> Money` — scalar multiply only
- `-Money -> Money` — negation
- Comparisons: `<`, `<=`, `>`, `>=`, `==`

No division — it's ambiguous (Money / Money = ratio vs Money / scalar = Money). Can be added later if needed.

### Error Type

```python
class CurrencyMismatchError(ValueError):
    pass
```

## Database Schema Changes

### Storage Strategy

SQLAlchemy `Numeric(precision=19, scale=8, asdecimal=True)`. SQLite stores as TEXT internally; SQLAlchemy converts to/from `Decimal` automatically. 8 decimal places covers crypto precision.

### Fields That Change

| Model | Current Fields | New Column Types |
|-------|---------------|-----------------|
| **Transaction** | `unit_price: Float`, `total_value: Float`, `tax_amount: Float`, `currency: String` | `unit_price: Numeric(19,8)`, `total_value: Numeric(19,8)`, `tax_amount: Numeric(19,8)`, `currency: String` (kept) |
| **MarketQuote** | `current_price: Float`, `market_cap: Float`, `currency: String` | `current_price: Numeric(19,8)`, `market_cap: Numeric(19,8)`, `currency: String` (kept) |
| **DividendHistory** | `value: Float` (no currency) | `value: Numeric(19,8)`, `currency: String` (added) |

### Fields That Stay as Float

- `Transaction.quantity` — count of shares/units
- `StockSplit.from_factor`, `to_factor` — split ratios
- `AssetWeight.target_weight`, `AssetClass.target_weight` — percentages
- All `FundamentalsScore` fields — ratios and scores

## Service & Provider Integration

### Providers — convert at the boundary

- `FinnhubProvider`: returns `Money(Decimal(str(price)), Currency.USD)`
- `BrapiProvider`: returns `Money(Decimal(str(price)), Currency.BRL)`
- `CoinGecko` (in `market_data.py`): returns `Money(Decimal(str(price)), Currency.USD)`
- `DadosDeMercado`: `_parse_value()` returns `Decimal` for monetary values
- `YFinanceProvider`: dividend amounts return `Money`, ratios stay as `float`

### Services — arithmetic uses Money/Decimal

- `PortfolioService.get_holdings()`: `avg_price`, `total_cost` become `Money`. Division uses `Decimal`.
- `PortfolioService.enrich_holdings()`: `current_value`, `gain_loss` become `Money`. Weights stay `float`.
- `RecommendationService`: asset values as `Money`, weight diffs stay `float`.
- `MarketDataService`: caches `Money` objects instead of float prices.

## API Response Format

All monetary fields become nested objects:

```json
{
  "unit_price": { "amount": "150.25", "currency": "USD" },
  "total_value": { "amount": "1502.50", "currency": "USD" },
  "tax_amount": { "amount": "5.00", "currency": "USD" },
  "quantity": 10.0
}
```

### Pydantic Schema

```python
class MoneyResponse(BaseModel):
    amount: str       # Decimal as string to preserve precision
    currency: str     # Currency code

class MoneyInput(BaseModel):
    amount: float | str
    currency: str
```

## Frontend Impact

- New TypeScript `Money` interface: `{ amount: string; currency: string }`
- All monetary `number` fields become `Money` objects
- `formatCurrency()` reads from `Money` object
- Arithmetic in frontend parses `amount` string to number for display calculations

## Migration Strategy

No Alembic — project uses `Base.metadata.create_all()` with SQLite.

### Migration Script (`backend/scripts/migrate_to_decimal.py`)

1. Read existing tables using raw SQL
2. Convert float values: `Decimal(str(float_value))`
3. For `DividendHistory`, infer currency from asset's country code (BR → BRL, else USD)
4. Create new tables with correct column types
5. Copy data over
6. Rename old → backup, new → active
7. Print summary

### Implementation Order

1. Create `Money` + `Currency` module (no dependencies)
2. Update SQLAlchemy models (column types)
3. Run migration script on existing data
4. Update providers (return `Money`)
5. Update services (use `Money` arithmetic)
6. Update Pydantic schemas (nested `MoneyResponse`)
7. Update routers
8. Update frontend types and display
9. Update seed data to use `Money`
