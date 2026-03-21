from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.money import Money, Currency
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.services.auth import create_access_token


def _setup(db, user_id):
    ac = AssetClass(user_id=user_id, name="Stocks", target_weight=60.0)
    db.add(ac)
    db.flush()

    aw = AssetWeight(asset_class_id=ac.id, symbol="AAPL", target_weight=100.0)
    db.add(aw)

    tx = Transaction(
        user_id=user_id,
        asset_class_id=ac.id,
        asset_symbol="AAPL",
        type="buy",
        quantity=10,
        unit_price=Decimal("150.0"),
        total_value=Decimal("1500.0"),
        currency="USD",
        tax_amount=Decimal("0.0"),
        date=date(2025, 6, 1),
    )
    db.add(tx)
    db.commit()
    return ac


@patch("app.services.recommendation.MarketDataService")
def test_get_recommendations(MockMarketData, client, default_user, db):
    _setup(db, default_user.id)

    mock_instance = MockMarketData.return_value
    mock_instance.get_stock_quote.return_value = {"current_price": Money(Decimal("175"), Currency.USD)}

    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/recommendations?count=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendations" in data


@patch("app.services.recommendation.MarketDataService")
@patch("app.routers.recommendations.fetch_exchange_rate", return_value=5.0)
def test_invest_plan_endpoint(mock_fx, MockMarketData, client, default_user, db):
    _setup(db, default_user.id)

    mock_instance = MockMarketData.return_value
    mock_instance.get_stock_quote.return_value = {"current_price": Money(Decimal("175"), Currency.USD)}

    token = create_access_token(default_user.id)
    headers = {"Authorization": f"Bearer {token}"}
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
