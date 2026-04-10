import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.transaction import Transaction

ZERO = Decimal("0")
FII_PATTERN = re.compile(r"^[A-Z]{4}11B?$")
STOCK_EXEMPTION_THRESHOLD = Decimal("20000")
STOCK_TAX_RATE = Decimal("0.15")
FII_TAX_RATE = Decimal("0.20")


class TaxService:
    def __init__(self, db: Session):
        self.db = db

    def get_monthly_report(self, user_id: str, year: int) -> list[dict]:
        transactions = (
            self.db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .filter(Transaction.type.in_(["buy", "sell"]))
            .order_by(Transaction.date.asc())
            .all()
        )

        # Track weighted average cost per symbol
        avg_cost: dict[str, Decimal] = defaultdict(lambda: ZERO)
        position: dict[str, Decimal] = defaultdict(lambda: ZERO)

        # Collect sells per month in the requested year
        # month -> list of (symbol, quantity, unit_price, avg_cost_at_sell, tax_amount)
        monthly_sells: dict[int, list] = {m: [] for m in range(1, 13)}

        for tx in transactions:
            symbol = tx.asset_symbol
            qty = Decimal(str(tx.quantity)) if tx.quantity else ZERO
            price = tx.unit_price if tx.unit_price is not None else ZERO

            if tx.type == "buy":
                old_qty = position[symbol]
                old_avg = avg_cost[symbol]
                new_qty = old_qty + qty
                if new_qty > ZERO:
                    avg_cost[symbol] = (old_qty * old_avg + qty * price) / new_qty
                position[symbol] = new_qty

            elif tx.type == "sell":
                current_avg = avg_cost[symbol]

                if tx.date.year == year:
                    tax_amount = tx.tax_amount if tx.tax_amount is not None else ZERO
                    monthly_sells[tx.date.month].append(
                        (symbol, qty, price, current_avg, tax_amount)
                    )

                # Reduce position, avg cost stays the same
                position[symbol] = position[symbol] - qty

        # Build report
        report = []
        for month in range(1, 13):
            sells = monthly_sells[month]

            stock_sales = ZERO
            stock_gain = ZERO
            stock_irrf = ZERO
            fii_sales = ZERO
            fii_gain = ZERO
            fii_irrf = ZERO

            for symbol, qty, price, cost, irrf in sells:
                sale_value = price * qty
                gain = (price - cost) * qty
                is_fii = bool(FII_PATTERN.match(symbol))

                if is_fii:
                    fii_sales += sale_value
                    fii_gain += gain
                    fii_irrf += irrf
                else:
                    stock_sales += sale_value
                    stock_gain += gain
                    stock_irrf += irrf

            # Stocks: exempt if total monthly sales < R$20k
            stock_exempt = stock_sales < STOCK_EXEMPTION_THRESHOLD
            if stock_exempt or stock_gain <= ZERO:
                stock_tax = ZERO
            else:
                stock_tax = max(
                    (stock_gain * STOCK_TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) - stock_irrf,
                    ZERO,
                )

            # FIIs: always taxed at 20%
            if fii_gain <= ZERO:
                fii_tax = ZERO
            else:
                fii_tax = max(
                    (fii_gain * FII_TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) - fii_irrf,
                    ZERO,
                )

            total_tax = stock_tax + fii_tax

            report.append(
                {
                    "month": month,
                    "stocks": {
                        "total_sales": str(stock_sales),
                        "total_gain": str(stock_gain),
                        "exempt": stock_exempt,
                        "tax_due": str(stock_tax),
                    },
                    "fiis": {
                        "total_sales": str(fii_sales),
                        "total_gain": str(fii_gain),
                        "tax_due": str(fii_tax),
                    },
                    "total_tax_due": str(total_tax),
                }
            )

        return report
