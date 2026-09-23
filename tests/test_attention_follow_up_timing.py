from __future__ import annotations

import pytest

from portia.attention import classify_follow_up_timing
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-09-20T23:59:59-04:00", "scheduled"),
        ("2026-09-21T00:00:00-04:00", "due"),
        ("2026-09-21T23:59:59-04:00", "due"),
        ("2026-09-22T00:00:00-04:00", "overdue"),
    ],
)
def test_date_only_uses_callers_calendar_date(
    as_of: str,
    expected: str,
) -> None:
    decision = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-21"},
        as_of=ExplicitOffsetTimestamp(as_of),
    )
    assert decision.classification == expected
    assert decision.precision == "date"


def test_date_only_does_not_convert_to_utc_calendar_date() -> None:
    decision = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-21"},
        as_of=ExplicitOffsetTimestamp("2026-09-21T00:30:00+14:00"),
    )
    assert decision.classification == "due"


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-09-21T17:59:59-04:00", "scheduled"),
        ("2026-09-21T18:00:00-04:00", "due"),
        ("2026-09-21T18:00:01-04:00", "overdue"),
        ("2026-09-21T22:00:00Z", "due"),
    ],
)
def test_exact_time_compares_real_offset_aware_instants(
    as_of: str,
    expected: str,
) -> None:
    decision = classify_follow_up_timing(
        {
            "kind": "exact_time",
            "at": "2026-09-21T18:00:00-04:00",
        },
        as_of=ExplicitOffsetTimestamp(as_of),
    )
    assert decision.classification == expected
    assert decision.precision == "timestamp"


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-09-20T12:00:00-04:00", "scheduled"),
        ("2026-09-21T12:00:00-04:00", "due"),
        ("2026-09-23T23:59:59-04:00", "due"),
        ("2026-09-24T00:00:00-04:00", "overdue"),
    ],
)
def test_date_window_is_inclusive(as_of: str, expected: str) -> None:
    decision = classify_follow_up_timing(
        {
            "kind": "window",
            "starts_on": "2026-09-21",
            "ends_on": "2026-09-23",
        },
        as_of=ExplicitOffsetTimestamp(as_of),
    )
    assert decision.classification == expected
    assert decision.precision == "date"


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        ("2026-09-21T17:59:59-04:00", "scheduled"),
        ("2026-09-21T18:00:00-04:00", "due"),
        ("2026-09-21T19:00:00-04:00", "due"),
        ("2026-09-21T20:00:00-04:00", "due"),
        ("2026-09-21T20:00:01-04:00", "overdue"),
    ],
)
def test_timestamp_window_is_inclusive(
    as_of: str,
    expected: str,
) -> None:
    decision = classify_follow_up_timing(
        {
            "kind": "window",
            "starts_at": "2026-09-21T18:00:00-04:00",
            "ends_at": "2026-09-21T20:00:00-04:00",
        },
        as_of=ExplicitOffsetTimestamp(as_of),
    )
    assert decision.classification == expected
    assert decision.precision == "timestamp"


def test_mixed_or_incomplete_window_fails_closed() -> None:
    with pytest.raises(PortiaLocalValidationError):
        classify_follow_up_timing(
            {
                "kind": "window",
                "starts_on": "2026-09-21",
                "ends_at": "2026-09-21T20:00:00-04:00",
            },
            as_of=ExplicitOffsetTimestamp(
                "2026-09-21T19:00:00-04:00"
            ),
        )


def test_reversed_window_fails_closed() -> None:
    with pytest.raises(PortiaLocalValidationError):
        classify_follow_up_timing(
            {
                "kind": "window",
                "starts_on": "2026-09-23",
                "ends_on": "2026-09-21",
            },
            as_of=ExplicitOffsetTimestamp(
                "2026-09-21T19:00:00-04:00"
            ),
        )
