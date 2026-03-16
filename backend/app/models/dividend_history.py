from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import String, Float, DateTime, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DividendHistory(Base):
    __tablename__ = "dividend_history"
    __table_args__ = (
        UniqueConstraint("symbol", "record_date", "dividend_type", "value", name="uq_dividend_record"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    dividend_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
