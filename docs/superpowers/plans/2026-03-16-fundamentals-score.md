# Fundamentals Score Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-stock fundamentals scoring system (0-100%) based on 4 criteria (IPO age, EPS growth, debt ratio, profitability), displayed in the HoldingsTable and on a dedicated analysis page.

**Architecture:** Backend scoring engine with evaluator-per-criterion pattern. Provider methods fetch raw financial data from Finnhub (US) and Brapi/DadosDeMercado (BR). Weekly scheduler precomputes scores into a new DB table. Three API endpoints serve scores to the frontend. Frontend adds a score column to HoldingsTable and a new `/fundamentals/:symbol` analysis page with Recharts charts.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React/TypeScript/Recharts (frontend), pytest (tests), Vitest (frontend tests)

**Spec:** `docs/superpowers/specs/2026-03-16-fundamentals-score-design.md`

---

## File Structure

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/app/models/fundamentals_score.py` | SQLAlchemy model for `fundamentals_scores` table |
| `backend/app/services/fundamentals_scorer.py` | Pure scoring logic: 4 evaluators + orchestrator |
| `backend/app/services/fundamentals_scheduler.py` | APScheduler job: discover symbols, fetch data, score, upsert |
| `backend/app/routers/fundamentals.py` | 3 API endpoints: list scores, get detail, manual refresh |
| `backend/tests/test_services/test_fundamentals_scorer.py` | Unit tests for scoring engine |
| `backend/tests/test_services/test_fundamentals_scheduler.py` | Unit tests for scheduler |
| `backend/tests/test_routers/test_fundamentals.py` | Integration tests for API endpoints |
| `backend/tests/test_providers/test_finnhub_fundamentals.py` | Tests for Finnhub fundamentals method |
| `backend/tests/test_providers/test_brapi_fundamentals.py` | Tests for Brapi fundamentals method |

### Backend — Modified Files
| File | Change |
|------|--------|
| `backend/app/models/__init__.py` | Add `FundamentalsScore` to exports |
| `backend/app/providers/finnhub.py` | Add `get_fundamentals(symbol)` method |
| `backend/app/providers/brapi.py` | Add `get_fundamentals(symbol)` method |
| `backend/app/providers/dados_de_mercado.py` | Add `scrape_fundamentals(symbol)` method |
| `backend/app/main.py` | Register fundamentals scheduler + router |
| `backend/app/config.py` | Add scheduler config fields |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/src/hooks/useFundamentals.ts` | Hook to fetch scores and detail data |
| `frontend/src/pages/Fundamentals.tsx` | Analysis page with score breakdown + charts |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/src/types/index.ts` | Add `FundamentalsScore`, `FundamentalsDetail` types |
| `frontend/src/components/HoldingsTable.tsx` | Add score column with color coding + navigation (thread through GroupSection → HoldingRows, update colSpans) |
| `frontend/src/App.tsx` | Add `/fundamentals/:symbol` route |

> **Note on FII/REIT exclusion:** The spec says "Excludes crypto, FIIs, REITs." The scheduler filters by `AssetClass.country.in_(["US", "BR"])` which already excludes assets without a country. FIIs/REITs in Brazil have country="BR" but are typically in separate asset classes (e.g., "FIIs"). The crypto exclusion uses class name matching. If FII/REIT exclusion becomes needed, add their class names to the exclusion set.

---

## Chunk 1: Backend Data Layer + Scoring Engine

### Task 1: FundamentalsScore DB Model

**Files:**
- Create: `backend/app/models/fundamentals_score.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the model file**

```python
# backend/app/models/fundamentals_score.py
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FundamentalsScore(Base):
    __tablename__ = "fundamentals_scores"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ipo_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ipo_rating: Mapped[str] = mapped_column(String(10), default="red")
    eps_growth_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps_rating: Mapped[str] = mapped_column(String(10), default="red")
    current_net_debt_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_debt_years_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_rating: Mapped[str] = mapped_column(String(10), default="red")
    profitable_years_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_rating: Mapped[str] = mapped_column(String(10), default="red")
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 2: Register model in `__init__.py`**

In `backend/app/models/__init__.py`, add:
```python
from app.models.fundamentals_score import FundamentalsScore
```
And add `"FundamentalsScore"` to the `__all__` list.

- [ ] **Step 3: Verify model loads without errors**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -c "from app.models.fundamentals_score import FundamentalsScore; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/fundamentals_score.py backend/app/models/__init__.py
git commit -m "feat: add FundamentalsScore DB model"
```

---

### Task 2: Scoring Engine (Pure Logic)

**Files:**
- Create: `backend/app/services/fundamentals_scorer.py`
- Create: `backend/tests/test_services/test_fundamentals_scorer.py`

This is the core scoring logic — pure functions, no DB or provider dependencies.

- [ ] **Step 1: Write failing tests for IPO evaluator**

```python
# backend/tests/test_services/test_fundamentals_scorer.py
import pytest

from app.services.fundamentals_scorer import (
    evaluate_ipo,
    evaluate_eps_growth,
    evaluate_debt,
    evaluate_profitability,
    compute_composite_score,
)


class TestEvaluateIpo:
    def test_green_over_10_years(self):
        rating, points = evaluate_ipo(ipo_years=15)
        assert rating == "green"
        assert points == 25

    def test_yellow_between_5_and_10(self):
        rating, points = evaluate_ipo(ipo_years=7)
        assert rating == "yellow"
        assert points == 15

    def test_red_under_5_years(self):
        rating, points = evaluate_ipo(ipo_years=3)
        assert rating == "red"
        assert points == 0

    def test_red_when_none(self):
        rating, points = evaluate_ipo(ipo_years=None)
        assert rating == "red"
        assert points == 0

    def test_boundary_exactly_10(self):
        rating, points = evaluate_ipo(ipo_years=10)
        assert rating == "yellow"
        assert points == 15

    def test_boundary_exactly_5(self):
        rating, points = evaluate_ipo(ipo_years=5)
        assert rating == "yellow"
        assert points == 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py::TestEvaluateIpo -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement IPO evaluator**

```python
# backend/app/services/fundamentals_scorer.py


def evaluate_ipo(ipo_years: int | None) -> tuple[str, int]:
    """Rate company age. >10y green, 5-10y yellow, <5y red."""
    if ipo_years is None:
        return "red", 0
    if ipo_years > 10:
        return "green", 25
    if ipo_years >= 5:
        return "yellow", 15
    return "red", 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py::TestEvaluateIpo -v`
Expected: All 6 PASS

- [ ] **Step 5: Write failing tests for EPS Growth evaluator**

Add to the same test file:
```python
class TestEvaluateEpsGrowth:
    def test_green_over_50_pct(self):
        # 6 years of EPS: [1, 2, 3, 4, 5, 6] → 5 YoY comparisons, all growth → 100%
        eps_history = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        rating, points = evaluate_eps_growth(eps_history)
        assert rating == "green"
        assert points == 25

    def test_yellow_between_40_and_50_pct(self):
        # 11 YoY comparisons: need 40-50% growth years (4-5 out of 10)
        # [1,2,3,4,5, 4,3,2,1,0.5, 0.6] → growth in positions 0-4 (5 out of 10 = 50%)
        eps_history = [1.0, 2.0, 3.0, 4.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5, 0.6]
        rating, points = evaluate_eps_growth(eps_history)
        assert rating == "yellow"
        assert points == 15

    def test_red_under_40_pct(self):
        # Mostly declining: [5, 4, 3, 2, 1, 0.5] → 0 growth out of 5 = 0%
        eps_history = [5.0, 4.0, 3.0, 2.0, 1.0, 0.5]
        rating, points = evaluate_eps_growth(eps_history)
        assert rating == "red"
        assert points == 0

    def test_red_insufficient_data(self):
        # Less than 5 years → minimum not met
        eps_history = [1.0, 2.0, 3.0]
        rating, points = evaluate_eps_growth(eps_history)
        assert rating == "red"
        assert points == 0

    def test_red_empty_data(self):
        rating, points = evaluate_eps_growth([])
        assert rating == "red"
        assert points == 0

    def test_boundary_exactly_50_pct_is_yellow(self):
        # 50% exactly → yellow (spec says >50% for green)
        # 6 data points → 5 comparisons. Need exactly 50% = 2.5, so 2 or 3
        # [1, 2, 3, 2, 1, 0.5] → growth at pos 0,1 (2 out of 5 = 40%) → red
        # [1, 2, 3, 4, 3, 2] → growth at pos 0,1,2 (3 out of 5 = 60%) → green
        # Need exactly 50%: 11 items → 10 comparisons, 5 growth
        eps = [1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1]
        rating, points = evaluate_eps_growth(eps)
        assert rating == "yellow"
        assert points == 15
