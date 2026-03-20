"""Currency enum and Money value object."""

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Union


class CurrencyMismatchError(ValueError):
    pass


class Currency(enum.Enum):
    USD = ("USD", "$", "before", ",", ".", "")    # $1,234.56
    BRL = ("BRL", "R$", "before", ".", ",", " ")   # R$ 1.234,56
    EUR = ("EUR", "€", "before", ".", ",", "")      # €1.234,56

    def __init__(
        self,
        code: str,
        symbol: str,
        symbol_position: str,
        thousands_sep: str,
        decimal_sep: str,
        symbol_spacing: str,
    ):
        self.code = code
        self.symbol = symbol
        self.symbol_position = symbol_position
        self.thousands_sep = thousands_sep
        self.decimal_sep = decimal_sep
        self.symbol_spacing = symbol_spacing

    @classmethod
    def from_code(cls, code: str) -> "Currency":
        for member in cls:
            if member.code == code:
                return member
        raise ValueError(f"Unknown currency code: {code}")


def _format_number(amount: Decimal, thousands_sep: str, decimal_sep: str) -> str:
    """Format a non-negative Decimal with the given separators, 2 decimal places."""
    # Format with 2 decimal places
    formatted = f"{amount:.2f}"
    integer_part, decimal_part = formatted.split(".")

    # Add thousands separators
    if thousands_sep:
        # Build integer part with thousands grouping
        chars = list(integer_part)
        result = []
        for i, ch in enumerate(reversed(chars)):
            if i > 0 and i % 3 == 0:
                result.append(thousands_sep)
            result.append(ch)
        integer_part = "".join(reversed(result))

    return f"{integer_part}{decimal_sep}{decimal_part}"


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: Currency

    @classmethod
    def from_db(cls, amount: Decimal, currency_code: str) -> "Money":
        currency = Currency.from_code(currency_code)
        return cls(amount, currency)

    @classmethod
    def zero(cls, currency: Currency) -> "Money":
        return cls(Decimal("0"), currency)

    def to_db(self) -> tuple[Decimal, str]:
        return self.amount, self.currency.code

    def display(self) -> str:
        negative = self.amount < 0
        abs_amount = abs(self.amount)

        number_str = _format_number(
            abs_amount,
            self.currency.thousands_sep,
            self.currency.decimal_sep,
        )

        symbol = self.currency.symbol
        spacing = self.currency.symbol_spacing

        if self.currency.symbol_position == "before":
            formatted = f"{symbol}{spacing}{number_str}"
        else:
            formatted = f"{number_str}{spacing}{symbol}"

        if negative:
            formatted = f"-{formatted}"

        return formatted

    def __str__(self) -> str:
        return self.display()

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency.code})"

    def _check_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(
                f"Currency mismatch: {self.currency.code} vs {other.currency.code}"
            )

    def __add__(self, other: "Money") -> "Money":
        self._check_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: Union[Decimal, int]) -> "Money":
        return Money(self.amount * Decimal(scalar), self.currency)

    def __rmul__(self, scalar: Union[Decimal, int]) -> "Money":
        return Money(Decimal(scalar) * self.amount, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def per_unit(self, quantity: Union[Decimal, int]) -> "Money":
        return Money(self.amount / Decimal(quantity), self.currency)

    def ratio(self, other: "Money") -> Decimal:
        self._check_same_currency(other)
        return self.amount / other.amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount == other.amount

    def __lt__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        self._check_same_currency(other)
        return self.amount >= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))
