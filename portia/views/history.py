"""Deliberate domain-history assembly for Issue #48 student views.

History is bounded to already-discovered focal work and exact references. It
never reads technical storage-history blobs and never selects currentness by
timestamp, filename, identifier ordering, or schema-version ordering.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Final, Literal, TypeAlias

from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage import (
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
    PortiaRepository,
    StoredRecord,
)
from portia.views.chronology import (
    SemanticTimelineMarker,
    SortDirection,
    StudentChronologyService,
)
from portia.views.currentness import TimelineSourceRef
from portia.views.discovery import DiscoveredStudentWork, StudentWorkDiscoveryResult
from portia.views.filters import StudentTimelineFilter
from portia.views.policy import projection_rules
from portia.views.projection import (
    ProjectedField,
    ProjectedStudentViewItem,
    ProjectionDisposition,
    StudentPrivacyProjectionResult,
    StudentPrivacyProjectionService,
)
from portia.workflows import (
    AmendmentWorkflowService,
    LifecycleWorkflowService,
    StatementOfDisagreementWorkflowService,
    supported_amendment_contracts,
    supported_record_lifecycle_contracts,
)
from portia.workflows.event_lifecycle_history import resolve_event_lifecycle_history
from portia.workflows.support_process_lifecycle import (
    require_support_process_lifecycle_reconciled,
)

HistoryEntryKind: TypeAlias = Literal[
    "current_representation",
    "historical_representation",
    "lifecycle_transition",
    "lifecycle_history_correction",
    "amendment",
    "statement_of_disagreement",
    "record_migration",
    "ownership_correction",
    "exceptional_removal",
]
NavigationScope: TypeAlias = Literal["work", "work_record", "class_record"]

_HISTORICAL_STATUSES: Final[frozenset[str]] = frozenset(
    {"invalidated", "superseded", "withdrawn"}
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


@dataclass(frozen=True, slots=True)
class StudentViewNavigationRef:
    """Exact navigation identity without a filesystem path or raw payload."""

    scope: NavigationScope
    class_id: str
    record_kind: str
    contract_version: str
    record_id: str
    work_ref: ExactPortiaWorkRef | None = None

    def __post_init__(self) -> None:
        if self.scope not in {"work", "work_record", "class_record"}:
            raise PortiaLocalValidationError(
                f"unsupported student-view navigation scope: {self.scope!r}"
            )
        validate_external_id(self.class_id, "navigation_class_id")
        validate_external_id(self.record_kind, "navigation_record_kind")
        validate_external_id(self.contract_version, "navigation_contract_version")
        validate_external_id(self.record_id, "navigation_record_id")
        if self.scope == "work":
            if self.work_ref is None:
                raise PortiaLocalValidationError(
                    "work navigation requires an exact work reference"
                )
            if (
                self.class_id != self.work_ref.class_id
                or self.record_kind != self.work_ref.work_kind
                or self.contract_version != self.work_ref.contract_version
                or self.record_id != self.work_ref.work_id
            ):
                raise PortiaLocalValidationError(
                    "work navigation fields disagree with exact work reference"
                )
        elif self.scope == "work_record":
            if self.work_ref is None:
                raise PortiaLocalValidationError(
                    "work-record navigation requires its exact owning work"
                )
            if self.class_id != self.work_ref.class_id:
                raise PortiaLocalValidationError(
                    "work-record navigation class disagrees with owning work"
                )
        elif self.work_ref is not None:
            raise PortiaLocalValidationError(
                "class-record navigation cannot claim work ownership"
            )


def navigation_for_source(source: TimelineSourceRef) -> StudentViewNavigationRef:
    if isinstance(source, ExactPortiaWorkRef):
        return StudentViewNavigationRef(
            "work",
            source.class_id,
            source.work_kind,
            source.contract_version,
            source.work_id,
            source,
        )
    return StudentViewNavigationRef(
        "work_record",
        source.work_ref.class_id,
        source.record_ref.record_kind,
        source.record_ref.contract_version,
        source.record_ref.record_id,
        source.work_ref,
    )


def _navigation_for_stored(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
) -> StudentViewNavigationRef:
    identifier = stored.record.logical_id
    if not isinstance(identifier, str):
        raise PortiaCorruptionError(
            f"history artifact {stored.record.contract} lacks exact identity"
        )
    return StudentViewNavigationRef(
        "work_record",
        work.class_id,
        stored.record.contract,
        stored.record.contract_version,
        identifier,
        work,
    )


def _navigation_for_class_record(stored: StoredRecord) -> StudentViewNavigationRef:
    identifier = stored.record.logical_id
    class_id = stored.record.class_id
    if not isinstance(identifier, str) or not isinstance(class_id, str):
        raise PortiaCorruptionError(
            "class-scoped history artifact lacks exact identity"
        )
    return StudentViewNavigationRef(
        "class_record",
        class_id,
        stored.record.contract,
        stored.record.contract_version,
        identifier,
    )


@dataclass(frozen=True, slots=True)
class StudentViewEntry:
    """One privacy-safe current or historical timeline entry."""

    navigation: StudentViewNavigationRef
    work_ref: ExactPortiaWorkRef
    target_refs: tuple[TimelineSourceRef, ...]
    history_kind: HistoryEntryKind
    disposition: ProjectionDisposition
    category: str
    semantic_type: str
    status: str | None
    marker: SemanticTimelineMarker
    fields: tuple[ProjectedField, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        validate_external_id(self.category, "student_view_entry_category")
        validate_external_id(self.semantic_type, "student_view_entry_semantic_type")
        if self.disposition == "absent":
            raise PortiaLocalValidationError(
                "assembled student-view entry cannot have absent disposition"
            )
        if not isinstance(self.target_refs, tuple) or not self.target_refs:
            raise PortiaLocalValidationError(
                "student-view entry requires at least one exact bounded target"
            )
        if self.navigation.scope in {"work", "work_record"}:
            if self.navigation.work_ref != self.work_ref:
                raise PortiaLocalValidationError(
                    "entry navigation belongs to another exact work"
                )
        names = tuple(field.name for field in self.fields)
        if len(set(names)) != len(names):
            raise PortiaLocalValidationError(
                "student-view entry cannot repeat a projected field"
            )


@dataclass(frozen=True, slots=True)
class StudentHistoryResult:
    """Deliberate domain history attached to one history-mode discovery result."""

    discovery: StudentWorkDiscoveryResult
    items: tuple[StudentViewEntry, ...]

    def __post_init__(self) -> None:
        if self.discovery.query.mode != "history":
            raise PortiaLocalValidationError(
                "history assembly requires an explicit history-mode query"
            )
        nav_keys = tuple(
            (
                item.navigation.scope,
                item.navigation.class_id,
                item.navigation.record_kind,
                item.navigation.contract_version,
                item.navigation.record_id,
                item.work_ref,
                item.history_kind,
            )
            for item in self.items
        )
        if len(set(nav_keys)) != len(nav_keys):
            raise PortiaLocalValidationError(
                "student history cannot repeat the same exact history entry"
            )


def current_entry(
    value: ProjectedStudentViewItem,
    marker: SemanticTimelineMarker,
) -> StudentViewEntry:
    source = value.source_ref
    work = source if isinstance(source, ExactPortiaWorkRef) else source.work_ref
    return StudentViewEntry(
        navigation_for_source(source),
        work,
        (source,),
        "current_representation",
        value.disposition,
        value.category,
        value.semantic_type,
        value.status,
        marker,
        value.fields,
        value.reason_code,
    )


def _local_target(
    work: ExactPortiaWorkRef,
    value: object,
) -> TimelineSourceRef:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("history target is malformed")
    kind = value.get("kind")
    if kind == "work":
        work_kind = value.get("work_kind")
        version = value.get("contract_version")
        if not isinstance(work_kind, str) or not isinstance(version, str):
            raise PortiaCorruptionError("history work target is inexact")
        return ExactPortiaWorkRef(
            class_id=work.class_id,
            work_id=work.work_id,
            work_kind=work_kind,
            contract_version=version,
        )
    if kind == "local_record":
        try:
            local = ExactLocalRecordRef.from_dict(value.get("record_ref"))
        except Exception as exc:
            raise PortiaCorruptionError(
                "history local-record target is inexact"
            ) from exc
        return ExactPortiaWorkRecordRef(work_ref=work, record_ref=local)
    raise PortiaCorruptionError(f"unsupported history target kind: {kind!r}")


def _certificate_target(value: object) -> TimelineSourceRef:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("history certificate endpoint is malformed")
    kind = value.get("kind")
    if kind in {"work", "event_work"}:
        try:
            return ExactPortiaWorkRef.from_dict(value.get("work_ref"))
        except Exception as exc:
            raise PortiaCorruptionError(
                "history work endpoint is not exact"
            ) from exc
    if kind == "work_record":
        try:
            return ExactPortiaWorkRecordRef.from_dict(value.get("work_record_ref"))
        except Exception as exc:
            raise PortiaCorruptionError(
                "history work-record endpoint is not exact"
            ) from exc
    raise PortiaCorruptionError(
        f"unsupported history certificate endpoint kind: {kind!r}"
    )


def _disagreement_source_matches(
    value: object,
    focal: frozenset[RosterStudentRef],
) -> bool:
    if not isinstance(value, Mapping) or value.get("kind") != "roster_student":
        return False
    try:
        reference = RosterStudentRef.from_dict(value.get("roster_student_ref"))
    except Exception as exc:
        raise PortiaCorruptionError(
            "Statement of Disagreement source roster identity is malformed"
        ) from exc
    return reference in focal


def _exact_child_reference(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
) -> ExactPortiaWorkRecordRef:
    identifier = stored.record.logical_id
    if not isinstance(identifier, str):
        raise PortiaCorruptionError(
            f"historical {stored.record.contract} lacks exact identity"
        )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=stored.record.contract,
            record_id=identifier,
            contract_version=stored.record.contract_version,
        ),
    )


def _exact_timestamp(
    value: object,
    *,
    basis: str,
) -> SemanticTimelineMarker:
    if not isinstance(value, str):
        raise PortiaCorruptionError(f"{basis} timestamp is malformed")
    return SemanticTimelineMarker(basis, "exact_timestamp", value)


def _selection_field(value: str) -> tuple[ProjectedField, ...]:
    return (ProjectedField("history_selection", "included", value),)


def _artifact_entry(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
    *,
    target_refs: tuple[TimelineSourceRef, ...],
    history_kind: HistoryEntryKind,
    marker: SemanticTimelineMarker,
    fields: tuple[ProjectedField, ...] = (),
    disposition: ProjectionDisposition = "included",
    status: str | None = None,
    reason_code: str,
) -> StudentViewEntry:
    return StudentViewEntry(
        _navigation_for_stored(work, stored),
        work,
        target_refs,
        history_kind,
        disposition,
        "history",
        stored.record.contract,
        status,
        marker,
        fields,
        reason_code,
    )


def _endpoint_refs(stored: StoredRecord) -> tuple[TimelineSourceRef, ...]:
    return tuple(
        _certificate_target(stored.record.field(field_name))
        for field_name in ("source", "destination")
    )


def _navigation_key(value: StudentViewEntry) -> tuple[str, ...]:
    nav = value.navigation
    work = value.work_ref
    return (
        work.class_id,
        work.work_kind,
        work.work_id,
        work.contract_version,
        nav.scope,
        nav.record_kind,
        nav.record_id,
        nav.contract_version,
        value.history_kind,
    )


def _parsed_timestamp(value: str) -> str:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PortiaLocalValidationError(
            "student history semantic timestamp must have an explicit offset"
        )
    return parsed.astimezone(timezone.utc).isoformat()


def _entry_sort_key(value: StudentViewEntry) -> tuple[str, str, tuple[str, ...]]:
    bounds = value.marker.date_bounds()
    if bounds is None:
        raise PortiaLocalValidationError("known history marker lacks date bounds")
    absolute = ""
    if value.marker.start is not None and value.marker.precision in {
        "exact_timestamp",
        "approximate_timestamp",
        "timestamp_range",
    }:
        absolute = _parsed_timestamp(value.marker.start)
    return (bounds[0].isoformat(), absolute, _navigation_key(value))


def order_student_view_entries(
    values: tuple[StudentViewEntry, ...],
    *,
    direction: SortDirection = "ascending",
) -> tuple[StudentViewEntry, ...]:
    known = [value for value in values if value.marker.is_known]
    unknown = [value for value in values if not value.marker.is_known]
    known.sort(key=_entry_sort_key, reverse=direction == "descending")
    unknown.sort(key=_navigation_key)
    return tuple((*known, *unknown))


class StudentHistoryService:
    """Assemble deliberate privacy-minimized domain history for discovered work."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        projection: StudentPrivacyProjectionService | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.projection = projection or StudentPrivacyProjectionService(
            self.workspace_root,
            repository=self.repository,
        )
        self.chronology = StudentChronologyService(
            self.workspace_root,
            repository=self.repository,
        )
        self.lifecycle = LifecycleWorkflowService(
            self.workspace_root,
            repository=self.repository,
        )
        self.amendments = AmendmentWorkflowService(
            self.workspace_root,
            repository=self.repository,
        )
        self.disagreements = StatementOfDisagreementWorkflowService(
            self.workspace_root,
            repository=self.repository,
        )

    def assemble(
        self,
        discovery: StudentWorkDiscoveryResult,
        current_projection: StudentPrivacyProjectionResult,
    ) -> StudentHistoryResult:
        if discovery.query.mode != "history":
            raise PortiaLocalValidationError(
                "deliberate history requires a history-mode query"
            )
        if current_projection.discovery != discovery:
            raise PortiaLocalValidationError(
                "history and current-frontier projection must share discovery"
            )

        items: list[StudentViewEntry] = []
        for discovered in discovery.works:
            current_items = tuple(
                item
                for item in current_projection.items
                if (
                    item.source_ref == discovered.work_ref
                    or (
                        isinstance(item.source_ref, ExactPortiaWorkRecordRef)
                        and item.source_ref.work_ref == discovered.work_ref
                    )
                )
            )
            work_items, visible = self._historical_representations(discovered)
            items.extend(work_items)
            visible.update(item.source_ref for item in current_items)
            visible.add(discovered.work_ref)
            visible.update(match.participant_ref for match in discovered.focal_matches)

            structural = self._structural_history(discovered, visible)
            items.extend(structural)

        return StudentHistoryResult(
            discovery,
            order_student_view_entries(tuple(items)),
        )

    def has_history(
        self,
        work: DiscoveredStudentWork,
        current_projection: StudentPrivacyProjectionResult,
    ) -> bool:
        """Return one bounded indicator without exposing history detail."""
        current_items = tuple(
            item
            for item in current_projection.items
            if (
                item.source_ref == work.work_ref
                or (
                    isinstance(item.source_ref, ExactPortiaWorkRecordRef)
                    and item.source_ref.work_ref == work.work_ref
                )
            )
        )
        historical, visible = self._historical_representations(work)
        if historical:
            return True
        visible.update(item.source_ref for item in current_items)
        visible.add(work.work_ref)
        visible.update(match.participant_ref for match in work.focal_matches)
        return bool(self._structural_history(work, visible))

    def _historical_representations(
        self,
        work: DiscoveredStudentWork,
    ) -> tuple[list[StudentViewEntry], set[TimelineSourceRef]]:
        values: list[StudentViewEntry] = []
        visible: set[TimelineSourceRef] = set()

        root = self.repository.load_work(work.work_ref)
        if root.record.status in _HISTORICAL_STATUSES:
            decision = self.projection.project_historical_source(
                work,
                work.work_ref,
                root,
            )
            if decision.item is not None:
                values.append(self._historical_entry(decision.item))
                visible.add(decision.item.source_ref)

        by_kind: dict[str, set[str]] = {}
        for rule in projection_rules():
            if rule.surface != "domain_current":
                continue
            by_kind.setdefault(rule.record_kind, set()).add(rule.contract_version)

        for kind in sorted(by_kind):
            for stored in self.repository.list_work_records_mixed_versions(
                work.work_ref,
                kind,
                supported_versions=frozenset(by_kind[kind]),
            ):
                if stored.record.status not in _HISTORICAL_STATUSES:
                    continue
                source = _exact_child_reference(work.work_ref, stored)
                decision = self.projection.project_historical_source(
                    work,
                    source,
                    stored,
                )
                if decision.item is None:
                    continue
                values.append(self._historical_entry(decision.item))
                visible.add(source)
        return values, visible

    def _historical_entry(
        self,
        item: ProjectedStudentViewItem,
    ) -> StudentViewEntry:
        marker = self.chronology.marker_for_item(item)
        source = item.source_ref
        work = source if isinstance(source, ExactPortiaWorkRef) else source.work_ref
        return StudentViewEntry(
            navigation_for_source(source),
            work,
            (source,),
            "historical_representation",
            item.disposition,
            item.category,
            item.semantic_type,
            item.status,
            marker,
            item.fields,
            item.reason_code or "historical_representation",
        )

    def _structural_history(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        values: list[StudentViewEntry] = []
        values.extend(self._lifecycle_entries(work, visible))
        values.extend(self._amendment_entries(work, visible))
        disagreements = self._disagreement_entries(work, visible)
        values.extend(disagreements)
        for item in disagreements:
            visible.update(item.target_refs)
        values.extend(self._certificate_entries(work, visible))
        values.extend(self._removal_entries(work, visible))
        return values

    def _lifecycle_entries(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        all_transitions = self.repository.list_work_records(
            work.work_ref,
            "lifecycle_transition",
            version="1",
        )
        all_corrections = self.repository.list_work_records(
            work.work_ref,
            "lifecycle_history_correction",
            version="1",
        )
        targeted: set[TimelineSourceRef] = set()
        for stored in (*all_transitions, *all_corrections):
            target = _local_target(work.work_ref, stored.record.field("target"))
            if target in visible:
                targeted.add(target)

        values: list[StudentViewEntry] = []
        for target in sorted(targeted, key=_source_key):
            transitions: tuple[StoredRecord, ...]
            corrections: tuple[StoredRecord, ...]
            selected_head: StoredRecord | None
            selected_correction: StoredRecord | None
            excluded: frozenset[str]
            if isinstance(target, ExactPortiaWorkRef):
                if target != work.work_ref:
                    continue
                root = self.repository.load_work(work.work_ref)
                if work.work_ref.work_kind == "event":
                    event_resolution = resolve_event_lifecycle_history(
                        self.repository,
                        work.work_ref,
                        root.record,
                    )
                    transitions = event_resolution.transitions
                    corrections = event_resolution.corrections
                    selected_head = event_resolution.selected_head
                    selected_correction = event_resolution.selected_correction
                    excluded = event_resolution.excluded_transition_ids
                elif work.work_ref.work_kind == "support_process":
                    state = require_support_process_lifecycle_reconciled(
                        self.repository,
                        work.work_ref,
                        root.record,
                    )
                    transitions = state.transitions
                    corrections = ()
                    selected_head = state.head
                    selected_correction = None
                    excluded = frozenset()
                else:
                    continue
            else:
                key = (
                    target.record_ref.record_kind,
                    target.record_ref.contract_version,
                )
                if key not in supported_record_lifecycle_contracts():
                    continue
                child_resolution = self.lifecycle.resolve_corrected_history(target)
                transitions = child_resolution.transitions
                corrections = child_resolution.corrections
                selected_head = child_resolution.selected_head
                selected_correction = child_resolution.selected_correction
                excluded = child_resolution.excluded_transition_ids

            selected_head_id = (
                selected_head.record.logical_id if selected_head is not None else None
            )
            selected_correction_id = (
                selected_correction.record.logical_id
                if selected_correction is not None
                else None
            )
            for stored in transitions:
                identifier = stored.record.logical_id
                if not isinstance(identifier, str):
                    raise PortiaCorruptionError(
                        "lifecycle transition lacks exact identity"
                    )
                selection = (
                    "excluded"
                    if identifier in excluded
                    else "selected"
                    if identifier == selected_head_id
                    else "historical"
                )
                from_status = stored.record.field("from_status")
                to_status = stored.record.field("to_status")
                if not isinstance(from_status, str) or not isinstance(to_status, str):
                    raise PortiaCorruptionError(
                        "lifecycle transition status values are malformed"
                    )
                fields = (
                    ProjectedField("from_status", "included", from_status),
                    ProjectedField("history_selection", "included", selection),
                    ProjectedField("to_status", "included", to_status),
                )
                values.append(
                    _artifact_entry(
                        work.work_ref,
                        stored,
                        target_refs=(target,),
                        history_kind="lifecycle_transition",
                        marker=_exact_timestamp(
                            stored.record.field("effective_at"),
                            basis="lifecycle_effective_at",
                        ),
                        fields=fields,
                        reason_code=f"lifecycle_{selection}",
                    )
                )
            for stored in corrections:
                identifier = stored.record.logical_id
                if not isinstance(identifier, str):
                    raise PortiaCorruptionError(
                        "lifecycle-history correction lacks exact identity"
                    )
                selection = (
                    "selected"
                    if identifier == selected_correction_id
                    else "historical"
                )
                values.append(
                    _artifact_entry(
                        work.work_ref,
                        stored,
                        target_refs=(target,),
                        history_kind="lifecycle_history_correction",
                        marker=_exact_timestamp(
                            stored.record.field("created_at"),
                            basis="lifecycle_history_correction_recorded_at",
                        ),
                        fields=_selection_field(selection),
                        reason_code=f"lifecycle_correction_{selection}",
                    )
                )
        return values

    def _amendment_entries(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        supported = frozenset(supported_amendment_contracts())
        values: list[StudentViewEntry] = []
        for target in sorted(visible, key=_source_key):
            if isinstance(target, ExactPortiaWorkRef):
                key = (target.work_kind, target.contract_version)
            else:
                key = (
                    target.record_ref.record_kind,
                    target.record_ref.contract_version,
                )
            if key not in supported:
                continue
            resolution = self.amendments.load_history(target)
            selected_id = resolution.selected_amendment_id
            for stored in resolution.amendments:
                identifier = stored.record.logical_id
                if not isinstance(identifier, str):
                    raise PortiaCorruptionError("Amendment lacks exact identity")
                selection = "selected" if identifier == selected_id else "historical"
                values.append(
                    _artifact_entry(
                        work.work_ref,
                        stored,
                        target_refs=(target,),
                        history_kind="amendment",
                        marker=_exact_timestamp(
                            stored.record.field("created_at"),
                            basis="amendment_recorded_at",
                        ),
                        fields=_selection_field(selection),
                        reason_code=f"amendment_{selection}",
                    )
                )
        return values

    def _disagreement_entries(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        focal = frozenset(match.student_ref for match in work.focal_matches)
        values: list[StudentViewEntry] = []
        for stored in self.disagreements.list(work.work_ref):
            target = _local_target(work.work_ref, stored.record.field("target"))
            source_match = _disagreement_source_matches(
                stored.record.field("source"),
                focal,
            )
            if target not in visible and not source_match:
                continue
            values.append(
                _artifact_entry(
                    work.work_ref,
                    stored,
                    target_refs=(target,),
                    history_kind="statement_of_disagreement",
                    marker=_exact_timestamp(
                        stored.record.field("created_at"),
                        basis="disagreement_recorded_at",
                    ),
                    fields=(
                        ProjectedField("statement", "requires_manual_review"),
                    ),
                    disposition="requires_manual_review",
                    status=stored.record.status,
                    reason_code="disagreement_requires_manual_review",
                )
            )
        return values

    def _certificate_entries(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        values: list[StudentViewEntry] = []
        registrations: tuple[
            tuple[str, tuple[str, ...], HistoryEntryKind], ...
        ] = (
            ("record_migration", ("1",), "record_migration"),
            ("ownership_correction", ("1", "2"), "ownership_correction"),
        )
        for kind, versions, history_kind in registrations:
            for stored in self.repository.list_work_records_mixed_versions(
                work.work_ref,
                kind,
                supported_versions=frozenset(versions),
            ):
                endpoints = _endpoint_refs(stored)
                bounded = tuple(ref for ref in endpoints if ref in visible)
                if not bounded:
                    continue
                values.append(
                    _artifact_entry(
                        work.work_ref,
                        stored,
                        target_refs=bounded,
                        history_kind=history_kind,
                        marker=_exact_timestamp(
                            stored.record.field("effective_at"),
                            basis=f"{kind}_effective_at",
                        ),
                        reason_code=f"{kind}_exists",
                    )
                )
        return values

    def _removal_entries(
        self,
        work: DiscoveredStudentWork,
        visible: set[TimelineSourceRef],
    ) -> list[StudentViewEntry]:
        values: list[StudentViewEntry] = []
        for stored in self.repository.list_exceptional_removals(
            work.work_ref.class_id
        ):
            target_value = stored.record.field("target")
            target = _certificate_target(target_value)
            if target not in visible:
                continue
            if not isinstance(target_value, Mapping):
                raise PortiaCorruptionError(
                    "Exceptional Removal target is malformed"
                )
            matches = tuple(
                candidate
                for candidate in self.repository.list_exceptional_removals(
                    work.work_ref.class_id
                )
                if candidate.record.field("target") == target_value
            )
            if len(matches) != 1:
                raise PortiaCorruptionError(
                    "Exceptional Removal target has duplicate certificates"
                )
            try:
                if isinstance(target, ExactPortiaWorkRef):
                    self.repository.load_work(target)
                else:
                    self.repository.load_work_record(
                        target.work_ref,
                        target.record_ref.record_kind,
                        target.record_ref.contract_version,
                        target.record_ref.record_id,
                    )
            except PortiaNotFoundError:
                pass
            else:
                raise PortiaRecoveryRequiredError(
                    "canonical payload and its removal certificate both exist"
                )
            values.append(
                StudentViewEntry(
                    _navigation_for_class_record(stored),
                    work.work_ref,
                    (target,),
                    "exceptional_removal",
                    "unavailable",
                    "history",
                    "exceptional_removal",
                    None,
                    _exact_timestamp(
                        stored.record.field("effective_at"),
                        basis="exceptional_removal_effective_at",
                    ),
                    (),
                    "historical_representation_unavailable",
                )
            )
        return values


def filter_history_entries(
    entries: tuple[StudentViewEntry, ...],
    filters: StudentTimelineFilter,
    *,
    mode: str,
) -> tuple[StudentViewEntry, ...]:
    if filters.modes and mode not in filters.modes:
        return ()
    values = tuple(entry for entry in entries if _history_matches(entry, filters))
    return order_student_view_entries(values, direction=filters.sort_direction)


def _filter_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PortiaLocalValidationError(
            "student history filter date must be an ISO calendar date"
        ) from exc


def _history_matches(
    entry: StudentViewEntry,
    filters: StudentTimelineFilter,
) -> bool:
    if filters.work_kinds and entry.work_ref.work_kind not in filters.work_kinds:
        return False
    if filters.exact_works and entry.work_ref not in filters.exact_works:
        return False
    if filters.record_families and entry.semantic_type not in filters.record_families:
        return False
    if filters.categories and entry.category not in filters.categories:
        return False
    if filters.statuses and entry.status not in filters.statuses:
        return False
    if filters.states:
        safe = {
            field.name: field.value
            for field in entry.fields
            if field.disposition == "included"
        }
        if not all(
            safe.get(criterion.field_name) == criterion.value
            for criterion in filters.states
        ):
            return False
    if filters.date_from is not None or filters.date_to is not None:
        bounds = entry.marker.date_bounds()
        if bounds is None:
            return False
        start, end = bounds
        requested_start = (
            _filter_date(filters.date_from)
            if filters.date_from is not None
            else date.min
        )
        requested_end = (
            _filter_date(filters.date_to)
            if filters.date_to is not None
            else date.max
        )
        if end < requested_start or start > requested_end:
            return False
    return True
