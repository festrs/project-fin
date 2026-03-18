# Stock Split Tracking Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect stock splits via Finnhub/Brapi, let users confirm/dismiss them, and adjust holdings math accordingly.

**Architecture:** New `StockSplit` model stores detected splits with pending/applied/dismissed workflow. `get_holdings()` becomes split-aware by querying individual transactions and multiplying quantities by cumulative split ratios. A daily APScheduler job detects splits for held symbols.

**Tech Stack:** FastAPI, SQLAlchemy, APScheduler, React hooks, Axios

**Spec:** `docs/superpowers/specs/2026-03-18-stock-split-tracking-design.md`

---

## Chunk 1: Backend Data Model & Config

### Task 1: StockSplit SQLAlchemy Model

**Files:**
- Create: `backend/app/models/stock_split.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the StockSplit model**

```python
# backend/app/models/stock_split.py
from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import String, Float, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockSplit(Base):
    __tablename__ = "stock_splits"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "split_date", name="uq_user_symbol_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    split_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_factor: Mapped[float] = mapped_column(Float, nullable=False)
    to_factor: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    asset_class_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_classes.id"), nullable=False)
```

- [ ] **Step 2: Register in models __init__**

Add to `backend/app/models/__init__.py`:
```python
from app.models.stock_split import StockSplit
# Add StockSplit to __all__
```

- [ ] **Step 3: Verify model loads**

Run: `cd backend && python -c "from app.models.stock_split import StockSplit; print(StockSplit.__tablename__)"`
Expected: `stock_splits`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/stock_split.py backend/app/models/__init__.py
git commit -m "feat: add StockSplit model"
```

### Task 2: Config Settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add split checker settings**

Add to `Settings` class in `backend/app/config.py`:
```python
enable_split_checker: bool = True
split_checker_hour: int = 10
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add split checker config settings"
```

### Task 3: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/stock_split.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/schemas/stock_split.py
from datetime import date, datetime
from pydantic import BaseModel


class StockSplitPending(BaseModel):
    id: str
    symbol: str
    split_date: date
    from_factor: float
    to_factor: float
    detected_at: datetime
    current_quantity: float
    new_quantity: float

    class Config:
        from_attributes = True


class StockSplitAction(BaseModel):
    message: str
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/stock_split.py
git commit -m "feat: add StockSplit pydantic schemas"
```

---

## Chunk 2: Split-Aware Holdings Calculation

### Task 4: Tests for Split-Aware get_holdings()

**Files:**
- Create: `backend/tests/test_services/test_portfolio_splits.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_services/test_portfolio_splits.py
from datetime import date

import pytest

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.services.portfolio import PortfolioService


