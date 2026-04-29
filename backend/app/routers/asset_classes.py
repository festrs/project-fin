from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.schemas.asset_class import AssetClassCreate, AssetClassUpdate, AssetClassResponse

router = APIRouter(prefix="/api/asset-classes", tags=["asset-classes"])


@router.get("", response_model=list[AssetClassResponse])
@limiter.limit(CRUD_LIMIT)
def list_asset_classes(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return db.query(AssetClass).filter(AssetClass.user_id == user_id).all()


@router.post("", response_model=AssetClassResponse, status_code=201)
@limiter.limit(CRUD_LIMIT)
def create_asset_class(
    request: Request,
    body: AssetClassCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if body.is_emergency_reserve:
        existing = (
            db.query(AssetClass)
            .filter(AssetClass.user_id == user_id, AssetClass.is_emergency_reserve == True)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Emergency reserve already exists")
        body.target_weight = "0.0"

    ac = AssetClass(
        user_id=user_id,
        name=body.name,
        target_weight=Decimal(body.target_weight),
        country=body.country,
        type=body.type,
        is_emergency_reserve=body.is_emergency_reserve,
    )
    db.add(ac)
    db.commit()
    db.refresh(ac)
    return ac


@router.put("/{ac_id}", response_model=AssetClassResponse)
@limiter.limit(CRUD_LIMIT)
def update_asset_class(
    request: Request,
    ac_id: str,
    body: AssetClassUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ac = (
        db.query(AssetClass)
        .filter(AssetClass.id == ac_id, AssetClass.user_id == user_id)
        .first()
    )
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    if body.is_emergency_reserve is True and not ac.is_emergency_reserve:
        existing = (
            db.query(AssetClass)
            .filter(
                AssetClass.user_id == user_id,
                AssetClass.is_emergency_reserve == True,
                AssetClass.id != ac_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Emergency reserve already exists")
    if body.is_emergency_reserve is not None:
        ac.is_emergency_reserve = body.is_emergency_reserve
    # Force target_weight to 0 for emergency reserve
    if ac.is_emergency_reserve:
        ac.target_weight = Decimal("0.0")
        body.target_weight = None  # prevent overwrite below
    if body.name is not None:
        ac.name = body.name
    if body.target_weight is not None:
        ac.target_weight = Decimal(body.target_weight)
    if body.country is not None:
        ac.country = body.country
    if body.type is not None:
        ac.type = body.type
    db.commit()
    db.refresh(ac)
    return ac


@router.delete("/{ac_id}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_asset_class(
    request: Request,
    ac_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ac = (
        db.query(AssetClass)
        .filter(AssetClass.id == ac_id, AssetClass.user_id == user_id)
        .first()
    )
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    db.delete(ac)
    db.commit()
