from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService
from app.services.quarantine import QuarantineService

CRYPTO_COINGECKO_MAP = {
    "BTC": "bitcoin", "BTC-USD": "bitcoin",
    "ETH": "ethereum", "ETH-USD": "ethereum",
    "USDT": "tether", "USDT-USD": "tether",
    "USDC": "usd-coin", "USDC-USD": "usd-coin",
    "DAI": "dai", "DAI-USD": "dai",
}
CRYPTO_CLASS_NAMES = {"Crypto", "Cryptos", "Stablecoins"}


class RecommendationService:
    def __init__(self, db: Session, market_data_service: MarketDataService | None = None):
        self.db = db
        self.market_data = market_data_service or MarketDataService()
        self.portfolio_service = PortfolioService(db)
        self.quarantine_service = QuarantineService(db)

    def _get_current_price(self, symbol: str, class_name: str) -> float:
        if class_name in CRYPTO_CLASS_NAMES:
            coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
            if coin_id:
                quote = self.market_data.get_crypto_quote(coin_id)
                return quote["current_price"]
        quote = self.market_data.get_stock_quote(symbol)
        return quote["current_price"]

    def get_recommendations(self, user_id: str, count: int = 2) -> list[dict]:
        # Get quarantine statuses
        quarantine_statuses = self.quarantine_service.get_all_statuses(user_id)
        quarantined_symbols = {
            s.asset_symbol for s in quarantine_statuses if s.is_quarantined
        }

        # Get holdings
        holdings = self.portfolio_service.get_holdings(user_id)

        # Build class name map
        asset_classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id)
            .all()
        )
        class_map = {ac.id: ac for ac in asset_classes}

        # Build asset weight map: symbol -> (class_target_weight, asset_target_weight, class_name)
        asset_info: dict[str, dict] = {}
        for ac in asset_classes:
            weights = (
                self.db.query(AssetWeight)
                .filter(AssetWeight.asset_class_id == ac.id)
                .all()
            )
            for aw in weights:
                asset_info[aw.symbol] = {
                    "class_target_weight": ac.target_weight,
                    "asset_target_weight": aw.target_weight,
                    "class_name": ac.name,
                }

        # Calculate current values using market prices
        asset_values: dict[str, float] = {}
        for h in holdings:
            ac = class_map.get(h["asset_class_id"])
            class_name = ac.name if ac else ""
            price = self._get_current_price(h["symbol"], class_name)
            asset_values[h["symbol"]] = h["quantity"] * price

        total_value = sum(asset_values.values())
        if total_value == 0:
            return []

        # Calculate recommendations
        recommendations = []
        for h in holdings:
            symbol = h["symbol"]
            if symbol in quarantined_symbols:
                continue

            info = asset_info.get(symbol)
            if not info:
                continue

            effective_target = (
                info["class_target_weight"] * info["asset_target_weight"] / 100
            )
            actual_weight = (asset_values.get(symbol, 0) / total_value) * 100
            diff = effective_target - actual_weight

            recommendations.append(
                {
                    "symbol": symbol,
                    "class_name": info["class_name"],
                    "effective_target": effective_target,
                    "actual_weight": actual_weight,
                    "diff": diff,
                }
            )

        # Sort by diff descending (most underweight first)
        recommendations.sort(key=lambda r: r["diff"], reverse=True)
        return recommendations[:count]
