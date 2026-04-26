import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass
class DividendRecord:
    dividend_type: str
    value: Decimal
    record_date: date
    ex_date: date
    payment_date: date | None


class Symbol:
    """Ticker-symbol helpers (country detection, .SA normalization, variants).

    Grouped here so any code touching ticker strings has one place to look,
    and so callers can't drift toward inconsistent custom regexes.
    """

    # B3 tickers: 4 letters + 1-2 digits (PETR4, ITUB3, KNRI11, BTLG11, AAPL34 BDRs).
    _BR_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")
    _SA_SUFFIX = ".SA"

    @classmethod
    def is_br(cls, symbol: str) -> bool:
        """True for Brazilian B3 tickers, with or without the .SA suffix."""
        return symbol.endswith(cls._SA_SUFFIX) or bool(cls._BR_PATTERN.match(symbol.upper()))

    @classmethod
    def country(cls, symbol: str) -> str:
        """Returns 'BR' for Brazilian tickers, 'US' otherwise."""
        return "BR" if cls.is_br(symbol) else "US"

    @classmethod
    def strip_sa(cls, symbol: str) -> str:
        """Remove the .SA suffix used by yfinance/Brapi for Brazilian tickers."""
        return symbol.removesuffix(cls._SA_SUFFIX)

    @classmethod
    def with_sa(cls, symbol: str) -> str:
        """Append .SA if missing (used when calling yfinance with BR tickers)."""
        return symbol if symbol.endswith(cls._SA_SUFFIX) else f"{symbol}{cls._SA_SUFFIX}"

    @classmethod
    def expand_variants(cls, symbols: list[str]) -> list[str]:
        """For each BR ticker, include both the bare and .SA forms.

        BR tickers are stored inconsistently across data providers (some with .SA,
        some without). The mobile app sends the bare form, so this lets a single
        query match both.
        """
        expanded: list[str] = []
        seen: set[str] = set()
        for s in symbols:
            candidates = [s]
            if cls.is_br(s):
                candidates.append(cls.strip_sa(s))
                candidates.append(cls.with_sa(s))
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    expanded.append(c)
        return expanded


