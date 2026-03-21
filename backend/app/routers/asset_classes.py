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
    ac = AssetClass(user_id=user_id, name=body.name, target_weight=body.target_weight, country=body.country, type=body.type)
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
    if body.name is not None:
        ac.name = body.name
    if body.target_weight is not None:
        ac.target_weight = body.target_weight
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
