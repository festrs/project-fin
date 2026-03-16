from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FundamentalsScore(Base):
    __tablename__ = "fundamentals_scores"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ipo_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ipo_rating: Mapped[str] = mapped_column(String(10), default="red")
    eps_growth_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    eps_rating: Mapped[str] = mapped_column(String(10), default="red")
    current_net_debt_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_debt_years_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_rating: Mapped[str] = mapped_column(String(10), default="red")
    profitable_years_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_rating: Mapped[str] = mapped_column(String(10), default="red")
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
