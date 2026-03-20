from fastapi import APIRouter, HTTPException, Query, Request

from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import get_market_data_service

router = APIRouter(prefix="/api/crypto", tags=["crypto"])


def _money_to_dict(m) -> dict | None:
    if m is None:
        return None
    if isinstance(m, dict):
        return m  # already serialized
    return {"amount": str(m.amount), "currency": m.currency.code}


@router.get("/{coin_id}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_quote(request: Request, coin_id: str):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_crypto_quote(coin_id)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {coin_id}")
    return {
        "coin_id": quote["coin_id"],
        "name": coin_id,
        "price": _money_to_dict(quote["current_price"]),
        "currency": "USD",
        "market_cap": _money_to_dict(quote["market_cap"]),
        "change_24h": quote.get("change_24h"),
    }


@router.get("/{coin_id}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_crypto_history(request: Request, coin_id: str, days: int = Query(30)):
    market_data = get_market_data_service()
    history = market_data.get_crypto_history(coin_id, days)
    return [{"date": h["date"], "price": {"amount": str(h["price"]), "currency": "USD"}} for h in history]
