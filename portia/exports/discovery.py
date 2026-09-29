"""Exact work-bounded source discovery for Portia Issue #51 teacher exports.

Slice 2 observes only exact canonical Portia representations beneath one exact
current Event@2 or Support Process@1.  It records stored-representation
fingerprints, source roles, current/unavailable state, and participant-specific
applicability without rendering fields or writing any export artifacts.

The service deliberately does not traverse related work, live-dereference Core
or Actor Directory for output enrichment, infer identity from display labels, or
select current state by timestamps / filenames / greatest identifiers.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Protocol, TypeAlias

from portia.exports.policy import (
    TEACHER_REFERENCE_CONTRACT_RULES,
    TEACHER_REFERENCE_EXPORT_PURPOSES,
    TeacherReferencePurpose,
    require_supported_teacher_reference_work_root,
    teacher_reference_contract_rule,
)
from portia.models import PortiaRecord
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ActorRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaQuarantinedError,
    PortiaRepository,
    StoredRecord,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.views import (
    CurrentnessDecision,
    CurrentnessResolver,
    FocalApplicability,
    NativeScope,
    StudentViewCurrentnessResolver,
)
from portia.workflows import (
    AmendmentResolution,
    AmendmentWorkflowService,
    StatementOfDisagreementWorkflowService,
    WorkflowPrerequisiteError,
    supported_amendment_contracts,
)

TeacherReferenceSourceRef: TypeAlias = ExactPortiaWorkRef | ExactPortiaWorkRecordRef
TeacherReferenceSourceRole: TypeAlias = Literal[
    "projected_domain",
    "projection_context",
    "correction_context",
    "disagreement_context",
]
TeacherReferenceObservationState: TypeAlias = Literal["current", "unavailable"]

_SOURCE_ROLES: Final[frozenset[str]] = frozenset(
    {
        "projected_domain",
        "projection_context",
        "correction_context",
        "disagreement_context",
    }
)
_ROLE_ORDER: Final[dict[str, int]] = {
    "projection_context": 0,
    "projected_domain": 1,
    "disagreement_context": 2,
    "correction_context": 3,
}

_CURRENT_DOMAIN_VERSIONS: Final[dict[str, frozenset[str]]] = {}
for _rule in TEACHER_REFERENCE_CONTRACT_RULES:
    if _rule.surface == "domain_current":
        _CURRENT_DOMAIN_VERSIONS.setdefault(_rule.record_kind, frozenset())
        _CURRENT_DOMAIN_VERSIONS[_rule.record_kind] = frozenset(
            (*_CURRENT_DOMAIN_VERSIONS[_rule.record_kind], _rule.contract_version)
        )

_AMENDABLE_CONTRACTS: Final[frozenset[tuple[str, str]]] = frozenset(
    supported_amendment_contracts()
)


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportScope:
    """One exact v0.2 work-scoped teacher-reference export request."""

    projection_purpose: TeacherReferencePurpose
    work_ref: ExactPortiaWorkRef
    focal_subject_ref: ExactPortiaWorkRecordRef | None = None

    def __post_init__(self) -> None:
        if self.projection_purpose not in TEACHER_REFERENCE_EXPORT_PURPOSES:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference projection purpose: "
                f"{self.projection_purpose!r}"
            )
        require_supported_teacher_reference_work_root(
            self.work_ref.work_kind,
            self.work_ref.contract_version,
        )
        if self.projection_purpose == "teacher_current":
            if self.focal_subject_ref is not None:
                raise PortiaLocalValidationError(
                    "teacher_current export scope cannot carry a focal subject"
                )
            return
        if self.focal_subject_ref is None:
            raise PortiaLocalValidationError(
                "participant_specific export scope requires one exact focal participant"
            )
        if self.focal_subject_ref.work_ref != self.work_ref:
            raise PortiaLocalValidationError(
                "participant_specific focal subject must belong to the exact selected work"
            )
        expected = (
            ("event_participant", "3")
            if self.work_ref.work_kind == "event"
            else ("support_process_participant", "1")
        )
        actual = (
            self.focal_subject_ref.record_ref.record_kind,
            self.focal_subject_ref.record_ref.contract_version,
        )
        if actual != expected:
            raise PortiaLocalValidationError(
                "participant_specific focal subject must be the exact current "
                f"participant family for {self.work_ref.work_kind}"
            )


@dataclass(frozen=True, slots=True)
class TeacherReferenceSourceObservation:
    """Read-only observation of one exact stored source representation."""

    source_ref: TeacherReferenceSourceRef
    source_role: TeacherReferenceSourceRole
    fingerprint: ContentFingerprint
    state: TeacherReferenceObservationState
    state_reason: str
    focal_applicability: FocalApplicability
    native_scope: NativeScope
    focal_relation: str | None = None
    context_target_ref: TeacherReferenceSourceRef | None = None

    def __post_init__(self) -> None:
        if self.source_role not in _SOURCE_ROLES:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference source role: {self.source_role!r}"
            )
        if self.state not in {"current", "unavailable"}:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference observation state: {self.state!r}"
            )
        if not isinstance(self.state_reason, str) or not self.state_reason:
            raise PortiaLocalValidationError(
                "teacher-reference observation requires a non-empty state reason"
            )
        if self.focal_applicability not in {
            "whole_work",
            "direct",
            "among_multiple",
            "not_applicable",
        }:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference focal applicability"
            )
        if self.native_scope not in {
            "work",
            "single_participant",
            "multi_participant",
            "multi_person",
            "record",
        }:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference native scope"
            )

        rule = teacher_reference_contract_rule(
            self.record_kind,
            self.contract_version,
        )
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            if self.source_role != "projection_context":
                raise PortiaLocalValidationError(
                    "teacher-reference work root must be projection_context"
                )
            if rule.surface != "work_root_current":
                raise PortiaLocalValidationError(
                    "projection_context work source must be a current work-root contract"
                )
        else:
            expected_surface = {
                "projected_domain": "domain_current",
                "correction_context": "correction_context",
                "disagreement_context": "disagreement_context",
            }.get(self.source_role)
            if expected_surface is None or rule.surface != expected_surface:
                raise PortiaLocalValidationError(
                    "teacher-reference record source role disagrees with policy surface"
                )

        is_context = self.source_role in {
            "correction_context",
            "disagreement_context",
        }
        if is_context and self.context_target_ref is None:
            raise PortiaLocalValidationError(
                "correction/disagreement context requires an exact context target"
            )
        if not is_context and self.context_target_ref is not None:
            raise PortiaLocalValidationError(
                "ordinary domain/work observations cannot carry a context target"
            )
        if self.context_target_ref is not None:
            if _work_ref(self.context_target_ref) != _work_ref(self.source_ref):
                raise PortiaLocalValidationError(
                    "teacher-reference context cannot cross the selected work boundary"
                )

    @property
    def source_kind(self) -> Literal["portia_work", "portia_record"]:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            return "portia_work"
        return "portia_record"

    @property
    def representation_digest(self) -> str:
        return self.fingerprint.digest

    @property
    def byte_length(self) -> int:
        return self.fingerprint.byte_length

    @property
    def work_ref(self) -> ExactPortiaWorkRef:
        return _work_ref(self.source_ref)

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
class TeacherReferenceScopeDiscovery:
    """Deterministic exact-source observation set for one bounded export scope."""

    scope: TeacherReferenceExportScope
    observations: tuple[TeacherReferenceSourceObservation, ...]

    def __post_init__(self) -> None:
        if not self.observations:
            raise PortiaLocalValidationError(
                "teacher-reference discovery requires the exact work-root observation"
            )
        refs = tuple(item.source_ref for item in self.observations)
        if len(set(refs)) != len(refs):
            raise PortiaLocalValidationError(
                "teacher-reference discovery cannot repeat an exact source"
            )
        if any(item.work_ref != self.scope.work_ref for item in self.observations):
            raise PortiaLocalValidationError(
                "teacher-reference discovery cannot escape the exact selected work"
            )
        if any(
            item.focal_applicability == "not_applicable"
            for item in self.observations
        ):
            raise PortiaLocalValidationError(
                "teacher-reference discovery cannot retain participant-inapplicable sources"
            )
        root = tuple(
            item for item in self.observations if item.source_ref == self.scope.work_ref
        )
        if len(root) != 1 or root[0].source_role != "projection_context":
            raise PortiaLocalValidationError(
                "teacher-reference discovery requires one exact projection-context root"
            )
        if root[0].state != "current":
            raise PortiaLocalValidationError(
                "teacher-reference discovery root must be current"
            )
        observed = frozenset(refs)
        for item in self.observations:
            if item.context_target_ref is not None:
                if item.context_target_ref not in observed:
                    raise PortiaLocalValidationError(
                        "teacher-reference context target must be an observed exact source"
                    )
                target = next(
                    candidate
                    for candidate in self.observations
                    if candidate.source_ref == item.context_target_ref
                )
                if target.focal_applicability == "not_applicable":
                    raise PortiaLocalValidationError(
                        "context cannot attach to a participant-inapplicable source"
                    )
        if self.observations != tuple(
            sorted(self.observations, key=_observation_key)
        ):
            raise PortiaLocalValidationError(
                "teacher-reference observations must use deterministic ordering"
            )

        if self.scope.projection_purpose == "participant_specific":
            focal = self.scope.focal_subject_ref
            assert focal is not None
            focal_items = tuple(
                item for item in self.observations if item.source_ref == focal
            )
            if len(focal_items) != 1:
                raise PortiaLocalValidationError(
                    "participant_specific discovery must observe its exact focal participant"
                )
            focal_item = focal_items[0]
            if (
                focal_item.state != "current"
                or focal_item.source_role != "projected_domain"
                or focal_item.focal_applicability != "direct"
            ):
                raise PortiaLocalValidationError(
                    "participant_specific focal participant must be current and directly applicable"
                )

    def observation_for(
        self,
        source_ref: TeacherReferenceSourceRef,
    ) -> TeacherReferenceSourceObservation:
        for observation in self.observations:
            if observation.source_ref == source_ref:
                return observation
        raise KeyError(source_ref)


@dataclass(frozen=True, slots=True)
class _Applicability:
    focal: FocalApplicability
    native_scope: NativeScope
    relation: str | None = None


StablePersonIdentity: TypeAlias = tuple[str, RosterStudentRef | ActorRef]


class _AmendmentReader(Protocol):
    def require_reconciled(
        self,
        reference: TeacherReferenceSourceRef,
    ) -> AmendmentResolution: ...


class _DisagreementReader(Protocol):
    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]: ...

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord: ...


def _work_ref(source: TeacherReferenceSourceRef) -> ExactPortiaWorkRef:
    if isinstance(source, ExactPortiaWorkRef):
        return source
    return source.work_ref


def _source_key(source: TeacherReferenceSourceRef) -> tuple[str, ...]:
    if isinstance(source, ExactPortiaWorkRef):
        return (
            source.class_id,
            source.work_kind,
            source.work_id,
            source.contract_version,
            "",
            "",
        )
    return (
        source.work_ref.class_id,
        source.work_ref.work_kind,
        source.work_ref.work_id,
        source.work_ref.contract_version,
        source.record_ref.record_kind,
        source.record_ref.contract_version,
        source.record_ref.record_id,
    )


def _observation_key(
    observation: TeacherReferenceSourceObservation,
) -> tuple[object, ...]:
    return (
        _ROLE_ORDER[observation.source_role],
        *_source_key(observation.source_ref),
    )


def _child_reference(
    work: ExactPortiaWorkRef,
    stored: StoredRecord,
) -> ExactPortiaWorkRecordRef:
    identifier = stored.record.logical_id
    if not isinstance(identifier, str):
        raise PortiaCorruptionError(
            f"canonical {stored.record.contract} record lacks exact logical identity"
        )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=stored.record.contract,
            record_id=identifier,
            contract_version=stored.record.contract_version,
        ),
    )


def _local_record_key(value: object) -> tuple[str, str, str]:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("canonical participant target reference is malformed")
    kind = value.get("record_kind")
    identifier = value.get("record_id")
    version = value.get("contract_version")
    if not all(isinstance(item, str) for item in (kind, identifier, version)):
        raise PortiaCorruptionError(
            "teacher-reference participant target must carry exact kind/id/version"
        )
    return str(kind), str(identifier), str(version)


def _participant_key(reference: ExactPortiaWorkRecordRef) -> tuple[str, str, str]:
    return (
        reference.record_ref.record_kind,
        reference.record_ref.record_id,
        reference.record_ref.contract_version,
    )


def _stable_focal_identity(record: PortiaRecord) -> StablePersonIdentity | None:
    if record.contract == "event_participant":
        value = record.field("subject")
        description = "Event Participant subject"
    elif record.contract == "support_process_participant":
        value = record.field("person")
        description = "Support Process Participant person"
    else:
        raise PortiaCorruptionError(
            "participant-specific focal source is not a supported participant record"
        )
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError(f"canonical {description} is malformed")
    kind = value.get("kind")
    try:
        if kind == "roster_student":
            return (
                "roster_student",
                RosterStudentRef.from_dict(value.get("roster_student_ref")),
            )
        if kind == "actor":
            return ("actor", ActorRef.from_dict(value.get("actor_ref")))
    except Exception as exc:
        raise PortiaCorruptionError(
            f"canonical {description} exact identity is malformed"
        ) from exc
    # Descriptive/local-operator/unidentified identities deliberately do not get
    # cross-record identity matching. Display labels are presentation, not identity.
    return None


def _represented_identity_matches(
    value: object,
    focal: StablePersonIdentity | None,
) -> bool:
    if focal is None or not isinstance(value, Mapping):
        return False
    expected_kind, expected_ref = focal
    if value.get("kind") != expected_kind:
        return False
    try:
        if expected_kind == "roster_student":
            return RosterStudentRef.from_dict(value.get("roster_student_ref")) == expected_ref
        return ActorRef.from_dict(value.get("actor_ref")) == expected_ref
    except Exception as exc:
        raise PortiaCorruptionError(
            "canonical represented-human exact identity is malformed"
        ) from exc


def _target_applicability(
    value: object,
    *,
    work: ExactPortiaWorkRef,
    focal: ExactPortiaWorkRecordRef,
) -> _Applicability:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("canonical target is malformed")
    kind = value.get("kind")
    if kind in {"event", "support_process"}:
        if kind != work.work_kind:
            raise PortiaCorruptionError(
                "canonical work target disagrees with containing work kind"
            )
        return _Applicability("whole_work", "work", "work_context")
    expected_participant = (
        "event_participant"
        if work.work_kind == "event"
        else "support_process_participant"
    )
    expected_many = (
        "event_participants"
        if work.work_kind == "event"
        else "support_process_participants"
    )
    if kind == expected_participant:
        key = _local_record_key(value.get("record_ref"))
        matched = key == _participant_key(focal)
        return _Applicability(
            "direct" if matched else "not_applicable",
            "single_participant",
            "target" if matched else None,
        )
    if kind == expected_many:
        values = value.get("targets")
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise PortiaCorruptionError(
                "canonical multi-participant target is malformed"
            )
        matches = False
        for target in values:
            if not isinstance(target, Mapping):
                raise PortiaCorruptionError(
                    "canonical multi-participant target entry is malformed"
                )
            if target.get("kind") != expected_participant:
                raise PortiaCorruptionError(
                    "canonical multi-participant target mixes participant families"
                )
            if _local_record_key(target.get("record_ref")) == _participant_key(focal):
                matches = True
        return _Applicability(
            "among_multiple" if matches else "not_applicable",
            "multi_participant",
            "target" if matches else None,
        )
    raise PortiaCorruptionError(f"unsupported canonical target kind: {kind!r}")


def _native_scope_for_teacher_current(record: PortiaRecord) -> NativeScope:
    if record.contract == "work_relationship":
        return "work"
    if record.contract in {"event_participant", "support_process_participant"}:
        return "single_participant"
    if record.contract == "communication":
        return "multi_person"
    target = record.field("actual_target") if record.contract == "implementation" else record.field("target")
    if isinstance(target, Mapping):
        kind = target.get("kind")
        if kind in {"event", "support_process"}:
            return "work"
        if kind in {"event_participant", "support_process_participant"}:
            return "single_participant"
        if kind in {"event_participants", "support_process_participants"}:
            return "multi_participant"
    return "record"


def _same_stored_representation(first: StoredRecord, second: StoredRecord) -> bool:
    return first.path == second.path and first.fingerprint == second.fingerprint


def _context_target_reference(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> TeacherReferenceSourceRef:
    raw = record.field("target")
    if not isinstance(raw, Mapping):
        raise PortiaCorruptionError(
            f"canonical {record.contract} target is malformed"
        )
    kind = raw.get("kind")
    if kind == "work":
        if (
            raw.get("work_kind") != work.work_kind
            or raw.get("contract_version") != work.contract_version
        ):
            raise PortiaCorruptionError(
                f"canonical {record.contract} work target disagrees with exact owner"
            )
        return work
    if kind != "local_record":
        raise PortiaCorruptionError(
            f"canonical {record.contract} target is not exact same-work context"
        )
    try:
        local = ExactLocalRecordRef.from_dict(raw.get("record_ref"))
    except Exception as exc:
        raise PortiaCorruptionError(
            f"canonical {record.contract} local target is not exact"
        ) from exc
    return ExactPortiaWorkRecordRef(work_ref=work, record_ref=local)


class TeacherReferenceScopeDiscoveryService:
    """Discover exact current work sources without rendering or persistence."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        currentness: CurrentnessResolver | None = None,
        amendments: _AmendmentReader | None = None,
        disagreements: _DisagreementReader | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.currentness: CurrentnessResolver = (
            currentness
            or StudentViewCurrentnessResolver(
                self.workspace_root,
                repository=self.repository,
            )
        )
        self.amendments: _AmendmentReader = (
            amendments
            or AmendmentWorkflowService(
                self.workspace_root,
                repository=self.repository,
            )
        )
        self.disagreements: _DisagreementReader = (
            disagreements
            or StatementOfDisagreementWorkflowService(
                self.workspace_root,
                repository=self.repository,
            )
        )

    def discover(
        self,
        scope: TeacherReferenceExportScope,
    ) -> TeacherReferenceScopeDiscovery:
        if not isinstance(scope, TeacherReferenceExportScope):
            raise TypeError("scope must be a TeacherReferenceExportScope")

        root_stored = self.repository.load_work(scope.work_ref)
        root_decision = self._stable_currentness(scope.work_ref, root_stored)
        if root_decision.state != "current":
            raise PortiaLocalValidationError(
                "teacher-reference export requires an exact current work root"
            )

        focal_identity: StablePersonIdentity | None = None
        focal_preflight: StoredRecord | None = None
        if scope.focal_subject_ref is not None:
            focal_preflight = self.repository.load_work_record(
                scope.work_ref,
                scope.focal_subject_ref.record_ref.record_kind,
                scope.focal_subject_ref.record_ref.contract_version,
                scope.focal_subject_ref.record_ref.record_id,
            )
            focal_decision = self._stable_currentness(
                scope.focal_subject_ref,
                focal_preflight,
            )
            if focal_decision.state != "current":
                raise PortiaLocalValidationError(
                    "participant_specific export requires a current focal participant"
                )
            focal_identity = _stable_focal_identity(focal_preflight.record)

        observations: list[TeacherReferenceSourceObservation] = [
            TeacherReferenceSourceObservation(
                source_ref=scope.work_ref,
                source_role="projection_context",
                fingerprint=root_stored.fingerprint,
                state="current",
                state_reason=root_decision.reason_code,
                focal_applicability="whole_work",
                native_scope="work",
                focal_relation="work_context",
            )
        ]

        for kind in sorted(_CURRENT_DOMAIN_VERSIONS):
            versions = _CURRENT_DOMAIN_VERSIONS[kind]
            for stored in self.repository.list_work_records_mixed_versions(
                scope.work_ref,
                kind,
                supported_versions=versions,
            ):
                source_ref = _child_reference(scope.work_ref, stored)
                applicability = self._applicability(
                    scope,
                    source_ref,
                    stored.record,
                    focal_identity=focal_identity,
                )
                # Preserve Issue #48's privacy-minimizing order: participant
                # applicability is decided before current-use resolution. Unrelated
                # sources never enter the scoped observation set and do not trigger
                # identity/current-use lookups merely to prove their irrelevance.
                if applicability.focal == "not_applicable":
                    continue
                decision = self._stable_currentness(source_ref, stored)
                if decision.state == "noncurrent":
                    continue
                if focal_preflight is not None and source_ref == scope.focal_subject_ref:
                    if stored.fingerprint != focal_preflight.fingerprint:
                        raise PortiaConflictError(
                            "focal participant changed during teacher-reference discovery"
                        )
                observations.append(
                    TeacherReferenceSourceObservation(
                        source_ref=source_ref,
                        source_role="projected_domain",
                        fingerprint=stored.fingerprint,
                        state=(
                            "current"
                            if decision.state == "current"
                            else "unavailable"
                        ),
                        state_reason=decision.reason_code,
                        focal_applicability=applicability.focal,
                        native_scope=applicability.native_scope,
                        focal_relation=applicability.relation,
                    )
                )

        focal_ref = scope.focal_subject_ref
        if focal_ref is not None:
            focal_candidates = [
                item for item in observations if item.source_ref == focal_ref
            ]
            if (
                len(focal_candidates) != 1
                or focal_candidates[0].state != "current"
                or focal_candidates[0].focal_applicability != "direct"
            ):
                raise PortiaLocalValidationError(
                    "participant_specific focal participant is not on the current domain frontier"
                )

        context_targets = {
            item.source_ref: item
            for item in observations
            if item.state == "current"
        }
        disagreement_items = self._discover_disagreements(
            scope,
            context_targets,
        )
        observations.extend(disagreement_items)

        correction_targets = dict(context_targets)
        correction_targets.update(
            {
                item.source_ref: item
                for item in disagreement_items
                if item.state == "current"
            }
        )
        observations.extend(
            self._discover_amendments(scope, correction_targets)
        )

        ordered = tuple(sorted(observations, key=_observation_key))
        return TeacherReferenceScopeDiscovery(scope=scope, observations=ordered)

    def _stable_currentness(
        self,
        source_ref: TeacherReferenceSourceRef,
        stored: StoredRecord,
    ) -> CurrentnessDecision:
        decision = self.currentness.evaluate(source_ref)
        if decision.source_ref != source_ref:
            raise PortiaCorruptionError(
                "currentness authority returned a different exact source"
            )
        if isinstance(source_ref, ExactPortiaWorkRef):
            reread = self.repository.load_work(source_ref)
        else:
            reread = self.repository.load_work_record(
                source_ref.work_ref,
                source_ref.record_ref.record_kind,
                source_ref.record_ref.contract_version,
                source_ref.record_ref.record_id,
            )
        if not _same_stored_representation(stored, reread):
            raise PortiaConflictError(
                "canonical source changed during teacher-reference discovery"
            )
        return decision

    def _applicability(
        self,
        scope: TeacherReferenceExportScope,
        source_ref: ExactPortiaWorkRecordRef,
        record: PortiaRecord,
        *,
        focal_identity: StablePersonIdentity | None,
    ) -> _Applicability:
        if scope.projection_purpose == "teacher_current":
            return _Applicability(
                "whole_work",
                _native_scope_for_teacher_current(record),
                "work_scope",
            )

        focal = scope.focal_subject_ref
        assert focal is not None
        kind = record.contract
        if kind in {"event_participant", "support_process_participant"}:
            matched = source_ref == focal
            return _Applicability(
                "direct" if matched else "not_applicable",
                "single_participant",
                "participant" if matched else None,
            )
        if kind == "work_relationship":
            # The relationship record itself is bounded context owned by this work;
            # its target work is never traversed or added to the discovery set.
            return _Applicability("whole_work", "work", "bounded_relationship")
        if kind == "event_participant_role":
            return _target_applicability(
                record.field("target"),
                work=scope.work_ref,
                focal=focal,
            )
        if kind == "communication":
            return self._communication_applicability(record, focal_identity)
        if kind == "account":
            target = _target_applicability(
                record.field("target"),
                work=scope.work_ref,
                focal=focal,
            )
            source_match = _represented_identity_matches(
                record.field("source"),
                focal_identity,
            )
            if target.focal != "not_applicable":
                if source_match:
                    return _Applicability(
                        target.focal,
                        target.native_scope,
                        "source_and_target",
                    )
                return target
            if source_match:
                return _Applicability("direct", target.native_scope, "source")
            return _Applicability("not_applicable", target.native_scope)
        if kind == "observation":
            target = _target_applicability(
                record.field("target"),
                work=scope.work_ref,
                focal=focal,
            )
            raw_observer = record.field("observer")
            if not isinstance(raw_observer, Mapping):
                raise PortiaCorruptionError("canonical Observation observer is malformed")
            observer_match = False
            if raw_observer.get("kind") == "human":
                observer_match = _represented_identity_matches(
                    raw_observer.get("human_attribution"),
                    focal_identity,
                )
            if target.focal != "not_applicable":
                if observer_match:
                    return _Applicability(
                        target.focal,
                        target.native_scope,
                        "observer_and_target",
                    )
                return target
            if observer_match:
                return _Applicability("direct", target.native_scope, "observer")
            return _Applicability("not_applicable", target.native_scope)
        if kind == "implementation":
            return _target_applicability(
                record.field("actual_target"),
                work=scope.work_ref,
                focal=focal,
            )
        if kind == "fidelity":
            raw = record.field("plan_ref")
            if not isinstance(raw, Mapping):
                raise PortiaCorruptionError("canonical Fidelity plan_ref is malformed")
            try:
                plan_ref = ExactLocalRecordRef.from_dict(raw)
            except Exception as exc:
                raise PortiaCorruptionError(
                    "canonical Fidelity plan_ref is not exact"
                ) from exc
            plan = self.repository.load_work_record(
                scope.work_ref,
                plan_ref.record_kind,
                plan_ref.contract_version,
                plan_ref.record_id,
            )
            return _target_applicability(
                plan.record.field("target"),
                work=scope.work_ref,
                focal=focal,
            )
        raw_target = record.field("target")
        if raw_target is not None:
            return _target_applicability(
                raw_target,
                work=scope.work_ref,
                focal=focal,
            )
        raise PortiaCorruptionError(
            f"teacher-reference applicability adapter missing for {kind!r}"
        )

    @staticmethod
    def _communication_applicability(
        record: PortiaRecord,
        focal_identity: StablePersonIdentity | None,
    ) -> _Applicability:
        sender_match = _represented_identity_matches(
            record.field("sender"),
            focal_identity,
        )
        raw_recipients = record.field("recipients")
        if not isinstance(raw_recipients, Sequence) or isinstance(
            raw_recipients,
            (str, bytes, bytearray),
        ):
            raise PortiaCorruptionError("canonical Communication recipients malformed")
        recipient_match = False
        for recipient in raw_recipients:
            if not isinstance(recipient, Mapping):
                raise PortiaCorruptionError(
                    "canonical Communication recipient is malformed"
                )
            if _represented_identity_matches(
                recipient.get("person"),
                focal_identity,
            ):
                recipient_match = True
        if not sender_match and not recipient_match:
            return _Applicability("not_applicable", "multi_person")
        relation = (
            "sender_and_recipient"
            if sender_match and recipient_match
            else "sender"
            if sender_match
            else "recipient"
        )
        return _Applicability("direct", "multi_person", relation)

    def _discover_disagreements(
        self,
        scope: TeacherReferenceExportScope,
        targets: Mapping[
            TeacherReferenceSourceRef,
            TeacherReferenceSourceObservation,
        ],
    ) -> tuple[TeacherReferenceSourceObservation, ...]:
        observations: list[TeacherReferenceSourceObservation] = []
        for stored in self.disagreements.list(scope.work_ref):
            if stored.record.status != "active":
                continue
            source_ref = _child_reference(scope.work_ref, stored)
            target_ref = _context_target_reference(scope.work_ref, stored.record)
            target = targets.get(target_ref)
            if target is None:
                continue
            state: TeacherReferenceObservationState = "current"
            reason = "current_disagreement_context"
            try:
                accepted = self.disagreements.require_current_use(source_ref)
            except PortiaQuarantinedError:
                state = "unavailable"
                reason = "current_use_blocked"
            except WorkflowPrerequisiteError:
                state = "unavailable"
                reason = "current_authority_unavailable"
            else:
                if not _same_stored_representation(stored, accepted):
                    raise PortiaConflictError(
                        "Statement of Disagreement changed during teacher-reference discovery"
                    )
            observations.append(
                TeacherReferenceSourceObservation(
                    source_ref=source_ref,
                    source_role="disagreement_context",
                    fingerprint=stored.fingerprint,
                    state=state,
                    state_reason=reason,
                    focal_applicability=target.focal_applicability,
                    native_scope=target.native_scope,
                    focal_relation="disagreement_context",
                    context_target_ref=target_ref,
                )
            )
        return tuple(sorted(observations, key=_observation_key))

    def _discover_amendments(
        self,
        scope: TeacherReferenceExportScope,
        targets: Mapping[
            TeacherReferenceSourceRef,
            TeacherReferenceSourceObservation,
        ],
    ) -> tuple[TeacherReferenceSourceObservation, ...]:
        observations: list[TeacherReferenceSourceObservation] = []
        for target_ref, target in sorted(targets.items(), key=lambda item: _source_key(item[0])):
            if isinstance(target_ref, ExactPortiaWorkRef):
                contract = (target_ref.work_kind, target_ref.contract_version)
            else:
                contract = (
                    target_ref.record_ref.record_kind,
                    target_ref.record_ref.contract_version,
                )
            if contract not in _AMENDABLE_CONTRACTS:
                continue
            resolution = self.amendments.require_reconciled(target_ref)
            selected = resolution.selected_amendment
            if selected is None:
                continue
            if resolution.reference != target_ref:
                raise PortiaCorruptionError(
                    "Amendment resolution returned a different exact target"
                )
            source_ref = _child_reference(scope.work_ref, selected)
            if _context_target_reference(scope.work_ref, selected.record) != target_ref:
                raise PortiaCorruptionError(
                    "selected Amendment head does not target the requested exact source"
                )
            reread = self.repository.load_work_record(
                scope.work_ref,
                source_ref.record_ref.record_kind,
                source_ref.record_ref.contract_version,
                source_ref.record_ref.record_id,
            )
            if not _same_stored_representation(selected, reread):
                raise PortiaConflictError(
                    "Amendment context changed during teacher-reference discovery"
                )
            observations.append(
                TeacherReferenceSourceObservation(
                    source_ref=source_ref,
                    source_role="correction_context",
                    fingerprint=selected.fingerprint,
                    state="current",
                    state_reason="selected_reconciled_amendment_head",
                    focal_applicability=target.focal_applicability,
                    native_scope=target.native_scope,
                    focal_relation="correction_context",
                    context_target_ref=target_ref,
                )
            )
        return tuple(sorted(observations, key=_observation_key))
