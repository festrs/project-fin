# Where to Invest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated "Where to Invest" page that takes an investment amount and currency, then returns an actionable shopping list of specific assets with quantities and amounts.

**Architecture:** New POST endpoint extends the existing `RecommendationService` with an `get_investment_plan` method that distributes an amount across the top N underweight assets, calculates quantities (whole shares for stocks, fractional for crypto, lump-sum for fixed income), and redistributes rounding remainders. New React page at `/invest` with input bar and results table, accessible from sidebar.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React 19, TypeScript, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-03-21-where-to-invest-page-design.md`

---

## File Map

### Backend — New Files
- `backend/app/schemas/recommendation.py` — Pydantic request/response models for investment plan
- `backend/tests/test_services/test_investment_plan.py` — Unit tests for the investment plan service logic

### Backend — Modified Files
- `backend/app/services/recommendation.py` — Add `get_investment_plan()` method
- `backend/app/routers/recommendations.py` — Add `POST /api/recommendations/invest` endpoint
- `backend/app/routers/portfolio.py` — Extract `_fetch_exchange_rate` to a shared utility
- `backend/app/services/exchange_rate.py` — New shared exchange rate utility (extracted from portfolio router)

### Frontend — New Files
- `frontend/src/hooks/useInvest.ts` — Hook calling the invest API
- `frontend/src/pages/Invest.tsx` — The Where to Invest page

### Frontend — Modified Files
- `frontend/src/types/index.ts` — Add `InvestmentRecommendation` and `InvestmentPlan` interfaces
- `frontend/src/App.tsx` — Add `/invest` route
- `frontend/src/components/Sidebar.tsx` — Add "Where to Invest" nav entry
- `frontend/src/pages/Settings.tsx` — Remove recommendation count section
- `frontend/src/pages/Dashboard.tsx` — Remove `RecommendationCard` usage
- `frontend/src/components/ClassSummaryTable.tsx` — Remove `getRecommendationCount()`, `computeWhereToInvest()`, `computeTopUnderweightClasses()`, the "Invest (R$)" input, and the "Where to Invest" column

### Frontend — Files to Delete
- `frontend/src/components/RecommendationCard.tsx`
- `frontend/src/components/__tests__/RecommendationCard.test.tsx`
- `frontend/src/hooks/useRecommendations.ts`

---

## Task 1: Pydantic Schemas for Investment Plan

**Files:**
- Create: `backend/app/schemas/recommendation.py`

- [ ] **Step 1: Create the schema file**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from app.schemas.money import MoneyResponse


class InvestmentPlanRequest(BaseModel):
    amount: str
    currency: Literal["BRL", "USD"]
    count: int = 3

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        d = Decimal(v)
        if d <= 0:
            raise ValueError("amount must be positive")
        return v

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1:
            raise ValueError("count must be at least 1")
        return v


class InvestmentRecommendationResponse(BaseModel):
    symbol: str
    class_name: str
    effective_target: float
    actual_weight: float
    diff: float
    price: MoneyResponse
    quantity: float
    invest_amount: MoneyResponse


class InvestmentPlanResponse(BaseModel):
    recommendations: list[InvestmentRecommendationResponse]
    total_invested: MoneyResponse
    exchange_rate: float | None
    exchange_rate_pair: str | None
    remainder: MoneyResponse
    empty_reason: str | None = None  # "no_holdings", "all_quarantined", "amount_too_small", or None
```

- [ ] **Step 2: Verify import works**

Run: `cd backend && python -c "from app.schemas.recommendation import InvestmentPlanRequest, InvestmentPlanResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/recommendation.py
git commit -m "feat: add Pydantic schemas for investment plan endpoint"
```

---

## Task 2: Investment Plan Service Logic

**Files:**
- Modify: `backend/app/services/recommendation.py`
- Create: `backend/tests/test_services/test_investment_plan.py`

- [ ] **Step 1: Write failing tests for `get_investment_plan`**

Create `backend/tests/test_services/test_investment_plan.py`:

