from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT
from app.services.market_data import get_market_data_service

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


def _money_to_dict(m) -> dict | None:
    if m is None:
        return None
    if isinstance(m, dict):
        return m  # already serialized
    return {"amount": str(m.amount), "currency": m.currency.code}


def _detect_country(symbol: str) -> tuple[str, str]:
    """Detect country from symbol. Returns (clean_symbol, country)."""
    if symbol.endswith(".SA"):
        return symbol, "BR"
    return symbol, "US"


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
def search_stocks(request: Request, q: str = Query(min_length=1)):
    """Search for stocks across US (Finnhub) and BR (Brapi) markets."""
    market_data = get_market_data_service()
    results = []
    try:
        results.extend(market_data._finnhub.search(q))
    except Exception:
        pass
    try:
        results.extend(market_data._brapi.search(q))
    except Exception:
        pass
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
def get_us_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="US")
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
def get_br_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(symbol, period, country="BR")
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
def get_stock_history(request: Request, symbol: str, period: str = Query("1mo")):
    """Auto-detect country from symbol and return history."""
    sym, country = _detect_country(symbol)
    market_data = get_market_data_service()
    try:
        history = market_data.get_stock_history(sym, period, country=country)
    except Exception:
        raise HTTPException(status_code=502, detail=f"Failed to fetch history for {symbol}")
    currency_code = "BRL" if country == "BR" else "USD"
    return [{"date": h["date"], "price": {"amount": str(h["close"]), "currency": currency_code}} for h in history]
