from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.quarantine_config import QuarantineConfig
from app.models.transaction import Transaction


@dataclass
class QuarantineStatus:
    asset_symbol: str
    buy_count_in_period: int
    is_quarantined: bool
    quarantine_ends_at: date | None


class QuarantineService:
    def __init__(self, db: Session):
        self.db = db

    def _get_config(self, user_id: str) -> QuarantineConfig:
        config = (
            self.db.query(QuarantineConfig)
            .filter(QuarantineConfig.user_id == user_id)
            .first()
        )
        if config is None:
            config = QuarantineConfig(user_id=user_id)
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def get_asset_status(self, user_id: str, symbol: str) -> QuarantineStatus:
        config = self._get_config(user_id)
        window_start = date.today() - timedelta(days=config.period_days)

        buys = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_symbol == symbol,
                Transaction.type == "buy",
                Transaction.date >= window_start,
            )
            .order_by(Transaction.date.asc())
            .all()
        )

        buy_count = len(buys)
        is_quarantined = buy_count >= config.threshold

        quarantine_ends_at = None
        if is_quarantined:
            # Date of the Nth (threshold) buy + period_days
            nth_buy = buys[config.threshold - 1]
            quarantine_ends_at = nth_buy.date + timedelta(days=config.period_days)

        return QuarantineStatus(
            asset_symbol=symbol,
            buy_count_in_period=buy_count,
            is_quarantined=is_quarantined,
            quarantine_ends_at=quarantine_ends_at,
        )

    def get_all_statuses(self, user_id: str) -> list[QuarantineStatus]:
        symbols = (
            self.db.query(Transaction.asset_symbol)
            .filter(
                Transaction.user_id == user_id,
                Transaction.type == "buy",
            )
            .distinct()
            .all()
        )
        return [self.get_asset_status(user_id, s[0]) for s in symbols]