```python
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.models import User, AssetClass, AssetWeight, Transaction
from app.money import Money, Currency
from app.services.recommendation import RecommendationService


def _create_user(db):
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_asset_class(db, user_id, name, target_weight, country="US", asset_type="stock"):
    ac = AssetClass(user_id=user_id, name=name, target_weight=target_weight, country=country, type=asset_type)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _create_asset_weight(db, asset_class_id, symbol, target_weight):
    aw = AssetWeight(asset_class_id=asset_class_id, symbol=symbol, target_weight=target_weight)
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


def _create_buy(db, user_id, asset_class_id, symbol, quantity, unit_price, currency="USD"):
    qty = Decimal(str(quantity))
    price = Decimal(str(unit_price))
    tx = Transaction(
        user_id=user_id,
        asset_class_id=asset_class_id,
        asset_symbol=symbol,
        type="buy",
        quantity=qty,
        unit_price=price,
        total_value=qty * price,
        currency=currency,
        date=date.today() - timedelta(days=5),
    )
    db.add(tx)
    db.commit()
    return tx


def _mock_market_data():
    mock = MagicMock()

    def stock_quote(symbol, country="US", db=None):
        prices = {
            "AAPL": Money(Decimal("150.0"), Currency.USD),
            "GOOG": Money(Decimal("200.0"), Currency.USD),
            "PETR4.SA": Money(Decimal("40.0"), Currency.BRL),
        }
        return {"symbol": symbol, "current_price": prices.get(symbol, Money(Decimal("100.0"), Currency.USD))}

    def crypto_quote(coin_id):
        prices = {"bitcoin": Money(Decimal("50000.0"), Currency.USD)}
        return {"coin_id": coin_id, "current_price": prices.get(coin_id, Money(Decimal("100.0"), Currency.USD))}

    mock.get_stock_quote.side_effect = stock_quote
    mock.get_crypto_quote.side_effect = crypto_quote
    return mock


class TestGetInvestmentPlan:
    def test_distributes_amount_across_underweight_assets(self, db):
        """Should distribute USD amount proportionally by gap, returning quantities."""
        user = _create_user(db)

        ac_stocks = _create_asset_class(db, user.id, "Stocks", 60.0)
        ac_crypto = _create_asset_class(db, user.id, "Crypto", 40.0, asset_type="crypto")

        _create_asset_weight(db, ac_stocks.id, "AAPL", 50.0)
        _create_asset_weight(db, ac_stocks.id, "GOOG", 50.0)
        _create_asset_weight(db, ac_crypto.id, "BTC", 100.0)

        _create_buy(db, user.id, ac_stocks.id, "AAPL", 10, 150.0)
        _create_buy(db, user.id, ac_stocks.id, "GOOG", 5, 200.0)
        _create_buy(db, user.id, ac_crypto.id, "BTC", 0.01, 50000.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("3000"), "USD", count=3)

        assert len(plan["recommendations"]) > 0
        # Every recommendation should have quantity > 0 and invest_amount > 0
        for rec in plan["recommendations"]:
            assert rec["quantity"] > 0
            assert rec["invest_amount"].amount > 0
            assert rec["price"].amount > 0

        # Total invested + remainder should equal input
        total = plan["total_invested"].amount + plan["remainder"].amount
        assert total == Decimal("3000")

    def test_stocks_get_whole_share_quantities(self, db):
        """Stock quantities should be rounded down to whole numbers."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "US Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 100.0)
        _create_buy(db, user.id, ac.id, "AAPL", 10, 150.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("400"), "USD", count=1)

        rec = plan["recommendations"][0]
        assert rec["symbol"] == "AAPL"
        # $400 / $150 = 2.666... -> should be 2 whole shares
        assert rec["quantity"] == 2
        assert rec["invest_amount"].amount == Decimal("300")
        assert plan["remainder"].amount == Decimal("100")

    def test_crypto_gets_fractional_quantity(self, db):
        """Crypto quantities should be fractional."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Crypto", 100.0, asset_type="crypto")
        _create_asset_weight(db, ac.id, "BTC", 100.0)
        _create_buy(db, user.id, ac.id, "BTC", 0.01, 50000.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=1)

        rec = plan["recommendations"][0]
        assert rec["symbol"] == "BTC"
        # $1000 / $50000 = 0.02
        assert rec["quantity"] == Decimal("0.02")
        assert plan["remainder"].amount == Decimal("0")

    def test_remainder_redistribution(self, db):
        """Remainder from rounding should be redistributed to buy more shares of other assets."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 60.0)
        _create_asset_weight(db, ac.id, "GOOG", 40.0)
        # Make AAPL and GOOG both underweight
        _create_buy(db, user.id, ac.id, "AAPL", 5, 150.0)
        _create_buy(db, user.id, ac.id, "GOOG", 3, 200.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=2)

        total_invested = sum(r["invest_amount"].amount for r in plan["recommendations"])
        # Total invested + remainder = input
        assert total_invested + plan["remainder"].amount == Decimal("1000")
        # Remainder should be less than the cheapest share price ($150)
        assert plan["remainder"].amount < Decimal("150")

    def test_currency_conversion_brl_input(self, db):
        """When user inputs BRL, US stock amounts should be converted."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "US Stocks", 100.0)
        _create_asset_weight(db, ac.id, "AAPL", 100.0)
        _create_buy(db, user.id, ac.id, "AAPL", 10, 150.0)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        # Pass BRL amount and exchange rate
        plan = svc.get_investment_plan(user.id, Decimal("1500"), "BRL", count=1, exchange_rate=Decimal("5.0"))

        rec = plan["recommendations"][0]
        # AAPL costs $150 = R$750. R$1500 / R$750 = 2 shares
        assert rec["quantity"] == 2
        assert rec["invest_amount"].currency == Currency.BRL
        assert plan["exchange_rate"] == 5.0
        assert plan["exchange_rate_pair"] == "USD-BRL"

    def test_empty_portfolio_returns_empty(self, db):
        """No holdings should return empty recommendations."""
        user = _create_user(db)

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("1000"), "USD", count=3)

        assert plan["recommendations"] == []

    def test_fixed_income_lump_sum(self, db):
        """Fixed income assets should get quantity=1 and lump-sum amount."""
        user = _create_user(db)

        ac = _create_asset_class(db, user.id, "Fixed Income", 100.0, asset_type="fixed_income")
        _create_asset_weight(db, ac.id, "CDB Banco X", 100.0)
        # Fixed income: value-based (quantity=None)
        tx = Transaction(
            user_id=user.id,
            asset_class_id=ac.id,
            asset_symbol="CDB Banco X",
            type="buy",
            quantity=None,
            unit_price=None,
            total_value=Decimal("10000"),
            currency="BRL",
            date=date.today() - timedelta(days=5),
        )
        db.add(tx)
        db.commit()

        mock_market = _mock_market_data()
        svc = RecommendationService(db, market_data_service=mock_market)
        plan = svc.get_investment_plan(user.id, Decimal("5000"), "BRL", count=1)

        assert len(plan["recommendations"]) == 1
        rec = plan["recommendations"][0]
        assert rec["symbol"] == "CDB Banco X"
        assert rec["quantity"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_services/test_investment_plan.py -v`
