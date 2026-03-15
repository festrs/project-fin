#!/usr/bin/env python3
"""
Import portfolio transactions from portfolio_import.json into the backend.
Usage: python3 import_portfolio.py [--base-url http://localhost:8000]
"""

import json
import sys
import argparse
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"
USER_ID = "default-user-id"
HEADERS = {"Content-Type": "application/json", "x-user-id": USER_ID}


def api_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def api_put(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers=HEADERS, method="PUT")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def ensure_asset_classes(needed: list[str], class_target_weights: dict) -> dict[str, str]:
    """Returns {name: id} for all needed asset classes, creating missing ones."""
    existing = api_get("/api/asset-classes")
    class_map = {ac["name"]: ac["id"] for ac in existing}

    country_map = {
        "BR Stocks": "BR", "FIIs": "BR",
        "US Stocks": "US", "REITs": "US", "Crypto": "US", "Stablecoins": "US",
    }

    for name in needed:
        target = class_target_weights.get(name, 0.0)
        if name not in class_map:
            print(f"  Creating asset class: {name} (target: {target}%)")
            ac = api_post("/api/asset-classes", {
                "name": name,
                "target_weight": target,
                "country": country_map.get(name, "US"),
            })
            class_map[name] = ac["id"]
        else:
            ac_id = class_map[name]
            print(f"  Updating asset class: {name} -> target_weight={target}%")
            api_put(f"/api/asset-classes/{ac_id}", {"target_weight": target})

    return class_map


def set_symbol_weights(class_map: dict, transactions: list) -> None:
    """Creates per-symbol target weights for each asset class."""
    # Group by asset class
    by_class: dict[str, list] = {}
    for tx in transactions:
        by_class.setdefault(tx["asset_class"], []).append(tx)

    for class_name, txs in by_class.items():
        ac_id = class_map[class_name]
        # Get existing asset weights to avoid duplicates
        existing = api_get(f"/api/asset-classes/{ac_id}/assets")
        existing_symbols = {aw["symbol"] for aw in existing}

        for tx in txs:
            symbol = tx["symbol"]
            weight = tx.get("target_weight", 0.0)
            if symbol not in existing_symbols:
                api_post(f"/api/asset-classes/{ac_id}/assets", {
                    "symbol": symbol,
                    "target_weight": weight,
                })
                print(f"  ✓ {symbol}: target_weight={weight}%")
            else:
                print(f"  — {symbol}: already exists, skipping")


def main():
    global BASE_URL
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--weights-only", action="store_true",
                        help="Only set target weights, skip transaction import")
    args = parser.parse_args()
    BASE_URL = args.base_url.rstrip("/")

    with open("portfolio_import.json") as f:
        data = json.load(f)

    transactions = data["transactions"]
    needed_classes = data["asset_classes_needed"]
    class_target_weights = data.get("class_target_weights", {})

    currency_map = {
        "BR Stocks": "BRL", "FIIs": "BRL",
        "US Stocks": "USD", "REITs": "USD", "Crypto": "USD", "Stablecoins": "USD",
    }

    print("=== Ensuring asset classes + class-level target weights ===")
    class_map = ensure_asset_classes(needed_classes, class_target_weights)

    print("\n=== Setting per-symbol target weights ===")
    set_symbol_weights(class_map, transactions)

    if args.weights_only:
        print("\n=== Weights-only mode: skipping transaction import ===")
        return

    print(f"\n=== Importing {len(transactions)} transactions ===")
    ok, fail = 0, 0
    for tx in transactions:
        asset_class = tx["asset_class"]
        qty = tx["quantity"]
        price = tx["price"]
        try:
            api_post("/api/transactions", {
                "asset_class_id": class_map[asset_class],
                "asset_symbol": tx["symbol"],
                "type": tx["type"],
                "quantity": qty,
                "unit_price": price,
                "total_value": round(qty * price, 6),
                "currency": currency_map[asset_class],
                "date": tx["date"],
                "notes": "Imported from Investimentos.numbers",
            })
            print(f"  ✓ {tx['symbol']} ({asset_class}): {qty} @ {price}")
            ok += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  ✗ {tx['symbol']}: {e.code} {body}", file=sys.stderr)
            fail += 1

    print(f"\n=== Done: {ok} imported, {fail} failed ===")


if __name__ == "__main__":
    main()
