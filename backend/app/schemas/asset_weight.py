from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class AssetWeightCreate(BaseModel):
    symbol: str
    target_weight: str = "0.0"

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)


class AssetWeightUpdate(BaseModel):
    target_weight: str

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)


class AssetWeightResponse(BaseModel):
    id: str
    asset_class_id: str
    symbol: str
    target_weight: str
    created_at: datetime
    updated_at: datetime

    @field_validator("target_weight", mode="before")
    @classmethod
    def coerce_to_str(cls, v: object) -> str:
        return str(v)

    model_config = {"from_attributes": True}
