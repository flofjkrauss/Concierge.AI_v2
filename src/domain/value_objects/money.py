"""Money value object."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    """A monetary amount in a specific currency."""

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        normalized_currency = self.currency.strip().upper()

        if len(normalized_currency) != 3:
            raise ValueError(
                "currency must be a three-letter currency code"
            )

        if self.amount < Decimal(0):
            raise ValueError("amount must not be negative")

        object.__setattr__(self, "currency", normalized_currency)

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)

        return Money(
            amount=self.amount + other.amount,
            currency=self.currency,
        )

    def __mul__(self, factor: int) -> "Money":
        if factor < 0:
            raise ValueError("factor must not be negative")

        return Money(
            amount=self.amount * factor,
            currency=self.currency,
        )

    def __eq__(self, other: "Money") -> bool:
        self._require_same_currency(other)
        if other.currency != self.currency:
            raise ValueError("money values with different currencies cannot be compared")

        return self.amount == other.amount

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError(
                "money values with different currencies cannot be combined"
            )