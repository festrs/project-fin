from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.schemas.recommendation import InvestmentPlanRequest, InvestmentPlanResponse, InvestmentRecommendationResponse
from app.schemas.money import MoneyResponse
from app.services.exchange_rate import fetch_exchange_rate
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
@limiter.limit(CRUD_LIMIT)
def get_recommendations(
    request: Request,
    count: int = Query(2),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    recommendations = service.get_recommendations(user_id, count=count)
    return {"recommendations": recommendations}


@router.post("/invest", response_model=InvestmentPlanResponse)
@limiter.limit(CRUD_LIMIT)
def invest_plan(
    request: Request,
    body: InvestmentPlanRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    rate = fetch_exchange_rate("USD-BRL")
    exchange_rate = Decimal(str(rate))

    service = RecommendationService(db)
    plan = service.get_investment_plan(
        user_id=user_id,
        amount=Decimal(body.amount),
        currency=body.currency,
        count=body.count,
        exchange_rate=exchange_rate,
    )

    # Convert Money objects to MoneyResponse
    recs_response = []
    for rec in plan["recommendations"]:
        recs_response.append(InvestmentRecommendationResponse(
            symbol=rec["symbol"],
            class_name=rec["class_name"],
            effective_target=rec["effective_target"],
            actual_weight=rec["actual_weight"],
            diff=rec["diff"],
            price=MoneyResponse(amount=str(rec["price"].amount), currency=rec["price"].currency.code),
            quantity=float(rec["quantity"]),
            invest_amount=MoneyResponse(amount=str(rec["invest_amount"].amount), currency=rec["invest_amount"].currency.code),
        ))

    return InvestmentPlanResponse(
        recommendations=recs_response,
        total_invested=MoneyResponse(amount=str(plan["total_invested"].amount), currency=plan["total_invested"].currency.code),
        exchange_rate=plan["exchange_rate"],
        exchange_rate_pair=plan["exchange_rate_pair"],
        remainder=MoneyResponse(amount=str(plan["remainder"].amount), currency=plan["remainder"].currency.code),
        empty_reason=plan.get("empty_reason"),
    )
