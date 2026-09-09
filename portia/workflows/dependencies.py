"""Exact graph and lifecycle authority for ``dependency@1`` declarations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from portia.models import DependencyV1, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    PortiaWorkRecordRef,
    PortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import WorkflowServiceBase
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
            module_id = raw_work.get("module_id")
            work_version = raw_work.get("contract_version")
            record_version = raw_record.get("contract_version")
            if module_id == "portia":
                raise WorkflowOwnershipError(
                    "Portia dependency targets must use the Portia target branch"
                )
            if not isinstance(module_id, str) or not module_id:
                raise WorkflowOwnershipError(
                    "Dependency module target lacks exact module identity"
                )
            if not isinstance(work_version, str) or not isinstance(record_version, str):
                raise WorkflowOwnershipError(
                    "Dependency module target must pin work and record contract versions"
                )
            return DependencyEndpointResolution(
                "module_record",
                dict(raw_reference),
                None,
            )
        raise WorkflowOwnershipError("Dependency target kind is unsupported")

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
