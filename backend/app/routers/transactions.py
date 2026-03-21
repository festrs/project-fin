import logging
import threading
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.models.fundamentals_score import FundamentalsScore
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _tx_to_response(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "user_id": tx.user_id,
        "asset_class_id": tx.asset_class_id,
        "asset_symbol": tx.asset_symbol,
        "type": tx.type,
        "quantity": tx.quantity,
        "unit_price": {"amount": str(tx.unit_price), "currency": tx.currency} if tx.unit_price is not None else None,
        "total_value": {"amount": str(tx.total_value), "currency": tx.currency},
        "tax_amount": {"amount": str(tx.tax_amount), "currency": tx.currency} if tx.tax_amount is not None else None,
        "date": tx.date.isoformat(),
        "notes": tx.notes,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
    }


@router.get("")
@limiter.limit(CRUD_LIMIT)
def list_transactions(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    type: str | None = Query(None),
    symbol: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == user_id)
    if type:
        q = q.filter(Transaction.type == type)
    if symbol:
        q = q.filter(Transaction.asset_symbol == symbol)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return [_tx_to_response(tx) for tx in q.all()]


def _trigger_fundamentals_refresh(symbol: str) -> None:
    """Fetch fundamentals for a symbol in a background thread."""
    def run():
        db = SessionLocal()
        try:
            from app.routers.fundamentals import _refresh_score
            _refresh_score(symbol, db)
            logger.info("Fundamentals fetched for %s", symbol)
        except Exception:
            logger.exception("Failed to fetch fundamentals for %s", symbol)
        finally:
            db.close()

    threading.Thread(target=run, daemon=True).start()


@router.post("", status_code=201)
@limiter.limit(CRUD_LIMIT)
def create_transaction(
    request: Request,
    body: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    tx = Transaction(
        user_id=user_id,
        asset_class_id=body.asset_class_id,
        asset_symbol=body.asset_symbol,
        type=body.type,
        quantity=body.quantity,
        unit_price=Decimal(body.unit_price.amount) if body.unit_price else None,
        total_value=Decimal(body.total_value.amount),
        currency=body.total_value.currency,
        tax_amount=Decimal(body.tax_amount.amount) if body.tax_amount else None,
        date=body.date,
        notes=body.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Trigger background fundamentals fetch for stock assets without existing scores
    fundamentals_refresh_started = False
    asset_class = db.query(AssetClass).filter_by(id=body.asset_class_id).first()
    if asset_class and asset_class.type == "stock":
        existing_score = db.query(FundamentalsScore).filter_by(symbol=body.asset_symbol).first()
        if not existing_score:
            _trigger_fundamentals_refresh(body.asset_symbol)
            fundamentals_refresh_started = True

    response = _tx_to_response(tx)
    response["fundamentals_refresh_started"] = fundamentals_refresh_started
    return response


@router.put("/{tx_id}")
@limiter.limit(CRUD_LIMIT)
def update_transaction(
    request: Request,
    tx_id: str,
    body: TransactionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field in ("unit_price", "total_value", "tax_amount") and value is not None:
            setattr(tx, field, Decimal(value["amount"]))
            if field == "total_value":
                tx.currency = value["currency"]
        elif field == "currency":
            pass  # deprecated, skip
        else:
            setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return _tx_to_response(tx)


@router.delete("/{tx_id}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_transaction(
    request: Request,
    tx_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()


@router.delete("/by-symbol/{symbol}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_transactions_by_symbol(
    request: Request,
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete all transactions for a symbol (removes the holding)."""
    count = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.asset_symbol == symbol)
        .delete()
    )
    if count == 0:
        raise HTTPException(status_code=404, detail="No transactions found for symbol")
    db.commit()


@router.put("/by-symbol/{symbol}/asset-class")
@limiter.limit(CRUD_LIMIT)
def update_asset_class_for_symbol(
    request: Request,
    symbol: str,
    asset_class_id: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Move all transactions for a symbol to a different asset class."""
    txs = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.asset_symbol == symbol)
        .all()
    )
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found for symbol")
    for tx in txs:
        tx.asset_class_id = asset_class_id
    db.commit()
    return {"updated": len(txs)}
