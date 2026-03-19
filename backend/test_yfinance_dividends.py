"""
Test script to evaluate yfinance for fetching US stock dividends and splits (bonifications).
"""
import yfinance as yf
from datetime import datetime

def test_ticker(symbol: str):
    print(f"\n{'='*60}")
    print(f"  {symbol}")
    print(f"{'='*60}")

    ticker = yf.Ticker(symbol)

    # --- Dividends ---
    print("\n--- DIVIDENDS ---")
    dividends = ticker.dividends
    if dividends.empty:
        print("No dividend data found.")
    else:
        print(f"Total dividend records: {len(dividends)}")
        print(f"Date range: {dividends.index[0].date()} to {dividends.index[-1].date()}")
        print("\nLast 10 dividends:")
        for date, amount in dividends.tail(10).items():
            print(f"  {date.date()}  ${amount:.4f}")

    # --- Splits ---
    print("\n--- SPLITS (Bonifications) ---")
    splits = ticker.splits
    if splits.empty:
        print("No split data found.")
    else:
        print(f"Total split records: {len(splits)}")
        for date, ratio in splits.items():
            print(f"  {date.date()}  ratio: {ratio} (e.g. 2.0 = 2-for-1)")

    # --- Actions (combined dividends + splits) ---
    print("\n--- ACTIONS (combined view) ---")
    actions = ticker.actions
    if actions.empty:
        print("No actions data found.")
    else:
        print(f"Columns: {list(actions.columns)}")
        print(f"Last 5 actions:")
        print(actions.tail(5).to_string())

    # --- Calendar (upcoming events) ---
    print("\n--- CALENDAR (upcoming events) ---")
    try:
        calendar = ticker.calendar
        if calendar:
            for key, val in calendar.items():
                print(f"  {key}: {val}")
        else:
            print("No calendar data.")
    except Exception as e:
        print(f"Error fetching calendar: {e}")

    # --- Dividend metadata from info ---
    print("\n--- DIVIDEND INFO FROM .info ---")
    info = ticker.info
    dividend_keys = [
        'dividendRate', 'dividendYield', 'exDividendDate',
        'lastDividendValue', 'lastDividendDate',
        'fiveYearAvgDividendYield', 'payoutRatio', 'trailingAnnualDividendRate',
        'trailingAnnualDividendYield'
    ]
    for key in dividend_keys:
        val = info.get(key)
        if val is not None:
            if 'Date' in key and isinstance(val, (int, float)):
                val = f"{val} ({datetime.fromtimestamp(val).date()})"
            print(f"  {key}: {val}")


# Test with different types of US stocks
symbols = [
    "AAPL",   # Tech, regular dividends, has had splits
    "KO",     # Consumer staples, long dividend history
    "NVDA",   # Recent split (10-for-1 in 2024)
    "BRK-B",  # Berkshire - no dividends
]

for symbol in symbols:
    test_ticker(symbol)

print("\n\n" + "="*60)
print("SUMMARY")
print("="*60)
print("""
yfinance provides:
1. Historical dividends (ticker.dividends) - full history with dates and amounts
2. Historical splits (ticker.splits) - with ratios
3. Combined view (ticker.actions) - dividends + splits together
4. Upcoming events (ticker.calendar) - ex-dividend dates, earnings
5. Current dividend metadata (ticker.info) - yield, payout ratio, etc.
""")
