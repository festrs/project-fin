import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import CRUD_LIMIT, limiter
from app.models.fundamentals_score import FundamentalsScore
from app.providers.common import Symbol

router = APIRouter(prefix="/api/fundamentals", tags=["fundamentals"])


def _score_to_dict(score: FundamentalsScore, include_raw: bool = False) -> dict:
    result = {
        "symbol": score.symbol,
        "ipo_years": score.ipo_years,
        "ipo_rating": score.ipo_rating,
        "eps_growth_pct": score.eps_growth_pct,
        "eps_rating": score.eps_rating,
        "current_net_debt_ebitda": score.current_net_debt_ebitda,
        "high_debt_years_pct": score.high_debt_years_pct,
        "debt_rating": score.debt_rating,
        "profitable_years_pct": score.profitable_years_pct,
        "profit_rating": score.profit_rating,
        "composite_score": score.composite_score,
        "updated_at": score.updated_at.isoformat() if score.updated_at else None,
    }
    if include_raw:
        result["raw_data"] = score.raw_data
    return result


def _refresh_score(symbol: str, db: Session) -> None:
    from app.providers.finnhub import FinnhubProvider
    from app.providers.yfinance import YFinanceProvider
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    yfinance = YFinanceProvider()
    brapi = BrapiProvider(api_key=settings.brapi_api_key)
    dados = DadosDeMercadoProvider()
    finnhub = FinnhubProvider(api_key=settings.finnhub_api_key)

    country = Symbol.country(symbol)

    scheduler = FundamentalsScoreScheduler(
        yfinance_provider=yfinance,
        brapi_provider=brapi,
        dados_provider=dados,
        finnhub_provider=finnhub,
        delay=0,
    )

    raw = scheduler._fetch_fundamentals(symbol, country)
    from app.services.fundamentals_scorer import score_fundamentals
    result = score_fundamentals(raw)
    raw_data = raw.get("raw_data")
    scheduler._upsert_score(db, symbol, result, raw_data)
    db.commit()


@router.post("/refresh-all")
@limiter.limit(CRUD_LIMIT)
def refresh_all_scores(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.finnhub import FinnhubProvider
    from app.providers.yfinance import YFinanceProvider
    from app.services.fundamentals_scheduler import FundamentalsScoreScheduler

    scheduler = FundamentalsScoreScheduler(
        yfinance_provider=YFinanceProvider(),
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
        dados_provider=DadosDeMercadoProvider(),
        finnhub_provider=FinnhubProvider(api_key=settings.finnhub_api_key),
        delay=1.0,
    )

    def run():
        db = SessionLocal()
        try:
            scheduler.score_all(db)
        finally:
            db.close()

    threading.Thread(target=run, daemon=True).start()
    return {"status": "started"}


@router.get("/scores")
@limiter.limit(CRUD_LIMIT)
def get_scores(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    scores = db.query(FundamentalsScore).all()
    return [_score_to_dict(score) for score in scores]


@router.get("/{symbol}")
@limiter.limit(CRUD_LIMIT)
def get_score_detail(
    request: Request,
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    if score is None:
        raise HTTPException(status_code=404, detail=f"No fundamentals score found for {symbol}")
    return _score_to_dict(score, include_raw=True)


@router.post("/{symbol}/refresh")
@limiter.limit(CRUD_LIMIT)
def refresh_score(
    request: Request,
    symbol: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        _refresh_score(symbol, db)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to refresh fundamentals for {symbol}: {exc}")

    score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    if score is None:
        raise HTTPException(status_code=404, detail=f"No fundamentals score found for {symbol} after refresh")
    return _score_to_dict(score, include_raw=True)
