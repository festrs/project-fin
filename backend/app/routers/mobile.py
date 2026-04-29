"""
Mobile-specific endpoints.

These endpoints serve the Tranquilidade iOS app.
The app stores its portfolio locally in SwiftData + iCloud.
The backend only provides market data: prices, dividends, exchange rates.

All endpoints require a valid X-API-Key header (see dependencies_mobile.py).
"""

import asyncio
import logging
import re
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies_mobile import verify_mobile_api_key
from app.middleware.rate_limit import limiter, MARKET_DATA_LIMIT, CRUD_LIMIT
from app.models.dividend_history import DividendHistory
from app.models.fundamentals_score import FundamentalsScore
from app.models.tracked_symbol import TrackedSymbol
from app.providers.common import Symbol
from app.services.exchange_rate import fetch_exchange_rate as _fetch_exchange_rate
from app.services.market_data import get_market_data_service

logger = logging.getLogger(__name__)

MAX_SYMBOLS_PER_REQUEST = 50
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]{1,20}$")
PAIR_PATTERN = re.compile(r"^[A-Z]{3}-[A-Z]{3}$")

router = APIRouter(
    prefix="/api/mobile",
    tags=["mobile"],
    dependencies=[Depends(verify_mobile_api_key)],
)


def _validate_symbols(raw: str) -> list[str]:
    """Parse, validate, and return a list of symbols from a comma-separated string."""
    symbol_list = [s.strip() for s in raw.split(",") if s.strip()]
    if len(symbol_list) > MAX_SYMBOLS_PER_REQUEST:
        raise HTTPException(
            status_code=422,
            detail=f"Too many symbols (max {MAX_SYMBOLS_PER_REQUEST})",
        )
    for s in symbol_list:
        if not SYMBOL_PATTERN.match(s):
            raise HTTPException(status_code=422, detail=f"Invalid symbol: {s}")
    return symbol_list


def _money_to_dict(m) -> dict | None:
    if m is None:
        return None
    if isinstance(m, dict):
        return m
    return {"amount": str(m.amount), "currency": m.currency.code}


# ──────────────────────────────────────────────
# Exchange Rate
# ──────────────────────────────────────────────

@router.get("/exchange-rate")
@limiter.limit(MARKET_DATA_LIMIT)
def get_exchange_rate(
    request: Request,
    pair: str = Query(default="USD-BRL"),
):
    """Get exchange rate for a currency pair."""
    if not PAIR_PATTERN.match(pair):
        raise HTTPException(status_code=422, detail=f"Invalid pair format: {pair}")
    rate: Decimal = _fetch_exchange_rate(pair)
    return {"pair": pair, "rate": str(rate)}


# ──────────────────────────────────────────────
# Batch Quotes
# ──────────────────────────────────────────────

_CRYPTO_COIN_MAP = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
    "ADA": "cardano", "DOT": "polkadot", "AVAX": "avalanche-2",
    "MATIC": "matic-network",
}


def _fetch_one_quote(market_data, symbol: str) -> dict | None:
    """Resolve a single symbol's quote via the right provider.

    Pure function so it's easy to fan out via asyncio.to_thread.
    Returns None on failure — caller filters them out.
    """
    try:
        if symbol.upper() in _CRYPTO_COIN_MAP:
            coin_id = _CRYPTO_COIN_MAP[symbol.upper()]
            quote = market_data.get_crypto_quote(coin_id)
        elif Symbol.is_br(symbol):
            quote = market_data.get_stock_quote(symbol, country="BR")
        else:
            quote = market_data.get_stock_quote(symbol, country="US")
    except Exception as e:
        logger.warning("Failed to fetch quote for %s: %s", symbol, e)
        return None

    currency = quote.get("currency")
    return {
        "symbol": symbol,
        "name": quote.get("name", symbol),
        "price": _money_to_dict(quote.get("current_price")),
        "currency": currency.code if hasattr(currency, "code") else str(currency or "USD"),
    }


