"""Currency enum and Money value object for the domain layer.

BRL + USD only. EUR is a one-line addition when needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Union

from app.schemas.money import MoneyResponse


class Currency(str, Enum):
    BRL = "BRL"
    USD = "USD"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError(f"amount must be Decimal, got {type(self.amount).__name__}")

    # ── Arithmetic ────────────────────────────────────────────────────────

    def __add__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __mul__(self, scalar: Union[Decimal, int]) -> Money:
        return Money(self.amount * Decimal(scalar), self.currency)

    def __rmul__(self, scalar: Union[Decimal, int]) -> Money:
        return Money(Decimal(scalar) * self.amount, self.currency)

    def __truediv__(self, scalar: Union[Decimal, int]) -> Money:
        return Money(self.amount / Decimal(scalar), self.currency)

    # ── Comparison ────────────────────────────────────────────────────────

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._require_same_currency(other)
        return self.amount == other.amount

    def __lt__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._require_same_currency(other)
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    # ── Conversion ────────────────────────────────────────────────────────

    def converted(self, to: Currency, rates: "ExchangeRates") -> Money:
        if self.currency == to:
            return self
        return Money(self.amount * rates.rate(self.currency, to), to)

    # ── DTOs ──────────────────────────────────────────────────────────────

    def to_dto(self) -> MoneyResponse:
        return MoneyResponse(amount=str(self.amount), currency=self.currency.value)

    @classmethod
    def from_dto(cls, dto: MoneyResponse) -> Money:
        return cls(Decimal(dto.amount), Currency(dto.currency))

    @classmethod
    def zero(cls, currency: Currency) -> Money:
        return cls(Decimal("0"), currency)

    # ── Internal ──────────────────────────────────────────────────────────

    def _require_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: {self.currency.value} vs {other.currency.value}"
            )
