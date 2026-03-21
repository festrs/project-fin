from fastapi import APIRouter, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import get_market_data_service

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
@limiter.limit(MARKET_DATA_LIMIT)
def get_market_news(request: Request):
    market_data = get_market_data_service()
    try:
        news = market_data._finnhub.get_market_news()
        return {"news": news}
    except Exception:
        return {"news": []}
