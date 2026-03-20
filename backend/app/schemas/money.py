from pydantic import BaseModel, field_validator
from decimal import Decimal


class MoneyResponse(BaseModel):
    amount: str
    currency: str


class MoneyInput(BaseModel):
    amount: str
    currency: str

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        Decimal(v)  # raises InvalidOperation if not a valid decimal string
        return v