```

- [ ] **Step 6: Implement EPS Growth evaluator**

Add to `fundamentals_scorer.py`:
```python
def evaluate_eps_growth(eps_history: list[float]) -> tuple[str, int]:
    """Rate EPS year-over-year growth consistency. Minimum 5 data points required."""
    if len(eps_history) < 5:
        return "red", 0

    growth_years = sum(
        1 for i in range(1, len(eps_history)) if eps_history[i] > eps_history[i - 1]
    )
    total_comparisons = len(eps_history) - 1
    growth_pct = growth_years / total_comparisons

    if growth_pct > 0.5:
        return "green", 25
    if growth_pct >= 0.4:
        return "yellow", 15
    return "red", 0
```

- [ ] **Step 7: Run EPS tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py::TestEvaluateEpsGrowth -v`
Expected: All PASS

- [ ] **Step 8: Write failing tests for Debt evaluator**

Add to the same test file:
```python
class TestEvaluateDebt:
    def test_green_low_current_and_historically(self):
        # Current ratio <3, and ratio >3 in ≤30% of years
        debt_history = [1.0, 2.0, 1.5, 2.5, 1.0]  # all <3
        rating, points = evaluate_debt(current_ratio=1.5, debt_history=debt_history)
        assert rating == "green"
        assert points == 25

    def test_yellow_only_current_low(self):
        # Current <3 but >30% of years were >3
        debt_history = [4.0, 5.0, 4.0, 2.0, 1.5]  # 3 out of 5 = 60% > 3
        rating, points = evaluate_debt(current_ratio=1.5, debt_history=debt_history)
        assert rating == "yellow"
        assert points == 15

    def test_yellow_only_history_good(self):
        # Current ≥3 but historically ≤30% of years were >3
        debt_history = [1.0, 2.0, 1.5, 2.5, 1.0]  # 0% > 3
        rating, points = evaluate_debt(current_ratio=3.5, debt_history=debt_history)
        assert rating == "yellow"
        assert points == 15

    def test_red_both_bad(self):
        # Current ≥3 and >30% of years were >3
        debt_history = [4.0, 5.0, 4.0, 3.5, 6.0]  # all >3
        rating, points = evaluate_debt(current_ratio=4.0, debt_history=debt_history)
        assert rating == "red"
        assert points == 0

    def test_red_insufficient_data(self):
        debt_history = [1.0, 2.0]
        rating, points = evaluate_debt(current_ratio=1.0, debt_history=debt_history)
        assert rating == "red"
        assert points == 0

    def test_red_none_current(self):
        rating, points = evaluate_debt(current_ratio=None, debt_history=[1.0, 2.0, 1.0, 2.0, 1.0])
        assert rating == "red"
        assert points == 0
```

- [ ] **Step 9: Implement Debt evaluator**

Add to `fundamentals_scorer.py`:
```python
def evaluate_debt(
    current_ratio: float | None, debt_history: list[float]
) -> tuple[str, int]:
    """Rate Net Debt/EBITDA. Both current ratio <3 AND ≤30% historical >3 for green."""
    if current_ratio is None or len(debt_history) < 5:
        return "red", 0

    current_ok = current_ratio < 3
    high_debt_years = sum(1 for r in debt_history if r > 3)
    high_debt_pct = high_debt_years / len(debt_history)
    history_ok = high_debt_pct <= 0.3

    if current_ok and history_ok:
        return "green", 25
    if current_ok or history_ok:
        return "yellow", 15
    return "red", 0
```

- [ ] **Step 10: Run Debt tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py::TestEvaluateDebt -v`
Expected: All PASS

- [ ] **Step 11: Write failing tests for Profitability evaluator**

Add to the same test file:
```python
class TestEvaluateProfitability:
    def test_green_all_profitable(self):
        net_income = [10.0, 20.0, 15.0, 25.0, 30.0]
        rating, points = evaluate_profitability(net_income)
        assert rating == "green"
        assert points == 25

    def test_green_last_15_consecutive_profitable(self):
        # First 5 years have losses, but last 15 are all profitable
        net_income = [-1.0, -2.0, -3.0, -4.0, -5.0] + [10.0] * 15
        rating, points = evaluate_profitability(net_income)
        assert rating == "green"
        assert points == 25

    def test_yellow_80_pct_profitable(self):
        # 5 years, 4 profitable = 80%
        net_income = [10.0, 20.0, -5.0, 15.0, 25.0]
        rating, points = evaluate_profitability(net_income)
        assert rating == "yellow"
        assert points == 15

    def test_red_under_80_pct(self):
        # 5 years, 3 profitable = 60%
        net_income = [10.0, -5.0, -3.0, 15.0, 25.0]
        rating, points = evaluate_profitability(net_income)
        assert rating == "red"
        assert points == 0

    def test_red_insufficient_data(self):
        rating, points = evaluate_profitability([10.0, 20.0])
        assert rating == "red"
        assert points == 0

    def test_red_empty_data(self):
        rating, points = evaluate_profitability([])
        assert rating == "red"
        assert points == 0
```

- [ ] **Step 12: Implement Profitability evaluator**

Add to `fundamentals_scorer.py`:
```python
def evaluate_profitability(net_income_history: list[float]) -> tuple[str, int]:
    """Rate profitability consistency. All profitable or last 15 consecutive for green."""
    if len(net_income_history) < 5:
        return "red", 0

    total = len(net_income_history)
    profitable_count = sum(1 for ni in net_income_history if ni > 0)
    profitable_pct = profitable_count / total

    # Green: all profitable OR last 15 consecutive years profitable
    if profitable_count == total:
        return "green", 25

    if len(net_income_history) >= 15:
        last_15 = net_income_history[-15:]
        if all(ni > 0 for ni in last_15):
            return "green", 25

    if profitable_pct >= 0.8:
        return "yellow", 15
    return "red", 0
```

- [ ] **Step 13: Run Profitability tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py::TestEvaluateProfitability -v`
Expected: All PASS

- [ ] **Step 14: Write failing tests for composite score**

Add to the same test file:
```python
class TestCompositeScore:
    def test_all_green_is_100(self):
        ratings = [("green", 25), ("green", 25), ("green", 25), ("green", 25)]
        assert compute_composite_score(ratings) == 100

    def test_three_green_one_yellow_is_90(self):
        ratings = [("green", 25), ("green", 25), ("green", 25), ("yellow", 15)]
        assert compute_composite_score(ratings) == 90

    def test_all_yellow_is_60(self):
        ratings = [("yellow", 15), ("yellow", 15), ("yellow", 15), ("yellow", 15)]
        assert compute_composite_score(ratings) == 60

    def test_all_red_is_0(self):
        ratings = [("red", 0), ("red", 0), ("red", 0), ("red", 0)]
        assert compute_composite_score(ratings) == 0

    def test_mixed(self):
        ratings = [("green", 25), ("red", 0), ("yellow", 15), ("green", 25)]
        assert compute_composite_score(ratings) == 65
```

- [ ] **Step 15: Implement composite score**

Add to `fundamentals_scorer.py`:
```python
def compute_composite_score(ratings: list[tuple[str, int]]) -> int:
    """Sum individual criterion points. Range 0-100."""
    return sum(points for _, points in ratings)
```

