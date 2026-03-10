from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    def get_holdings(self, user_id: str) -> list[dict]:
        # Get all distinct symbols with their asset_class_id
        symbols = (
            self.db.query(Transaction.asset_symbol, Transaction.asset_class_id)
            .filter(Transaction.user_id == user_id)
            .distinct()
            .all()
        )

        holdings = []
        for symbol, asset_class_id in symbols:
            # Sum buys
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

            buy_qty = buy_agg.total_qty or 0
            buy_value = buy_agg.total_value or 0

            # Sum sells
            sell_agg = (
                self.db.query(
                    func.sum(Transaction.quantity).label("total_qty"),
                )
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

            holdings.append(
                {
                    "symbol": symbol,
                    "asset_class_id": asset_class_id,
                    "quantity": net_qty,
                    "avg_price": avg_price,
                    "total_cost": total_cost,
                }
            )

        return holdings

    def get_allocation(self, user_id: str) -> list[dict]:
        holdings = self.get_holdings(user_id)
        holdings_by_class: dict[str, list[dict]] = {}
        for h in holdings:
            holdings_by_class.setdefault(h["asset_class_id"], []).append(h)

        asset_classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id)
            .all()
        )

        result = []
        for ac in asset_classes:
            class_holdings = holdings_by_class.get(ac.id, [])
            if not class_holdings:
                continue

            # Get asset weights for this class
            asset_weights = (
                self.db.query(AssetWeight)
                .filter(AssetWeight.asset_class_id == ac.id)
                .all()
            )
            weight_map = {aw.symbol: aw.target_weight for aw in asset_weights}

            assets = []
            for h in class_holdings:
                assets.append(
                    {
                        "symbol": h["symbol"],
                        "quantity": h["quantity"],
                        "total_cost": h["total_cost"],
                        "target_weight": weight_map.get(h["symbol"], 0.0),
                    }
                )

            result.append(
                {
                    "class_id": ac.id,
                    "class_name": ac.name,
                    "target_weight": ac.target_weight,
                    "assets": assets,
                }
            )

        return result
