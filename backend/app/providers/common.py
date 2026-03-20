from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class DividendRecord:
    dividend_type: str
    value: Decimal
    record_date: date
    ex_date: date
    payment_date: date | None