@router.get("/quotes")
@limiter.limit(MARKET_DATA_LIMIT)
async def get_batch_quotes(
    request: Request,
    symbols: str = Query(description="Comma-separated symbols, e.g. ITUB3.SA,AAPL,BTC"),
):
    """Get current prices for a list of symbols, fanned-out in parallel.

    Each symbol's provider call runs concurrently via asyncio.to_thread, so
    request latency is bounded by the slowest single provider call rather
    than summing across all symbols.
    """
    symbol_list = _validate_symbols(symbols)
    if not symbol_list:
        return {"quotes": []}

    market_data = get_market_data_service()
    fetched = await asyncio.gather(
        *(asyncio.to_thread(_fetch_one_quote, market_data, s) for s in symbol_list),
        return_exceptions=False,
    )
    results = [q for q in fetched if q is not None]
    return {"quotes": results}


# ──────────────────────────────────────────────
# Dividends for symbols
# ──────────────────────────────────────────────

@router.get("/dividends")
@limiter.limit(CRUD_LIMIT)
def get_dividends_for_symbols(
    request: Request,
    symbols: str = Query(description="Comma-separated symbols"),
    year: int = Query(default=None, description="Year to filter, defaults to current"),
    db: Session = Depends(get_db),
):
    """Get dividend history for specific symbols.

    The mobile app sends its local portfolio symbols to get dividend data.
    """
    symbol_list = _validate_symbols(symbols)
    if not symbol_list:
        return []

    target_year = year or date.today().year
    year_start = date(target_year, 1, 1)
    year_end = date(target_year, 12, 31)

    query_symbols = Symbol.expand_variants(symbol_list)

    rows = (
        db.query(DividendHistory)
        .filter(
            DividendHistory.symbol.in_(query_symbols),
            or_(
                and_(
                    DividendHistory.payment_date.isnot(None),
                    DividendHistory.payment_date >= year_start,
                    DividendHistory.payment_date <= year_end,
                ),
                and_(
                    DividendHistory.payment_date.is_(None),
                    DividendHistory.ex_date >= year_start,
                    DividendHistory.ex_date <= year_end,
                ),
            ),
        )
        .order_by(DividendHistory.ex_date.desc())
        .all()
    )

    # Echo back the symbol the client sent, not the .SA-suffixed DB form.
    canonical = {s.removesuffix(".SA"): s for s in symbol_list}

    result = []
    for r in rows:
        value = r.value if isinstance(r.value, Decimal) else Decimal(str(r.value))
        currency = r.currency if r.currency else "BRL"
        client_symbol = canonical.get(r.symbol.removesuffix(".SA"), r.symbol)
        result.append({
            "symbol": client_symbol,
            "dividend_type": r.dividend_type,
            "value": {"amount": str(value), "currency": currency},
            "ex_date": r.ex_date.isoformat(),
            "payment_date": r.payment_date.isoformat() if r.payment_date else None,
        })

    return result


# ──────────────────────────────────────────────
# Dividend summary per symbol
# ──────────────────────────────────────────────

@router.get("/dividends/summary")
@limiter.limit(CRUD_LIMIT)
def get_dividend_summary(
    request: Request,
    symbols: str = Query(description="Comma-separated symbols"),
    db: Session = Depends(get_db),
):
    """Get annual dividend-per-share for symbols (current year)."""
    symbol_list = _validate_symbols(symbols)
    if not symbol_list:
        return {}

    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    query_symbols = Symbol.expand_variants(symbol_list)

    rows = (
        db.query(DividendHistory.symbol, func.sum(DividendHistory.value))
        .filter(
            DividendHistory.symbol.in_(query_symbols),
            or_(
                and_(
                    DividendHistory.payment_date.isnot(None),
                    DividendHistory.payment_date >= year_start,
                    DividendHistory.payment_date <= year_end,
                ),
                and_(
                    DividendHistory.payment_date.is_(None),
                    DividendHistory.ex_date >= year_start,
                    DividendHistory.ex_date <= year_end,
                ),
            ),
        )
        .group_by(DividendHistory.symbol)
        .all()
    )

    # Collapse .SA / bare duplicates back to the symbol the client requested.
    canonical = {s.removesuffix(".SA"): s for s in symbol_list}
    result: dict[str, dict] = {}
    for symbol, total in rows:
        client_symbol = canonical.get(symbol.removesuffix(".SA"), symbol)
        dps = total if isinstance(total, Decimal) else Decimal(str(total))
        existing = result.get(client_symbol)
        if existing is None or Decimal(existing["dividend_per_share"]) < dps:
            result[client_symbol] = {"dividend_per_share": str(dps)}

    return result


