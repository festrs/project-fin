from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/crypto", tags=["crypto"])

market_data = MarketDataService()


@router.get("/{coin_id}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_quote(request: Request, coin_id: str):
    quote = market_data.get_crypto_quote(coin_id)
    return {
        "coin_id": quote["coin_id"],
        "name": coin_id,
        "price": quote["current_price"],
        "currency": quote["currency"],
        "market_cap": quote["market_cap"],
        "change_24h": quote.get("change_24h"),
    }


@router.get("/{coin_id}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_history(request: Request, coin_id: str, days: int = Query(30)):
    return market_data.get_crypto_history(coin_id, days)
