from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import String, Float, DateTime, Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    asset_class_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_classes.id"), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    type: Mapped[str] = mapped_column(Enum("buy", "sell", "dividend", name="transaction_type"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(Enum("BRL", "USD", name="currency_type"), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
