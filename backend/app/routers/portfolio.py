import logging
import time
from datetime import date
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import and_, func, or_
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


def _money_to_dict(m) -> dict | None:
    if m is None:
        return None
    if isinstance(m, dict):
        return m  # already serialized
    return {"amount": str(m.amount), "currency": m.currency.code}


@router.get("/summary")
@limiter.limit(CRUD_LIMIT)
def portfolio_summary(
    request: Request,
    x_user_id: str = Header(),
    live: bool = True,
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
    enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data, db=db, db_only=not live)
    enriched_serialized = []
    for h in enriched:
        enriched_serialized.append({
            "symbol": h["symbol"],
            "asset_class_id": h["asset_class_id"],
            "quantity": h["quantity"],
            "avg_price": _money_to_dict(h.get("avg_price")),
            "total_cost": _money_to_dict(h["total_cost"]),
            "current_price": _money_to_dict(h.get("current_price")),
            "current_value": _money_to_dict(h.get("current_value")),
            "gain_loss": _money_to_dict(h.get("gain_loss")),
            "target_weight": h.get("target_weight"),
            "actual_weight": h.get("actual_weight"),
        })
    return {"holdings": enriched_serialized}


@router.get("/performance")
@limiter.limit(CRUD_LIMIT)
def portfolio_performance(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)
    total_cost = sum((h["total_cost"].amount for h in holdings), Decimal("0"))
    holdings_serialized = []
    for h in holdings:
        hs = {**h}
        hs["total_cost"] = _money_to_dict(h["total_cost"])
        hs["avg_price"] = _money_to_dict(h.get("avg_price"))
        hs["currency"] = h["currency"].code if hasattr(h.get("currency", ""), "code") else h.get("currency", "")
        holdings_serialized.append(hs)
    return {"holdings": holdings_serialized, "total_cost": str(total_cost)}


@router.get("/allocation")
@limiter.limit(CRUD_LIMIT)
def portfolio_allocation(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = PortfolioService(db)
    allocation = service.get_allocation(x_user_id)
    for ac_data in allocation:
        for asset in ac_data["assets"]:
            asset["total_cost"] = _money_to_dict(asset["total_cost"])
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


@router.get("/dividends")
@limiter.limit(CRUD_LIMIT)
def portfolio_dividends(
    request: Request,
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    """Get estimated annual dividends per holding from dividend_history table."""
    service = PortfolioService(db)
    holdings = service.get_holdings(x_user_id)

    asset_classes = db.query(AssetClass).filter(AssetClass.user_id == x_user_id).all()
    class_map = {ac.id: ac for ac in asset_classes}

    current_year = date.today().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)

    # Collect all stock symbols (BR + US), excluding crypto
    stock_symbols = [
        h["symbol"] for h in holdings
        if class_map.get(h["asset_class_id"])
        and class_map[h["asset_class_id"]].name not in CRYPTO_CLASS_NAMES
        and class_map[h["asset_class_id"]].name != "Stablecoins"
        and class_map[h["asset_class_id"]].country in ("BR", "US")
    ]

    # Single batch query for all dividends (unified BR + US)
    div_map: dict[str, Decimal] = {}
    if stock_symbols:
        rows = (
            db.query(DividendHistory.symbol, func.sum(DividendHistory.value))
            .filter(
                DividendHistory.symbol.in_(stock_symbols),
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
        for symbol, total in rows:
            div_map[symbol] = total if isinstance(total, Decimal) else Decimal(str(total))

    results = []
    for holding in holdings:
        symbol = holding["symbol"]
        ac = class_map.get(holding["asset_class_id"])
        if not ac or holding["quantity"] is None:
            continue
        if ac.name in CRYPTO_CLASS_NAMES or ac.name == "Stablecoins":
            continue

        dps = div_map.get(symbol, Decimal("0"))
        if dps <= 0:
            continue

        annual_income_val = dps * Decimal(str(holding["quantity"]))
        currency = "BRL" if ac.country == "BR" else "USD"

        results.append({
            "symbol": symbol,
            "asset_class_id": holding["asset_class_id"],
            "quantity": holding["quantity"],
            "dividend_per_share": {"amount": str(dps), "currency": currency},
            "dividend_yield": 0,
            "annual_income": {"amount": str(annual_income_val.quantize(Decimal("0.01"))), "currency": currency},
            "currency": currency,
        })

    # Aggregate by asset class
    class_totals: dict[str, dict] = {}
    for r in results:
        cid = r["asset_class_id"]
        if cid not in class_totals:
            ac = class_map.get(cid)
            class_totals[cid] = {
                "asset_class_id": cid,
                "class_name": ac.name if ac else cid,
                "annual_income": Decimal("0"),
                "currency": r["currency"],
                "assets": [],
            }
        class_totals[cid]["annual_income"] += Decimal(r["annual_income"]["amount"])
        class_totals[cid]["assets"].append(r)

    # Serialize class totals
    for ct in class_totals.values():
        ct["annual_income"] = {"amount": str(ct["annual_income"].quantize(Decimal("0.01"))), "currency": ct["currency"]}

    total_annual = sum(
        (Decimal(ct["annual_income"]["amount"]) for ct in class_totals.values()),
        Decimal("0"),
    )

    return {
        "dividends": list(class_totals.values()),
        "total_annual_income": {"amount": str(total_annual.quantize(Decimal("0.01"))), "currency": "mixed"},
    }


@router.get("/exchange-rate")
@limiter.limit(CRUD_LIMIT)
def get_exchange_rate(request: Request, pair: str = "USD-BRL"):
    """Get current exchange rate. Default: USD-BRL."""
    rate = _fetch_exchange_rate(pair)
    return {"pair": pair, "rate": rate}