# ──────────────────────────────────────────────
# Symbol Tracking (iOS tells backend which symbols to keep fresh)
# ──────────────────────────────────────────────

ASSET_CLASS_COUNTRY = {
    "acoesBR": "BR", "fiis": "BR", "rendaFixa": "BR",
    "usStocks": "US", "reits": "US", "crypto": "US",
}


@router.post("/track", status_code=201)
@limiter.limit(CRUD_LIMIT)
def track_symbol(
    request: Request,
    symbol: str = Query(description="Symbol to track, e.g. HGLG11.SA"),
    asset_class: str = Query(description="Asset class, e.g. fiis, acoesBR, usStocks"),
    db: Session = Depends(get_db),
):
    """Register a symbol for background price/dividend updates."""
    if not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=422, detail=f"Invalid symbol: {symbol}")
    if asset_class not in ASSET_CLASS_COUNTRY:
        raise HTTPException(status_code=422, detail=f"Invalid asset_class: {asset_class}")
    country = ASSET_CLASS_COUNTRY[asset_class]
    existing = db.query(TrackedSymbol).filter_by(symbol=symbol).first()
    if existing:
        existing.asset_class = asset_class
        existing.country = country
    else:
        db.add(TrackedSymbol(symbol=symbol, asset_class=asset_class, country=country))
    db.commit()
    return {"symbol": symbol, "asset_class": asset_class, "country": country}


@router.delete("/track/{symbol}", status_code=204)
@limiter.limit(CRUD_LIMIT)
def untrack_symbol(
    request: Request,
    symbol: str,
    db: Session = Depends(get_db),
):
    """Stop tracking a symbol."""
    db.query(TrackedSymbol).filter_by(symbol=symbol).delete()
    db.commit()


@router.post("/track/sync", status_code=200)
@limiter.limit(CRUD_LIMIT)
def sync_tracked_symbols(
    request: Request,
    symbols: str = Query(description="Comma-separated symbol:asset_class pairs, e.g. HGLG11.SA:fiis,AAPL:usStocks"),
    db: Session = Depends(get_db),
):
    """Bulk sync tracked symbols. Adds missing, updates existing."""
    pairs = [p.strip() for p in symbols.split(",") if ":" in p]
    if len(pairs) > MAX_SYMBOLS_PER_REQUEST:
        raise HTTPException(
            status_code=422,
            detail=f"Too many symbols (max {MAX_SYMBOLS_PER_REQUEST})",
        )
    incoming: dict[str, str] = {}
    for pair in pairs:
        sym, cls = pair.split(":", 1)
        sym, cls = sym.strip(), cls.strip()
        if not SYMBOL_PATTERN.match(sym):
            raise HTTPException(status_code=422, detail=f"Invalid symbol: {sym}")
        if cls not in ASSET_CLASS_COUNTRY:
            raise HTTPException(status_code=422, detail=f"Invalid asset_class: {cls}")
        incoming[sym] = cls

    # Upsert incoming (never remove — symbols are shared across users)
    for symbol, asset_class in incoming.items():
        country = ASSET_CLASS_COUNTRY.get(asset_class, "BR")
        ts = db.query(TrackedSymbol).filter_by(symbol=symbol).first()
        if ts:
            ts.asset_class = asset_class
            ts.country = country
        else:
            db.add(TrackedSymbol(symbol=symbol, asset_class=asset_class, country=country))

    db.commit()
    return {"tracked": len(incoming)}


# ──────────────────────────────────────────────
# On-demand dividend refresh
# ──────────────────────────────────────────────

# Keep a tiny set of symbols per request so a single refresh call doesn't
# exceed sensible request budgets when each symbol triggers an upstream HTTP
# fetch with provider-side rate limiting.
MAX_REFRESH_SYMBOLS = 20

# Mirrors DividendScheduler._TRACKED_FII_CLASSES: only the FII rows need the
# class_name promoted from the iOS asset_class string so the BR fetch chain
# skips DadosDeMercado (which doesn't cover FIIs).
_REFRESH_FII_CLASSES = {"fiis"}


