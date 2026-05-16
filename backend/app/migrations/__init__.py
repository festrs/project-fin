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


def _003_add_password_hash(cur: sqlite3.Cursor) -> None:
    """Add password_hash column to users table."""
    if not _table_exists(cur, "users"):
        return

    columns = _get_columns(cur, "users")
    if "password_hash" in columns:
        return

    cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")

    # Backfill existing users with hashed default password
    from app.services.auth import hash_password
    from app.config import settings
    default_hash = hash_password(settings.default_user_password)
    cur.execute("UPDATE users SET password_hash = ?", (default_hash,))


def _004_add_dividend_yield(cur: sqlite3.Cursor) -> None:
    """Add nullable dividend_yield column to market_quotes."""
    if not _table_exists(cur, "market_quotes"):
        return
    if "dividend_yield" in _get_columns(cur, "market_quotes"):
        return
    cur.execute("ALTER TABLE market_quotes ADD COLUMN dividend_yield TEXT")


_BR_PATTERN = __import__("re").compile(r"^[A-Z]{4}[0-9]{1,2}$")


def _is_bare_br(symbol: str) -> bool:
    """Match the iOS/backend BR ticker shape: 4 letters + 1–2 digits, no `.SA`."""
    return bool(_BR_PATTERN.match(symbol or ""))


def _005_canonicalize_br_symbols(cur: sqlite3.Cursor) -> None:
    """Append `.SA` to all Brazilian B3 symbols across the schema.

    The end-to-end rule is: BR (B3 stocks, FIIs, BDRs) symbols always carry
    `.SA`. iOS, the web app, providers, and storage all converge on this. This
    one-shot migration brings legacy bare-form rows up to canonical so a
    single canonical lookup hits everything.

    For tables with `symbol` as a primary/unique key (`market_quotes`,
    `tracked_symbols`, `fundamentals_score`) we rename when the canonical row
    is absent; when it already exists the bare duplicate is dropped. Per-row
    tables (`dividend_history`, `price_history`, `transactions`) just get
    their column rewritten in place — duplicates are intrinsically valid
    there because the row is identified by date, not symbol.

    Idempotent: re-running the migration is a no-op because no bare BR rows
    will be left after the first pass.
    """

    def rename_unique(table: str) -> None:
        if not _table_exists(cur, table):
            return
        cur.execute(f"SELECT symbol FROM {table}")
        bare = [r[0] for r in cur.fetchall() if _is_bare_br(r[0])]
        renamed = 0
        deleted = 0
        for sym in bare:
            canonical = sym + ".SA"
            cur.execute(f"SELECT 1 FROM {table} WHERE symbol = ?", (canonical,))
            if cur.fetchone():
                cur.execute(f"DELETE FROM {table} WHERE symbol = ?", (sym,))
                deleted += 1
            else:
                cur.execute(f"UPDATE {table} SET symbol = ? WHERE symbol = ?", (canonical, sym))
                renamed += 1
        logger.info("  %s: renamed %d, deleted %d bare-form duplicates", table, renamed, deleted)

    def rewrite_column(table: str, column: str, where: str = "") -> None:
        if not _table_exists(cur, table):
            return
        clause = f" AND ({where})" if where else ""
        cur.execute(f"SELECT {column} FROM {table} WHERE 1=1{clause}")
        rows = cur.fetchall()
        bare = {r[0] for r in rows if _is_bare_br(r[0])}
        renamed_total = 0
        dropped_total = 0
        for sym in bare:
            extra = f" AND ({where})" if where else ""
            # `UPDATE OR IGNORE` silently skips rows whose canonical twin
            # already satisfies a UNIQUE/PK constraint (real case in prod
            # `dividend_history` where (symbol, record_date, dividend_type,
            # value) is unique and bare/`.SA` rows for the same payment exist
            # side-by-side from prior cron runs).
            cur.execute(
                f"UPDATE OR IGNORE {table} SET {column} = ? WHERE {column} = ?{extra}",
                (sym + ".SA", sym),
            )
            renamed_total += cur.rowcount
            # Anything still bare after the OR IGNORE pass is a leftover
            # duplicate of an already-canonical row — safe to drop so future
            # canonical lookups don't double-count.
            cur.execute(
                f"DELETE FROM {table} WHERE {column} = ?{extra}",
                (sym,),
            )
            dropped_total += cur.rowcount
        logger.info(
            "  %s.%s: %d distinct symbol(s); renamed %d row(s), dropped %d duplicate row(s)",
            table, column, len(bare), renamed_total, dropped_total,
        )

    rename_unique("market_quotes")
    rename_unique("tracked_symbols")
    rename_unique("fundamentals_score")

    rewrite_column("dividend_history", "symbol")
    rewrite_column("price_history", "symbol")

    # Scope transactions to BR asset classes so US/crypto rows that happen to
    # match the 4-letter+digit shape (e.g. `BRK4` placeholders in test fixtures)
    # don't get polluted.
    rewrite_column(
        "transactions",
        "asset_symbol",
        where="asset_class_id IN (SELECT id FROM asset_classes WHERE country = 'BR')",
    )


# Register migrations in order
_MIGRATIONS = [
    _001_decimal_money,
    _002_emergency_reserve_flag,
    _003_add_password_hash,
    _004_add_dividend_yield,
    _005_canonicalize_br_symbols,
]
