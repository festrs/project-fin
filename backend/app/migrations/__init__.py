"""
Simple migration system for SQLite.

Each migration is a function that:
- Checks if it has already been applied (idempotent)
- Applies schema/data changes via raw sqlite3
- Logs what it did

Migrations run on app startup, before SQLAlchemy create_all().
"""
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_columns(cur: sqlite3.Cursor, table: str) -> list[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def run_all(db_path: str) -> None:
    """Run all pending migrations."""
    if not Path(db_path).exists():
        logger.info("Database %s not found, skipping migrations (fresh DB)", db_path)
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Ensure migrations tracking table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            name TEXT PRIMARY KEY,
            applied_at TEXT DEFAULT (datetime('now'))
        )
    """)

    for migration in _MIGRATIONS:
        name = migration.__name__
        cur.execute("SELECT 1 FROM _migrations WHERE name = ?", (name,))
        if cur.fetchone():
            continue

        logger.info("Running migration: %s", name)
        try:
            migration(cur)
            cur.execute("INSERT INTO _migrations (name) VALUES (?)", (name,))
            conn.commit()
            logger.info("Migration %s applied successfully", name)
        except Exception:
            conn.rollback()
            logger.exception("Migration %s failed", name)
            raise

    conn.close()


# ---------------------------------------------------------------------------
# Migration functions — append new migrations at the end, never reorder/remove
# ---------------------------------------------------------------------------

def _001_decimal_money(cur: sqlite3.Cursor) -> None:
    """Convert float monetary columns to Decimal text and add currency to dividend_history."""
    from decimal import Decimal

    # Skip if dividend_history doesn't exist yet (fresh DB)
    if not _table_exists(cur, "dividend_history"):
        return

    # 1. Add currency column to dividend_history if missing
    columns = _get_columns(cur, "dividend_history")
    if "currency" not in columns:
        cur.execute("ALTER TABLE dividend_history ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'")

        # Infer currency from asset class country
        cur.execute("""
            UPDATE dividend_history SET currency = 'BRL'
            WHERE symbol IN (
                SELECT DISTINCT t.asset_symbol
                FROM transactions t
                JOIN asset_classes ac ON t.asset_class_id = ac.id
                WHERE ac.country = 'BR'
            )
        """)

    # 2. Convert float values in transactions to Decimal text
    if _table_exists(cur, "transactions"):
        cur.execute("SELECT id, unit_price, total_value, tax_amount FROM transactions")
        rows = cur.fetchall()
        for row_id, unit_price, total_value, tax_amount in rows:
            # Skip if already text (re-run safe)
            if isinstance(total_value, str):
                continue
            cur.execute(
                "UPDATE transactions SET unit_price=?, total_value=?, tax_amount=? WHERE id=?",
                (
                    str(Decimal(str(unit_price))) if unit_price is not None else None,
                    str(Decimal(str(total_value))) if total_value is not None else None,
                    str(Decimal(str(tax_amount))) if tax_amount is not None else None,
                    row_id,
                ),
            )
        logger.info("  Converted %d transactions to Decimal", len(rows))

    # 3. Convert float values in market_quotes
    if _table_exists(cur, "market_quotes"):
        cur.execute("SELECT symbol, current_price, market_cap FROM market_quotes")
        rows = cur.fetchall()
        for symbol, price, mcap in rows:
            if isinstance(price, str):
                continue
            cur.execute(
                "UPDATE market_quotes SET current_price=?, market_cap=? WHERE symbol=?",
                (str(Decimal(str(price))), str(Decimal(str(mcap))), symbol),
            )
        logger.info("  Converted %d market quotes to Decimal", len(rows))

    # 4. Convert float values in dividend_history
    cur.execute("SELECT id, value FROM dividend_history")
    rows = cur.fetchall()
    for row_id, value in rows:
        if isinstance(value, str):
            continue
        cur.execute(
            "UPDATE dividend_history SET value=? WHERE id=?",
            (str(Decimal(str(value))), row_id),
        )
    logger.info("  Converted %d dividend records to Decimal", len(rows))


def _002_emergency_reserve_flag(cur: sqlite3.Cursor) -> None:
    """Add is_emergency_reserve column to asset_classes table."""
    # Skip if asset_classes table doesn't exist (fresh DB)
    if not _table_exists(cur, "asset_classes"):
        return

    # Check if column already exists (idempotent)
    columns = _get_columns(cur, "asset_classes")
    if "is_emergency_reserve" not in columns:
        cur.execute("ALTER TABLE asset_classes ADD COLUMN is_emergency_reserve BOOLEAN NOT NULL DEFAULT 0")
        logger.info("  Added is_emergency_reserve column to asset_classes")


# Register migrations in order
_MIGRATIONS = [
    _001_decimal_money,
    _002_emergency_reserve_flag,
]
