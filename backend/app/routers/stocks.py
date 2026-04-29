import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies_mobile import verify_mobile_api_key
from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.providers.common import Symbol
from app.services.market_data import get_market_data_service

router = APIRouter(
    prefix="/api/stocks",
    tags=["stocks"],
    dependencies=[Depends(verify_mobile_api_key)],
)


def _money_to_dict(m) -> dict | None:
    if m is None:
        return None
    if isinstance(m, dict):
        return m  # already serialized
    return {"amount": str(m.amount), "currency": m.currency.code}


def _detect_country(symbol: str) -> tuple[str, str]:
    """Detect country from symbol. Returns (clean_symbol, country)."""
    return symbol, Symbol.country(symbol)


def _quote_to_response(quote: dict) -> dict:
    return {
        "symbol": quote["symbol"],
        "name": quote["name"],
        "price": _money_to_dict(quote["current_price"]),
        "currency": quote["currency"].code if hasattr(quote["currency"], "code") else quote["currency"],
        "market_cap": _money_to_dict(quote["market_cap"]),
    }


@router.get("/search")
@limiter.limit(MARKET_DATA_LIMIT)
async def search_stocks(request: Request, q: str = Query(min_length=1)):
    """Search for stocks across US (Finnhub), BR (Brapi), and crypto markets.

    Each provider runs in parallel via asyncio.gather so total latency is
    max(provider_times) instead of sum. Crypto runs first in the merge so
    that on duplicate symbols the crypto record wins (the dedupe loop keeps
    the first occurrence). The final list is sorted alphabetically by name
    for the iOS client.
    """
    market_data = get_market_data_service()

    async def _safe(fn, *args):
        try:
            return await asyncio.to_thread(fn, *args)
        except Exception:
            return []

    crypto_res, finnhub_res, brapi_res = await asyncio.gather(
        _safe(market_data.search_crypto, q),
        _safe(market_data._finnhub.search, q),
        _safe(market_data._brapi.search, q),
    )
    raw = list(crypto_res) + list(finnhub_res) + list(brapi_res)

    # Deduplicate by symbol — first occurrence (crypto-first) wins
    seen: set[str] = set()
    results = []
    for item in raw:
        symbol = item.get("symbol", "")
        if symbol and symbol not in seen:
            seen.add(symbol)
            result = {
                "id": symbol,
                "symbol": symbol,
                "name": item.get("name"),
                "type": item.get("type"),
            }
            # Include enriched fields when available (from brapi /api/quote/list)
            if item.get("price") is not None:
                result["price"] = item["price"]
            if item.get("currency"):
                result["currency"] = item["currency"]
            if item.get("change") is not None:
                result["change"] = item["change"]
            if item.get("sector"):
                result["sector"] = item["sector"]
            if item.get("logo"):
                result["logo"] = item["logo"]
            results.append(result)

    # Sort alphabetically by name (case-insensitive); fall back to symbol
    # when name is missing so unnamed entries stay deterministic.
    results.sort(key=lambda r: ((r.get("name") or r.get("symbol") or "").lower(), r.get("symbol") or ""))
    return results


# Specific country routes first (before catch-all /{symbol})

@router.get("/us/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_us_stock_quote(request: Request, symbol: str, db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(symbol, country="US", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
    return _quote_to_response(quote)


@router.get("/us/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_us_stock_history(request: Request, symbol: str, period: str = Query("1mo"), db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="US", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    return [{"date": h["date"], "price": {"amount": str(h["close"]), "currency": "USD"}} for h in history]


@router.get("/br/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_br_stock_quote(request: Request, symbol: str, db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(symbol, country="BR", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
    return _quote_to_response(quote)


@router.get("/br/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_br_stock_history(request: Request, symbol: str, period: str = Query("1mo"), db: Session = Depends(get_db)):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="BR", db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    return [{"date": h["date"], "price": {"amount": str(h["close"]), "currency": "BRL"}} for h in history]


# Generic routes (auto-detect country from symbol)

@router.get("/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_quote(request: Request, symbol: str, db: Session = Depends(get_db)):
    """Auto-detect country from symbol and return quote."""
    sym, country = _detect_country(symbol)
    market_data = get_market_data_service()
    try:
        quote = market_data.get_stock_quote(sym, country=country, db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch quote for {symbol}")
    return _quote_to_response(quote)


@router.get("/{symbol}/history")
@limiter.limit(MARKET_DATA_LIMIT)
def get_stock_history(request: Request, symbol: str, period: str = Query("1mo"), db: Session = Depends(get_db)):
    """Auto-detect country from symbol and return history."""
    sym, country = _detect_country(symbol)
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(sym, period, country=country, db=db)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    currency_code = "BRL" if country == "BR" else "USD"
    return [{"date": h["date"], "price": {"amount": str(h["close"]), "currency": currency_code}} for h in history]
