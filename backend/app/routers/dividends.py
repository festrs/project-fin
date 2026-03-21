import threading
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_id
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get dividend history for the current year filtered by asset class."""
    from app.services.portfolio import PortfolioService

    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    # Get holdings to know quantity per symbol
    service = PortfolioService(db)
    holdings = service.get_holdings(user_id)
    qty_map: dict[str, float] = {}
    symbol_list: list[str] = []
    for h in holdings:
        if h["asset_class_id"] == asset_class_id and h["quantity"]:
            symbol_list.append(h["symbol"])
            qty_map[h["symbol"]] = h["quantity"]

    if not symbol_list:
        return []

    rows = (
        db.query(DividendHistory)
        .filter(
            DividendHistory.symbol.in_(symbol_list),
            or_(
                and_(
                    DividendHistory.payment_date.isnot(None),
                    DividendHistory.payment_date >= year_start,
                    DividendHistory.payment_date <= year_end,
                ),
                and_(
                    DividendHistory.payment_date.is_(None),
                    DividendHistory.ex_date >= year_start,
                    DividendHistory.ex_date <= year_end,
                ),
            ),
        )
        .order_by(DividendHistory.ex_date.desc())
        .all()
    )

    result = []
    for r in rows:
        value = r.value if isinstance(r.value, Decimal) else Decimal(str(r.value))
        qty = Decimal(str(qty_map.get(r.symbol, 0)))
        total = value * qty
        currency = r.currency
        result.append({
            "symbol": r.symbol,
            "dividend_type": r.dividend_type,
            "value": {"amount": str(value), "currency": currency},
            "quantity": float(qty),
            "total": {"amount": str(total.quantize(Decimal("0.01"))), "currency": currency},
            "ex_date": r.ex_date.isoformat(),
            "payment_date": r.payment_date.isoformat() if r.payment_date else None,
        })

    return result


@router.get("/scrape/status")
@limiter.limit("30/minute")
def get_scrape_status(request: Request):
    return {"running": _scraping}
