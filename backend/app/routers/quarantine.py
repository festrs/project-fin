from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.quarantine_config import QuarantineConfig
from app.schemas.quarantine import QuarantineConfigUpdate, QuarantineConfigResponse, QuarantineStatusResponse
from app.services.quarantine import QuarantineService

router = APIRouter(prefix="/api/quarantine", tags=["quarantine"])


@router.get("/status", response_model=list[QuarantineStatusResponse])
@limiter.limit(CRUD_LIMIT)
def get_all_statuses(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = QuarantineService(db)
    return service.get_all_statuses(user_id)


@router.get("/config", response_model=QuarantineConfigResponse)
@limiter.limit(CRUD_LIMIT)
def get_config(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config = db.query(QuarantineConfig).filter(QuarantineConfig.user_id == user_id).first()
    if not config:
        # Create default config
        config = QuarantineConfig(user_id=user_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/config", response_model=QuarantineConfigResponse)
@limiter.limit(CRUD_LIMIT)
def update_config(
    request: Request,
    body: QuarantineConfigUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    config = db.query(QuarantineConfig).filter(QuarantineConfig.user_id == user_id).first()
    if not config:
        config = QuarantineConfig(user_id=user_id)
        db.add(config)
        db.flush()
    if body.threshold is not None:
        config.threshold = body.threshold
    if body.period_days is not None:
        config.period_days = body.period_days
    db.commit()
    db.refresh(config)
    return config
