# Portfolio Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add portfolio performance charts, market overview page, asset detail page, and DARF tax report.

**Architecture:** Four independent features built sequentially. A1 (performance chart) adds a new model + scheduler + endpoint. C1 (market page) adds two endpoints reusing existing services. A2 (asset detail) is frontend-only. D2 (tax report) adds a new service + endpoint + page.

**Tech Stack:** FastAPI, SQLAlchemy, APScheduler, React 19, TypeScript, Recharts, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-10-portfolio-improvements-design.md`

---

## File Structure

### Backend — New Files
- `backend/app/models/portfolio_snapshot.py` — PortfolioSnapshot ORM model
- `backend/app/services/snapshot_scheduler.py` — daily snapshot job
- `backend/app/routers/market.py` — market indices + movers endpoints
- `backend/app/services/tax.py` — DARF tax calculation service
- `backend/app/routers/tax.py` — tax report endpoint
- `backend/tests/test_services/test_snapshot_scheduler.py`
- `backend/tests/test_routers/test_portfolio_history.py`
- `backend/tests/test_routers/test_market.py`
- `backend/tests/test_services/test_tax.py`
- `backend/tests/test_routers/test_tax.py`

### Backend — Modified Files
- `backend/app/models/__init__.py` — export PortfolioSnapshot
- `backend/app/config.py` — add snapshot_hour setting
- `backend/app/main.py` — register snapshot scheduler job, include market + tax routers
- `backend/app/routers/portfolio.py` — add history + latest snapshot endpoints

### Frontend — New Files
- `frontend/src/hooks/usePortfolioHistory.ts`
- `frontend/src/hooks/useMarketIndices.ts`
- `frontend/src/hooks/useMarketMovers.ts`
- `frontend/src/hooks/useAssetDetail.ts`
- `frontend/src/hooks/useTaxReport.ts`
- `frontend/src/pages/AssetDetail.tsx`
- `frontend/src/pages/Tax.tsx`

### Frontend — Modified Files
- `frontend/src/types/index.ts` — add new interfaces
- `frontend/src/components/PortfolioHeroCard.tsx` — real chart with period selector
- `frontend/src/pages/Market.tsx` — full market overview
- `frontend/src/components/HoldingsTable.tsx` — row click navigates to asset detail
- `frontend/src/components/TopNav.tsx` — add Tax tab
- `frontend/src/components/MobileNav.tsx` — add Tax tab
- `frontend/src/App.tsx` — add new routes

---

## Feature A1: Portfolio Performance Chart

### Task 1: PortfolioSnapshot Model

**Files:**
- Create: `backend/app/models/portfolio_snapshot.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_services/test_snapshot_scheduler.py`

- [ ] **Step 1: Write the model**

```python
# backend/app/models/portfolio_snapshot.py
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_snapshot_user_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_value_brl: Mapped[float] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Export from models/__init__.py**

Add to `backend/app/models/__init__.py`:
```python
from app.models.portfolio_snapshot import PortfolioSnapshot
```

- [ ] **Step 3: Write a test that the model can be created and queried**

```python
# backend/tests/test_services/test_snapshot_scheduler.py
import pytest
from datetime import date
from decimal import Decimal

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User


def _create_user(db):
    user = User(name="Test", email="snap@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestPortfolioSnapshotModel:
    def test_create_snapshot(self, db):
        user = _create_user(db)
        snap = PortfolioSnapshot(
            user_id=user.id,
            date=date(2026, 4, 10),
            total_value_brl=Decimal("247832.15"),
        )
        db.add(snap)
        db.commit()

        result = db.query(PortfolioSnapshot).filter_by(user_id=user.id).first()
        assert result is not None
        assert result.date == date(2026, 4, 10)
        assert float(result.total_value_brl) == pytest.approx(247832.15)

    def test_unique_constraint(self, db):
        user = _create_user(db)
        snap1 = PortfolioSnapshot(user_id=user.id, date=date(2026, 4, 10), total_value_brl=Decimal("100"))
        db.add(snap1)
        db.commit()

        snap2 = PortfolioSnapshot(user_id=user.id, date=date(2026, 4, 10), total_value_brl=Decimal("200"))
        db.add(snap2)
        with pytest.raises(Exception):
            db.commit()
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_snapshot_scheduler.py::TestPortfolioSnapshotModel -v`
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/portfolio_snapshot.py backend/app/models/__init__.py backend/tests/test_services/test_snapshot_scheduler.py
git commit -m "feat: add PortfolioSnapshot model"
```

---

### Task 2: Snapshot Scheduler Service

**Files:**
- Create: `backend/app/services/snapshot_scheduler.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_services/test_snapshot_scheduler.py`

- [ ] **Step 1: Add config setting**

Add to `backend/app/config.py` Settings class:
```python
    enable_snapshot_scheduler: bool = True
    snapshot_hour: int = 18
```

- [ ] **Step 2: Write failing test for the scheduler**

Append to `backend/tests/test_services/test_snapshot_scheduler.py`:

```python
from unittest.mock import MagicMock, patch
from app.services.snapshot_scheduler import SnapshotScheduler
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction


def _setup_user_with_holdings(db):
    user = User(name="Test", email="sched@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)

    ac = AssetClass(user_id=user.id, name="US Stocks", country="US", type="stock", target_weight=100.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=100.0)
    db.add(aw)
    db.commit()

    tx = Transaction(
        user_id=user.id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10,
        unit_price=Decimal("150.00"),
        total_value=Decimal("1500.00"),
        currency="USD",
        date=date(2026, 1, 1),
    )
    db.add(tx)
    db.commit()
    return user


class TestSnapshotScheduler:
    def test_creates_snapshot_for_user(self, db):
        user = _setup_user_with_holdings(db)
        mock_market = MagicMock()
        mock_market.get_quote_safe.return_value = {
            "price": Decimal("160.00"),
            "currency": "USD",
            "name": "Apple",
        }

        with patch("app.services.snapshot_scheduler.get_market_data_service", return_value=mock_market):
            with patch("app.services.snapshot_scheduler._get_exchange_rate", return_value=Decimal("5.10")):
                scheduler = SnapshotScheduler()
                scheduler.take_snapshots(db)

        snap = db.query(PortfolioSnapshot).filter_by(user_id=user.id).first()
        assert snap is not None
        # 10 shares * 160 USD * 5.10 BRL/USD = 8160.00
        assert float(snap.total_value_brl) == pytest.approx(8160.0, rel=0.01)

    def test_skips_if_already_exists(self, db):
        user = _setup_user_with_holdings(db)
        existing = PortfolioSnapshot(
            user_id=user.id, date=date.today(), total_value_brl=Decimal("999")
        )
        db.add(existing)
        db.commit()

        mock_market = MagicMock()
        with patch("app.services.snapshot_scheduler.get_market_data_service", return_value=mock_market):
            scheduler = SnapshotScheduler()
            scheduler.take_snapshots(db)

        snaps = db.query(PortfolioSnapshot).filter_by(user_id=user.id).all()
        assert len(snaps) == 1
        assert float(snaps[0].total_value_brl) == pytest.approx(999.0)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_services/test_snapshot_scheduler.py::TestSnapshotScheduler -v`
Expected: FAIL (import error — module not found)

- [ ] **Step 4: Write the scheduler service**

```python
# backend/app/services/snapshot_scheduler.py
import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User
from app.services.market_data import get_market_data_service
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)


def _get_exchange_rate(market_data) -> Decimal:
    """Get USD→BRL exchange rate."""
    try:
        rate = market_data.get_exchange_rate("USD-BRL")
        return Decimal(str(rate))
    except Exception:
        logger.warning("Failed to fetch USD-BRL rate, using 1.0")
        return Decimal("1")


