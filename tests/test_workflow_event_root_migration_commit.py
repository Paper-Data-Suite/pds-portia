"""Focused Issue #47 Slice 27 tests for Event work-root migration commit."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaConflictError
from portia.storage.migration_representations import MigrationRepresentationStore
from portia.storage.paths import work_record_path
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    MigrationTransformContext,
    RecordMigrationWorkflowService,
    WorkflowPrerequisiteError,
)
from portia.workflows.event_lifecycle import require_event_lifecycle_reconciled
from tests.workflow_helpers import AGENT, TIMESTAMP, event_ref, event_wire

EFFECTIVE_AT = "2026-08-26T12:05:00-04:00"
CREATED_AT = "2026-08-26T12:06:00-04:00"
HISTORY_AT = "2026-08-26T12:01:00-04:00"
HISTORY_LATER = "2026-08-26T12:02:00-04:00"
CORRECTION_AT = "2026-08-26T12:03:00-04:00"


def _event_v1(*, status: str = "active") -> PortiaRecord:
    value = event_wire(status=status)
    value["schema_version"] = "1"
    return parse_portia_record("event", "1", value)


def _event_transform(
    source: PortiaRecord,
    context: MigrationTransformContext,
) -> PortiaRecord:
    value = source.to_dict()
    value["schema_version"] = context.destination_version
    value["supersedes"] = [context.source_reference.to_dict()]
    value["creation_source"] = {"type": "digital_entry"}
    value["created_at"] = context.effective_at
    value["created_by"] = dict(context.created_by)
    value["updated_at"] = context.effective_at
    value["updated_by"] = dict(context.created_by)
    return parse_portia_record("event", context.destination_version, value)


def _event_equivalent(source: PortiaRecord, destination: PortiaRecord) -> bool:
    source_data = source.to_dict()
    destination_data = destination.to_dict()
    semantic_fields = (
        "class_id",
        "instructional_context",
        "location",
        "module_id",
        "occurrence",
        "school_year",
        "status",
        "summary",
        "work_id",
        "work_kind",
    )
    return all(
        source_data.get(field) == destination_data.get(field)
        for field in semantic_fields
    )


def _setup(
    tmp_path: Path,
    *,
    status: str = "active",
) -> tuple[PortiaRepository, RecordMigrationWorkflowService]:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(version="1"), _event_v1(status=status))
    service = RecordMigrationWorkflowService(tmp_path, repository=repository)
    service.register_transformer(
        "event",
        "1",
        "2",
        transformer_id="event_v1_to_v2",
        transformer_version="1",
        reason_category="contract_upgrade",
        reason_code="event_v1_to_v2",
        transform=_event_transform,
        semantic_equivalence=_event_equivalent,
    )
    return repository, service


def _plan(service: RecordMigrationWorkflowService):
    return service.plan_migration(
        event_ref(version="1"),
        "2",
        effective_at=EFFECTIVE_AT,
        created_by=AGENT,
    )


def _commit(
    service: RecordMigrationWorkflowService,
    plan,
    *,
    operation_id: str = "op_event_root_migrate_slice25",
    transition_id: str = "lct_event_root_migrate_slice25",
    migration_id: str = "mig_event_root_migrate_slice25",
    created_at: str = CREATED_AT,
    fault_hook=None,
):
    return service.commit_migration(
        plan,
        migration_id=migration_id,
        transition_id=transition_id,
        created_at=created_at,
        operation_id=operation_id,
        fault_hook=fault_hook,
    )


def _transition(
    transition_id: str,
    *,
    previous: str | None = None,
    from_status: str = "draft",
    to_status: str = "active",
    effective_at: str = HISTORY_AT,
) -> PortiaRecord:
    return parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": event_ref(version="1").class_id,
            "work_id": event_ref(version="1").work_id,
            "transition_id": transition_id,
            "target": {
                "kind": "work",
                "work_kind": "event",
                "contract_version": "1",
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
            "reason": {"category": "workflow", "code": "event_confirmed"},
            "effective_at": effective_at,
            "creation_source": {"type": "digital_entry"},
            "created_at": effective_at,
            "created_by": AGENT,
        },
    )


def _correction(
    *,
    replaced: str,
    replacement: str | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "lifecycle_history_correction",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_history_correction",
            "module_id": "portia",
            "class_id": event_ref(version="1").class_id,
            "work_id": event_ref(version="1").work_id,
            "correction_id": "lhc_event_root_slice25",
            "target": {
                "kind": "work",
                "work_kind": "event",
                "contract_version": "1",
            },
            "previous_correction": None,
            "replaced_head": {
                "record_kind": "lifecycle_transition",
                "record_id": replaced,
                "contract_version": "1",
            },
            "replacement_head": (
                None
                if replacement is None
                else {
                    "record_kind": "lifecycle_transition",
                    "record_id": replacement,
                    "contract_version": "1",
                }
            ),
            "reason": {"code": "transition_should_not_exist"},
            "creation_source": {"type": "digital_entry"},
            "created_at": CORRECTION_AT,
            "created_by": AGENT,
        },
    )


def test_commit_event_root_migration_switches_current_and_preserves_both_versions(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)

    result = _commit(service, plan)

    assert result.accepted_steps == (
        "step_source_history",
        "step_destination",
        "step_certificate",
        "step_transition",
        "step_source_superseded",
        "step_source_version",
        "step_current_switch",
    )
    current = repository.load_work(event_ref(version="2"))
    assert current.record.to_dict() == plan.destination.to_dict()
    assert current.record.status == "active"

    representations = MigrationRepresentationStore(tmp_path, repository=repository)
    preserved_source = representations.load_preserved_work_representation(
        event_ref(version="1")
    )
    preserved_destination = representations.load_preserved_work_representation(
        event_ref(version="2")
    )
    assert preserved_source.record.status == "superseded"
    assert preserved_source.record.field("updated_at") == CREATED_AT
    assert preserved_destination.record.to_dict() == plan.destination.to_dict()

    certificate = repository.load_work_record(
        event_ref(version="2"),
        "record_migration",
        "1",
        "mig_event_root_migrate_slice25",
    ).record
    assert certificate.field("source") == {
        "kind": "work",
        "work_ref": event_ref(version="1").to_dict(),
        "observed_updated_at": TIMESTAMP,
    }
    assert certificate.field("destination") == {
        "kind": "work",
        "work_ref": event_ref(version="2").to_dict(),
        "observed_updated_at": EFFECTIVE_AT,
    }

    transition = repository.load_work_record(
        event_ref(version="2"),
        "lifecycle_transition",
        "1",
        "lct_event_root_migrate_slice25",
    ).record
    assert transition.field("target") == {
        "kind": "work",
        "work_kind": "event",
        "contract_version": "1",
    }
    assert transition.field("previous_transition") is None
    assert transition.field("reason") == {
        "category": "migration",
        "code": "contract_migrated",
    }
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"

    destination_state = require_event_lifecycle_reconciled(
        repository,
        event_ref(version="2"),
        current.record,
    )
    assert destination_state.transitions == ()
    assert destination_state.head is None


def test_event_root_migration_extends_exact_uncorrected_v1_lifecycle_head(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    repository.create_work_record(
        event_ref(version="1"),
        _transition("lct_event_v1_activate_slice25"),
    )
    plan = _plan(service)

    _commit(
        service,
        plan,
        operation_id="op_event_head_migrate_slice25",
        transition_id="lct_event_head_migrate_slice25",
        migration_id="mig_event_head_migrate_slice25",
    )

    transition = repository.load_work_record(
        event_ref(version="2"),
        "lifecycle_transition",
        "1",
        "lct_event_head_migrate_slice25",
    ).record
    assert transition.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_event_v1_activate_slice25",
        "contract_version": "1",
    }


def test_event_root_migration_extends_corrected_selected_branch(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    excluded = "lct_event_v1_cancelled_slice27"
    selected = "lct_event_v1_active_slice27"
    repository.create_work_record(
        event_ref(version="1"),
        _transition(excluded, to_status="cancelled"),
    )
    repository.create_work_record(
        event_ref(version="1"),
        _transition(selected),
    )
    correction = _correction(replaced=excluded, replacement=selected)
    repository.create_work_record(event_ref(version="1"), correction)
    plan = _plan(service)

    _commit(
        service,
        plan,
        operation_id="op_event_corrected_migrate_slice27",
        transition_id="lct_event_corrected_migrate_slice27",
        migration_id="mig_event_corrected_migrate_slice27",
    )

    transition = repository.load_work_record(
        event_ref(version="2"),
        "lifecycle_transition",
        "1",
        "lct_event_corrected_migrate_slice27",
    ).record
    assert transition.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": selected,
        "contract_version": "1",
    }
    accepted_correction = repository.load_work_record(
        event_ref(version="2"),
        "lifecycle_history_correction",
        "1",
        "lhc_event_root_slice25",
    ).record
    assert accepted_correction.to_dict() == correction.to_dict()


def test_event_root_migration_extends_selected_head_beyond_correction_replacement(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path, status="closed")
    excluded = "lct_event_v1_cancelled_branch_slice27"
    replacement = "lct_event_v1_active_branch_slice27"
    selected_head = "lct_event_v1_closed_head_slice27"
    repository.create_work_record(
        event_ref(version="1"),
        _transition(excluded, to_status="cancelled"),
    )
    repository.create_work_record(
        event_ref(version="1"),
        _transition(replacement),
    )
    repository.create_work_record(
        event_ref(version="1"),
        _transition(
            selected_head,
            previous=replacement,
            from_status="active",
            to_status="closed",
            effective_at=HISTORY_LATER,
        ),
    )
    repository.create_work_record(
        event_ref(version="1"),
        _correction(replaced=excluded, replacement=replacement),
    )
    plan = _plan(service)

    _commit(
        service,
        plan,
        operation_id="op_event_corrected_extension_migrate_slice27",
        transition_id="lct_event_corrected_extension_migrate_slice27",
        migration_id="mig_event_corrected_extension_migrate_slice27",
    )

    transition = repository.load_work_record(
        event_ref(version="2"),
        "lifecycle_transition",
        "1",
        "lct_event_corrected_extension_migrate_slice27",
    ).record
    assert transition.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": selected_head,
        "contract_version": "1",
    }


def test_event_root_migration_rejects_history_drift_before_work_lock(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    first = "lct_event_v1_before_race_slice25"
    repository.create_work_record(event_ref(version="1"), _transition(first))
    plan = _plan(service)
    injected = False

    def inject_history(checkpoint: str, _identifier: str | None) -> None:
        nonlocal injected
        if checkpoint != "before_lock_acquire" or injected:
            return
        injected = True
        repository.create_work_record(
            event_ref(version="1"),
            _transition(
                "lct_event_v1_race_slice25",
                previous=first,
                from_status="active",
                to_status="invalidated",
                effective_at=HISTORY_LATER,
            ),
        )

    with pytest.raises(
        PortiaConflictError,
        match="lifecycle transition history changed",
    ):
        _commit(
            service,
            plan,
            operation_id="op_event_race_migrate_slice25",
            transition_id="lct_event_race_migrate_slice25",
            migration_id="mig_event_race_migrate_slice25",
            fault_hook=inject_history,
        )

    assert injected is True
    assert repository.load_work(event_ref(version="1")).record.status == "active"


def test_event_root_migration_rejects_correction_drift_before_work_lock(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    head = "lct_event_v1_before_correction_race_slice25"
    repository.create_work_record(event_ref(version="1"), _transition(head))
    plan = _plan(service)
    injected = False

    def inject_correction(checkpoint: str, _identifier: str | None) -> None:
        nonlocal injected
        if checkpoint != "before_lock_acquire" or injected:
            return
        injected = True
        repository.create_work_record(
            event_ref(version="1"),
            _correction(replaced=head),
        )

    with pytest.raises(
        PortiaConflictError,
        match="lifecycle-history correction chain changed",
    ):
        _commit(
            service,
            plan,
            operation_id="op_event_correction_race_slice25",
            transition_id="lct_event_correction_race_slice25",
            migration_id="mig_event_correction_race_slice25",
            fault_hook=inject_correction,
        )

    assert injected is True
    assert repository.load_work(event_ref(version="1")).record.status == "active"


def test_completed_event_root_migration_replays_idempotently(tmp_path: Path) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)

    first = _commit(service, plan)
    replay = _commit(service, plan)

    assert replay.accepted_steps == first.accepted_steps
    assert repository.load_work(event_ref(version="2")).record.to_dict() == (
        plan.destination.to_dict()
    )
    migrations = repository.list_work_records(
        event_ref(version="2"),
        "record_migration",
        version="1",
    )
    transitions = tuple(
        stored
        for stored in repository.list_work_records(
            event_ref(version="2"),
            "lifecycle_transition",
            version="1",
        )
        if stored.record.logical_id == "lct_event_root_migrate_slice25"
    )
    assert len(migrations) == 1
    assert len(transitions) == 1


def test_event_root_migration_rejects_created_at_before_effective_at(
    tmp_path: Path,
) -> None:
    repository, service = _setup(tmp_path)
    plan = _plan(service)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="created_at cannot precede effective_at",
    ):
        _commit(
            service,
            plan,
            operation_id="op_event_early_created_slice25",
            transition_id="lct_event_early_created_slice25",
            migration_id="mig_event_early_created_slice25",
            created_at="2026-08-26T12:04:00-04:00",
        )

    assert repository.load_work(event_ref(version="1")).record.status == "active"
    assert not work_record_path(
        tmp_path,
        event_ref(version="1"),
        "record_migration",
        "mig_event_early_created_slice25",
    ).exists()
