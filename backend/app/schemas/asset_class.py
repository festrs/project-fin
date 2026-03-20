from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AssetClassCreate(BaseModel):
    name: str
    target_weight: float = 0.0
    country: str = "US"
    type: Literal["stock", "crypto", "fixed_income"] = "stock"
    is_emergency_reserve: bool = False


class AssetClassUpdate(BaseModel):
    name: Optional[str] = None
    target_weight: Optional[float] = None
    country: Optional[str] = None
    type: Literal["stock", "crypto", "fixed_income"] | None = None
    is_emergency_reserve: Optional[bool] = None


class AssetClassResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_weight: float
    country: str
    type: str
    is_emergency_reserve: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
