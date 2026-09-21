"""Closed semantic chronology adapters for Issue #48 student views.

Chronology is intentionally separate from privacy authorization.  It annotates
only sources that already survived the Slice 3 projection boundary.  Audit
timestamps are never used as silent occurrence-time fallbacks.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

from portia.models import PortiaRecord
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaCorruptionError, PortiaRepository, StoredRecord
from portia.views.models import TimelineSourceRef
from portia.views.policy import STUDENT_VIEW_PROJECTION_INVENTORY
from portia.views.projection import (
    ProjectedStudentViewItem,
    StudentPrivacyProjectionResult,
)

ChronologyPrecision = Literal[
    "exact_timestamp",
    "approximate_timestamp",
    "timestamp_range",
    "date_only",
    "date_range",
    "unknown",
]
ChronologyAdapterKind = Literal[
    "unknown",
    "event_occurrence",
    "evidence_time",
    "started_interval",
    "planned_schedule",
    "evaluated_at",
    "follow_up",
    "outcome_timeframe",
    "reentry",
    "repair",
]
SortDirection = Literal["ascending", "descending"]

_PRECISIONS: Final[frozenset[str]] = frozenset(
    {
        "exact_timestamp",
        "approximate_timestamp",
        "timestamp_range",
        "date_only",
        "date_range",
        "unknown",
    }
)
_ADAPTERS: Final[frozenset[str]] = frozenset(
    {
        "unknown",
        "event_occurrence",
        "evidence_time",
        "started_interval",
        "planned_schedule",
        "evaluated_at",
        "follow_up",
        "outcome_timeframe",
        "reentry",
        "repair",
    }
)
_PRECISION_RANK: Final[dict[str, int]] = {
    "date_only": 0,
    "date_range": 1,
    "approximate_timestamp": 2,
    "exact_timestamp": 3,
    "timestamp_range": 4,
    "unknown": 5,
}


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PortiaLocalValidationError(
            f"{field_name} must be an ISO calendar date"
        ) from exc


def _parse_timestamp(value: str, field_name: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PortiaLocalValidationError(
            f"{field_name} must be an explicit-offset timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PortiaLocalValidationError(
            f"{field_name} must carry an explicit UTC offset"
        )
    return parsed


@dataclass(frozen=True, slots=True)
class SemanticTimelineMarker:
    """One precision-preserving semantic time marker for an authorized source."""

    basis: str
    precision: ChronologyPrecision
    start: str | None = None
    end: str | None = None
    approximation: str | None = None
    planned: bool = False

    def __post_init__(self) -> None:
        validate_external_id(self.basis, "timeline_marker_basis")
        if self.precision not in _PRECISIONS:
            raise PortiaLocalValidationError(
                f"unsupported chronology precision: {self.precision!r}"
            )
        if self.precision == "unknown":
            if (
                self.start is not None
                or self.end is not None
                or self.approximation is not None
            ):
                raise PortiaLocalValidationError(
                    "unknown semantic time cannot carry temporal bounds"
                )
            return
        if not isinstance(self.start, str):
            raise PortiaLocalValidationError(
                "known semantic time requires a start value"
            )
        if self.precision in {"exact_timestamp", "approximate_timestamp"}:
            _parse_timestamp(self.start, "semantic time start")
            if self.end is not None:
                raise PortiaLocalValidationError(
                    "point semantic time cannot carry an end value"
                )
        elif self.precision == "timestamp_range":
            _parse_timestamp(self.start, "semantic time start")
            if not isinstance(self.end, str):
                raise PortiaLocalValidationError(
                    "timestamp range requires an end value"
                )
            if _parse_timestamp(self.end, "semantic time end") < _parse_timestamp(
                self.start, "semantic time start"
            ):
                raise PortiaLocalValidationError(
                    "semantic timestamp range cannot end before it starts"
                )
        elif self.precision == "date_only":
            _parse_date(self.start, "semantic date")
            if self.end is not None:
                raise PortiaLocalValidationError(
                    "date-only semantic time cannot carry an end value"
                )
        elif self.precision == "date_range":
            start = _parse_date(self.start, "semantic start date")
            if not isinstance(self.end, str):
                raise PortiaLocalValidationError(
                    "date range requires an end date"
                )
            if _parse_date(self.end, "semantic end date") < start:
                raise PortiaLocalValidationError(
                    "semantic date range cannot end before it starts"
                )

        if self.precision == "approximate_timestamp":
            if self.approximation not in {"about", "before", "after"}:
                raise PortiaLocalValidationError(
                    "approximate semantic timestamp requires its accepted "
                    "approximation qualifier"
                )
        elif (
            self.approximation is not None
            and not (
                self.precision == "timestamp_range"
                and self.approximation == "within_range"
            )
        ):
            raise PortiaLocalValidationError(
                "approximation qualifier is incompatible with chronology precision"
            )

    @property
    def is_known(self) -> bool:
        return self.precision != "unknown"

    def date_bounds(self) -> tuple[date, date] | None:
        """Return calendar-date bounds without inventing time-of-day precision."""
        if self.start is None:
            return None
        if self.precision in {
            "exact_timestamp",
            "approximate_timestamp",
            "timestamp_range",
        }:
            start = _parse_timestamp(self.start, "semantic time start").date()
            if self.end is None:
                return start, start
            return (
                start,
                _parse_timestamp(self.end, "semantic time end").date(),
            )
        start_date = _parse_date(self.start, "semantic date")
        if self.end is None:
            return start_date, start_date
        return start_date, _parse_date(self.end, "semantic end date")


@dataclass(frozen=True, slots=True)
class StudentViewChronologyRule:
    """Closed chronology adapter registration for one exact view contract."""

    record_kind: str
    contract_version: str
    adapter: ChronologyAdapterKind
    basis: str

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "chronology_record_kind")
        validate_external_id(self.contract_version, "chronology_contract_version")
        validate_external_id(self.basis, "chronology_basis")
        if self.adapter not in _ADAPTERS:
            raise PortiaLocalValidationError(
                f"unsupported chronology adapter: {self.adapter!r}"
            )
        if (
            self.record_kind,
            self.contract_version,
        ) not in STUDENT_VIEW_PROJECTION_INVENTORY:
            raise PortiaLocalValidationError(
                "chronology rule must name an exact projectable contract"
            )

    @property
    def exact_key(self) -> tuple[str, str]:
        return (self.record_kind, self.contract_version)


def _rules(
    record_kind: str,
    versions: tuple[str, ...],
    adapter: ChronologyAdapterKind,
    basis: str,
) -> tuple[StudentViewChronologyRule, ...]:
    return tuple(
        StudentViewChronologyRule(record_kind, version, adapter, basis)
        for version in versions
    )


STUDENT_VIEW_CHRONOLOGY_RULES: Final[tuple[StudentViewChronologyRule, ...]] = (
    *_rules("event", ("2",), "event_occurrence", "event_occurrence"),
    *_rules("support_process", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules(
        "event_participant",
        ("3",),
        "unknown",
        "semantic_time_not_recorded",
    ),
    *_rules(
        "event_participant_role",
        ("3",),
        "unknown",
        "semantic_time_not_recorded",
    ),
    *_rules("work_relationship", ("2",), "unknown", "semantic_time_not_recorded"),
    *_rules("account", ("1", "2"), "evidence_time", "account_provided_time"),
    *_rules(
        "observation",
        ("1", "2"),
        "evidence_time",
        "observation_time",
    ),
    *_rules("review", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("classification", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("hypothesis", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("determination", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("response", ("1",), "started_interval", "response_act_time"),
    *_rules(
        "communication",
        ("1",),
        "started_interval",
        "communication_act_time",
    ),
    *_rules(
        "support_process_participant",
        ("1",),
        "unknown",
        "semantic_time_not_recorded",
    ),
    *_rules("support_need", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("support_goal", ("1",), "unknown", "semantic_time_not_recorded"),
    *_rules("support", ("1",), "planned_schedule", "support_planned_schedule"),
    *_rules(
        "intervention",
        ("1",),
        "planned_schedule",
        "intervention_planned_schedule",
    ),
    *_rules(
        "implementation",
        ("1",),
        "started_interval",
        "implementation_occurrence",
    ),
    *_rules("fidelity", ("1",), "evaluated_at", "fidelity_evaluated_at"),
    *_rules("follow_up", ("1",), "follow_up", "follow_up_timing"),
    *_rules("outcome", ("1",), "outcome_timeframe", "outcome_timeframe"),
    *_rules("reentry", ("1",), "reentry", "reentry_timing"),
    *_rules("repair", ("1",), "repair", "repair_completion"),
)

STUDENT_VIEW_CHRONOLOGY_INVENTORY: Final[
    Mapping[tuple[str, str], StudentViewChronologyRule]
] = MappingProxyType(
    {rule.exact_key: rule for rule in STUDENT_VIEW_CHRONOLOGY_RULES}
)

if len(STUDENT_VIEW_CHRONOLOGY_INVENTORY) != len(
    STUDENT_VIEW_CHRONOLOGY_RULES
):
    raise RuntimeError("student-view chronology inventory contains duplicate keys")

if frozenset(STUDENT_VIEW_CHRONOLOGY_INVENTORY) != frozenset(
    STUDENT_VIEW_PROJECTION_INVENTORY
):
    missing = sorted(
        frozenset(STUDENT_VIEW_PROJECTION_INVENTORY)
        - frozenset(STUDENT_VIEW_CHRONOLOGY_INVENTORY)
    )
    extra = sorted(
        frozenset(STUDENT_VIEW_CHRONOLOGY_INVENTORY)
        - frozenset(STUDENT_VIEW_PROJECTION_INVENTORY)
    )
    raise RuntimeError(
        "student-view chronology inventory drift: "
        f"missing={missing}, extra={extra}"
    )


def chronology_rule(
    record_kind: str,
    contract_version: str,
) -> StudentViewChronologyRule:
    """Return one exact closed chronology rule or fail closed."""
    rule = STUDENT_VIEW_CHRONOLOGY_INVENTORY.get(
        (record_kind, contract_version)
    )
    if rule is None:
        raise PortiaLocalValidationError(
            "unsupported student-view chronology contract: "
            f"{record_kind}@{contract_version}"
        )
    return rule


@dataclass(frozen=True, slots=True)
class ChronologizedStudentViewItem:
    """One privacy-safe projected item plus its semantic chronology marker."""

    item: ProjectedStudentViewItem
    marker: SemanticTimelineMarker

    @property
    def source_ref(self) -> TimelineSourceRef:
        return self.item.source_ref


@dataclass(frozen=True, slots=True)
class StudentChronologyResult:
    """Deterministically ordered chronology over one privacy projection result."""

    projection: StudentPrivacyProjectionResult
    items: tuple[ChronologizedStudentViewItem, ...]

    def __post_init__(self) -> None:
        projected_refs = frozenset(item.source_ref for item in self.projection.items)
        refs = tuple(item.source_ref for item in self.items)
        if len(set(refs)) != len(refs):
            raise PortiaLocalValidationError(
                "student chronology cannot repeat an exact source"
            )
        if frozenset(refs) != projected_refs:
            raise PortiaLocalValidationError(
                "student chronology must preserve every assembled projected source"
            )


def _source_key(source: TimelineSourceRef) -> tuple[str, ...]:
    if isinstance(source, ExactPortiaWorkRef):
        return (
            source.class_id,
            source.work_kind,
            source.work_id,
            source.contract_version,
            "",
            "",
            "",
        )
    return (
        source.work_ref.class_id,
        source.work_ref.work_kind,
        source.work_ref.work_id,
        source.work_ref.contract_version,
        source.record_ref.record_kind,
        source.record_ref.record_id,
        source.record_ref.contract_version,
    )


def _known_sort_key(
    value: ChronologizedStudentViewItem,
) -> tuple[str, int, str, tuple[str, ...]]:
    marker = value.marker
    bounds = marker.date_bounds()
    if bounds is None:
        raise PortiaLocalValidationError("known chronology item lacks date bounds")
    start_day = bounds[0].isoformat()
    absolute = ""
    if marker.start is not None and marker.precision in {
        "exact_timestamp",
        "approximate_timestamp",
        "timestamp_range",
    }:
        absolute = (
            _parse_timestamp(marker.start, "semantic sort timestamp")
            .astimezone(timezone.utc)
            .isoformat()
        )
    return (
        start_day,
        _PRECISION_RANK[marker.precision],
        absolute,
        _source_key(value.source_ref),
    )


def order_chronology_items(
    items: tuple[ChronologizedStudentViewItem, ...],
    *,
    direction: SortDirection = "ascending",
) -> tuple[ChronologizedStudentViewItem, ...]:
    """Order known semantic time deterministically; keep unknown time last."""
    if direction not in {"ascending", "descending"}:
        raise PortiaLocalValidationError(
            f"unsupported chronology sort direction: {direction!r}"
        )
    known = [item for item in items if item.marker.is_known]
    unknown = [item for item in items if not item.marker.is_known]
    known.sort(key=_known_sort_key, reverse=direction == "descending")
    unknown.sort(key=lambda item: _source_key(item.source_ref))
    return tuple((*known, *unknown))


def _mapping(value: object, description: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError(f"canonical {description} is malformed")
    return value


def _string(
    value: object,
    description: str,
) -> str:
    if not isinstance(value, str):
        raise PortiaCorruptionError(f"canonical {description} is malformed")
    return value


def _evidence_time_marker(
    value: object,
    *,
    basis: str,
    instant_key: str = "at",
) -> SemanticTimelineMarker:
    mapping = _mapping(value, basis)
    precision = mapping.get("precision")
    if precision == "exact":
        return SemanticTimelineMarker(
            basis,
            "exact_timestamp",
            _string(mapping.get(instant_key), f"{basis} timestamp"),
        )
    if precision == "approximate":
        start = _string(mapping.get(instant_key), f"{basis} timestamp")
        approximation = _string(
            mapping.get("approximation"),
            f"{basis} approximation",
        )
        end = mapping.get("ended_at")
        if approximation == "within_range":
            return SemanticTimelineMarker(
                basis,
                "timestamp_range",
                start,
                _string(end, f"{basis} end timestamp"),
                approximation="within_range",
            )
        return SemanticTimelineMarker(
            basis,
            "approximate_timestamp",
            start,
            approximation=approximation,
        )
    if precision == "date_only":
        return SemanticTimelineMarker(
            basis,
            "date_only",
            _string(mapping.get("date"), f"{basis} date"),
        )
    if precision == "range":
        return SemanticTimelineMarker(
            basis,
            "timestamp_range",
            _string(mapping.get("started_at"), f"{basis} start timestamp"),
            _string(mapping.get("ended_at"), f"{basis} end timestamp"),
        )
    if precision == "unknown":
        return SemanticTimelineMarker(basis, "unknown")
    raise PortiaCorruptionError(
        f"canonical {basis} has unsupported precision {precision!r}"
    )


def _event_occurrence(record: PortiaRecord, basis: str) -> SemanticTimelineMarker:
    value = _mapping(record.field("occurrence"), "Event occurrence")
    precision = value.get("precision")
    if precision in {"exact", "approximate"}:
        start = _string(value.get("started_at"), "Event occurrence start")
        end = value.get("ended_at")
        approximation = value.get("approximation")
        if isinstance(end, str):
            return SemanticTimelineMarker(
                basis,
                "timestamp_range",
                start,
                end,
                approximation=(
                    approximation if isinstance(approximation, str) else None
                ),
            )
        if precision == "approximate":
            return SemanticTimelineMarker(
                basis,
                "approximate_timestamp",
                start,
                approximation=_string(
                    approximation,
                    "Event occurrence approximation",
                ),
            )
        return SemanticTimelineMarker(basis, "exact_timestamp", start)
    return _evidence_time_marker(value, basis=basis)


def _started_interval(
    record: PortiaRecord,
    basis: str,
) -> SemanticTimelineMarker:
    start = _string(record.field("started_at"), f"{basis} start")
    end = record.field("ended_at")
    if end is None:
        return SemanticTimelineMarker(basis, "exact_timestamp", start)
    return SemanticTimelineMarker(
        basis,
        "timestamp_range",
        start,
        _string(end, f"{basis} end"),
    )


def _planned_schedule(
    record: PortiaRecord,
    basis: str,
) -> SemanticTimelineMarker:
    schedule = _mapping(record.field("schedule"), f"{basis} schedule")
    window = schedule.get("window")
    if window is None:
        return SemanticTimelineMarker(basis, "unknown", planned=True)
    values = _mapping(window, f"{basis} window")
    starts_on = values.get("starts_on")
    ends_on = values.get("ends_on")
    review_on = values.get("review_on")
    if isinstance(starts_on, str) and isinstance(ends_on, str):
        return SemanticTimelineMarker(
            basis,
            "date_range",
            starts_on,
            ends_on,
            planned=True,
        )
    if isinstance(starts_on, str):
        return SemanticTimelineMarker(
            basis,
            "date_only",
            starts_on,
            planned=True,
        )
    if isinstance(ends_on, str):
        return SemanticTimelineMarker(
            basis,
            "date_only",
            ends_on,
            planned=True,
        )
    if isinstance(review_on, str):
        return SemanticTimelineMarker(
            f"{basis}_review",
            "date_only",
            review_on,
            planned=True,
        )
    return SemanticTimelineMarker(basis, "unknown", planned=True)


def _planned_point_or_window(
    value: object,
    *,
    basis: str,
) -> SemanticTimelineMarker:
    mapping = _mapping(value, basis)
    kind = mapping.get("kind")
    if kind == "date_only":
        return SemanticTimelineMarker(
            basis,
            "date_only",
            _string(mapping.get("date"), f"{basis} date"),
            planned=True,
        )
    if kind == "exact_time":
        return SemanticTimelineMarker(
            basis,
            "exact_timestamp",
            _string(mapping.get("at"), f"{basis} timestamp"),
            planned=True,
        )
    if kind == "window":
        starts_on = mapping.get("starts_on")
        ends_on = mapping.get("ends_on")
        if isinstance(starts_on, str) and isinstance(ends_on, str):
            return SemanticTimelineMarker(
                basis,
                "date_range",
                starts_on,
                ends_on,
                planned=True,
            )
        return SemanticTimelineMarker(
            basis,
            "timestamp_range",
            _string(mapping.get("starts_at"), f"{basis} start timestamp"),
            _string(mapping.get("ends_at"), f"{basis} end timestamp"),
            planned=True,
        )
    raise PortiaCorruptionError(
        f"canonical {basis} has unsupported kind {kind!r}"
    )


def _marker_for_record(record: PortiaRecord) -> SemanticTimelineMarker:
    rule = chronology_rule(record.contract, record.contract_version)
    if rule.adapter == "unknown":
        return SemanticTimelineMarker(rule.basis, "unknown")
    if rule.adapter == "event_occurrence":
        return _event_occurrence(record, rule.basis)
    if rule.adapter == "evidence_time":
        field_name = (
            "provided_time" if record.contract == "account" else "observation_time"
        )
        return _evidence_time_marker(
            record.field(field_name),
            basis=rule.basis,
        )
    if rule.adapter == "started_interval":
        return _started_interval(record, rule.basis)
    if rule.adapter == "planned_schedule":
        return _planned_schedule(record, rule.basis)
    if rule.adapter == "evaluated_at":
        return SemanticTimelineMarker(
            rule.basis,
            "exact_timestamp",
            _string(record.field("evaluated_at"), f"{rule.basis} timestamp"),
        )
    if rule.adapter == "follow_up":
        completed = record.field("completed_at")
        if isinstance(completed, str):
            return SemanticTimelineMarker(
                "follow_up_completed_at",
                "exact_timestamp",
                completed,
            )
        return _planned_point_or_window(
            record.field("planned_timing"),
            basis="follow_up_planned_timing",
        )
    if rule.adapter == "outcome_timeframe":
        return _evidence_time_marker(
            record.field("timeframe"),
            basis=rule.basis,
        )
    if rule.adapter == "reentry":
        completed = record.field("completed_at")
        if isinstance(completed, str):
            return SemanticTimelineMarker(
                "reentry_completed_at",
                "exact_timestamp",
                completed,
            )
        return _planned_point_or_window(
            record.field("planned_return"),
            basis="reentry_planned_return",
        )
    if rule.adapter == "repair":
        completed = record.field("completed_at")
        if isinstance(completed, str):
            return SemanticTimelineMarker(
                rule.basis,
                "exact_timestamp",
                completed,
            )
        return SemanticTimelineMarker(rule.basis, "unknown")
    raise PortiaCorruptionError(
        f"chronology adapter is not implemented: {rule.adapter!r}"
    )


class StudentChronologyService:
    """Annotate only already-projected sources with closed semantic chronology."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)

    def annotate(
        self,
        projection: StudentPrivacyProjectionResult,
    ) -> StudentChronologyResult:
        values: list[ChronologizedStudentViewItem] = []
        for item in projection.items:
            marker = self.marker_for_item(item)
            values.append(ChronologizedStudentViewItem(item, marker))
        return StudentChronologyResult(
            projection,
            order_chronology_items(tuple(values)),
        )

    def marker_for_item(
        self,
        item: ProjectedStudentViewItem,
    ) -> SemanticTimelineMarker:
        # A withheld or unavailable item may reveal only the bounded existence
        # already admitted by Slice 3.  Semantic timing is ordinary detail and
        # therefore remains hidden in these fail-closed states.
        if item.disposition in {"withheld", "unavailable"}:
            return SemanticTimelineMarker("privacy_limited", "unknown")
        stored = self._load_source(item.source_ref)
        record = stored.record
        if record.contract != item.semantic_type:
            raise PortiaCorruptionError(
                "projected semantic type disagrees with exact canonical source"
            )
        return _marker_for_record(record)

    def _load_source(self, source_ref: TimelineSourceRef) -> StoredRecord:
        if isinstance(source_ref, ExactPortiaWorkRef):
            return self.repository.load_work(source_ref)
        if not isinstance(source_ref, ExactPortiaWorkRecordRef):
            raise TypeError("timeline source reference is unsupported")
        return self.repository.load_work_record(
            source_ref.work_ref,
            source_ref.record_ref.record_kind,
            source_ref.record_ref.contract_version,
            source_ref.record_ref.record_id,
        )
