"""Focused Slice 4 tests for Support Process activation and current use."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.paths import work_storage_history_path
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)
from portia.workflows.support_process_lifecycle import (
    build_support_process_lifecycle_transition,
    require_coordinated_support_process_transition,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-08-31T10:05:00-04:00"
ROOT_UPDATED = "2026-08-31T10:10:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice4_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record(
    *,
    status: str = "proposed",
    workflow_state: str = "planning",
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": workflow_state,
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_record(
    *,
    status: str = "proposed",
    contexts: list[dict[str, object]] | None = None,
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "participant_id": "spp_alpha",
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
            },
            "contexts": contexts or [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def active_root_candidate(**changes: object) -> PortiaRecord:
    wire = root_record().to_dict()
    wire["status"] = "active"
    wire["updated_at"] = ROOT_UPDATED
    wire.update(changes)
    return parse_portia_record("support_process", "1", wire)


def active_participant_candidate(
    *,
    contexts: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    wire = participant_record(contexts=contexts).to_dict()
    wire["status"] = "active"
    wire["updated_at"] = PARTICIPANT_UPDATED
    return parse_portia_record("support_process_participant", "1", wire)


def _create_active_participant(
    tmp_path: Path,
    *,
    contexts: list[dict[str, object]] | None = None,
):
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    created = participant_service.create(
        work_ref(),
        participant_record(contexts=contexts),
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_alpha"),
        active_participant_candidate(contexts=contexts),
        expected=created.fingerprint,
        transition_id="lct_spp_activate_for_root",
        reason_code="planning_confirmed",
        operation_id="op_spp_activate_for_root",
    )
    return root_service, participant_service, root


def _activate_root(tmp_path: Path):
    root_service, participant_service, root = _create_active_participant(tmp_path)
    candidate = active_root_candidate()
    result = root_service.transition_lifecycle(
        work_ref(),
        candidate,
        expected=root.fingerprint,
        transition_id="lct_sup_activate_001",
        reason_code="planning_confirmed",
        operation_id="op_sup_activate_001",
    )
    return root_service, participant_service, root, candidate, result


def test_build_activation_transition_targets_support_process_root() -> None:
    repository = type(
        "Repository",
        (),
        {"list_work_records": lambda *_args, **_kwargs: ()},
    )()
    transition = build_support_process_lifecycle_transition(
        repository,  # type: ignore[arg-type]
        work_ref(),
        root_record(),
        active_root_candidate(),
        transition_id="lct_sup_activate_001",
        reason_code="planning_confirmed",
    )
    target = transition.field("target")
    assert isinstance(target, Mapping)
    assert target == {
        "kind": "work",
        "work_kind": "support_process",
        "contract_version": "1",
    }


def test_root_lifecycle_transition_cannot_rewrite_workflow_state() -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="workflow_state"):
        require_coordinated_support_process_transition(
            root_record(),
            active_root_candidate(workflow_state="active"),
        )


def test_root_lifecycle_transition_cannot_directly_supersede() -> None:
    wire = root_record().to_dict()
    wire["status"] = "superseded"
    wire["updated_at"] = ROOT_UPDATED
    candidate = parse_portia_record("support_process", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        require_coordinated_support_process_transition(root_record(), candidate)


def test_activation_requires_active_supported_person_and_writes_nothing(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    with pytest.raises(WorkflowPrerequisiteError, match="supported_person"):
        service.transition_lifecycle(
            work_ref(),
            active_root_candidate(),
            expected=created.fingerprint,
            transition_id="lct_sup_rejected_001",
            reason_code="planning_confirmed",
            operation_id="op_sup_rejected_001",
        )
    assert service.load_exact(work_ref()).record.status == "proposed"
    assert service.repository.list_work_records(
        work_ref(),
        "lifecycle_transition",
        version="1",
    ) == ()


def test_active_observer_alone_does_not_satisfy_supported_person(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root = _create_active_participant(
        tmp_path,
        contexts=[{"kind": "observer"}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="supported_person"):
        root_service.transition_lifecycle(
            work_ref(),
            active_root_candidate(),
            expected=root.fingerprint,
            transition_id="lct_sup_observer_only",
            reason_code="planning_confirmed",
        )
    assert root_service.load_exact(work_ref()).record.status == "proposed"


def test_activation_persists_history_transition_and_root_replacement(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root, _candidate, result = _activate_root(
        tmp_path
    )
    assert result.accepted_steps == (
        "step_history",
        "step_transition",
        "step_work",
    )
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "support_process",
        "sup_alpha",
        root.fingerprint.digest,
    )
    assert history.exists()
    current = root_service.require_current_use(work_ref())
    assert current.record.status == "active"
    assert current.record.field("workflow_state") == "planning"
    transition = root_service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_sup_activate_001",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_completed_activation_operation_replays_idempotently(tmp_path: Path) -> None:
    (
        root_service,
        _participant_service,
        root,
        candidate,
        first,
    ) = _activate_root(tmp_path)
    replay = root_service.transition_lifecycle(
        work_ref(),
        candidate,
        expected=root.fingerprint,
        transition_id="lct_sup_activate_001",
        reason_code="planning_confirmed",
        operation_id="op_sup_activate_001",
    )
    assert replay.accepted_steps == first.accepted_steps
    assert root_service.require_current_use(work_ref()).record.status == "active"


def test_current_use_rejects_proposed_root(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    service.create(root_record())
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical lifecycle"):
        service.require_current_use(work_ref())


def test_active_process_cannot_lose_final_supported_person(tmp_path: Path) -> None:
    root_service, participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    reference = support_process_participant_reference(work_ref(), "spp_alpha")
    current = participant_service.load_exact(reference)
    wire = current.record.to_dict()
    wire["status"] = "invalidated"
    wire["updated_at"] = "2026-08-31T10:15:00-04:00"
    invalidated = parse_portia_record("support_process_participant", "1", wire)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="final active supported_person",
    ):
        participant_service.transition_lifecycle(
            reference,
            invalidated,
            expected=current.fingerprint,
            transition_id="lct_spp_invalidated_final",
            reason_code="recording_error",
        )
    current_participant = participant_service.require_current_use(reference)
    assert current_participant.participant.record.status == "active"
    assert root_service.require_current_use(work_ref()).record.status == "active"


def test_activation_effective_at_cannot_precede_root_creation(tmp_path: Path) -> None:
    root_service, _participant_service, root = _create_active_participant(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede creation"):
        root_service.transition_lifecycle(
            work_ref(),
            active_root_candidate(),
            expected=root.fingerprint,
            transition_id="lct_sup_bad_time",
            reason_code="planning_confirmed",
            effective_at="2026-08-31T09:59:00-04:00",
        )
    assert root_service.load_exact(work_ref()).record.status == "proposed"


# Slice 9a — ordinary Support Process workflow-state progression.

WORKFLOW_UPDATE_1 = "2026-08-31T10:20:00-04:00"
WORKFLOW_UPDATE_2 = "2026-08-31T10:25:00-04:00"


def _workflow_revision(
    prior: PortiaRecord,
    *,
    workflow_state: str,
    updated_at: str,
    **changes: object,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["workflow_state"] = workflow_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    wire.update(changes)
    return parse_portia_record("support_process", "1", wire)


def test_workflow_state_planning_to_active_preserves_identity(
    tmp_path: Path,
) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    transitioned = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            current.record,
            workflow_state="active",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=current.fingerprint,
    )
    assert transitioned.record.work_id == "sup_alpha"
    assert transitioned.record.status == "active"
    assert transitioned.record.field("workflow_state") == "active"


def test_workflow_state_transition_creates_no_lifecycle_transition(
    tmp_path: Path,
) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    before = service.repository.list_work_records(
        work_ref(), "lifecycle_transition", version="1"
    )
    current = service.load_exact(work_ref())
    service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            current.record,
            workflow_state="active",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=current.fingerprint,
    )
    after = service.repository.list_work_records(
        work_ref(), "lifecycle_transition", version="1"
    )
    assert after == before


def test_workflow_state_active_pause_resume(tmp_path: Path) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    active = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            current.record,
            workflow_state="active",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=current.fingerprint,
    )
    paused = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            active.record,
            workflow_state="paused",
            updated_at=WORKFLOW_UPDATE_2,
        ),
        expected=active.fingerprint,
    )
    resumed = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            paused.record,
            workflow_state="active",
            updated_at="2026-08-31T10:30:00-04:00",
        ),
        expected=paused.fingerprint,
    )
    assert resumed.record.field("workflow_state") == "active"


@pytest.mark.parametrize("terminal", ["completed", "discontinued"])
def test_workflow_state_active_terminal_states_are_terminal(
    tmp_path: Path,
    terminal: str,
) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    active = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            current.record,
            workflow_state="active",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=current.fingerprint,
    )
    terminal_record = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            active.record,
            workflow_state=terminal,
            updated_at=WORKFLOW_UPDATE_2,
        ),
        expected=active.fingerprint,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="illegal"):
        service.transition_workflow_state(
            work_ref(),
            _workflow_revision(
                terminal_record.record,
                workflow_state="active",
                updated_at="2026-08-31T10:30:00-04:00",
            ),
            expected=terminal_record.fingerprint,
        )


def test_proposed_planning_may_be_cancelled_without_activation(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    cancelled = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            created.record,
            workflow_state="cancelled",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    assert cancelled.record.status == "proposed"
    assert cancelled.record.field("workflow_state") == "cancelled"


def test_proposed_root_cannot_enter_active_workflow_state(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="activate canonical lifecycle",
    ):
        service.transition_workflow_state(
            work_ref(),
            _workflow_revision(
                created.record,
                workflow_state="active",
                updated_at=WORKFLOW_UPDATE_1,
            ),
            expected=created.fingerprint,
        )


def test_workflow_state_rejects_illegal_planning_to_paused(
    tmp_path: Path,
) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    with pytest.raises(WorkflowPrerequisiteError, match="illegal"):
        service.transition_workflow_state(
            work_ref(),
            _workflow_revision(
                current.record,
                workflow_state="paused",
                updated_at=WORKFLOW_UPDATE_1,
            ),
            expected=current.fingerprint,
        )


def test_workflow_state_revision_cannot_rewrite_summary(tmp_path: Path) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    with pytest.raises(WorkflowPrerequisiteError, match="summary"):
        service.transition_workflow_state(
            work_ref(),
            _workflow_revision(
                current.record,
                workflow_state="active",
                updated_at=WORKFLOW_UPDATE_1,
                summary="Illegally rewritten summary.",
            ),
            expected=current.fingerprint,
        )


def test_terminal_workflow_state_does_not_invalidate_current_representation(
    tmp_path: Path,
) -> None:
    service, _participant_service, _root, _candidate, _result = _activate_root(
        tmp_path
    )
    current = service.load_exact(work_ref())
    active = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            current.record,
            workflow_state="active",
            updated_at=WORKFLOW_UPDATE_1,
        ),
        expected=current.fingerprint,
    )
    completed = service.transition_workflow_state(
        work_ref(),
        _workflow_revision(
            active.record,
            workflow_state="completed",
            updated_at=WORKFLOW_UPDATE_2,
        ),
        expected=active.fingerprint,
    )
    qualified = service.require_current_use(work_ref())
    assert qualified.fingerprint == completed.fingerprint
    assert qualified.record.status == "active"
    assert qualified.record.field("workflow_state") == "completed"


# Slice 9e — proposed/planning Support Process root correction.
CORRECTION_UPDATE = "2026-08-31T10:35:00-04:00"


def corrected_work_ref(work_id: str = "sup_beta") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def _root_successor(
    prior: PortiaRecord,
    *,
    work_id: str = "sup_beta",
    reason: str,
    detail: str | None = None,
    summary: str | None = None,
    initiation: dict[str, object] | None = None,
    planned_start_date: str | None = None,
    status: str | None = None,
    workflow_state: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["work_id"] = work_id
    if summary is not None:
        wire["summary"] = summary
    if initiation is not None:
        wire["initiation"] = initiation
    if planned_start_date is not None:
        wire["planned_start_date"] = planned_start_date
    if status is not None:
        wire["status"] = status
    if workflow_state is not None:
        wire["workflow_state"] = workflow_state
    entry: dict[str, object] = {
        "work_ref": work_ref().to_dict(),
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    wire["supersedes"] = [entry]
    wire["created_at"] = CORRECTION_UPDATE
    wire["created_by"] = AGENT
    wire["updated_at"] = CORRECTION_UPDATE
    wire["updated_by"] = AGENT
    return parse_portia_record("support_process", "1", wire)


def _participant_for(
    work: ExactPortiaWorkRef,
    *,
    participant_id: str = "spp_beta",
    status: str = "proposed",
    updated_at: str = CORRECTION_UPDATE,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": work.class_id,
            "work_id": work.work_id,
            "participant_id": participant_id,
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic corrected-root learner",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": CORRECTION_UPDATE,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def test_root_summary_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected bounded synthetic support-process summary.",
    )
    result = service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_summary",
        operation_id="op_sup_slice9e_summary",
    )
    assert result.accepted_steps == (
        "step_history",
        "step_successor",
        "step_transition",
        "step_work",
    )
    assert service.load_exact(work_ref()).record.status == "superseded"
    current = service.load_exact(corrected_work_ref())
    assert current.record.status == "proposed"
    assert current.record.field("workflow_state") == "planning"
    assert current.record.field("summary") == (
        "Corrected bounded synthetic support-process summary."
    )


def test_root_correction_records_exact_lifecycle_reason(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected summary for transition reason coverage.",
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_reason",
        operation_id="op_sup_slice9e_reason",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_sup_slice9e_reason",
    )
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "summary_corrected",
    }


def test_root_initiation_correction_is_material_and_bounded(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="initiation_corrected",
        initiation={
            "kind": "other",
            "detail": "Corrected bounded initiating context.",
        },
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_initiation",
        operation_id="op_sup_slice9e_initiation",
    )
    accepted = service.load_exact(corrected_work_ref())
    assert accepted.record.field("initiation") == {
        "kind": "other",
        "detail": "Corrected bounded initiating context.",
    }


def test_root_planned_timing_correction_changes_planning_only(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="planned_timing_corrected",
        planned_start_date="2026-09-02",
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_timing",
        operation_id="op_sup_slice9e_timing",
    )
    accepted = service.load_exact(corrected_work_ref())
    assert accepted.record.field("planned_start_date") == "2026-09-02"
    assert accepted.record.field("workflow_state") == "planning"


def test_root_correction_reason_must_match_changed_fact(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="initiation_corrected",
        summary="Only the summary actually changed.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_sup_slice9e_reason_mismatch",
            operation_id="op_sup_slice9e_reason_mismatch",
        )


def test_root_correction_rejects_topology_heavy_reason(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="work_root_corrected",
        summary="Ownership/topology changes require their dedicated path.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="topology/migration"):
        service.correct(
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_sup_slice9e_topology",
            operation_id="op_sup_slice9e_topology",
        )


def test_root_correction_rejects_active_process(tmp_path: Path) -> None:
    service, _participants, _root, _candidate, _result = _activate_root(tmp_path)
    current = service.load_exact(work_ref())
    successor = _root_successor(
        current.record,
        reason="summary_corrected",
        summary="Attempted correction of an already active process.",
        status="proposed",
        workflow_state="planning",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="child-reconciliation"):
        service.correct(
            work_ref(),
            successor,
            expected=current.fingerprint,
            transition_id="lct_sup_slice9e_active",
            operation_id="op_sup_slice9e_active",
        )


def test_root_correction_rejects_proposed_root_with_children(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    participants = SupportProcessParticipantWorkflowService(tmp_path)
    participants.create(work_ref(), participant_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Correction would otherwise strand the existing child.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="no canonical child records"):
        service.correct(
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_sup_slice9e_children",
            operation_id="op_sup_slice9e_children",
        )


def test_root_correction_cannot_smuggle_workflow_state_progression(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected summary with invalid workflow progression.",
        workflow_state="active",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="remain planning"):
        service.correct(
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_sup_slice9e_state",
            operation_id="op_sup_slice9e_state",
        )


def test_exact_old_root_remains_historical_after_correction(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected summary retaining exact predecessor history.",
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_exact",
        operation_id="op_sup_slice9e_exact",
    )
    assert service.resolve_exact(work_ref()).record.status == "superseded"
    assert service.resolve_exact(corrected_work_ref()).record.status == "proposed"
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical lifecycle"):
        service.require_current_use(work_ref())


def test_corrected_root_can_bootstrap_participant_and_activate(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected root that will continue ordinary bootstrap.",
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_bootstrap_correction",
        operation_id="op_sup_slice9e_bootstrap_correction",
    )

    new_work = corrected_work_ref()
    participants = SupportProcessParticipantWorkflowService(tmp_path)
    proposed_participant = participants.create(
        new_work,
        _participant_for(new_work),
    )
    active_participant = _participant_for(
        new_work,
        status="active",
        updated_at="2026-08-31T10:40:00-04:00",
    )
    participants.transition_lifecycle(
        support_process_participant_reference(new_work, "spp_beta"),
        active_participant,
        expected=proposed_participant.fingerprint,
        transition_id="lct_spp_slice9e_bootstrap",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice9e_bootstrap",
    )

    current_root = service.load_exact(new_work)
    root_wire = current_root.record.to_dict()
    root_wire["status"] = "active"
    root_wire["updated_at"] = "2026-08-31T10:45:00-04:00"
    root_wire["updated_by"] = AGENT
    active_root = parse_portia_record("support_process", "1", root_wire)
    service.transition_lifecycle(
        new_work,
        active_root,
        expected=current_root.fingerprint,
        transition_id="lct_sup_slice9e_bootstrap_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice9e_bootstrap_active",
    )
    accepted = service.require_current_use(new_work)
    assert accepted.record.status == "active"
    assert service.resolve_exact(work_ref()).record.status == "superseded"


def test_completed_root_correction_replays_idempotently(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected root for idempotent operation replay.",
    )
    first = service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_replay",
        operation_id="op_sup_slice9e_replay",
    )
    replay = service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_replay",
        operation_id="op_sup_slice9e_replay",
    )
    assert replay.accepted_steps == first.accepted_steps
    assert service.load_exact(work_ref()).record.status == "superseded"
    assert service.load_exact(corrected_work_ref()).record.status == "proposed"


def test_corrected_active_root_accepts_need_and_goal_planning(tmp_path: Path) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(root_record())
    successor = _root_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected root for downstream Need and Goal planning.",
    )
    service.correct(
        work_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_sup_slice9e_downstream_correction",
        operation_id="op_sup_slice9e_downstream_correction",
    )

    new_work = corrected_work_ref()
    participants = SupportProcessParticipantWorkflowService(tmp_path)
    proposed_participant = participants.create(new_work, _participant_for(new_work))
    participants.transition_lifecycle(
        support_process_participant_reference(new_work, "spp_beta"),
        _participant_for(
            new_work,
            status="active",
            updated_at="2026-08-31T10:40:00-04:00",
        ),
        expected=proposed_participant.fingerprint,
        transition_id="lct_spp_slice9e_downstream",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice9e_downstream",
    )
    current_root = service.load_exact(new_work)
    root_wire = current_root.record.to_dict()
    root_wire["status"] = "active"
    root_wire["updated_at"] = "2026-08-31T10:45:00-04:00"
    root_wire["updated_by"] = AGENT
    service.transition_lifecycle(
        new_work,
        parse_portia_record("support_process", "1", root_wire),
        expected=current_root.fingerprint,
        transition_id="lct_sup_slice9e_downstream_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice9e_downstream_active",
    )

    need = parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": new_work.class_id,
            "work_id": new_work.work_id,
            "need_id": "spn_beta",
            "status": "active",
            "target": {"kind": "support_process"},
            "need_kind": "access",
            "description": "Synthetic bounded Need under corrected root.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-08-31T10:50:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-08-31T10:50:00-04:00",
            "updated_by": AGENT,
        },
    )
    goal = parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": new_work.class_id,
            "work_id": new_work.work_id,
            "goal_id": "spg_beta",
            "status": "active",
            "target": {"kind": "support_process"},
            "description": "Synthetic future objective under corrected root.",
            "planned_criteria": "Synthetic criteria for later human review.",
            "measurement_approach": "Synthetic later-review approach.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-08-31T10:55:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-08-31T10:55:00-04:00",
            "updated_by": AGENT,
        },
    )
    accepted_need = SupportNeedWorkflowService(tmp_path).create(new_work, need)
    accepted_goal = SupportGoalWorkflowService(tmp_path).create(new_work, goal)
    assert accepted_need.record.status == "active"
    assert accepted_goal.record.status == "active"


def test_proposed_root_correction_chain_preserves_exact_ancestry(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    alpha = service.create(root_record())
    beta = _root_successor(
        alpha.record,
        reason="summary_corrected",
        summary="First corrected summary.",
    )
    service.correct(
        work_ref(),
        beta,
        expected=alpha.fingerprint,
        transition_id="lct_sup_slice9e_chain_alpha",
        operation_id="op_sup_slice9e_chain_alpha",
    )
    beta_stored = service.load_exact(corrected_work_ref())
    beta_wire = beta_stored.record.to_dict()
    beta_wire["work_id"] = "sup_gamma"
    beta_wire["summary"] = "Second corrected summary."
    beta_wire["supersedes"] = [
        {
            "work_ref": corrected_work_ref().to_dict(),
            "reason": "summary_corrected",
        }
    ]
    beta_wire["created_at"] = "2026-08-31T10:40:00-04:00"
    beta_wire["created_by"] = AGENT
    beta_wire["updated_at"] = "2026-08-31T10:40:00-04:00"
    beta_wire["updated_by"] = AGENT
    gamma = parse_portia_record("support_process", "1", beta_wire)
    service.correct(
        corrected_work_ref(),
        gamma,
        expected=beta_stored.fingerprint,
        transition_id="lct_sup_slice9e_chain_beta",
        operation_id="op_sup_slice9e_chain_beta",
    )
    assert service.load_exact(work_ref()).record.status == "superseded"
    assert service.load_exact(corrected_work_ref()).record.status == "superseded"
    assert service.load_exact(corrected_work_ref("sup_gamma")).record.status == (
        "proposed"
    )
