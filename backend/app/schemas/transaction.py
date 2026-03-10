from datetime import datetime, date
from typing import Literal, Optional

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    asset_class_id: str
    asset_symbol: str
    type: Literal["buy", "sell", "dividend"]
    quantity: float
    unit_price: float
    total_value: float
    currency: Literal["BRL", "USD"]
    tax_amount: float = 0.0
    date: date
    notes: Optional[str] = None


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
    quantity: float
    unit_price: float
    total_value: float
    currency: str
    tax_amount: float
    date: date
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
