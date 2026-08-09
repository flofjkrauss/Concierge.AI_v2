"""Supported hotel room categories."""

from enum import StrEnum


class RoomCategory(StrEnum):
    """A room category supported by the hotel."""

    SINGLE="single"
    DOUBLE="double"
    DELUXE="deluxe"
    FAMILY="family"