- [ ] **Step 16: Run all scorer tests**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py -v`
Expected: All PASS

- [ ] **Step 17: Write the orchestrator function and its test**

Add test:
```python
class TestScoreFundamentals:
    def test_full_scoring(self):
        from app.services.fundamentals_scorer import score_fundamentals

        data = {
            "ipo_years": 15,
            "eps_history": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "debt_history": [1.0, 2.0, 1.5, 2.5, 1.0],
            "current_net_debt_ebitda": 1.5,
            "net_income_history": [10.0, 20.0, 15.0, 25.0, 30.0],
        }
        result = score_fundamentals(data)

        assert result["ipo_rating"] == "green"
        assert result["eps_rating"] == "green"
        assert result["debt_rating"] == "green"
        assert result["profit_rating"] == "green"
        assert result["composite_score"] == 100
        assert result["ipo_years"] == 15

    def test_missing_data_all_red(self):
        from app.services.fundamentals_scorer import score_fundamentals

        data = {
            "ipo_years": None,
            "eps_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "net_income_history": [],
        }
        result = score_fundamentals(data)

        assert result["composite_score"] == 0
        assert result["ipo_rating"] == "red"
        assert result["eps_rating"] == "red"
        assert result["debt_rating"] == "red"
        assert result["profit_rating"] == "red"
```

Add implementation to `fundamentals_scorer.py`:
```python
def score_fundamentals(data: dict) -> dict:
    """Orchestrate all evaluators and return full score breakdown."""
    ipo_rating, ipo_points = evaluate_ipo(data.get("ipo_years"))

    eps_history = data.get("eps_history", [])
    eps_rating, eps_points = evaluate_eps_growth(eps_history)

    debt_history = data.get("debt_history", [])
    current_debt = data.get("current_net_debt_ebitda")
    debt_rating, debt_points = evaluate_debt(current_debt, debt_history)

    net_income = data.get("net_income_history", [])
    profit_rating, profit_points = evaluate_profitability(net_income)

    ratings = [
        (ipo_rating, ipo_points),
        (eps_rating, eps_points),
        (debt_rating, debt_points),
        (profit_rating, profit_points),
    ]
    composite = compute_composite_score(ratings)

    eps_comparisons = len(eps_history) - 1 if len(eps_history) >= 5 else 0
    eps_growth_years = (
        sum(1 for i in range(1, len(eps_history)) if eps_history[i] > eps_history[i - 1])
        if eps_comparisons > 0
        else 0
    )
    high_debt_years = sum(1 for r in debt_history if r > 3) if len(debt_history) >= 5 else 0
    profitable_count = sum(1 for ni in net_income if ni > 0) if len(net_income) >= 5 else 0

    return {
        "ipo_years": data.get("ipo_years"),
        "ipo_rating": ipo_rating,
        "eps_growth_pct": round(eps_growth_years / eps_comparisons * 100, 1) if eps_comparisons > 0 else None,
        "eps_rating": eps_rating,
        "current_net_debt_ebitda": current_debt,
        "high_debt_years_pct": round(high_debt_years / len(debt_history) * 100, 1) if len(debt_history) >= 5 else None,
        "debt_rating": debt_rating,
        "profitable_years_pct": round(profitable_count / len(net_income) * 100, 1) if len(net_income) >= 5 else None,
        "profit_rating": profit_rating,
        "composite_score": composite,
    }
```

- [ ] **Step 18: Run all scorer tests**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scorer.py -v`
Expected: All PASS

- [ ] **Step 19: Commit**

```bash
git add backend/app/services/fundamentals_scorer.py backend/tests/test_services/test_fundamentals_scorer.py
git commit -m "feat: add FundamentalsScorer with 4 evaluators and composite score"
```

---

### Task 3: FinnhubProvider.get_fundamentals()

**Files:**
- Modify: `backend/app/providers/finnhub.py`
- Create: `backend/tests/test_providers/test_finnhub_fundamentals.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_providers/test_finnhub_fundamentals.py
from unittest.mock import MagicMock, patch
from datetime import date

import pytest

from app.providers.finnhub import FinnhubProvider


@pytest.fixture
def provider():
    return FinnhubProvider(api_key="test-key", base_url="https://finnhub.io/api/v1")


class TestGetFundamentals:
    def test_extracts_ipo_date_and_computes_years(self, provider):
        profile_response = MagicMock()
        profile_response.json.return_value = {"ipo": "2010-06-29", "name": "TestCo"}
        profile_response.raise_for_status = MagicMock()

        financials_response = MagicMock()
        financials_response.json.return_value = {"data": [
            {
                "year": 2025, "report": {"bs": {"totalDebt": {"value": 100}}, "ic": {
                    "dilutedEPS": {"value": 5.0},
                    "netIncome": {"value": 50},
                    "ebitda": {"value": 80},
                }},
            },
            {
                "year": 2024, "report": {"bs": {"totalDebt": {"value": 120}}, "ic": {
                    "dilutedEPS": {"value": 4.5},
                    "netIncome": {"value": 45},
                    "ebitda": {"value": 75},
                }},
            },
            {
                "year": 2023, "report": {"bs": {"totalDebt": {"value": 110}}, "ic": {
                    "dilutedEPS": {"value": 4.0},
                    "netIncome": {"value": 40},
                    "ebitda": {"value": 70},
                }},
            },
            {
                "year": 2022, "report": {"bs": {"totalDebt": {"value": 90}}, "ic": {
                    "dilutedEPS": {"value": 3.5},
                    "netIncome": {"value": 35},
                    "ebitda": {"value": 65},
                }},
            },
            {
                "year": 2021, "report": {"bs": {"totalDebt": {"value": 80}}, "ic": {
                    "dilutedEPS": {"value": 3.0},
                    "netIncome": {"value": 30},
                    "ebitda": {"value": 60},
                }},
            },
        ]}
        financials_response.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [profile_response, financials_response]
            result = provider.get_fundamentals("AAPL")

        assert result["ipo_years"] >= 15  # 2010 to 2026
        assert len(result["eps_history"]) == 5
        assert result["eps_history"] == [3.0, 3.5, 4.0, 4.5, 5.0]  # sorted chronologically
        assert len(result["net_income_history"]) == 5
        assert result["current_net_debt_ebitda"] == pytest.approx(100 / 80, rel=0.01)

    def test_handles_missing_ipo_date(self, provider):
        profile_response = MagicMock()
        profile_response.json.return_value = {"name": "TestCo"}  # no ipo field
        profile_response.raise_for_status = MagicMock()

        financials_response = MagicMock()
        financials_response.json.return_value = {"data": []}
        financials_response.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [profile_response, financials_response]
            result = provider.get_fundamentals("UNKNOWN")

        assert result["ipo_years"] is None
        assert result["eps_history"] == []

    def test_handles_missing_financial_fields(self, provider):
        profile_response = MagicMock()
        profile_response.json.return_value = {"ipo": "2015-01-01"}
        profile_response.raise_for_status = MagicMock()

        financials_response = MagicMock()
        financials_response.json.return_value = {"data": [
            {"year": 2025, "report": {"bs": {}, "ic": {}}},
            {"year": 2024, "report": {"bs": {}, "ic": {}}},
            {"year": 2023, "report": {"bs": {}, "ic": {}}},
            {"year": 2022, "report": {"bs": {}, "ic": {}}},
            {"year": 2021, "report": {"bs": {}, "ic": {}}},
        ]}
        financials_response.raise_for_status = MagicMock()

        with patch("app.providers.finnhub.httpx.get") as mock_get:
            mock_get.side_effect = [profile_response, financials_response]
            result = provider.get_fundamentals("SPARSE")

        # Should still have entries but with 0/None values
        assert result["ipo_years"] >= 10
        assert len(result["eps_history"]) == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/test_finnhub_fundamentals.py -v`
Expected: FAIL with `AttributeError: 'FinnhubProvider' has no attribute 'get_fundamentals'`

- [ ] **Step 3: Implement get_fundamentals**

