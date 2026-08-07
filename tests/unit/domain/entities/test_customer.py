import pytest

from domain.entities.customer import Customer


def make_customer(**changes: object) -> Customer:
    values = {
        "customer_id": "customer-1",
        "first_name": "Alex",
        "last_name": "Morgan",
        "email": "alex@example.com",
        "preferred_language": "en",
    }
    values.update(changes)
    return Customer(**values)  # type: ignore[arg-type]


def test_customer_exposes_full_name() -> None:
    assert make_customer().full_name == "Alex Morgan"


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("customer_id", "customer_id must not be empty"),
        ("first_name", "first_name must not be empty"),
        ("last_name", "last_name must not be empty"),
        ("email", "email must not be empty"),
    ],
)
def test_customer_rejects_blank_required_text(field: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        make_customer(**{field: " "})


def test_customer_requires_email_marker() -> None:
    with pytest.raises(ValueError, match="must contain an '@'"):
        make_customer(email="alex.example.com")


def test_customer_requires_two_letter_language_code() -> None:
    with pytest.raises(ValueError, match="two letter language code"):
        make_customer(preferred_language="eng")
