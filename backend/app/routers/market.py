from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.models.asset_class import AssetClass
from app.services.exchange_rate import fetch_exchange_rate
from app.services.market_data import CRYPTO_CLASS_NAMES, get_market_data_service
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/indices")
@limiter.limit(MARKET_DATA_LIMIT)
def get_indices(request: Request, db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    indices = []

    # IBOV via ^BVSP
    try:
        ibov = market_data.get_stock_quote("^BVSP", "BR", db)
        indices.append({
            "symbol": "IBOV",
            "name": "Ibovespa",
            "value": str(ibov["current_price"].amount),
            "change_pct": None,
        })
    except Exception:
        indices.append({"symbol": "IBOV", "name": "Ibovespa", "value": None, "change_pct": None})

    # S&P 500 via SPY
    try:
        spy = market_data.get_stock_quote("SPY", "US", db)
        indices.append({
            "symbol": "S&P 500",
            "name": "S&P 500",
            "value": str(spy["current_price"].amount),
            "change_pct": None,
        })
    except Exception:
        indices.append({"symbol": "S&P 500", "name": "S&P 500", "value": None, "change_pct": None})

    # USD/BRL
    try:
        rate: Decimal = fetch_exchange_rate("USD-BRL")
        indices.append({"symbol": "USD/BRL", "name": "Dólar", "value": str(rate), "change_pct": None})
    except Exception:
        indices.append({"symbol": "USD/BRL", "name": "Dólar", "value": None, "change_pct": None})

    return indices


@router.get("/movers")
@limiter.limit(MARKET_DATA_LIMIT)
def get_movers(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    svc = PortfolioService(db)
    holdings = svc.get_holdings(user_id)
    if not holdings:
        return {"gainers": [], "losers": []}

    market_data = get_market_data_service()
    movers = []

    for h in holdings:
        if h.get("avg_price") is None:
            continue
        ac = db.query(AssetClass).filter_by(id=h["asset_class_id"]).first()
        if not ac or ac.name in CRYPTO_CLASS_NAMES:
            continue

        try:
            quote = market_data.get_stock_quote(h["symbol"], ac.country, db)
            current = float(quote["current_price"].amount)
            avg = float(h["avg_price"].amount)
            if avg > 0:
                change_pct = ((current - avg) / avg) * 100
                movers.append({
                    "symbol": h["symbol"],
                    "name": quote.get("name", h["symbol"]),
                    "change_pct": round(change_pct, 2),
                    "current_price": str(quote["current_price"].amount),
                })
        except Exception:
            continue

    movers.sort(key=lambda m: m["change_pct"], reverse=True)
    gainers = [m for m in movers if m["change_pct"] > 0][:3]
    losers = [m for m in movers if m["change_pct"] < 0]
    losers.sort(key=lambda m: m["change_pct"])
    losers = losers[:3]

    return {"gainers": gainers, "losers": losers}
