from fastapi import APIRouter, HTTPException, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import get_market_data_service

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_quote(request: Request, symbol: str):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
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
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    return [{"date": h["date"], "price": h["close"]} for h in history]
