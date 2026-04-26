"""Shared httpx clients with HTTP/2 keep-alive.

A single, long-lived httpx.Client per upstream means TLS handshakes and TCP
sockets get reused across requests. Each `httpx.get(...)` call would otherwise
open a fresh connection — measurable latency savings on the hot quote/search
paths where providers get called many times per minute.

All clients live for the process lifetime; FastAPI doesn't need to close them
explicitly. Tests can patch the module-level instances if needed.
"""
import httpx

# 8s timeout matches the most-restrictive existing per-call timeout in providers
# so behaviour stays the same on slow upstreams. Connection pool sized for
# bursts when /api/mobile/quotes parallel-fetches a portfolio.
_LIMITS = httpx.Limits(max_connections=32, max_keepalive_connections=16)
_TIMEOUT = httpx.Timeout(connect=4.0, read=15.0, write=8.0, pool=4.0)


def _client() -> httpx.Client:
    return httpx.Client(limits=_LIMITS, timeout=_TIMEOUT, http2=False)


# One per provider so a stuck upstream can't starve the others' pool.
brapi_client = _client()
finnhub_client = _client()
coingecko_client = _client()
dados_client = _client()
exchange_client = _client()
