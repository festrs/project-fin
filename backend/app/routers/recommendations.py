from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, CRUD_LIMIT
from app.services.recommendation import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("")
@limiter.limit(CRUD_LIMIT)
def get_recommendations(
    request: Request,
    count: int = Query(2),
    x_user_id: str = Header(),
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    recommendations = service.get_recommendations(x_user_id, count=count)
    return {"recommendations": recommendations}
