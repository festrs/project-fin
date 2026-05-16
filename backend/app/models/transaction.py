from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, Numeric, DateTime, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    asset_class_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_classes.id"), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(Enum("buy", "sell", "dividend", name="transaction_type"), nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=True, default=None)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