def _make_user(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()
    return user


def _make_stock_class(db, user):
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    db.add(ac)
    db.flush()
    return ac


class TestSplitAwareHoldings:
    def test_no_splits_no_regression(self, db):
        """Existing behavior: no splits applied, quantities unchanged."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="AAPL",
            type="buy", quantity=100, unit_price=150.0, total_value=15000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        assert len(holdings) == 1
        assert holdings[0]["quantity"] == 100
        assert holdings[0]["avg_price"] == 150.0

    def test_simple_split_no_sells(self, db):
        """Buy 100 @ $60, split 1:2 -> 200 shares, avg $30."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 200
        assert h["avg_price"] == pytest.approx(30.0)
        assert h["total_cost"] == pytest.approx(6000.0)

    def test_split_with_pre_split_sells(self, db):
        """Buy 200 @ $60, sell 100, split 1:2 -> 200 shares, avg $30, cost $6000."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=200, unit_price=60.0, total_value=12000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="sell", quantity=100, unit_price=65.0, total_value=6500.0,
            currency="USD", date=date(2025, 3, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 200  # (200*2) - (100*2) = 200
        assert h["avg_price"] == pytest.approx(30.0)  # 12000 / 400
        assert h["total_cost"] == pytest.approx(6000.0)

    def test_split_with_post_split_sells(self, db):
        """Buy 100 @ $60, split 1:2, sell 50 -> 150 shares, avg $30."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="sell", quantity=50, unit_price=32.0, total_value=1600.0,
            currency="USD", date=date(2025, 6, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 150  # (100*2) - (50*1)
        assert h["avg_price"] == pytest.approx(30.0)
        assert h["total_cost"] == pytest.approx(4500.0)

    def test_multiple_splits(self, db):
        """Buy 100 @ $120, split 1:2, then split 1:3 -> 600 shares, avg $20."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=120.0, total_value=12000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="applied", asset_class_id=ac.id,
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 9, 1),
            from_factor=1, to_factor=3, status="applied", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 600  # 100 * 2 * 3
        assert h["avg_price"] == pytest.approx(20.0)  # 12000 / 600

    def test_pending_split_not_applied(self, db):
        """Pending splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 100  # unchanged
        assert h["avg_price"] == 60.0

    def test_dismissed_split_not_applied(self, db):
        """Dismissed splits should NOT affect holdings."""
        user = _make_user(db)
        ac = _make_stock_class(db, user)
        db.add(Transaction(
            user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
            type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
            currency="USD", date=date(2025, 1, 1),
        ))
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="dismissed", asset_class_id=ac.id,
        ))
        db.commit()

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        h = next(x for x in holdings if x["symbol"] == "FAST")
        assert h["quantity"] == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_services/test_portfolio_splits.py -v`
Expected: FAIL (split-aware logic not yet implemented)

- [ ] **Step 3: Commit test file**

```bash
git add backend/tests/test_services/test_portfolio_splits.py
git commit -m "test: add split-aware holdings calculation tests"
```

### Task 5: Implement Split-Aware get_holdings()

**Files:**
- Modify: `backend/app/services/portfolio.py` (lines 16-128, the `get_holdings` method)

- [ ] **Step 1: Rewrite the quantity-based branch to be split-aware**

The key change: instead of using `func.sum()` aggregates, query individual transactions for each symbol, then for each transaction compute `adjusted_qty = qty * product(to/from for splits after tx.date)`. Only `applied` splits are considered.

Replace the quantity-based branch (the `else` block starting at line 79) in `get_holdings()`:

```python
def get_holdings(self, user_id: str) -> list[dict]:
    from app.models.stock_split import StockSplit

    symbols = (
        self.db.query(Transaction.asset_symbol, Transaction.asset_class_id)
        .filter(Transaction.user_id == user_id)
        .distinct()
        .all()
    )

    # Pre-load all applied splits for this user
    applied_splits = (
        self.db.query(StockSplit)
        .filter(StockSplit.user_id == user_id, StockSplit.status == "applied")
        .all()
    )
    splits_by_symbol: dict[str, list] = {}
    for s in applied_splits:
        splits_by_symbol.setdefault(s.symbol, []).append(s)

    holdings = []
    for symbol, asset_class_id in symbols:
        # Check if this symbol has quantity-based transactions
        buy_agg = (
            self.db.query(
                func.sum(Transaction.quantity).label("total_qty"),
                func.sum(Transaction.total_value).label("total_value"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_symbol == symbol,
                Transaction.type == "buy",
            )
            .first()
        )

        buy_qty = buy_agg.total_qty

        if buy_qty is None:
            # Value-based (fixed income): unchanged
            buy_value = buy_agg.total_value or 0
            sell_value = (
                self.db.query(func.sum(Transaction.total_value))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.asset_symbol == symbol,
                    Transaction.type == "sell",
                )
                .scalar()
            ) or 0
            net_value = buy_value - sell_value
            if net_value <= 0:
                continue
            tx_currency = (
                self.db.query(Transaction.currency)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.asset_symbol == symbol,
                    Transaction.type == "buy",
                )
                .order_by(Transaction.date.desc())
                .first()
            )
            holdings.append({
                "symbol": symbol,
                "asset_class_id": asset_class_id,
                "quantity": None,
                "avg_price": None,
                "total_cost": net_value,
                "currency": tx_currency[0] if tx_currency else "BRL",
            })
        else:
            # Quantity-based: split-aware calculation
            symbol_splits = splits_by_symbol.get(symbol, [])

            if not symbol_splits:
                # Fast path: no splits, use original aggregate logic
                buy_qty = buy_qty or 0
                buy_value = buy_agg.total_value or 0
                sell_agg = (
                    self.db.query(func.sum(Transaction.quantity).label("total_qty"))
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.asset_symbol == symbol,
                        Transaction.type == "sell",
                    )
                    .first()
                )
                sell_qty = sell_agg.total_qty or 0
                net_qty = buy_qty - sell_qty
                if net_qty <= 0:
                    continue
                avg_price = buy_value / buy_qty if buy_qty > 0 else 0
                total_cost = avg_price * net_qty
            else:
                # Slow path: per-transaction split adjustment
                transactions = (
                    self.db.query(Transaction)
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.asset_symbol == symbol,
                        Transaction.type.in_(["buy", "sell"]),
                    )
                    .all()
                )

                adjusted_buy_qty = 0.0
                adjusted_buy_value = 0.0
                adjusted_sell_qty = 0.0

                for tx in transactions:
                    # Compute cumulative split ratio for splits after this tx date
                    ratio = 1.0
                    for sp in symbol_splits:
                        if sp.split_date > tx.date:
                            ratio *= sp.to_factor / sp.from_factor
                    adjusted_qty = (tx.quantity or 0) * ratio

                    if tx.type == "buy":
                        adjusted_buy_qty += adjusted_qty
                        adjusted_buy_value += tx.total_value
                    elif tx.type == "sell":
                        adjusted_sell_qty += adjusted_qty

                net_qty = adjusted_buy_qty - adjusted_sell_qty
                if net_qty <= 0:
                    continue
                avg_price = adjusted_buy_value / adjusted_buy_qty if adjusted_buy_qty > 0 else 0
                total_cost = avg_price * net_qty

            tx_currency = (
                self.db.query(Transaction.currency)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.asset_symbol == symbol,
                    Transaction.type == "buy",
                )
                .order_by(Transaction.date.desc())
                .first()
            )

            holdings.append({
                "symbol": symbol,
                "asset_class_id": asset_class_id,
                "quantity": net_qty,
                "avg_price": avg_price,
                "total_cost": total_cost,
                "currency": tx_currency[0] if tx_currency else "BRL",
            })

    return holdings
