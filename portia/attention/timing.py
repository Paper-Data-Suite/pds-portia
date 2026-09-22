"""Explicit, deterministic timing semantics for Portia attention queries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Literal, TypeAlias

from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError

TimingClassification: TypeAlias = Literal["scheduled", "due", "overdue"]
TimingPrecision: TypeAlias = Literal["date", "timestamp"]
TimingPoint: TypeAlias = date | datetime


@dataclass(frozen=True, slots=True)
class TimingDecision:
    """One precision-preserving schedule classification."""

    classification: TimingClassification
    precision: TimingPrecision
    start: TimingPoint
    end: TimingPoint

    def __post_init__(self) -> None:
        if self.classification not in {"scheduled", "due", "overdue"}:
            raise PortiaLocalValidationError(
                f"unsupported timing classification: {self.classification!r}"
            )

        if self.precision == "date":
            if (
                not isinstance(self.start, date)
                or isinstance(self.start, datetime)
                or not isinstance(self.end, date)
                or isinstance(self.end, datetime)
            ):
                raise PortiaLocalValidationError(
                    "date-precision timing requires date-only boundaries"
                )
            start_on = self.start
            end_on = self.end
            if end_on < start_on:
                raise PortiaLocalValidationError(
                    "timing end cannot precede timing start"
                )
            return

        if self.precision == "timestamp":
            if not isinstance(self.start, datetime) or not isinstance(
                self.end, datetime
            ):
                raise PortiaLocalValidationError(
                    "timestamp-precision timing requires datetime boundaries"
                )
            if (
                self.start.tzinfo is None
                or self.start.utcoffset() is None
                or self.end.tzinfo is None
                or self.end.utcoffset() is None
            ):
                raise PortiaLocalValidationError(
                    "timestamp-precision timing requires explicit offsets"
                )
            if self.end < self.start:
                raise PortiaLocalValidationError(
                    "timing end cannot precede timing start"
                )
            return

        raise PortiaLocalValidationError(
            f"unsupported timing precision: {self.precision!r}"
        )

    def deterministic_key(self) -> tuple[str, str, str]:
        """Return an ordering key that carries no urgency/risk meaning."""
        if self.precision == "date":
            assert isinstance(self.start, date)
            assert not isinstance(self.start, datetime)
            assert isinstance(self.end, date)
            assert not isinstance(self.end, datetime)
            return ("date", self.start.isoformat(), self.end.isoformat())

        assert isinstance(self.start, datetime)
        assert isinstance(self.end, datetime)
        return (
            "timestamp",
            self.start.astimezone(timezone.utc).isoformat(),
            self.end.astimezone(timezone.utc).isoformat(),
        )


def _parse_date(value: object, *, field_name: str) -> date:
    if not isinstance(value, str):
        raise PortiaLocalValidationError(f"{field_name} must be a date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PortiaLocalValidationError(
            f"{field_name} must be a valid ISO date"
        ) from exc


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise PortiaLocalValidationError(
            f"{field_name} must be an explicit-offset timestamp string"
        )
    try:
        return ExplicitOffsetTimestamp(value).datetime
    except PortiaLocalValidationError as exc:
        raise PortiaLocalValidationError(
            f"{field_name} must be a valid explicit-offset timestamp"
        ) from exc


def _classify_date(
    *,
    as_of: ExplicitOffsetTimestamp,
    start: date,
    end: date,
) -> TimingDecision:
    current = as_of.datetime.date()
    if current < start:
        classification: TimingClassification = "scheduled"
    elif current > end:
        classification = "overdue"
    else:
        classification = "due"
    return TimingDecision(
        classification=classification,
        precision="date",
        start=start,
        end=end,
    )


def _classify_timestamp(
    *,
    as_of: ExplicitOffsetTimestamp,
    start: datetime,
    end: datetime,
) -> TimingDecision:
    current = as_of.datetime
    if current < start:
        classification: TimingClassification = "scheduled"
    elif current > end:
        classification = "overdue"
    else:
        classification = "due"
    return TimingDecision(
        classification=classification,
        precision="timestamp",
        start=start,
        end=end,
    )


def classify_follow_up_timing(
    planned_timing: Mapping[str, object],
    *,
    as_of: ExplicitOffsetTimestamp,
) -> TimingDecision:
    """Classify one accepted Follow-Up planned timing at one explicit instant.

    Date-only values use the calendar date represented by ``as_of``'s own
    explicit offset. Timestamp values compare real offset-aware instants.
    Planned windows are inclusive at both boundaries.
    """
    if not isinstance(planned_timing, Mapping):
        raise PortiaLocalValidationError("planned_timing must be a mapping")
    if not isinstance(as_of, ExplicitOffsetTimestamp):
        raise PortiaLocalValidationError(
            "as_of must be an ExplicitOffsetTimestamp"
        )

    kind = planned_timing.get("kind")
    if kind == "date_only":
        if set(planned_timing) != {"kind", "date"}:
            raise PortiaLocalValidationError(
                "date_only planned_timing must contain only kind and date"
            )
        planned = _parse_date(
            planned_timing.get("date"),
            field_name="Follow-Up planned date",
        )
        return _classify_date(as_of=as_of, start=planned, end=planned)

    if kind == "exact_time":
        if set(planned_timing) != {"kind", "at"}:
            raise PortiaLocalValidationError(
                "exact_time planned_timing must contain only kind and at"
            )
        planned_at = _parse_timestamp(
            planned_timing.get("at"),
            field_name="Follow-Up planned exact time",
        )
        return _classify_timestamp(
            as_of=as_of,
            start=planned_at,
            end=planned_at,
        )

    if kind != "window":
        raise PortiaLocalValidationError(
            f"unsupported Follow-Up planned_timing kind: {kind!r}"
        )

    keys = set(planned_timing)
    if keys == {"kind", "starts_on", "ends_on"}:
        starts_on = _parse_date(
            planned_timing.get("starts_on"),
            field_name="Follow-Up window starts_on",
        )
        ends_on = _parse_date(
            planned_timing.get("ends_on"),
            field_name="Follow-Up window ends_on",
        )
        return _classify_date(
            as_of=as_of,
            start=starts_on,
            end=ends_on,
        )

    if keys == {"kind", "starts_at", "ends_at"}:
        starts_at = _parse_timestamp(
            planned_timing.get("starts_at"),
            field_name="Follow-Up window starts_at",
        )
        ends_at = _parse_timestamp(
            planned_timing.get("ends_at"),
            field_name="Follow-Up window ends_at",
        )
        return _classify_timestamp(
            as_of=as_of,
            start=starts_at,
            end=ends_at,
        )

    raise PortiaLocalValidationError(
        "Follow-Up window must use one complete date or timestamp boundary pair"
    )
