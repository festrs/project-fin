import logging
import time

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Note: matches fundamentals_scheduler.py. market_data.py uses a different set
# that includes "Stablecoins" and "Cryptos". This is a pre-existing inconsistency.
CRYPTO_CLASS_NAMES = {"Crypto", "Criptomoedas"}


class DividendScheduler:
    def __init__(self, dados_provider, yfinance_provider, br_delay: float = 2.0, us_delay: float = 1.0):
        self._dados = dados_provider
        self._yfinance = yfinance_provider
        self._br_delay = br_delay
        self._us_delay = us_delay

    def scrape_all(self, db: Session) -> None:
        rows = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(
                AssetClass.country.in_(["BR", "US"]),
                AssetClass.name.notin_(CRYPTO_CLASS_NAMES),
            )
            .distinct()
            .all()
        )

        for symbol, country in rows:
            try:
                if country == "BR":
                    records = self._dados.scrape_dividends(symbol)
                    delay = self._br_delay
                else:
                    records = self._yfinance.get_dividends(symbol)
                    delay = self._us_delay

                new_count = 0
                seen = set()

                for rec in records:
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
                if delay > 0:
                    time.sleep(delay)
