from datetime import date

import pytest

from domain.value_objects.stay_period import StayPeriod


def test_stay_period_reports_nights_and_text() -> None:
    period = StayPeriod(date(2030, 5, 1), date(2030, 5, 4))

    assert period.number_of_nights == 3
    assert str(period) == "from 2030-05-01 to 2030-05-04"


def test_stay_period_requires_checkout_after_checkin() -> None:
    with pytest.raises(ValueError, match="check_out must be after check_in"):
        StayPeriod(date(2030, 5, 1), date(2030, 5, 1))


def test_overlaps_detects_intersecting_periods() -> None:
    period = StayPeriod(date(2030, 5, 1), date(2030, 5, 4))

    assert period.overlaps(StayPeriod(date(2030, 5, 3), date(2030, 5, 6)))


def test_overlaps_treats_adjacent_periods_as_non_overlapping() -> None:
    period = StayPeriod(date(2030, 5, 1), date(2030, 5, 4))

    assert not period.overlaps(StayPeriod(date(2030, 5, 4), date(2030, 5, 6)))
