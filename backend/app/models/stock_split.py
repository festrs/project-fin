from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import String, Float, DateTime, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StockSplit(Base):
    __tablename__ = "stock_splits"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "split_date", name="uq_user_symbol_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    split_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_factor: Mapped[float] = mapped_column(Float, nullable=False)
    to_factor: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    asset_class_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_classes.id"), nullable=False)