Expected: All tests FAIL with `AttributeError: 'RecommendationService' object has no attribute 'get_investment_plan'`

- [ ] **Step 3: Implement `get_investment_plan` in the service**

Add to `backend/app/services/recommendation.py` — a new method on `RecommendationService`:

```python
def get_investment_plan(
    self,
    user_id: str,
    amount: Decimal,
    currency: str,
    count: int = 3,
    exchange_rate: Decimal | None = None,
) -> dict:
    """Build an investment plan distributing `amount` across top N underweight assets."""
    from app.money import Currency

    input_currency = Currency.from_code(currency)

    # Step 1: Get underweight assets (reuse existing logic)
    recs = self.get_recommendations(user_id, count=count)

    def _empty_result(reason: str) -> dict:
        return {
            "recommendations": [],
            "total_invested": Money(Decimal("0"), input_currency),
            "exchange_rate": float(exchange_rate) if exchange_rate else None,
            "exchange_rate_pair": "USD-BRL" if exchange_rate else None,
            "remainder": Money(amount, input_currency),
            "empty_reason": reason,
        }

    # Determine why there are no recommendations
    if not recs:
        # Check if user has any holdings at all
        holdings = self.portfolio_service.get_holdings(user_id)
        if not holdings:
            return _empty_result("no_holdings")
        # Has holdings but no recs → all must be quarantined
        return _empty_result("all_quarantined")

    # Step 2: Build asset class type map for rounding decisions
    asset_classes = (
        self.db.query(AssetClass)
        .filter(AssetClass.user_id == user_id, AssetClass.is_emergency_reserve == False)
        .all()
    )
    # symbol -> asset_class via asset_weights
    symbol_to_class: dict[str, AssetClass] = {}
    for ac in asset_classes:
        weights = self.db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
        for aw in weights:
            symbol_to_class[aw.symbol] = ac

    # Step 3: Fetch prices and determine asset types
    asset_data: list[dict] = []
    total_diff = sum(max(r["diff"], 0) for r in recs)
    if total_diff <= 0:
        return _empty_result("all_quarantined")

    for rec in recs:
        if rec["diff"] <= 0:
            continue
        symbol = rec["symbol"]
        ac = symbol_to_class.get(symbol)
        if not ac:
            continue

        asset_type = ac.type or "stock"
        country = ac.country or "US"
        is_fixed_income = asset_type == "fixed_income"
        is_crypto = asset_type == "crypto"

        if is_fixed_income:
            # Fixed income: no market price, lump-sum allocation
            price = None
        else:
            price = self._get_current_price(symbol, ac.name, country=country, db=self.db)

        asset_data.append({
            **rec,
            "price": price,
            "asset_type": asset_type,
            "is_fixed_income": is_fixed_income,
            "is_crypto": is_crypto,
            "country": country,
        })

    # Step 4: Distribute amount proportionally by gap
    results = []
    remaining = amount

    for ad in asset_data:
        share = Decimal(str(ad["diff"])) / Decimal(str(total_diff))
        allocated = (amount * share).quantize(Decimal("0.01"))
        ad["allocated"] = allocated

    # Step 5: Calculate quantities
    for ad in asset_data:
        allocated = ad["allocated"]

        if ad["is_fixed_income"]:
            # Fixed income: quantity is 1, invest the allocated amount
            invest_amount = allocated
            quantity = Decimal("1")
            price_money = Money(allocated, input_currency)
            invest_money = Money(invest_amount, input_currency)
        else:
            price_money = ad["price"]
            # Convert price to input currency if needed
            if price_money.currency != input_currency:
                if exchange_rate is None:
                    raise ValueError("Exchange rate required for cross-currency investment")
                if input_currency == Currency.BRL:
                    price_in_input = price_money.amount * exchange_rate
                else:
                    price_in_input = price_money.amount / exchange_rate
            else:
                price_in_input = price_money.amount

            if price_in_input <= 0:
                continue

            raw_qty = allocated / price_in_input

            if ad["is_crypto"]:
                quantity = raw_qty.quantize(Decimal("0.00000001"))
            else:
                quantity = int(raw_qty)

            if quantity <= 0:
                continue

            invest_amount = Decimal(str(quantity)) * price_in_input
            invest_money = Money(invest_amount.quantize(Decimal("0.01")), input_currency)

        remaining -= invest_money.amount
        results.append({
            "symbol": ad["symbol"],
            "class_name": ad["class_name"],
            "effective_target": ad["effective_target"],
            "actual_weight": ad["actual_weight"],
            "diff": ad["diff"],
            "price": price_money,
            "quantity": quantity,
            "invest_amount": invest_money,
        })

    # Step 6: Redistribute remainder (iterate through list, buy one more share each pass)
    if remaining > 0:
        changed = True
        while changed:
            changed = False
            for r in results:
                if remaining <= 0:
                    break
                ac = symbol_to_class.get(r["symbol"])
                if not ac or ac.type == "crypto" or ac.type == "fixed_income":
                    continue

                price_money = r["price"]
                if price_money.currency != input_currency and exchange_rate:
                    if input_currency == Currency.BRL:
                        share_cost = price_money.amount * exchange_rate
                    else:
                        share_cost = price_money.amount / exchange_rate
                else:
                    share_cost = price_money.amount

                cost = share_cost.quantize(Decimal("0.01")) if isinstance(share_cost, Decimal) else Decimal(str(share_cost)).quantize(Decimal("0.01"))
                if remaining >= cost and cost > 0:
                    r["quantity"] += 1
                    r["invest_amount"] = Money(r["invest_amount"].amount + cost, input_currency)
                    remaining -= cost
                    changed = True

    # Check if all quantities ended up zero (amount too small)
    if results and all(r["quantity"] <= 0 for r in results):
        return _empty_result("amount_too_small")

    return {
        "recommendations": [r for r in results if r["quantity"] > 0],
        "total_invested": Money(amount - remaining.quantize(Decimal("0.01")), input_currency),
        "exchange_rate": float(exchange_rate) if exchange_rate else None,
        "exchange_rate_pair": "USD-BRL" if exchange_rate else None,
        "remainder": Money(remaining.quantize(Decimal("0.01")), input_currency),
        "empty_reason": None,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_services/test_investment_plan.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run existing recommendation tests to ensure no regression**

Run: `cd backend && python -m pytest tests/test_services/test_recommendation.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/recommendation.py backend/tests/test_services/test_investment_plan.py
git commit -m "feat: add get_investment_plan method to RecommendationService"
```

---

## Task 3: Extract Exchange Rate Utility

**Files:**
- Create: `backend/app/services/exchange_rate.py`
- Modify: `backend/app/routers/portfolio.py`

The portfolio router has `_fetch_exchange_rate` with caching. Extract it to a shared module so both the portfolio and recommendations routers can use it.

- [ ] **Step 1: Create the shared exchange rate module**

Create `backend/app/services/exchange_rate.py`:

```python
import logging
import time

