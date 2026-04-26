from datetime import date, datetime
from pydantic import BaseModel, field_validator


class StockSplitPending(BaseModel):
    id: str
    symbol: str
    split_date: date
    from_factor: str
    to_factor: str
    event_type: str = "split"
    detected_at: datetime
    current_quantity: str
    new_quantity: str

    @field_validator("from_factor", "to_factor", "current_quantity", "new_quantity", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)

    class Config:
        from_attributes = True


class StockSplitAction(BaseModel):
    message: str
