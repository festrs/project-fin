from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketQuote(Base):
    __tablename__ = "market_quotes"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    current_price: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    market_cap: Mapped[Decimal] = mapped_column(Numeric(19, 8, asdecimal=True), default=0)
    country: Mapped[str] = mapped_column(String(2), default="US")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
