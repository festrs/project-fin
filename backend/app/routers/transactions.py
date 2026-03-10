from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
@limiter.limit(CRUD_LIMIT)
def list_transactions(
    request: Request,
    x_user_id: str = Header(),
    type: str | None = Query(None),
    symbol: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Transaction).filter(Transaction.user_id == x_user_id)
    if type:
        q = q.filter(Transaction.type == type)
    if symbol:
        q = q.filter(Transaction.asset_symbol == symbol)
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    return q.all()


@router.post("", response_model=TransactionResponse, status_code=201)
@limiter.limit(CRUD_LIMIT)
def create_transaction(
    request: Request,
    body: TransactionCreate,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    tx = Transaction(
        user_id=x_user_id,
        asset_class_id=body.asset_class_id,
        asset_symbol=body.asset_symbol,
        type=body.type,
        quantity=body.quantity,
        unit_price=body.unit_price,
        total_value=body.total_value,
        currency=body.currency,
        tax_amount=body.tax_amount,
        date=body.date,
        notes=body.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.put("/{tx_id}", response_model=TransactionResponse)
@limiter.limit(CRUD_LIMIT)
def update_transaction(
    request: Request,
    tx_id: str,
    body: TransactionUpdate,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == x_user_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def delete_transaction(
    request: Request,
    tx_id: str,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == x_user_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
