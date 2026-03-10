from fastapi import APIRouter, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import MarketDataService

router = APIRouter(prefix="/api/crypto", tags=["crypto"])

market_data = MarketDataService()


@router.get("/{coin_id}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_quote(request: Request, coin_id: str):
    return market_data.get_crypto_quote(coin_id)


@router.get("/{coin_id}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_history(request: Request, coin_id: str, days: int = Query(30)):
    return market_data.get_crypto_history(coin_id, days)
