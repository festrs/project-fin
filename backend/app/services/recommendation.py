from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.money import Money, Currency
from app.services.market_data import MarketDataService, CRYPTO_COINGECKO_MAP, CRYPTO_CLASS_NAMES
from app.services.portfolio import PortfolioService
from app.services.quarantine import QuarantineService


class RecommendationService:
    def __init__(self, db: Session, market_data_service: MarketDataService | None = None):
        self.db = db
        self.market_data = market_data_service or MarketDataService()
        self.portfolio_service = PortfolioService(db)
        self.quarantine_service = QuarantineService(db)

    def _get_current_price(self, symbol: str, class_name: str, country: str = "US", db: Session | None = None) -> Money:
        if class_name in CRYPTO_CLASS_NAMES:
            coin_id = CRYPTO_COINGECKO_MAP.get(symbol)
            if coin_id:
                quote = self.market_data.get_crypto_quote(coin_id)
                return quote["current_price"]
        quote = self.market_data.get_stock_quote(symbol, country=country, db=db)
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
        asset_values: dict[str, Decimal] = {}
        for h in holdings:
            ac = class_map.get(h["asset_class_id"])
            class_name = ac.name if ac else ""
            country = ac.country if ac else "US"
            if h["quantity"] is None:
                # Value-based holding: use total_cost (now a Money object)
                asset_values[h["symbol"]] = h["total_cost"].amount
                continue
            price = self._get_current_price(h["symbol"], class_name, country=country, db=self.db)
            asset_values[h["symbol"]] = price.amount * Decimal(str(h["quantity"]))

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
            actual_weight = float(asset_values.get(symbol, Decimal("0")) / total_value * 100)
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

    def get_investment_plan(
        self,
        user_id: str,
        amount: Decimal,
        currency: str,
        count: int = 3,
        exchange_rate: Decimal | None = None,
    ) -> dict:
        """Build an investment plan distributing `amount` across top N underweight assets."""
        input_currency = Currency.from_code(currency)

        # Step 1: Get underweight assets (reuse existing logic)
        recs = self.get_recommendations(user_id, count=count)

        def _empty_result(reason: str) -> dict:
            return {
                "recommendations": [],
                "total_invested": Money(Decimal("0"), input_currency),
                "exchange_rate": float(exchange_rate) if exchange_rate else None,
                "exchange_rate_pair": "USD-BRL" if exchange_rate else None,
                "remainder": Money(amount, input_currency),
                "empty_reason": reason,
            }

        # Determine why there are no recommendations
        if not recs:
            holdings = self.portfolio_service.get_holdings(user_id)
            if not holdings:
                return _empty_result("no_holdings")
            return _empty_result("all_quarantined")

        # Step 2: Build asset class type map for rounding decisions
        asset_classes = (
            self.db.query(AssetClass)
            .filter(AssetClass.user_id == user_id)
            .all()
        )
        symbol_to_class: dict[str, AssetClass] = {}
        for ac in asset_classes:
            weights = self.db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
            for aw in weights:
                symbol_to_class[aw.symbol] = ac

        # Step 3: Fetch prices and determine asset types
        asset_data: list[dict] = []
        total_positive_diff = sum(max(r["diff"], 0) for r in recs)
        # If no positive diffs, distribute evenly among all recommended assets
        use_even_distribution = total_positive_diff <= 0

        for rec in recs:
            if not use_even_distribution and rec["diff"] <= 0:
                continue
            symbol = rec["symbol"]
            ac = symbol_to_class.get(symbol)
            if not ac:
                continue

            asset_type = ac.type or "stock"
            country = ac.country or "US"
            is_fixed_income = asset_type == "fixed_income"
            is_crypto = asset_type == "crypto"

            if is_fixed_income:
                price = None
            else:
                price = self._get_current_price(symbol, ac.name, country=country, db=self.db)

            asset_data.append({
                **rec,
                "price": price,
                "asset_type": asset_type,
                "is_fixed_income": is_fixed_income,
                "is_crypto": is_crypto,
                "country": country,
            })

        # Step 4: Distribute amount proportionally by gap
        results = []
        remaining = amount

        for ad in asset_data:
            if use_even_distribution:
                share = Decimal("1") / Decimal(str(len(asset_data)))
            else:
                share = Decimal(str(ad["diff"])) / Decimal(str(total_positive_diff))
            allocated = (amount * share).quantize(Decimal("0.01"))
            ad["allocated"] = allocated

        # Step 5: Calculate quantities
        for ad in asset_data:
            allocated = ad["allocated"]

            if ad["is_fixed_income"]:
                invest_amount = allocated
                quantity = Decimal("1")
                price_money = Money(allocated, input_currency)
                invest_money = Money(invest_amount, input_currency)
            else:
                price_money = ad["price"]
                if price_money.currency != input_currency:
                    if exchange_rate is None:
                        raise ValueError("Exchange rate required for cross-currency investment")
                    if input_currency == Currency.BRL:
                        price_in_input = price_money.amount * exchange_rate
                    else:
                        price_in_input = price_money.amount / exchange_rate
                else:
                    price_in_input = price_money.amount

                if price_in_input <= 0:
                    continue

                raw_qty = allocated / price_in_input

                if ad["is_crypto"]:
                    quantity = raw_qty.quantize(Decimal("0.00000001"))
                else:
                    quantity = int(raw_qty)

                if quantity <= 0:
                    continue

                invest_amount = Decimal(str(quantity)) * price_in_input
                invest_money = Money(invest_amount.quantize(Decimal("0.01")), input_currency)

            remaining -= invest_money.amount
            results.append({
                "symbol": ad["symbol"],
                "class_name": ad["class_name"],
                "effective_target": ad["effective_target"],
                "actual_weight": ad["actual_weight"],
                "diff": ad["diff"],
                "price": price_money,
                "quantity": quantity,
                "invest_amount": invest_money,
            })

        # Step 6: Redistribute remainder (iterate through list, buy one more share each pass)
        if remaining > 0:
            changed = True
            while changed:
                changed = False
                for r in results:
                    if remaining <= 0:
                        break
                    ac = symbol_to_class.get(r["symbol"])
                    if not ac or ac.type == "crypto" or ac.type == "fixed_income":
                        continue

                    price_money = r["price"]
                    if price_money.currency != input_currency and exchange_rate:
                        if input_currency == Currency.BRL:
                            share_cost = price_money.amount * exchange_rate
                        else:
                            share_cost = price_money.amount / exchange_rate
                    else:
                        share_cost = price_money.amount

                    cost = share_cost.quantize(Decimal("0.01")) if isinstance(share_cost, Decimal) else Decimal(str(share_cost)).quantize(Decimal("0.01"))
                    if remaining >= cost and cost > 0:
                        r["quantity"] += 1
                        r["invest_amount"] = Money(r["invest_amount"].amount + cost, input_currency)
                        remaining -= cost
                        changed = True

        # Check if all quantities ended up zero (amount too small)
        if results and all(r["quantity"] <= 0 for r in results):
            return _empty_result("amount_too_small")

        return {
            "recommendations": [r for r in results if r["quantity"] > 0],
            "total_invested": Money(amount - remaining.quantize(Decimal("0.01")), input_currency),
            "exchange_rate": float(exchange_rate) if exchange_rate else None,
            "exchange_rate_pair": "USD-BRL" if exchange_rate else None,
            "remainder": Money(remaining.quantize(Decimal("0.01")), input_currency),
            "empty_reason": None,
        }
