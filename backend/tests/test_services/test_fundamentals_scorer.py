import pytest
from app.services.fundamentals_scorer import (
    evaluate_ipo,
    evaluate_eps_growth,
    evaluate_debt,
    evaluate_profitability,
    compute_composite_score,
    score_fundamentals,
)


class TestEvaluateIpo:
    def test_green_over_10_years(self):
        assert evaluate_ipo(15) == ("green", 25)

    def test_yellow_between_5_and_10(self):
        assert evaluate_ipo(7) == ("yellow", 15)

    def test_red_under_5_years(self):
        assert evaluate_ipo(3) == ("red", 0)

    def test_red_when_none(self):
        assert evaluate_ipo(None) == ("red", 0)

    def test_boundary_exactly_10(self):
        assert evaluate_ipo(10) == ("yellow", 15)

    def test_boundary_exactly_5(self):
        assert evaluate_ipo(5) == ("yellow", 15)


class TestEvaluateEpsGrowth:
    def test_green_over_50_pct(self):
        # 5 YoY growth out of 5 comparisons = 100%
        result = evaluate_eps_growth([1, 2, 3, 4, 5, 6])
        assert result == ("green", 25)

    def test_yellow_between_40_and_50_pct(self):
        # [1,2,3,4,5,4,3,2,1,0.5,0.6] -> 10 comparisons
        # growth at: 1→2, 2→3, 3→4, 4→5 (4 up), 5→4 (down), 4→3 (down), 3→2 (down), 2→1 (down), 1→0.5 (down), 0.5→0.6 (up)
        # 5 growth out of 10 = 50% → yellow (not > 50%)
        result = evaluate_eps_growth([1, 2, 3, 4, 5, 4, 3, 2, 1, 0.5, 0.6])
        assert result == ("yellow", 15)

    def test_red_under_40_pct(self):
        # [5,4,3,2,1,0.5] -> 0 growth out of 5 = 0%
        result = evaluate_eps_growth([5, 4, 3, 2, 1, 0.5])
        assert result == ("red", 0)

    def test_red_insufficient_data(self):
        result = evaluate_eps_growth([1, 2, 3])
        assert result == ("red", 0)

    def test_red_empty_data(self):
        result = evaluate_eps_growth([])
        assert result == ("red", 0)

    def test_boundary_exactly_50_pct_is_yellow(self):
        # 11 items, 10 comparisons, exactly 5 growth = 50% → yellow (not > 50%)
        # Build: alternating up/down starting from base
        # indices 0-10: up, down, up, down, up, down, up, down, up, down, same
        # 5 growths, 5 declines => 50%
        data = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1]
        result = evaluate_eps_growth(data)
        assert result == ("yellow", 15)


class TestEvaluateDebt:
    def test_green_low_current_and_historically(self):
        # current=1.5 (<3), history=[1,2,1.5,2.5,1] -> 0/5 > 3 = 0% ≤ 30%
        result = evaluate_debt(1.5, [1, 2, 1.5, 2.5, 1])
        assert result == ("green", 25)

    def test_yellow_only_current_low(self):
        # current=1.5 (<3 ✓), history=[4,5,4,2,1.5] -> 3/5 > 3 = 60% > 30% ✗
        result = evaluate_debt(1.5, [4, 5, 4, 2, 1.5])
        assert result == ("yellow", 15)

    def test_yellow_only_history_good(self):
        # current=3.5 (≥3 ✗), history=[1,2,1.5,2.5,1] -> 0/5 > 3 = 0% ≤ 30% ✓
        result = evaluate_debt(3.5, [1, 2, 1.5, 2.5, 1])
        assert result == ("yellow", 15)

    def test_red_both_bad(self):
        # current=4.0 (≥3 ✗), history=[4,5,4,3.5,6] -> 5/5 > 3 = 100% > 30% ✗
        result = evaluate_debt(4.0, [4, 5, 4, 3.5, 6])
        assert result == ("red", 0)

    def test_red_insufficient_data(self):
        result = evaluate_debt(1.5, [1, 2])
        assert result == ("red", 0)

    def test_red_none_current(self):
        result = evaluate_debt(None, [1, 2, 1.5, 2.5, 1])
        assert result == ("red", 0)


class TestEvaluateProfitability:
    def test_green_all_profitable(self):
        result = evaluate_profitability([10, 20, 15, 25, 30])
        assert result == ("green", 25)

    def test_green_last_15_consecutive(self):
        # 5 unprofitable at start, then 15 consecutive profitable
        data = [-1, -2, -3, -4, -5] + [10] * 15
        result = evaluate_profitability(data)
        assert result == ("green", 25)

    def test_yellow_80_pct(self):
        # [10, 20, -5, 15, 25] -> 4/5 profitable = 80%
        result = evaluate_profitability([10, 20, -5, 15, 25])
        assert result == ("yellow", 15)

    def test_red_under_80_pct(self):
        # [10, -5, -3, 15, 25] -> 3/5 profitable = 60%
        result = evaluate_profitability([10, -5, -3, 15, 25])
        assert result == ("red", 0)

    def test_red_insufficient_data(self):
        result = evaluate_profitability([10, 20])
        assert result == ("red", 0)

    def test_red_empty(self):
        result = evaluate_profitability([])
        assert result == ("red", 0)


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
        # green(25) + red(0) + yellow(15) + green(25) = 65
        ratings = [("green", 25), ("red", 0), ("yellow", 15), ("green", 25)]
        assert compute_composite_score(ratings) == 65


class TestScoreFundamentals:
    def test_full_scoring(self):
        data = {
            "ipo_years": 15,
            "eps_history": [1, 2, 3, 4, 5, 6],
            "current_net_debt_ebitda": 1.5,
            "debt_history": [1, 2, 1.5, 2.5, 1],
            "net_income_history": [10, 20, 15, 25, 30],
        }
        result = score_fundamentals(data)
        assert result["composite_score"] == 100
        assert result["ipo_rating"] == "green"
        assert result["eps_rating"] == "green"
        assert result["debt_rating"] == "green"
        assert result["profit_rating"] == "green"

    def test_missing_data_all_red(self):
        data = {
            "ipo_years": None,
            "eps_history": [],
            "current_net_debt_ebitda": None,
            "debt_history": [],
            "net_income_history": [],
        }
        result = score_fundamentals(data)
        assert result["composite_score"] == 0
        assert result["ipo_rating"] == "red"
        assert result["eps_rating"] == "red"
        assert result["debt_rating"] == "red"
        assert result["profit_rating"] == "red"
