from datetime import datetime, date
from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class TransactionCreate(BaseModel):
    asset_class_id: str
    asset_symbol: str
    type: Literal["buy", "sell", "dividend"]
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_value: float
    currency: Literal["BRL", "USD"]
    tax_amount: Optional[float] = 0.0
    date: date
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_field_consistency(self):
        fields = [self.quantity, self.unit_price]
        all_set = all(f is not None for f in fields)
        none_set = all(f is None for f in fields)
        if not (all_set or none_set):
            raise ValueError("quantity and unit_price must be all provided or all None")
        return self


class TransactionUpdate(BaseModel):
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_value: Optional[float] = None
    tax_amount: Optional[float] = None
    date: Optional[date] = None
    notes: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    asset_class_id: str
    asset_symbol: str
    type: str
    quantity: float | None
    unit_price: float | None
    total_value: float
    currency: str
    tax_amount: float | None
    date: date
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
