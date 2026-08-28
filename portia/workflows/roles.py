"""Optional, neutral Event Participant Role workflows."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import EventParticipantRoleV3, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaCorruptionError, PortiaNotFoundError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.repository import StoredRecord
from portia.workflows.common import (
    CHILD_STATUS_TRANSITIONS,
    EVENT_VERSION,
    ROLE_VERSION,
    WorkflowServiceBase,
    participant_id_from_target,
    record_target,
    require_current_status,
    require_owned,
    require_revision_invariants,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.participants import (
    ParticipantWorkflowService,
    participant_reference,
)

_QUALIFYING_ACCOUNT_SOURCES = frozenset(
    {"roster_student", "actor", "local_operator", "descriptive_person"}
)


def role_reference(
    work: ExactPortiaWorkRef, role_id: str, *, version: str = ROLE_VERSION
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant_role",
            record_id=role_id,
            contract_version=version,
        ),
    )


class RoleWorkflowService(WorkflowServiceBase):
    """Manage neutral Role records and their exact prerequisites."""

    def _participant(self, work: ExactPortiaWorkRef, role: PortiaRecord) -> StoredRecord:
        participant_id, version = participant_id_from_target(role)
        return self.repository.load_work_record(
            work, "event_participant", version, participant_id
        )

    def _basis_records(
        self, work: ExactPortiaWorkRef, role: PortiaRecord
    ) -> tuple[StoredRecord, ...]:
        basis = role.field("basis")
        if not isinstance(basis, tuple):
            return ()
        loaded: list[StoredRecord] = []
        for entry in basis:
            if not isinstance(entry, Mapping):
                continue
            kind = entry.get("kind")
            if kind not in {"account_ref", "observation_ref"}:
                continue
            reference = entry.get("record_ref")
            if not isinstance(reference, Mapping):
                continue
            record_kind = reference.get("record_kind")
            record_id = reference.get("record_id")
            version = reference.get("contract_version")
            if not all(isinstance(value, str) for value in (record_kind, record_id, version)):
                continue
            try:
                loaded.append(
                    self.repository.load_work_record(
                        work, str(record_kind), str(version), str(record_id)
                    )
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    f"required exact {record_kind} authority {record_id!r} is absent"
                ) from exc
            except PortiaCorruptionError as exc:
                raise WorkflowPrerequisiteError(
                    f"{record_kind} {record_id!r} does not satisfy requested contract version {version!r}"
                ) from exc
        return tuple(loaded)

    def _write_graph(
        self, work: ExactPortiaWorkRef, candidate: PortiaRecord
    ) -> tuple[PortiaRecord, ...]:
        event = self.repository.load_work(work).record
        participant = self._participant(work, candidate).record
        basis = tuple(item.record for item in self._basis_records(work, candidate))
        return (event, participant, *basis, candidate)

    def _require_write_input(
        self, work: ExactPortiaWorkRef, record: PortiaRecord
    ) -> EventParticipantRoleV3:
        if work.work_kind != "event" or work.contract_version != EVENT_VERSION:
            raise WorkflowOwnershipError("Role writes require an exact event@2 owner")
        if not isinstance(record, EventParticipantRoleV3):
            raise WorkflowOwnershipError(
                "Role workflow writes require event_participant_role@3 input"
            )
        require_owned(record, work)
        return record

    @staticmethod
    def _target_contains(account: PortiaRecord, participant_id: str, version: str) -> bool:
        target = account.field("target")
        if not isinstance(target, Mapping):
            return False

        def matches(value: object) -> bool:
            if not isinstance(value, Mapping) or value.get("kind") != "event_participant":
                return False
            ref = value.get("record_ref")
            return (
                isinstance(ref, Mapping)
                and ref.get("record_kind") == "event_participant"
                and ref.get("record_id") == participant_id
                and ref.get("contract_version") == version
            )

        if matches(target):
            return True
        targets = target.get("targets")
        return isinstance(targets, tuple) and any(matches(item) for item in targets)

    def _require_reported_involved_account(
        self, work: ExactPortiaWorkRef, role: PortiaRecord
    ) -> None:
        if role.field("role_type") != "reported_involved" or role.status != "active":
            return
        participant_id, participant_version = participant_id_from_target(role)
        accounts = tuple(
            item
            for item in self._basis_records(work, role)
            if item.record.contract == "account"
        )
        if not accounts:
            raise WorkflowPrerequisiteError(
                "active reported_involved requires an exact qualifying Account"
            )
        for stored in accounts:
            account = stored.record
            if account.status != "active":
                continue
            source = account.field("source")
            source_kind = source.get("kind") if isinstance(source, Mapping) else None
            if source_kind not in _QUALIFYING_ACCOUNT_SOURCES:
                continue
            if not self._target_contains(account, participant_id, participant_version):
                continue
            self.quarantine.require_allowed(
                record_target(work, account), "block_current_use"
            )
            return
        raise WorkflowPrerequisiteError(
            "reported_involved Account must be active, attributable, same-Event, and target-aligned"
        )

    def _require_active_compatibility(
        self, work: ExactPortiaWorkRef, candidate: PortiaRecord
    ) -> None:
        if candidate.status != "active":
            return
        participant_id, _version = participant_id_from_target(candidate)
        role_type = candidate.field("role_type")
        exclusive = {"directly_involved", "reported_involved", "contextual"}
        for stored in self.repository.list_event_participant_roles(
            work, version=ROLE_VERSION
        ):
            other = stored.record
            if other.logical_id == candidate.logical_id or other.status != "active":
                continue
            other_id, _other_version = participant_id_from_target(other)
            if other_id != participant_id:
                continue
            other_type = other.field("role_type")
            if other_type == role_type or (
                role_type in exclusive and other_type in exclusive
            ):
                raise WorkflowPrerequisiteError(
                    "active Role conflicts with an existing current Role for the Participant"
                )

    def _preflight_activation(self, work: ExactPortiaWorkRef, role: PortiaRecord) -> None:
        if role.status != "active":
            return
        event = self.repository.load_work(work)
        if event.record.status not in {"draft", "active"}:
            raise WorkflowPrerequisiteError(
                "active Role requires a draft or active parent Event"
            )
        participant_id, version = participant_id_from_target(role)
        participant_service = ParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        participant_service.require_role_eligibility(
            participant_reference(work, participant_id, version=version)
        )
        self._require_active_compatibility(work, role)
        self._require_reported_involved_account(work, role)

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        graph = self._write_graph(work, candidate)
        self._preflight_activation(work, candidate)
        self.validate_complete_graph(
            graph, require_actor_current_use=candidate.status == "active"
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, candidate), "block_work_writes")
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        if (
            reference.work_ref.work_kind != "event"
            or reference.work_ref.contract_version != EVENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Role resolution requires an exact event@2 owner"
            )
        if reference.record_ref.record_kind != "event_participant_role":
            raise WorkflowOwnershipError("reference is not an Event Participant Role")
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "event_participant_role",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def replace(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        if candidate.logical_id is None:
            raise WorkflowOwnershipError("Role has no exact identity")
        prior = self.load_exact(role_reference(work, candidate.logical_id))
        if participant_id_from_target(prior.record) != participant_id_from_target(
            candidate
        ):
            raise WorkflowOwnershipError(
                "persisted Role Participant target cannot be retargeted in place"
            )
        require_revision_invariants(
            prior.record,
            candidate,
            transitions=CHILD_STATUS_TRANSITIONS,
            immutable_fields=("target",),
        )
        if prior.record.status == "active":
            for field in ("role_type", "basis", "detail"):
                if prior.record.to_dict().get(field) != candidate.to_dict().get(field):
                    raise WorkflowPrerequisiteError(
                        f"active Role {field} correction requires a successor"
                    )
        graph = self._write_graph(work, candidate)
        self._preflight_activation(work, candidate)
        self.validate_complete_graph(
            graph, require_actor_current_use=candidate.status == "active"
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, candidate), "block_work_writes")
        return self.repository.replace_work_record(
            work, candidate, expected=expected
        )

    revise = replace

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        if work.work_kind != "event" or work.contract_version != EVENT_VERSION:
            raise WorkflowOwnershipError(
                "Role listing requires an exact event@2 owner"
            )
        return self.repository.list_event_participant_roles(work, version=ROLE_VERSION)

    list_roles = list

    def list_for_participant(
        self, work: ExactPortiaWorkRef, participant_id: str
    ) -> tuple[StoredRecord, ...]:
        selected: list[StoredRecord] = []
        for stored in self.list(work):
            target_id, _version = participant_id_from_target(stored.record)
            if target_id == participant_id:
                selected.append(stored)
        return tuple(selected)

    def require_current_use(
        self, reference: ExactPortiaWorkRecordRef
    ) -> StoredRecord:
        if reference.record_ref.contract_version != ROLE_VERSION:
            raise WorkflowOwnershipError(
                "current Role use requires event_participant_role@3"
            )
        role = self.load_exact(reference)
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, role.record), "block_current_use"
        )
        require_current_status(role.record)
        event = self.repository.load_work(reference.work_ref)
        require_current_status(event.record)
        participant_id, version = participant_id_from_target(role.record)
        participant_service = ParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        participant_service.require_current_use(
            participant_reference(reference.work_ref, participant_id, version=version)
        )
        self._require_active_compatibility(reference.work_ref, role.record)
        self._require_reported_involved_account(reference.work_ref, role.record)
        return role

    resolve_current = require_current_use
