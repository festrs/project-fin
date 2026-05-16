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
    """Canonicalize and detect country. Returns (canonical_symbol, country).

    Accepts either form on input (`ITUB3` or `ITUB3.SA`) so legacy callers
    keep working; downstream provider/storage code always sees the canonical
    form.
    """
    canonical = Symbol.canonicalize(symbol)
    return canonical, Symbol.country(canonical)


def _quote_to_response(quote: dict) -> dict:
    dy = quote.get("dividend_yield")
    return {
        "symbol": Symbol.canonicalize(quote["symbol"]),
        "name": quote["name"],
        "price": _money_to_dict(quote["current_price"]),
        "currency": quote["currency"].code if hasattr(quote["currency"], "code") else quote["currency"],
        "market_cap": _money_to_dict(quote["market_cap"]),
        "dividend_yield": str(dy) if dy is not None else None,
    }


@router.get("/search")
@limiter.limit(MARKET_DATA_LIMIT)
async def search_stocks(
    request: Request,
    q: str = Query(min_length=1),
    asset_class: str | None = Query(default=None, description="iOS AssetClassType.rawValue (acoesBR, fiis, usStocks, reits, crypto, rendaFixa)"),
):
    """Class-aware unified search.

    Backed by yfinance for stocks/FIIs/REITs and CoinGecko for crypto. When
    ``asset_class`` is given, the provider only returns matches for that
    class (and yfinance gets a chance to retry BR queries with a ``.SA``
    suffix to hit B3 ticker matches). BR results are enriched with Brapi
    price/logo when available; the search degrades gracefully if Brapi is
    down.
    """
    market_data = get_market_data_service()
    raw = await market_data.search_stocks(q, asset_class=asset_class)

    seen: set[str] = set()
    results = []
    for item in raw:
        symbol = item.get("symbol", "")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        result = {
            "id": symbol,
            "symbol": symbol,
            "name": item.get("name"),
            "type": item.get("type"),
        }
        for key in ("price", "currency", "change", "sector", "industry", "logo"):
            value = item.get(key)
            if value is not None:
                result[key] = value
        results.append(result)

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
