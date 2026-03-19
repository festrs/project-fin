from dataclasses import dataclass
from datetime import date


@dataclass
class DividendRecord:
    dividend_type: str
    value: float
    record_date: date
    ex_date: date
    payment_date: date | None
