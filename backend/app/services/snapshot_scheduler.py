"""Daily scheduler that snapshots each user's portfolio total value in BRL."""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.user import User
from app.services.exchange_rate import fetch_exchange_rate
from app.services.market_data import get_market_data_service
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)


class SnapshotScheduler:
    def take_snapshots(self, db: Session) -> None:
        today = date.today()
        users = db.query(User).all()
        logger.info("Taking portfolio snapshots for %d users", len(users))

        for user in users:
            try:
                self._snapshot_user(db, user, today)
            except Exception:
                logger.exception("Failed to snapshot user %s", user.id)

    def _snapshot_user(self, db: Session, user: User, today: date) -> None:
        # Check if snapshot already exists for today
        existing = (
            db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.user_id == user.id,
                PortfolioSnapshot.date == today,
            )
            .first()
        )
        if existing:
            logger.debug("Snapshot already exists for user %s on %s", user.id, today)
            return

        service = PortfolioService(db)
        holdings = service.get_holdings(user.id)
        if not holdings:
            logger.debug("No holdings for user %s, skipping snapshot", user.id)
            return

        # Build class_map and weight_map (same pattern as router)
        asset_classes = db.query(AssetClass).filter(AssetClass.user_id == user.id).all()
        class_map = {}
        weight_map = {}
        for ac in asset_classes:
            class_map[ac.id] = {
                "name": ac.name,
                "target_weight": ac.target_weight,
                "country": ac.country,
                "is_emergency_reserve": ac.is_emergency_reserve,
            }
            weights = db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
            for aw in weights:
                weight_map[aw.symbol] = aw.target_weight

        market_data = get_market_data_service()
        enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data, db=db)

        # Sum total value in BRL
        exchange_rate = fetch_exchange_rate("USD-BRL")
        total_value_brl = Decimal("0")
        for h in enriched:
            current_value = h.get("current_value")
            if current_value is None:
                continue
            amount = current_value.amount
            currency_code = current_value.currency.code
            if currency_code == "USD":
                amount = amount * Decimal(str(exchange_rate))
            total_value_brl += amount

        snapshot = PortfolioSnapshot(
            user_id=user.id,
            date=today,
            total_value_brl=total_value_brl,
        )
        db.add(snapshot)
        db.commit()
        logger.info("Snapshot created for user %s: BRL %s", user.id, total_value_brl)
