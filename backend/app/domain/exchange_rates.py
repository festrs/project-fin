"""Exchange-rate protocol and implementations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.domain.money import Currency


class ExchangeRates(Protocol):
    def rate(self, from_: Currency, to: Currency) -> Decimal: ...


@dataclass
class StaticRates:
    """Simple rates backed by a single BRL/USD pair."""

    brl_per_usd: Decimal

    def rate(self, from_: Currency, to: Currency) -> Decimal:
        if from_ == to:
            return Decimal("1")
        if from_ == Currency.USD and to == Currency.BRL:
            return self.brl_per_usd
        if from_ == Currency.BRL and to == Currency.USD:
            return Decimal("1") / self.brl_per_usd
        raise ValueError(f"Unsupported pair: {from_.value} → {to.value}")


class IdentityRates:
    """Returns 1 for same-currency; raises for cross-currency. Tests only."""

    def rate(self, from_: Currency, to: Currency) -> Decimal:
        if from_ == to:
            return Decimal("1")
        raise ValueError(f"IdentityRates does not support cross-currency: {from_.value} → {to.value}")
