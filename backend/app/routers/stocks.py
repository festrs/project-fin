from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

market_data = MarketDataService()


@router.get("/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_quote(request: Request, symbol: str):
    quote = market_data.get_stock_quote(symbol)
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
    }


@router.get("/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    history = market_data.get_stock_history(symbol, period)
    return [{"date": h["date"], "price": h["close"]} for h in history]
