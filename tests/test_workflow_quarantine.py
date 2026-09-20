from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

import portia.storage.series as series_storage
from portia.identity import ActorDirectoryService
from portia.models import parse_portia_record
from portia.models.references import ExactActorRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaOperationPartialCommitError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
)
from portia.storage.paths import quarantine_current_path, quarantine_revision_path
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore, QuarantineStore
from portia.workflows import (
    EventBundle,
    EventBundleWorkflowService,
    EventWorkflowService,
    IntegrityWorkflowService,
    QuarantineWorkflowService,
    RecoveryWorkflowService,
    WorkflowPrerequisiteError,
)
from portia.workflows.common import work_target
from tests.workflow_helpers import event_record, event_ref, participant_record


@pytest.fixture(autouse=True)
def _stable_operation_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep operation creation before this module's fixed evidence timestamps."""
    monkeypatch.setattr(
        "portia.workflows.coordinated._now",
        lambda: "2026-09-17T22:00:00-04:00",
    )


def _roster(root: Path, class_id: str = "class_a") -> None:
    write_class_roster(
        root,
        create_roster(
            class_id,
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )


def _completed_bundle(root: Path, operation_id: str = "op_quarantine_apply") -> dict[str, object]:
    _roster(root)
    EventBundleWorkflowService(root).commit(
        EventBundle(
            event=event_record(),  # type: ignore[arg-type]
            participants=(participant_record(),),  # type: ignore[arg-type]
        ),
        operation_id=operation_id,
    )
    current = OperationJournalStore(root).load_current(operation_id)
    revision = current.revision.to_dict()["journal_revision"]
    assert isinstance(revision, int)
    return {
        "operation_id": operation_id,
        "journal_revision": revision,
        "contract_version": "2",
    }


def _completed_repair(
    root: Path,
    source_operation: str,
    operation_id: str,
    target: dict[str, object],
) -> dict[str, object]:
    source = OperationJournalStore(root).load_current(source_operation).revision.to_dict()
    data = deepcopy(source)
    data.update(
        {
            "operation_id": operation_id,
            "operation_kind": "repair_operation",
            "scope": "operation" if target.get("kind") == "operation" else "work",
            "primary_target": target,
            "affected_targets": [],
            "journal_revision": 1,
            "previous_journal_revision": None,
        }
    )
    record = parse_portia_record("operation_journal", "2", data)
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": operation_id,
            "journal_revision": 1,
        },
    )
    OperationJournalStore(root).create(record, pointer)
    return {
        "operation_id": operation_id,
        "journal_revision": 1,
        "contract_version": "2",
    }


