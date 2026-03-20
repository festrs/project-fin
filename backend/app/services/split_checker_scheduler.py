import logging
import time
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.stock_split import StockSplit, SplitEventType
from app.models.transaction import Transaction
from app.providers.brapi import BrapiProvider
from app.providers.dados_de_mercado import DadosDeMercadoProvider
from app.providers.yfinance import YFinanceProvider

logger = logging.getLogger(__name__)


class SplitCheckerScheduler:
    def __init__(self, brapi_provider: BrapiProvider, delay: float = 0.5):
        self._yfinance = YFinanceProvider()
        self._brapi = brapi_provider
        self._dados = DadosDeMercadoProvider()
        self._delay = delay

    def check_all(self, db: Session) -> None:
        user_ids = (
            db.query(Transaction.user_id)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.type == "stock")
            .distinct()
            .all()
        )

        for (user_id,) in user_ids:
            self._check_user(db, user_id)

    def _check_user(self, db: Session, user_id: str) -> None:
        stock_classes = (
            db.query(AssetClass)
            .filter(AssetClass.user_id == user_id, AssetClass.type == "stock")
            .all()
        )
        class_map = {ac.id: ac for ac in stock_classes}

        symbols_with_class = (
            db.query(Transaction.asset_symbol, Transaction.asset_class_id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.asset_class_id.in_([ac.id for ac in stock_classes]),
            )
            .distinct()
            .all()
        )

        today = date.today()
        cutoff_date = today - timedelta(days=2 * 365)
        from_date = cutoff_date.isoformat()
        to_date = today.isoformat()

        for symbol, asset_class_id in symbols_with_class:
            ac = class_map.get(asset_class_id)
            if not ac:
                continue

            try:
                if symbol.endswith(".SA"):
                    raw_splits = self._dados.scrape_splits(symbol)
                else:
                    raw_splits = self._yfinance.get_splits(symbol, from_date, to_date)

                for sp in raw_splits:
                    split_date = date.fromisoformat(sp["date"])

                    if split_date < cutoff_date:
                        continue

                    exists = (
                        db.query(StockSplit)
                        .filter_by(user_id=user_id, symbol=symbol, split_date=split_date)
                        .first()
                    )
                    if exists:
                        continue

                    db.add(StockSplit(
                        user_id=user_id,
                        symbol=symbol,
                        split_date=split_date,
                        from_factor=sp["fromFactor"],
                        to_factor=sp["toFactor"],
                        event_type=sp.get("eventType", SplitEventType.SPLIT),
                        status="pending",
                        asset_class_id=asset_class_id,
                    ))
                    db.commit()
                    logger.info(f"Detected split for {symbol}: {sp['fromFactor']}:{sp['toFactor']} on {sp['date']}")

            except Exception:
                logger.exception(f"Failed to check splits for {symbol}")
                db.rollback()
            finally:
                if self._delay > 0:
                    time.sleep(self._delay)
