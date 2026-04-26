#!/usr/bin/env python3
"""Backend load test — measures latency under simulated concurrent users.

Uses asyncio + httpx so no extra deps (project already pulls httpx via
requirements). Each "user" runs a tight read-mostly loop hitting the same
endpoints the iOS app uses, with realistic think-time between calls.

Usage:
    python scripts/load_test.py \\
        --base https://grove-invest-api.fly.dev \\
        --api-key "$MOBILE_API_KEY" \\
        --users 50 \\
        --duration 30

Output: per-endpoint p50/p95/p99 latency, throughput, error rate, plus a
projected user-capacity number based on the slowest p95.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx


# ────────────────────────────────────────────────
# Endpoint definitions — keep in sync with the iOS hot path
# ────────────────────────────────────────────────


@dataclass
class Endpoint:
    name: str
    method: str
    path: str
    # Returns (path_or_url, params) — lets us vary symbols/queries per call.
    build: Callable[[], tuple[str, dict]] = field(default_factory=lambda: lambda: ("", {}))
    weight: int = 1


SAMPLE_SYMBOLS_BR = ["KNRI11", "BTLG11", "ITUB3", "PETR4", "WEGE3", "VALE3", "KLBN4"]
SAMPLE_SYMBOLS_US = ["AAPL", "GOOG", "NVDA", "VTI", "O", "DLR"]
SAMPLE_QUERIES = ["btc", "bitcoin", "aapl", "petr", "knri", "itub", "kln", "eth"]


def _quote_endpoint() -> Endpoint:
    def build():
        n = random.randint(2, 6)
        symbols = random.sample(SAMPLE_SYMBOLS_BR + SAMPLE_SYMBOLS_US, k=min(n, 13))
        return ("/api/mobile/quotes", {"symbols": ",".join(symbols)})
    return Endpoint("quotes", "GET", "/api/mobile/quotes", build, weight=4)


def _search_endpoint() -> Endpoint:
    def build():
        return ("/api/stocks/search", {"q": random.choice(SAMPLE_QUERIES)})
    return Endpoint("search", "GET", "/api/stocks/search", build, weight=2)


def _history_endpoint() -> Endpoint:
    def build():
        sym = random.choice(SAMPLE_SYMBOLS_BR + SAMPLE_SYMBOLS_US)
        period = random.choice(["1mo", "3mo", "1y"])
        return (f"/api/stocks/{sym}/history", {"period": period})
    return Endpoint("history", "GET", "/api/stocks/{symbol}/history", build, weight=2)


def _dividends_endpoint() -> Endpoint:
    def build():
        symbols = random.sample(SAMPLE_SYMBOLS_BR + SAMPLE_SYMBOLS_US, k=4)
        return ("/api/mobile/dividends", {"symbols": ",".join(symbols)})
    return Endpoint("dividends", "GET", "/api/mobile/dividends", build, weight=1)


def _exchange_rate_endpoint() -> Endpoint:
    return Endpoint(
        "exchange-rate",
        "GET",
        "/api/mobile/exchange-rate",
        lambda: ("/api/mobile/exchange-rate", {"pair": "USD-BRL"}),
        weight=1,
    )


ENDPOINTS = [
    _quote_endpoint(),
    _search_endpoint(),
    _history_endpoint(),
    _dividends_endpoint(),
    _exchange_rate_endpoint(),
]


# ────────────────────────────────────────────────
# Stats
# ────────────────────────────────────────────────


@dataclass
class EndpointStats:
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    statuses: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def record(self, latency_ms: float, status: int):
        self.latencies_ms.append(latency_ms)
        self.statuses[status] += 1
        if status >= 500 or status == 0:
            self.errors += 1

    def percentile(self, p: float) -> float:
        if not self.latencies_ms:
            return 0.0
        ordered = sorted(self.latencies_ms)
        idx = max(0, min(len(ordered) - 1, int(round(p / 100 * (len(ordered) - 1)))))
        return ordered[idx]

    def report_line(self) -> str:
        n = len(self.latencies_ms)
        if n == 0:
            return f"  no samples"
        return (
            f"  n={n:5d}  p50={self.percentile(50):7.1f}ms  "
            f"p95={self.percentile(95):7.1f}ms  p99={self.percentile(99):7.1f}ms  "
            f"max={max(self.latencies_ms):7.1f}ms  errors={self.errors:3d}"
        )


# ────────────────────────────────────────────────
# Virtual user
# ────────────────────────────────────────────────


async def _hit(client: httpx.AsyncClient, ep: Endpoint, headers: dict, stats: dict[str, EndpointStats]):
    path, params = ep.build()
    start = time.monotonic()
    try:
        resp = await client.request(ep.method, path, params=params, headers=headers, timeout=30)
        status = resp.status_code
    except Exception:
        status = 0
    elapsed_ms = (time.monotonic() - start) * 1000
    stats[ep.name].record(elapsed_ms, status)


def _pick_endpoint() -> Endpoint:
    # Weighted random by `weight`
    pool = []
    for ep in ENDPOINTS:
        pool.extend([ep] * ep.weight)
    return random.choice(pool)


async def _user(client: httpx.AsyncClient, headers: dict, stats, deadline: float, think_min: float, think_max: float):
    while time.monotonic() < deadline:
        ep = _pick_endpoint()
        await _hit(client, ep, headers, stats)
        await asyncio.sleep(random.uniform(think_min, think_max))


# ────────────────────────────────────────────────
# Driver
# ────────────────────────────────────────────────


async def run(base: str, api_key: str, users: int, duration: float, think_min: float, think_max: float):
    headers = {"X-API-Key": api_key} if api_key else {}
    stats = {ep.name: EndpointStats() for ep in ENDPOINTS}

    limits = httpx.Limits(max_connections=users * 2, max_keepalive_connections=users)
    async with httpx.AsyncClient(base_url=base, limits=limits) as client:
        deadline = time.monotonic() + duration
        tasks = [
            asyncio.create_task(_user(client, headers, stats, deadline, think_min, think_max))
            for _ in range(users)
        ]
        await asyncio.gather(*tasks)

    return stats


def report(stats, users: int, duration: float):
    total_requests = sum(len(s.latencies_ms) for s in stats.values())
    total_errors = sum(s.errors for s in stats.values())
    rps = total_requests / duration if duration > 0 else 0

    print("\n========================================")
    print(f" Load test: {users} virtual users, {duration:.0f}s")
    print("========================================")
    print(f"  Total requests : {total_requests}")
    print(f"  Throughput     : {rps:.1f} req/s")
    print(f"  Errors (5xx/timeout) : {total_errors} ({100 * total_errors / max(total_requests, 1):.2f}%)")
    print()
    print("Per-endpoint latency:")
    for name, s in sorted(stats.items()):
        print(f"  {name:14s}{s.report_line()}")

    # Capacity projection: pick the worst p95 across all endpoints.
    # Assumption: a healthy production target is p95 < 500ms.
    # Linear scaling estimate — useful as a sanity floor, not a guarantee.
    target_p95 = 500.0
    worst_endpoint = max(stats.values(), key=lambda s: s.percentile(95) if s.latencies_ms else 0)
    worst_p95 = worst_endpoint.percentile(95)

    print()
    print("Capacity projection (back-of-envelope):")
    if worst_p95 == 0 or total_requests == 0:
        print("  Not enough data.")
        return
    if worst_p95 <= target_p95:
        ratio = target_p95 / worst_p95
        projected = int(users * ratio)
        print(
            f"  At {users} users the worst p95 is {worst_p95:.0f}ms (< {target_p95:.0f}ms).\n"
            f"  Linear projection: ~{projected} users before p95 crosses {target_p95:.0f}ms.\n"
            f"  Cross-check by running with --users {min(projected, users * 4)} to confirm it's not Fly machine-bound."
        )
    else:
        print(
            f"  At {users} users worst p95 ({worst_p95:.0f}ms) already exceeds {target_p95:.0f}ms.\n"
            f"  This is the soft ceiling — re-run with fewer users to find the knee."
        )


def main():
    p = argparse.ArgumentParser(description="Backend load test")
    p.add_argument("--base", default="https://grove-invest-api.fly.dev")
    p.add_argument("--api-key", default="", help="X-API-Key header (env MOBILE_API_KEY also works)")
    p.add_argument("--users", type=int, default=20)
    p.add_argument("--duration", type=float, default=30.0, help="Seconds to run")
    p.add_argument("--think-min", type=float, default=0.5)
    p.add_argument("--think-max", type=float, default=2.0)
    args = p.parse_args()

    api_key = args.api_key or __import__("os").environ.get("MOBILE_API_KEY", "")

    stats = asyncio.run(
        run(args.base, api_key, args.users, args.duration, args.think_min, args.think_max)
    )
    report(stats, args.users, args.duration)


if __name__ == "__main__":
    main()
