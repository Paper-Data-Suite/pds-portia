"""Exact graph and lifecycle authority for ``dependency@1`` declarations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from portia.models import DependencyV1, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    PortiaWorkRecordRef,
    PortiaWorkRef,
)
from portia.storage.errors import (
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.dependency_lifecycle import (
    build_dependency_lifecycle_transition,
    require_dependency_lifecycle_reconciled,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

DEPENDENCY_VERSION = "1"

_CURRENT_WORKS = frozenset({("event", "2"), ("support_process", "1")})
_NON_DOMAIN_RECORDS = frozenset(
    {
        "amendment",
        "dependency",
        "derived_current_pointer",
        "derived_index_metadata",
        "exceptional_removal",
        "finding_acknowledgement",
        "finding_suppression",
        "finding_suppression_current_pointer",
        "integrity_finding",
        "lifecycle_history_correction",
        "lifecycle_transition",
        "operation_current_pointer",
        "operation_journal",
        "operation_lock",
        "ownership_correction",
        "quarantine_current_pointer",
        "quarantine_record",
        "record_migration",
        "source_snapshot",
    }
)
_LIVE_GRAPH_STATUSES = frozenset({"proposed", "active"})
_DEPENDENCY_GATES = frozenset({"activation", "current_use", "completion"})
_DEPENDENCY_CONDITIONS = frozenset(
    {
        "satisfied",
        "review_required",
        "unsatisfied",
        "indeterminate",
        "not_currently_evaluated",
    }
)
_GATE_BLOCKING_CONDITIONS = frozenset(
    {"review_required", "unsatisfied", "indeterminate"}
)
_TARGET_SATISFIED_STATUSES = frozenset({"active"})
_TARGET_REVIEW_STATUSES = frozenset(
    {"draft", "proposed", "paused", "closed", "completed", "superseded"}
)
_TARGET_UNSATISFIED_STATUSES = frozenset(
    {"invalidated", "cancelled", "withdrawn", "discontinued"}
)
_SUPPORTED_PORTIA_RECORD_TARGETS = frozenset(
    {
        ("event_participant", "1"),
        ("event_participant", "2"),
        ("event_participant", "3"),
        ("event_participant_role", "1"),
        ("event_participant_role", "2"),
        ("event_participant_role", "3"),
        ("work_relationship", "1"),
        ("work_relationship", "2"),
        ("account", "1"),
        ("account", "2"),
        ("observation", "1"),
        ("observation", "2"),
        ("review", "1"),
        ("classification", "1"),
        ("hypothesis", "1"),
        ("determination", "1"),
        ("response", "1"),
        ("communication", "1"),
        ("statement_of_disagreement", "1"),
        ("support_process_participant", "1"),
        ("support_need", "1"),
        ("support_goal", "1"),
        ("support", "1"),
        ("intervention", "1"),
        ("implementation", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("outcome", "1"),
        ("reentry", "1"),
        ("repair", "1"),
    }
)

Endpoint = ExactPortiaWorkRef | ExactPortiaWorkRecordRef


@dataclass(frozen=True, slots=True)
class DependencyEndpointResolution:
    """One exact local endpoint or one exact-but-uninterpreted module endpoint."""

    kind: str
    reference: object
    stored: StoredRecord | None


@dataclass(frozen=True, slots=True)
class DependencyGraphResolution:
    """Validated bounded dependency graph over an explicitly supplied work scope."""

    works: tuple[ExactPortiaWorkRef, ...]
    dependencies: tuple[StoredRecord, ...]
    live_edge_count: int


@dataclass(frozen=True, slots=True)
class DependencyConditionEvaluation:
    """Derived condition for one exact declared Dependency at one selected gate."""

    reference: ExactPortiaWorkRecordRef
    dependent: Endpoint
    strength: str
    applies_to: str
    purpose: str
    condition: str
    reason: str
    evaluated_at: str | None


@dataclass(frozen=True, slots=True)
class DependencyGateEvaluation:
    """Aggregate one dependent's active declared conditions for one gate."""

    dependent: Endpoint
    gate: str
    evaluated_at: str | None
    conditions: tuple[DependencyConditionEvaluation, ...]
    required_blockers: tuple[str, ...]
    advisory_attention: tuple[str, ...]

    @property
    def required_gate_satisfied(self) -> bool:
        """Whether no required active declaration blocks the selected gate."""
        return not self.required_blockers


