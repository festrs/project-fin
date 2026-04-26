from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def get_device_or_ip(request: Request) -> str:
    """Prefer X-Device-ID header for rate-limiting key, fall back to IP."""
    device_id = request.headers.get("X-Device-ID", "")
    if device_id and len(device_id) <= 64:
        return f"device:{device_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=get_device_or_ip)
MARKET_DATA_LIMIT = "30/minute"
CRUD_LIMIT = "60/minute"
LOGIN_LIMIT = "5/minute"
