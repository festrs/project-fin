"""Tests for domain Money value object and Currency enum."""

import pytest
from decimal import Decimal

from app.domain.money import Currency, Money
from app.domain.exchange_rates import StaticRates, IdentityRates
from app.schemas.money import MoneyResponse


class TestCurrency:
    def test_brl_value(self):
        assert Currency.BRL == "BRL"
        assert Currency.BRL.value == "BRL"

    def test_usd_value(self):
        assert Currency.USD == "USD"
        assert Currency.USD.value == "USD"

    def test_str_enum_membership(self):
        assert Currency("BRL") is Currency.BRL
        assert Currency("USD") is Currency.USD

    def test_unknown_currency_raises(self):
        with pytest.raises(ValueError):
            Currency("EUR")


class TestMoneyConstruction:
    def test_basic(self):
        m = Money(Decimal("100.00"), Currency.USD)
        assert m.amount == Decimal("100.00")
        assert m.currency == Currency.USD

    def test_non_decimal_raises(self):
        with pytest.raises(TypeError):
            Money(100.0, Currency.USD)  # type: ignore

    def test_frozen(self):
        m = Money(Decimal("10"), Currency.BRL)
        with pytest.raises(Exception):
            m.amount = Decimal("20")  # type: ignore

    def test_zero(self):
        m = Money.zero(Currency.BRL)
        assert m.amount == Decimal("0")
        assert m.currency == Currency.BRL

    def test_zero_usd(self):
        m = Money.zero(Currency.USD)
        assert m.currency == Currency.USD


class TestMoneyArithmetic:
    def test_add_same_currency(self):
        a = Money(Decimal("100"), Currency.USD)
        b = Money(Decimal("50"), Currency.USD)
        assert (a + b).amount == Decimal("150")

    def test_add_mismatch_raises(self):
        a = Money(Decimal("100"), Currency.USD)
        b = Money(Decimal("50"), Currency.BRL)
        with pytest.raises(ValueError):
            _ = a + b

    def test_sub_same_currency(self):
        a = Money(Decimal("100"), Currency.USD)
        b = Money(Decimal("30"), Currency.USD)
        assert (a - b).amount == Decimal("70")

    def test_sub_mismatch_raises(self):
        a = Money(Decimal("100"), Currency.USD)
        b = Money(Decimal("30"), Currency.BRL)
        with pytest.raises(ValueError):
            _ = a - b

    def test_neg(self):
        m = Money(Decimal("50"), Currency.BRL)
        assert (-m).amount == Decimal("-50")

    def test_neg_negative(self):
        m = Money(Decimal("-50"), Currency.USD)
        assert (-m).amount == Decimal("50")

    def test_mul_decimal(self):
        m = Money(Decimal("10"), Currency.USD)
        result = m * Decimal("3")
        assert result.amount == Decimal("30")
        assert result.currency == Currency.USD

    def test_mul_int(self):
        m = Money(Decimal("10"), Currency.USD)
        result = m * 4
        assert result.amount == Decimal("40")

    def test_rmul_decimal(self):
        m = Money(Decimal("10"), Currency.USD)
        result = Decimal("2") * m
        assert result.amount == Decimal("20")

    def test_rmul_int(self):
        m = Money(Decimal("10"), Currency.USD)
        result = 5 * m
        assert result.amount == Decimal("50")

    def test_truediv_decimal(self):
        m = Money(Decimal("100"), Currency.BRL)
        result = m / Decimal("4")
        assert result.amount == Decimal("25")

    def test_truediv_int(self):
        m = Money(Decimal("100"), Currency.BRL)
        result = m / 5
        assert result.amount == Decimal("20")

    def test_no_money_times_money(self):
        a = Money(Decimal("10"), Currency.USD)
        with pytest.raises(TypeError):
            _ = a * a  # type: ignore