def dependency_reference(
    work: ExactPortiaWorkRef,
    dependency_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact same-work ``dependency@1`` reference."""
    _require_current_work(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="dependency",
            record_id=dependency_id,
            contract_version=DEPENDENCY_VERSION,
        ),
    )


def _require_current_work(work: ExactPortiaWorkRef) -> None:
    if (work.work_kind, work.contract_version) not in _CURRENT_WORKS:
        raise WorkflowOwnershipError(
            "Dependency workflows require exact event@2 or support_process@1 ownership"
        )


def _mapping(value: object, *, description: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"{description} is malformed")
    if not all(isinstance(key, str) for key in value):
        raise WorkflowOwnershipError(f"{description} has a non-string key")
    return cast(Mapping[str, object], value)


def _exact_work(value: object, *, description: str) -> ExactPortiaWorkRef:
    raw = PortiaWorkRef.from_dict(value)
    version = raw.contract_version
    if version is None:
        raise WorkflowOwnershipError(f"{description} is not version-exact")
    return ExactPortiaWorkRef(
        module_id=raw.module_id,
        class_id=raw.class_id,
        work_id=raw.work_id,
        work_kind=raw.work_kind,
        contract_version=version,
    )


def _exact_work_record(
    value: object,
    *,
    description: str,
) -> ExactPortiaWorkRecordRef:
    raw = PortiaWorkRecordRef.from_dict(value)
    work_version = raw.work_ref.contract_version
    record_version = raw.record_ref.contract_version
    if work_version is None or record_version is None:
        raise WorkflowOwnershipError(f"{description} is not version-exact")
    work = ExactPortiaWorkRef(
        module_id=raw.work_ref.module_id,
        class_id=raw.work_ref.class_id,
        work_id=raw.work_ref.work_id,
        work_kind=raw.work_ref.work_kind,
        contract_version=work_version,
    )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=raw.record_ref.record_kind,
            record_id=raw.record_ref.record_id,
            contract_version=record_version,
        ),
    )


def _endpoint_key(endpoint: Endpoint) -> tuple[str, ...]:
    if isinstance(endpoint, ExactPortiaWorkRef):
        return (
            "work",
            endpoint.module_id,
            endpoint.class_id,
            endpoint.work_id,
            endpoint.work_kind,
            endpoint.contract_version,
        )
    return (
        "record",
        endpoint.work_ref.module_id,
        endpoint.work_ref.class_id,
        endpoint.work_ref.work_id,
        endpoint.work_ref.work_kind,
        endpoint.work_ref.contract_version,
        endpoint.record_ref.record_kind,
        endpoint.record_ref.record_id,
        endpoint.record_ref.contract_version,
    )


def _local_target_for(endpoint: Endpoint) -> dict[str, object]:
    if isinstance(endpoint, ExactPortiaWorkRef):
        return {
            "kind": "work",
            "work_kind": endpoint.work_kind,
            "contract_version": endpoint.contract_version,
        }
    return {
        "kind": "local_record",
        "record_ref": endpoint.record_ref.to_dict(),
    }


def _require_domain_record_kind(record_kind: str, *, role: str) -> None:
    if record_kind in _NON_DOMAIN_RECORDS:
        raise WorkflowOwnershipError(
            f"Dependency {role} cannot be maintenance/infrastructure record "
            f"{record_kind!r}"
        )


class DependencyWorkflowService(WorkflowServiceBase):
    """Resolve Dependency declarations and coordinate their bounded lifecycle."""

    def _require_record_owner(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> DependencyV1:
        _require_current_work(work)
        if not isinstance(record, DependencyV1):
            raise WorkflowOwnershipError(
                "Dependency authority requires exact dependency@1 records"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Dependency record does not belong to its canonical containing work"
            )
        return record

    def _dependent_endpoint(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_resolution: bool,
    ) -> DependencyEndpointResolution:
        self._require_record_owner(work, record)
        target = _mapping(record.field("dependent"), description="Dependency dependent")
        kind = target.get("kind")
        if kind == "work":
            work_kind = target.get("work_kind")
            version = target.get("contract_version")
            if (work_kind, version) != (work.work_kind, work.contract_version):
                raise WorkflowOwnershipError(
                    "Dependency work dependent must name the exact containing work"
                )
            stored = self.repository.load_work(work) if require_resolution else None
            return DependencyEndpointResolution("work", work, stored)
        if kind != "local_record":
            raise WorkflowOwnershipError(
                "Dependency dependent must be the containing work or exact local record"
            )
        local = _mapping(
            target.get("record_ref"),
            description="Dependency local dependent reference",
        )
        record_kind = local.get("record_kind")
        record_id = local.get("record_id")
        version = local.get("contract_version")
        if not all(isinstance(item, str) for item in (record_kind, record_id, version)):
            raise WorkflowOwnershipError("Dependency local dependent is not exact")
        exact_kind = cast(str, record_kind)
        exact_id = cast(str, record_id)
        exact_version = cast(str, version)
        _require_domain_record_kind(exact_kind, role="dependent")
        reference = ExactPortiaWorkRecordRef(
            work_ref=work,
            record_ref=ExactLocalRecordRef(
                record_kind=exact_kind,
                record_id=exact_id,
                contract_version=exact_version,
            ),
        )
        stored = None
        if require_resolution:
            stored = self.repository.load_work_record(
                work,
                exact_kind,
                exact_version,
                exact_id,
            )
        return DependencyEndpointResolution("local_record", reference, stored)

    def _dependency_endpoint(
        self,
        record: PortiaRecord,
        *,
        require_resolution: bool,
    ) -> DependencyEndpointResolution:
        target = _mapping(record.field("dependency"), description="Dependency target")
        kind = target.get("kind")
        if kind == "portia_work":
            work_reference = _exact_work(
                target.get("work_ref"),
                description="Dependency Portia work target",
            )
            stored = (
                self.repository.load_work(work_reference)
                if require_resolution
                else None
            )
            return DependencyEndpointResolution(
                "portia_work", work_reference, stored
            )
        if kind == "portia_record":
            record_reference = _exact_work_record(
                target.get("work_record_ref"),
                description="Dependency Portia record target",
            )
            _require_domain_record_kind(
                record_reference.record_ref.record_kind,
                role="target",
            )
            stored = None
            if require_resolution:
                stored = self.repository.load_work_record(
                    record_reference.work_ref,
                    record_reference.record_ref.record_kind,
                    record_reference.record_ref.contract_version,
                    record_reference.record_ref.record_id,
                )
            return DependencyEndpointResolution(
                "portia_record", record_reference, stored
            )
        if kind == "module_record":
            raw_reference = _mapping(
                target.get("module_work_record_ref"),
                description="Dependency module record target",
            )
            raw_work = _mapping(
                raw_reference.get("work_ref"),
                description="Dependency module work reference",
            )
            raw_record = _mapping(
                raw_reference.get("record_ref"),
                description="Dependency module record reference",
            )
            work_module_id = raw_work.get("module_id")
            record_module_id = raw_record.get("module_id")
            record_version = raw_record.get("contract_version")
            if work_module_id == "portia" or record_module_id == "portia":
                raise WorkflowOwnershipError(
                    "Portia dependency targets must use the Portia target branch"
                )
            if (
                not isinstance(work_module_id, str)
                or not work_module_id
                or not isinstance(record_module_id, str)
                or not record_module_id
            ):
                raise WorkflowOwnershipError(
                    "Dependency module target lacks exact module identity"
                )
            if work_module_id != record_module_id:
                raise WorkflowOwnershipError(
                    "Dependency module work and record references disagree on module_id"
                )
            if not isinstance(record_version, str):
                raise WorkflowOwnershipError(
                    "Dependency module target must pin the record contract version"
                )
            return DependencyEndpointResolution(
                "module_record",
                dict(raw_reference),
                None,
            )
        raise WorkflowOwnershipError("Dependency target kind is unsupported")

    @staticmethod
    def _require_creation_semantics(candidate: PortiaRecord) -> None:
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "fresh Dependency creation must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Dependency creation cannot establish supersession history"
            )
        created_at = candidate.field("created_at")
        updated_at = candidate.field("updated_at")
        if not isinstance(created_at, str) or not isinstance(updated_at, str):
            raise WorkflowPrerequisiteError(
                "Dependency creation timestamps are malformed"
            )
        try:
            created = datetime.fromisoformat(
                created_at[:-1] + "+00:00" if created_at.endswith("Z") else created_at
            )
            updated = datetime.fromisoformat(
                updated_at[:-1] + "+00:00" if updated_at.endswith("Z") else updated_at
            )
        except ValueError as exc:
            raise WorkflowPrerequisiteError(
                "Dependency creation timestamps are malformed"
            ) from exc
        if created.utcoffset() is None or updated.utcoffset() is None:
            raise WorkflowPrerequisiteError(
                "Dependency creation timestamps require explicit offsets"
            )
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Dependency updated_at cannot precede created_at"
            )

    def _require_declared_policy(
        self,
        candidate: PortiaRecord,
        dependent: DependencyEndpointResolution,
    ) -> None:
        strength = candidate.field("strength")
        applies_to = candidate.field("applies_to")
        purpose = candidate.field("purpose")
        if not all(
            isinstance(value, str) for value in (strength, applies_to, purpose)
        ):
            raise WorkflowOwnershipError(
                "Dependency condition classification is malformed"
            )
        if purpose == "authorization_basis" and strength != "required":
            raise WorkflowPrerequisiteError(
                "Dependency authorization_basis requires required strength"
            )
        if applies_to == "completion":
            if dependent.kind != "work":
                raise WorkflowPrerequisiteError(
                    "Dependency completion scope is not supported for this child record"
                )
            exact_dependent = cast(ExactPortiaWorkRef, dependent.reference)
            if (
                exact_dependent.work_kind,
                exact_dependent.contract_version,
            ) != ("event", "2"):
                raise WorkflowPrerequisiteError(
                    "Dependency completion scope currently requires exact event@2 work"
                )

    @staticmethod
    def _basis_duplicates_target(
        dependent: StoredRecord,
        target: ExactPortiaWorkRecordRef,
    ) -> bool:
        record = dependent.record
        if record.contract != "event_participant_role":
            return False
        if (
            target.work_ref.class_id != record.class_id
            or target.work_ref.work_id != record.work_id
        ):
            return False
        if target.record_ref.record_kind not in {"account", "observation"}:
            return False
        basis = record.field("basis")
        if not isinstance(basis, Sequence) or isinstance(basis, (str, bytes)):
            return False
        expected_kind = f"{target.record_ref.record_kind}_ref"
        for value in basis:
            if not isinstance(value, Mapping) or value.get("kind") != expected_kind:
                continue
            reference = value.get("record_ref")
            if not isinstance(reference, Mapping):
                continue
            if (
                reference.get("record_kind") == target.record_ref.record_kind
                and reference.get("record_id") == target.record_ref.record_id
            ):
                return True
        return False

    def _require_no_intrinsic_duplication(
        self,
        dependent: DependencyEndpointResolution,
        target: DependencyEndpointResolution,
    ) -> None:
        if dependent.stored is None or target.kind != "portia_record":
            return
        exact_target = cast(ExactPortiaWorkRecordRef, target.reference)
        if self._basis_duplicates_target(dependent.stored, exact_target):
            raise WorkflowPrerequisiteError(
                "Dependency duplicates an intrinsic Event Participant Role basis reference"
            )

    def _require_creation_graph(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
        dependent: DependencyEndpointResolution,
        target: DependencyEndpointResolution,
        graph_works: Sequence[ExactPortiaWorkRef] | None,
    ) -> None:
        scope = (work,) if graph_works is None else tuple(graph_works)
        if work not in scope:
            raise WorkflowPrerequisiteError(
                "Dependency creation graph scope must include the containing work"
            )
        works = self._bounded_work_scope(scope)
        self.require_graph_valid(works)

        exact_dependent = cast(Endpoint, dependent.reference)
        if target.kind == "module_record":
            raise WorkflowPrerequisiteError(
                "Dependency creation for sibling-module targets requires explicit "
                "producer compatibility authority"
            )
        exact_target = cast(Endpoint, target.reference)
        target_work = (
            exact_target
            if isinstance(exact_target, ExactPortiaWorkRef)
            else exact_target.work_ref
        )
        target_is_current_owner = (
            target_work.work_kind,
            target_work.contract_version,
        ) in _CURRENT_WORKS
        if target_is_current_owner and target_work not in works:
            raise WorkflowPrerequisiteError(
                "Dependency creation graph scope is incomplete for an exact Portia "
                "target; supply the referenced work explicitly"
            )

        dependent_key = _endpoint_key(exact_dependent)
        target_key = _endpoint_key(exact_target)
        if dependent_key == target_key:
            raise WorkflowPrerequisiteError(
                "Dependency creation cannot be self-dependent"
            )

        if candidate.status == "active":
            signature = self._active_condition_signature(work, candidate)
            for stored in self.list(work):
                if stored.record.status != "active":
                    continue
                if self._active_condition_signature(work, stored.record) == signature:
                    raise WorkflowPrerequisiteError(
                        "Dependency creation conflicts with an existing active semantic "
                        "declaration"
                    )

        edges: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
        for owner in works:
            for stored in self.list(owner):
                if stored.record.status not in _LIVE_GRAPH_STATUSES:
                    continue
                existing_dependent = self._dependent_endpoint(
                    owner,
                    stored.record,
                    require_resolution=False,
                )
                existing_target = self._dependency_endpoint(
                    stored.record,
                    require_resolution=False,
                )
                if existing_target.kind == "module_record":
                    continue
                source = cast(Endpoint, existing_dependent.reference)
                destination = cast(Endpoint, existing_target.reference)
                edges.setdefault(_endpoint_key(source), set()).add(
                    _endpoint_key(destination)
                )
        edges.setdefault(dependent_key, set()).add(target_key)

        visiting: set[tuple[str, ...]] = set()
        visited: set[tuple[str, ...]] = set()

        def visit(node: tuple[str, ...]) -> None:
            if node in visiting:
                raise WorkflowPrerequisiteError(
                    "Dependency creation would introduce a cycle"
                )
            if node in visited:
                return
            visiting.add(node)
            for destination in edges.get(node, set()):
                visit(destination)
            visiting.remove(node)
            visited.add(node)

        for node in tuple(edges):
            visit(node)

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        graph_works: Sequence[ExactPortiaWorkRef] | None = None,
    ) -> StoredRecord:
        """Persist one fresh exact declared Dependency after bounded preflight."""
        _require_current_work(work)
        self.repository.load_work(work)
        candidate = self._require_record_owner(work, record)
        self._require_creation_semantics(candidate)
        dependent = self._dependent_endpoint(
            work,
            candidate,
            require_resolution=True,
        )
        target = self._dependency_endpoint(
            candidate,
            require_resolution=True,
        )
        self._require_declared_policy(candidate, dependent)
        self._require_no_intrinsic_duplication(dependent, target)
        self._require_creation_graph(
            work,
            candidate,
            dependent,
            target,
            graph_works,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate),
            "block_work_writes",
        )
        if candidate.status == "active":
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        if not isinstance(candidate.logical_id, str):
            raise WorkflowOwnershipError(
                "Dependency creation requires exact canonical identity"
            )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        """Load one exact Dependency without following replacement lineage."""
        _require_current_work(reference.work_ref)
        if (
            reference.record_ref.record_kind != "dependency"
            or reference.record_ref.contract_version != DEPENDENCY_VERSION
        ):
            raise WorkflowOwnershipError(
                "Dependency exact read requires a dependency@1 reference"
            )
        stored = self.repository.load_work_record(
            reference.work_ref,
            "dependency",
            DEPENDENCY_VERSION,
            reference.record_ref.record_id,
        )
        self._require_record_owner(reference.work_ref, stored.record)
        self._dependent_endpoint(
            reference.work_ref,
            stored.record,
            require_resolution=False,
        )
        self._dependency_endpoint(stored.record, require_resolution=False)
        return stored

    resolve_exact = load_exact

    def resolve_dependent(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> DependencyEndpointResolution:
        """Resolve the exact same-work dependent endpoint."""
        stored = self.load_exact(reference)
        return self._dependent_endpoint(
            reference.work_ref,
            stored.record,
            require_resolution=True,
        )

    def resolve_dependency_target(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> DependencyEndpointResolution:
        """Resolve an exact Portia target or preserve a sibling-module target."""
        stored = self.load_exact(reference)
        return self._dependency_endpoint(stored.record, require_resolution=True)

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        """List exact Dependency identities beneath one explicitly selected work."""
        _require_current_work(work)
        values = self.repository.list_work_records(
            work,
            "dependency",
            version=DEPENDENCY_VERSION,
        )
        for value in values:
            self._require_record_owner(work, value.record)
            self._dependent_endpoint(work, value.record, require_resolution=False)
            self._dependency_endpoint(value.record, require_resolution=False)
        return values

    list_dependencies = list

    def list_for_dependent(
        self,
        dependent: Endpoint,
    ) -> tuple[StoredRecord, ...]:
        """List declarations owned by one exact dependent without successor following."""
        work = (
            dependent
            if isinstance(dependent, ExactPortiaWorkRef)
            else dependent.work_ref
        )
        _require_current_work(work)
        expected_key = _endpoint_key(dependent)
        matches: list[StoredRecord] = []
        for item in self.list(work):
            resolution = self._dependent_endpoint(
                work,
                item.record,
                require_resolution=False,
            )
            reference = cast(Endpoint, resolution.reference)
            if _endpoint_key(reference) == expected_key:
                matches.append(item)
        return tuple(matches)

    def list_incoming(
        self,
        search_works: Sequence[ExactPortiaWorkRef],
        target: Endpoint,
    ) -> tuple[StoredRecord, ...]:
        """Derive incoming declarations only across an explicit bounded work scope."""
        works = self._bounded_work_scope(search_works)
        expected_kind = "portia_work" if isinstance(target, ExactPortiaWorkRef) else "portia_record"
        expected_key = _endpoint_key(target)
        matches: list[StoredRecord] = []
        for work in works:
            for item in self.list(work):
                resolution = self._dependency_endpoint(
                    item.record,
                    require_resolution=False,
                )
                if resolution.kind != expected_kind:
                    continue
                reference = resolution.reference
                if isinstance(
                    reference,
                    (ExactPortiaWorkRef, ExactPortiaWorkRecordRef),
                ) and _endpoint_key(reference) == expected_key:
                    matches.append(item)
        return tuple(matches)

    def _active_condition_signature(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[tuple[str, ...], tuple[str, ...], str, str, str]:
        dependent_resolution = self._dependent_endpoint(
            work,
            record,
            require_resolution=False,
        )
        dependent = cast(Endpoint, dependent_resolution.reference)
        target_resolution = self._dependency_endpoint(
            record,
            require_resolution=False,
        )
        target_key: tuple[str, ...]
        if target_resolution.kind == "module_record":
            target_key = ("module_record", repr(target_resolution.reference))
        else:
            target = cast(Endpoint, target_resolution.reference)
            target_key = _endpoint_key(target)
        strength = record.field("strength")
        applies_to = record.field("applies_to")
        purpose = record.field("purpose")
        if not all(
            isinstance(value, str)
            for value in (strength, applies_to, purpose)
        ):
            raise WorkflowOwnershipError(
                "Dependency condition classification is malformed"
            )
        return (
            _endpoint_key(dependent),
            target_key,
            cast(str, strength),
            cast(str, applies_to),
            cast(str, purpose),
        )

    def _require_activation_graph(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
        graph_works: Sequence[ExactPortiaWorkRef] | None,
    ) -> None:
        scope = (work,) if graph_works is None else tuple(graph_works)
        if work not in scope:
            raise WorkflowPrerequisiteError(
                "Dependency activation graph scope must include the containing work"
            )
        self.require_graph_valid(scope)
        signature = self._active_condition_signature(work, candidate)
        prior_id = prior.logical_id
        for stored in self.list(work):
            if stored.record.logical_id == prior_id or stored.record.status != "active":
                continue
            if self._active_condition_signature(work, stored.record) == signature:
                raise WorkflowPrerequisiteError(
                    "Dependency activation conflicts with an existing active semantic declaration"
                )

    def _require_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
        *,
        graph_works: Sequence[ExactPortiaWorkRef] | None,
    ) -> None:
        self._require_record_owner(work, prior)
        self._require_record_owner(work, candidate)
        self._dependent_endpoint(work, candidate, require_resolution=True)
        self._dependency_endpoint(candidate, require_resolution=True)
        if candidate.status == "active":
            self._require_activation_graph(
                work,
                prior,
                candidate,
                graph_works,
            )

    def transition_lifecycle(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str,
        reason_detail: str | None = None,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
        graph_works: Sequence[ExactPortiaWorkRef] | None = None,
    ) -> OperationCommitResult:
        """Persist one ordinary Dependency activation or invalidation."""
        if (
            reference.record_ref.record_kind != "dependency"
            or reference.record_ref.contract_version != DEPENDENCY_VERSION
        ):
            raise WorkflowOwnershipError(
                "Dependency lifecycle requires an exact dependency@1 reference"
            )
        work = reference.work_ref
        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        result = coordinator.commit(
            reference,
            candidate,
            expected=expected,
            transition_id=transition_id,
            reason_code=reason_code,
            operation_id=operation_id,
            fault_hook=fault_hook,
            candidate_validator=lambda prior, value: self._require_transition_candidate(
                work,
                prior,
                value,
                graph_works=graph_works,
            ),
            transition_factory=lambda prior, value: build_dependency_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=reason_code,
                reason_detail=reason_detail,
                effective_at=effective_at,
            ),
        )
        accepted = self.load_exact(reference)
        require_dependency_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    @staticmethod
    def _evaluation_time(value: object, *, description: str) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise WorkflowPrerequisiteError(
                f"Dependency {description} timestamp is malformed"
            )
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise WorkflowPrerequisiteError(
                f"Dependency {description} timestamp is malformed"
            ) from exc
        if parsed.utcoffset() is None:
            raise WorkflowPrerequisiteError(
                f"Dependency {description} timestamp requires an explicit offset"
            )
        return parsed

    @staticmethod
    def _condition(
        reference: ExactPortiaWorkRecordRef,
        dependent: Endpoint,
        record: PortiaRecord,
        *,
        condition: str,
        reason: str,
        evaluated_at: str | None,
    ) -> DependencyConditionEvaluation:
        if condition not in _DEPENDENCY_CONDITIONS:
            raise AssertionError(f"unknown Dependency condition {condition!r}")
        strength = record.field("strength")
        applies_to = record.field("applies_to")
        purpose = record.field("purpose")
        if not all(
            isinstance(value, str)
            for value in (strength, applies_to, purpose)
        ):
            raise WorkflowOwnershipError(
                "Dependency condition classification is malformed"
            )
        return DependencyConditionEvaluation(
            reference=reference,
            dependent=dependent,
            strength=cast(str, strength),
            applies_to=cast(str, applies_to),
            purpose=cast(str, purpose),
            condition=condition,
            reason=reason,
            evaluated_at=evaluated_at,
        )

    def _target_has_active_disagreement(self, target: Endpoint) -> bool:
        work = target if isinstance(target, ExactPortiaWorkRef) else target.work_ref
        expected = _local_target_for(target)
        try:
            values = self.repository.list_work_records(
                work,
                "statement_of_disagreement",
                version="1",
            )
        except PortiaNotFoundError:
            return False
        return any(
            stored.record.status == "active"
            and stored.record.field("target") == expected
            for stored in values
        )

    def _require_target_history_reconciled(
        self,
        target: Endpoint,
        stored: StoredRecord,
    ) -> None:
        if isinstance(target, ExactPortiaWorkRef):
            if (
                target.work_kind,
                target.contract_version,
            ) == ("support_process", "1"):
                from portia.workflows.support_process_lifecycle import (
                    require_support_process_lifecycle_reconciled,
                )

                require_support_process_lifecycle_reconciled(
                    self.repository,
                    target,
                    stored.record,
                )
            return

        from portia.workflows.lifecycle import (
            LifecycleWorkflowService,
            supported_record_lifecycle_contracts,
        )

        key = (
            target.record_ref.record_kind,
            target.record_ref.contract_version,
        )
        if key not in supported_record_lifecycle_contracts():
            return
        LifecycleWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        ).require_corrected_history_reconciled(target)

    def _require_evaluation_dependent(self, dependent: Endpoint) -> StoredRecord:
        owner = (
            dependent
            if isinstance(dependent, ExactPortiaWorkRef)
            else dependent.work_ref
        )
        _require_current_work(owner)
        if isinstance(dependent, ExactPortiaWorkRef):
            return self.repository.load_work(dependent)
        _require_domain_record_kind(
            dependent.record_ref.record_kind,
            role="dependent",
        )
        stored = self.repository.load_work_record(
            dependent.work_ref,
            dependent.record_ref.record_kind,
            dependent.record_ref.contract_version,
            dependent.record_ref.record_id,
        )
        if (
            stored.record.contract != dependent.record_ref.record_kind
            or stored.record.contract_version
            != dependent.record_ref.contract_version
            or stored.record.logical_id != dependent.record_ref.record_id
            or stored.record.class_id != dependent.work_ref.class_id
            or stored.record.work_id != dependent.work_ref.work_id
        ):
            raise WorkflowOwnershipError(
                "Dependency gate dependent does not match exact canonical identity"
            )
        return stored

    def _load_evaluation_target(
        self,
        target: Endpoint,
    ) -> StoredRecord:
        if isinstance(target, ExactPortiaWorkRef):
            return self.repository.load_work(target)
        return self.repository.load_work_record(
            target.work_ref,
            target.record_ref.record_kind,
            target.record_ref.contract_version,
            target.record_ref.record_id,
        )

    def _require_target_current_use_not_quarantined(
        self,
        target: Endpoint,
        stored: StoredRecord,
    ) -> None:
        if isinstance(target, ExactPortiaWorkRef):
            self.quarantine.require_allowed(work_target(target), "block_current_use")
            return
        self.quarantine.require_allowed(
            work_target(target.work_ref),
            "block_current_use",
        )
        self.quarantine.require_allowed(
            record_target(target.work_ref, stored.record),
            "block_current_use",
        )

    @staticmethod
    def _target_policy_supported(target: Endpoint) -> bool:
        if isinstance(target, ExactPortiaWorkRef):
            return (target.work_kind, target.contract_version) in _CURRENT_WORKS
        return (
            (target.work_ref.work_kind, target.work_ref.contract_version)
            in _CURRENT_WORKS
            and (
                target.record_ref.record_kind,
                target.record_ref.contract_version,
            )
            in _SUPPORTED_PORTIA_RECORD_TARGETS
        )

    def _target_status_condition(
        self,
        status: object,
    ) -> tuple[str, str]:
        if not isinstance(status, str):
            return ("indeterminate", "target_lifecycle_status_missing")
        if status in _TARGET_SATISFIED_STATUSES:
            return ("satisfied", "target_status_satisfies_initial_policy")
        if status in _TARGET_REVIEW_STATUSES:
            return ("review_required", "target_status_requires_review")
        if status in _TARGET_UNSATISFIED_STATUSES:
            return ("unsatisfied", "target_status_is_ineligible")
        return ("indeterminate", "target_status_policy_unavailable")

    def evaluate_condition(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        gate: str,
        evaluated_at: str | None = None,
    ) -> DependencyConditionEvaluation:
        """Derive one declared Dependency condition without mutating canonical state."""
        if gate not in _DEPENDENCY_GATES:
            raise WorkflowPrerequisiteError(
                f"unsupported Dependency gate {gate!r}"
            )
        selected_time = self._evaluation_time(
            evaluated_at,
            description="gate evaluation",
        )
        stored_dependency = self.load_exact(reference)
        dependency = stored_dependency.record
        dependent_resolution = self._dependent_endpoint(
            reference.work_ref,
            dependency,
            require_resolution=False,
        )
        dependent = cast(Endpoint, dependent_resolution.reference)
        try:
            self._require_evaluation_dependent(dependent)
        except PortiaNotFoundError:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="exact_dependent_missing",
                evaluated_at=evaluated_at,
            )
        except (PortiaCorruptionError, PortiaRecoveryRequiredError):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="exact_dependent_state_unavailable",
                evaluated_at=evaluated_at,
            )
        applies_to = dependency.field("applies_to")
        if dependency.status != "active":
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="not_currently_evaluated",
                reason="declaration_not_active",
                evaluated_at=evaluated_at,
            )
        if applies_to != gate:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="not_currently_evaluated",
                reason="scope_not_selected",
                evaluated_at=evaluated_at,
            )
        try:
            lifecycle = require_dependency_lifecycle_reconciled(
                self.repository,
                reference.work_ref,
                dependency,
            )
        except (WorkflowOwnershipError, WorkflowPrerequisiteError):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="declaration_lifecycle_unreconciled",
                evaluated_at=evaluated_at,
            )

        if gate in {"activation", "completion"} and selected_time is None:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="exact_temporal_context_required",
                evaluated_at=evaluated_at,
            )
        if selected_time is not None:
            created_at = self._evaluation_time(
                dependency.field("created_at"),
                description="declaration created_at",
            )
            if created_at is None:
                return self._condition(
                    reference,
                    dependent,
                    dependency,
                    condition="indeterminate",
                    reason="declaration_created_at_missing",
                    evaluated_at=evaluated_at,
                )
            if selected_time < created_at:
                return self._condition(
                    reference,
                    dependent,
                    dependency,
                    condition="not_currently_evaluated",
                    reason="declaration_not_yet_created",
                    evaluated_at=evaluated_at,
                )
            if lifecycle.head is not None:
                active_effective = lifecycle.head.record.field("effective_at")
                if lifecycle.head.record.field("to_status") == "active":
                    active_time = self._evaluation_time(
                        active_effective,
                        description="declaration activation effective_at",
                    )
                    if active_time is None:
                        return self._condition(
                            reference,
                            dependent,
                            dependency,
                            condition="indeterminate",
                            reason="declaration_activation_time_missing",
                            evaluated_at=evaluated_at,
                        )
                    if selected_time < active_time:
                        return self._condition(
                            reference,
                            dependent,
                            dependency,
                            condition="not_currently_evaluated",
                            reason="declaration_not_yet_effective",
                            evaluated_at=evaluated_at,
                        )

        target_resolution = self._dependency_endpoint(
            dependency,
            require_resolution=False,
        )
        if target_resolution.kind == "module_record":
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="external_module_semantics_unavailable",
                evaluated_at=evaluated_at,
            )
        target = cast(Endpoint, target_resolution.reference)
        if not self._target_policy_supported(target):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="target_contract_policy_unavailable",
                evaluated_at=evaluated_at,
            )
        try:
            target_stored = self._load_evaluation_target(target)
        except PortiaNotFoundError:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="unsatisfied",
                reason="exact_target_missing",
                evaluated_at=evaluated_at,
            )
        except (PortiaCorruptionError, PortiaRecoveryRequiredError):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="exact_target_state_unavailable",
                evaluated_at=evaluated_at,
            )

        if selected_time is not None:
            target_created = self._evaluation_time(
                target_stored.record.field("created_at"),
                description="target created_at",
            )
            target_updated = self._evaluation_time(
                target_stored.record.field("updated_at"),
                description="target updated_at",
            )
            if target_created is None or target_updated is None:
                return self._condition(
                    reference,
                    dependent,
                    dependency,
                    condition="indeterminate",
                    reason="target_temporal_state_incomplete",
                    evaluated_at=evaluated_at,
                )
            if selected_time < target_created:
                return self._condition(
                    reference,
                    dependent,
                    dependency,
                    condition="unsatisfied",
                    reason="target_not_yet_created",
                    evaluated_at=evaluated_at,
                )
            if selected_time < target_updated:
                return self._condition(
                    reference,
                    dependent,
                    dependency,
                    condition="indeterminate",
                    reason="target_revision_postdates_evaluation",
                    evaluated_at=evaluated_at,
                )

        try:
            self._require_target_history_reconciled(target, target_stored)
        except (WorkflowOwnershipError, WorkflowPrerequisiteError):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="target_lifecycle_unreconciled",
                evaluated_at=evaluated_at,
            )
        try:
            self._require_target_current_use_not_quarantined(target, target_stored)
        except PortiaQuarantinedError:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="review_required",
                reason="target_quarantined",
                evaluated_at=evaluated_at,
            )
        except PortiaRecoveryRequiredError:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="target_quarantine_state_unavailable",
                evaluated_at=evaluated_at,
            )

        try:
            target_disputed = self._target_has_active_disagreement(target)
        except (PortiaCorruptionError, PortiaRecoveryRequiredError):
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="indeterminate",
                reason="target_disagreement_state_unavailable",
                evaluated_at=evaluated_at,
            )
        if target_disputed:
            return self._condition(
                reference,
                dependent,
                dependency,
                condition="review_required",
                reason="target_has_active_disagreement",
                evaluated_at=evaluated_at,
            )
        condition, reason = self._target_status_condition(target_stored.record.status)
        return self._condition(
            reference,
            dependent,
            dependency,
            condition=condition,
            reason=reason,
            evaluated_at=evaluated_at,
        )

    def evaluate_gate(
        self,
        dependent: Endpoint,
        *,
        gate: str,
        evaluated_at: str | None = None,
    ) -> DependencyGateEvaluation:
        """Aggregate active declared conditions for one exact dependent and gate."""
        if gate not in _DEPENDENCY_GATES:
            raise WorkflowPrerequisiteError(
                f"unsupported Dependency gate {gate!r}"
            )
        self._evaluation_time(evaluated_at, description="gate evaluation")
        self._require_evaluation_dependent(dependent)
        evaluations: list[DependencyConditionEvaluation] = []
        owner = (
            dependent
            if isinstance(dependent, ExactPortiaWorkRef)
            else dependent.work_ref
        )
        for stored in self.list_for_dependent(dependent):
            identifier = stored.record.logical_id
            if not isinstance(identifier, str):
                raise WorkflowOwnershipError(
                    "Dependency gate evaluation encountered a declaration without "
                    "exact canonical identity"
                )
            evaluations.append(
                self.evaluate_condition(
                    dependency_reference(owner, identifier),
                    gate=gate,
                    evaluated_at=evaluated_at,
                )
            )
        values = tuple(evaluations)
        required_blockers = tuple(
            evaluation.reference.record_ref.record_id
            for evaluation in values
            if evaluation.strength == "required"
            and evaluation.condition in _GATE_BLOCKING_CONDITIONS
        )
        advisory_attention = tuple(
            evaluation.reference.record_ref.record_id
            for evaluation in values
            if evaluation.strength == "advisory"
            and evaluation.condition in _GATE_BLOCKING_CONDITIONS
        )
        return DependencyGateEvaluation(
            dependent=dependent,
            gate=gate,
            evaluated_at=evaluated_at,
            conditions=values,
            required_blockers=required_blockers,
            advisory_attention=advisory_attention,
        )

    def _bounded_work_scope(
        self,
        works: Sequence[ExactPortiaWorkRef],
    ) -> tuple[ExactPortiaWorkRef, ...]:
        values = tuple(works)
        if not values:
            raise WorkflowPrerequisiteError(
                "Dependency graph/search scope requires at least one exact work"
            )
        if len(values) > 64:
            raise WorkflowPrerequisiteError(
                "Dependency graph/search scope exceeds the 64-work bound"
            )
        if len(set(values)) != len(values):
            raise WorkflowPrerequisiteError(
                "Dependency graph/search scope repeats an exact work"
            )
        for work in values:
            _require_current_work(work)
            self.repository.load_work(work)
        return values

    def require_graph_valid(
        self,
        search_works: Sequence[ExactPortiaWorkRef],
    ) -> DependencyGraphResolution:
        """Require an acyclic, nonduplicated live graph over an explicit closure."""
        works = self._bounded_work_scope(search_works)
        work_keys = {
            (work.class_id, work.work_id, work.work_kind, work.contract_version)
            for work in works
        }
        owned_dependencies = tuple(
            (work, item)
            for work in works
            for item in self.list(work)
        )
        dependencies = tuple(item for _work, item in owned_dependencies)

        edges: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
        active_conditions: dict[
            tuple[tuple[str, ...], tuple[str, ...], str, str, str],
            str,
        ] = {}
        live_edge_count = 0

        for owner, stored in owned_dependencies:
            record = stored.record
            if record.status not in _LIVE_GRAPH_STATUSES:
                continue
            dependent_resolution = self._dependent_endpoint(
                owner,
                record,
                require_resolution=True,
            )
            dependent = cast(Endpoint, dependent_resolution.reference)
            target_resolution = self._dependency_endpoint(
                record,
                require_resolution=False,
            )
            if target_resolution.kind == "module_record":
                continue
            target = cast(Endpoint, target_resolution.reference)
            target_work = (
                target if isinstance(target, ExactPortiaWorkRef) else target.work_ref
            )
            target_work_key = (
                target_work.class_id,
                target_work.work_id,
                target_work.work_kind,
                target_work.contract_version,
            )
            target_is_current_owner = (
                target_work.work_kind,
                target_work.contract_version,
            ) in _CURRENT_WORKS
            if target_is_current_owner and target_work_key not in work_keys:
                raise WorkflowPrerequisiteError(
                    "Dependency graph scope is incomplete for an exact Portia target; "
                    "supply the referenced work explicitly"
                )
            dependent_key = _endpoint_key(dependent)
            target_key = _endpoint_key(target)
            if dependent_key == target_key:
                raise WorkflowPrerequisiteError("Dependency graph contains self-dependency")
            edges.setdefault(dependent_key, set()).add(target_key)
            live_edge_count += 1

            if record.status == "active":
                strength = record.field("strength")
                applies_to = record.field("applies_to")
                purpose = record.field("purpose")
                if not all(
                    isinstance(value, str)
                    for value in (strength, applies_to, purpose)
                ):
                    raise WorkflowOwnershipError(
                        "Dependency condition classification is malformed"
                    )
                signature = (
                    dependent_key,
                    target_key,
                    cast(str, strength),
                    cast(str, applies_to),
                    cast(str, purpose),
                )
                identifier = record.logical_id
                if identifier is None:
                    raise WorkflowOwnershipError(
                        "Dependency record has no canonical identity"
                    )
                previous = active_conditions.get(signature)
                if previous is not None:
                    raise WorkflowPrerequisiteError(
                        "Dependency graph contains duplicate active semantic "
                        f"declarations {previous!r} and {identifier!r}"
                    )
                active_conditions[signature] = identifier

        visiting: set[tuple[str, ...]] = set()
        visited: set[tuple[str, ...]] = set()

        def visit(node: tuple[str, ...]) -> None:
            if node in visiting:
                raise WorkflowPrerequisiteError("Dependency graph contains a cycle")
            if node in visited:
                return
            visiting.add(node)
            for target in edges.get(node, set()):
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for node in tuple(edges):
            visit(node)

        return DependencyGraphResolution(
            works=works,
            dependencies=dependencies,
            live_edge_count=live_edge_count,
        )
