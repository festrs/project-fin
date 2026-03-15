from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AssetClassCreate(BaseModel):
    name: str
    target_weight: float = 0.0
    country: str = "US"


class AssetClassUpdate(BaseModel):
    name: Optional[str] = None
    target_weight: Optional[float] = None
    country: Optional[str] = None


class AssetClassResponse(BaseModel):
    id: str
    user_id: str
    name: str
    target_weight: float
    country: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
