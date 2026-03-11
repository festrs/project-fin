from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.models.asset_class import AssetClass
from app.models.asset_weight import AssetWeight
from app.services.market_data import MarketDataService
from app.services.portfolio import PortfolioService

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


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
        class_map[ac.id] = {"name": ac.name, "target_weight": ac.target_weight}
        weights = db.query(AssetWeight).filter(AssetWeight.asset_class_id == ac.id).all()
        for aw in weights:
            weight_map[aw.symbol] = aw.target_weight

    market_data = MarketDataService()
    enriched = PortfolioService.enrich_holdings(holdings, class_map, weight_map, market_data)
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
