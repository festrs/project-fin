from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limit import limiter, LOGIN_LIMIT
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit(LOGIN_LIMIT)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return LoginResponse(
        access_token=token,
        user=UserInfo(id=user.id, name=user.name, email=user.email),
    )
