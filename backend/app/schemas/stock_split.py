from datetime import date, datetime
from pydantic import BaseModel


class StockSplitPending(BaseModel):
    id: str
    symbol: str
    split_date: date
    from_factor: float
    to_factor: float
    event_type: str = "split"
    detected_at: datetime
    current_quantity: float
    new_quantity: float

    class Config:
        from_attributes = True


class StockSplitAction(BaseModel):
    message: str
