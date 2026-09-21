"""Composed read-only student timeline and work view for Issue #48."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.views.chronology import SemanticTimelineMarker, StudentChronologyService
from portia.views.discovery import (
    DiscoveredStudentWork,
    StudentWorkDiscoveryResult,
    StudentWorkDiscoveryService,
)
from portia.views.filters import StudentTimelineFilter, StudentTimelineFilterService
from portia.views.history import (
    StudentHistoryResult,
    StudentHistoryService,
    StudentViewEntry,
    current_entry,
    filter_history_entries,
    order_student_view_entries,
)
from portia.views.models import StudentTimelineQuery
from portia.views.projection import (
    ProjectedScalar,
    StudentPrivacyProjectionResult,
    StudentPrivacyProjectionService,
)


def _work_key(reference: ExactPortiaWorkRef) -> tuple[str, str, str, str]:
    return (
        reference.class_id,
        reference.work_kind,
        reference.work_id,
        reference.contract_version,
    )


def _field_value(entry: StudentViewEntry, name: str) -> ProjectedScalar | None:
    for field in entry.fields:
        if field.name == name and field.disposition == "included":
            return field.value
    return None


@dataclass(frozen=True, slots=True)
class StudentWorkTimelineView:
    """One authoritative Event or Support Process grouping in the student view."""

    work_ref: ExactPortiaWorkRef
    current_status: str | None
    school_year: str | None
    focal_participant_refs: tuple[ExactPortiaWorkRecordRef, ...]
    semantic_work_timing: SemanticTimelineMarker
    current_items: tuple[StudentViewEntry, ...]
    history_items: tuple[StudentViewEntry, ...]
    history_available: bool
    related_work_refs: tuple[ExactPortiaWorkRef, ...]

    def __post_init__(self) -> None:
        if self.work_ref.work_kind not in {"event", "support_process"}:
            raise PortiaLocalValidationError(
                "student work grouping requires Event or Support Process ownership"
            )
        if any(
            reference.work_ref != self.work_ref
            for reference in self.focal_participant_refs
        ):
            raise PortiaLocalValidationError(
                "focal participant navigation belongs to another work"
            )
        if any(item.work_ref != self.work_ref for item in self.current_items):
            raise PortiaLocalValidationError(
                "current work-group entry belongs to another work"
            )
        if any(item.work_ref != self.work_ref for item in self.history_items):
            raise PortiaLocalValidationError(
                "history work-group entry belongs to another work"
            )
        if any(
            item.history_kind != "current_representation"
            for item in self.current_items
        ):
            raise PortiaLocalValidationError(
                "current work-group entries must be current representations"
            )
        if any(
            item.history_kind == "current_representation"
            for item in self.history_items
        ):
            raise PortiaLocalValidationError(
                "history work-group entries cannot be current representations"
            )


@dataclass(frozen=True, slots=True)
class StudentTimelineViewResult:
    """Completed privacy-minimized read-only student timeline/work view."""

    query: StudentTimelineQuery
    filters: StudentTimelineFilter
    discovery: StudentWorkDiscoveryResult
    projection: StudentPrivacyProjectionResult
    history: StudentHistoryResult | None
    entries: tuple[StudentViewEntry, ...]
    works: tuple[StudentWorkTimelineView, ...]

    def __post_init__(self) -> None:
        if self.discovery.query != self.query:
            raise PortiaLocalValidationError(
                "student timeline result discovery does not match its query"
            )
        if self.projection.discovery != self.discovery:
            raise PortiaLocalValidationError(
                "student timeline result projection does not match discovery"
            )
        if self.query.mode == "history":
            if self.history is None or self.history.discovery != self.discovery:
                raise PortiaLocalValidationError(
                    "history-mode result requires matching deliberate history"
                )
        elif self.history is not None:
            raise PortiaLocalValidationError(
                "current-mode result cannot expose deliberate history detail"
            )
        work_refs = tuple(work.work_ref for work in self.works)
        if len(set(work_refs)) != len(work_refs):
            raise PortiaLocalValidationError(
                "student timeline result cannot repeat a work grouping"
            )
        discovered_refs = frozenset(self.discovery.work_refs)
        if frozenset(work_refs) != discovered_refs:
            raise PortiaLocalValidationError(
                "student timeline work groups must exactly match discovered works"
            )


class StudentTimelineService:
    """Compose bounded discovery, projection, chronology, history, and grouping."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.discovery = StudentWorkDiscoveryService(
            self.workspace_root,
            repository=self.repository,
        )
        self.projection = StudentPrivacyProjectionService(
            self.workspace_root,
            repository=self.repository,
        )
        self.chronology = StudentChronologyService(
            self.workspace_root,
            repository=self.repository,
        )
        self.filters = StudentTimelineFilterService()
        self.history = StudentHistoryService(
            self.workspace_root,
            repository=self.repository,
            projection=self.projection,
        )

    def generate(
        self,
        query: StudentTimelineQuery,
        *,
        filters: StudentTimelineFilter | None = None,
    ) -> StudentTimelineViewResult:
        selected_filters = filters or StudentTimelineFilter()
        discovery = self.discovery.discover(query)
        projection = self.projection.project(discovery)
        chronology = self.chronology.annotate(projection)
        filtered_current = self.filters.apply(chronology, selected_filters)
        current_entries = tuple(
            current_entry(item.item, item.marker)
            for item in filtered_current.items
        )

        history_result: StudentHistoryResult | None = None
        history_entries: tuple[StudentViewEntry, ...] = ()
        if query.mode == "history":
            history_result = self.history.assemble(discovery, projection)
            history_entries = filter_history_entries(
                history_result.items,
                selected_filters,
                mode=query.mode,
            )

        entries = order_student_view_entries(
            (*current_entries, *history_entries),
            direction=selected_filters.sort_direction,
        )
        works = tuple(
            self._work_view(
                work,
                entries,
                projection,
                history_result,
            )
            for work in sorted(
                discovery.works, key=lambda item: _work_key(item.work_ref)
            )
        )
        return StudentTimelineViewResult(
            query,
            selected_filters,
            discovery,
            projection,
            history_result,
            entries,
            works,
        )

    def _work_view(
        self,
        discovered: DiscoveredStudentWork,
        entries: tuple[StudentViewEntry, ...],
        projection: StudentPrivacyProjectionResult,
        history: StudentHistoryResult | None,
    ) -> StudentWorkTimelineView:
        work_entries = tuple(
            entry for entry in entries if entry.work_ref == discovered.work_ref
        )
        current_items = tuple(
            entry
            for entry in work_entries
            if entry.history_kind == "current_representation"
        )
        history_items = tuple(
            entry
            for entry in work_entries
            if entry.history_kind != "current_representation"
        )
        root = next(
            (
                entry
                for entry in current_items
                if entry.target_refs == (discovered.work_ref,)
                and entry.semantic_type == discovered.work_ref.work_kind
            ),
            None,
        )
        if root is None:
            root = next(
                (
                    entry
                    for entry in history_items
                    if entry.target_refs == (discovered.work_ref,)
                    and entry.history_kind == "historical_representation"
                ),
                None,
            )
        status = root.status if root is not None else None
        school_year_value = (
            _field_value(root, "school_year") if root is not None else None
        )
        school_year = school_year_value if isinstance(school_year_value, str) else None
        timing = (
            root.marker
            if root is not None
            else SemanticTimelineMarker("semantic_time_not_available", "unknown")
        )

        if history is not None:
            available = any(
                item.work_ref == discovered.work_ref for item in history.items
            )
        else:
            available = self.history.has_history(discovered, projection)

        related = tuple(
            sorted(
                {relation.target_work for relation in discovered.related_context},
                key=_work_key,
            )
        )
        focal = tuple(match.participant_ref for match in discovered.focal_matches)
        return StudentWorkTimelineView(
            discovered.work_ref,
            status,
            school_year,
            focal,
            timing,
            current_items,
            history_items,
            available,
            related,
        )