def _apply_work_quarantine(
    root: Path,
    *,
    quarantine_id: str = "qnt_0123456789abcdef0123456789abcdef",
) -> tuple[QuarantineWorkflowService, object, dict[str, object]]:
    applying = _completed_bundle(root)
    target = work_target(event_ref())
    service = QuarantineWorkflowService(root)
    state = service.apply_quarantine(
        target=target,
        reason="partial_commit",
        reason_detail="Exact coordinated state requires repair and reevaluation.",
        effects=["block_current_use", "block_work_writes", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        review_deadline="2026-09-20T23:05:00-04:00",
        quarantine_id=quarantine_id,
    )
    return service, state, applying


def test_apply_creates_active_v2_revision_and_explicit_pointer(tmp_path: Path) -> None:
    service, state, _applying = _apply_work_quarantine(tmp_path)

    data = state.revision.to_dict()
    assert data["schema_version"] == "2"
    assert data["state"] == "active"
    assert data["quarantine_revision"] == 1
    assert data["previous_quarantine_revision"] is None
    assert data["resolution"] is None
    assert state.pointer.to_dict()["quarantine_revision"] == 1
    assert service.store.load_current(str(data["quarantine_id"])).revision.to_dict() == data

    with pytest.raises(PortiaQuarantinedError, match="block_work_writes"):
        QuarantineGuard(tmp_path).require_allowed(
            work_target(event_ref()), "block_work_writes"
        )


def test_active_work_quarantine_blocks_production_lifecycle_transition(
    tmp_path: Path,
) -> None:
    applying = _completed_bundle(tmp_path)
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=work_target(event_ref()),
        reason="partial_commit",
        effects=["block_lifecycle_writes", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_44444444444444444444444444444444",
    )
    events = EventWorkflowService(tmp_path)
    selected = events.load_exact(event_ref())

    with pytest.raises(PortiaQuarantinedError, match="block_lifecycle_writes"):
        events.transition_lifecycle(
            event_ref(),
            event_record(status="closed", updated_at="2026-09-17T23:10:00-04:00"),
            expected=selected.fingerprint,
            transition_id="lct_quarantine_blocked_001",
            reason_code="event_completed",
            operation_id="op_quarantine_blocked_lifecycle",
        )

    assert events.load_exact(event_ref()).record.status == "active"


def test_apply_rejects_unowned_or_overbroad_effect_before_persistence(
    tmp_path: Path,
) -> None:
    applying = _completed_bundle(tmp_path)
    service = QuarantineWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="proportional"):
        service.apply_quarantine(
            target=work_target(event_ref()),
            reason="partial_commit",
            effects=["block_class_writes"],
            applying_operation=applying,
            supporting_finding_keys=[],
            applied_at="2026-09-17T23:05:00-04:00",
            applied_by={"type": "system_process", "process_id": "workflow_bundle"},
            release_requirements=["canonical_state_reconciled"],
            quarantine_id="qnt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
    assert not quarantine_revision_path(
        tmp_path, "qnt_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", 1
    ).exists()


def test_apply_pointer_failure_leaves_unselected_exact_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    applying = _completed_bundle(tmp_path)
    identifier = "qnt_55555555555555555555555555555555"
    original_create = series_storage.exclusive_create
    calls = 0

    def fail_pointer(path: Path, content: bytes):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic initial pointer interruption")
        return original_create(path, content)

    monkeypatch.setattr(series_storage, "exclusive_create", fail_pointer)
    with pytest.raises(PortiaRecoveryRequiredError, match="pointer was not accepted"):
        QuarantineWorkflowService(tmp_path).apply_quarantine(
            target=work_target(event_ref()),
            reason="partial_commit",
            effects=["block_current_use", "review_required"],
            applying_operation=applying,
            supporting_finding_keys=[],
            applied_at="2026-09-17T23:05:00-04:00",
            applied_by={"type": "system_process", "process_id": "workflow_bundle"},
            release_requirements=["canonical_state_reconciled"],
            quarantine_id=identifier,
        )

    assert quarantine_revision_path(tmp_path, identifier, 1).exists()
    assert not quarantine_current_path(tmp_path, identifier).exists()


def test_release_requires_all_evidence_and_is_idempotent(tmp_path: Path) -> None:
    service, active, applying = _apply_work_quarantine(tmp_path)
    target = active.revision.to_dict()["target"]
    assert isinstance(target, dict)
    repair = _completed_repair(
        tmp_path,
        str(applying["operation_id"]),
        "op_quarantine_release",
        target,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="every exact"):
        service.release_quarantine(
            str(active.revision.to_dict()["quarantine_id"]),
            expected_pointer=active.pointer_fingerprint,
            resolving_operation=repair,
            satisfied_release_requirements=[],
            effective_at="2026-09-17T23:30:00-04:00",
            resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
        )

    released = service.release_quarantine(
        str(active.revision.to_dict()["quarantine_id"]),
        expected_pointer=active.pointer_fingerprint,
        resolving_operation=repair,
        satisfied_release_requirements=["canonical_state_reconciled"],
        effective_at="2026-09-17T23:30:00-04:00",
        resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
    )
    assert released.revision.to_dict()["state"] == "released"
    assert released.revision.to_dict()["previous_quarantine_revision"] == 1
    assert QuarantineStore(tmp_path).load_current(
        str(active.revision.to_dict()["quarantine_id"])
    ).revision.to_dict()["quarantine_revision"] == 2
    assert active.revision.to_dict()["state"] == "active"
    QuarantineGuard(tmp_path).require_allowed(
        work_target(event_ref()), "block_work_writes"
    )

    replay = service.release_quarantine(
        str(active.revision.to_dict()["quarantine_id"]),
        expected_pointer=active.pointer_fingerprint,
        resolving_operation=repair,
        satisfied_release_requirements=["canonical_state_reconciled"],
        effective_at="2026-09-17T23:30:00-04:00",
        resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
    )
    assert replay.revision.to_dict()["quarantine_revision"] == 2


def test_release_rejects_stale_pointer_without_new_revision(tmp_path: Path) -> None:
    service, active, applying = _apply_work_quarantine(tmp_path)
    target = active.revision.to_dict()["target"]
    assert isinstance(target, dict)
    repair = _completed_repair(
        tmp_path,
        str(applying["operation_id"]),
        "op_quarantine_release",
        target,
    )
    stale = type(active.pointer_fingerprint)(
        algorithm="sha256", digest="0" * 64, byte_length=0
    )
    with pytest.raises(PortiaConflictError, match="pointer changed"):
        service.release_quarantine(
            str(active.revision.to_dict()["quarantine_id"]),
            expected_pointer=stale,
            resolving_operation=repair,
            satisfied_release_requirements=["canonical_state_reconciled"],
            effective_at="2026-09-17T23:30:00-04:00",
            resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
        )
    assert service.store.load_current(
        str(active.revision.to_dict()["quarantine_id"])
    ).revision.to_dict()["quarantine_revision"] == 1


def test_supersession_requires_exact_active_narrower_successor(tmp_path: Path) -> None:
    service, first, applying = _apply_work_quarantine(tmp_path)
    second = service.apply_quarantine(
        target=work_target(event_ref()),
        reason="partial_commit",
        effects=["block_work_writes", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:10:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_fedcba9876543210fedcba9876543210",
    )
    target = first.revision.to_dict()["target"]
    assert isinstance(target, dict)
    repair = _completed_repair(
        tmp_path,
        str(applying["operation_id"]),
        "op_quarantine_supersede",
        target,
    )
    successor_ref = {
        "quarantine_id": second.revision.to_dict()["quarantine_id"],
        "quarantine_revision": 1,
        "contract_version": "2",
    }
    superseded = service.supersede_quarantine(
        str(first.revision.to_dict()["quarantine_id"]),
        expected_pointer=first.pointer_fingerprint,
        successor_quarantine=successor_ref,
        resolving_operation=repair,
        rationale="The explicit successor narrows the blocking effects.",
        effective_at="2026-09-17T23:30:00-04:00",
        resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
    )
    assert superseded.revision.to_dict()["state"] == "superseded"
    assert first.revision.to_dict()["state"] == "active"


def test_operation_target_quarantine_blocks_completion_effect(tmp_path: Path) -> None:
    original = _completed_bundle(tmp_path)
    operation_target = {
        "kind": "operation",
        "operation_ref": {"operation_id": original["operation_id"]},
    }
    applying = _completed_repair(
        tmp_path,
        str(original["operation_id"]),
        "op_quarantine_operation",
        operation_target,
    )
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=operation_target,
        reason="journal_integrity",
        effects=["block_operation_completion", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_11111111111111111111111111111111",
    )
    with pytest.raises(PortiaQuarantinedError, match="block_operation_completion"):
        QuarantineGuard(tmp_path).require_allowed(
            operation_target, "block_operation_completion"
        )


def test_operation_quarantine_blocks_recovery_completion_after_durable_writes(
    tmp_path: Path,
) -> None:
    _roster(tmp_path)
    operation_id = "op_quarantine_partial_bundle"

    def interrupt(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_1":
            raise RuntimeError("synthetic partial commit")

    with pytest.raises(PortiaOperationPartialCommitError):
        EventBundleWorkflowService(tmp_path).commit(
            EventBundle(
                event=event_record(),  # type: ignore[arg-type]
                participants=(participant_record(),),  # type: ignore[arg-type]
            ),
            operation_id=operation_id,
            fault_hook=interrupt,
        )
    partial = OperationJournalStore(tmp_path).load_current(operation_id)
    operation_target = {
        "kind": "operation",
        "operation_ref": {"operation_id": operation_id},
    }
    _roster(tmp_path, "class_b")
    authority_operation = "op_quarantine_authority_source"
    EventBundleWorkflowService(tmp_path).commit(
        EventBundle(
            event=event_record(class_id="class_b", event_id="evt_beta"),  # type: ignore[arg-type]
            participants=(
                participant_record(
                    participant_id="ep_beta",
                    class_id="class_b",
                    event_id="evt_beta",
                ),
            ),  # type: ignore[arg-type]
        ),
        operation_id=authority_operation,
    )
    applying = _completed_repair(
        tmp_path,
        authority_operation,
        "op_quarantine_partial_containment",
        operation_target,
    )
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=operation_target,
        reason="partial_commit",
        effects=["block_operation_completion", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_66666666666666666666666666666666",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_operation_completion"):
        RecoveryWorkflowService(tmp_path).resume_incomplete(
            operation_id,
            expected_pointer=partial.pointer_fingerprint,
        )

    selected = OperationJournalStore(tmp_path).load_current(operation_id)
    assert selected.revision.to_dict()["state"] == "committed"
    assert len(PortiaRepository(tmp_path).list_event_participants(event_ref())) == 1


def test_class_write_effect_blocks_only_work_in_exact_class(tmp_path: Path) -> None:
    original = _completed_bundle(tmp_path)
    class_target = {"kind": "class", "class_id": "class_a"}
    applying = _completed_repair(
        tmp_path,
        str(original["operation_id"]),
        "op_quarantine_class",
        class_target,
    )
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=class_target,
        reason="canonical_contradiction",
        effects=["block_class_writes", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_22222222222222222222222222222222",
    )
    guard = QuarantineGuard(tmp_path)
    with pytest.raises(PortiaQuarantinedError, match="block_work_writes"):
        guard.require_allowed(work_target(event_ref()), "block_work_writes")
    other = deepcopy(work_target(event_ref()))
    other["work_ref"]["class_id"] = "class_b"  # type: ignore[index]
    guard.require_allowed(other, "block_work_writes")


def test_actor_target_quarantine_blocks_production_directory_write(
    tmp_path: Path,
) -> None:
    actor_wire = {
        "schema_version": "1",
        "record_type": "actor",
        "module_id": "portia",
        "actor_id": "actr_quarantined",
        "status": "active",
        "display": {"display_name": "Synthetic Caregiver"},
        "actor_category": {"kind": "family_or_caregiver"},
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-08-26T12:00:00-04:00",
        "created_by": {"type": "system_process", "process_id": "identity_test"},
        "updated_at": "2026-08-26T12:00:00-04:00",
        "updated_by": {"type": "system_process", "process_id": "identity_test"},
    }
    actors = ActorDirectoryService(tmp_path)
    created = actors.create_actor(parse_portia_record("actor", "1", actor_wire))
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor",
            "actor_ref": {
                "actor_id": "actr_quarantined",
                "contract_version": "1",
            },
        },
    }
    applying_source = _completed_bundle(tmp_path)
    applying = _completed_repair(
        tmp_path,
        str(applying_source["operation_id"]),
        "op_quarantine_actor_containment",
        target,
    )
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=target,
        reason="authorization_limitation",
        effects=["block_actor_directory_writes", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["actor_state_reconciled"],
        quarantine_id="qnt_77777777777777777777777777777777",
    )
    replacement_wire = deepcopy(actor_wire)
    replacement_wire["display"] = {"display_name": "Blocked Replacement"}
    replacement_wire["updated_at"] = "2026-09-17T23:10:00-04:00"

    with pytest.raises(PortiaQuarantinedError, match="block_actor_directory_writes"):
        actors.replace_actor(
            parse_portia_record("actor", "1", replacement_wire),
            expected=created.fingerprint,
        )

    assert actors.load_actor(
        ExactActorRef(actor_id="actr_quarantined", contract_version="1")
    ).record.to_dict() == actor_wire


def test_release_pointer_failure_leaves_exact_orphan_for_explicit_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, active, applying = _apply_work_quarantine(tmp_path)
    target = active.revision.to_dict()["target"]
    assert isinstance(target, dict)
    repair = _completed_repair(
        tmp_path,
        str(applying["operation_id"]),
        "op_quarantine_release",
        target,
    )

    def fail_pointer(*args: object, **kwargs: object) -> object:
        raise RuntimeError("synthetic pointer interruption")

    monkeypatch.setattr("portia.storage.series.guarded_replace", fail_pointer)
    with pytest.raises(PortiaRecoveryRequiredError, match="pointer did not advance"):
        service.release_quarantine(
            str(active.revision.to_dict()["quarantine_id"]),
            expected_pointer=active.pointer_fingerprint,
            resolving_operation=repair,
            satisfied_release_requirements=["canonical_state_reconciled"],
            effective_at="2026-09-17T23:30:00-04:00",
            resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
        )
    observation = service.store.inspect_recovery(
        str(active.revision.to_dict()["quarantine_id"])
    )
    assert observation.disposition == "orphan_linear_successor"
    assert observation.orphan_successors == (2,)
    assert service.store.load_current(
        str(active.revision.to_dict()["quarantine_id"])
    ).revision.to_dict()["state"] == "active"


def test_generated_quarantine_id_is_opaque_and_target_independent(tmp_path: Path) -> None:
    applying = _completed_bundle(tmp_path)
    state = QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=work_target(event_ref()),
        reason="partial_commit",
        effects=["review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
    )
    identifier = state.revision.to_dict()["quarantine_id"]
    assert isinstance(identifier, str)
    assert identifier.startswith("qnt_")
    assert len(identifier) == 36
    assert "class_a" not in identifier and "evt_alpha" not in identifier


def test_integrity_scan_clean_release_uses_current_fresh_zero_generation(
    tmp_path: Path,
) -> None:
    applying = _completed_bundle(tmp_path)
    operation_id = str(applying["operation_id"])
    scope = IntegrityWorkflowService.operation_scope(operation_id)
    projected = IntegrityWorkflowService(tmp_path).project_operation_persistence_findings(
        operation_id
    )
    assert projected.findings == ()
    target = work_target(event_ref())
    service = QuarantineWorkflowService(tmp_path)
    active = service.apply_quarantine(
        target=target,
        reason="partial_commit",
        effects=["block_current_use", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=[
            "canonical_state_reconciled",
            "integrity_scan_clean",
        ],
        quarantine_id="qnt_33333333333333333333333333333333",
    )
    repair = _completed_repair(
        tmp_path,
        operation_id,
        "op_quarantine_integrity_release",
        target,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="integrity_scan_clean"):
        service.release_quarantine(
            "qnt_33333333333333333333333333333333",
            expected_pointer=active.pointer_fingerprint,
            resolving_operation=repair,
            satisfied_release_requirements=[
                "canonical_state_reconciled",
                "integrity_scan_clean",
            ],
            effective_at="2026-09-17T23:30:00-04:00",
            resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
        )
    released = service.release_quarantine(
        "qnt_33333333333333333333333333333333",
        expected_pointer=active.pointer_fingerprint,
        resolving_operation=repair,
        satisfied_release_requirements=[
            "canonical_state_reconciled",
            "integrity_scan_clean",
        ],
        effective_at="2026-09-17T23:30:00-04:00",
        resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
        finding_scope=scope,
    )
    assert released.revision.to_dict()["state"] == "released"


def test_projection_quarantine_blocks_current_integrity_projection_use(
    tmp_path: Path,
) -> None:
    applying_source = _completed_bundle(tmp_path)
    operation_id = str(applying_source["operation_id"])
    integrity = IntegrityWorkflowService(tmp_path)
    scope = integrity.operation_scope(operation_id)
    integrity.project_operation_persistence_findings(operation_id)
    target = {
        "kind": "derived_projection",
        "projection_kind": "active_integrity_finding_index",
        "projection_scope": scope,
    }
    applying = _completed_repair(
        tmp_path,
        operation_id,
        "op_quarantine_projection_containment",
        {"kind": "workspace"},
    )
    QuarantineWorkflowService(tmp_path).apply_quarantine(
        target=target,
        reason="authorization_limitation",
        effects=["block_projection_use", "review_required"],
        applying_operation=applying,
        supporting_finding_keys=[],
        applied_at="2026-09-17T23:05:00-04:00",
        applied_by={"type": "system_process", "process_id": "workflow_bundle"},
        release_requirements=["canonical_state_reconciled"],
        quarantine_id="qnt_88888888888888888888888888888888",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_projection_use"):
        integrity.current_findings(scope)
