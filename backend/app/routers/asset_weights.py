from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_weight import AssetWeight
from app.models.asset_class import AssetClass
from app.schemas.asset_weight import AssetWeightCreate, AssetWeightUpdate, AssetWeightResponse

router = APIRouter(tags=["asset-weights"])


@router.get("/api/asset-classes/{ac_id}/assets", response_model=list[AssetWeightResponse])
@limiter.limit(CRUD_LIMIT)
def list_assets(
    request: Request,
    ac_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # Verify ownership
    ac = db.query(AssetClass).filter(AssetClass.id == ac_id, AssetClass.user_id == user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    return db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac_id).all()


@router.post("/api/asset-classes/{ac_id}/assets", response_model=AssetWeightResponse, status_code=201)
@limiter.limit(CRUD_LIMIT)
def add_asset(
    request: Request,
    ac_id: str,
    body: AssetWeightCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ac = db.query(AssetClass).filter(AssetClass.id == ac_id, AssetClass.user_id == user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset class not found")
    aw = AssetWeight(asset_class_id=ac_id, symbol=body.symbol, target_weight=body.target_weight)
    db.add(aw)
    db.commit()
    db.refresh(aw)
    return aw


@router.put("/api/asset-weights/{aw_id}", response_model=AssetWeightResponse)
@limiter.limit(CRUD_LIMIT)
def update_weight(
    request: Request,
    aw_id: str,
    body: AssetWeightUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    aw = db.query(AssetWeight).filter(AssetWeight.id == aw_id).first()
    if not aw:
        raise HTTPException(status_code=404, detail="Asset weight not found")
    # Verify ownership through asset class
    ac = db.query(AssetClass).filter(AssetClass.id == aw.asset_class_id, AssetClass.user_id == user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset weight not found")
    aw.target_weight = body.target_weight
    db.commit()
    db.refresh(aw)
    return aw


@router.delete("/api/asset-weights/{aw_id}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_asset(
    request: Request,
    aw_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    aw = db.query(AssetWeight).filter(AssetWeight.id == aw_id).first()
    if not aw:
        raise HTTPException(status_code=404, detail="Asset weight not found")
    ac = db.query(AssetClass).filter(AssetClass.id == aw.asset_class_id, AssetClass.user_id == user_id).first()
    if not ac:
        raise HTTPException(status_code=404, detail="Asset weight not found")
    db.delete(aw)
    db.commit()