Add to `backend/app/providers/finnhub.py`:
```python
    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental data for scoring: IPO date, EPS, debt, income history."""
        # IPO date from profile
        profile_resp = httpx.get(
            f"{self._base_url}/stock/profile2",
            params={"symbol": symbol, "token": self._api_key},
            timeout=10,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

        ipo_str = profile.get("ipo")
        ipo_years = None
        if ipo_str:
            try:
                ipo_date = datetime.strptime(ipo_str, "%Y-%m-%d")
                ipo_years = (datetime.now(timezone.utc) - ipo_date.replace(tzinfo=timezone.utc)).days // 365
            except ValueError:
                pass

        # Annual financial statements
        fin_resp = httpx.get(
            f"{self._base_url}/stock/financials-reported",
            params={"symbol": symbol, "token": self._api_key, "freq": "annual"},
            timeout=15,
        )
        fin_resp.raise_for_status()
        reports = fin_resp.json().get("data", [])

        # Sort chronologically (oldest first)
        reports.sort(key=lambda r: r.get("year", 0))

        eps_history = []
        net_income_history = []
        debt_history = []
        raw_years = []

        for report in reports:
            year = report.get("year", 0)
            ic = report.get("report", {}).get("ic", {})
            bs = report.get("report", {}).get("bs", {})

            eps = ic.get("dilutedEPS", {}).get("value", 0) if isinstance(ic.get("dilutedEPS"), dict) else ic.get("dilutedEPS", 0) or 0
            net_income = ic.get("netIncome", {}).get("value", 0) if isinstance(ic.get("netIncome"), dict) else ic.get("netIncome", 0) or 0
            ebitda = ic.get("ebitda", {}).get("value", 0) if isinstance(ic.get("ebitda"), dict) else ic.get("ebitda", 0) or 0
            total_debt = bs.get("totalDebt", {}).get("value", 0) if isinstance(bs.get("totalDebt"), dict) else bs.get("totalDebt", 0) or 0

            eps_history.append(eps)
            net_income_history.append(net_income)
            net_debt_ebitda = total_debt / ebitda if ebitda != 0 else 0
            debt_history.append(net_debt_ebitda)
            raw_years.append({
                "year": year, "eps": eps, "net_income": net_income,
                "net_debt_ebitda": round(net_debt_ebitda, 2),
            })

        current_net_debt_ebitda = debt_history[-1] if debt_history else None

        return {
            "ipo_years": ipo_years,
            "eps_history": eps_history,
            "net_income_history": net_income_history,
            "debt_history": debt_history,
            "current_net_debt_ebitda": current_net_debt_ebitda,
            "raw_data": raw_years,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/test_finnhub_fundamentals.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers/finnhub.py backend/tests/test_providers/test_finnhub_fundamentals.py
git commit -m "feat: add FinnhubProvider.get_fundamentals() for scoring data"
```

---

### Task 4: BrapiProvider.get_fundamentals() + DadosDeMercado Fallback

**Files:**
- Modify: `backend/app/providers/brapi.py`
- Modify: `backend/app/providers/dados_de_mercado.py`
- Create: `backend/tests/test_providers/test_brapi_fundamentals.py`

**Approach:** Try Brapi `fundamental=true` first. Inspect the response during implementation to determine what fields are available. If Brapi doesn't provide multi-year EPS/debt/income data, fall back to DadosDeMercado scraping of `/acoes/{ticker}/balanco` and `/acoes/{ticker}/resultado`.

> **Implementation note:** The Brapi response shape needs to be discovered during implementation. The test below uses a realistic mock based on known Brapi patterns. If the real response differs, adjust the parsing code and tests accordingly.

- [ ] **Step 1: Write failing test for Brapi get_fundamentals**

```python
# backend/tests/test_providers/test_brapi_fundamentals.py
from unittest.mock import MagicMock, patch

import pytest

from app.providers.brapi import BrapiProvider


@pytest.fixture
def provider():
    return BrapiProvider(api_key="test-key", base_url="https://brapi.dev")


class TestBrapiGetFundamentals:
    def test_returns_fundamentals_shape(self, provider):
        """Test that get_fundamentals returns the expected dict shape."""
        response = MagicMock()
        response.json.return_value = {"results": [{"shortName": "PETR4"}]}
        response.raise_for_status = MagicMock()

        with patch("app.providers.brapi.httpx.get", return_value=response):
            result = provider.get_fundamentals("PETR4.SA")

        # Must return the standard shape even if data is sparse
        assert "ipo_years" in result
        assert "eps_history" in result
        assert "net_income_history" in result
        assert "debt_history" in result
        assert "current_net_debt_ebitda" in result
        assert "raw_data" in result
        assert isinstance(result["eps_history"], list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/test_brapi_fundamentals.py -v`
Expected: FAIL

- [ ] **Step 3: Implement BrapiProvider.get_fundamentals()**

Add to `backend/app/providers/brapi.py`:
```python
    def get_fundamentals(self, symbol: str) -> dict:
        """Fetch fundamental data from Brapi. Returns standardized shape."""
        ticker = _strip_sa(symbol)
        resp = httpx.get(
            f"{self._base_url}/api/quote/{ticker}",
            params={"token": self._api_key, "fundamental": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()["results"][0]

        # Extract whatever Brapi provides - shape may vary
        # Return standardized dict; caller checks if data is sufficient
        return {
            "ipo_years": None,  # Brapi doesn't provide IPO date
            "eps_history": [],
            "net_income_history": [],
            "debt_history": [],
            "current_net_debt_ebitda": None,
            "raw_data": [],
        }
```

> **Note:** This is a minimal stub. During implementation, inspect `data` with a real API call to determine available fields. Update parsing and tests accordingly. The DadosDeMercado fallback below handles the case where Brapi data is insufficient.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/test_brapi_fundamentals.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for DadosDeMercado scrape_fundamentals**

Add to the same test file or create `backend/tests/test_providers/test_dados_fundamentals.py`:
```python
# backend/tests/test_providers/test_dados_fundamentals.py
import pytest

from app.providers.dados_de_mercado import DadosDeMercadoProvider


@pytest.fixture
def provider():
    return DadosDeMercadoProvider(base_url="https://www.dadosdemercado.com.br")


class TestScrapeFundamentals:
    def test_returns_fundamentals_shape(self, provider, monkeypatch):
        """Test HTML parsing of balance sheet + income statement pages."""
        balance_html = """
        <html><body>
        <table><thead><tr><th>Item</th><th>2025</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th></tr></thead>
        <tbody>
        <tr><td>Dívida Líquida</td><td>100.000</td><td>120.000</td><td>110.000</td><td>90.000</td><td>80.000</td></tr>
        </tbody></table>
        </body></html>
        """
        resultado_html = """
        <html><body>
        <table><thead><tr><th>Item</th><th>2025</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th></tr></thead>
        <tbody>
        <tr><td>LPA</td><td>5,00</td><td>4,50</td><td>4,00</td><td>3,50</td><td>3,00</td></tr>
        <tr><td>Lucro Líquido</td><td>50.000</td><td>45.000</td><td>40.000</td><td>35.000</td><td>30.000</td></tr>
        <tr><td>EBITDA</td><td>80.000</td><td>75.000</td><td>70.000</td><td>65.000</td><td>60.000</td></tr>
        </tbody></table>
        </body></html>
        """

        call_count = {"n": 0}

        def mock_get(*args, **kwargs):
            call_count["n"] += 1
            resp = type("Response", (), {
                "raise_for_status": lambda self: None,
                "text": balance_html if call_count["n"] == 1 else resultado_html,
            })()
            return resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["eps_history"]) == 5
        assert len(result["net_income_history"]) == 5
        assert len(result["debt_history"]) == 5
        assert result["current_net_debt_ebitda"] is not None
```

- [ ] **Step 6: Implement DadosDeMercadoProvider.scrape_fundamentals()**

