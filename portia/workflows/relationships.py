"""Explicit exact ``draws_context_from`` Work Relationship workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from portia.models import PortiaRecord, WorkRelationshipV2
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.repository import StoredRecord
from portia.workflows.common import (
    CHILD_STATUS_TRANSITIONS,
    RELATIONSHIP_VERSION,
    WorkflowServiceBase,
    record_target,
    require_current_status,
    require_revision_invariants,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


@dataclass(frozen=True, slots=True)
class RelationshipEndpointResolution:
    relationship: StoredRecord
    source: StoredRecord
    target: StoredRecord


def relationship_reference(
    work: ExactPortiaWorkRef,
    relationship_id: str,
    *,
    version: str = RELATIONSHIP_VERSION,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="work_relationship",
            record_id=relationship_id,
            contract_version=version,
        ),
    )


def _endpoint(record: PortiaRecord, field: str) -> ExactPortiaWorkRef:
    value = record.field(field)
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"Work Relationship {field} is malformed")
    try:
        return ExactPortiaWorkRef.from_dict(value)
    except Exception as exc:
        raise WorkflowOwnershipError(
            f"Work Relationship {field} is not an exact Portia work reference"
        ) from exc


class WorkRelationshipService(WorkflowServiceBase):
    """Manage explicit relationships without inference or endpoint mutation."""

    @staticmethod
    def _require_endpoint_eligibility(
        endpoint: PortiaRecord,
        reference: ExactPortiaWorkRef,
        *,
        position: str,
    ) -> None:
        if reference.work_kind == "event":
            allowed = (
                {"draft", "active", "closed"}
                if position == "source"
                else {"active", "closed"}
            )
        elif reference.work_kind == "support_process" and position == "source":
            allowed = {"proposed", "active"}
        else:
            allowed = set()
        if endpoint.status not in allowed:
            accepted = ", ".join(sorted(allowed)) or "none"
            raise WorkflowPrerequisiteError(
                f"{position} {reference.work_kind} status is not usable for an active "
                f"Work Relationship; accepted statuses: {accepted}"
            )

    def _require_write_input(
        self, record: PortiaRecord
    ) -> tuple[WorkRelationshipV2, ExactPortiaWorkRef, ExactPortiaWorkRef]:
        if not isinstance(record, WorkRelationshipV2):
            raise WorkflowOwnershipError(
                "relationship workflow writes require work_relationship@2 input"
            )
        source = _endpoint(record, "source")
        target = _endpoint(record, "target")
        if record.class_id != source.class_id or record.work_id != source.work_id:
            raise WorkflowOwnershipError(
                "Work Relationship envelope does not agree with exact source"
            )
        if source == target:
            raise WorkflowPrerequisiteError(
                "a Work Relationship cannot draw context from itself"
            )
        return record, source, target

    def resolve_endpoints(
        self, record: PortiaRecord
    ) -> tuple[StoredRecord, StoredRecord]:
        source = _endpoint(record, "source")
        target = _endpoint(record, "target")
        return self.repository.load_work(source), self.repository.load_work(target)

    def _write_graph(
        self, candidate: PortiaRecord
    ) -> tuple[PortiaRecord, ...]:
        source, target = self.resolve_endpoints(candidate)
        return (source.record, target.record, candidate)

    def _require_no_duplicate_edge(
        self, source: ExactPortiaWorkRef, candidate: PortiaRecord
    ) -> None:
        if candidate.status != "active":
            return
        target = _endpoint(candidate, "target")
        for stored in self.repository.list_work_relationships(
            source, version=RELATIONSHIP_VERSION
        ):
            other = stored.record
            if other.logical_id == candidate.logical_id or other.status != "active":
                continue
            if _endpoint(other, "source") == source and _endpoint(other, "target") == target:
                raise WorkflowPrerequisiteError(
                    "an active draws_context_from edge already exists for these exact endpoints"
                )

    def _preflight_current(
        self,
        relationship: PortiaRecord,
        source: ExactPortiaWorkRef,
        target: ExactPortiaWorkRef,
    ) -> None:
        if relationship.status != "active":
            return
        source_record = self.repository.load_work(source)
        target_record = self.repository.load_work(target)
        self.quarantine.require_allowed(work_target(source), "block_current_use")
        self.quarantine.require_allowed(work_target(target), "block_current_use")
        self._require_endpoint_eligibility(
            source_record.record, source, position="source"
        )
        self._require_endpoint_eligibility(
            target_record.record, target, position="target"
        )
        self._require_no_duplicate_edge(source, relationship)

    def create(self, record: PortiaRecord) -> StoredRecord:
        candidate, source, target = self._require_write_input(record)
        graph = self._write_graph(candidate)
        self.validate_complete_graph(graph)
        self._preflight_current(candidate, source, target)
        self.quarantine.require_allowed(work_target(source), "block_work_writes")
        self.quarantine.require_allowed(record_target(source, candidate), "block_work_writes")
        return self.repository.create_work_record(source, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        if reference.record_ref.record_kind != "work_relationship":
            raise WorkflowOwnershipError("reference is not a Work Relationship")
        self.repository.load_work(reference.work_ref)
        stored = self.repository.load_work_record(
            reference.work_ref,
            "work_relationship",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
        if _endpoint(stored.record, "source") != reference.work_ref:
            raise WorkflowOwnershipError(
                "relationship reference does not identify its exact source work"
            )
        return stored

    def resolve_exact(
        self, reference: ExactPortiaWorkRecordRef
    ) -> RelationshipEndpointResolution:
        relationship = self.load_exact(reference)
        source, target = self.resolve_endpoints(relationship.record)
        return RelationshipEndpointResolution(relationship, source, target)

    def replace(
        self,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        candidate, source, target = self._require_write_input(record)
        if candidate.logical_id is None:
            raise WorkflowOwnershipError("Work Relationship has no exact identity")
        prior = self.load_exact(relationship_reference(source, candidate.logical_id))
        require_revision_invariants(
            prior.record,
            candidate,
            transitions=CHILD_STATUS_TRANSITIONS,
            immutable_fields=("relationship_type", "source", "target"),
        )
        graph = self._write_graph(candidate)
        self.validate_complete_graph(graph)
        self._preflight_current(candidate, source, target)
        self.quarantine.require_allowed(work_target(source), "block_work_writes")
        self.quarantine.require_allowed(record_target(source, candidate), "block_work_writes")
        return self.repository.replace_work_record(
            source, candidate, expected=expected
        )

    revise = replace

    def list(self, source: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        return self.repository.list_work_relationships(
            source, version=RELATIONSHIP_VERSION
        )

    list_relationships = list

    def require_current_use(
        self, reference: ExactPortiaWorkRecordRef
    ) -> RelationshipEndpointResolution:
        if reference.record_ref.contract_version != RELATIONSHIP_VERSION:
            raise WorkflowOwnershipError(
                "current relationship use requires work_relationship@2"
            )
        resolution = self.resolve_exact(reference)
        relationship = resolution.relationship.record
        require_current_status(relationship)
        self.quarantine.require_allowed(
            record_target(reference.work_ref, relationship), "block_current_use"
        )
        self._preflight_current(
            relationship,
            _endpoint(relationship, "source"),
            _endpoint(relationship, "target"),
        )
        return resolution

    resolve_current = require_current_use
