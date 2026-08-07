from decimal import Decimal

import pytest

from domain.value_objects.money import Money


def test_money_normalizes_currency() -> None:
    money = Money(amount=Decimal("12.50"), currency=" eur ")

    assert money.currency == "EUR"


def test_money_rejects_invalid_currency_code() -> None:
    with pytest.raises(ValueError, match="three-letter"):
        Money(amount=Decimal("1.00"), currency="EU")


def test_money_rejects_negative_amount() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        Money(amount=Decimal("-0.01"), currency="EUR")


def test_money_adds_values_with_the_same_currency() -> None:
    total = Money(Decimal("2.40"), "EUR") + Money(Decimal("1.60"), "EUR")

    assert total == Money(Decimal("4.00"), "EUR")


def test_money_rejects_arithmetic_with_different_currencies() -> None:
    with pytest.raises(ValueError, match="different currencies"):
        Money(Decimal("2.00"), "EUR") + Money(Decimal("2.00"), "USD")


def test_money_multiplies_by_non_negative_integer() -> None:
    assert Money(Decimal("2.50"), "EUR") * 3 == Money(
        Decimal("7.50"),
        "EUR",
    )


def test_money_rejects_negative_factor() -> None:
    with pytest.raises(ValueError, match="factor must not be negative"):
        Money(Decimal("2.50"), "EUR") * -1


def test_money_rejects_comparison_with_unrelated_object() -> None:
    with pytest.raises(TypeError, match="unknown object comparison"):
        _ = Money(Decimal("2.50"), "EUR") == object()
