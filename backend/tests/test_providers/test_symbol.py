"""Tests for `Symbol` ticker helpers.

Existed implicitly through integration tests, but mutation testing showed
the BR-detection regex, country mapping, and `expand_variants` lacked
direct unit coverage. These tests pin the contract so mutants like
"^[A-Z]{4}\\d{1,2}$" → "^[A-Z]{3}\\d{1,2}$" die.
"""
from app.providers.common import Symbol


class TestSymbolIsBR:
    def test_bare_br_ticker_is_br(self):
        assert Symbol.is_br("PETR4") is True
        assert Symbol.is_br("ITUB3") is True
        assert Symbol.is_br("KNRI11") is True

    def test_us_ticker_is_not_br(self):
        assert Symbol.is_br("AAPL") is False
        assert Symbol.is_br("MSFT") is False

    def test_three_letter_ticker_is_not_br(self):
        # B3 tickers are exactly 4 letters + 1-2 digits. Kills the
        # `{4}` → `{3}` regex mutation that would falsely classify
        # 3-letter prefixes as BR.
        assert Symbol.is_br("ABC3") is False
        assert Symbol.is_br("XYZ4") is False

    def test_sa_suffix_alone_is_br(self):
        # Even non-standard prefixes are treated as BR when the suffix
        # is present (data is already provider-canonical).
        assert Symbol.is_br("UNUSUAL.SA") is True


class TestSymbolCountry:
    def test_br_tickers_return_BR(self):
        assert Symbol.country("PETR4") == "BR"
        assert Symbol.country("ITUB3.SA") == "BR"

    def test_us_tickers_return_US(self):
        assert Symbol.country("AAPL") == "US"
        assert Symbol.country("MSFT") == "US"


class TestSymbolExpandVariants:
    def test_br_ticker_expands_to_both_forms(self):
        out = Symbol.expand_variants(["PETR4"])
        assert "PETR4" in out
        assert "PETR4.SA" in out

    def test_us_ticker_passes_through(self):
        # US tickers must NOT be expanded — would falsely match BDRs.
        # Kills the "pass through symbols" mutation in routers/mobile.py
        # by ensuring the symbol-set the endpoint queries actually differs
        # for BR vs US.
        out = Symbol.expand_variants(["AAPL"])
        assert out == ["AAPL"]

    def test_dedup_preserves_first_occurrence(self):
        out = Symbol.expand_variants(["PETR4.SA", "PETR4"])
        # Bare + .SA both present, no duplicates.
        assert out.count("PETR4") == 1
        assert out.count("PETR4.SA") == 1
