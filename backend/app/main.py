import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)


def _run_scheduled_fetch():
    from app.database import SessionLocal
    from app.services.market_data import get_market_data_service

    service = get_market_data_service()
    from app.services.market_data_scheduler import MarketDataScheduler
    scheduler = MarketDataScheduler(
        finnhub_provider=service._finnhub,
        brapi_provider=service._brapi,
    )

    db = SessionLocal()
    try:
        scheduler.fetch_all_quotes(db)
    except Exception:
        logger.exception("Scheduled market data fetch failed")
    finally:
        db.close()


def _run_dividend_scrape():
    from app.database import SessionLocal
    from app.providers.dados_de_mercado import DadosDeMercadoProvider
    from app.services.dividend_scraper_scheduler import DividendScraperScheduler

    provider = DadosDeMercadoProvider()
    scheduler = DividendScraperScheduler(provider=provider, delay=settings.dividend_scraper_delay)

    db = SessionLocal()
    try:
        scheduler.scrape_all(db)
    except Exception:
        logger.exception("Scheduled dividend scrape failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    from app.seed import seed_data
    seed_data()

    bg_scheduler = None
    if settings.enable_scheduler:
        from apscheduler.schedulers.background import BackgroundScheduler
        bg_scheduler = BackgroundScheduler()
        bg_scheduler.add_job(
            _run_scheduled_fetch, "cron",
            hour=settings.scheduler_hours,
            id="market_data_fetch",
        )
        if settings.enable_dividend_scraper:
            bg_scheduler.add_job(
                _run_dividend_scrape, "cron",
                day_of_week=settings.dividend_scraper_days,
                hour=settings.dividend_scraper_hour,
                id="dividend_scrape",
            )
            logger.info(
                f"Dividend scraper scheduled ({settings.dividend_scraper_days} at {settings.dividend_scraper_hour}:00 UTC)"
            )
        bg_scheduler.start()
        logger.info(f"Market data scheduler started (runs at {settings.scheduler_hours})")

        import threading
        threading.Thread(target=_run_scheduled_fetch, daemon=True).start()

    yield

    if bg_scheduler is not None:
        bg_scheduler.shutdown()
        logger.info("Market data scheduler stopped")


app = FastAPI(title="Project Fin", version="0.1.0", lifespan=lifespan)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
