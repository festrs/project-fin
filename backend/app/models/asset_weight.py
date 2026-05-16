from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetWeight(Base):
    __tablename__ = "asset_weights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    asset_class_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_classes.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(7, 4, asdecimal=True), default=Decimal("0.0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    asset_class = relationship("AssetClass", back_populates="assets")
