"""Tests for Currency enum and Money value object."""

import pytest
from decimal import Decimal

from app.money import Currency, CurrencyMismatchError, Money


class TestCurrency:
    def test_usd_properties(self):
        assert Currency.USD.code == "USD"
        assert Currency.USD.symbol == "$"
        assert Currency.USD.symbol_position == "before"
        assert Currency.USD.thousands_sep == ","
        assert Currency.USD.decimal_sep == "."
        assert Currency.USD.symbol_spacing == ""

    def test_brl_properties(self):
        assert Currency.BRL.code == "BRL"
        assert Currency.BRL.symbol == "R$"
        assert Currency.BRL.symbol_position == "before"
        assert Currency.BRL.thousands_sep == "."
        assert Currency.BRL.decimal_sep == ","
        assert Currency.BRL.symbol_spacing == " "

    def test_eur_properties(self):
        assert Currency.EUR.code == "EUR"
        assert Currency.EUR.symbol == "€"
        assert Currency.EUR.symbol_position == "before"
        assert Currency.EUR.thousands_sep == "."
        assert Currency.EUR.decimal_sep == ","
        assert Currency.EUR.symbol_spacing == ""

    def test_from_code_valid_usd(self):
        assert Currency.from_code("USD") is Currency.USD

    def test_from_code_valid_brl(self):
        assert Currency.from_code("BRL") is Currency.BRL

    def test_from_code_valid_eur(self):
        assert Currency.from_code("EUR") is Currency.EUR

    def test_from_code_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown currency code: XYZ"):
            Currency.from_code("XYZ")

    def test_from_code_empty_raises(self):
        with pytest.raises(ValueError):
            Currency.from_code("")


class TestMoneyConstruction:
    def test_basic_construction(self):
        m = Money(Decimal("100.00"), Currency.USD)
        assert m.amount == Decimal("100.00")
        assert m.currency == Currency.USD

    def test_from_db(self):
        m = Money.from_db(Decimal("50.25"), "USD")
        assert m.amount == Decimal("50.25")
        assert m.currency == Currency.USD

    def test_from_db_brl(self):
        m = Money.from_db(Decimal("1234.56"), "BRL")
        assert m.amount == Decimal("1234.56")
        assert m.currency == Currency.BRL

    def test_from_db_invalid_currency_raises(self):
        with pytest.raises(ValueError):
            Money.from_db(Decimal("100"), "XYZ")

    def test_to_db(self):
        m = Money(Decimal("100.50"), Currency.USD)
        amount, code = m.to_db()
        assert amount == Decimal("100.50")
        assert code == "USD"

    def test_to_db_brl(self):
        m = Money(Decimal("1234.56"), Currency.BRL)
        amount, code = m.to_db()
        assert amount == Decimal("1234.56")
        assert code == "BRL"

    def test_zero_usd(self):
        m = Money.zero(Currency.USD)
        assert m.amount == Decimal("0")
        assert m.currency == Currency.USD

    def test_zero_brl(self):
        m = Money.zero(Currency.BRL)
        assert m.amount == Decimal("0")
        assert m.currency == Currency.BRL

    def test_frozen_immutable(self):
        m = Money(Decimal("100"), Currency.USD)
        with pytest.raises(Exception):
            m.amount = Decimal("200")  # type: ignore


class TestMoneyDisplay:
    def test_display_usd_simple(self):
        m = Money(Decimal("1234.56"), Currency.USD)
        assert m.display() == "$1,234.56"

    def test_display_usd_small(self):
        m = Money(Decimal("10.50"), Currency.USD)
        assert m.display() == "$10.50"

    def test_display_usd_large(self):
        m = Money(Decimal("1000000.00"), Currency.USD)
        assert m.display() == "$1,000,000.00"

    def test_display_brl(self):
        m = Money(Decimal("1234.56"), Currency.BRL)
        assert m.display() == "R$ 1.234,56"

    def test_display_brl_small(self):
        m = Money(Decimal("10.50"), Currency.BRL)
        assert m.display() == "R$ 10,50"

    def test_display_eur(self):
        m = Money(Decimal("1234.56"), Currency.EUR)
        assert m.display() == "€1.234,56"

    def test_display_eur_small(self):
        m = Money(Decimal("10.50"), Currency.EUR)
        assert m.display() == "€10,50"

    def test_display_negative_usd(self):
        m = Money(Decimal("-100.00"), Currency.USD)
        assert m.display() == "-$100.00"

    def test_display_negative_brl(self):
        m = Money(Decimal("-1234.56"), Currency.BRL)
        assert m.display() == "-R$ 1.234,56"

    def test_str_delegates_to_display(self):
        m = Money(Decimal("1234.56"), Currency.USD)
        assert str(m) == m.display()

    def test_repr(self):
        m = Money(Decimal("10.50"), Currency.USD)
        assert repr(m) == "Money(10.50, USD)"

    def test_repr_brl(self):
        m = Money(Decimal("1234.56"), Currency.BRL)
        assert repr(m) == "Money(1234.56, BRL)"


