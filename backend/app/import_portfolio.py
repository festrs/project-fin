"""Import portfolio data into Project Fin via API calls."""

import time

import httpx

from app.database import SessionLocal
from app.models.user import User

BASE_URL = "http://localhost:8000"
DATE = "2026-03-11"


def get_default_user_id() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "default@projectfin.com").first()
        if not user:
            raise RuntimeError("Default user not found. Run seed first.")
        return user.id
    finally:
        db.close()


def api(method: str, path: str, user_id: str, **kwargs) -> httpx.Response:
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        resp = client.request(method, path, headers={"X-User-Id": user_id}, **kwargs)
        resp.raise_for_status()
        return resp


def delete_existing_asset_classes(user_id: str):
    print("Deleting existing asset classes...")
    resp = api("GET", "/api/asset-classes", user_id)
    classes = resp.json()
    for ac in classes:
        print(f"  Deleting {ac['name']} ({ac['id']})")
        api("DELETE", f"/api/asset-classes/{ac['id']}", user_id)
    print(f"  Deleted {len(classes)} asset classes.")


def create_asset_class(user_id: str, name: str, target_weight: float) -> str:
    resp = api("POST", "/api/asset-classes", user_id, json={
        "name": name,
        "target_weight": target_weight,
    })
    ac = resp.json()
    print(f"  Created asset class: {name} (weight={target_weight}%) -> {ac['id']}")
    return ac["id"]


def add_asset(user_id: str, ac_id: str, symbol: str, target_weight: float):
    api("POST", f"/api/asset-classes/{ac_id}/assets", user_id, json={
        "symbol": symbol,
        "target_weight": target_weight,
    })


def create_transaction(user_id: str, ac_id: str, symbol: str, qty: float,
                       unit_price: float, currency: str):
    total_value = round(qty * unit_price, 2)
    api("POST", "/api/transactions", user_id, json={
        "asset_class_id": ac_id,
        "asset_symbol": symbol,
        "type": "buy",
        "quantity": qty,
        "unit_price": unit_price,
        "total_value": total_value,
        "currency": currency,
        "tax_amount": 0,
        "date": DATE,
    })


def import_assets(user_id: str, ac_id: str, assets: list[dict], currency: str):
    for a in assets:
        symbol = a["symbol"]
        qty = a["qty"]
        weight = a["weight"]
        price = a["price"]
        add_asset(user_id, ac_id, symbol, weight)
        create_transaction(user_id, ac_id, symbol, qty, price, currency)
        print(f"    {symbol}: qty={qty}, weight={weight}%, price={price} {currency}")


