"""Immutable internal models for the Issue #48 student view surface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.views.policy import (
    PROJECTION_PURPOSES,
    ProjectionPurpose,
    contract_rule,
    current_work_root_rule,
)

ViewMode: TypeAlias = Literal["current", "history"]
TimelineSourceRef: TypeAlias = ExactPortiaWorkRef | ExactPortiaWorkRecordRef

_VIEW_MODES: Final[tuple[ViewMode, ...]] = ("current", "history")


def _student_key(reference: RosterStudentRef) -> tuple[str, str]:
    return (reference.class_id, reference.student_id)


def _work_key(reference: ExactPortiaWorkRef) -> tuple[str, str, str, str]:
    return (
        reference.class_id,
        reference.work_id,
        reference.work_kind,
        reference.contract_version,
    )


@dataclass(frozen=True, slots=True)
class StudentViewScope:
    """Explicit authority boundary for one teacher-local student view.

    Focal people are exact class-qualified Core roster identities. Work-owner
    class scope is separate because Portia permits cross-class participation.
    When ``allowed_class_ids`` is empty, discovery defaults to the focal roster
    classes. A nonempty ``allowed_works`` tuple narrows that class scope further
    to the listed exact works.
    """

    focal_students: tuple[RosterStudentRef, ...]
    allowed_works: tuple[ExactPortiaWorkRef, ...] = ()
    history_allowed: bool = False
    purpose: ProjectionPurpose = "teacher_current"
    allowed_class_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.focal_students, tuple) or not self.focal_students:
            raise PortiaLocalValidationError(
                "student view scope requires at least one exact focal roster student"
            )
        if not all(
            isinstance(reference, RosterStudentRef)
            for reference in self.focal_students
        ):
            raise PortiaLocalValidationError(
                "focal_students must contain only RosterStudentRef values"
            )
        student_keys = tuple(_student_key(item) for item in self.focal_students)
        if len(set(student_keys)) != len(student_keys):
            raise PortiaLocalValidationError(
                "student view scope cannot repeat a focal roster identity"
            )

        if self.purpose not in PROJECTION_PURPOSES:
            raise PortiaLocalValidationError(
                f"unsupported student-view projection purpose: {self.purpose!r}"
            )

        if not isinstance(self.allowed_class_ids, tuple):
            raise PortiaLocalValidationError("allowed_class_ids must be a tuple")
        validated_classes = tuple(
            validate_external_id(class_id, "allowed_class_id")
            for class_id in self.allowed_class_ids
        )
        if len(set(validated_classes)) != len(validated_classes):
            raise PortiaLocalValidationError(
                "student view scope cannot repeat an allowed work-owner class"
            )

        if not isinstance(self.allowed_works, tuple):
            raise PortiaLocalValidationError("allowed_works must be a tuple")
        if not all(
            isinstance(reference, ExactPortiaWorkRef)
            for reference in self.allowed_works
        ):
            raise PortiaLocalValidationError(
                "allowed_works must contain only ExactPortiaWorkRef values"
            )
        work_keys = tuple(_work_key(item) for item in self.allowed_works)
        if len(set(work_keys)) != len(work_keys):
            raise PortiaLocalValidationError(
                "student view scope cannot repeat an exact work reference"
            )

        work_class_ids = self.work_class_ids
        for work in self.allowed_works:
            if work.class_id not in work_class_ids:
                raise PortiaLocalValidationError(
                    "allowed work belongs outside the explicit allowed "
                    "work-owner class scope"
                )
            rule = contract_rule(work.work_kind, work.contract_version)
            if rule.surface not in {
                "work_root_current",
                "legacy_history_only",
            }:
                raise PortiaLocalValidationError(
                    "allowed work reference does not identify a supported "
                    "Portia work root"
                )
            if (
                rule.surface == "legacy_history_only"
                and not self.history_allowed
            ):
                raise PortiaLocalValidationError(
                    "legacy work scope requires explicit history authority"
                )

    @property
    def class_ids(self) -> frozenset[str]:
        """Exact roster classes represented by the focal student identities."""
        return frozenset(item.class_id for item in self.focal_students)

    @property
    def work_class_ids(self) -> frozenset[str]:
        """Explicit work-owner classes, defaulting to the focal roster classes."""
        if self.allowed_class_ids:
            return frozenset(self.allowed_class_ids)
        return self.class_ids

    def allows_student(self, reference: RosterStudentRef) -> bool:
        return any(reference == item for item in self.focal_students)

    def allows_work(self, reference: ExactPortiaWorkRef) -> bool:
        if reference.class_id not in self.work_class_ids:
            return False
        if not self.allowed_works:
            return True
        return any(reference == item for item in self.allowed_works)


@dataclass(frozen=True, slots=True)
class StudentTimelineQuery:
    """One bounded current/history query before discovery or projection."""

    scope: StudentViewScope
    mode: ViewMode = "current"
    exact_works: tuple[ExactPortiaWorkRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scope, StudentViewScope):
            raise PortiaLocalValidationError(
                "student timeline query requires a StudentViewScope"
            )
        if self.mode not in _VIEW_MODES:
            raise PortiaLocalValidationError(
                f"unsupported student timeline mode: {self.mode!r}"
            )
        if self.mode == "history" and not self.scope.history_allowed:
            raise PortiaLocalValidationError(
                "history mode requires explicit history authority in the scope"
            )
        if not isinstance(self.exact_works, tuple):
            raise PortiaLocalValidationError("exact_works must be a tuple")
        if not all(
            isinstance(reference, ExactPortiaWorkRef)
            for reference in self.exact_works
        ):
            raise PortiaLocalValidationError(
                "exact_works must contain only ExactPortiaWorkRef values"
            )
        work_keys = tuple(_work_key(item) for item in self.exact_works)
        if len(set(work_keys)) != len(work_keys):
            raise PortiaLocalValidationError(
                "student timeline query cannot repeat an exact work reference"
            )
        for work in self.exact_works:
            if not self.scope.allows_work(work):
                raise PortiaLocalValidationError(
                    "query work falls outside the explicit student view scope"
                )
            rule = contract_rule(work.work_kind, work.contract_version)
            if rule.surface not in {
                "work_root_current",
                "legacy_history_only",
            }:
                raise PortiaLocalValidationError(
                    "query work does not identify a supported Portia work root"
                )

        selected = self.exact_works or self.scope.allowed_works
        if self.mode == "current":
            for work in selected:
                current_work_root_rule(
                    work.work_kind,
                    work.contract_version,
                )

    @property
    def selected_works(self) -> tuple[ExactPortiaWorkRef, ...]:
        """Return explicit query narrowing, or the scope-level exact narrowing."""
        return self.exact_works or self.scope.allowed_works


@dataclass(frozen=True, slots=True)
class StudentTimelineItem:
    """Minimal exact-source item used by later discovery/projection slices.

    Slice 1 deliberately stores no native payload and no projected free text.
    Later slices may add privacy-safe presentation fields without changing this
    exact-source provenance boundary.
    """

    source_ref: TimelineSourceRef

    def __post_init__(self) -> None:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            rule = contract_rule(
                self.source_ref.work_kind,
                self.source_ref.contract_version,
            )
            if rule.surface not in {
                "work_root_current",
                "legacy_history_only",
            }:
                raise PortiaLocalValidationError(
                    "timeline root source is not a supported work root"
                )
            return
        if isinstance(self.source_ref, ExactPortiaWorkRecordRef):
            rule = contract_rule(
                self.source_ref.record_ref.record_kind,
                self.source_ref.record_ref.contract_version,
            )
            if not rule.ordinary_view_candidate:
                raise PortiaLocalValidationError(
                    "timeline item cannot expose an identity, operational, "
                    "or export-only contract"
                )
            return
        raise PortiaLocalValidationError(
            "timeline item requires an exact Portia work or work-record reference"
        )

    @property
    def work_ref(self) -> ExactPortiaWorkRef:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            return self.source_ref
        return self.source_ref.work_ref

    @property
    def record_kind(self) -> str:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            return self.source_ref.work_kind
        return self.source_ref.record_ref.record_kind

    @property
    def contract_version(self) -> str:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            return self.source_ref.contract_version
        return self.source_ref.record_ref.contract_version


@dataclass(frozen=True, slots=True)
class StudentWorkView:
    """One exact work grouping containing only exact-source timeline items."""

    work_ref: ExactPortiaWorkRef
    items: tuple[StudentTimelineItem, ...] = ()

    def __post_init__(self) -> None:
        rule = contract_rule(
            self.work_ref.work_kind,
            self.work_ref.contract_version,
        )
        if rule.surface not in {
            "work_root_current",
            "legacy_history_only",
        }:
            raise PortiaLocalValidationError(
                "student work view requires a supported Portia work root"
            )
        if not isinstance(self.items, tuple) or not all(
            isinstance(item, StudentTimelineItem) for item in self.items
        ):
            raise PortiaLocalValidationError(
                "student work view items must be a tuple of StudentTimelineItem"
            )
        if any(item.work_ref != self.work_ref for item in self.items):
            raise PortiaLocalValidationError(
                "student work view item belongs to another exact work"
            )
        source_refs = tuple(item.source_ref for item in self.items)
        if len(set(source_refs)) != len(source_refs):
            raise PortiaLocalValidationError(
                "student work view cannot repeat an exact source"
            )


@dataclass(frozen=True, slots=True)
class StudentTimelineResult:
    """Read-only result container; later slices populate privacy-safe detail."""

    query: StudentTimelineQuery
    items: tuple[StudentTimelineItem, ...] = ()
    works: tuple[StudentWorkView, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.query, StudentTimelineQuery):
            raise PortiaLocalValidationError(
                "student timeline result requires its originating query"
            )
        if not isinstance(self.items, tuple) or not all(
            isinstance(item, StudentTimelineItem) for item in self.items
        ):
            raise PortiaLocalValidationError(
                "student timeline result items must be a tuple of StudentTimelineItem"
            )
        if not isinstance(self.works, tuple) or not all(
            isinstance(item, StudentWorkView) for item in self.works
        ):
            raise PortiaLocalValidationError(
                "student timeline result works must be a tuple of StudentWorkView"
            )

        selected = self.query.selected_works
        for item in self.items:
            if not self.query.scope.allows_work(item.work_ref):
                raise PortiaLocalValidationError(
                    "timeline result contains a source outside query scope"
                )
            if selected and item.work_ref not in selected:
                raise PortiaLocalValidationError(
                    "timeline result contains a source outside exact query narrowing"
                )
            if (
                self.query.mode == "current"
                and contract_rule(
                    item.record_kind,
                    item.contract_version,
                ).surface
                == "legacy_history_only"
            ):
                raise PortiaLocalValidationError(
                    "current timeline result cannot contain legacy historical "
                    "representations"
                )
        for work in self.works:
            if not self.query.scope.allows_work(work.work_ref):
                raise PortiaLocalValidationError(
                    "work result falls outside query scope"
                )
            if selected and work.work_ref not in selected:
                raise PortiaLocalValidationError(
                    "work result falls outside exact query narrowing"
                )

        source_refs = tuple(item.source_ref for item in self.items)
        if len(set(source_refs)) != len(source_refs):
            raise PortiaLocalValidationError(
                "student timeline result cannot repeat an exact source"
            )
        work_refs = tuple(item.work_ref for item in self.works)
        if len(set(work_refs)) != len(work_refs):
            raise PortiaLocalValidationError(
                "student timeline result cannot repeat an exact work"
            )
