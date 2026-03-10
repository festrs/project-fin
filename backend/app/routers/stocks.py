from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

market_data = MarketDataService()


@router.get("/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_quote(request: Request, symbol: str):
    return market_data.get_stock_quote(symbol)


@router.get("/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    return market_data.get_stock_history(symbol, period)
