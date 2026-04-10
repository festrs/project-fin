from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_id
from app.middleware.rate_limit import limiter
from app.services.tax import TaxService

router = APIRouter(prefix="/api/tax", tags=["tax"])


@router.get("/report")
@limiter.limit("30/minute")
def get_tax_report(
    request: Request,
    year: int = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if year is None:
        year = date.today().year
    svc = TaxService(db)
    return svc.get_monthly_report(user_id, year)