class SnapshotScheduler:
    def take_snapshots(self, db: Session) -> None:
        today = date.today()
        market_data = get_market_data_service()
        exchange_rate = _get_exchange_rate(market_data)

        users = db.query(User).all()
        for user in users:
            existing = (
                db.query(PortfolioSnapshot)
                .filter_by(user_id=user.id, date=today)
                .first()
            )
            if existing:
                logger.info(f"Snapshot already exists for user {user.id} on {today}")
                continue

            try:
                svc = PortfolioService(db)
                holdings = svc.get_holdings(user.id)
                if not holdings:
                    continue

                class_map = svc._build_class_map(user.id)
                weight_map = svc._build_weight_map()
                enriched = PortfolioService.enrich_holdings(
                    holdings, class_map, weight_map, market_data, db
                )

                total_brl = Decimal("0")
                for h in enriched:
                    cv = h.get("current_value")
                    if cv is None:
                        continue
                    amount = Decimal(str(cv.amount)) if hasattr(cv, "amount") else Decimal(str(cv.get("amount", 0)))
                    currency = cv.currency if hasattr(cv, "currency") else cv.get("currency", "BRL")
                    currency_code = currency.code if hasattr(currency, "code") else str(currency)
                    if currency_code == "USD":
                        total_brl += amount * exchange_rate
                    else:
                        total_brl += amount

                snap = PortfolioSnapshot(
                    user_id=user.id,
                    date=today,
                    total_value_brl=total_brl,
                )
                db.add(snap)
                db.commit()
                logger.info(f"Snapshot created for user {user.id}: R$ {total_brl}")
            except Exception as e:
                logger.error(f"Failed to create snapshot for user {user.id}: {e}")
                db.rollback()
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_snapshot_scheduler.py::TestSnapshotScheduler -v`
Expected: 2 PASSED

- [ ] **Step 6: Register scheduler in main.py**

Add to `backend/app/main.py` — new job function (after existing `_run_split_checker`):

```python
def _run_snapshot():
    from app.database import SessionLocal
    from app.services.snapshot_scheduler import SnapshotScheduler
    db = SessionLocal()
    try:
        SnapshotScheduler().take_snapshots(db)
    finally:
        db.close()
```

Add inside the `if settings.enable_scheduler:` block in `lifespan()`, after the split_checker job:

```python
        if settings.enable_snapshot_scheduler:
            bg_scheduler.add_job(
                _run_snapshot, "cron",
                hour=settings.snapshot_hour,
                id="portfolio_snapshot",
            )
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/snapshot_scheduler.py backend/app/config.py backend/app/main.py backend/tests/test_services/test_snapshot_scheduler.py
git commit -m "feat: add portfolio snapshot scheduler"
```

---

### Task 3: Portfolio History Endpoints

**Files:**
- Modify: `backend/app/routers/portfolio.py`
- Test: `backend/tests/test_routers/test_portfolio_history.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_routers/test_portfolio_history.py
import pytest
from datetime import date, timedelta
from decimal import Decimal

from app.models.user import User
from app.models.portfolio_snapshot import PortfolioSnapshot


