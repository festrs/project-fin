"""
Fundamentals Scorer — pure functions, no DB or provider dependencies.
Scores are based on four evaluators, each returning a (rating, points) tuple.
"""

from __future__ import annotations


def evaluate_ipo(ipo_years: int | None) -> tuple[str, int]:
    """
    Evaluate IPO age.
    >10 years → ("green", 25)
    5-10 years (inclusive) → ("yellow", 15)
    <5 years or None → ("red", 0)
    """
    if ipo_years is None or ipo_years < 5:
        return ("red", 0)
    if ipo_years <= 10:
        return ("yellow", 15)
    return ("green", 25)


def evaluate_eps_growth(eps_history: list[float]) -> tuple[str, int]:
    """
    Evaluate EPS growth consistency.
    Requires at least 5 data points.
    Count YoY growth years (eps[i] > eps[i-1]).
    >50% growth years → green, 40-50% → yellow, <40% → red.
    """
    if len(eps_history) < 5:
        return ("red", 0)

    comparisons = len(eps_history) - 1
    growth_years = sum(
        1 for i in range(1, len(eps_history)) if eps_history[i] > eps_history[i - 1]
    )
    growth_pct = growth_years / comparisons

    if growth_pct > 0.50:
        return ("green", 25)
    if growth_pct >= 0.40:
        return ("yellow", 15)
    return ("red", 0)


def evaluate_debt(
    current_ratio: float | None, debt_history: list[float]
) -> tuple[str, int]:
    """
    Evaluate debt level.
    Requires at least 5 data points in debt_history and a non-None current_ratio.
    Green: current_ratio < 3 AND ≤30% of historical years have ratio > 3.
    Yellow: only one condition met.
    Red: neither condition met (or insufficient data / None current_ratio).
    """
    if current_ratio is None or len(debt_history) < 5:
        return ("red", 0)

    current_ok = current_ratio < 3
    high_years = sum(1 for r in debt_history if r > 3)
    high_pct = high_years / len(debt_history)
    history_ok = high_pct <= 0.30

    if current_ok and history_ok:
        return ("green", 25)
    if current_ok or history_ok:
        return ("yellow", 15)
    return ("red", 0)


def evaluate_profitability(net_income_history: list[float]) -> tuple[str, int]:
    """
    Evaluate profitability history.
    Requires at least 5 data points.
    Green: ALL profitable OR last 15 consecutive years profitable.
    Yellow: ≥80% profitable.
    Red: <80%.
    """
    if len(net_income_history) < 5:
        return ("red", 0)

    profitable = [v > 0 for v in net_income_history]
    total = len(profitable)
    profitable_count = sum(profitable)
    profitable_pct = profitable_count / total

    all_profitable = profitable_count == total

    # Check last 15 consecutive profitable years
    last_15_profitable = False
    if total >= 15:
        last_15_profitable = all(profitable[-15:])

    if all_profitable or last_15_profitable:
        return ("green", 25)
    if profitable_pct >= 0.80:
        return ("yellow", 15)
    return ("red", 0)


def compute_composite_score(ratings: list[tuple[str, int]]) -> int:
    """Sum all point values. Range 0-100."""
    return sum(points for _, points in ratings)


def score_fundamentals(data: dict) -> dict:
    """
    Orchestrator: calls all evaluators, returns a full breakdown dict.

    Expected keys in data:
        ipo_years: int | None
        eps_history: list[float]
        current_ratio: float | None
        debt_history: list[float]
        net_income_history: list[float]
    """
    ipo_years: int | None = data.get("ipo_years")
    eps_history: list[float] = data.get("eps_history") or []
    current_ratio: float | None = data.get("current_ratio")
    debt_history: list[float] = data.get("debt_history") or []
    net_income_history: list[float] = data.get("net_income_history") or []

    ipo_rating, ipo_score = evaluate_ipo(ipo_years)
    eps_rating, eps_score = evaluate_eps_growth(eps_history)
    debt_rating, debt_score = evaluate_debt(current_ratio, debt_history)
    profit_rating, profit_score = evaluate_profitability(net_income_history)

    composite = compute_composite_score([
        (ipo_rating, ipo_score),
        (eps_rating, eps_score),
        (debt_rating, debt_score),
        (profit_rating, profit_score),
    ])

    # Derived metrics for transparency
    eps_comparisons = len(eps_history) - 1 if len(eps_history) >= 2 else 0
    eps_growth_years = (
        sum(1 for i in range(1, len(eps_history)) if eps_history[i] > eps_history[i - 1])
        if eps_comparisons > 0
        else 0
    )
    eps_growth_pct = round(eps_growth_years / eps_comparisons * 100, 1) if eps_comparisons > 0 else 0.0

    debt_high_years = sum(1 for r in debt_history if r > 3) if debt_history else 0
    high_debt_years_pct = round(debt_high_years / len(debt_history) * 100, 1) if debt_history else 0.0

    net_income_profitable = sum(1 for v in net_income_history if v > 0)
    profitable_years_pct = (
        round(net_income_profitable / len(net_income_history) * 100, 1)
        if net_income_history
        else 0.0
    )

    return {
        "ipo_years": ipo_years,
        "ipo_rating": ipo_rating,
        "eps_growth_pct": eps_growth_pct,
        "eps_rating": eps_rating,
        "current_net_debt_ebitda": current_ratio,
        "high_debt_years_pct": high_debt_years_pct,
        "debt_rating": debt_rating,
        "profitable_years_pct": profitable_years_pct,
        "profit_rating": profit_rating,
        "composite_score": composite,
    }
