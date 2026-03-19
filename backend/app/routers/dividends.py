import threading
from datetime import date

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.dividend_history import DividendHistory

router = APIRouter(prefix="/api/dividends", tags=["dividends"])

_scrape_lock = threading.Lock()
_scraping = False


@router.post("/scrape")
@limiter.limit("2/minute")
def trigger_dividend_scrape(request: Request):
    global _scraping
    if not _scrape_lock.acquire(blocking=False):
        return {"status": "already_running"}

    _scraping = True
    _scrape_lock.release()

    def _run():
        global _scraping
        try:
            from app.database import SessionLocal
            from app.providers.dados_de_mercado import DadosDeMercadoProvider
            from app.providers.yfinance import YFinanceProvider
            from app.services.dividend_scraper_scheduler import DividendScheduler

            scheduler = DividendScheduler(
                dados_provider=DadosDeMercadoProvider(),
                yfinance_provider=YFinanceProvider(),
                br_delay=settings.dividend_scraper_delay,
                us_delay=settings.dividend_us_delay,
            )
            db = SessionLocal()
            try:
                scheduler.scrape_all(db)
            finally:
                db.close()
        finally:
            _scraping = False

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}


@router.get("/history")
@limiter.limit(CRUD_LIMIT)
def get_dividend_history(
    request: Request,
    asset_class_id: str,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    """Get dividend history for the current year filtered by asset class."""
    from app.models.transaction import Transaction

    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    # Get symbols belonging to this asset class for this user
    symbols = (
        db.query(Transaction.asset_symbol)
        .filter(
            Transaction.user_id == x_user_id,
            Transaction.asset_class_id == asset_class_id,
        )
        .distinct()
        .all()
    )
    symbol_list = [s[0] for s in symbols]
    if not symbol_list:
        return []

    rows = (
        db.query(DividendHistory)
        .filter(
            DividendHistory.symbol.in_(symbol_list),
            DividendHistory.ex_date >= year_start,
            DividendHistory.ex_date <= year_end,
        )
        .order_by(DividendHistory.ex_date.desc())
        .all()
    )

    return [
        {
            "symbol": r.symbol,
            "dividend_type": r.dividend_type,
            "value": r.value,
            "ex_date": r.ex_date.isoformat(),
            "payment_date": r.payment_date.isoformat() if r.payment_date else None,
        }
        for r in rows
    ]


@router.get("/scrape/status")
@limiter.limit("30/minute")
def get_scrape_status(request: Request):
    return {"running": _scraping}
