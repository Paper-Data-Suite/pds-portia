"""Deterministic privacy-monotone filters for Issue #48 student chronology."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final, Literal, TypeAlias

from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import ExactPortiaWorkRef
from portia.views.chronology import (
    ChronologizedStudentViewItem,
    SortDirection,
    StudentChronologyResult,
    order_chronology_items,
)
from portia.views.models import ViewMode
from portia.views.policy import STUDENT_VIEW_PROJECTION_INVENTORY

TimelineStateField: TypeAlias = Literal[
    "workflow_state",
    "review_state",
    "stage",
    "consideration_state",
    "execution_state",
    "act_state",
    "plan_state",
    "result",
]

_STATE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "workflow_state",
        "review_state",
        "stage",
        "consideration_state",
        "execution_state",
        "act_state",
        "plan_state",
        "result",
    }
)
_WORK_KINDS: Final[frozenset[str]] = frozenset({"event", "support_process"})
_VIEW_MODES: Final[frozenset[str]] = frozenset({"current", "history"})
_CATEGORIES: Final[frozenset[str]] = frozenset(
    rule.category for rule in STUDENT_VIEW_PROJECTION_INVENTORY.values()
)
_RECORD_FAMILIES: Final[frozenset[str]] = frozenset(
    rule.record_kind for rule in STUDENT_VIEW_PROJECTION_INVENTORY.values()
)


def _date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PortiaLocalValidationError(
            f"{field_name} must be an ISO calendar date"
        ) from exc


def _unique(values: tuple[str, ...], field_name: str) -> None:
    if not isinstance(values, tuple):
        raise PortiaLocalValidationError(f"{field_name} must be a tuple")
    if not all(isinstance(value, str) and value for value in values):
        raise PortiaLocalValidationError(
            f"{field_name} must contain non-empty strings"
        )
    if len(set(values)) != len(values):
        raise PortiaLocalValidationError(f"{field_name} cannot repeat values")


@dataclass(frozen=True, slots=True)
class TimelineStateCriterion:
    """One exact safely projected workflow/evaluation state requirement."""

    field_name: TimelineStateField
    value: str

    def __post_init__(self) -> None:
        if self.field_name not in _STATE_FIELDS:
            raise PortiaLocalValidationError(
                f"unsupported timeline state field: {self.field_name!r}"
            )
        validate_external_id(self.value, "timeline_state_value")


@dataclass(frozen=True, slots=True)
class StudentTimelineFilter:
    """Closed filter specification over already-authorized timeline metadata."""

    modes: tuple[ViewMode, ...] = ()
    date_from: str | None = None
    date_to: str | None = None
    work_kinds: tuple[str, ...] = ()
    exact_works: tuple[ExactPortiaWorkRef, ...] = ()
    record_families: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    states: tuple[TimelineStateCriterion, ...] = ()
    sort_direction: SortDirection = "ascending"

    def __post_init__(self) -> None:
        _unique(self.modes, "timeline modes")
        if any(mode not in _VIEW_MODES for mode in self.modes):
            raise PortiaLocalValidationError("timeline modes contain an unknown mode")

        start = _date(self.date_from, "date_from") if self.date_from else None
        end = _date(self.date_to, "date_to") if self.date_to else None
        if start is not None and end is not None and end < start:
            raise PortiaLocalValidationError(
                "timeline date range cannot end before it starts"
            )

        _unique(self.work_kinds, "work_kinds")
        if any(kind not in _WORK_KINDS for kind in self.work_kinds):
            raise PortiaLocalValidationError(
                "work_kinds contain an unsupported Portia work kind"
            )

        if not isinstance(self.exact_works, tuple):
            raise PortiaLocalValidationError("exact_works must be a tuple")
        if not all(
            isinstance(reference, ExactPortiaWorkRef)
            for reference in self.exact_works
        ):
            raise PortiaLocalValidationError(
                "exact_works must contain exact Portia work references"
            )
        if len(set(self.exact_works)) != len(self.exact_works):
            raise PortiaLocalValidationError(
                "exact_works cannot repeat a work reference"
            )

        _unique(self.record_families, "record_families")
        if any(
            family not in _RECORD_FAMILIES for family in self.record_families
        ):
            raise PortiaLocalValidationError(
                "record_families contain an unsupported student-view family"
            )

        _unique(self.categories, "categories")
        if any(category not in _CATEGORIES for category in self.categories):
            raise PortiaLocalValidationError(
                "categories contain an unsupported student-view category"
            )

        _unique(self.statuses, "statuses")
        for status in self.statuses:
            validate_external_id(status, "timeline_status")

        if not isinstance(self.states, tuple) or not all(
            isinstance(value, TimelineStateCriterion) for value in self.states
        ):
            raise PortiaLocalValidationError(
                "states must be a tuple of TimelineStateCriterion values"
            )
        state_keys = tuple(
            (criterion.field_name, criterion.value)
            for criterion in self.states
        )
        if len(set(state_keys)) != len(state_keys):
            raise PortiaLocalValidationError(
                "states cannot repeat an exact state criterion"
            )

        if self.sort_direction not in {"ascending", "descending"}:
            raise PortiaLocalValidationError(
                f"unsupported timeline sort direction: {self.sort_direction!r}"
            )


@dataclass(frozen=True, slots=True)
class FilteredStudentTimelineResult:
    """Privacy-monotone subset of one chronology result."""

    chronology: StudentChronologyResult
    filters: StudentTimelineFilter
    items: tuple[ChronologizedStudentViewItem, ...]

    def __post_init__(self) -> None:
        source_refs = frozenset(
            item.source_ref for item in self.chronology.items
        )
        refs = tuple(item.source_ref for item in self.items)
        if len(set(refs)) != len(refs):
            raise PortiaLocalValidationError(
                "filtered timeline cannot repeat an exact source"
            )
        if not frozenset(refs).issubset(source_refs):
            raise PortiaLocalValidationError(
                "filtered timeline cannot introduce a source absent from chronology"
            )


class StudentTimelineFilterService:
    """Apply deterministic filters without re-reading canonical source payloads."""

    def apply(
        self,
        chronology: StudentChronologyResult,
        filters: StudentTimelineFilter | None = None,
    ) -> FilteredStudentTimelineResult:
        selected = filters or StudentTimelineFilter()
        mode = chronology.projection.discovery.query.mode
        if selected.modes and mode not in selected.modes:
            return FilteredStudentTimelineResult(chronology, selected, ())

        matches = tuple(
            item
            for item in chronology.items
            if self._matches(item, selected)
        )
        return FilteredStudentTimelineResult(
            chronology,
            selected,
            order_chronology_items(
                matches,
                direction=selected.sort_direction,
            ),
        )

    def _matches(
        self,
        value: ChronologizedStudentViewItem,
        filters: StudentTimelineFilter,
    ) -> bool:
        item = value.item
        work = (
            item.source_ref
            if isinstance(item.source_ref, ExactPortiaWorkRef)
            else item.source_ref.work_ref
        )
        if filters.work_kinds and work.work_kind not in filters.work_kinds:
            return False
        if filters.exact_works and work not in filters.exact_works:
            return False
        if (
            filters.record_families
            and item.semantic_type not in filters.record_families
        ):
            return False
        if filters.categories and item.category not in filters.categories:
            return False
        if filters.statuses and item.status not in filters.statuses:
            return False
        if filters.states and not self._matches_states(value, filters.states):
            return False
        if (
            filters.date_from is not None or filters.date_to is not None
        ) and not self._matches_dates(value, filters):
            return False
        return True

    @staticmethod
    def _matches_states(
        value: ChronologizedStudentViewItem,
        criteria: tuple[TimelineStateCriterion, ...],
    ) -> bool:
        safe_values = {
            field.name: field.value
            for field in value.item.fields
            if (
                field.disposition == "included"
                and field.name in _STATE_FIELDS
                and isinstance(field.value, str)
            )
        }
        return all(
            safe_values.get(criterion.field_name) == criterion.value
            for criterion in criteria
        )

    @staticmethod
    def _matches_dates(
        value: ChronologizedStudentViewItem,
        filters: StudentTimelineFilter,
    ) -> bool:
        bounds = value.marker.date_bounds()
        if bounds is None:
            return False
        start, end = bounds
        requested_start = (
            _date(filters.date_from, "date_from")
            if filters.date_from is not None
            else date.min
        )
        requested_end = (
            _date(filters.date_to, "date_to")
            if filters.date_to is not None
            else date.max
        )
        return end >= requested_start and start <= requested_end
