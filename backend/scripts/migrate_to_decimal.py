"""
One-time migration: convert Float columns to Numeric (TEXT in SQLite)
and add currency column to dividend_history.

Usage: cd backend && python -m scripts.migrate_to_decimal
"""
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path


def migrate(db_path: str = "portfolio.db"):
    if not Path(db_path).exists():
        print(f"Database {db_path} not found, skipping migration (fresh DB will use new schema)")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if migration already applied (currency column exists on dividend_history)
    cur.execute("PRAGMA table_info(dividend_history)")
    columns = [row[1] for row in cur.fetchall()]
    if "currency" in columns:
        print("Migration already applied (dividend_history.currency exists)")
        conn.close()
        return

    print("Starting migration...")

    # 1. Convert float values in transactions
    cur.execute("SELECT id, unit_price, total_value, tax_amount FROM transactions")
    rows = cur.fetchall()
    for row_id, unit_price, total_value, tax_amount in rows:
        cur.execute(
            "UPDATE transactions SET unit_price=?, total_value=?, tax_amount=? WHERE id=?",
            (
                str(Decimal(str(unit_price))) if unit_price is not None else None,
                str(Decimal(str(total_value))) if total_value is not None else None,
                str(Decimal(str(tax_amount))) if tax_amount is not None else None,
                row_id,
            ),
        )
    print(f"  Migrated {len(rows)} transactions")

    # 2. Convert float values in market_quotes
    cur.execute("SELECT symbol, current_price, market_cap FROM market_quotes")
    rows = cur.fetchall()
    for symbol, price, mcap in rows:
        cur.execute(
            "UPDATE market_quotes SET current_price=?, market_cap=? WHERE symbol=?",
            (str(Decimal(str(price))), str(Decimal(str(mcap))), symbol),
        )
    print(f"  Migrated {len(rows)} market quotes")

    # 3. Add currency column to dividend_history and populate it
    cur.execute("ALTER TABLE dividend_history ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")

    # Infer currency from asset class country via transactions
    cur.execute("""
        UPDATE dividend_history SET currency = 'BRL'
        WHERE symbol IN (
            SELECT DISTINCT t.asset_symbol
            FROM transactions t
            JOIN asset_classes ac ON t.asset_class_id = ac.id
            WHERE ac.country = 'BR'
        )
    """)

    # Convert dividend float values
    cur.execute("SELECT id, value FROM dividend_history")
    rows = cur.fetchall()
    for row_id, value in rows:
        cur.execute(
            "UPDATE dividend_history SET value=? WHERE id=?",
            (str(Decimal(str(value))), row_id),
        )
    print(f"  Migrated {len(rows)} dividend history records")

    conn.commit()
    conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "portfolio.db"
    migrate(db_path)
