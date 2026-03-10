from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel


class QuarantineConfigUpdate(BaseModel):
    threshold: Optional[int] = None
    period_days: Optional[int] = None


class QuarantineConfigResponse(BaseModel):
    id: str
    user_id: str
    threshold: int
    period_days: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuarantineStatusResponse(BaseModel):
    asset_symbol: str
    buy_count_in_period: int
    is_quarantined: bool
    quarantine_ends_at: Optional[date] = None
