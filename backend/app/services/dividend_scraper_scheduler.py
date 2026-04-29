import logging
import time
from datetime import date as _date

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.dividend_history import DividendHistory
from app.models.tracked_symbol import TrackedSymbol
from app.models.transaction import Transaction
from app.providers.brapi import BrapiFeatureUnavailable
from app.providers.common import Symbol

logger = logging.getLogger(__name__)

# Note: matches fundamentals_scheduler.py. market_data.py uses a different set
# that includes "Stablecoins" and "Cryptos". This is a pre-existing inconsistency.
CRYPTO_CLASS_NAMES = {"Crypto", "Criptomoedas"}


class DividendScheduler:
    def __init__(
        self,
        dados_provider,
        yfinance_provider,
        brapi_provider=None,
        br_delay: float = 2.0,
        us_delay: float = 1.0,
    ):
        self._dados = dados_provider
        self._yfinance = yfinance_provider
        self._brapi = brapi_provider
        self._br_delay = br_delay
        self._us_delay = us_delay
        # Becomes True after the first FEATURE_NOT_AVAILABLE so we stop trying
        # Brapi for the rest of the run.
        self._brapi_disabled = False

    # FIIs are not covered by DadosDeMercado; use yfinance for them
    _YFINANCE_CLASS_NAMES = {"FIIs"}

    # Map iOS asset_class values to class names used by the dividend scraper
    _TRACKED_FII_CLASSES = {"fiis"}

    def scrape_all(self, db: Session) -> dict:
        # Symbols from web app transactions
        tx_rows = (
            db.query(Transaction.asset_symbol, AssetClass.country, AssetClass.name)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(
                AssetClass.country.in_(["BR", "US"]),
                AssetClass.name.notin_(CRYPTO_CLASS_NAMES),
            )
            .distinct()
            .all()
        )

        # Symbols tracked by iOS app
        tracked_rows = (
            db.query(TrackedSymbol.symbol, TrackedSymbol.country, TrackedSymbol.asset_class)
            .filter(TrackedSymbol.asset_class != "crypto")
            .all()
        )
        # Normalize tracked rows: map asset_class to class_name for FII detection
        for symbol, country, asset_class in tracked_rows:
            class_name = "FIIs" if asset_class in self._TRACKED_FII_CLASSES else asset_class
            tx_rows.append((symbol, country, class_name))

        # Deduplicate
        seen: set[str] = set()
        rows: list[tuple[str, str, str]] = []
        for symbol, country, class_name in tx_rows:
            if symbol not in seen:
                seen.add(symbol)
                rows.append((symbol, country, class_name))

        return self.scrape_symbols(db, rows)

    def scrape_symbols(
        self,
        db: Session,
        rows: list[tuple[str, str, str]],
        since: _date | None = None,
    ) -> dict:
        """Scrape dividend records for the given (symbol, country, class_name) rows.

        Used by both the cron (`scrape_all`) and the iOS on-demand refresh
        endpoint. Returns aggregate stats so the caller can surface progress.

        When `since` is provided, records with payment_date (or ex_date when
        payment_date is missing) earlier than `since` are skipped. The iOS
        bootstrap path passes the holding's first-Contribution date so the
        store doesn't get polluted with dividends from before the user owned
        the asset; the manual refresh button leaves it `None` so users can
        backfill full history.
        """
        new_total = 0
        failed: list[str] = []
        delay = 0.0
        for symbol, country, class_name in rows:
            try:
                records, currency, delay = self._fetch_records(symbol, country, class_name)

                new_count = 0
                seen_records: set = set()

                for rec in records:
                    if since is not None:
                        cutoff_date = rec.payment_date or rec.ex_date
                        if cutoff_date is not None and cutoff_date < since:
                            continue

                    key = (symbol, rec.record_date, rec.dividend_type, rec.value)
                    if key in seen_records:
                        continue
                    seen_records.add(key)

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
                        currency=currency,
                    )
                    db.add(entry)
                    new_count += 1

                db.commit()
                new_total += new_count
                logger.info(f"Scraped dividends for {symbol}: {new_count} new records")
            except Exception:
                logger.exception(f"Failed to scrape dividends for {symbol}")
                db.rollback()
                failed.append(symbol)
            finally:
                if delay > 0:
                    time.sleep(delay)
        return {"scraped": len(rows), "new_records": new_total, "failed": failed}

    def _fetch_records(self, symbol: str, country: str, class_name: str):
        """Resolve the dividend records for a symbol via the provider chain.

        BR (stocks + FIIs): Brapi cashDividends → yfinance(.SA) fallback.
        US (stocks + REITs): yfinance.

        Returns (records, currency, delay).
        """
        if country == "BR":
            if self._brapi is not None and not self._brapi_disabled:
                try:
                    records = self._brapi.get_dividends(symbol)
                    if records:
                        return records, "BRL", self._br_delay
                except BrapiFeatureUnavailable as e:
                    logger.warning("Brapi dividends unavailable on current plan: %s", e)
                    self._brapi_disabled = True
                except Exception:
                    logger.exception("Brapi.get_dividends failed for %s; falling back", symbol)

            records = self._yfinance.get_dividends(Symbol.with_sa(symbol))
            if not records and class_name not in self._YFINANCE_CLASS_NAMES:
                records = self._dados.scrape_dividends(symbol)
            return records, "BRL", self._br_delay

        # US stocks & REITs
        return self._yfinance.get_dividends(symbol), "USD", self._us_delay
