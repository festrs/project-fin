from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight

from app.models.transaction import Transaction
from app.money import Money, Currency
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

            buy_qty = buy_agg.total_qty  # Do NOT default to 0

            if buy_qty is None:
                # Value-based (fixed income): no quantity, just total_value
                buy_value_raw = buy_agg.total_value or Decimal("0")
                sell_value_raw = (
                    self.db.query(func.sum(Transaction.total_value))
                    .filter(
                        Transaction.user_id == user_id,
                        Transaction.asset_symbol == symbol,
                        Transaction.type == "sell",
                    )
                    .scalar()
                ) or Decimal("0")
                net_value_raw = buy_value_raw - sell_value_raw
                if net_value_raw <= 0:
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
                currency_code = tx_currency[0] if tx_currency else "BRL"
                currency = Currency.from_code(currency_code)
                holdings.append(
                    {
                        "symbol": symbol,
                        "asset_class_id": asset_class_id,
                        "quantity": None,
                        "avg_price": None,
                        "total_cost": Money(net_value_raw, currency),
                        "currency": currency,
                    }
                )
            else:
                # Quantity-based: totals reflect transaction history directly
                # (splits and bonificações are recorded as separate buy transactions)
                buy_qty = buy_qty or 0
                buy_value_raw = buy_agg.total_value or Decimal("0")
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
                avg_price_raw = buy_value_raw / Decimal(str(buy_qty)) if buy_qty > 0 else Decimal("0")
                total_cost_raw = avg_price_raw * Decimal(str(net_qty))

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
                currency_code = tx_currency[0] if tx_currency else "BRL"
                currency = Currency.from_code(currency_code)

                holdings.append(
                    {
                        "symbol": symbol,
                        "asset_class_id": asset_class_id,
                        "quantity": net_qty,
                        "avg_price": Money(avg_price_raw, currency),
                        "total_cost": Money(total_cost_raw, currency),
                        "currency": currency,
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
            if ac.is_emergency_reserve:
                continue
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
        db_only: bool = False,
    ) -> list[dict]:
        """Enrich holdings with current prices, values, gain/loss, and weights."""

        # Separate quantity-based and value-based holdings
        qty_holdings = [h for h in holdings if h["quantity"] is not None]
        val_holdings = [h for h in holdings if h["quantity"] is None]

        def fetch_price(holding: dict) -> tuple[str, "Money | None"]:
            symbol = holding["symbol"]
            class_info = class_map.get(holding["asset_class_id"], {})
            class_name = class_info.get("name", "")
            country = class_info.get("country", "US")
            if class_name in CRYPTO_CLASS_NAMES:
                coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
                if coin_id:
                    return symbol, market_data.get_quote_safe(coin_id, is_crypto=True, db_only=db_only)
            return symbol, market_data.get_quote_safe(symbol, is_crypto=False, country=country, db=db, db_only=db_only)

        # Fetch prices in parallel (only for quantity-based holdings)
        prices: dict[str, "Money | None"] = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_price, h): h for h in qty_holdings}
            for future in as_completed(futures):
                symbol, price = future.result()
                prices[symbol] = price

        # Calculate total portfolio value (excluding emergency reserve)
        total_value = Decimal("0")
        for h in qty_holdings:
            if class_map.get(h["asset_class_id"], {}).get("is_emergency_reserve"):
                continue
            price = prices.get(h["symbol"])
            if price is not None:
                total_value += price.amount * Decimal(str(h["quantity"]))
        for h in val_holdings:
            if class_map.get(h["asset_class_id"], {}).get("is_emergency_reserve"):
                continue
            total_value += h["total_cost"].amount

        # Enrich each holding
        enriched = []
        for h in holdings:
            class_info = class_map.get(h["asset_class_id"], {})
            is_reserve = class_info.get("is_emergency_reserve", False)
            class_target = class_info.get("target_weight", 0.0)
            asset_target = weight_map.get(h["symbol"], 0.0)
            effective_target = class_target * asset_target / 100
            if h["quantity"] is None:
                # Fixed income: use the currency from the holding
                current_value = h["total_cost"]  # already Money
                actual_weight = float(current_value.amount / total_value * 100) if total_value > 0 else 0.0
                if is_reserve:
                    actual_weight = 0.0
                enriched.append({
                    **h,
                    "current_price": None,
                    "current_value": current_value,
                    "gain_loss": None,
                    "target_weight": effective_target,
                    "actual_weight": actual_weight,
                })
            else:
                price = prices.get(h["symbol"])
                if price is not None and price.currency == h["avg_price"].currency:
                    current_value = price * Decimal(str(h["quantity"]))  # Money * scalar -> Money
                    gain_loss = (price - h["avg_price"]) * Decimal(str(h["quantity"]))  # Money - Money -> Money, then * scalar
                    actual_weight = float(current_value.amount / total_value * 100) if total_value > 0 else 0.0
                    if is_reserve:
                        actual_weight = 0.0
                elif price is not None:
                    # Currency mismatch between market data and transaction — use price currency
                    current_value = price * Decimal(str(h["quantity"]))
                    gain_loss = None  # Can't compute gain/loss across currencies
                    actual_weight = float(current_value.amount / total_value * 100) if total_value > 0 else 0.0
                    if is_reserve:
                        actual_weight = 0.0
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
