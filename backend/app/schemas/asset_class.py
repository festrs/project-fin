from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class AssetClassCreate(BaseModel):
    name: str
    target_weight: str = "0.0"
    country: str = "US"
    type: Literal["stock", "crypto", "fixed_income"] = "stock"
    is_emergency_reserve: bool = False

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)


class AssetClassUpdate(BaseModel):
    name: Optional[str] = None
    target_weight: Optional[str] = None
    country: Optional[str] = None
    type: Literal["stock", "crypto", "fixed_income"] | None = None
    is_emergency_reserve: Optional[bool] = None

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        return str(v)


class AssetClassResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_weight: str
    country: str
    type: str
    is_emergency_reserve: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)

    model_config = {"from_attributes": True}
