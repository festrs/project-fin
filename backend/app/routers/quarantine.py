from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.quarantine_config import QuarantineConfig
from app.schemas.quarantine import QuarantineConfigUpdate, QuarantineConfigResponse, QuarantineStatusResponse
from app.services.quarantine import QuarantineService

router = APIRouter(prefix="/api/quarantine", tags=["quarantine"])


@router.get("/status", response_model=list[QuarantineStatusResponse])
@limiter.limit(CRUD_LIMIT)
def get_all_statuses(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = QuarantineService(db)
    return service.get_all_statuses(x_user_id)


@router.get("/config", response_model=QuarantineConfigResponse)
@limiter.limit(CRUD_LIMIT)
def get_config(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    config = db.query(QuarantineConfig).filter(QuarantineConfig.user_id == x_user_id).first()
    if not config:
        # Create default config
        config = QuarantineConfig(user_id=x_user_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/config", response_model=QuarantineConfigResponse)
@limiter.limit(CRUD_LIMIT)
def update_config(
    request: Request,
    body: QuarantineConfigUpdate,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    config = db.query(QuarantineConfig).filter(QuarantineConfig.user_id == x_user_id).first()
    if not config:
        config = QuarantineConfig(user_id=x_user_id)
        db.add(config)
        db.flush()
    if body.threshold is not None:
        config.threshold = body.threshold
    if body.period_days is not None:
        config.period_days = body.period_days
    db.commit()
    db.refresh(config)
    return config
