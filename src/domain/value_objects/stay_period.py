"""Stay-period value object."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class StayPeriod:
    """A valid hotel stay from check-in up to, but excluding, check-out."""

    check_in: date
    check_out: date

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")

    @property
    def number_of_nights(self) -> int:
        """Return the number of booked nights."""

        return (self.check_out - self.check_in).days

    def overlaps(self, other: "StayPeriod") -> bool:
        """Return whether two stay periods overlap."""

        return (
            self.check_in < other.check_out
            and other.check_in < self.check_out
        )