Add to `backend/app/providers/dados_de_mercado.py`:
```python
    def scrape_fundamentals(self, symbol: str) -> dict:
        """Scrape balance sheet and income statement for fundamentals scoring."""
        ticker = _strip_sa(symbol).lower()

        # Fetch balance sheet (for net debt)
        balance_data = self._scrape_financial_table(f"{self._base_url}/acoes/{ticker}/balanco")

        # Fetch income statement (for EPS, net income, EBITDA)
        resultado_data = self._scrape_financial_table(f"{self._base_url}/acoes/{ticker}/resultado")

        # Extract years from column headers
        years = sorted(set(balance_data.get("years", []) + resultado_data.get("years", [])))

        eps_history = []
        net_income_history = []
        debt_history = []
        raw_years = []

        for year in years:
            eps = resultado_data.get("LPA", {}).get(year, 0)
            net_income = resultado_data.get("Lucro Líquido", {}).get(year, 0)
            ebitda = resultado_data.get("EBITDA", {}).get(year, 0)
            net_debt = balance_data.get("Dívida Líquida", {}).get(year, 0)

            eps_history.append(eps)
            net_income_history.append(net_income)
            net_debt_ebitda = net_debt / ebitda if ebitda != 0 else 0
            debt_history.append(net_debt_ebitda)
            raw_years.append({
                "year": year, "eps": eps, "net_income": net_income,
                "net_debt_ebitda": round(net_debt_ebitda, 2),
            })

        current_net_debt_ebitda = debt_history[-1] if debt_history else None

        return {
            "ipo_years": None,  # Not available from this source
            "eps_history": eps_history,
            "net_income_history": net_income_history,
            "debt_history": debt_history,
            "current_net_debt_ebitda": current_net_debt_ebitda,
            "raw_data": raw_years,
        }

    def _scrape_financial_table(self, url: str) -> dict:
        """Scrape a financial table page. Returns {row_label: {year: value}, years: []}."""
        try:
            resp = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception:
            logger.exception(f"Failed to fetch {url}")
            return {"years": []}

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if table is None:
            return {"years": []}

        # Parse header for years
        thead = table.find("thead")
        if thead is None:
            return {"years": []}

        headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        years = []
        for h in headers[1:]:  # Skip first column (label)
            try:
                years.append(int(h))
            except ValueError:
                continue

        result = {"years": years}

        tbody = table.find("tbody")
        if tbody is None:
            return result

        for row in tbody.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            label = cells[0].get_text(strip=True)
            values = {}
            for i, year in enumerate(years):
                if i + 1 < len(cells):
                    try:
                        values[year] = _parse_value(cells[i + 1].get_text(strip=True))
                    except (ValueError, IndexError):
                        values[year] = 0
            result[label] = values

        return result
```

- [ ] **Step 7: Run DadosDeMercado test to verify it passes**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/test_dados_fundamentals.py -v`
Expected: PASS

- [ ] **Step 8: Run all provider tests together**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_providers/ -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/providers/brapi.py backend/app/providers/dados_de_mercado.py \
  backend/tests/test_providers/test_brapi_fundamentals.py backend/tests/test_providers/test_dados_fundamentals.py
git commit -m "feat: add fundamentals methods to Brapi and DadosDeMercado providers"
```

---

## Chunk 2: Scheduler, Router, and App Wiring

### Task 5: FundamentalsScoreScheduler

**Files:**
- Create: `backend/app/services/fundamentals_scheduler.py`
- Create: `backend/tests/test_services/test_fundamentals_scheduler.py`

**Depends on:** Task 1 (model), Task 2 (scorer), Tasks 3-4 (providers)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_services/test_fundamentals_scheduler.py
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.asset_class import AssetClass
from app.models.fundamentals_score import FundamentalsScore
from app.models.transaction import Transaction
from app.models.user import User
from app.services.fundamentals_scheduler import FundamentalsScoreScheduler


@pytest.fixture
def finnhub():
    return MagicMock()


@pytest.fixture
def brapi():
    return MagicMock()


@pytest.fixture
def dados():
    return MagicMock()


@pytest.fixture
def scheduler(finnhub, brapi, dados):
    return FundamentalsScoreScheduler(
        finnhub_provider=finnhub,
        brapi_provider=brapi,
        dados_provider=dados,
        delay=0.0,
    )


