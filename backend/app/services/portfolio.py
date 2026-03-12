from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.transaction import Transaction
from app.services.market_data import MarketDataService, CRYPTO_COINGECKO_MAP, CRYPTO_CLASS_NAMES


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

    @staticmethod
    def enrich_holdings(
        holdings: list[dict],
        class_map: dict[str, dict],
        weight_map: dict[str, float],
        market_data: MarketDataService,
        db: Session | None = None,
    ) -> list[dict]:
        """Enrich holdings with current prices, values, gain/loss, and weights."""

        def fetch_price(holding: dict) -> tuple[str, float | None]:
            symbol = holding["symbol"]
            class_info = class_map.get(holding["asset_class_id"], {})
            class_name = class_info.get("name", "")
            country = class_info.get("country", "US")
            if class_name in CRYPTO_CLASS_NAMES:
                coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
                if coin_id:
                    return symbol, market_data.get_quote_safe(coin_id, is_crypto=True)
            return symbol, market_data.get_quote_safe(symbol, is_crypto=False, country=country, db=db)

        # Fetch prices in parallel
        prices: dict[str, float | None] = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_price, h): h for h in holdings}
            for future in as_completed(futures):
                symbol, price = future.result()
                prices[symbol] = price

        # Calculate total portfolio value
        total_value = 0.0
        for h in holdings:
            price = prices.get(h["symbol"])
            if price is not None:
                total_value += h["quantity"] * price

        # Enrich each holding
        enriched = []
        for h in holdings:
            price = prices.get(h["symbol"])
            class_info = class_map.get(h["asset_class_id"], {})
            class_target = class_info.get("target_weight", 0.0)
            asset_target = weight_map.get(h["symbol"], 0.0)
            effective_target = class_target * asset_target / 100

            if price is not None:
                current_value = h["quantity"] * price
                gain_loss = (price - h["avg_price"]) * h["quantity"]
                actual_weight = (current_value / total_value * 100) if total_value > 0 else 0.0
            else:
                current_value = None
                gain_loss = None
                actual_weight = None

            enriched.append({
                **h,
                "current_price": price,
                "current_value": current_value,
                "gain_loss": gain_loss,
                "target_weight": effective_target,
                "actual_weight": actual_weight,
            })

        return enriched