def _create_user(db):
    user = User(name="Test", email="hist@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_snapshots(db, user_id, days_back=60):
    """Create daily snapshots going back N days."""
    today = date.today()
    for i in range(days_back):
        d = today - timedelta(days=i)
        snap = PortfolioSnapshot(
            user_id=user_id,
            date=d,
            total_value_brl=Decimal(str(100000 + i * 100)),
        )
        db.add(snap)
    db.commit()


class TestPortfolioHistory:
    def test_history_1w(self, client, db, default_user, auth_headers):
        _create_snapshots(db, default_user.id, days_back=30)
        resp = client.get("/api/portfolio/history?period=1W", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 7
        assert "date" in data[0]
        assert "total_value_brl" in data[0]

    def test_history_1m(self, client, db, default_user, auth_headers):
        _create_snapshots(db, default_user.id, days_back=60)
        resp = client.get("/api/portfolio/history?period=1M", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 30

    def test_history_1y(self, client, db, default_user, auth_headers):
        _create_snapshots(db, default_user.id, days_back=60)
        resp = client.get("/api/portfolio/history?period=1Y", headers=auth_headers)
        assert resp.status_code == 200

    def test_history_all(self, client, db, default_user, auth_headers):
        _create_snapshots(db, default_user.id, days_back=60)
        resp = client.get("/api/portfolio/history?period=ALL", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 60

    def test_latest_snapshot(self, client, db, default_user, auth_headers):
        yesterday = date.today() - timedelta(days=1)
        snap = PortfolioSnapshot(
            user_id=default_user.id,
            date=yesterday,
            total_value_brl=Decimal("250000"),
        )
        db.add(snap)
        db.commit()

        resp = client.get("/api/portfolio/snapshot/latest", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value_brl"] == "250000.00000000"

    def test_latest_snapshot_empty(self, client, db, default_user, auth_headers):
        resp = client.get("/api/portfolio/snapshot/latest", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routers/test_portfolio_history.py -v`
Expected: FAIL (404 — endpoints don't exist)

- [ ] **Step 3: Add endpoints to portfolio router**

Add to `backend/app/routers/portfolio.py`:

```python
from datetime import date, timedelta
from app.models.portfolio_snapshot import PortfolioSnapshot
```

Add these endpoints (after existing endpoints):

```python
@router.get("/history")
@limiter.limit(PORTFOLIO_LIMIT)
def get_portfolio_history(
    request: Request,
    period: str = Query("1M"),
    user_id: str = Header(alias="X-User-Id", default=""),
    db: Session = Depends(get_db),
):
    if not user_id:
        user_id = _get_user_from_token(request)

    days_map = {"1W": 7, "1M": 30, "1Y": 365}
    if period == "ALL":
        snapshots = (
            db.query(PortfolioSnapshot)
            .filter_by(user_id=user_id)
            .order_by(PortfolioSnapshot.date.asc())
            .all()
        )
    else:
        days = days_map.get(period, 30)
        since = date.today() - timedelta(days=days)
        snapshots = (
            db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.date >= since,
            )
            .order_by(PortfolioSnapshot.date.asc())
            .all()
        )

    return [
        {"date": str(s.date), "total_value_brl": str(s.total_value_brl)}
        for s in snapshots
    ]


@router.get("/snapshot/latest")
@limiter.limit(PORTFOLIO_LIMIT)
def get_latest_snapshot(
    request: Request,
    user_id: str = Header(alias="X-User-Id", default=""),
    db: Session = Depends(get_db),
):
    if not user_id:
        user_id = _get_user_from_token(request)

    snapshot = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.date < date.today(),
        )
        .order_by(PortfolioSnapshot.date.desc())
        .first()
    )

    if not snapshot:
        return None

    return {"date": str(snapshot.date), "total_value_brl": str(snapshot.total_value_brl)}
```

Note: Check how `_get_user_from_token` or `user_id` header is handled in the existing portfolio router and follow the same pattern.

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_routers/test_portfolio_history.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/portfolio.py backend/tests/test_routers/test_portfolio_history.py
git commit -m "feat: add portfolio history and latest snapshot endpoints"
```

---

### Task 4: Frontend — usePortfolioHistory Hook + Types

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/hooks/usePortfolioHistory.ts`

- [ ] **Step 1: Add types**

Add to `frontend/src/types/index.ts`:

```typescript
export interface PortfolioSnapshot {
  date: string;
  total_value_brl: string;
}
```

- [ ] **Step 2: Create the hook**

```typescript
// frontend/src/hooks/usePortfolioHistory.ts
import { useState, useEffect } from "react";
import api from "../services/api";
import type { PortfolioSnapshot } from "../types";

type Period = "1D" | "1W" | "1M" | "1Y" | "ALL";

let _historyCache: Record<string, PortfolioSnapshot[]> = {};
let _latestCache: PortfolioSnapshot | null = null;

export function usePortfolioHistory(period: Period) {
  const [history, setHistory] = useState<PortfolioSnapshot[]>(_historyCache[period] || []);
  const [latestSnapshot, setLatestSnapshot] = useState<PortfolioSnapshot | null>(_latestCache);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      setError("");
      try {
        if (period === "1D") {
          const resp = await api.get<PortfolioSnapshot | null>("/portfolio/snapshot/latest");
          _latestCache = resp.data;
          setLatestSnapshot(resp.data);
        } else {
          const resp = await api.get<PortfolioSnapshot[]>("/portfolio/history", {
            params: { period },
          });
          _historyCache[period] = resp.data;
          setHistory(resp.data);
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load history");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [period]);

  return { history, latestSnapshot, loading, error };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/usePortfolioHistory.ts
git commit -m "feat: add usePortfolioHistory hook and PortfolioSnapshot type"
```

---

### Task 5: PortfolioHeroCard — Real Chart

**Files:**
- Modify: `frontend/src/components/PortfolioHeroCard.tsx`

- [ ] **Step 1: Update PortfolioHeroCard with real chart and period selector**

Replace the entire component. Key changes:
- Add `useState` for `selectedPeriod`
- Import `usePortfolioHistory`
- Import Recharts `AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer`
- Replace SVG placeholder with Recharts AreaChart when period != "1D"
- For "1D": show delta number from latest snapshot vs current grandTotalBRL
- Enable all period buttons (remove disabled/tooltip logic)
- Chart line: green (`#34c759`) when gain, red (`#ff3b30`) when loss
- Gradient fill below line

The component should:
1. Accept `grandTotalBRL` and `loading` props (unchanged)
2. Use `usePortfolioHistory(selectedPeriod)` internally
3. For 1D: compute `delta = grandTotalBRL - parseFloat(latestSnapshot.total_value_brl)` and show as "+R$ X (Y%)"
4. For other periods: render AreaChart from history data, mapping `total_value_brl` as Y axis
5. Period buttons: all clickable, active one gets `bg-[rgba(255,255,255,0.1)]` style

```tsx
// Key additions to imports:
import { useState } from "react";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import { usePortfolioHistory } from "../hooks/usePortfolioHistory";

// Inside component:
const [selectedPeriod, setSelectedPeriod] = useState<"1D" | "1W" | "1M" | "1Y" | "ALL">("1M");
const { history, latestSnapshot, loading: historyLoading } = usePortfolioHistory(selectedPeriod);

// Chart data transformation:
const chartData = history.map((s) => ({
  date: s.date,
  value: parseFloat(s.total_value_brl),
}));

const periodGain = chartData.length >= 2
  ? chartData[chartData.length - 1].value - chartData[0].value
  : 0;
const chartColor = periodGain >= 0 ? "#34c759" : "#ff3b30";

// For 1D delta:
const yesterdayValue = latestSnapshot ? parseFloat(latestSnapshot.total_value_brl) : null;
const dayDelta = yesterdayValue !== null ? grandTotalBRL - yesterdayValue : null;
const dayDeltaPct = yesterdayValue && yesterdayValue > 0
  ? ((dayDelta ?? 0) / yesterdayValue) * 100
  : null;
```

For the chart section, replace the SVG placeholder with:

```tsx
{selectedPeriod === "1D" ? (
  <div className="h-36 md:h-48 flex items-center justify-center">
    {dayDelta !== null ? (
      <div className="text-center">
        <p className={`text-2xl font-bold ${dayDelta >= 0 ? "text-[#34c759]" : "text-[#ff3b30]"}`}>
          {dayDelta >= 0 ? "+" : ""}R$ {Math.abs(dayDelta).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        {dayDeltaPct !== null && (
          <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
            {dayDeltaPct >= 0 ? "+" : ""}{dayDeltaPct.toFixed(2)}% today
          </p>
        )}
      </div>
    ) : (
      <p style={{ color: "var(--text-tertiary)" }}>No snapshot yet</p>
    )}
  </div>
) : historyLoading ? (
  <div className="h-36 md:h-48 animate-pulse rounded" style={{ background: "var(--surface-hover)" }} />
) : chartData.length > 0 ? (
  <div className="h-36 md:h-48">
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={chartColor} stopOpacity={0.15} />
            <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="date" hide />
        <Tooltip
          contentStyle={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: "0.8rem" }}
          labelFormatter={(label) => new Date(label + "T00:00:00").toLocaleDateString("pt-BR")}
          formatter={(value: number) => [`R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`, "Portfolio"]}
        />
        <Area type="monotone" dataKey="value" stroke={chartColor} strokeWidth={2} fill="url(#chartGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  </div>
) : (
  <div className="h-36 md:h-48 flex items-center justify-center">
    <p style={{ color: "var(--text-tertiary)" }}>No history data yet</p>
  </div>
)}
```

For the period buttons, replace the disabled logic — all buttons should be clickable:

```tsx
{["1D", "1W", "1M", "1Y", "ALL"].map((p) => (
  <button
    key={p}
    onClick={() => setSelectedPeriod(p as typeof selectedPeriod)}
    className="px-3 py-1 rounded-full text-xs font-medium transition-colors"
    style={{
      background: selectedPeriod === p ? "rgba(255,255,255,0.1)" : "transparent",
      color: selectedPeriod === p ? "var(--blue)" : "var(--text-secondary)",
    }}
  >
    {p}
  </button>
))}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PortfolioHeroCard.tsx
git commit -m "feat: wire up portfolio hero card with real performance chart"
```

---

## Feature C1: Market Overview Page

### Task 6: Market Indices Endpoint

**Files:**
- Create: `backend/app/routers/market.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers/test_market.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_routers/test_market.py
import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from datetime import date


def _create_user(db):
    user = User(name="Test", email="market@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestMarketIndices:
    def test_get_indices(self, client, db, default_user, auth_headers):
        mock_market = MagicMock()
        mock_market.get_stock_quote.side_effect = lambda sym, country, db, **kw: {
            "price": Decimal("128450"),
            "name": sym,
            "currency": "BRL" if country == "BR" else "USD",
            "change_pct": 1.2,
        }
        mock_market.get_exchange_rate.return_value = 5.12

        with patch("app.routers.market.get_market_data_service", return_value=mock_market):
            resp = client.get("/api/market/indices", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        symbols = [d["symbol"] for d in data]
        assert "IBOV" in symbols or "^BVSP" in symbols
        assert "USD/BRL" in symbols


class TestMarketMovers:
    def test_get_movers(self, client, db, default_user, auth_headers):
        ac = AssetClass(user_id=default_user.id, name="US", country="US", type="stock", target_weight=100.0)
        db.add(ac)
        db.commit()
        db.refresh(ac)

        for sym, qty, price in [("AAPL", 10, "150"), ("GOOG", 5, "200"), ("MSFT", 8, "300"), ("TSLA", 3, "250")]:
            tx = Transaction(
                user_id=default_user.id, asset_class_id=ac.id, asset_symbol=sym,
                type="buy", quantity=qty, unit_price=Decimal(price),
                total_value=Decimal(str(int(qty) * int(price))),
                currency="USD", date=date(2026, 1, 1),
            )
            db.add(tx)
        db.commit()

        mock_market = MagicMock()
        changes = {"AAPL": 3.5, "GOOG": -2.1, "MSFT": 1.0, "TSLA": -0.5}
        mock_market.get_quote_safe.side_effect = lambda sym, country, db, **kw: {
            "price": Decimal("100"),
            "name": sym,
            "currency": "USD",
            "change_pct": changes.get(sym, 0),
        }

        with patch("app.routers.market.get_market_data_service", return_value=mock_market):
            resp = client.get("/api/market/movers", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert "gainers" in data
        assert "losers" in data
        assert len(data["gainers"]) <= 3
        assert len(data["losers"]) <= 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routers/test_market.py -v`
Expected: FAIL (import error / 404)

- [ ] **Step 3: Create market router**

```python
# backend/app/routers/market.py
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.market_data import get_market_data_service
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/market", tags=["market"])
limiter = Limiter(key_func=get_remote_address)
MARKET_LIMIT = "30/minute"


@router.get("/indices")
@limiter.limit(MARKET_LIMIT)
def get_indices(request: Request, db: Session = Depends(get_db)):
    market_data = get_market_data_service()

    indices = []

    # IBOV
    try:
        ibov = market_data.get_stock_quote("^BVSP", "BR", db)
        indices.append({
            "symbol": "IBOV",
            "name": "Ibovespa",
            "value": str(ibov.get("price", 0)),
            "change_pct": ibov.get("change_pct", 0),
        })
    except Exception:
        indices.append({"symbol": "IBOV", "name": "Ibovespa", "value": None, "change_pct": None})

    # S&P 500 (via SPY ETF as proxy)
    try:
        spy = market_data.get_stock_quote("SPY", "US", db)
        indices.append({
            "symbol": "S&P 500",
            "name": "S&P 500",
            "value": str(spy.get("price", 0)),
            "change_pct": spy.get("change_pct", 0),
        })
    except Exception:
        indices.append({"symbol": "S&P 500", "name": "S&P 500", "value": None, "change_pct": None})

    # USD/BRL
    try:
        rate = market_data.get_exchange_rate("USD-BRL")
        indices.append({
            "symbol": "USD/BRL",
            "name": "Dólar",
            "value": str(rate),
            "change_pct": None,
        })
    except Exception:
        indices.append({"symbol": "USD/BRL", "name": "Dólar", "value": None, "change_pct": None})

    return indices


@router.get("/movers")
@limiter.limit(MARKET_LIMIT)
def get_movers(
    request: Request,
    user_id: str = Header(alias="X-User-Id", default=""),
    db: Session = Depends(get_db),
):
    market_data = get_market_data_service()
    svc = PortfolioService(db)
    holdings = svc.get_holdings(user_id)

    if not holdings:
        return {"gainers": [], "losers": []}

    class_map = svc._build_class_map(user_id)
    movers = []

    for h in holdings:
        symbol = h["symbol"]
        ac = class_map.get(h["asset_class_id"], {})
        country = ac.get("country", "US")
        quote = market_data.get_quote_safe(symbol, country, db)
        if quote and quote.get("change_pct") is not None:
            movers.append({
                "symbol": symbol,
                "name": quote.get("name", symbol),
                "change_pct": float(quote["change_pct"]),
                "current_price": str(quote.get("price", 0)),
            })

    movers.sort(key=lambda m: m["change_pct"], reverse=True)
    gainers = [m for m in movers if m["change_pct"] > 0][:3]
    losers = [m for m in movers if m["change_pct"] < 0][-3:]
    losers.sort(key=lambda m: m["change_pct"])

    return {"gainers": gainers, "losers": losers}
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/app/main.py` imports and router includes:

```python
from app.routers import market
app.include_router(market.router)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_routers/test_market.py -v`
Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/market.py backend/tests/test_routers/test_market.py backend/app/main.py
git commit -m "feat: add market indices and movers endpoints"
```

---

### Task 7: Frontend — Market Page

**Files:**
- Create: `frontend/src/hooks/useMarketIndices.ts`
- Create: `frontend/src/hooks/useMarketMovers.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/pages/Market.tsx`

- [ ] **Step 1: Add types**

Add to `frontend/src/types/index.ts`:

```typescript
export interface MarketIndex {
  symbol: string;
  name: string;
  value: string | null;
  change_pct: number | null;
}

export interface MarketMover {
  symbol: string;
  name: string;
  change_pct: number;
  current_price: string;
}

export interface MarketMoversResponse {
  gainers: MarketMover[];
  losers: MarketMover[];
}
```

- [ ] **Step 2: Create useMarketIndices hook**

```typescript
// frontend/src/hooks/useMarketIndices.ts
import { useState, useEffect } from "react";
import api from "../services/api";
import type { MarketIndex } from "../types";

let _cache: MarketIndex[] | null = null;
let _cacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

export function useMarketIndices() {
  const [indices, setIndices] = useState<MarketIndex[]>(_cache || []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      if (_cache && Date.now() - _cacheTime < CACHE_TTL) {
        setIndices(_cache);
        return;
      }
      setLoading(true);
      try {
        const resp = await api.get<MarketIndex[]>("/market/indices");
        _cache = resp.data;
        _cacheTime = Date.now();
        setIndices(resp.data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load indices");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return { indices, loading, error };
}
```

- [ ] **Step 3: Create useMarketMovers hook**

```typescript
// frontend/src/hooks/useMarketMovers.ts
import { useState, useEffect } from "react";
import api from "../services/api";
import type { MarketMoversResponse } from "../types";

let _cache: MarketMoversResponse | null = null;
let _cacheTime = 0;
const CACHE_TTL = 5 * 60 * 1000;

export function useMarketMovers() {
  const [movers, setMovers] = useState<MarketMoversResponse>(_cache || { gainers: [], losers: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      if (_cache && Date.now() - _cacheTime < CACHE_TTL) {
        setMovers(_cache);
        return;
      }
      setLoading(true);
      try {
        const resp = await api.get<MarketMoversResponse>("/market/movers");
        _cache = resp.data;
        _cacheTime = Date.now();
        setMovers(resp.data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load movers");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return { movers, loading, error };
}
```

- [ ] **Step 4: Rewrite Market page**

Replace `frontend/src/pages/Market.tsx` with the full market overview:

```tsx
// frontend/src/pages/Market.tsx
import { useMarketIndices } from "../hooks/useMarketIndices";
import { useMarketMovers } from "../hooks/useMarketMovers";
import { useNews } from "../hooks/useNews";
import type { MarketMover } from "../types";

function IndexCard({ symbol, value, change_pct }: { symbol: string; value: string | null; change_pct: number | null }) {
  const changeColor = change_pct === null ? "var(--text-tertiary)" : change_pct >= 0 ? "#34c759" : "#ff3b30";
  return (
    <div className="card flex-1 min-w-[120px]">
      <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>{symbol}</p>
      <p className="text-lg font-semibold mt-1">
        {value ? parseFloat(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) : "—"}
      </p>
      {change_pct !== null && (
        <p className="text-xs mt-1" style={{ color: changeColor }}>
          {change_pct >= 0 ? "+" : ""}{change_pct.toFixed(2)}%
        </p>
      )}
    </div>
  );
}

function MoverRow({ mover }: { mover: MarketMover }) {
  const color = mover.change_pct >= 0 ? "#34c759" : "#ff3b30";
  return (
    <div className="flex justify-between items-center py-2" style={{ borderBottom: "1px solid var(--border)" }}>
      <div>
        <span className="font-medium">{mover.symbol}</span>
        <span className="text-xs ml-2" style={{ color: "var(--text-tertiary)" }}>{mover.name}</span>
      </div>
      <span className="text-sm font-medium" style={{ color }}>
        {mover.change_pct >= 0 ? "+" : ""}{mover.change_pct.toFixed(2)}%
      </span>
    </div>
  );
}

export default function Market() {
  const { indices, loading: indicesLoading } = useMarketIndices();
  const { movers, loading: moversLoading } = useMarketMovers();
  const { news, loading: newsLoading } = useNews();

  return (
    <div className="space-y-6 py-6">
      <h1 className="text-2xl font-bold">Market Overview</h1>

      {/* Index Cards */}
      <div className="flex gap-3 flex-wrap">
        {indicesLoading ? (
          [1, 2, 3].map((i) => (
            <div key={i} className="card flex-1 min-w-[120px] h-20 animate-pulse" style={{ background: "var(--surface-hover)" }} />
          ))
        ) : (
          indices.map((idx) => (
            <IndexCard key={idx.symbol} symbol={idx.symbol} value={idx.value} change_pct={idx.change_pct} />
          ))
        )}
      </div>

      {/* Top Movers */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Your Portfolio Movers</h2>
        {moversLoading ? (
          <div className="h-32 animate-pulse rounded" style={{ background: "var(--surface-hover)" }} />
        ) : movers.gainers.length === 0 && movers.losers.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>No holdings with price changes today.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {movers.gainers.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide mb-2" style={{ color: "var(--text-tertiary)" }}>Gainers</p>
                {movers.gainers.map((m) => <MoverRow key={m.symbol} mover={m} />)}
              </div>
            )}
            {movers.losers.length > 0 && (
              <div>
                <p className="text-xs uppercase tracking-wide mb-2" style={{ color: "var(--text-tertiary)" }}>Losers</p>
                {movers.losers.map((m) => <MoverRow key={m.symbol} mover={m} />)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* News Feed */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Market News</h2>
        {newsLoading ? (
          <div className="h-48 animate-pulse rounded" style={{ background: "var(--surface-hover)" }} />
        ) : !news || news.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>No news available.</p>
        ) : (
          <div className="space-y-0">
            {news.map((item: { id: number; url: string; source: string; headline: string; summary: string; datetime: number }, i: number) => (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block py-3 hover:opacity-80 transition-opacity"
                style={{ borderBottom: i < news.length - 1 ? "1px solid var(--border)" : "none" }}
              >
                <div className="flex items-center gap-2 text-xs mb-1" style={{ color: "var(--text-tertiary)" }}>
                  <span>{item.source}</span>
                  <span>·</span>
                  <span>{new Date(item.datetime * 1000).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>
                </div>
                <p className="font-medium text-sm line-clamp-2">{item.headline}</p>
                <p className="text-xs mt-1 line-clamp-2" style={{ color: "var(--text-secondary)" }}>{item.summary}</p>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useMarketIndices.ts frontend/src/hooks/useMarketMovers.ts frontend/src/types/index.ts frontend/src/pages/Market.tsx
git commit -m "feat: build market overview page with indices, movers, and news"
```

---

## Feature A2: Asset Detail Page

### Task 8: Frontend — useAssetDetail Hook

**Files:**
- Create: `frontend/src/hooks/useAssetDetail.ts`

- [ ] **Step 1: Create the hook**

```typescript
// frontend/src/hooks/useAssetDetail.ts
import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import type { Holding, Transaction, DividendHistoryItem, FundamentalsDetail } from "../types";

interface PricePoint {
  date: string;
  price: { amount: string; currency: string };
}

type Period = "1W" | "1M" | "3M" | "1Y" | "ALL";

const PERIOD_MAP: Record<Period, string | number> = {
  "1W": "5d",
  "1M": "1mo",
  "3M": "3mo",
  "1Y": "1y",
  "ALL": "max",
};

export function useAssetDetail(
  symbol: string,
  country: string,
  assetClassId: string,
  type: string,
) {
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);
  const [holding, setHolding] = useState<Holding | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [dividends, setDividends] = useState<DividendHistoryItem[]>([]);
  const [fundamentals, setFundamentals] = useState<FundamentalsDetail | null>(null);
  const [period, setPeriod] = useState<Period>("1M");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Fetch price history when period changes
  useEffect(() => {
    async function fetchHistory() {
      try {
        if (type === "crypto") {
          const days = { "1W": 7, "1M": 30, "3M": 90, "1Y": 365, "ALL": 1825 }[period];
          const resp = await api.get<PricePoint[]>(`/crypto/${symbol}/history`, { params: { days } });
          setPriceHistory(resp.data);
        } else {
          const periodParam = PERIOD_MAP[period];
          const endpoint = country === "BR"
            ? `/stocks/br/${symbol}/history`
            : `/stocks/us/${symbol}/history`;
          const resp = await api.get<PricePoint[]>(endpoint, { params: { period: periodParam } });
          setPriceHistory(resp.data);
        }
      } catch {
        setPriceHistory([]);
      }
    }
    fetchHistory();
  }, [symbol, country, type, period]);

  // Fetch static data once
  useEffect(() => {
    async function fetchAll() {
      setLoading(true);
      setError("");
      try {
        const [holdingsResp, txResp, divResp] = await Promise.all([
          api.get<Holding[]>("/portfolio/summary", { params: { live: true } }),
          api.get<Transaction[]>("/transactions", { params: { symbol } }),
          api.get<{ items: DividendHistoryItem[] }>("/dividends/history", { params: { asset_class_id: assetClassId } }).catch(() => ({ data: { items: [] } })),
        ]);

        const h = holdingsResp.data.find((h) => h.symbol === symbol) || null;
        setHolding(h);
        setTransactions(txResp.data);
        setDividends(divResp.data.items?.filter((d) => d.symbol === symbol) || []);

        // Fundamentals (only for stocks)
        if (type === "stock") {
          try {
            const fResp = await api.get<FundamentalsDetail>(`/fundamentals/${symbol}`);
            setFundamentals(fResp.data);
          } catch {
            setFundamentals(null);
          }
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load asset detail");
      } finally {
        setLoading(false);
      }
    }
    fetchAll();
  }, [symbol, assetClassId, type]);

  const changePeriod = useCallback((p: Period) => setPeriod(p), []);

  return { priceHistory, holding, transactions, dividends, fundamentals, period, changePeriod, loading, error };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/useAssetDetail.ts
git commit -m "feat: add useAssetDetail hook"
```

---

### Task 9: Asset Detail Page + Routing

**Files:**
- Create: `frontend/src/pages/AssetDetail.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/HoldingsTable.tsx`

- [ ] **Step 1: Create AssetDetail page**

```tsx
// frontend/src/pages/AssetDetail.tsx
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useAssetDetail } from "../hooks/useAssetDetail";

const SCORE_COLORS: Record<string, string> = { green: "#34c759", yellow: "#ff9f0a", red: "#ff3b30" };

export default function AssetDetail() {
  const { assetClassId, symbol } = useParams<{ assetClassId: string; symbol: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const country = searchParams.get("country") || "US";
  const type = searchParams.get("type") || "stock";

  const { priceHistory, holding, transactions, dividends, fundamentals, period, changePeriod, loading, error } = useAssetDetail(
    symbol!, country, assetClassId!, type,
  );

  const chartData = priceHistory.map((p) => ({
    date: p.date,
    price: parseFloat(p.price.amount),
  }));

  const periodGain = chartData.length >= 2 ? chartData[chartData.length - 1].price - chartData[0].price : 0;
  const chartColor = periodGain >= 0 ? "#34c759" : "#ff3b30";

  const currentPrice = holding?.current_price ? parseFloat(holding.current_price.amount) : null;
  const avgCost = holding?.avg_price ? parseFloat(holding.avg_price.amount) : null;
  const gainLoss = holding?.gain_loss ? parseFloat(holding.gain_loss.amount) : null;
  const gainPct = avgCost && holding?.quantity ? ((currentPrice ?? 0) - avgCost) / avgCost * 100 : null;
  const currency = holding?.current_price?.currency || holding?.total_cost?.currency || "BRL";

  if (error) {
    return (
      <div className="py-6">
        <button onClick={() => navigate(-1)} className="text-sm mb-4" style={{ color: "var(--blue)" }}>← Back</button>
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 py-6">
      {/* Header */}
      <div>
        <button onClick={() => navigate(`/portfolio/${assetClassId}`)} className="text-sm mb-2" style={{ color: "var(--blue)" }}>
          ← Back to Holdings
        </button>
        <div className="flex items-baseline gap-3">
          <h1 className="text-2xl font-bold">{symbol}</h1>
          {currentPrice !== null && (
            <span className="text-lg" style={{ color: "var(--text-secondary)" }}>
              {currency === "BRL" ? "R$ " : "$ "}{currentPrice.toLocaleString(currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          )}
        </div>
      </div>

      {/* Price Chart */}
      <div className="card">
        <div className="flex gap-2 mb-4">
          {(["1W", "1M", "3M", "1Y", "ALL"] as const).map((p) => (
            <button
              key={p}
              onClick={() => changePeriod(p)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-colors"
              style={{
                background: period === p ? "rgba(255,255,255,0.1)" : "transparent",
                color: period === p ? "var(--blue)" : "var(--text-secondary)",
              }}
            >
              {p}
            </button>
          ))}
        </div>
        {chartData.length > 0 ? (
          <div className="h-48 md:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="assetGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={chartColor} stopOpacity={0.15} />
                    <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" hide />
                <Tooltip
                  contentStyle={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: 8, fontSize: "0.8rem" }}
                  labelFormatter={(label) => new Date(label + "T00:00:00").toLocaleDateString("pt-BR")}
                  formatter={(value: number) => [`${currency === "BRL" ? "R$ " : "$ "}${value.toLocaleString(currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2 })}`, "Price"]}
                />
                <Area type="monotone" dataKey="price" stroke={chartColor} strokeWidth={2} fill="url(#assetGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-48 flex items-center justify-center">
            <p style={{ color: "var(--text-tertiary)" }}>{loading ? "Loading..." : "No price data available"}</p>
          </div>
        )}
      </div>

      {/* Key Stats */}
      {holding && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card">
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Quantity</p>
            <p className="text-lg font-semibold mt-1">{holding.quantity?.toLocaleString("pt-BR") ?? "—"}</p>
          </div>
          <div className="card">
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Avg Cost</p>
            <p className="text-lg font-semibold mt-1">
              {avgCost !== null ? `${currency === "BRL" ? "R$ " : "$ "}${avgCost.toLocaleString(currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
            </p>
          </div>
          <div className="card">
            <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Total Gain/Loss</p>
            <p className={`text-lg font-semibold mt-1 ${gainLoss !== null && gainLoss >= 0 ? "text-[#34c759]" : "text-[#ff3b30]"}`}>
              {gainLoss !== null ? `${gainLoss >= 0 ? "+" : ""}${currency === "BRL" ? "R$ " : "$ "}${Math.abs(gainLoss).toLocaleString(currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2 })}` : "—"}
              {gainPct !== null && <span className="text-xs ml-1">({gainPct >= 0 ? "+" : ""}{gainPct.toFixed(1)}%)</span>}
            </p>
          </div>
          {fundamentals && (
            <div className="card">
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Fundamentals</p>
              <p className="text-lg font-semibold mt-1">
                <span style={{ color: SCORE_COLORS[fundamentals.profit_rating] || "var(--text-primary)" }}>
                  {fundamentals.composite_score}/100
                </span>
              </p>
            </div>
          )}
        </div>
      )}

      {/* Transactions */}
      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Transactions</h2>
        {transactions.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)" }}>No transactions found.</p>
        ) : (
          <div className="space-y-2">
            {transactions.map((tx) => {
              const typeColor = tx.type === "buy" ? "#34c759" : tx.type === "sell" ? "#ff3b30" : "var(--blue)";
              return (
                <div key={tx.id} className="flex justify-between items-center py-2" style={{ borderBottom: "1px solid var(--border)" }}>
                  <div>
                    <span className="text-xs font-medium uppercase px-2 py-0.5 rounded" style={{ color: typeColor, background: `${typeColor}15` }}>
                      {tx.type}
                    </span>
                    <span className="text-sm ml-3">{new Date(tx.date + "T00:00:00").toLocaleDateString("pt-BR")}</span>
                  </div>
                  <div className="text-right">
                    {tx.quantity && <span className="text-sm mr-3" style={{ color: "var(--text-secondary)" }}>{tx.quantity} units</span>}
                    <span className="text-sm font-medium">
                      {tx.total_value.currency === "BRL" ? "R$ " : "$ "}
                      {parseFloat(tx.total_value.amount).toLocaleString(tx.total_value.currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Dividends */}
      {dividends.length > 0 && (
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Dividend History</h2>
          <div className="space-y-2">
            {dividends.map((d, i) => (
              <div key={i} className="flex justify-between items-center py-2" style={{ borderBottom: "1px solid var(--border)" }}>
                <div>
                  <span className="text-xs" style={{ color: "var(--text-tertiary)" }}>{d.dividend_type}</span>
                  <span className="text-sm ml-3">{new Date(d.ex_date + "T00:00:00").toLocaleDateString("pt-BR")}</span>
                </div>
                <span className="text-sm font-medium">
                  {d.total.currency === "BRL" ? "R$ " : "$ "}
                  {parseFloat(d.total.amount).toLocaleString(d.total.currency === "BRL" ? "pt-BR" : "en-US", { minimumFractionDigits: 2 })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

Add import:
```typescript
import AssetDetail from "./pages/AssetDetail";
```

Add route inside the protected layout routes (after the `/portfolio/:assetClassId` route):
```tsx
<Route path="/portfolio/:assetClassId/:symbol" element={<AssetDetail />} />
```

- [ ] **Step 3: Update HoldingsTable row click to navigate**

In `frontend/src/components/HoldingsTable.tsx`, add `useNavigate` import and use it for row clicks.

Find the mobile card `onClick` that opens the transaction form and change it to navigate:
```tsx
onClick={() => navigate(`/portfolio/${assetClassId}/${h.symbol}?country=${/* get country from props or class */}&type=${type}`)}
```

For desktop rows, add a similar onClick handler or make the symbol cell a link.

Keep the buy/sell button opening the transaction form modal — don't change that.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AssetDetail.tsx frontend/src/App.tsx frontend/src/components/HoldingsTable.tsx
git commit -m "feat: add asset detail page with price chart and transaction history"
```

---

## Feature D2: Tax Report (DARF)

### Task 10: Tax Service

**Files:**
- Create: `backend/app/services/tax.py`
- Test: `backend/tests/test_services/test_tax.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_services/test_tax.py
import pytest
from datetime import date
from decimal import Decimal

from app.models.user import User
from app.models.asset_class import AssetClass
from app.models.transaction import Transaction
from app.services.tax import TaxService


def _create_user(db):
    user = User(name="Tax Test", email="tax@test.com", password_hash="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_class(db, user_id, name="BR Stocks", asset_type="stock"):
    ac = AssetClass(user_id=user_id, name=name, country="BR", type=asset_type, target_weight=50.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


def _add_tx(db, user_id, ac_id, symbol, tx_type, qty, unit_price, total, tx_date, tax=None):
    tx = Transaction(
        user_id=user_id, asset_class_id=ac_id, asset_symbol=symbol,
        type=tx_type, quantity=qty, unit_price=Decimal(str(unit_price)),
        total_value=Decimal(str(total)), currency="BRL", date=tx_date,
        tax_amount=Decimal(str(tax)) if tax else None,
    )
    db.add(tx)
    db.commit()
    return tx


class TestTaxService:
    def test_no_sells_returns_empty(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 100, 30.0, 3000.0, date(2026, 1, 15))

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        # All months should have zero tax
        for month in report:
            assert float(month["total_tax_due"]) == 0

    def test_stock_exempt_under_20k(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        # Buy 100 shares at R$30
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 100, 30.0, 3000.0, date(2026, 1, 10))
        # Sell 50 shares at R$35 = R$1,750 total sales (< 20k)
        _add_tx(db, user.id, ac.id, "PETR4", "sell", 50, 35.0, 1750.0, date(2026, 2, 15))

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        feb = next(m for m in report if m["month"] == 2)
        assert feb["stocks"]["exempt"] is True
        assert float(feb["stocks"]["total_gain"]) == pytest.approx(250.0)  # 50 * (35-30)
        assert float(feb["total_tax_due"]) == 0

    def test_stock_taxed_over_20k(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 1000, 30.0, 30000.0, date(2026, 1, 10))
        # Sell 700 at R$35 = R$24,500 total sales (> 20k), gain = 700 * 5 = 3500
        _add_tx(db, user.id, ac.id, "PETR4", "sell", 700, 35.0, 24500.0, date(2026, 3, 20))

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        mar = next(m for m in report if m["month"] == 3)
        assert mar["stocks"]["exempt"] is False
        assert float(mar["stocks"]["total_gain"]) == pytest.approx(3500.0)
        # 15% of 3500 = 525
        assert float(mar["stocks"]["tax_due"]) == pytest.approx(525.0)

    def test_fii_always_taxed(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id, name="FIIs", asset_type="stock")
        # Mark as FII by symbol convention (ends with 11)
        _add_tx(db, user.id, ac.id, "HGLG11", "buy", 100, 150.0, 15000.0, date(2026, 1, 10))
        # Sell 10 at R$160 = R$1,600 (< 20k but FII, no exemption)
        _add_tx(db, user.id, ac.id, "HGLG11", "sell", 10, 160.0, 1600.0, date(2026, 2, 20))

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        feb = next(m for m in report if m["month"] == 2)
        # gain = 10 * (160-150) = 100, tax = 20% of 100 = 20
        assert float(feb["fiis"]["total_gain"]) == pytest.approx(100.0)
        assert float(feb["fiis"]["tax_due"]) == pytest.approx(20.0)

    def test_loss_no_tax(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        _add_tx(db, user.id, ac.id, "VALE3", "buy", 100, 80.0, 8000.0, date(2026, 1, 10))
        # Sell at loss: 100 * R$70 = R$7,000, but > 20k check doesn't apply since total < 20k
        # Actually let's make it > 20k to ensure loss means no tax
        _add_tx(db, user.id, ac.id, "VALE3", "buy", 500, 80.0, 40000.0, date(2026, 1, 11))
        _add_tx(db, user.id, ac.id, "VALE3", "sell", 400, 70.0, 28000.0, date(2026, 4, 15))

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        apr = next(m for m in report if m["month"] == 4)
        assert float(apr["stocks"]["total_gain"]) < 0
        assert float(apr["total_tax_due"]) == 0

    def test_irrf_deducted(self, db):
        user = _create_user(db)
        ac = _create_class(db, user.id)
        _add_tx(db, user.id, ac.id, "PETR4", "buy", 1000, 30.0, 30000.0, date(2026, 1, 10))
        # Sell with IRRF tax already withheld
        _add_tx(db, user.id, ac.id, "PETR4", "sell", 700, 35.0, 24500.0, date(2026, 5, 15), tax=10.0)

        svc = TaxService(db)
        report = svc.get_monthly_report(user.id, 2026)
        may = next(m for m in report if m["month"] == 5)
        # gain = 3500, tax = 15% * 3500 - 10 IRRF = 525 - 10 = 515
        assert float(may["stocks"]["tax_due"]) == pytest.approx(515.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_services/test_tax.py -v`
Expected: FAIL (import error)

- [ ] **Step 3: Implement TaxService**

```python
# backend/app/services/tax.py
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.asset_class import AssetClass

STOCK_TAX_RATE = Decimal("0.15")
FII_TAX_RATE = Decimal("0.20")
STOCK_EXEMPTION_THRESHOLD = Decimal("20000")

# FII symbol pattern: ends with 11 or 11B
FII_PATTERN = re.compile(r"^[A-Z]{4}11B?$")


def _is_fii(symbol: str) -> bool:
    return bool(FII_PATTERN.match(symbol))


class TaxService:
    def __init__(self, db: Session):
        self._db = db

    def get_monthly_report(self, user_id: str, year: int) -> list[dict]:
        # Get all transactions for this user in this year
        all_txs = (
            self._db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.date.asc())
            .all()
        )

        # Build average cost per symbol from all buys before or during this year
        avg_cost = self._compute_avg_costs(all_txs)

        # Filter sells for the requested year
        sells_by_month: dict[int, list] = defaultdict(list)
        for tx in all_txs:
            if tx.type == "sell" and tx.date.year == year:
                sells_by_month[tx.date.month].append(tx)

        report = []
        for month in range(1, 13):
            month_sells = sells_by_month.get(month, [])

            stock_sales = Decimal("0")
            stock_gain = Decimal("0")
            stock_irrf = Decimal("0")
            fii_sales = Decimal("0")
            fii_gain = Decimal("0")
            fii_irrf = Decimal("0")

            for tx in month_sells:
                sell_total = tx.total_value
                qty = Decimal(str(tx.quantity)) if tx.quantity else Decimal("0")
                unit_cost = avg_cost.get(tx.asset_symbol, Decimal("0"))
                gain = (tx.unit_price - unit_cost) * qty if tx.unit_price and qty else Decimal("0")
                irrf = tx.tax_amount if tx.tax_amount else Decimal("0")

                if _is_fii(tx.asset_symbol):
                    fii_sales += sell_total
                    fii_gain += gain
                    fii_irrf += irrf
                else:
                    stock_sales += sell_total
                    stock_gain += gain
                    stock_irrf += irrf

            # Stock tax: exempt if total monthly sales < 20k
            stock_exempt = stock_sales < STOCK_EXEMPTION_THRESHOLD
            stock_tax = Decimal("0")
            if not stock_exempt and stock_gain > 0:
                stock_tax = max(stock_gain * STOCK_TAX_RATE - stock_irrf, Decimal("0"))

            # FII tax: always taxed, no exemption
            fii_tax = Decimal("0")
            if fii_gain > 0:
                fii_tax = max(fii_gain * FII_TAX_RATE - fii_irrf, Decimal("0"))

            total_tax = stock_tax + fii_tax

            report.append({
                "month": month,
                "stocks": {
                    "total_sales": str(stock_sales),
                    "total_gain": str(stock_gain),
                    "exempt": stock_exempt,
                    "tax_due": str(stock_tax),
                },
                "fiis": {
                    "total_sales": str(fii_sales),
                    "total_gain": str(fii_gain),
                    "tax_due": str(fii_tax),
                },
                "total_tax_due": str(total_tax),
            })

        return report

    def _compute_avg_costs(self, all_txs: list) -> dict[str, Decimal]:
        """Compute weighted average cost per symbol from buy transactions."""
        holdings: dict[str, dict] = {}  # symbol -> { qty, total_cost }

        for tx in all_txs:
            if tx.type == "buy" and tx.quantity and tx.unit_price:
                sym = tx.asset_symbol
                if sym not in holdings:
                    holdings[sym] = {"qty": Decimal("0"), "total_cost": Decimal("0")}
                qty = Decimal(str(tx.quantity))
                holdings[sym]["qty"] += qty
                holdings[sym]["total_cost"] += qty * tx.unit_price
            elif tx.type == "sell" and tx.quantity:
                sym = tx.asset_symbol
                if sym in holdings and holdings[sym]["qty"] > 0:
                    qty = Decimal(str(tx.quantity))
                    avg = holdings[sym]["total_cost"] / holdings[sym]["qty"]
                    holdings[sym]["qty"] -= qty
                    holdings[sym]["total_cost"] = holdings[sym]["qty"] * avg

        return {
            sym: (data["total_cost"] / data["qty"] if data["qty"] > 0 else Decimal("0"))
            for sym, data in holdings.items()
        }
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_services/test_tax.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tax.py backend/tests/test_services/test_tax.py
git commit -m "feat: add TaxService for DARF capital gains calculation"
```

---

### Task 11: Tax Report Endpoint

**Files:**
- Create: `backend/app/routers/tax.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routers/test_tax.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_routers/test_tax.py
import pytest
from datetime import date
from decimal import Decimal

from app.models.asset_class import AssetClass
from app.models.transaction import Transaction


def _setup_data(db, user_id):
    ac = AssetClass(user_id=user_id, name="BR Stocks", country="BR", type="stock", target_weight=100.0)
    db.add(ac)
    db.commit()
    db.refresh(ac)

    # Buy
    tx1 = Transaction(
        user_id=user_id, asset_class_id=ac.id, asset_symbol="PETR4",
        type="buy", quantity=1000, unit_price=Decimal("30.0"),
        total_value=Decimal("30000.0"), currency="BRL", date=date(2026, 1, 10),
    )
    # Sell > 20k
    tx2 = Transaction(
        user_id=user_id, asset_class_id=ac.id, asset_symbol="PETR4",
        type="sell", quantity=700, unit_price=Decimal("35.0"),
        total_value=Decimal("24500.0"), currency="BRL", date=date(2026, 3, 15),
    )
    db.add_all([tx1, tx2])
    db.commit()


class TestTaxRouter:
    def test_get_report(self, client, db, default_user, auth_headers):
        _setup_data(db, default_user.id)
        resp = client.get("/api/tax/report?year=2026", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12
        mar = next(m for m in data if m["month"] == 3)
        assert mar["stocks"]["exempt"] is False
        assert float(mar["total_tax_due"]) > 0

    def test_get_report_default_year(self, client, db, default_user, auth_headers):
        resp = client.get("/api/tax/report", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 12

    def test_empty_report(self, client, db, default_user, auth_headers):
        resp = client.get("/api/tax/report?year=2025", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for month in data:
            assert float(month["total_tax_due"]) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_routers/test_tax.py -v`
Expected: FAIL (404)

- [ ] **Step 3: Create tax router**

```python
# backend/app/routers/tax.py
from datetime import date

from fastapi import APIRouter, Depends, Header, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.tax import TaxService

router = APIRouter(prefix="/api/tax", tags=["tax"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/report")
@limiter.limit("30/minute")
def get_tax_report(
    request: Request,
    year: int = Query(default=None),
    user_id: str = Header(alias="X-User-Id", default=""),
    db: Session = Depends(get_db),
):
    if year is None:
        year = date.today().year

    svc = TaxService(db)
    return svc.get_monthly_report(user_id, year)
```

- [ ] **Step 4: Register router in main.py**

Add to `backend/app/main.py`:

```python
from app.routers import tax
app.include_router(tax.router)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_routers/test_tax.py -v`
Expected: 3 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/tax.py backend/tests/test_routers/test_tax.py backend/app/main.py
git commit -m "feat: add tax report endpoint for DARF calculation"
```

---

### Task 12: Frontend — Tax Page + Navigation

**Files:**
- Create: `frontend/src/hooks/useTaxReport.ts`
- Create: `frontend/src/pages/Tax.tsx`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TopNav.tsx`
- Modify: `frontend/src/components/MobileNav.tsx`

- [ ] **Step 1: Add types**

Add to `frontend/src/types/index.ts`:

```typescript
export interface TaxMonthlyEntry {
  month: number;
  stocks: {
    total_sales: string;
    total_gain: string;
    exempt: boolean;
    tax_due: string;
  };
  fiis: {
    total_sales: string;
    total_gain: string;
    tax_due: string;
  };
  total_tax_due: string;
}
```

- [ ] **Step 2: Create useTaxReport hook**

```typescript
// frontend/src/hooks/useTaxReport.ts
import { useState, useEffect } from "react";
import api from "../services/api";
import type { TaxMonthlyEntry } from "../types";

export function useTaxReport(year: number) {
  const [report, setReport] = useState<TaxMonthlyEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetch() {
      setLoading(true);
      setError("");
      try {
        const resp = await api.get<TaxMonthlyEntry[]>("/tax/report", { params: { year } });
        setReport(resp.data);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load tax report");
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, [year]);

  return { report, loading, error };
}
```

- [ ] **Step 3: Create Tax page**

```tsx
// frontend/src/pages/Tax.tsx
import { useState } from "react";
import { useTaxReport } from "../hooks/useTaxReport";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: 5 }, (_, i) => currentYear - i);

function formatBRL(value: string): string {
  const num = parseFloat(value);
  if (num === 0) return "—";
  return `R$ ${Math.abs(num).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function Tax() {
  const [year, setYear] = useState(currentYear);
  const { report, loading, error } = useTaxReport(year);

  const totalTaxDue = report.reduce((sum, m) => sum + parseFloat(m.total_tax_due), 0);
  const totalGains = report.reduce((sum, m) => sum + parseFloat(m.stocks.total_gain) + parseFloat(m.fiis.total_gain), 0);
  const monthsWithDarf = report.filter((m) => parseFloat(m.total_tax_due) > 0).length;
  const hasAnySells = report.some((m) => parseFloat(m.stocks.total_sales) > 0 || parseFloat(m.fiis.total_sales) > 0);

  return (
    <div className="space-y-6 py-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tax Report (DARF)</h1>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="px-3 py-1.5 rounded-lg text-sm"
          style={{ background: "var(--surface-hover)", color: "var(--text-primary)", border: "1px solid var(--border)" }}
        >
          {YEARS.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-500">{error}</p>}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg" style={{ background: "var(--surface-hover)" }} />
          ))}
        </div>
      ) : !hasAnySells ? (
        <div className="card text-center py-12">
          <p style={{ color: "var(--text-tertiary)" }}>No sell transactions in {year}.</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="card">
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Total Gains</p>
              <p className={`text-xl font-bold mt-1 ${totalGains >= 0 ? "text-[#34c759]" : "text-[#ff3b30]"}`}>
                {totalGains >= 0 ? "+" : "-"}R$ {Math.abs(totalGains).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div className="card">
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Total DARF Due</p>
              <p className={`text-xl font-bold mt-1 ${totalTaxDue > 0 ? "text-[#ff3b30]" : "text-[#34c759]"}`}>
                R$ {totalTaxDue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div className="card">
              <p className="text-xs" style={{ color: "var(--text-tertiary)" }}>Months with DARF</p>
              <p className="text-xl font-bold mt-1">{monthsWithDarf}</p>
            </div>
          </div>

          {/* Monthly Table */}
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ color: "var(--text-tertiary)", borderBottom: "1px solid var(--border)" }}>
                  <th className="text-left py-2 px-2">Month</th>
                  <th className="text-right py-2 px-2">Stock Sales</th>
                  <th className="text-right py-2 px-2">Stock Gain</th>
                  <th className="text-center py-2 px-2">Exempt?</th>
                  <th className="text-right py-2 px-2">FII Sales</th>
                  <th className="text-right py-2 px-2">FII Gain</th>
                  <th className="text-right py-2 px-2 font-semibold">DARF Due</th>
                </tr>
              </thead>
              <tbody>
                {report.map((m) => {
                  const hasSells = parseFloat(m.stocks.total_sales) > 0 || parseFloat(m.fiis.total_sales) > 0;
                  if (!hasSells) return null;
                  const taxDue = parseFloat(m.total_tax_due);
                  return (
                    <tr key={m.month} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td className="py-3 px-2 font-medium">{MONTH_NAMES[m.month - 1]}</td>
                      <td className="text-right py-3 px-2">{formatBRL(m.stocks.total_sales)}</td>
                      <td className="text-right py-3 px-2" style={{ color: parseFloat(m.stocks.total_gain) >= 0 ? "#34c759" : "#ff3b30" }}>
                        {parseFloat(m.stocks.total_gain) !== 0 ? `${parseFloat(m.stocks.total_gain) >= 0 ? "+" : ""}${formatBRL(m.stocks.total_gain)}` : "—"}
                      </td>
                      <td className="text-center py-3 px-2">
                        {parseFloat(m.stocks.total_sales) > 0 ? (
                          <span className={`text-xs px-2 py-0.5 rounded ${m.stocks.exempt ? "text-[#34c759]" : "text-[#ff9f0a]"}`}
                            style={{ background: m.stocks.exempt ? "rgba(52,199,89,0.1)" : "rgba(255,159,10,0.1)" }}>
                            {m.stocks.exempt ? "Yes" : "No"}
                          </span>
                        ) : "—"}
                      </td>
                      <td className="text-right py-3 px-2">{formatBRL(m.fiis.total_sales)}</td>
                      <td className="text-right py-3 px-2" style={{ color: parseFloat(m.fiis.total_gain) >= 0 ? "#34c759" : "#ff3b30" }}>
                        {parseFloat(m.fiis.total_gain) !== 0 ? `${parseFloat(m.fiis.total_gain) >= 0 ? "+" : ""}${formatBRL(m.fiis.total_gain)}` : "—"}
                      </td>
                      <td className="text-right py-3 px-2 font-semibold" style={{ color: taxDue > 0 ? "#ff3b30" : "var(--text-primary)" }}>
                        {taxDue > 0 ? `R$ ${taxDue.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}` : "R$ 0,00"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Add route to App.tsx**

Add import:
```typescript
import Tax from "./pages/Tax";
```

Add route inside protected layout:
```tsx
<Route path="/tax" element={<Tax />} />
```

- [ ] **Step 5: Add Tax tab to TopNav**

In `frontend/src/components/TopNav.tsx`, add to the TABS array:
```typescript
{ label: "Tax", path: "/tax" },
```

- [ ] **Step 6: Add Tax tab to MobileNav**

In `frontend/src/components/MobileNav.tsx`, add to the TABS array (replace Settings or add before it):
```typescript
{ label: "Tax", path: "/tax", icon: "receipt_long", end: false },
```

Note: MobileNav has 5 tabs. Consider replacing "Settings" with "Tax" in the bottom nav and making Settings accessible only from TopNav, or keep 5 tabs and add Tax as a 6th. Check the current layout and decide — if 6 tabs are too crowded, replace the least-used one or add Tax to a "More" menu. The simplest approach: add Tax and keep Settings in TopNav only.

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useTaxReport.ts frontend/src/pages/Tax.tsx frontend/src/types/index.ts frontend/src/App.tsx frontend/src/components/TopNav.tsx frontend/src/components/MobileNav.tsx
git commit -m "feat: add DARF tax report page with monthly capital gains summary"
```

---

## Final Verification

### Task 13: Run All Tests

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass (including new ones)

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no type errors

- [ ] **Step 3: Run frontend tests**

Run: `cd frontend && npm run test`
Expected: All tests pass

- [ ] **Step 4: Fix any failures and commit**

If any tests fail, fix and commit with:
```bash
git commit -m "fix: resolve test failures from portfolio improvements"
```