```

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest tests/test_services/test_portfolio_splits.py -v`
Expected: All PASS

- [ ] **Step 3: Run full test suite for regression**

Run: `cd backend && pytest -v`
Expected: All existing tests still pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/portfolio.py
git commit -m "feat: make get_holdings() split-aware"
```

---

## Chunk 3: API Endpoints (Router + Apply/Dismiss)

### Task 6: Splits Router

**Files:**
- Create: `backend/app/routers/splits.py`
- Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Create the router**

```python
# backend/app/routers/splits.py
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.stock_split import StockSplit
from app.schemas.stock_split import StockSplitPending, StockSplitAction
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/splits", tags=["splits"])


@router.get("/pending", response_model=list[StockSplitPending])
@limiter.limit(CRUD_LIMIT)
def get_pending_splits(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    splits = (
        db.query(StockSplit)
        .filter(StockSplit.user_id == x_user_id, StockSplit.status == "pending")
        .all()
    )

    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)
    qty_map = {h["symbol"]: h["quantity"] or 0 for h in holdings}

    result = []
    for s in splits:
        current_qty = qty_map.get(s.symbol, 0)
        ratio = s.to_factor / s.from_factor
        result.append(StockSplitPending(
            id=s.id,
            symbol=s.symbol,
            split_date=s.split_date,
            from_factor=s.from_factor,
            to_factor=s.to_factor,
            detected_at=s.detected_at,
            current_quantity=current_qty,
            new_quantity=current_qty * ratio,
        ))

    return result


