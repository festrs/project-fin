from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AssetWeightCreate(BaseModel):
    symbol: str
    target_weight: float = 0.0


class AssetWeightUpdate(BaseModel):
    target_weight: float


class AssetWeightResponse(BaseModel):
    id: str
    asset_class_id: str
    symbol: str
    target_weight: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
