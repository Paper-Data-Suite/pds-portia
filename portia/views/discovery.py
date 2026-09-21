"""Exact identity-based work discovery for the Issue #48 student view.

This slice discovers only current Event and Support Process work roots. It does
not apply privacy projection, currentness reconciliation, chronology, or history
expansion. Those remain later Issue #48 slices.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from portia.identity.roster import CoreRosterResolver
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage.errors import PortiaCorruptionError, PortiaOwnershipError
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.views.models import StudentTimelineQuery
from portia.views.policy import current_work_root_rule

ParticipantKind: TypeAlias = Literal[
    "event_participant", "support_process_participant"
]

_DISCOVERY_ROOTS: Final[tuple[tuple[str, str], ...]] = (
    ("event", "2"),
    ("support_process", "1"),
)


def _work_key(reference: ExactPortiaWorkRef) -> tuple[str, str, str, str]:
    return (
        reference.class_id,
        reference.work_kind,
        reference.work_id,
        reference.contract_version,
    )


def _participant_key(match: "FocalParticipantMatch") -> tuple[str, str, str, str]:
    reference = match.participant_ref
    return (
        reference.work_ref.class_id,
        reference.work_ref.work_id,
        reference.record_ref.record_kind,
        reference.record_ref.record_id,
    )


def _relationship_key(
    relation: "RelatedWorkContext",
) -> tuple[str, str, str, str]:
    reference = relation.relationship_ref
    return (
        reference.work_ref.class_id,
        reference.work_ref.work_id,
        reference.record_ref.record_kind,
        reference.record_ref.record_id,
    )


def _exact_child_reference(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
) -> ExactPortiaWorkRecordRef:
    identifier = stored.record.logical_id
    if identifier is None:
        raise PortiaCorruptionError(
            f"canonical {stored.record.contract} record has no exact logical identity"
        )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=stored.record.contract,
            record_id=identifier,
            contract_version=stored.record.contract_version,
        ),
    )


def _exact_root_reference(stored: StoredRecord) -> ExactPortiaWorkRef:
    record = stored.record
    if record.class_id is None or record.work_id is None or record.work_kind is None:
        raise PortiaCorruptionError(
            "canonical Portia work root has incomplete exact identity"
        )
    if record.contract != record.work_kind:
        raise PortiaCorruptionError(
            "canonical Portia work root contract disagrees with work_kind"
        )
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind=record.work_kind,
        contract_version=record.contract_version,
    )


def _roster_reference(value: object, *, field_name: str) -> RosterStudentRef:
    try:
        return RosterStudentRef.from_dict(value)
    except Exception as exc:
        raise PortiaCorruptionError(
            f"canonical {field_name} roster identity is malformed"
        ) from exc


def _exact_work_field(stored: StoredRecord, field_name: str) -> ExactPortiaWorkRef:
    value = stored.record.field(field_name)
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError(
            f"canonical Work Relationship {field_name} is malformed"
        )
    try:
        return ExactPortiaWorkRef.from_dict(value)
    except Exception as exc:
        raise PortiaCorruptionError(
            f"canonical Work Relationship {field_name} is not an exact work reference"
        ) from exc


@dataclass(frozen=True, slots=True)
class FocalParticipantMatch:
    """One exact participant identity that matches one exact focal roster student."""

    student_ref: RosterStudentRef
    participant_ref: ExactPortiaWorkRecordRef
    contexts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        kind = self.participant_ref.record_ref.record_kind
        version = self.participant_ref.record_ref.contract_version
        work = self.participant_ref.work_ref
        if kind == "event_participant":
            if work.work_kind != "event" or version != "3":
                raise PortiaLocalValidationError(
                    "Event focal match requires exact event_participant@3"
                )
            if self.contexts:
                raise PortiaLocalValidationError(
                    "Event focal participant match cannot carry "
                    "Support Process contexts"
                )
        elif kind == "support_process_participant":
            if work.work_kind != "support_process" or version != "1":
                raise PortiaLocalValidationError(
                    "Support Process focal match requires exact "
                    "support_process_participant@1"
                )
        else:
            raise PortiaLocalValidationError(
                "focal participant match requires an Event or Support Process "
                "participant"
            )
        if not isinstance(self.contexts, tuple) or not all(
            isinstance(value, str) and value for value in self.contexts
        ):
            raise PortiaLocalValidationError(
                "focal participant contexts must be a tuple of non-empty strings"
            )
        if len(set(self.contexts)) != len(self.contexts):
            raise PortiaLocalValidationError(
                "focal participant contexts cannot repeat"
            )

    @property
    def work_ref(self) -> ExactPortiaWorkRef:
        return self.participant_ref.work_ref

    @property
    def participant_kind(self) -> ParticipantKind:
        kind = self.participant_ref.record_ref.record_kind
        if kind == "event_participant":
            return "event_participant"
        return "support_process_participant"


@dataclass(frozen=True, slots=True)
class RelatedWorkContext:
    """One exact in-scope relationship edge; never an instruction to traverse it."""

    relationship_ref: ExactPortiaWorkRecordRef
    source_work: ExactPortiaWorkRef
    target_work: ExactPortiaWorkRef

    def __post_init__(self) -> None:
        if (
            self.relationship_ref.record_ref.record_kind != "work_relationship"
            or self.relationship_ref.record_ref.contract_version != "2"
        ):
            raise PortiaLocalValidationError(
                "related-work context requires exact work_relationship@2"
            )
        if self.relationship_ref.work_ref != self.source_work:
            raise PortiaLocalValidationError(
                "related-work relationship must be owned by its exact source work"
            )
        current_work_root_rule(
            self.source_work.work_kind,
            self.source_work.contract_version,
        )
        current_work_root_rule(
            self.target_work.work_kind,
            self.target_work.contract_version,
        )


@dataclass(frozen=True, slots=True)
class DiscoveredStudentWork:
    """One independently focal-matched work root plus bounded relationship context."""

    work_ref: ExactPortiaWorkRef
    focal_matches: tuple[FocalParticipantMatch, ...]
    related_context: tuple[RelatedWorkContext, ...] = ()

    def __post_init__(self) -> None:
        current_work_root_rule(self.work_ref.work_kind, self.work_ref.contract_version)
        if not isinstance(self.focal_matches, tuple) or not self.focal_matches:
            raise PortiaLocalValidationError(
                "discovered student work requires at least one exact focal participant"
            )
        if not all(
            isinstance(match, FocalParticipantMatch)
            for match in self.focal_matches
        ):
            raise PortiaLocalValidationError(
                "discovered focal matches must be FocalParticipantMatch values"
            )
        if any(match.work_ref != self.work_ref for match in self.focal_matches):
            raise PortiaLocalValidationError(
                "focal participant match belongs to another exact work"
            )
        if len({_participant_key(match) for match in self.focal_matches}) != len(
            self.focal_matches
        ):
            raise PortiaLocalValidationError(
                "discovered student work cannot repeat a focal participant"
            )
        if not isinstance(self.related_context, tuple) or not all(
            isinstance(relation, RelatedWorkContext)
            for relation in self.related_context
        ):
            raise PortiaLocalValidationError(
                "related_context must be a tuple of RelatedWorkContext values"
            )
        if any(
            relation.source_work != self.work_ref
            for relation in self.related_context
        ):
            raise PortiaLocalValidationError(
                "related-work context belongs to another source work"
            )
        if len({_relationship_key(item) for item in self.related_context}) != len(
            self.related_context
        ):
            raise PortiaLocalValidationError(
                "discovered student work cannot repeat a relationship"
            )


@dataclass(frozen=True, slots=True)
class StudentWorkDiscoveryResult:
    """Privacy-minimal exact-reference discovery result for one bounded query."""

    query: StudentTimelineQuery
    resolved_students: tuple[RosterStudentRef, ...]
    works: tuple[DiscoveredStudentWork, ...]

    def __post_init__(self) -> None:
        if self.resolved_students != self.query.scope.focal_students:
            raise PortiaLocalValidationError(
                "discovery result must preserve the exact resolved focal identities"
            )
        if not isinstance(self.works, tuple) or not all(
            isinstance(work, DiscoveredStudentWork) for work in self.works
        ):
            raise PortiaLocalValidationError(
                "discovery works must be a tuple of DiscoveredStudentWork values"
            )
        refs = tuple(work.work_ref for work in self.works)
        if len(set(refs)) != len(refs):
            raise PortiaLocalValidationError(
                "discovery result cannot repeat an exact work"
            )
        selected = self.query.selected_works
        ref_set = frozenset(refs)
        for work in self.works:
            if not self.query.scope.allows_work(work.work_ref):
                raise PortiaLocalValidationError(
                    "discovered work falls outside the explicit query scope"
                )
            if selected and work.work_ref not in selected:
                raise PortiaLocalValidationError(
                    "discovered work falls outside exact query narrowing"
                )
            for match in work.focal_matches:
                if not self.query.scope.allows_student(match.student_ref):
                    raise PortiaLocalValidationError(
                        "discovery contains a participant outside focal identity scope"
                    )
            for relation in work.related_context:
                if relation.target_work not in ref_set:
                    raise PortiaLocalValidationError(
                        "related-work context cannot widen the discovered work set"
                    )

    @property
    def work_refs(self) -> tuple[ExactPortiaWorkRef, ...]:
        return tuple(work.work_ref for work in self.works)


class StudentWorkDiscoveryService:
    """Discover focal student work without name matching or graph expansion."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        roster_resolver: CoreRosterResolver | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.rosters = roster_resolver or CoreRosterResolver(self.workspace_root)

    def discover(self, query: StudentTimelineQuery) -> StudentWorkDiscoveryResult:
        if not isinstance(query, StudentTimelineQuery):
            raise TypeError("query must be a StudentTimelineQuery")

        # Resolve every exact focal roster identity before touching Portia work.
        # Missing/malformed roster authority therefore remains distinct from an
        # otherwise valid query that simply has no matching Portia work.
        for reference in query.scope.focal_students:
            self.rosters.resolve_reference(reference)

        candidates = self._candidate_works(query)
        discovered: list[DiscoveredStudentWork] = []
        for work in candidates:
            matches = self._focal_matches(query, work)
            if matches:
                discovered.append(
                    DiscoveredStudentWork(
                        work_ref=work,
                        focal_matches=matches,
                    )
                )

        discovered_refs = frozenset(item.work_ref for item in discovered)
        with_context = tuple(
            DiscoveredStudentWork(
                work_ref=item.work_ref,
                focal_matches=item.focal_matches,
                related_context=self._related_context(
                    item.work_ref,
                    discovered_refs,
                ),
            )
            for item in discovered
        )
        return StudentWorkDiscoveryResult(
            query=query,
            resolved_students=query.scope.focal_students,
            works=with_context,
        )

    def _candidate_works(
        self,
        query: StudentTimelineQuery,
    ) -> tuple[ExactPortiaWorkRef, ...]:
        selected = query.selected_works
        if selected:
            exact: list[ExactPortiaWorkRef] = []
            for reference in selected:
                try:
                    current_work_root_rule(
                        reference.work_kind,
                        reference.contract_version,
                    )
                except PortiaLocalValidationError as exc:
                    raise PortiaLocalValidationError(
                        "legacy work-root history requires exact historical "
                        "participant authority; automatic student discovery "
                        "does not infer prior membership"
                    ) from exc
                stored = self.repository.load_work(reference)
                resolved = _exact_root_reference(stored)
                if resolved != reference:
                    raise PortiaOwnershipError(
                        "selected exact work does not match canonical work identity"
                    )
                exact.append(reference)
            return tuple(sorted(exact, key=_work_key))

        candidates: list[ExactPortiaWorkRef] = []
        for class_id in sorted(query.scope.work_class_ids):
            for work_kind, version in _DISCOVERY_ROOTS:
                for stored in self.repository.list_works(
                    class_id,
                    work_kind=work_kind,
                    version=version,
                ):
                    reference = _exact_root_reference(stored)
                    current_work_root_rule(
                        reference.work_kind,
                        reference.contract_version,
                    )
                    candidates.append(reference)
        return tuple(sorted(set(candidates), key=_work_key))

    def _focal_matches(
        self,
        query: StudentTimelineQuery,
        work: ExactPortiaWorkRef,
    ) -> tuple[FocalParticipantMatch, ...]:
        if work.work_kind == "event":
            matches = self._event_matches(query, work)
        elif work.work_kind == "support_process":
            matches = self._support_process_matches(query, work)
        else:
            raise PortiaCorruptionError(
                "student work discovery encountered an unsupported work root"
            )
        return tuple(sorted(matches, key=_participant_key))

    def _event_matches(
        self,
        query: StudentTimelineQuery,
        work: ExactPortiaWorkRef,
    ) -> tuple[FocalParticipantMatch, ...]:
        matches: list[FocalParticipantMatch] = []
        for stored in self.repository.list_event_participants(work, version="3"):
            subject = stored.record.field("subject")
            if not isinstance(subject, Mapping):
                raise PortiaCorruptionError(
                    "canonical Event Participant subject is malformed"
                )
            if subject.get("kind") != "roster_student":
                continue
            student = _roster_reference(
                subject.get("roster_student_ref"),
                field_name="Event Participant subject",
            )
            if not query.scope.allows_student(student):
                continue
            matches.append(
                FocalParticipantMatch(
                    student_ref=student,
                    participant_ref=_exact_child_reference(work, stored),
                )
            )
        return tuple(matches)

    def _support_process_matches(
        self,
        query: StudentTimelineQuery,
        work: ExactPortiaWorkRef,
    ) -> tuple[FocalParticipantMatch, ...]:
        matches: list[FocalParticipantMatch] = []
        for stored in self.repository.list_work_records(
            work,
            "support_process_participant",
            version="1",
        ):
            person = stored.record.field("person")
            if not isinstance(person, Mapping):
                raise PortiaCorruptionError(
                    "canonical Support Process Participant person is malformed"
                )
            if person.get("kind") != "roster_student":
                continue
            student = _roster_reference(
                person.get("roster_student_ref"),
                field_name="Support Process Participant person",
            )
            if not query.scope.allows_student(student):
                continue
            raw_contexts = stored.record.field("contexts")
            if not isinstance(raw_contexts, Sequence) or isinstance(
                raw_contexts, (str, bytes, bytearray)
            ):
                raise PortiaCorruptionError(
                    "canonical Support Process Participant contexts are malformed"
                )
            contexts: list[str] = []
            for context in raw_contexts:
                if not isinstance(context, Mapping):
                    raise PortiaCorruptionError(
                        "canonical Support Process Participant context is malformed"
                    )
                context_kind = context.get("kind")
                if not isinstance(context_kind, str):
                    raise PortiaCorruptionError(
                        "canonical Support Process Participant context is malformed"
                    )
                contexts.append(context_kind)
            matches.append(
                FocalParticipantMatch(
                    student_ref=student,
                    participant_ref=_exact_child_reference(work, stored),
                    contexts=tuple(contexts),
                )
            )
        return tuple(matches)

    def _related_context(
        self,
        source: ExactPortiaWorkRef,
        discovered: frozenset[ExactPortiaWorkRef],
    ) -> tuple[RelatedWorkContext, ...]:
        relations: list[RelatedWorkContext] = []
        for stored in self.repository.list_work_relationships(source, version="2"):
            declared_source = _exact_work_field(stored, "source")
            if declared_source != source:
                raise PortiaOwnershipError(
                    "Work Relationship source disagrees with its canonical owner"
                )
            target = _exact_work_field(stored, "target")
            # The target is intentionally not loaded here. Only work that was
            # independently focal-matched may contribute relationship context.
            if target not in discovered:
                continue
            relations.append(
                RelatedWorkContext(
                    relationship_ref=_exact_child_reference(source, stored),
                    source_work=source,
                    target_work=target,
                )
            )
        return tuple(sorted(relations, key=_relationship_key))
