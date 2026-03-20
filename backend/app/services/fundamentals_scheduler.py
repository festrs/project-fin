import logging
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset_class import AssetClass
from app.models.fundamentals_score import FundamentalsScore
from app.models.transaction import Transaction
from app.services.fundamentals_scorer import score_fundamentals

logger = logging.getLogger(__name__)

CRYPTO_CLASS_NAMES = {"Crypto", "Criptomoedas"}


class FundamentalsScoreScheduler:
    def __init__(self, yfinance_provider, brapi_provider, dados_provider, finnhub_provider=None, delay: float = 1.5):
        self._yfinance = yfinance_provider
        self._brapi = brapi_provider
        self._dados = dados_provider
        self._finnhub = finnhub_provider
        self._delay = delay

    def score_all(self, db: Session) -> None:
        rows = (
            db.query(Transaction.asset_symbol, AssetClass.country)
            .join(AssetClass, Transaction.asset_class_id == AssetClass.id)
            .filter(
                AssetClass.country.in_(["US", "BR"]),
                AssetClass.name.notin_(CRYPTO_CLASS_NAMES),
            )
            .distinct()
            .all()
        )

        for symbol, country in rows:
            try:
                raw = self._fetch_fundamentals(symbol, country)
                result = score_fundamentals(raw)
                raw_data = raw.get("raw_data")
                self._upsert_score(db, symbol, result, raw_data)
                db.commit()
                logger.info(f"Scored fundamentals for {symbol}: {result['composite_score']}")
            except Exception:
                logger.exception(f"Failed to score fundamentals for {symbol}")
                db.rollback()
            finally:
                if self._delay > 0 and country == "US":
                    time.sleep(self._delay)

    def _fetch_fundamentals(self, symbol: str, country: str) -> dict:
        if country == "US":
            if self._finnhub:
                return self._finnhub.get_fundamentals(symbol)
            return self._yfinance.get_fundamentals(symbol)

        # BR: try brapi first, fall back to dados if eps_history is insufficient
        data = self._brapi.get_fundamentals(symbol)
        eps_history = data.get("eps_history") or []
        if len(eps_history) < 5:
            logger.info(
                f"brapi returned insufficient eps_history for {symbol} "
                f"({len(eps_history)} entries), falling back to dados_de_mercado"
            )
            data = self._dados.scrape_fundamentals(symbol)
        return data

    def _upsert_score(self, db: Session, symbol: str, result: dict, raw_data: list | None) -> None:
        score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
        if score is None:
            score = FundamentalsScore(symbol=symbol)
            db.add(score)

        score.ipo_years = result.get("ipo_years")
        score.ipo_rating = result.get("ipo_rating", "red")
        score.eps_growth_pct = result.get("eps_growth_pct")
        score.eps_rating = result.get("eps_rating", "red")
        score.current_net_debt_ebitda = result.get("current_net_debt_ebitda")
        score.high_debt_years_pct = result.get("high_debt_years_pct")
        score.debt_rating = result.get("debt_rating", "red")
        score.profitable_years_pct = result.get("profitable_years_pct")
        score.profit_rating = result.get("profit_rating", "red")
        score.composite_score = result.get("composite_score", 0.0)
        score.raw_data = raw_data
        score.updated_at = datetime.now(timezone.utc)
