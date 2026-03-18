from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.stock_split import StockSplit
from app.schemas.stock_split import StockSplitPending, StockSplitAction
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/splits", tags=["splits"])


@router.get("/pending", response_model=list[StockSplitPending])
@limiter.limit(CRUD_LIMIT)
def get_pending_splits(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    splits = (
        db.query(StockSplit)
        .filter(StockSplit.user_id == x_user_id, StockSplit.status == "pending")
        .all()
    )

    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)
    qty_map = {h["symbol"]: h["quantity"] or 0 for h in holdings}

    result = []
    for s in splits:
        current_qty = qty_map.get(s.symbol, 0)
        ratio = s.to_factor / s.from_factor
        result.append(StockSplitPending(
            id=s.id,
            symbol=s.symbol,
            split_date=s.split_date,
            from_factor=s.from_factor,
            to_factor=s.to_factor,
            detected_at=s.detected_at,
            current_quantity=current_qty,
            new_quantity=current_qty * ratio,
        ))

    return result


@router.post("/{split_id}/apply", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def apply_split(
    split_id: str,
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == x_user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    split.status = "applied"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split applied")


@router.post("/{split_id}/dismiss", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def dismiss_split(
    split_id: str,
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == x_user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    split.status = "dismissed"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split dismissed")