class TestMoneyArithmetic:
    def test_add_same_currency(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.USD)
        result = a + b
        assert result.amount == Decimal("150.00")
        assert result.currency == Currency.USD

    def test_add_different_currency_raises(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            _ = a + b

    def test_sub_same_currency(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("30.00"), Currency.USD)
        result = a - b
        assert result.amount == Decimal("70.00")
        assert result.currency == Currency.USD

    def test_sub_different_currency_raises(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.EUR)
        with pytest.raises(CurrencyMismatchError):
            _ = a - b

    def test_mul_int(self):
        m = Money(Decimal("10.00"), Currency.USD)
        result = m * 3
        assert result.amount == Decimal("30.00")
        assert result.currency == Currency.USD

    def test_mul_decimal(self):
        m = Money(Decimal("10.00"), Currency.USD)
        result = m * Decimal("1.5")
        assert result.amount == Decimal("15.000")
        assert result.currency == Currency.USD

    def test_rmul_int(self):
        m = Money(Decimal("10.00"), Currency.USD)
        result = 3 * m
        assert result.amount == Decimal("30.00")
        assert result.currency == Currency.USD

    def test_rmul_decimal(self):
        m = Money(Decimal("10.00"), Currency.USD)
        result = Decimal("2.5") * m
        assert result.amount == Decimal("25.000")
        assert result.currency == Currency.USD

    def test_neg(self):
        m = Money(Decimal("100.00"), Currency.USD)
        result = -m
        assert result.amount == Decimal("-100.00")
        assert result.currency == Currency.USD

    def test_neg_negative(self):
        m = Money(Decimal("-50.00"), Currency.USD)
        result = -m
        assert result.amount == Decimal("50.00")

    def test_per_unit(self):
        m = Money(Decimal("100.00"), Currency.USD)
        result = m.per_unit(4)
        assert result.amount == Decimal("25.00")
        assert result.currency == Currency.USD

    def test_per_unit_decimal(self):
        m = Money(Decimal("100.00"), Currency.USD)
        result = m.per_unit(Decimal("2.5"))
        assert result.amount == Decimal("40.00")
        assert result.currency == Currency.USD

    def test_ratio_same_currency(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.USD)
        result = a.ratio(b)
        assert result == Decimal("2.00")

    def test_ratio_different_currency_raises(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            a.ratio(b)

    def test_add_returns_frozen(self):
        a = Money(Decimal("10"), Currency.USD)
        b = Money(Decimal("20"), Currency.USD)
        result = a + b
        with pytest.raises(Exception):
            result.amount = Decimal("0")  # type: ignore


class TestMoneyComparison:
    def test_eq_same_amount_and_currency(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a == b

    def test_eq_different_amount(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("200.00"), Currency.USD)
        assert a != b

    def test_lt_same_currency(self):
        a = Money(Decimal("50.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a < b

    def test_lt_false(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.USD)
        assert not (a < b)

    def test_le_equal(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a <= b

    def test_le_less(self):
        a = Money(Decimal("50.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a <= b

    def test_gt(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("50.00"), Currency.USD)
        assert a > b

    def test_ge_equal(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert a >= b

    def test_compare_different_currency_raises(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            _ = a < b

    def test_eq_different_currency_raises(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.BRL)
        with pytest.raises(CurrencyMismatchError):
            _ = a == b

    def test_hash_equal_objects(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        assert hash(a) == hash(b)

    def test_hash_usable_in_set(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("100.00"), Currency.USD)
        c = Money(Decimal("200.00"), Currency.USD)
        s = {a, b, c}
        assert len(s) == 2

    def test_hash_different_amounts(self):
        a = Money(Decimal("100.00"), Currency.USD)
        b = Money(Decimal("200.00"), Currency.USD)
        assert hash(a) != hash(b)