def _setup_holdings(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    ac_us = AssetClass(user_id=user.id, name="US Stocks", target_weight=50.0, country="US")
    ac_br = AssetClass(user_id=user.id, name="BR Stocks", target_weight=50.0, country="BR")
    ac_crypto = AssetClass(user_id=user.id, name="Crypto", target_weight=0.0, country="US")
    db.add_all([ac_us, ac_br, ac_crypto])
    db.flush()

    db.add_all([
        Transaction(
            user_id=user.id, asset_class_id=ac_us.id, asset_symbol="AAPL",
            type="buy", quantity=10, unit_price=150.0, total_value=1500.0,
            currency="USD", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_br.id, asset_symbol="PETR4.SA",
            type="buy", quantity=100, unit_price=38.0, total_value=3800.0,
            currency="BRL", date=date(2025, 1, 1),
        ),
        Transaction(
            user_id=user.id, asset_class_id=ac_crypto.id, asset_symbol="BTC",
            type="buy", quantity=1, unit_price=50000.0, total_value=50000.0,
            currency="USD", date=date(2025, 1, 1),
        ),
    ])
    db.commit()


MOCK_FUNDAMENTALS = {
    "ipo_years": 15,
    "eps_history": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    "net_income_history": [10.0, 20.0, 15.0, 25.0, 30.0, 35.0],
    "debt_history": [1.0, 2.0, 1.5, 2.5, 1.0, 1.2],
    "current_net_debt_ebitda": 1.2,
    "raw_data": [{"year": y, "eps": e} for y, e in zip(range(2020, 2026), [1, 2, 3, 4, 5, 6])],
}


class TestFundamentalsScheduler:
    def test_discovers_us_and_br_stocks_only(self, scheduler, finnhub, brapi, db):
        _setup_holdings(db)
        finnhub.get_fundamentals.return_value = MOCK_FUNDAMENTALS
        brapi.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        # Should call finnhub for AAPL, brapi for PETR4.SA, skip BTC
        finnhub.get_fundamentals.assert_called_once_with("AAPL")
        brapi.get_fundamentals.assert_called_once_with("PETR4.SA")

    def test_upserts_score_to_db(self, scheduler, finnhub, brapi, db):
        _setup_holdings(db)
        finnhub.get_fundamentals.return_value = MOCK_FUNDAMENTALS
        brapi.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        score = db.query(FundamentalsScore).filter_by(symbol="AAPL").first()
        assert score is not None
        assert score.composite_score == 100
        assert score.ipo_rating == "green"

    def test_falls_back_to_dados_for_br(self, scheduler, finnhub, brapi, dados, db):
        _setup_holdings(db)
        finnhub.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        # Brapi returns insufficient data
        brapi.get_fundamentals.return_value = {
            "ipo_years": None, "eps_history": [], "net_income_history": [],
            "debt_history": [], "current_net_debt_ebitda": None, "raw_data": [],
        }
        dados.scrape_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        dados.scrape_fundamentals.assert_called_once_with("PETR4.SA")
        score = db.query(FundamentalsScore).filter_by(symbol="PETR4.SA").first()
        assert score is not None
        assert score.composite_score == 100

    def test_continues_on_individual_failure(self, scheduler, finnhub, brapi, db):
        _setup_holdings(db)
        finnhub.get_fundamentals.side_effect = Exception("API error")
        brapi.get_fundamentals.return_value = MOCK_FUNDAMENTALS

        scheduler.score_all(db)

        # AAPL should fail, PETR4.SA should succeed
        assert db.query(FundamentalsScore).filter_by(symbol="AAPL").first() is None
        assert db.query(FundamentalsScore).filter_by(symbol="PETR4.SA").first() is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement FundamentalsScoreScheduler**

```python
# backend/app/services/fundamentals_scheduler.py
import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.fundamentals_score import FundamentalsScore
from app.models.transaction import Transaction
from app.services.fundamentals_scorer import score_fundamentals

logger = logging.getLogger(__name__)

CRYPTO_CLASS_NAMES = {"Crypto", "Criptomoedas"}


class FundamentalsScoreScheduler:
    def __init__(self, finnhub_provider, brapi_provider, dados_provider, delay: float = 1.5):
        self._finnhub = finnhub_provider
        self._brapi = brapi_provider
        self._dados = dados_provider
        self._delay = delay

    def score_all(self, db: Session) -> None:
        symbols = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(
                AssetClass.country.in_(["US", "BR"]),
                AssetClass.name.notin_(list(CRYPTO_CLASS_NAMES)),
            )
            .distinct()
            .all()
        )

        for symbol, country in symbols:
            try:
                raw = self._fetch_fundamentals(symbol, country)
                result = score_fundamentals(raw)
                self._upsert_score(db, symbol, result, raw.get("raw_data"))
                db.commit()
                logger.info(f"Scored {symbol}: {result['composite_score']}%")
            except Exception:
                logger.exception(f"Failed to score {symbol}")
                db.rollback()
            finally:
                if self._delay > 0 and country == "US":
                    time.sleep(self._delay)

    def _fetch_fundamentals(self, symbol: str, country: str) -> dict:
        if country == "US":
            return self._finnhub.get_fundamentals(symbol)

        # BR: try Brapi first, fallback to DadosDeMercado
        data = self._brapi.get_fundamentals(symbol)
        if len(data.get("eps_history", [])) >= 5:
            return data

        logger.info(f"Brapi data insufficient for {symbol}, falling back to DadosDeMercado")
        return self._dados.scrape_fundamentals(symbol)

    def _upsert_score(self, db: Session, symbol: str, result: dict, raw_data: list | None) -> None:
        score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
        if score is None:
            score = FundamentalsScore(symbol=symbol)
            db.add(score)

        score.ipo_years = result["ipo_years"]
        score.ipo_rating = result["ipo_rating"]
        score.eps_growth_pct = result["eps_growth_pct"]
        score.eps_rating = result["eps_rating"]
        score.current_net_debt_ebitda = result["current_net_debt_ebitda"]
        score.high_debt_years_pct = result["high_debt_years_pct"]
        score.debt_rating = result["debt_rating"]
        score.profitable_years_pct = result["profitable_years_pct"]
        score.profit_rating = result["profit_rating"]
        score.composite_score = result["composite_score"]
        score.raw_data = raw_data
        score.updated_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_services/test_fundamentals_scheduler.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fundamentals_scheduler.py backend/tests/test_services/test_fundamentals_scheduler.py
git commit -m "feat: add FundamentalsScoreScheduler with Brapi/DadosDeMercado fallback"
```

---

### Task 6: Fundamentals API Router

**Files:**
- Create: `backend/app/routers/fundamentals.py`
- Create: `backend/tests/test_routers/test_fundamentals.py`

**Depends on:** Task 1 (model)

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_routers/test_fundamentals.py
from datetime import datetime, timezone

import pytest

from app.models.fundamentals_score import FundamentalsScore
from app.models.user import User


def _seed_scores(db):
    user = User(name="Test", email="test@test.com")
    db.add(user)
    db.flush()

    scores = [
        FundamentalsScore(
            symbol="AAPL",
            ipo_years=45, ipo_rating="green",
            eps_growth_pct=80.0, eps_rating="green",
            current_net_debt_ebitda=1.2, high_debt_years_pct=10.0, debt_rating="green",
            profitable_years_pct=100.0, profit_rating="green",
            composite_score=100,
            raw_data=[{"year": 2025, "eps": 6.0}],
        ),
        FundamentalsScore(
            symbol="PETR4.SA",
            ipo_years=20, ipo_rating="green",
            eps_growth_pct=45.0, eps_rating="yellow",
            current_net_debt_ebitda=2.5, high_debt_years_pct=20.0, debt_rating="green",
            profitable_years_pct=85.0, profit_rating="yellow",
            composite_score=80,
            raw_data=[{"year": 2025, "eps": 4.0}],
        ),
    ]
    db.add_all(scores)
    db.commit()
    return user


class TestGetScores:
    def test_returns_all_scores(self, client, db):
        user = _seed_scores(db)

        resp = client.get("/api/fundamentals/scores", headers={"X-User-Id": user.id})

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        symbols = {s["symbol"] for s in data}
        assert symbols == {"AAPL", "PETR4.SA"}

    def test_returns_score_fields(self, client, db):
        user = _seed_scores(db)

        resp = client.get("/api/fundamentals/scores", headers={"X-User-Id": user.id})

        aapl = next(s for s in resp.json() if s["symbol"] == "AAPL")
        assert aapl["composite_score"] == 100
        assert aapl["ipo_rating"] == "green"
        assert aapl["eps_rating"] == "green"
        assert aapl["debt_rating"] == "green"
        assert aapl["profit_rating"] == "green"


class TestGetDetail:
    def test_returns_score_with_raw_data(self, client, db):
        user = _seed_scores(db)

        resp = client.get("/api/fundamentals/AAPL", headers={"X-User-Id": user.id})

        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert data["composite_score"] == 100
        assert data["raw_data"] is not None

    def test_returns_404_for_unknown_symbol(self, client, db):
        user = _seed_scores(db)

        resp = client.get("/api/fundamentals/UNKNOWN", headers={"X-User-Id": user.id})

        assert resp.status_code == 404


class TestRefresh:
    def test_returns_200_with_refreshed_score(self, client, db, monkeypatch):
        user = _seed_scores(db)

        # Mock the refresh to avoid actual provider calls
        monkeypatch.setattr(
            "app.routers.fundamentals._refresh_score", lambda symbol, db: None
        )

        resp = client.post("/api/fundamentals/AAPL/refresh", headers={"X-User-Id": user.id})

        assert resp.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_routers/test_fundamentals.py -v`
Expected: FAIL

- [ ] **Step 3: Implement the router**

```python
# backend/app/routers/fundamentals.py
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import CRUD_LIMIT, limiter
from app.models.fundamentals_score import FundamentalsScore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


def _score_to_dict(score: FundamentalsScore, include_raw: bool = False) -> dict:
    result = {
        "symbol": score.symbol,
        "ipo_years": score.ipo_years,
        "ipo_rating": score.ipo_rating,
        "eps_growth_pct": score.eps_growth_pct,
        "eps_rating": score.eps_rating,
        "current_net_debt_ebitda": score.current_net_debt_ebitda,
        "high_debt_years_pct": score.high_debt_years_pct,
        "debt_rating": score.debt_rating,
        "profitable_years_pct": score.profitable_years_pct,
        "profit_rating": score.profit_rating,
        "composite_score": score.composite_score,
        "updated_at": score.updated_at.isoformat() if score.updated_at else None,
    }
    if include_raw:
        result["raw_data"] = score.raw_data
    return result


def _refresh_score(symbol: str, db: Session) -> None:
    """Fetch fresh data and re-score a single symbol."""
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.finnhub import FinnhubProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    scheduler = FundamentalsScoreScheduler(
        finnhub_provider=FinnhubProvider(api_key=settings.finnhub_api_key, base_url=settings.finnhub_base_url),
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
        dados_provider=DadosDeMercadoProvider(),
        delay=0,
    )

    country = "BR" if symbol.endswith(".SA") else "US"
    raw = scheduler._fetch_fundamentals(symbol, country)

    from app.services.fundamentals_scorer import score_fundamentals

    result = score_fundamentals(raw)
    scheduler._upsert_score(db, symbol, result, raw.get("raw_data"))
    db.commit()


@router.get("/scores")
@limiter.limit(CRUD_LIMIT)
def get_scores(request: Request, x_user_id: str = Header(), db: Session = Depends(get_db)):
    scores = db.query(FundamentalsScore).all()
    return [_score_to_dict(s) for s in scores]


@router.get("/{symbol}")
@limiter.limit(CRUD_LIMIT)
def get_detail(request: Request, symbol: str, x_user_id: str = Header(), db: Session = Depends(get_db)):
    score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    if score is None:
        raise HTTPException(status_code=404, detail=f"No score found for {symbol}")
    return _score_to_dict(score, include_raw=True)


@router.post("/{symbol}/refresh")
@limiter.limit(CRUD_LIMIT)
def refresh_score(request: Request, symbol: str, x_user_id: str = Header(), db: Session = Depends(get_db)):
    try:
        _refresh_score(symbol, db)
    except Exception:
        logger.exception(f"Failed to refresh score for {symbol}")
        raise HTTPException(status_code=502, detail=f"Failed to refresh score for {symbol}")
    score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    if score is None:
        raise HTTPException(status_code=502, detail="Score computation failed")
    return _score_to_dict(score, include_raw=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_routers/test_fundamentals.py -v`
Expected: All PASS

- [ ] **Step 5: Register router in main.py (required for tests to pass)**

In `backend/app/main.py`, add `fundamentals` to the router imports:
```python
from app.routers import (
    asset_classes, asset_weights, transactions,
    stocks, crypto, portfolio, recommendations, quarantine,
    fundamentals,
)
```
And add after the last `include_router` call:
```python
app.include_router(fundamentals.router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest tests/test_routers/test_fundamentals.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/fundamentals.py backend/tests/test_routers/test_fundamentals.py backend/app/main.py
git commit -m "feat: add fundamentals API router with scores, detail, and refresh endpoints"
```

---

### Task 7: Scheduler Wiring (Config + Lifespan)

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`

**Depends on:** Task 5

- [ ] **Step 1: Add config settings**

In `backend/app/config.py`, add these fields to the `Settings` class:
```python
    enable_fundamentals_scorer: bool = True
    fundamentals_scorer_day: str = "sun"
    fundamentals_scorer_hour: int = 3
```

- [ ] **Step 2: Add scheduler function and register in lifespan**

In `backend/app/main.py`, add the scheduler function (after `_run_dividend_scrape`):
```python
def _run_fundamentals_score():
    from app.database import SessionLocal
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.finnhub import FinnhubProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    scheduler = FundamentalsScoreScheduler(
        finnhub_provider=FinnhubProvider(api_key=settings.finnhub_api_key, base_url=settings.finnhub_base_url),
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

In the `lifespan` function, after the dividend scraper registration block, add:
```python
        if settings.enable_fundamentals_scorer:
            bg_scheduler.add_job(
                _run_fundamentals_score, "cron",
                day_of_week=settings.fundamentals_scorer_day,
                hour=settings.fundamentals_scorer_hour,
                id="fundamentals_score",
            )
            logger.info(
                f"Fundamentals scorer scheduled ({settings.fundamentals_scorer_day} at {settings.fundamentals_scorer_hour}:00 UTC)"
            )
```

- [ ] **Step 3: Verify app starts without errors**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && ENABLE_SCHEDULER=false python -c "from app.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Run the full backend test suite**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/main.py
git commit -m "feat: register fundamentals scorer scheduler and router in app"
```

---

## Chunk 3: Frontend

### Task 8: Frontend Types + useFundamentals Hook

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/hooks/useFundamentals.ts`

- [ ] **Step 1: Add TypeScript types**

Add to `frontend/src/types/index.ts`:
```typescript
export interface FundamentalsScore {
  symbol: string;
  ipo_years: number | null;
  ipo_rating: "green" | "yellow" | "red";
  eps_growth_pct: number | null;
  eps_rating: "green" | "yellow" | "red";
  current_net_debt_ebitda: number | null;
  high_debt_years_pct: number | null;
  debt_rating: "green" | "yellow" | "red";
  profitable_years_pct: number | null;
  profit_rating: "green" | "yellow" | "red";
  composite_score: number;
  updated_at: string | null;
}

export interface FundamentalsDetail extends FundamentalsScore {
  raw_data: Array<{
    year: number;
    eps: number;
    net_income: number;
    net_debt_ebitda: number;
  }> | null;
}
```

- [ ] **Step 2: Create useFundamentals hook**

```typescript
// frontend/src/hooks/useFundamentals.ts
import { useCallback, useEffect, useState } from "react";
import api from "../services/api";
import type { FundamentalsDetail, FundamentalsScore } from "../types";

export function useFundamentals() {
  const [scores, setScores] = useState<FundamentalsScore[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchScores = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await api.get<FundamentalsScore[]>("/fundamentals/scores");
      setScores(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch scores");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScores();
  }, [fetchScores]);

  return { scores, loading, error, refresh: fetchScores };
}

export function useFundamentalsDetail(symbol: string) {
  const [detail, setDetail] = useState<FundamentalsDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await api.get<FundamentalsDetail>(`/fundamentals/${symbol}`);
      setDetail(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch detail");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  const refreshScore = useCallback(async () => {
    try {
      setLoading(true);
      const resp = await api.post<FundamentalsDetail>(`/fundamentals/${symbol}/refresh`);
      setDetail(resp.data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to refresh score");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  return { detail, loading, error, refresh: refreshScore };
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/hooks/useFundamentals.ts
git commit -m "feat: add FundamentalsScore types and useFundamentals hook"
```

---

### Task 9: HoldingsTable Score Column

**Files:**
- Modify: `frontend/src/components/HoldingsTable.tsx`
- Modify: `frontend/src/pages/Portfolio.tsx`

**Depends on:** Task 8

> **Architecture note:** HoldingsTable has a 3-level component hierarchy: `HoldingsTable` → `GroupSection` → `HoldingRows`. The `fundamentalsScores` prop must be threaded through all three. The table currently has 10 columns (Symbol, Qty, Avg Price, Current Price, Current Value, Gain/Loss, Target %, Actual %, Div, Actions). Adding "Score" makes 11. All `colSpan` values in group headers and expanded rows must be updated.

- [ ] **Step 1: Add score prop and imports to HoldingsTable**

In `frontend/src/components/HoldingsTable.tsx`:

Add import at top:
```typescript
import { useNavigate } from "react-router-dom";
import type { Holding, Transaction, QuarantineStatus, AssetClass, FundamentalsScore } from "../types";
```

Add `fundamentalsScores` to `HoldingsTableProps` interface (after `dividendsBySymbol`):
```typescript
  fundamentalsScores?: FundamentalsScore[];
```

- [ ] **Step 2: Add score lookup helper and thread prop to GroupSection**

Inside the `HoldingsTable` component function, add:
```typescript
  const navigate = useNavigate();

  const scoreMap = new Map(
    (fundamentalsScores ?? []).map((s) => [s.symbol, s])
  );
```

In the `<thead>`, add a new `<th>` between "Div" and the Actions column (between line 197 and 198):
```html
<th className="text-right px-3 py-2">Score</th>
```

Pass `scoreMap` and `navigate` to `GroupSection`:
```tsx
<GroupSection
  key={group.classId}
  {...existingProps}
  scoreMap={scoreMap}
  onNavigateScore={(symbol) => navigate(`/fundamentals/${symbol}`)}
/>
```

- [ ] **Step 3: Thread through GroupSectionProps → HoldingRows**

Add to `GroupSectionProps` interface:
```typescript
  scoreMap: Map<string, FundamentalsScore>;
  onNavigateScore: (symbol: string) => void;
```

In `GroupSection` function, destructure the new props and update:

1. **Group header row** — update colSpan values. Currently: `<td colSpan={4}>` (Symbol through Current Price), `<td>` (Current Value), `<td colSpan={3}>` (Gain/Loss through Actual %), `<td>` (Div), `<td>` (Actions). Add one empty `<td />` for the new Score column between Div and Actions:
```tsx
{/* Group header row */}
<tr ...>
  <td colSpan={4} ...>{/* class name */}</td>
  <td ...>{/* group total */}</td>
  <td colSpan={3} />
  <td ...>{/* group div total */}</td>
  <td />  {/* Score column — empty in group header */}
  <td />  {/* Actions */}
</tr>
```

2. **Pass to HoldingRows:**
```tsx
<HoldingRows
  key={h.symbol}
  {...existingProps}
  score={scoreMap.get(h.symbol)}
  onNavigateScore={() => onNavigateScore(h.symbol)}
/>
```

- [ ] **Step 4: Add score cell to HoldingRows**

Add to `HoldingRowsProps` interface:
```typescript
  score?: FundamentalsScore;
  onNavigateScore: () => void;
```

In `HoldingRows` function, add a helper:
```typescript
const scoreColor = (value: number) => {
  if (value >= 90) return "var(--color-positive)";
  if (value >= 60) return "var(--color-warning)";
  return "var(--color-negative)";
};
```

Add a new `<td>` in the holding row, between the Div column and the Actions column (between the dividend `<td>` at line ~468 and the actions `<td>` at line ~469):
```tsx
<td className="px-3 py-2 text-right">
  {score ? (
    <span
      style={{ color: scoreColor(score.composite_score), cursor: "pointer", fontWeight: 600 }}
      onClick={(e) => { e.stopPropagation(); onNavigateScore(); }}
      title={`IPO: ${score.ipo_rating} | EPS: ${score.eps_rating} | Debt: ${score.debt_rating} | Profit: ${score.profit_rating}`}
    >
      {score.composite_score}%
    </span>
  ) : (
    <span className="text-text-muted">—</span>
  )}
</td>
```

Update the expanded transaction row `colSpan` from 10 to 11:
```tsx
<td colSpan={11} className="px-4 py-3 bg-[var(--glass-row-alt)] rounded-lg">
```

- [ ] **Step 5: Wire up in Portfolio page**

In `frontend/src/pages/Portfolio.tsx`, add:
```typescript
import { useFundamentals } from "../hooks/useFundamentals";
```

Inside the component:
```typescript
const { scores: fundamentalsScores } = useFundamentals();
```

Pass to HoldingsTable:
```tsx
<HoldingsTable
  {...existingProps}
  fundamentalsScores={fundamentalsScores}
/>
```

- [ ] **Step 6: Verify the app compiles**

Run: `cd /Users/felipediaspereira/Code/project-fin/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/HoldingsTable.tsx frontend/src/pages/Portfolio.tsx
git commit -m "feat: add fundamentals score column to HoldingsTable"
```

---

### Task 10: Fundamentals Analysis Page

**Files:**
- Create: `frontend/src/pages/Fundamentals.tsx`
- Modify: `frontend/src/App.tsx`

**Depends on:** Task 8

> **Note:** The Fundamentals page is accessed by clicking a score in HoldingsTable, not via sidebar navigation. No Sidebar changes needed.

- [ ] **Step 1: Create the Fundamentals page**

```tsx
// frontend/src/pages/Fundamentals.tsx
import { useParams, useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer,
  LineChart, Line, ReferenceLine, Cell,
} from "recharts";
import { useFundamentalsDetail } from "../hooks/useFundamentals";

const RATING_COLORS = { green: "#22c55e", yellow: "#eab308", red: "#ef4444" };

function RatingDot({ rating }: { rating: "green" | "yellow" | "red" }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 12,
        height: 12,
        borderRadius: "50%",
        backgroundColor: RATING_COLORS[rating],
        marginRight: 8,
      }}
    />
  );
}

export default function Fundamentals() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const { detail, loading, error, refresh } = useFundamentalsDetail(symbol || "");

  if (!symbol) return null;

  if (loading && !detail) {
    return <div className="p-8 text-secondary">Loading fundamentals for {symbol}...</div>;
  }

  if (error) {
    return <div className="p-8 text-negative">Error: {error}</div>;
  }

  if (!detail) {
    return <div className="p-8 text-secondary">No fundamentals data available for {symbol}.</div>;
  }

  const rawData = detail.raw_data || [];

  const scoreColor = detail.composite_score >= 90
    ? RATING_COLORS.green
    : detail.composite_score >= 60
      ? RATING_COLORS.yellow
      : RATING_COLORS.red;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="text-secondary hover:text-primary"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold text-primary">{symbol} Fundamentals</h1>
        <button
          onClick={refresh}
          disabled={loading}
          className="ml-auto px-4 py-2 rounded-[10px] text-sm font-medium"
          style={{ background: "var(--glass-card-bg)", border: "1px solid var(--glass-border)" }}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Score Breakdown Card */}
      <div
        className="p-6 rounded-[14px]"
        style={{ background: "var(--glass-card-bg)", border: "1px solid var(--glass-border)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary">Score Breakdown</h2>
          <span className="text-3xl font-bold" style={{ color: scoreColor }}>
            {detail.composite_score}%
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center">
            <RatingDot rating={detail.ipo_rating} />
            <span className="text-secondary">IPO Age: {detail.ipo_years ?? "N/A"} years</span>
          </div>
          <div className="flex items-center">
            <RatingDot rating={detail.eps_rating} />
            <span className="text-secondary">
              EPS Growth: {detail.eps_growth_pct != null ? `${detail.eps_growth_pct}%` : "N/A"} of years
            </span>
          </div>
          <div className="flex items-center">
            <RatingDot rating={detail.debt_rating} />
            <span className="text-secondary">
              Net Debt/EBITDA: {detail.current_net_debt_ebitda != null ? detail.current_net_debt_ebitda.toFixed(1) : "N/A"}x
            </span>
          </div>
          <div className="flex items-center">
            <RatingDot rating={detail.profit_rating} />
            <span className="text-secondary">
              Profitability: {detail.profitable_years_pct != null ? `${detail.profitable_years_pct}%` : "N/A"} of years
            </span>
          </div>
        </div>
      </div>

      {/* EPS Growth Chart */}
      {rawData.length > 0 && (
        <div
          className="p-6 rounded-[14px]"
          style={{ background: "var(--glass-card-bg)", border: "1px solid var(--glass-border)" }}
        >
          <h2 className="text-lg font-semibold text-primary mb-4">EPS History</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={rawData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
              <XAxis dataKey="year" stroke="var(--color-text-secondary)" />
              <YAxis stroke="var(--color-text-secondary)" />
              <Tooltip />
              <Bar dataKey="eps">
                {rawData.map((entry, index) => (
                  <Cell
                    key={`eps-${index}`}
                    fill={
                      index === 0
                        ? "#8884d8"
                        : entry.eps > rawData[index - 1].eps
                          ? RATING_COLORS.green
                          : RATING_COLORS.red
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Net Debt/EBITDA Chart */}
      {rawData.length > 0 && (
        <div
          className="p-6 rounded-[14px]"
          style={{ background: "var(--glass-card-bg)", border: "1px solid var(--glass-border)" }}
        >
          <h2 className="text-lg font-semibold text-primary mb-4">Net Debt / EBITDA</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={rawData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
              <XAxis dataKey="year" stroke="var(--color-text-secondary)" />
              <YAxis stroke="var(--color-text-secondary)" />
              <Tooltip />
              <ReferenceLine y={3} stroke={RATING_COLORS.red} strokeDasharray="5 5" label="Threshold (3x)" />
              <Line type="monotone" dataKey="net_debt_ebitda" stroke="#8884d8" strokeWidth={2} dot />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Profitability Chart */}
      {rawData.length > 0 && (
        <div
          className="p-6 rounded-[14px]"
          style={{ background: "var(--glass-card-bg)", border: "1px solid var(--glass-border)" }}
        >
          <h2 className="text-lg font-semibold text-primary mb-4">Net Income History</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={rawData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
              <XAxis dataKey="year" stroke="var(--color-text-secondary)" />
              <YAxis stroke="var(--color-text-secondary)" />
              <Tooltip />
              <Bar dataKey="net_income">
                {rawData.map((entry, index) => (
                  <Cell
                    key={`income-${index}`}
                    fill={entry.net_income > 0 ? RATING_COLORS.green : RATING_COLORS.red}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {detail.updated_at && (
        <p className="text-sm text-muted">
          Last updated: {new Date(detail.updated_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

In `frontend/src/App.tsx`, add import:
```typescript
import Fundamentals from "./pages/Fundamentals";
```

Add route inside `<Routes>`:
```tsx
<Route path="/fundamentals/:symbol" element={<Fundamentals />} />
```

- [ ] **Step 3: Verify the app compiles**

Run: `cd /Users/felipediaspereira/Code/project-fin/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Fundamentals.tsx frontend/src/App.tsx
git commit -m "feat: add fundamentals analysis page with score breakdown and charts"
```

---

## Chunk 4: Integration Test + Final Verification

### Task 11: End-to-End Verification

- [ ] **Step 1: Run full backend test suite**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && python -m pytest -v`
Expected: All PASS

- [ ] **Step 2: Run frontend type check**

Run: `cd /Users/felipediaspereira/Code/project-fin/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Run frontend build**

Run: `cd /Users/felipediaspereira/Code/project-fin/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Verify backend starts**

Run: `cd /Users/felipediaspereira/Code/project-fin/backend && ENABLE_SCHEDULER=false timeout 5 python -m uvicorn app.main:app --port 8099 || true`
Expected: Server starts (times out after 5s which is fine)

---

## Parallelization Guide

Tasks are designed for maximum parallel execution:

```
Group A (independent — run in parallel):
  Task 1: DB Model
  Task 2: Scoring Engine
  Task 3: Finnhub Provider
  Task 4: Brapi + DadosDeMercado Providers

Group B (depends on Group A — run in parallel):
  Task 5: Scheduler (needs 1, 2, 3, 4)
  Task 6: Router + registration (needs 1; also registers router in main.py)

Group C (depends on Group B):
  Task 7: Scheduler Wiring (needs 5, 6)

Group D (independent of backend — run in parallel with B/C):
  Task 8: Frontend Types + Hook
  Task 9: HoldingsTable Column (needs 8)
  Task 10: Analysis Page (needs 8)

Group E (depends on all):
  Task 11: Final Verification
```