def main():
    user_id = get_default_user_id()
    print(f"Using user ID: {user_id}")

    # Step 1: Clean slate
    delete_existing_asset_classes(user_id)

    # Step 2: Create asset classes and import assets
    print("\nCreating asset classes and importing assets...")

    # --- Ações BR ---
    ac_id = create_asset_class(user_id, "Ações BR", 25.0)
    import_assets(user_id, ac_id, [
        {"symbol": "AGRO3.SA",   "qty": 400,  "weight": 0.0,  "price": 21.82},
        {"symbol": "AZZA3.SA",   "qty": 552,  "weight": 5.0,  "price": 27.52},
        {"symbol": "B3SA3.SA",   "qty": 2333, "weight": 5.0,  "price": 18.11},
        {"symbol": "EGIE3.SA",   "qty": 1000, "weight": 5.0,  "price": 32.6},
        {"symbol": "FLRY3.SA",   "qty": 2601, "weight": 5.0,  "price": 16.27},
        {"symbol": "HYPE3.SA",   "qty": 360,  "weight": 0.0,  "price": 22.02},
        {"symbol": "ITUB3.SA",   "qty": 1688, "weight": 5.0,  "price": 41.68},
        {"symbol": "KLBN11.SA",  "qty": 396,  "weight": 0.0,  "price": 19.72},
        {"symbol": "LREN3.SA",   "qty": 1683, "weight": 5.0,  "price": 15.22},
        {"symbol": "PSSA3.SA",   "qty": 860,  "weight": 5.0,  "price": 50.0},
        {"symbol": "RADL3.SA",   "qty": 1956, "weight": 5.0,  "price": 23.74},
        {"symbol": "TAEE11.SA",  "qty": 799,  "weight": 5.0,  "price": 42.76},
        {"symbol": "WEGE3.SA",   "qty": 1400, "weight": 5.0,  "price": 47.19},
        {"symbol": "ODPV3.SA",   "qty": 2692, "weight": 5.0,  "price": 13.87},
        {"symbol": "XPBR31.SA",  "qty": 12,   "weight": 0.0,  "price": 103.31},
    ], "BRL")

    # --- Stocks US ---
    ac_id = create_asset_class(user_id, "Stocks US", 30.0)
    import_assets(user_id, ac_id, [
        {"symbol": "AAPL",  "qty": 62,  "weight": 5.0, "price": 260.83},
        {"symbol": "BLK",   "qty": 7,   "weight": 5.0, "price": 967.36},
        {"symbol": "CVX",   "qty": 11,  "weight": 3.0, "price": 186.29},
        {"symbol": "DIS",   "qty": 48,  "weight": 3.0, "price": 101.32},
        {"symbol": "FAST",  "qty": 116, "weight": 5.0, "price": 46.3},
        {"symbol": "GOOG",  "qty": 40,  "weight": 5.0, "price": 306.93},
        {"symbol": "MA",    "qty": 9,   "weight": 5.0, "price": 514.72},
        {"symbol": "NOW",   "qty": 5,   "weight": 0.0, "price": 116.61},
        {"symbol": "NVDA",  "qty": 350, "weight": 5.0, "price": 184.77},
        {"symbol": "TSLA",  "qty": 12,  "weight": 0.0, "price": 399.24},
        {"symbol": "TXN",   "qty": 28,  "weight": 5.0, "price": 197.46},
        {"symbol": "WST",   "qty": 12,  "weight": 5.0, "price": 233.83},
    ], "USD")

    # --- REITs ---
    ac_id = create_asset_class(user_id, "REITs", 10.0)
    import_assets(user_id, ac_id, [
        {"symbol": "AMT",   "qty": 30,  "weight": 5.0, "price": 186.12},
        {"symbol": "DLR",   "qty": 44,  "weight": 5.0, "price": 180.86},
        {"symbol": "NLOP",  "qty": 4,   "weight": 0.0, "price": 14.15},
        {"symbol": "O",     "qty": 97,  "weight": 5.0, "price": 64.88},
        {"symbol": "PSA",   "qty": 20,  "weight": 5.0, "price": 305.99},
        {"symbol": "STAG",  "qty": 120, "weight": 5.0, "price": 38.37},
        {"symbol": "WPC",   "qty": 90,  "weight": 5.0, "price": 72.26},
        {"symbol": "REXR",  "qty": 122, "weight": 5.0, "price": 35.72},
    ], "USD")

    # --- FIIs ---
    ac_id = create_asset_class(user_id, "FIIs", 10.0)
    import_assets(user_id, ac_id, [
        {"symbol": "BCRI11.SA",  "qty": 300,  "weight": 5.0, "price": 62.94},
        {"symbol": "KNRI11.SA",  "qty": 550,  "weight": 5.0, "price": 165.68},
        {"symbol": "VRTA11.SA",  "qty": 27,   "weight": 5.0, "price": 77.25},
        {"symbol": "BTLG11.SA",  "qty": 256,  "weight": 5.0, "price": 103.27},
        {"symbol": "HGLG11.SA",  "qty": 200,  "weight": 5.0, "price": 158.0},
        {"symbol": "RBRF11.SA",  "qty": 4410, "weight": 0.0, "price": 6.65},
        {"symbol": "MXRF11.SA",  "qty": 2402, "weight": 5.0, "price": 9.7},
    ], "BRL")

    # --- Cryptos ---
    ac_id = create_asset_class(user_id, "Cryptos", 15.0)
    import_assets(user_id, ac_id, [
        {"symbol": "BTC",  "qty": 0.35963512, "weight": 95.0, "price": 69578.35},
        {"symbol": "USDC", "qty": 7492,       "weight": 5.0,  "price": 1.0},
        {"symbol": "DAI",  "qty": 361.7517,   "weight": 0.0,  "price": 0.16},
        {"symbol": "USDT", "qty": 2863,       "weight": 5.0,  "price": 1.0},
    ], "USD")

    # --- Renda Fixa ---
    create_asset_class(user_id, "Renda Fixa", 6.0)

    # --- Imóveis ---
    create_asset_class(user_id, "Imóveis", 2.0)

    print("\nImport complete!")


if __name__ == "__main__":
    main()
