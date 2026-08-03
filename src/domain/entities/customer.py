"""Customer domain entity."""

from dataclasses import dataclass


@dataclass(slots=True)
class Customer:
    """A known customer who can be associated with one or more bookings."""

    customer_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    preferred_language: str = "en"

    def __post_init__(self) -> None:
        if not self.customer_id.strip():
            raise ValueError("customer_id must not be empty")

        if not self.first_name.strip():
            raise ValueError("first_name must not be empty")

        if not self.last_name.strip():
            raise ValueError("last_name must not be empty")

        if not self.email.strip():
            raise ValueError("email must not be empty")

        if "@" not in self.email:
            raise ValueError("email must contain an '@' character")

        if len(self.preferred_language) != 2:
                    raise ValueError("a two letter language code must be provided")

    @property
    def full_name(self) -> str:
        """Return the customer's complete name."""

        return f"{self.first_name} {self.last_name}"