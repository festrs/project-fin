import math
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.stock_split import StockSplit, SplitEventType
from app.models.transaction import Transaction
from app.schemas.stock_split import StockSplitPending, StockSplitAction
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/splits", tags=["splits"])


@router.get("/pending", response_model=list[StockSplitPending])
@limiter.limit(CRUD_LIMIT)
def get_pending_splits(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    splits = (
        db.query(StockSplit)
        .filter(StockSplit.user_id == user_id, StockSplit.status == "pending")
        .all()
    )

    service = PortfolioService(db)
    holdings = service.get_holdings(user_id)
    qty_map = {h["symbol"]: h["quantity"] or 0 for h in holdings}

    result = []
    for s in splits:
        current_qty = qty_map.get(s.symbol, 0)
        if s.event_type == SplitEventType.BONIFICACAO:
            # Bonificação from:to means from bonus shares per to held
            # e.g. 1:10 → 1 bonus per 10 held → 100 shares becomes 110
            bonus_shares = math.floor(current_qty / s.to_factor * s.from_factor) if s.to_factor else 0
            new_qty = current_qty + bonus_shares
        else:
            # Desdobramento from:to → from shares become to shares
            new_qty = current_qty * s.to_factor / s.from_factor
        result.append(StockSplitPending(
            id=s.id,
            symbol=s.symbol,
            split_date=s.split_date,
            from_factor=s.from_factor,
            to_factor=s.to_factor,
            event_type=s.event_type,
            detected_at=s.detected_at,
            current_quantity=current_qty,
            new_quantity=new_qty,
        ))

    return result


@router.post("/{split_id}/apply", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def apply_split(
    split_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    if split.event_type == SplitEventType.BONIFICACAO:
        # Bonificação: create a buy transaction for the bonus shares
        service = PortfolioService(db)
        holdings = service.get_holdings(user_id)
        current_qty = next(
            (h["quantity"] or 0 for h in holdings if h["symbol"] == split.symbol), 0
        )
        bonus_shares = math.floor(current_qty / split.to_factor * split.from_factor) if split.to_factor else 0

        if bonus_shares > 0:
            tx_currency = (
                db.query(Transaction.currency)
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.asset_symbol == split.symbol,
                    Transaction.type == "buy",
                )
                .order_by(Transaction.date.desc())
                .first()
            )
            currency = tx_currency[0] if tx_currency else "BRL"

            db.add(Transaction(
                user_id=user_id,
                asset_class_id=split.asset_class_id,
                asset_symbol=split.symbol,
                type="buy",
                quantity=bonus_shares,
                unit_price=0,
                total_value=0,
                currency=currency,
                tax_amount=0,
                date=split.split_date,
                notes=f"Bonificação {split.from_factor}:{split.to_factor}",
            ))
    else:
        # Stock split: create a buy transaction for the extra shares
        # (same approach as bonificação — totals reflect transaction history)
        service = PortfolioService(db)
        holdings = service.get_holdings(user_id)
        current_qty = next(
            (h["quantity"] or 0 for h in holdings if h["symbol"] == split.symbol), 0
        )
        ratio = split.to_factor / split.from_factor
        extra_shares = current_qty * (ratio - 1)

        tx_currency = (
            db.query(Transaction.currency)
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_symbol == split.symbol,
                Transaction.type == "buy",
            )
            .order_by(Transaction.date.desc())
            .first()
        )
        currency = tx_currency[0] if tx_currency else "BRL"

        if extra_shares > 0:
            db.add(Transaction(
                user_id=user_id,
                asset_class_id=split.asset_class_id,
                asset_symbol=split.symbol,
                type="buy",
                quantity=extra_shares,
                unit_price=0,
                total_value=0,
                currency=currency,
                tax_amount=0,
                date=split.split_date,
                notes=f"Desdobramento {split.from_factor}:{split.to_factor}",
            ))

    split.status = "applied"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split applied")


@router.post("/{split_id}/dismiss", response_model=StockSplitAction)
@limiter.limit(CRUD_LIMIT)
def dismiss_split(
    split_id: str,
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    split = db.query(StockSplit).filter(
        StockSplit.id == split_id, StockSplit.user_id == user_id
    ).first()
    if not split:
        raise HTTPException(status_code=404, detail="Split not found")
    if split.status != "pending":
        raise HTTPException(status_code=400, detail=f"Split already {split.status}")

    split.status = "dismissed"
    split.resolved_at = datetime.utcnow()
    db.commit()
    return StockSplitAction(message="Split dismissed")
