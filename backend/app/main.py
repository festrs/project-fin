from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter

app = FastAPI(title="Project Fin", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.routers import (
    asset_classes, asset_weights, transactions,
    stocks, crypto, portfolio, recommendations, quarantine,
)

app.include_router(asset_classes.router)
app.include_router(asset_weights.router)
app.include_router(transactions.router)
app.include_router(stocks.router)
app.include_router(crypto.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(quarantine.router)


@app.on_event("startup")
def startup():
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed import seed_data
    seed_data()


@app.get("/api/health")
def health():
    return {"status": "ok"}