import httpx

logger = logging.getLogger(__name__)

_fx_cache: dict[str, tuple[float, float]] = {}
_FX_CACHE_TTL = 300  # 5 minutes


def fetch_exchange_rate(pair: str = "USD-BRL") -> float:
    """Fetch exchange rate with caching. pair e.g. 'USD-BRL'."""
    now = time.time()
    cached = _fx_cache.get(pair)
    if cached and (now - cached[1]) < _FX_CACHE_TTL:
        return cached[0]

    try:
        resp = httpx.get(
            f"https://economia.awesomeapi.com.br/last/{pair}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        key = pair.replace("-", "")
        rate = float(data[key]["bid"])
        _fx_cache[pair] = (rate, now)
        return rate
    except Exception:
        logger.exception("Failed to fetch exchange rate for %s", pair)
        if cached:
            return cached[0]
        return 5.15  # fallback
```

- [ ] **Step 2: Update portfolio router to use shared utility**

In `backend/app/routers/portfolio.py`, replace the local `_fetch_exchange_rate` function and its cache with:

```python
from app.services.exchange_rate import fetch_exchange_rate as _fetch_exchange_rate
```

Remove the old `_fx_cache`, `_FX_CACHE_TTL`, and `_fetch_exchange_rate` function definition. Keep all call sites unchanged (they call `_fetch_exchange_rate(pair)`).

- [ ] **Step 3: Run backend tests to confirm no regression**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/exchange_rate.py backend/app/routers/portfolio.py
git commit -m "refactor: extract exchange rate fetching to shared utility"
```

---

## Task 4: Investment Plan API Endpoint

**Files:**
- Modify: `backend/app/routers/recommendations.py`

- [ ] **Step 1: Add the POST endpoint**

Add to `backend/app/routers/recommendations.py`:

```python
# Add imports at top:
from app.schemas.recommendation import InvestmentPlanRequest, InvestmentPlanResponse, InvestmentRecommendationResponse
from app.schemas.money import MoneyResponse
from app.services.exchange_rate import fetch_exchange_rate
from decimal import Decimal


@router.post("/invest", response_model=InvestmentPlanResponse)
@limiter.limit(CRUD_LIMIT)
def invest_plan(
    request: Request,
    body: InvestmentPlanRequest,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    rate = fetch_exchange_rate("USD-BRL")
    exchange_rate = Decimal(str(rate))

    service = RecommendationService(db)
    plan = service.get_investment_plan(
        user_id=x_user_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        count=body.count,
        exchange_rate=exchange_rate,
    )

    # Convert Money objects to MoneyResponse
    recs_response = []
    for rec in plan["recommendations"]:
        recs_response.append(InvestmentRecommendationResponse(
            symbol=rec["symbol"],
            class_name=rec["class_name"],
            effective_target=rec["effective_target"],
            actual_weight=rec["actual_weight"],
            diff=rec["diff"],
            price=MoneyResponse(amount=str(rec["price"].amount), currency=rec["price"].currency.code),
            quantity=float(rec["quantity"]),
            invest_amount=MoneyResponse(amount=str(rec["invest_amount"].amount), currency=rec["invest_amount"].currency.code),
        ))

    return InvestmentPlanResponse(
        recommendations=recs_response,
        total_invested=MoneyResponse(amount=str(plan["total_invested"].amount), currency=plan["total_invested"].currency.code),
        exchange_rate=plan["exchange_rate"],
        exchange_rate_pair=plan["exchange_rate_pair"],
        remainder=MoneyResponse(amount=str(plan["remainder"].amount), currency=plan["remainder"].currency.code),
        empty_reason=plan.get("empty_reason"),
    )
```

- [ ] **Step 2: Write a router-level test**

Add to `backend/tests/test_routers/test_recommendations.py` (this file already has `_setup`, `Money`, `Currency`, `Decimal` imports and `patch`):

```python
@patch("app.services.recommendation.MarketDataService")
@patch("app.routers.recommendations.fetch_exchange_rate", return_value=5.0)
def test_invest_plan_endpoint(mock_fx, MockMarketData, client, default_user, db):
    _setup(db, default_user.id)

    mock_instance = MockMarketData.return_value
    mock_instance.get_stock_quote.return_value = {"current_price": Money(Decimal("175"), Currency.USD)}

    headers = {"X-User-Id": default_user.id}
    resp = client.post(
        "/api/recommendations/invest",
        json={"amount": "1000", "currency": "USD", "count": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data
    assert "total_invested" in data
    assert "remainder" in data
    if data["recommendations"]:
        rec = data["recommendations"][0]
        assert "price" in rec
        assert "quantity" in rec
        assert "invest_amount" in rec
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_routers/test_recommendations.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/recommendations.py backend/tests/test_routers/test_recommendations.py
git commit -m "feat: add POST /api/recommendations/invest endpoint"
```

---

## Task 5: Frontend Types and Hook

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/hooks/useInvest.ts`

- [ ] **Step 1: Add TypeScript interfaces**

Add to `frontend/src/types/index.ts` (after the existing `Recommendation` interface):

```typescript
export interface InvestmentRecommendation {
  symbol: string;
  class_name: string;
  effective_target: number;
  actual_weight: number;
  diff: number;
  price: Money;
  quantity: number;
  invest_amount: Money;
}

export interface InvestmentPlan {
  recommendations: InvestmentRecommendation[];
  total_invested: Money;
  exchange_rate: number | null;
  exchange_rate_pair: string | null;
  remainder: Money;
  empty_reason: "no_holdings" | "all_quarantined" | "amount_too_small" | null;
}
```

- [ ] **Step 2: Create the `useInvest` hook**

Create `frontend/src/hooks/useInvest.ts`:

```typescript
import { useState } from "react";
import api from "../services/api";
import type { InvestmentPlan } from "../types";

export function useInvest() {
  const [plan, setPlan] = useState<InvestmentPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = async (amount: string, currency: string, count: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.post<InvestmentPlan>("/recommendations/invest", {
        amount,
        currency,
        count,
      });
      setPlan(res.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to calculate investment plan";
      setError(message);
      setPlan(null);
    } finally {
      setLoading(false);
    }
  };

  return { plan, loading, error, calculate };
}
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useInvest.ts
git commit -m "feat: add InvestmentPlan types and useInvest hook"
```

---

## Task 6: Where to Invest Page

**Files:**
- Create: `frontend/src/pages/Invest.tsx`

- [ ] **Step 1: Create the page component**

Create `frontend/src/pages/Invest.tsx`:

```tsx
import { useState } from "react";
import { useInvest } from "../hooks/useInvest";

export default function Invest() {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("BRL");
  const [count, setCount] = useState(3);
  const { plan, loading, error, calculate } = useInvest();

  const handleCalculate = () => {
    if (!amount || parseFloat(amount) <= 0) return;
    calculate(amount, currency, count);
  };

  const formatMoney = (value: { amount: string; currency: string }) => {
    const num = parseFloat(value.amount);
    if (value.currency === "BRL") {
      return `R$ ${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatQuantity = (qty: number) => {
    if (qty >= 1 && Number.isInteger(qty)) return qty.toString();
    return qty.toFixed(8).replace(/0+$/, "").replace(/\.$/, "");
  };

  return (
    <div className="space-y-4">
      <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Where to Invest</h1>

      {/* Input bar */}
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <div className="flex items-end gap-4 flex-wrap">
          <div>
            <label htmlFor="amount" className="block text-base font-medium text-text-secondary mb-1">
              Amount
            </label>
            <input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCalculate()}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary w-40 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <div>
            <label htmlFor="currency" className="block text-base font-medium text-text-secondary mb-1">
              Currency
            </label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            >
              <option value="BRL">BRL</option>
              <option value="USD">USD</option>
            </select>
          </div>
          <div>
            <label htmlFor="count" className="block text-base font-medium text-text-secondary mb-1">
              # Recommendations
            </label>
            <input
              id="count"
              type="number"
              min="1"
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value, 10) || 1)}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary w-24 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <button
            onClick={handleCalculate}
            disabled={loading || !amount}
            className="bg-primary text-white px-6 py-2.5 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {loading ? "Calculating..." : "Calculate"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-negative/10 border border-negative/30 rounded-[14px] p-4">
          <p className="text-negative text-base">{error}</p>
        </div>
      )}

      {/* Results */}
      {!plan && !loading && !error && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <p className="text-text-muted text-base">Enter an amount and click Calculate to get your investment plan.</p>
        </div>
      )}

      {loading && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <p className="text-text-muted text-base">Calculating investment plan...</p>
        </div>
      )}

      {plan && !loading && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Investment Plan</h2>

          {plan.recommendations.length === 0 ? (
            <p className="text-text-muted text-base">
              {plan.empty_reason === "no_holdings"
                ? "Add holdings to your portfolio first."
                : plan.empty_reason === "all_quarantined"
                ? "No recommendations available — all top candidates are in quarantine."
                : plan.empty_reason === "amount_too_small"
                ? "Amount too low to purchase any recommended assets."
                : "No recommendations available."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-base">
                <thead>
                  <tr className="text-text-muted text-left border-b border-[var(--glass-border)]">
                    <th className="py-2 px-2">Asset</th>
                    <th className="py-2 px-2">Class</th>
                    <th className="py-2 px-2 text-right">Target</th>
                    <th className="py-2 px-2 text-right">Actual</th>
                    <th className="py-2 px-2 text-right">Gap</th>
                    <th className="py-2 px-2 text-right">Price</th>
                    <th className="py-2 px-2 text-right">Qty</th>
                    <th className="py-2 px-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.recommendations.map((rec) => (
                    <tr key={rec.symbol} className="border-b border-[var(--glass-border)] last:border-0 even:bg-[var(--glass-row-alt)]">
                      <td className="py-2.5 px-2 font-semibold text-text-primary">{rec.symbol}</td>
                      <td className="py-2.5 px-2 text-text-muted">{rec.class_name}</td>
                      <td className="py-2.5 px-2 text-right">{rec.effective_target.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right">{rec.actual_weight.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right text-positive">+{rec.diff.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right">{formatMoney(rec.price)}</td>
                      <td className="py-2.5 px-2 text-right font-semibold">{formatQuantity(rec.quantity)}</td>
                      <td className="py-2.5 px-2 text-right font-semibold">{formatMoney(rec.invest_amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-[var(--glass-border)] font-bold">
                    <td colSpan={7} className="py-3 px-2">Total</td>
                    <td className="py-3 px-2 text-right">{formatMoney(plan.total_invested)}</td>
                  </tr>
                  {parseFloat(plan.remainder.amount) > 0 && (
                    <tr className="text-text-muted">
                      <td colSpan={7} className="py-1 px-2 text-sm">Uninvested remainder</td>
                      <td className="py-1 px-2 text-right text-sm">{formatMoney(plan.remainder)}</td>
                    </tr>
                  )}
                </tfoot>
              </table>
            </div>
          )}

          {plan.exchange_rate && (
            <p className="text-text-muted text-sm mt-3">
              Exchange rate ({plan.exchange_rate_pair}): {plan.exchange_rate.toFixed(2)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Invest.tsx
git commit -m "feat: add Where to Invest page component"
```

---

## Task 7: Wire Up Route and Sidebar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Add route to App.tsx**

In `frontend/src/App.tsx`, add the import and route:

Add import: `import Invest from "./pages/Invest";`

Add route after the Dashboard route:
```tsx
<Route path="/invest" element={<Invest />} />
```

- [ ] **Step 2: Add sidebar entry**

In `frontend/src/components/Sidebar.tsx`:

Add import: `import { LayoutGrid, TrendingUp, Settings } from "lucide-react";`

Update the `links` array to include the new entry between Dashboard and Settings:
```typescript
const links = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/invest", label: "Where to Invest", icon: TrendingUp },
  { to: "/settings", label: "Settings", icon: Settings },
];
```

- [ ] **Step 3: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat: add Where to Invest route and sidebar navigation"
```

---

## Task 8: Remove Old Recommendation UI

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx` — Remove RecommendationCard usage
- Modify: `frontend/src/pages/Settings.tsx` — Remove recommendation count section
- Modify: `frontend/src/components/ClassSummaryTable.tsx` — Remove "Where to Invest" column, invest input, and helper functions
- Delete: `frontend/src/components/RecommendationCard.tsx`
- Delete: `frontend/src/components/__tests__/RecommendationCard.test.tsx`
- Delete: `frontend/src/hooks/useRecommendations.ts`

- [ ] **Step 1: Clean up Dashboard.tsx**

Remove from `frontend/src/pages/Dashboard.tsx`:
- Remove import: `import { RecommendationCard } from "../components/RecommendationCard";`
- Remove import: `import { useRecommendations } from "../hooks/useRecommendations";`
- Remove the `savedCount`, `count`, and `useRecommendations(count)` variables
- Remove the `recsLoading` conditional and `<RecommendationCard>` JSX block (the "Recommendations" section near bottom of the return)

- [ ] **Step 2: Clean up Settings.tsx**

Remove from `frontend/src/pages/Settings.tsx`:
- Remove the `recCount` state initializer and `handleSaveRecommendations` function
- Remove the entire "Recommendation Settings" card section (the `<div>` containing the `recCount` input and its save button)

- [ ] **Step 3: Clean up ClassSummaryTable.tsx**

Remove from `frontend/src/components/ClassSummaryTable.tsx`:
- Remove `getRecommendationCount()` function
- Remove `computeWhereToInvest()` function
- Remove `computeTopUnderweightClasses()` function
- Remove `investAmount` state and its setter
- Remove `parsedInvest`, `recCount`, `whereToInvest`, `topUnderweight` computed values
- Remove the "Invest (R$)" label and input in the table header area
- Remove the "Where to Invest" `<th>` column header
- Remove the `investSuggestion` variable and the corresponding `<td>` cell in each row
- Remove any row highlighting based on `topUnderweight`

- [ ] **Step 4: Delete old component files**

Delete:
- `frontend/src/components/RecommendationCard.tsx`
- `frontend/src/components/__tests__/RecommendationCard.test.tsx`
- `frontend/src/hooks/useRecommendations.ts`

- [ ] **Step 5: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 6: Run frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: All tests pass (some tests related to RecommendationCard should be gone now)

- [ ] **Step 7: Commit**

```bash
git add -u frontend/src/
git commit -m "refactor: remove old recommendation card, settings, and class-level invest column"
```

---

## Task 9: Full Integration Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npm run test -- --run`
Expected: All tests PASS

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Manual smoke test**

Start backend and frontend dev servers:
```bash
cd backend && python -m uvicorn app.main:app --reload &
cd frontend && npm run dev &
```

Verify:
1. Sidebar shows "Where to Invest" between Dashboard and Settings
2. Click "Where to Invest" — page loads with input bar
3. Enter an amount, select currency, set count, click Calculate
4. Results table shows assets with prices, quantities, and amounts
5. Dashboard no longer shows the old recommendation card
6. Settings no longer shows recommendation count section
7. ClassSummaryTable no longer shows "Where to Invest" column or invest input
