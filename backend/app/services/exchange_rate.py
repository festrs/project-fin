import logging
import time

import httpx

logger = logging.getLogger(__name__)

_fx_cache: dict[str, tuple[float, float]] = {}
_FX_CACHE_TTL = 300  # 5 minutes


def fetch_exchange_rate(pair: str = "USD-BRL") -> float:
    """Fetch exchange rate with caching. pair e.g. 'USD-BRL'."""
    now = time.time()
    cached = _fx_cache.get(pair)
    if cached and (now - cached[1]) < _FX_CACHE_TTL:
        return cached[0]

    try:
        resp = httpx.get(
            f"https://economia.awesomeapi.com.br/last/{pair}",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        key = pair.replace("-", "")
        rate = float(data[key]["bid"])
        _fx_cache[pair] = (rate, now)
        return rate
    except Exception:
        logger.exception("Failed to fetch exchange rate for %s", pair)
        if cached:
            return cached[0]
        return 5.15  # fallback
