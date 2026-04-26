#!/bin/bash
# Mutation testing for the FastAPI backend — batched.
#
# macOS-bash-3.2 compatible (no associative arrays).
# Strategy:
#   - Mutations listed as "file|||desc|||search|||replace" entries.
#   - Batch up to BATCH_SIZE mutations at once, ensuring each file appears
#     at most once per batch (so they're independent).
#   - Run pytest ONCE per batch.
#   - On failure, fall back to per-mutation tests for accurate attribution.

set -uo pipefail
cd "$(dirname "$0")/.."

PY="python3 scripts/mutate.py"
TEST_CMD="${TEST_CMD:-.venv312/bin/python -m pytest tests/ -q --no-header --tb=no}"
BATCH_SIZE="${BATCH_SIZE:-6}"

KILLED=0
SURVIVED=0
TOTAL=0
SURVIVORS=""

MUTATIONS=()
add() { MUTATIONS+=("$1|||$2|||$3|||$4"); }

# providers/common.py (Symbol class)
add "app/providers/common.py" "Symbol.is_br: drop .SA suffix branch"   'symbol.endswith(cls._SA_SUFFIX) or'  'False or'
add "app/providers/common.py" "Symbol pattern: 4 letters → 3 letters"  '_BR_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")' '_BR_PATTERN = re.compile(r"^[A-Z]{3}\d{1,2}$")'
add "app/providers/common.py" "Symbol.country flips BR/US"             'return "BR" if cls.is_br(symbol) else "US"' 'return "US" if cls.is_br(symbol) else "BR"'

# providers/brapi.py
add "app/providers/brapi.py" "Brapi: drop FEATURE_NOT_AVAILABLE branch" 'if payload.get("code") == "FEATURE_NOT_AVAILABLE":' 'if False:'
add "app/providers/brapi.py" "Brapi: skip records with both dates None" 'if ex_date is None and payment_date is None:' 'if ex_date is not None and payment_date is not None:'

# providers/yfinance.py
add "app/providers/yfinance.py" "yfinance: include past upcoming"      'if ex_date < date.today():'  'if ex_date > date.today():'
add "app/providers/yfinance.py" "yfinance: drop amount > 0 guard"      'if not ex_epoch or amount is None or amount <= 0:' 'if False:'

# services/dividend_scraper_scheduler.py
add "app/services/dividend_scraper_scheduler.py" "scheduler: ignore Brapi when available" 'if self._brapi is not None and not self._brapi_disabled:' 'if False:'
add "app/services/dividend_scraper_scheduler.py" "scheduler: BR ignores Brapi result"     'if records:' 'if not records:'

# services/market_data.py
add "app/services/market_data.py" "search_crypto: don't normalize symbol case" 'symbol = (c.get("symbol") or "").upper()' 'symbol = (c.get("symbol") or "")'
add "app/services/market_data.py" "fallback: don't append .SA for BR"          'yf_symbol = Symbol.with_sa(symbol) if country == "BR" else symbol' 'yf_symbol = symbol'

# routers/stocks.py
add "app/routers/stocks.py" "search: drop crypto branch"  'raw.extend(market_data.search_crypto(q))' 'pass'

# routers/mobile.py
add "app/routers/mobile.py" "mobile/quotes: ignore is_br_symbol"       'elif Symbol.is_br(symbol):' 'elif False:'
add "app/routers/mobile.py" "expand_variants: pass through symbols"    'query_symbols = Symbol.expand_variants(symbol_list)' 'query_symbols = symbol_list'

# ────────────────────────────────────────────────
parse_entry() {
    local entry="$1"
    ENTRY_FILE="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_DESC="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_SEARCH="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_REPLACE="$entry"
}

token_for() { echo "$1" | shasum | cut -c1-8; }

apply_one() {
    parse_entry "$1"
    if ! $PY check "$ENTRY_FILE" "$ENTRY_SEARCH" >/dev/null 2>&1; then return 1; fi
    $PY apply "$ENTRY_FILE" "$ENTRY_SEARCH" "$ENTRY_REPLACE" "$(token_for "$1")" >/dev/null 2>&1
}

revert_all_batch() { $PY revert-all >/dev/null 2>&1; }
run_tests_silent() { $TEST_CMD >/dev/null 2>&1; }

record_killed()   { KILLED=$((KILLED + 1));   printf "  KILLED   %s\n" "$1"; }
record_survived() { SURVIVED=$((SURVIVED + 1)); SURVIVORS="${SURVIVORS}    - $1"$'\n'; printf "  SURVIVED %s\n" "$1"; }

run_individually() {
    for entry in "$@"; do
        parse_entry "$entry"
        $PY check "$ENTRY_FILE" "$ENTRY_SEARCH" >/dev/null 2>&1 || continue
        TOTAL=$((TOTAL + 1))
        $PY apply "$ENTRY_FILE" "$ENTRY_SEARCH" "$ENTRY_REPLACE" >/dev/null
        if run_tests_silent; then
            record_survived "$ENTRY_FILE: $ENTRY_DESC"
        else
            record_killed "$ENTRY_FILE: $ENTRY_DESC"
        fi
        $PY revert "$ENTRY_FILE" >/dev/null
    done
}

run_batch() {
    local applied=()
    for entry in "$@"; do
        if apply_one "$entry"; then applied+=("$entry"); fi
    done
    [ ${#applied[@]} -eq 0 ] && return

    if run_tests_silent; then
        for entry in "${applied[@]}"; do
            parse_entry "$entry"
            TOTAL=$((TOTAL + 1))
            record_survived "$ENTRY_FILE: $ENTRY_DESC"
        done
        revert_all_batch
    else
        revert_all_batch
        run_individually "${applied[@]}"
    fi
}

echo "========================================"
echo " Mutation Testing - backend (batched, size=$BATCH_SIZE)"
echo "========================================"
echo ""

# Build batches: walk MUTATIONS, fill each batch with mutations from distinct
# files (so they're independent). Skipped entries get pushed into the next pass.
remaining=("${MUTATIONS[@]}")
while [ ${#remaining[@]} -gt 0 ]; do
    batch=()
    files_in_batch=""
    next_pass=()
    for entry in "${remaining[@]}"; do
        f="${entry%%|||*}"
        if [ ${#batch[@]} -lt $BATCH_SIZE ] && [[ "$files_in_batch" != *"|$f|"* ]]; then
            batch+=("$entry")
            files_in_batch="${files_in_batch}|$f|"
        else
            next_pass+=("$entry")
        fi
    done
    run_batch "${batch[@]}"
    remaining=("${next_pass[@]+"${next_pass[@]}"}")
done

revert_all_batch

echo ""
echo "========================================"
echo " Results"
echo "========================================"
echo "  Total:     $TOTAL"
echo "  Killed:    $KILLED"
echo "  Survived:  $SURVIVED"
[ $TOTAL -gt 0 ] && echo "  Score:     $((KILLED * 100 / TOTAL))%"
if [ -n "$SURVIVORS" ]; then
    echo ""
    echo "  SURVIVORS (need better tests):"
    printf "%s" "$SURVIVORS"
fi
