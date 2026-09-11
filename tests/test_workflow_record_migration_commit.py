"""Focused Issue #47 Slice 22 tests for journaled work-record migration commit."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaNotFoundError,
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import guarded_replace
from portia.storage.migration_representations import MigrationRepresentationStore
from portia.storage.paths import work_record_path
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    DependencyWorkflowService,
    MigrationTransformContext,
    RecordMigrationWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_wire,
)

EFFECTIVE_AT = "2026-08-26T12:05:00-04:00"
CREATED_AT = "2026-08-26T12:06:00-04:00"
MIGRATION_ID = "mig_participant_slice22"
TRANSITION_ID = "lct_participant_slice22"
OPERATION_ID = "op_participant_migration_slice22"


def _participant_v2(*, status: str = "active") -> PortiaRecord:
    value = participant_wire(status=status)
    value["schema_version"] = "2"
    return parse_portia_record("event_participant", "2", value)


def _participant_ref(version: str) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version=version,
        ),
    )


def _participant_transform(
    source: PortiaRecord,
    context: MigrationTransformContext,
) -> PortiaRecord:
    assert isinstance(context.source_reference, ExactPortiaWorkRecordRef)
    value = source.to_dict()
    value["schema_version"] = "3"
    value["creation_source"] = {"type": "digital_entry"}
    value["created_at"] = context.effective_at
    value["created_by"] = dict(context.created_by)
    value["updated_at"] = context.effective_at
    value["updated_by"] = dict(context.created_by)
    value["supersedes"] = [
        {
            "work_record_ref": context.source_reference.to_dict(),
            "reason": "contract_migrated",
        }
    ]
    return parse_portia_record("event_participant", "3", value)


def _equivalent(source: PortiaRecord, destination: PortiaRecord) -> bool:
    return (
        source.logical_id == destination.logical_id
        and source.class_id == destination.class_id
        and source.work_id == destination.work_id
        and source.status == destination.status
        and source.field("subject") == destination.field("subject")
    )


def _service(
    tmp_path: Path,
    *,
    repository: PortiaRepository | None = None,
) -> RecordMigrationWorkflowService:
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    service.register_transformer(
        contract="event_participant",
        source_version="2",
        destination_version="3",
        transformer_id="event_participant_v2_to_v3",
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="event_participant_v2_to_v3",
        transform=_participant_transform,
        semantic_equivalence=_equivalent,
    )
    return service


def _setup(
    tmp_path: Path,
) -> tuple[PortiaRepository, RecordMigrationWorkflowService]:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), _participant_v2())
    return repository, _service(tmp_path, repository=repository)


def _plan(service: RecordMigrationWorkflowService):
    return service.plan_migration(
        _participant_ref("2"),
        "3",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )


def _commit(
    service: RecordMigrationWorkflowService,
    plan,
    *,
    operation_id: str = OPERATION_ID,
    fault_hook=None,
):
    return service.commit_migration(
        plan,
        migration_id=MIGRATION_ID,
        transition_id=TRANSITION_ID,
        created_at=CREATED_AT,
        operation_id=operation_id,
        fault_hook=fault_hook,
    )


def test_commit_work_record_migration_reconciles_all_canonical_components(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)

    result = _commit(service, plan)

    assert result.operation_id == OPERATION_ID
    assert result.accepted_steps == (
        "step_source_history",
        "step_destination",
        "step_certificate",
        "step_transition",
        "step_source_superseded",
        "step_source_version",
        "step_current_switch",
    )

    current = repository.load_work_record(
        event_ref(),
        "event_participant",
        "3",
        "ep_alpha",
    )
    assert current.record.to_dict() == plan.destination.to_dict()

    store = MigrationRepresentationStore(tmp_path, repository=repository)
    source = store.load_preserved_work_record_representation(_participant_ref("2"))
    destination = store.load_preserved_work_record_representation(
        _participant_ref("3")
    )
    assert source.record.status == "superseded"
    assert source.record.field("updated_at") == TIMESTAMP
    assert source.record.field("updated_by") == plan.source.record.field("updated_by")
    assert destination.record.to_dict() == plan.destination.to_dict()

    certificate = repository.load_work_record(
        event_ref(),
        "record_migration",
        "1",
        MIGRATION_ID,
    ).record
    assert certificate.field("source") == {
        "kind": "work_record",
        "work_record_ref": _participant_ref("2").to_dict(),
        "observed_updated_at": TIMESTAMP,
    }
    assert certificate.field("destination") == {
        "kind": "work_record",
        "work_record_ref": _participant_ref("3").to_dict(),
        "observed_updated_at": EFFECTIVE_AT,
    }
    assert certificate.field("effective_at") == EFFECTIVE_AT

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        TRANSITION_ID,
    ).record
    assert transition.field("previous_transition") is None
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason") == {
        "category": "migration",
        "code": "event_participant_v2_to_v3",
    }
    assert transition.field("effective_at") == EFFECTIVE_AT

    journal = OperationJournalStore(tmp_path).load_current(OPERATION_ID).revision
    assert journal.field("operation_kind") == "migrate_representation"
    assert journal.field("state") == "completed"


def test_commit_preserves_pre_migration_source_in_technical_storage_history(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)
    original = plan.source

    _commit(service, plan)

    history = (
        tmp_path
        / "classes"
        / event_ref().class_id
        / "modules"
        / "portia"
        / "work"
        / event_ref().work_id
        / "history"
        / "storage_revisions"
        / "event_participant"
        / "ep_alpha"
        / f"{original.fingerprint.digest}.json"
    )
    assert history.read_bytes()
    historical = parse_portia_record(
        "event_participant",
        "2",
        json.loads(history.read_text(encoding="utf-8")),
    )
    assert historical.status == "active"


def test_completed_migration_operation_replays_idempotently(tmp_path: Path) -> None:
    _repository, service = _setup(tmp_path)
    plan = _plan(service)
    first = _commit(service, plan)

    second = _commit(service, plan)

    assert second.operation_id == first.operation_id
    assert second.accepted_steps == first.accepted_steps




def test_completed_replay_rejects_changed_final_current_representation(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)
    _commit(service, plan)

    current = repository.load_work_record(
        event_ref(),
        "event_participant",
        "3",
        "ep_alpha",
    )
    wire = current.record.to_dict()
    wire["updated_at"] = "2026-08-26T12:07:00-04:00"
    wire["updated_by"] = AGENT
    altered = parse_portia_record("event_participant", "3", wire)
    guarded_replace(
        work_record_path(
            tmp_path,
            event_ref(),
            "event_participant",
            "ep_alpha",
        ),
        canonical_json_bytes(altered.to_dict()),
        expected=current.fingerprint,
    )

    with pytest.raises(
        PortiaRecoveryRequiredError,
        match="step_current_switch",
    ):
        _commit(service, plan)


def test_completed_operation_id_rejects_different_migration_intent(
    tmp_path: Path,
) -> None:
    _repository, service = _setup(tmp_path)
    plan = _plan(service)
    _commit(service, plan)

    with pytest.raises(PortiaConflictError, match="different intent"):
        service.commit_migration(
            plan,
            migration_id="mig_participant_other_slice22",
            transition_id=TRANSITION_ID,
            created_at=CREATED_AT,
            operation_id=OPERATION_ID,
        )


def test_commit_rejects_work_root_plan_in_slice22(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    source = event_record()
    value = source.to_dict()
    value["schema_version"] = "1"
    repository.create_work(
        event_ref(version="1"),
        parse_portia_record("event", "1", value),
    )

    def transform(
        old: PortiaRecord,
        context: MigrationTransformContext,
    ) -> PortiaRecord:
        wire = old.to_dict()
        wire["schema_version"] = "2"
        wire["creation_source"] = {"type": "digital_entry"}
        wire["created_at"] = context.effective_at
        wire["created_by"] = dict(context.created_by)
        wire["updated_at"] = context.effective_at
        wire["updated_by"] = dict(context.created_by)
        wire["supersedes"] = [context.source_reference.to_dict()]
        return parse_portia_record("event", "2", wire)

    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    service.register_transformer(
        contract="event",
        source_version="1",
        destination_version="2",
        transformer_id="event_v1_to_v2",
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="event_v1_to_v2",
        transform=transform,
        semantic_equivalence=lambda old, new: (
            old.logical_id == new.logical_id and old.status == new.status
        ),
    )
    plan = service.plan_migration(
        event_ref(version="1"),
        "2",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )

    with pytest.raises(WorkflowOwnershipError, match="work-record migrations only"):
        service.commit_migration(
            plan,
            migration_id="mig_event_slice22",
            transition_id="lct_event_slice22",
            created_at=CREATED_AT,
            operation_id="op_event_slice22",
        )


def test_commit_rejects_source_changed_after_planning(tmp_path: Path) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)
    current = repository.load_work_record(
        event_ref(),
        "event_participant",
        "2",
        "ep_alpha",
    )
    wire = current.record.to_dict()
    wire["updated_at"] = "2026-08-26T12:04:00-04:00"
    wire["updated_by"] = AGENT
    guarded_replace(
        work_record_path(
            tmp_path,
            event_ref(),
            "event_participant",
            "ep_alpha",
        ),
        canonical_json_bytes(
            parse_portia_record("event_participant", "2", wire).to_dict()
        ),
        expected=current.fingerprint,
    )

    with pytest.raises((PortiaConflictError, WorkflowPrerequisiteError)):
        _commit(service, plan)


def test_commit_rejects_existing_lifecycle_history(tmp_path: Path) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)
    transition = parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": event_ref().class_id,
            "work_id": event_ref().work_id,
            "transition_id": "lct_prior_slice22",
            "target": {
                "kind": "local_record",
                "record_ref": _participant_ref("2").record_ref.to_dict(),
            },
            "previous_transition": None,
            "from_status": "proposed",
            "to_status": "active",
            "reason": {
                "category": "workflow",
                "code": "activation_confirmed",
            },
            "effective_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), transition)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="creation-baseline lifecycle branch",
    ):
        _commit(service, plan)


def test_required_unsatisfied_current_use_dependency_blocks_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)
    condition = SimpleNamespace(
        reference=SimpleNamespace(
            record_ref=SimpleNamespace(record_id="dep_block_slice22")
        ),
        strength="required",
        condition="unsatisfied",
    )
    gate = SimpleNamespace(
        conditions=(condition,),
        required_gate_satisfied=False,
        required_blockers=("dep_block_slice22",),
    )

    def fake_gate(
        _self,
        _dependent,
        *,
        gate: str,
        evaluated_at: str | None = None,
    ):
        assert gate == "current_use"
        assert evaluated_at == EFFECTIVE_AT
        return gate_result

    gate_result = gate
    monkeypatch.setattr(DependencyWorkflowService, "evaluate_gate", fake_gate)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Dependency current-use lifecycle-write gate",
    ):
        _commit(service, plan)

    current = repository.load_work_record(
        event_ref(),
        "event_participant",
        "2",
        "ep_alpha",
    )
    assert current.record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        OperationJournalStore(tmp_path).load_current(OPERATION_ID)


@pytest.mark.parametrize("condition_value", ["review_required", "indeterminate"])
def test_required_review_or_indeterminate_dependency_does_not_block_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition_value: str,
) -> None:
    _repository, service = _setup(tmp_path)
    plan = _plan(service)
    condition = SimpleNamespace(
        reference=SimpleNamespace(
            record_ref=SimpleNamespace(record_id="dep_review_slice22")
        ),
        strength="required",
        condition=condition_value,
    )
    gate_result = SimpleNamespace(
        conditions=(condition,),
        required_gate_satisfied=False,
        required_blockers=("dep_review_slice22",),
    )

    monkeypatch.setattr(
        DependencyWorkflowService,
        "evaluate_gate",
        lambda _self, _dependent, *, gate, evaluated_at=None: gate_result,
    )

    result = _commit(service, plan)
    assert result.operation_id == OPERATION_ID


def test_partial_commit_records_failed_journal_without_retiring_source(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)

    def fail_before_certificate(event: str, step_id: str | None) -> None:
        if event == "before_publish" and step_id == "step_certificate":
            raise RuntimeError("slice22 synthetic interruption")

    with pytest.raises(PortiaOperationPartialCommitError):
        _commit(service, plan, fault_hook=fail_before_certificate)

    current = repository.load_work_record(
        event_ref(),
        "event_participant",
        "2",
        "ep_alpha",
    )
    assert current.record.status == "active"

    destination = MigrationRepresentationStore(
        tmp_path,
        repository=repository,
    ).load_preserved_work_record_representation(_participant_ref("3"))
    assert destination.record.to_dict() == plan.destination.to_dict()

    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            event_ref(),
            "record_migration",
            "1",
            MIGRATION_ID,
        )

    journal = OperationJournalStore(tmp_path).load_current(OPERATION_ID).revision
    assert journal.field("state") == "failed"

    with pytest.raises(PortiaRecoveryRequiredError):
        _commit(service, plan)
