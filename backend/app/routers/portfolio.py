import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.models.dividend_history import DividendHistory
from app.services.market_data import get_market_data_service, CRYPTO_CLASS_NAMES
from app.services.portfolio import PortfolioService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

# Simple in-memory cache for exchange rate
_fx_cache: dict[str, tuple[float, float]] = {}  # pair -> (rate, timestamp)
_FX_CACHE_TTL = 600  # 10 minutes


@router.get("/summary")
@limiter.limit(CRUD_LIMIT)
def portfolio_summary(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)

    # Build class_map and weight_map for enrichment
    asset_classes = db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()
    class_map = {}
    weight_map = {}
    for ac in asset_classes:
        class_map[ac.id] = {"name": ac.name, "target_weight": ac.target_weight, "country": ac.country}
        weights = db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
        for aw in weights:
            weight_map[aw.symbol] = aw.target_weight

    market_data = get_market_data_service()
    enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data, db=db)
    return {"holdings": enriched}


@router.get("/performance")
@limiter.limit(CRUD_LIMIT)
def portfolio_performance(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)
    total_cost = sum(h["total_cost"] for h in holdings)
    return {"holdings": holdings, "total_cost": total_cost}


@router.get("/allocation")
@limiter.limit(CRUD_LIMIT)
def portfolio_allocation(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    allocation = service.get_allocation(x_user_id)
    return {"allocation": allocation}


def _fetch_exchange_rate(pair: str) -> float:
    """Fetch exchange rate with caching. pair e.g. 'USD-BRL'."""
    now = time.time()
    cached = _fx_cache.get(pair)
    if cached and (now - cached[1]) < _FX_CACHE_TTL:
        return cached[0]

    try:
        resp = httpx.get(
            f"https://economia.awesomeapi.com.br/last/{pair}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        key = pair.replace("-", "")
        rate = float(data[key]["bid"])
        _fx_cache[pair] = (rate, now)
        return rate
    except Exception:
        logger.exception("Failed to fetch exchange rate for %s", pair)
        if cached:
            return cached[0]
        raise


_div_cache: dict[str, tuple[dict, float]] = {}  # symbol -> (data, timestamp)
_DIV_CACHE_TTL = 3600  # 1 hour


@router.get("/dividends")
@limiter.limit(CRUD_LIMIT)
def portfolio_dividends(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    """Get estimated annual dividends per holding using Finnhub (US) and brapi (BR)."""
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)

    asset_classes = db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()
    class_map = {ac.id: ac for ac in asset_classes}

    market_data = get_market_data_service()
    finnhub = market_data._finnhub

    # Pre-compute BR dividend data from local DividendHistory table (current year by payment date)
    # Includes both Dividendo and JCP (Juros sobre Capital Próprio)
    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)
    br_symbols = [
        h["symbol"] for h in holdings
        if class_map.get(h["asset_class_id"]) and class_map[h["asset_class_id"]].country == "BR"
    ]
    br_div_map: dict[str, float] = {}
    if br_symbols:
        rows = (
            db.query(DividendHistory.symbol, func.sum(DividendHistory.value))
            .filter(
                DividendHistory.symbol.in_(br_symbols),
                DividendHistory.payment_date >= year_start,
                DividendHistory.payment_date <= year_end,
            )
            .group_by(DividendHistory.symbol)
            .all()
        )
        for symbol, total in rows:
            br_div_map[symbol] = float(total)

    def fetch_dividend(holding: dict) -> dict | None:
        symbol = holding["symbol"]
        ac = class_map.get(holding["asset_class_id"])
        if not ac:
            return None

        if holding["quantity"] is None:
            return None  # Fixed income — no dividend calculation

        class_name = ac.name
        if class_name in CRYPTO_CLASS_NAMES or class_name == "Stablecoins":
            return None

        if ac.country == "BR":
            dps = br_div_map.get(symbol, 0)
            if dps <= 0:
                return None
            annual_income = dps * holding["quantity"]
            return {
                "symbol": symbol,
                "asset_class_id": holding["asset_class_id"],
                "quantity": holding["quantity"],
                "dividend_per_share": round(dps, 6),
                "dividend_yield": 0,
                "annual_income": round(annual_income, 2),
                "currency": "BRL",
            }

        if ac.country == "US":
            now = time.time()
            cached = _div_cache.get(symbol)
            if cached and (now - cached[1]) < _DIV_CACHE_TTL:
                div_data = cached[0]
            else:
                try:
                    div_data = finnhub.get_dividend_metric(symbol)
                    _div_cache[symbol] = (div_data, now)
                except Exception:
                    logger.warning("Failed to fetch dividend for %s", symbol)
                    return None

            dps = div_data.get("dividend_per_share_annual", 0)
            if dps <= 0:
                return None
            annual_income = dps * holding["quantity"]
            return {
                "symbol": symbol,
                "asset_class_id": holding["asset_class_id"],
                "quantity": holding["quantity"],
                "dividend_per_share": dps,
                "dividend_yield": div_data.get("dividend_yield_annual", 0),
                "annual_income": round(annual_income, 2),
                "currency": "USD",
            }

        return None

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_dividend, h): h for h in holdings}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    # Aggregate by asset class
    class_totals: dict[str, dict] = {}
    for r in results:
        cid = r["asset_class_id"]
        if cid not in class_totals:
            ac = class_map.get(cid)
            class_totals[cid] = {
                "asset_class_id": cid,
                "class_name": ac.name if ac else cid,
                "annual_income": 0,
                "currency": r["currency"],
                "assets": [],
            }
        class_totals[cid]["annual_income"] += r["annual_income"]
        class_totals[cid]["annual_income"] = round(class_totals[cid]["annual_income"], 2)
        class_totals[cid]["assets"].append(r)

    return {
        "dividends": list(class_totals.values()),
        "total_annual_income": round(sum(ct["annual_income"] for ct in class_totals.values()), 2),
    }


@router.get("/exchange-rate")
@limiter.limit(CRUD_LIMIT)
def get_exchange_rate(request: Request, pair: str = "USD-BRL"):
    """Get current exchange rate. Default: USD-BRL."""
    rate = _fetch_exchange_rate(pair)
    return {"pair": pair, "rate": rate}