class TestMoneyComparison:
    def test_eq_same(self):
        assert Money(Decimal("10"), Currency.USD) == Money(Decimal("10"), Currency.USD)

    def test_eq_different_amount(self):
        assert Money(Decimal("10"), Currency.USD) != Money(Decimal("20"), Currency.USD)

    def test_eq_mismatch_raises(self):
        a = Money(Decimal("10"), Currency.USD)
        b = Money(Decimal("10"), Currency.BRL)
        with pytest.raises(ValueError):
            _ = a == b

    def test_lt(self):
        assert Money(Decimal("5"), Currency.USD) < Money(Decimal("10"), Currency.USD)

    def test_gt(self):
        assert Money(Decimal("10"), Currency.BRL) > Money(Decimal("5"), Currency.BRL)

    def test_compare_mismatch_raises(self):
        a = Money(Decimal("10"), Currency.USD)
        b = Money(Decimal("10"), Currency.BRL)
        with pytest.raises(ValueError):
            _ = a < b

    def test_hash_equal(self):
        a = Money(Decimal("10"), Currency.USD)
        b = Money(Decimal("10"), Currency.USD)
        assert hash(a) == hash(b)

    def test_hash_set(self):
        a = Money(Decimal("10"), Currency.USD)
        b = Money(Decimal("10"), Currency.USD)
        c = Money(Decimal("20"), Currency.USD)
        assert len({a, b, c}) == 2


class TestMoneyDTO:
    def test_to_dto(self):
        m = Money(Decimal("1234.56"), Currency.BRL)
        dto = m.to_dto()
        assert isinstance(dto, MoneyResponse)
        assert dto.amount == "1234.56"
        assert dto.currency == "BRL"

    def test_from_dto(self):
        dto = MoneyResponse(amount="500.00", currency="USD")
        m = Money.from_dto(dto)
        assert m.amount == Decimal("500.00")
        assert m.currency == Currency.USD

    def test_round_trip(self):
        original = Money(Decimal("999.99"), Currency.USD)
        assert Money.from_dto(original.to_dto()) == original

    def test_json_shape(self):
        m = Money(Decimal("42.00"), Currency.USD)
        dto = m.to_dto()
        assert dto.model_dump() == {"amount": "42.00", "currency": "USD"}


class TestMoneyConversion:
    def test_same_currency_fast_path(self):
        m = Money(Decimal("100"), Currency.BRL)
        rates = StaticRates(brl_per_usd=Decimal("5"))
        result = m.converted(Currency.BRL, rates)
        assert result is m  # same object, no computation

    def test_usd_to_brl(self):
        m = Money(Decimal("100"), Currency.USD)
        rates = StaticRates(brl_per_usd=Decimal("5"))
        result = m.converted(Currency.BRL, rates)
        assert result.amount == Decimal("500")
        assert result.currency == Currency.BRL

    def test_brl_to_usd(self):
        m = Money(Decimal("500"), Currency.BRL)
        rates = StaticRates(brl_per_usd=Decimal("5"))
        result = m.converted(Currency.USD, rates)
        assert result.amount == Decimal("100")
        assert result.currency == Currency.USD


class TestExchangeRates:
    def test_static_same_currency(self):
        rates = StaticRates(brl_per_usd=Decimal("5.15"))
        assert rates.rate(Currency.BRL, Currency.BRL) == Decimal("1")
        assert rates.rate(Currency.USD, Currency.USD) == Decimal("1")

    def test_static_usd_brl(self):
        rates = StaticRates(brl_per_usd=Decimal("5.15"))
        assert rates.rate(Currency.USD, Currency.BRL) == Decimal("5.15")

    def test_static_brl_usd(self):
        rates = StaticRates(brl_per_usd=Decimal("5"))
        result = rates.rate(Currency.BRL, Currency.USD)
        assert result == Decimal("1") / Decimal("5")

    def test_identity_same_currency(self):
        rates = IdentityRates()
        assert rates.rate(Currency.USD, Currency.USD) == Decimal("1")

    def test_identity_cross_raises(self):
        rates = IdentityRates()
        with pytest.raises(ValueError):
            rates.rate(Currency.USD, Currency.BRL)
