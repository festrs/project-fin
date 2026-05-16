#!/bin/bash
# Mutation testing for the FastAPI backend — batched, with per-mutation
# test selectors (mirrors scripts/mutation_test.sh in the Grove iOS repo).
#
# Strategy:
#   1. Mutations are 5-tuples: file|||desc|||search|||replace|||tests
#      `tests` is a comma-separated list of pytest node-ids or paths that
#      cover this mutation. Per-mutation selection keeps each test run
#      tiny (1-3s) instead of running the whole suite (~60s).
#   2. Tool batches up to BATCH_SIZE mutations across DIFFERENT FILES at
#      once and runs pytest ONCE against the union of their selectors.
#   3. On batch failure, reverts and re-runs each mutation individually
#      (linear bisect) for accurate attribution.
#
# Tunable env vars:
#   BATCH_SIZE        max mutations per batch (default 6).
#   MUTATION_LIMIT    cap mutations processed (sample/CI runs).
#   PYTEST_FLAGS      override pytest flags (default quiet, no cache).

set -uo pipefail
cd "$(dirname "$0")/.."

PY="python3 scripts/mutate.py"
PYTEST_BIN="${PYTEST_BIN:-.venv312/bin/python -m pytest}"
PYTEST_FLAGS="${PYTEST_FLAGS:--q --no-header --tb=no -p no:cacheprovider}"
BATCH_SIZE="${BATCH_SIZE:-6}"
MUTATION_LIMIT="${MUTATION_LIMIT:-}"

KILLED=0
SURVIVED=0
TOTAL=0
SURVIVORS=()

MUTATIONS=()

add() {
    # add file desc search replace tests
    # `tests` is comma-separated pytest selectors (file paths or `file::Class`
    # node-ids). The runner unions selectors across a batch so each batch
    # only runs the tests that could actually catch its mutants.
    MUTATIONS+=("$1|||$2|||$3|||$4|||$5")
}

# --- providers/common.py: Symbol helpers (BR detection, .SA, expand_variants)
C="app/providers/common.py"
C_TESTS="tests/test_providers/test_symbol.py,tests/test_routers/test_mobile_quotes_yield.py"
add "$C" "Symbol.is_br: drop .SA suffix branch"  'symbol.endswith(cls._SA_SUFFIX) or'  'False or'  "$C_TESTS"
add "$C" "Symbol pattern: 4 letters → 3 letters" '_BR_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")' '_BR_PATTERN = re.compile(r"^[A-Z]{3}\d{1,2}$")' "$C_TESTS"
add "$C" "Symbol.country flips BR/US"            'return "BR" if cls.is_br(symbol) else "US"' 'return "US" if cls.is_br(symbol) else "BR"' "$C_TESTS"

# --- providers/brapi.py: BR market data + dividends + splits
B="app/providers/brapi.py"
B_TESTS="tests/test_providers/test_brapi.py,tests/test_providers/test_brapi_splits.py"
add "$B" "Brapi: drop FEATURE_NOT_AVAILABLE branch" 'if payload.get("code") == "FEATURE_NOT_AVAILABLE":' 'if False:' "$B_TESTS"
add "$B" "Brapi: skip records with both dates None" 'if ex_date is None and payment_date is None:' 'if ex_date is not None and payment_date is not None:' "$B_TESTS"

# --- providers/yfinance.py: US dividends + upcoming announcement
Y="app/providers/yfinance.py"
Y_TESTS="tests/test_providers/test_yfinance.py"
add "$Y" "yfinance: include past upcoming"  'if ex_date < date.today():'  'if ex_date > date.today():'  "$Y_TESTS"
add "$Y" "yfinance: drop amount > 0 guard"  'if not ex_epoch or amount is None or amount <= 0:'  'if False:'  "$Y_TESTS"

# --- services/market_data.py: crypto normalization + BR fallback
MD="app/services/market_data.py"
MD_TESTS="tests/test_services/test_market_data.py,tests/test_routers/test_stocks.py"
add "$MD" "search_crypto: don't normalize symbol case" 'symbol = (c.get("symbol") or "").upper()' 'symbol = (c.get("symbol") or "")' "$MD_TESTS"

# --- services/dividend_scraper_scheduler.py: Brapi-first routing
DS="app/services/dividend_scraper_scheduler.py"
DS_TESTS="tests/test_services/test_dividend_scheduler_routing.py"
add "$DS" "scheduler: ignore Brapi when available" 'if self._brapi is not None and not self._brapi_disabled:' 'if False:' "$DS_TESTS"
add "$DS" "scheduler: BR ignores Brapi result"     'if records:' 'if not records:' "$DS_TESTS"

