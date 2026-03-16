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
            ipo_years=45,
            ipo_rating="green",
            eps_growth_pct=80.0,
            eps_rating="green",
            current_net_debt_ebitda=1.2,
            high_debt_years_pct=10.0,
            debt_rating="green",
            profitable_years_pct=100.0,
            profit_rating="green",
            composite_score=100,
            raw_data=[{"year": 2025, "eps": 6.0}],
        ),
        FundamentalsScore(
            symbol="PETR4.SA",
            ipo_years=20,
            ipo_rating="green",
            eps_growth_pct=45.0,
            eps_rating="yellow",
            current_net_debt_ebitda=2.5,
            high_debt_years_pct=20.0,
            debt_rating="green",
            profitable_years_pct=85.0,
            profit_rating="yellow",
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
        headers = {"X-User-Id": user.id}
        resp = client.get("/api/fundamentals/scores", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_returns_score_fields(self, client, db):
        user = _seed_scores(db)
        headers = {"X-User-Id": user.id}
        resp = client.get("/api/fundamentals/scores", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        aapl = next(s for s in data if s["symbol"] == "AAPL")
        assert aapl["ipo_years"] == 45
        assert aapl["ipo_rating"] == "green"
        assert aapl["eps_growth_pct"] == 80.0
        assert aapl["composite_score"] == 100
        # scores endpoint should NOT include raw_data
        assert "raw_data" not in aapl


class TestGetDetail:
    def test_returns_score_with_raw_data(self, client, db):
        user = _seed_scores(db)
        headers = {"X-User-Id": user.id}
        resp = client.get("/api/fundamentals/AAPL", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
        assert "raw_data" in data
        assert data["raw_data"] == [{"year": 2025, "eps": 6.0}]

    def test_returns_404_for_unknown(self, client, db):
        user = _seed_scores(db)
        headers = {"X-User-Id": user.id}
        resp = client.get("/api/fundamentals/UNKNOWN", headers=headers)
        assert resp.status_code == 404


class TestRefresh:
    def test_returns_200_with_refreshed_score(self, client, db, monkeypatch):
        user = _seed_scores(db)
        headers = {"X-User-Id": user.id}

        monkeypatch.setattr(
            "app.routers.fundamentals._refresh_score",
            lambda symbol, db: None,
        )

        resp = client.post("/api/fundamentals/AAPL/refresh", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == "AAPL"