@router.post("/dividends/refresh", status_code=200)
@limiter.limit("4/minute")
def refresh_dividends(
    request: Request,
    symbols: str = Query(description="Comma-separated symbols to refresh"),
    asset_class: str = Query(description="Asset class for these symbols, e.g. fiis"),
    since: str | None = Query(
        default=None,
        description="Optional cutoff date (YYYY-MM-DD). Records with payment/ex date earlier than this are skipped. Use the holding's first-transaction date for auto-fetch; leave empty for full history.",
    ),
    db: Session = Depends(get_db),
):
    """Run the dividend scraper inline for the given symbols.

    Used by the iOS app when a holding was just added and the next cron run
    is hours away. Synchronously calls the upstream provider chain
    (Brapi → yfinance → DadosDeMercado depending on country/class), writes
    new records to `dividend_history`, and returns counts. Caller is expected
    to refetch `/mobile/dividends` afterwards.

    Pass `since` (the holding's first-transaction date) on the auto-bootstrap
    path so we don't pull dividends from before the user held the asset.
    The manual refresh button omits it to allow backfills.
    """
    symbol_list = _validate_symbols(symbols)
    if not symbol_list:
        return {"scraped": 0, "new_records": 0, "failed": []}
    if len(symbol_list) > MAX_REFRESH_SYMBOLS:
        raise HTTPException(
            status_code=422,
            detail=f"Too many symbols (max {MAX_REFRESH_SYMBOLS} per refresh)",
        )
    if asset_class not in ASSET_CLASS_COUNTRY:
        raise HTTPException(status_code=422, detail=f"Invalid asset_class: {asset_class}")
    country = ASSET_CLASS_COUNTRY[asset_class]
    if asset_class == "crypto":
        raise HTTPException(status_code=422, detail="Crypto has no dividends")

    parsed_since = None
    if since:
        try:
            parsed_since = date.fromisoformat(since)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid since (expected YYYY-MM-DD): {since}")

    class_name = "FIIs" if asset_class in _REFRESH_FII_CLASSES else asset_class
    rows = [(s, country, class_name) for s in symbol_list]

    from app.config import settings as _settings
    from app.providers.brapi import BrapiProvider
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.providers.yfinance import YFinanceProvider
    from app.services.dividend_scraper_scheduler import DividendScheduler

    scheduler = DividendScheduler(
        dados_provider=DadosDeMercadoProvider(),
        yfinance_provider=YFinanceProvider(),
        brapi_provider=BrapiProvider(
            api_key=_settings.brapi_api_key,
            base_url=_settings.brapi_base_url,
        ),
        br_delay=_settings.dividend_scraper_delay,
        us_delay=_settings.dividend_us_delay,
    )
    return scheduler.scrape_symbols(db, rows, since=parsed_since)


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

@router.get("/fundamentals/{symbol}")
@limiter.limit(MARKET_DATA_LIMIT)
def get_fundamentals(
    request: Request,
    symbol: str,
    db: Session = Depends(get_db),
):
    """Return fundamentals score for a symbol, fetching on-demand if not cached."""
    _validate_symbols(symbol)
    score = db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    if score is None:
        score = _fetch_fundamentals_on_demand(symbol, db)
    if score is None:
        raise HTTPException(status_code=404, detail=f"No fundamentals for {symbol}")
    return _fundamentals_to_dict(score)


def _fetch_fundamentals_on_demand(symbol: str, db: Session):
    """Fetch and score fundamentals for a symbol that has no cached score."""
    try:
        from app.routers.fundamentals import _refresh_score
        _refresh_score(symbol, db)
        return db.query(FundamentalsScore).filter_by(symbol=symbol).first()
    except Exception:
        logger.warning("On-demand fundamentals fetch failed for %s", symbol, exc_info=True)
        return None


def _fundamentals_to_dict(score: FundamentalsScore) -> dict:
    return {
        "symbol": score.symbol,
        "ipo_years": score.ipo_years,
        "ipo_rating": score.ipo_rating,
        "eps_growth_pct": score.eps_growth_pct,
        "eps_rating": score.eps_rating,
        "current_net_debt_ebitda": score.current_net_debt_ebitda,
        "high_debt_years_pct": score.high_debt_years_pct,
        "debt_rating": score.debt_rating,
        "profitable_years_pct": score.profitable_years_pct,
        "profit_rating": score.profit_rating,
        "composite_score": score.composite_score,
        "updated_at": score.updated_at.isoformat() if score.updated_at else None,
    }
