import logging
import time

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction
from app.providers.dados_de_mercado import DadosDeMercadoProvider

logger = logging.getLogger(__name__)


class DividendScraperScheduler:
    def __init__(self, provider: DadosDeMercadoProvider, delay: float = 2.0):
        self._provider = provider
        self._delay = delay

    def scrape_all(self, db: Session) -> None:
        symbols = (
            db.query(Transaction.asset_symbol)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(AssetClass.country == "BR")
            .distinct()
            .all()
        )

        for (symbol,) in symbols:
            try:
                records = self._provider.scrape_dividends(symbol)
                new_count = 0
                seen = set()

                for rec in records:
                    # Deduplicate within the scraped batch
                    key = (symbol, rec.record_date, rec.dividend_type, rec.value)
                    if key in seen:
                        continue
                    seen.add(key)

                    exists = (
                        db.query(DividendHistory)
                        .filter_by(
                            symbol=symbol,
                            record_date=rec.record_date,
                            dividend_type=rec.dividend_type,
                            value=rec.value,
                        )
                        .first()
                    )
                    if exists:
                        continue

                    entry = DividendHistory(
                        symbol=symbol,
                        dividend_type=rec.dividend_type,
                        value=rec.value,
                        record_date=rec.record_date,
                        ex_date=rec.ex_date,
                        payment_date=rec.payment_date,
                    )
                    db.add(entry)
                    new_count += 1

                db.commit()
                logger.info(f"Scraped dividends for {symbol}: {new_count} new records")
            except Exception:
                logger.exception(f"Failed to scrape dividends for {symbol}")
                db.rollback()
            finally:
                if self._delay > 0:
                    time.sleep(self._delay)