@router.post("/{split_id}/apply", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def apply_split(
    split_id: str,
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == x_user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    split.status = "applied"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split applied")


@router.post("/{split_id}/dismiss", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def dismiss_split(
    split_id: str,
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == x_user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    split.status = "dismissed"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split dismissed")
```

- [ ] **Step 2: Register router in main.py**

Add to imports and `include_router` calls in `backend/app/main.py`:
```python
from app.routers import (
    asset_classes, asset_weights, transactions,
    stocks, crypto, portfolio, recommendations, quarantine,
    fundamentals, splits,
)
# ...
app.include_router(splits.router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/splits.py backend/app/main.py
git commit -m "feat: add splits router (pending, apply, dismiss endpoints)"
```

### Task 7: Router Tests

**Files:**
- Create: `backend/tests/test_routers/test_splits.py`

- [ ] **Step 1: Write router tests**

```python
# backend/tests/test_routers/test_splits.py
from datetime import date

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction


def _setup_split(db, user):
    ac = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    db.add(ac)
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac.id, asset_symbol="FAST",
        type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
        currency="USD", date=date(2025, 1, 1),
    ))

    split = StockSplit(
        user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
        from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
    )
    db.add(split)
    db.commit()
    return split


class TestSplitsRouter:
    def test_get_pending(self, client, default_user, db):
        split = _setup_split(db, default_user)
        resp = client.get("/api/splits/pending", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "FAST"
        assert data[0]["current_quantity"] == 100
        assert data[0]["new_quantity"] == 200

    def test_apply_split(self, client, default_user, db):
        split = _setup_split(db, default_user)
        resp = client.post(f"/api/splits/{split.id}/apply", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 200
        db.refresh(split)
        assert split.status == "applied"
        assert split.resolved_at is not None

    def test_dismiss_split(self, client, default_user, db):
        split = _setup_split(db, default_user)
        resp = client.post(f"/api/splits/{split.id}/dismiss", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 200
        db.refresh(split)
        assert split.status == "dismissed"

    def test_apply_already_applied(self, client, default_user, db):
        split = _setup_split(db, default_user)
        client.post(f"/api/splits/{split.id}/apply", headers={"X-User-Id": default_user.id})
        resp = client.post(f"/api/splits/{split.id}/apply", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 400

    def test_apply_nonexistent(self, client, default_user, db):
        resp = client.post("/api/splits/nonexistent/apply", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 404

    def test_no_pending_returns_empty(self, client, default_user, db):
        resp = client.get("/api/splits/pending", headers={"X-User-Id": default_user.id})
        assert resp.status_code == 200
        assert resp.json() == []
```

- [ ] **Step 2: Run tests**

Run: `cd backend && pytest tests/test_routers/test_splits.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_routers/test_splits.py
git commit -m "test: add splits router tests"
```

---

## Chunk 4: Provider get_splits() Methods

### Task 8: Finnhub get_splits()

**Files:**
- Modify: `backend/app/providers/finnhub.py`
- Create: `backend/tests/test_providers/test_finnhub_splits.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_providers/test_finnhub_splits.py
from unittest.mock import patch, MagicMock

from app.providers.finnhub import FinnhubProvider


class TestFinnhubSplits:
    def test_get_splits_returns_normalized(self):
        provider = FinnhubProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp) as mock_get:
            result = provider.get_splits("FAST", "2025-01-01", "2025-12-31")

        assert len(result) == 1
        assert result[0]["symbol"] == "FAST"
        assert result[0]["date"] == "2025-05-22"
        assert result[0]["fromFactor"] == 1
        assert result[0]["toFactor"] == 2
        mock_get.assert_called_once()

    def test_get_splits_empty(self):
        provider = FinnhubProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("AAPL", "2025-01-01", "2025-12-31")

        assert result == []
```

- [ ] **Step 2: Add get_splits() to FinnhubProvider**

Add to `backend/app/providers/finnhub.py`:
```python
def get_splits(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
    """GET /stock/split for a symbol within a date range."""
    resp = httpx.get(
        f"{self._base_url}/stock/split",
        params={"symbol": symbol, "from": from_date, "to": to_date, "token": self._api_key},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_providers/test_finnhub_splits.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/providers/finnhub.py backend/tests/test_providers/test_finnhub_splits.py
git commit -m "feat: add get_splits() to FinnhubProvider"
```

### Task 9: Brapi get_splits()

**Files:**
- Modify: `backend/app/providers/brapi.py`
- Create: `backend/tests/test_providers/test_brapi_splits.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_providers/test_brapi_splits.py
from unittest.mock import patch, MagicMock

from app.providers.brapi import BrapiProvider


class TestBrapiSplits:
    def test_get_splits_filters_desdobramento(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{
                "dividendsData": {
                    "stockDividends": [
                        {"label": "DESDOBRAMENTO", "rate": 2, "lastDatePrior": "2008-03-24T00:00:00.000Z"},
                        {"label": "BONIFICACAO", "rate": 0.1, "lastDatePrior": "2010-01-15T00:00:00.000Z"},
                    ]
                }
            }]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("PETR4.SA")

        assert len(result) == 1
        assert result[0]["symbol"] == "PETR4.SA"
        assert result[0]["date"] == "2008-03-24"
        assert result[0]["fromFactor"] == 1
        assert result[0]["toFactor"] == 2

    def test_get_splits_empty_dividends(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{"dividendsData": {"stockDividends": []}}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("VALE3.SA")

        assert result == []

    def test_get_splits_no_dividends_data(self):
        provider = BrapiProvider(api_key="test", base_url="http://fake")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": [{}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.get", return_value=mock_resp):
            result = provider.get_splits("VALE3.SA")

        assert result == []
```

- [ ] **Step 2: Add get_splits() to BrapiProvider**

Add to `backend/app/providers/brapi.py`:
```python
def get_splits(self, symbol: str) -> list[dict]:
    """Get stock splits from quote endpoint with dividends=true."""
    ticker = _strip_sa(symbol)
    resp = httpx.get(
        f"{self._base_url}/api/quote/{ticker}",
        params={"token": self._api_key, "dividends": "true"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()["results"][0]
    dividends_data = data.get("dividendsData", {})
    stock_dividends = dividends_data.get("stockDividends", [])

    splits = []
    for entry in stock_dividends:
        if entry.get("label") == "DESDOBRAMENTO":
            date_str = entry.get("lastDatePrior", "")
            if date_str:
                splits.append({
                    "symbol": symbol,
                    "date": date_str[:10],
                    "fromFactor": 1,
                    "toFactor": entry.get("rate", 1),
                })
    return splits
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_providers/test_brapi_splits.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/providers/brapi.py backend/tests/test_providers/test_brapi_splits.py
git commit -m "feat: add get_splits() to BrapiProvider"
```

---

## Chunk 5: Split Checker Scheduler

### Task 10: Split Checker Scheduler

**Files:**
- Create: `backend/app/services/split_checker_scheduler.py`
- Create: `backend/tests/test_services/test_split_checker_scheduler.py`
- Modify: `backend/app/main.py` (add scheduler job)

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_services/test_split_checker_scheduler.py
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.models.user import User
from app.services.split_checker_scheduler import SplitCheckerScheduler


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US", type="stock")
    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR", type="stock")
    db.add_all([ac_us, ac_br])
    db.flush()

    db.add(Transaction(
        user_id=user.id, asset_class_id=ac_us.id, asset_symbol="FAST",
        type="buy", quantity=100, unit_price=60.0, total_value=6000.0,
        currency="USD", date=date(2025, 1, 1),
    ))
    db.add(Transaction(
        user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
        type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
        currency="BRL", date=date(2025, 1, 1),
    ))
    db.commit()
    return user


class TestSplitCheckerScheduler:
    def test_creates_pending_splits(self, db):
        user = _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()

        finnhub.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1
        assert splits[0].status == "pending"
        assert splits[0].from_factor == 1
        assert splits[0].to_factor == 2

    def test_skips_existing_splits(self, db):
        user = _setup_holdings(db)

        ac = db.query(AssetClass).filter(AssetClass.name == "US Stocks").first()
        db.add(StockSplit(
            user_id=user.id, symbol="FAST", split_date=date(2025, 5, 22),
            from_factor=1, to_factor=2, status="pending", asset_class_id=ac.id,
        ))
        db.commit()

        finnhub = MagicMock()
        brapi = MagicMock()
        finnhub.get_splits.return_value = [
            {"symbol": "FAST", "date": "2025-05-22", "fromFactor": 1, "toFactor": 2},
        ]
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        splits = db.query(StockSplit).filter(StockSplit.symbol == "FAST").all()
        assert len(splits) == 1  # no duplicate

    def test_continues_on_provider_error(self, db):
        user = _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()

        finnhub.get_splits.side_effect = Exception("API error")
        brapi.get_splits.return_value = [
            {"symbol": "PETR4.SA", "date": "2008-03-24", "fromFactor": 1, "toFactor": 2},
        ]

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        # FAST failed but PETR4 should still be created
        splits = db.query(StockSplit).all()
        assert len(splits) == 1
        assert splits[0].symbol == "PETR4.SA"

    def test_uses_correct_provider_by_suffix(self, db):
        user = _setup_holdings(db)
        finnhub = MagicMock()
        brapi = MagicMock()
        finnhub.get_splits.return_value = []
        brapi.get_splits.return_value = []

        scheduler = SplitCheckerScheduler(finnhub_provider=finnhub, brapi_provider=brapi, delay=0)
        scheduler.check_all(db)

        # Finnhub called for FAST (US), Brapi called for PETR4.SA (BR)
        finnhub.get_splits.assert_called_once()
        assert finnhub.get_splits.call_args[0][0] == "FAST"
        brapi.get_splits.assert_called_once()
        assert brapi.get_splits.call_args[0][0] == "PETR4.SA"
```

- [ ] **Step 2: Create the scheduler service**

```python
# backend/app/services/split_checker_scheduler.py
import logging
import time
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit
from app.models.transaction import Transaction
from app.providers.brapi import BrapiProvider
from app.providers.finnhub import FinnhubProvider

logger = logging.getLogger(__name__)


class SplitCheckerScheduler:
    def __init__(self, finnhub_provider: FinnhubProvider, brapi_provider: BrapiProvider, delay: float = 0.5):
        self._finnhub = finnhub_provider
        self._brapi = brapi_provider
        self._delay = delay

    def check_all(self, db: Session) -> None:
        # Get all users who have stock-type asset classes with transactions
        user_ids = (
            db.query(Transaction.user_id)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.type == "stock")
            .distinct()
            .all()
        )

        for (user_id,) in user_ids:
            self._check_user(db, user_id)

    def _check_user(self, db: Session, user_id: str) -> None:
        # Get symbols with positive holdings in stock classes
        stock_classes = (
            db.query(AssetClass)
            .filter(AssetClass.user_id == user_id, AssetClass.type == "stock")
            .all()
        )
        class_map = {ac.id: ac for ac in stock_classes}

        symbols_with_class = (
            db.query(Transaction.asset_symbol, Transaction.asset_class_id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_class_id.in_([ac.id for ac in stock_classes]),
            )
            .distinct()
            .all()
        )

        today = date.today()
        from_date = (today - timedelta(days=365)).isoformat()
        to_date = today.isoformat()

        for symbol, asset_class_id in symbols_with_class:
            ac = class_map.get(asset_class_id)
            if not ac:
                continue

            try:
                if symbol.endswith(".SA"):
                    raw_splits = self._brapi.get_splits(symbol)
                else:
                    raw_splits = self._finnhub.get_splits(symbol, from_date, to_date)

                for sp in raw_splits:
                    split_date = date.fromisoformat(sp["date"])
                    exists = (
                        db.query(StockSplit)
                        .filter_by(user_id=user_id, symbol=symbol, split_date=split_date)
                        .first()
                    )
                    if exists:
                        continue

                    db.add(StockSplit(
                        user_id=user_id,
                        symbol=symbol,
                        split_date=split_date,
                        from_factor=sp["fromFactor"],
                        to_factor=sp["toFactor"],
                        status="pending",
                        asset_class_id=asset_class_id,
                    ))
                    db.commit()
                    logger.info(f"Detected split for {symbol}: {sp['fromFactor']}:{sp['toFactor']} on {sp['date']}")

            except Exception:
                logger.exception(f"Failed to check splits for {symbol}")
                db.rollback()
            finally:
                if self._delay > 0:
                    time.sleep(self._delay)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && pytest tests/test_services/test_split_checker_scheduler.py -v`
Expected: All PASS

- [ ] **Step 4: Wire scheduler into main.py lifespan**

Add to `backend/app/main.py`:

```python
def _run_split_checker():
    from app.database import SessionLocal
    from app.providers.brapi import BrapiProvider
    from app.providers.finnhub import FinnhubProvider
    from app.services.split_checker_scheduler import SplitCheckerScheduler

    scheduler = SplitCheckerScheduler(
        finnhub_provider=FinnhubProvider(api_key=settings.finnhub_api_key, base_url=settings.finnhub_base_url),
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
    )

    db = SessionLocal()
    try:
        scheduler.check_all(db)
    except Exception:
        logger.exception("Scheduled split check failed")
    finally:
        db.close()
```

And in the lifespan function, after the fundamentals scorer block:
```python
if settings.enable_split_checker:
    bg_scheduler.add_job(
        _run_split_checker, "cron",
        hour=settings.split_checker_hour,
        id="split_checker",
    )
    logger.info(f"Split checker scheduled (daily at {settings.split_checker_hour}:00 UTC)")
```

- [ ] **Step 5: Run full backend tests**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/split_checker_scheduler.py backend/tests/test_services/test_split_checker_scheduler.py backend/app/main.py
git commit -m "feat: add split checker scheduler with daily detection"
```

---

## Chunk 6: Frontend

### Task 11: Frontend Types + API + Hook

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`
- Create: `frontend/src/hooks/useSplits.ts`

- [ ] **Step 1: Add StockSplit type**

Add to `frontend/src/types/index.ts`:
```typescript
export interface StockSplit {
  id: string;
  symbol: string;
  split_date: string;
  from_factor: number;
  to_factor: number;
  detected_at: string;
  current_quantity: number;
  new_quantity: number;
}
```

- [ ] **Step 2: Create useSplits hook**

```typescript
// frontend/src/hooks/useSplits.ts
import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { StockSplit } from "../types";

export function useSplits() {
  const [pendingSplits, setPendingSplits] = useState<StockSplit[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<StockSplit[]>("/splits/pending");
      setPendingSplits(res.data);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const applySplit = useCallback(async (splitId: string) => {
    await api.post(`/splits/${splitId}/apply`);
    await refresh();
  }, [refresh]);

  const dismissSplit = useCallback(async (splitId: string) => {
    await api.post(`/splits/${splitId}/dismiss`);
    await refresh();
  }, [refresh]);

  return { pendingSplits, loading, applySplit, dismissSplit, refresh };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useSplits.ts
git commit -m "feat: add StockSplit type and useSplits hook"
```

### Task 12: Dashboard Split Banner

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add split banner to Dashboard**

Import and use the `useSplits` hook in `Dashboard.tsx`. Add a banner section at the top of the `<div className="space-y-4">` after the `<h1>`:

```tsx
import { useSplits } from "../hooks/useSplits";

// Inside Dashboard component:
const { pendingSplits, applySplit, dismissSplit } = useSplits();

// In JSX, after <h1>:
{pendingSplits.length > 0 && (
  <div className="space-y-2">
    {pendingSplits.map((split) => (
      <div key={split.id} className="glass-card p-4 border border-yellow-500/30 bg-yellow-500/5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-text-primary font-medium">
              Stock split detected: {split.symbol} ({split.from_factor}:{split.to_factor} on{" "}
              {new Date(split.split_date).toLocaleDateString()})
            </p>
            <p className="text-text-muted text-sm mt-1">
              Your {split.current_quantity} shares will become {split.new_quantity} shares.
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <button
              onClick={() => applySplit(split.id)}
              className="px-3 py-1.5 text-sm rounded-lg bg-accent/20 text-accent hover:bg-accent/30 transition-colors"
            >
              Apply
            </button>
            <button
              onClick={() => dismissSplit(split.id)}
              className="px-3 py-1.5 text-sm rounded-lg bg-surface-card text-text-muted hover:text-text-primary transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    ))}
  </div>
)}
```

- [ ] **Step 2: Verify build passes**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add pending split banner to Dashboard"
```

---

## Chunk 7: Final Verification

### Task 13: Full Test Suite + Build

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && pytest -v`
Expected: All PASS

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors
