"""Production application service for neutral ``event@2`` records."""

from __future__ import annotations

from portia.models import EventV2, PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.repository import StoredRecord
from portia.workflows.common import (
    EVENT_STATUS_TRANSITIONS,
    EVENT_VERSION,
    PARTICIPANT_VERSION,
    WorkflowServiceBase,
    require_current_status,
    require_revision_invariants,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


def event_reference(record: PortiaRecord) -> ExactPortiaWorkRef:
    if not isinstance(record, EventV2) or record.class_id is None or record.work_id is None:
        raise WorkflowOwnershipError("Event workflow writes require event@2 input")
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version=EVENT_VERSION,
    )


class EventWorkflowService(WorkflowServiceBase):
    """Create, revise, enumerate, and resolve exact Event representations."""

    def create(self, record: PortiaRecord) -> StoredRecord:
        work = event_reference(record)
        if record.status in {"active", "closed"}:
            raise WorkflowPrerequisiteError(
                "standalone Event creation cannot satisfy the minimum active Participant requirement"
            )
        self.validate_complete_graph((record,))
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        return self.repository.create_work(work, record)

    def load_exact(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if work.work_kind != "event":
            raise WorkflowOwnershipError("Event load requires an exact Event work reference")
        return self.repository.load_work(work)

    def resolve_exact(self, work: ExactPortiaWorkRef) -> StoredRecord:
        """Resolve exactly the requested version without successor following."""
        return self.load_exact(work)

    def replace(
        self,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        work = event_reference(record)
        prior = self.repository.load_work(work)
        require_revision_invariants(
            prior.record,
            record,
            transitions=EVENT_STATUS_TRANSITIONS,
        )
        participants = self.repository.list_event_participants(
            work, version=PARTICIPANT_VERSION
        )
        active_participants = tuple(
            item.record for item in participants if item.record.status == "active"
        )
        if record.status in {"active", "closed"} and not active_participants:
            raise WorkflowPrerequisiteError(
                f"{record.status} Event requires at least one valid active Participant"
            )
        graph = (record, *active_participants)
        self.validate_complete_graph(
            graph,
            require_actor_current_use=record.status == "active",
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        return self.repository.replace_work(work, record, expected=expected)

    revise = replace

    def list(self, class_id: str) -> tuple[StoredRecord, ...]:
        return self.repository.list_events(class_id, version=EVENT_VERSION)

    list_events = list

    def require_current_use(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if work.contract_version != EVENT_VERSION:
            raise WorkflowOwnershipError("current Event use requires event@2")
        stored = self.load_exact(work)
        self.quarantine.require_allowed(work_target(work), "block_current_use")
        require_current_status(stored.record)
        return stored

    resolve_current = require_current_use
