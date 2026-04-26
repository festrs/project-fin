import hmac

from fastapi import Header, HTTPException

from app.config import settings


def verify_mobile_api_key(x_api_key: str = Header(default="")) -> None:
    """Validate the X-API-Key header for mobile endpoints.

    In production (MOBILE_API_KEY is set), the key is required.
    In local development (MOBILE_API_KEY is empty), validation is skipped.
    """
    if not settings.mobile_api_key:
        import logging
        logging.getLogger(__name__).warning("MOBILE_API_KEY not set — auth disabled")
        return

    if not x_api_key or not hmac.compare_digest(x_api_key, settings.mobile_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