# --- routers/mobile.py: BR routing, variant expansion, redeem
MO="app/routers/mobile.py"
MO_QUOTES_TESTS="tests/test_routers/test_mobile_quotes_yield.py"
MO_REDEEM_TESTS="tests/test_routers/test_mobile_redeem.py"
add "$MO" "mobile/quotes: ignore is_br_symbol"    'elif Symbol.is_br(symbol):' 'elif False:' "$MO_QUOTES_TESTS"
add "$MO" "expand_variants: pass through symbols" 'query_symbols = Symbol.expand_variants(symbol_list)' 'query_symbols = symbol_list' "$MO_QUOTES_TESTS"
add "$MO" "redeem: accept all codes when none configured" 'if not valid or not _code_matches(submitted, valid):' 'if False:' "$MO_REDEEM_TESTS"
add "$MO" "redeem: drop length guard"                     'if not submitted or len(submitted) > MAX_REDEEM_CODE_LENGTH:' 'if False:' "$MO_REDEEM_TESTS"
add "$MO" "redeem: hmac compare flipped"                  'if hmac.compare_digest(submitted, code):' 'if not hmac.compare_digest(submitted, code):' "$MO_REDEEM_TESTS"

# ────────────────────────────────────────────────
#  Batched runner
# ────────────────────────────────────────────────

parse_entry() {
    # Splits "file|||desc|||search|||replace|||tests" into globals.
    local entry="$1"
    ENTRY_FILE="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_DESC="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_SEARCH="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_REPLACE="${entry%%|||*}"; entry="${entry#*|||}"
    ENTRY_TESTS="$entry"
}

# Convert a comma-separated list of selectors into a deduped, space-separated
# string ready to splice into the pytest command line.
build_test_args() {
    local csv="$1"
    if [ -z "$csv" ]; then
        echo ""
        return
    fi
    echo "$csv" | tr ',' '\n' | awk 'NF' | sort -u | tr '\n' ' '
}

apply_one() {
    local entry="$1"
    parse_entry "$entry"
    if ! $PY check "$ENTRY_FILE" "$ENTRY_SEARCH" >/dev/null 2>&1; then
        return 1
    fi
    $PY apply "$ENTRY_FILE" "$ENTRY_SEARCH" "$ENTRY_REPLACE" "$(echo "$entry" | shasum | cut -c1-8)" >/dev/null 2>&1
    return 0
}

revert_all_batch() { $PY revert-all >/dev/null 2>&1; }

run_tests_silent() {
    # Targeted pytest run. Args are pytest selectors.
    local tests_csv="$1"
    local targets
    targets=$(build_test_args "$tests_csv")
    if [ -n "$targets" ]; then
        $PYTEST_BIN $PYTEST_FLAGS $targets >/dev/null 2>&1
    else
        # Belt-and-suspenders fallback for entries that forgot a selector.
        $PYTEST_BIN $PYTEST_FLAGS tests/ >/dev/null 2>&1
    fi
}

record_killed()   { KILLED=$((KILLED + 1));   printf "  KILLED   %s\n" "$1"; }
record_survived() { SURVIVED=$((SURVIVED + 1)); SURVIVORS+=("$1"); printf "  SURVIVED %s\n" "$1"; }

run_individually() {
    local -a batch=("$@")
    for entry in "${batch[@]}"; do
        parse_entry "$entry"
        $PY check "$ENTRY_FILE" "$ENTRY_SEARCH" >/dev/null 2>&1 || continue
        TOTAL=$((TOTAL + 1))
        $PY apply "$ENTRY_FILE" "$ENTRY_SEARCH" "$ENTRY_REPLACE" >/dev/null
        if run_tests_silent "$ENTRY_TESTS"; then
            record_survived "$ENTRY_FILE: $ENTRY_DESC"
        else
            record_killed "$ENTRY_FILE: $ENTRY_DESC"
        fi
        $PY revert "$ENTRY_FILE" >/dev/null
    done
}

run_batch() {
    local -a batch=("$@")
    local applied=()
    local batch_tests_csv=""
    for entry in "${batch[@]}"; do
        if apply_one "$entry"; then
            applied+=("$entry")
            parse_entry "$entry"
            if [ -n "$ENTRY_TESTS" ]; then
                if [ -n "$batch_tests_csv" ]; then
                    batch_tests_csv="$batch_tests_csv,$ENTRY_TESTS"
                else
                    batch_tests_csv="$ENTRY_TESTS"
                fi
            fi
        fi
    done

    [ ${#applied[@]} -eq 0 ] && return

    local t0=$(date +%s)
    if run_tests_silent "$batch_tests_csv"; then
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
    echo "  (batch took $(( $(date +%s) - t0 ))s, ${#applied[@]} mutation(s))"
}

echo "========================================"
echo " Mutation Testing - backend (batched, size=$BATCH_SIZE)"
echo "========================================"
echo ""

if [ -n "$MUTATION_LIMIT" ]; then
    echo "→ MUTATION_LIMIT=$MUTATION_LIMIT — sampling first $MUTATION_LIMIT mutations"
    MUTATIONS=("${MUTATIONS[@]:0:$MUTATION_LIMIT}")
fi

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
if [ $TOTAL -gt 0 ]; then
    SCORE=$((KILLED * 100 / TOTAL))
    echo "  Score:     ${SCORE}%"
fi

if [ ${#SURVIVORS[@]} -gt 0 ]; then
    echo ""
    echo "  SURVIVORS (need better tests):"
    for s in "${SURVIVORS[@]}"; do
        echo "    - $s"
    done
fi
