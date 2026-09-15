"""Focused Issue #47 Slice 23 tests for selected-history migration commit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRecordRef
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    LifecycleWorkflowService,
    MigrationTransformContext,
    RecordMigrationWorkflowService,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import AGENT, event_record, event_ref

HISTORY_AT = "2026-08-08T09:00:00-04:00"
HISTORY_LATER = "2026-08-08T09:05:00-04:00"
CORRECTION_AT = "2026-08-08T09:10:00-04:00"
EFFECTIVE_AT = "2026-08-26T12:05:00-04:00"
CREATED_AT = "2026-08-26T12:06:00-04:00"


def _account_v1() -> PortiaRecord:
    fixture = Path(
        "tests/schema_validation/fixtures/issue-15/account/valid/minimum-active.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    value["target"] = {"kind": "event"}
    value["source"] = {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    }
    return parse_portia_record("account", "1", value)


def _account_ref(version: str) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind="account",
            record_id="acct_student_report_1",
            contract_version=version,
        ),
    )


def _account_transform(
    source: PortiaRecord,
    context: MigrationTransformContext,
) -> PortiaRecord:
    assert isinstance(context.source_reference, ExactPortiaWorkRecordRef)
    value = source.to_dict()
    value["schema_version"] = "2"
    value["work_kind"] = "event"
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
    return parse_portia_record("account", "2", value)


def _equivalent(source: PortiaRecord, destination: PortiaRecord) -> bool:
    return (
        source.logical_id == destination.logical_id
        and source.class_id == destination.class_id
        and source.work_id == destination.work_id
        and source.status == destination.status
        and source.field("target") == destination.field("target")
        and source.field("source") == destination.field("source")
        and source.field("information_origin")
        == destination.field("information_origin")
        and source.field("source_certainty") == destination.field("source_certainty")
        and source.field("content") == destination.field("content")
        and source.field("provided_time") == destination.field("provided_time")
    )


def _service(
    root: Path,
    *,
    repository: PortiaRepository,
) -> RecordMigrationWorkflowService:
    service = RecordMigrationWorkflowService(root, repository=repository)
    service.register_transformer(
        contract="account",
        source_version="1",
        destination_version="2",
        transformer_id="account_v1_to_v2",
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="contract_migrated",
        transform=_account_transform,
        semantic_equivalence=_equivalent,
    )
    return service


def _setup(
    tmp_path: Path,
) -> tuple[PortiaRepository, RecordMigrationWorkflowService]:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), _account_v1())
    return repository, _service(tmp_path, repository=repository)


def _transition(
    transition_id: str,
    *,
    previous: str | None = None,
    from_status: str = "proposed",
    to_status: str = "active",
    effective_at: str = HISTORY_AT,
    reason_category: str = "workflow",
    reason_code: str = "review_completed",
) -> PortiaRecord:
    return parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": event_ref().class_id,
            "work_id": event_ref().work_id,
            "transition_id": transition_id,
            "target": {
                "kind": "local_record",
                "record_ref": _account_ref("1").record_ref.to_dict(),
            },
            "previous_transition": (
                None
                if previous is None
                else {
                    "record_kind": "lifecycle_transition",
                    "record_id": previous,
                    "contract_version": "1",
                }
            ),
            "from_status": from_status,
            "to_status": to_status,
            "reason": {
                "category": reason_category,
                "code": reason_code,
            },
            "effective_at": effective_at,
            "creation_source": {"type": "digital_entry"},
            "created_at": effective_at,
            "created_by": AGENT,
        },
    )


def _correction(
    *,
    replaced: str,
    replacement: str,
) -> PortiaRecord:
    return parse_portia_record(
        "lifecycle_history_correction",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_history_correction",
            "module_id": "portia",
            "class_id": event_ref().class_id,
            "work_id": event_ref().work_id,
            "correction_id": "lhc_account_reason_slice23",
            "target": {
                "kind": "local_record",
                "record_ref": _account_ref("1").record_ref.to_dict(),
            },
            "previous_correction": None,
            "replaced_head": {
                "record_kind": "lifecycle_transition",
                "record_id": replaced,
                "contract_version": "1",
            },
            "replacement_head": {
                "record_kind": "lifecycle_transition",
                "record_id": replacement,
                "contract_version": "1",
            },
            "reason": {"code": "wrong_reason"},
            "creation_source": {"type": "digital_entry"},
            "created_at": CORRECTION_AT,
            "created_by": AGENT,
        },
    )


def _plan(service: RecordMigrationWorkflowService):
    return service.plan_migration(
        _account_ref("1"),
        "2",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )


def _commit(
    service: RecordMigrationWorkflowService,
    plan,
    *,
    transition_id: str,
    operation_id: str,
    fault_hook=None,
):
    return service.commit_migration(
        plan,
        migration_id=f"mig_{transition_id[4:]}",
        transition_id=transition_id,
        created_at=CREATED_AT,
        operation_id=operation_id,
        fault_hook=fault_hook,
    )


def test_commit_appends_migration_to_existing_selected_lifecycle_head(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    repository.create_work_record(
        event_ref(),
        _transition("lct_account_activate_slice23"),
    )
    plan = _plan(service)

    _commit(
        service,
        plan,
        transition_id="lct_account_migrate_slice23",
        operation_id="op_account_migrate_slice23",
    )

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_account_migrate_slice23",
    ).record
    assert transition.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_account_activate_slice23",
        "contract_version": "1",
    }
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"

    destination_history = LifecycleWorkflowService(
        tmp_path,
        repository=repository,
    ).load_history(_account_ref("2"))
    assert destination_history.canonical_status == "active"
    assert destination_history.transitions == ()
    assert destination_history.head is None


def test_commit_uses_corrected_selected_head_not_replaced_branch(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    repository.create_work_record(
        event_ref(),
        _transition(
            "lct_account_old_slice23",
            reason_code="activation_confirmed",
        ),
    )
    repository.create_work_record(
        event_ref(),
        _transition(
            "lct_account_replacement_slice23",
            reason_code="review_completed",
        ),
    )
    repository.create_work_record(
        event_ref(),
        _correction(
            replaced="lct_account_old_slice23",
            replacement="lct_account_replacement_slice23",
        ),
    )

    selected = LifecycleWorkflowService(
        tmp_path,
        repository=repository,
    ).require_corrected_history_reconciled(_account_ref("1"))
    assert selected.selected_head is not None
    assert selected.selected_head.record.logical_id == "lct_account_replacement_slice23"
    assert "lct_account_old_slice23" in selected.excluded_transition_ids

    plan = _plan(service)
    _commit(
        service,
        plan,
        transition_id="lct_account_corrected_migrate_slice23",
        operation_id="op_account_corrected_migrate_slice23",
    )

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_account_corrected_migrate_slice23",
    ).record
    assert transition.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_account_replacement_slice23",
        "contract_version": "1",
    }
    assert transition.field("previous_transition") != {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_account_old_slice23",
        "contract_version": "1",
    }

    destination_history = LifecycleWorkflowService(
        tmp_path,
        repository=repository,
    ).load_history(_account_ref("2"))
    assert destination_history.transitions == ()


def test_commit_rejects_selected_history_change_before_work_lock(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    repository.create_work_record(
        event_ref(),
        _transition("lct_account_before_race_slice23"),
    )
    plan = _plan(service)
    injected = False

    def inject_history(checkpoint: str, _identifier: str | None) -> None:
        nonlocal injected
        if checkpoint != "before_lock_acquire" or injected:
            return
        injected = True
        repository.create_work_record(
            event_ref(),
            _transition(
                "lct_account_race_slice23",
                previous="lct_account_before_race_slice23",
                from_status="active",
                to_status="invalidated",
                effective_at=HISTORY_LATER,
                reason_category="record_validity",
                reason_code="recording_error",
            ),
        )

    with pytest.raises(
        PortiaConflictError,
        match="lifecycle transition history changed",
    ):
        _commit(
            service,
            plan,
            transition_id="lct_account_race_migrate_slice23",
            operation_id="op_account_race_migrate_slice23",
            fault_hook=inject_history,
        )

    assert injected is True
    current = repository.load_work_record(
        event_ref(),
        "account",
        "1",
        "acct_student_report_1",
    )
    assert current.record.status == "active"


def test_commit_rejects_migration_chronology_before_selected_head(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    repository.create_work_record(
        event_ref(),
        _transition(
            "lct_account_late_head_slice23",
            effective_at="2026-08-27T09:00:00-04:00",
        ),
    )
    plan = _plan(service)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot precede the selected lifecycle head",
    ):
        _commit(
            service,
            plan,
            transition_id="lct_account_early_migrate_slice23",
            operation_id="op_account_early_migrate_slice23",
        )
