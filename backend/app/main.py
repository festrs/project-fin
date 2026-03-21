import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    from app.providers.yfinance import YFinanceProvider
    from app.services.dividend_scraper_scheduler import DividendScheduler

    scheduler = DividendScheduler(
        dados_provider=DadosDeMercadoProvider(),
        yfinance_provider=YFinanceProvider(),
        br_delay=settings.dividend_scraper_delay,
        us_delay=settings.dividend_us_delay,
    )

    db = SessionLocal()
    try:
        scheduler.scrape_all(db)
    except Exception:
        logger.exception("Scheduled dividend scrape failed")
    finally:
        db.close()


def _run_split_checker():
    from app.database import SessionLocal
    from app.providers.brapi import BrapiProvider
    from app.services.split_checker_scheduler import SplitCheckerScheduler

    scheduler = SplitCheckerScheduler(
        brapi_provider=BrapiProvider(api_key=settings.brapi_api_key, base_url=settings.brapi_base_url),
    )

    db = SessionLocal()
    try:
        scheduler.check_all(db)
    except Exception:
        logger.exception("Scheduled split check failed")
    finally:
        db.close()


def _run_migrations():
    """Run database migrations before create_all.

    Uses raw sqlite3 to alter existing tables that create_all cannot modify.
    Safe to call repeatedly — each migration checks if already applied.
    """
    from app.config import settings

    db_url = settings.database_url
    if not db_url.startswith("sqlite"):
        return

    # Extract file path from sqlite URL (sqlite:///./data/project_fin.db -> ./data/project_fin.db)
    db_path = db_url.replace("sqlite:///", "")
    from app.migrations import run_all
    run_all(db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()

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
        if settings.enable_split_checker:
            bg_scheduler.add_job(
                _run_split_checker, "cron",
                hour=settings.split_checker_hour,
                id="split_checker",
            )
            logger.info(f"Split checker scheduled (daily at {settings.split_checker_hour}:00 UTC)")
        bg_scheduler.start()
        logger.info(f"Market data scheduler started (runs at {settings.scheduler_hours})")

        import threading
        threading.Thread(target=_run_scheduled_fetch, daemon=True).start()
        if settings.enable_dividend_scraper:
            threading.Thread(target=_run_dividend_scrape, daemon=True).start()

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
    fundamentals, splits, dividends, auth, news,
)

app.include_router(auth.router)
app.include_router(asset_classes.router)
app.include_router(asset_weights.router)
app.include_router(transactions.router)
app.include_router(stocks.router)
app.include_router(crypto.router)
app.include_router(portfolio.router)
app.include_router(recommendations.router)
app.include_router(quarantine.router)
app.include_router(fundamentals.router)
app.include_router(splits.router)
app.include_router(dividends.router)
app.include_router(news.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Serve frontend static files (for production single-container deploy)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
