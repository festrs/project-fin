from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from app.schemas.money import MoneyResponse


class InvestmentPlanRequest(BaseModel):
    amount: str
    currency: Literal["BRL", "USD"]
    count: int = 3

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        d = Decimal(v)
        if d <= 0:
            raise ValueError("amount must be positive")
        return v

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1:
            raise ValueError("count must be at least 1")
        return v


class InvestmentRecommendationResponse(BaseModel):
    symbol: str
    class_name: str
    effective_target: float
    actual_weight: float
    diff: float
    price: MoneyResponse
    quantity: float
    invest_amount: MoneyResponse


class InvestmentPlanResponse(BaseModel):
    recommendations: list[InvestmentRecommendationResponse]
    total_invested: MoneyResponse
    exchange_rate: float | None
    exchange_rate_pair: str | None
    remainder: MoneyResponse
    empty_reason: str | None = None  # "no_holdings", "all_quarantined", "amount_too_small", or None
