"""Final focused Issue #44 runtime acceptance paths."""

from __future__ import annotations

import json
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    intervention_reference,
    support_process_participant_reference,
)

AGENT = {"type": "local_operator", "display_label": "Synthetic Teacher"}
INTERVENTION_FIXTURE = Path(
    "tests/schema_validation/fixtures/issue-18/intervention/valid/"
    "active-recurring-assigned.json"
)
CROSS_CLASS_FIXTURE = Path(
    "tests/schema_validation/fixtures/issue-18/support-process-participant/valid/"
    "cross-class-roster-student.json"
)


def _work(
    class_id: str = "english10_p2",
    work_id: str = "sup_support_1",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def _root_record(
    *,
    class_id: str = "english10_p2",
    work_id: str = "sup_support_1",
    status: str = "proposed",
    created_at: str = "2026-09-02T08:00:00-04:00",
    updated_at: str | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": work_id,
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": "planning",
            "summary": "Synthetic bounded support-planning acceptance root.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic bounded planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": AGENT,
            "updated_at": updated_at or created_at,
            "updated_by": AGENT,
        },
    )


def _participant_record(
    participant_id: str,
    *,
    person: dict[str, object],
    contexts: list[dict[str, object]],
    status: str = "proposed",
    created_at: str,
    updated_at: str,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "english10_p2",
            "work_id": "sup_support_1",
            "participant_id": participant_id,
            "status": status,
            "person": person,
            "contexts": contexts,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _activate_participant(
    root: Path,
    proposed: PortiaRecord,
    active: PortiaRecord,
) -> None:
    work = _work()
    participant_id = active.logical_id
    assert participant_id is not None
    service = SupportProcessParticipantWorkflowService(root)
    created = service.create(work, proposed)
    service.transition_lifecycle(
        support_process_participant_reference(work, participant_id),
        active,
        expected=created.fingerprint,
        transition_id=f"lct_{participant_id}_issue44_acceptance",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_issue44_acceptance",
    )


def _activate_root(root: Path) -> None:
    service = SupportProcessWorkflowService(root)
    created = service.create(_root_record())
    service.transition_lifecycle(
        _work(),
        _root_record(
            status="active",
            updated_at="2026-09-02T08:03:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_sup_support_1_issue44_acceptance",
        reason_code="planning_confirmed",
        operation_id="op_sup_support_1_issue44_acceptance",
    )


def _target(participant_id: str) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def _need_record() -> PortiaRecord:
    return parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": "english10_p2",
            "work_id": "sup_support_1",
            "need_id": "spn_access_1",
            "status": "active",
            "target": _target("spp_student_1"),
            "need_kind": "access",
            "description": "Synthetic bounded access need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-02T08:05:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-09-02T08:05:00-04:00",
            "updated_by": AGENT,
        },
    )


def _goal_record() -> PortiaRecord:
    return parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": "english10_p2",
            "work_id": "sup_support_1",
            "goal_id": "spg_routine_1",
            "status": "active",
            "target": _target("spp_student_1"),
            "description": "Synthetic bounded future routine objective.",
            "planned_criteria": "Review the planned bounded routine.",
            "measurement_approach": "Teacher review of later implementation records.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-02T08:06:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-09-02T08:06:00-04:00",
            "updated_by": AGENT,
        },
    )


def _bootstrap_intervention_dependencies(root: Path) -> None:
    student_proposed = _participant_record(
        "spp_student_1",
        person={
            "kind": "descriptive_person",
            "description_type": "outside_student",
            "display_label": "Synthetic learner",
        },
        contexts=[{"kind": "supported_person"}],
        created_at="2026-09-02T08:01:00-04:00",
        updated_at="2026-09-02T08:01:00-04:00",
    )
    student_active_wire = student_proposed.to_dict()
    student_active_wire["status"] = "active"
    student_active = parse_portia_record(
        "support_process_participant",
        "1",
        student_active_wire,
    )

    provider_proposed = _participant_record(
        "spp_teacher_1",
        person={"kind": "local_operator", "display_label": "Synthetic Teacher"},
        contexts=[{"kind": "provider_or_collaborator"}],
        created_at="2026-09-02T08:02:00-04:00",
        updated_at="2026-09-02T08:02:00-04:00",
    )
    provider_active_wire = provider_proposed.to_dict()
    provider_active_wire["status"] = "active"
    provider_active = parse_portia_record(
        "support_process_participant",
        "1",
        provider_active_wire,
    )

    root_service = SupportProcessWorkflowService(root)
    root_service.create(_root_record())
    _activate_participant(root, student_proposed, student_active)
    _activate_participant(root, provider_proposed, provider_active)

    root_stored = root_service.load_exact(_work())
    root_service.transition_lifecycle(
        _work(),
        _root_record(
            status="active",
            updated_at="2026-09-02T08:03:00-04:00",
        ),
        expected=root_stored.fingerprint,
        transition_id="lct_sup_support_1_intervention_acceptance",
        reason_code="planning_confirmed",
        operation_id="op_sup_support_1_intervention_acceptance",
    )

    SupportNeedWorkflowService(root).create(_work(), _need_record())
    SupportGoalWorkflowService(root).create(_work(), _goal_record())


def test_exact_frozen_active_intervention_executes_through_production_service(
    tmp_path: Path,
) -> None:
    _bootstrap_intervention_dependencies(tmp_path)

    fixture = json.loads(INTERVENTION_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(fixture, dict)
    intervention = parse_portia_record("intervention", "1", fixture)

    service = InterventionWorkflowService(tmp_path)
    created = service.create(_work(), intervention)
    current = service.require_current_use(
        intervention_reference(_work(), "int_routine_1")
    )

    assert created.record.to_dict() == fixture
    assert current.fingerprint == created.fingerprint
    assert current.record.field("plan_state") == "active"
    assert current.record.field("schedule")["kind"] == "recurring"
    assert current.record.field("provider_plan")["kind"] == "assigned"
    assert current.record.field("monitoring_approach")


def test_exact_cross_class_participant_uses_foreign_roster_without_owner_drift(
    tmp_path: Path,
) -> None:
    write_class_roster(
        tmp_path,
        create_roster(
            "english10_p2",
            [
                {
                    "student_id": "student_101",
                    "last_name": "Owner",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    write_class_roster(
        tmp_path,
        create_roster(
            "english10_p5",
            [
                {
                    "student_id": "student_205",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "5",
                }
            ],
        ),
    )

    root_service = SupportProcessWorkflowService(tmp_path)
    created_root = root_service.create(
        _root_record(
            created_at="2026-08-20T12:00:00-04:00",
            updated_at="2026-08-20T12:00:00-04:00",
        )
    )

    fixture = json.loads(CROSS_CLASS_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(fixture, dict)
    active = parse_portia_record(
        "support_process_participant",
        "1",
        fixture,
    )
    proposed_wire = active.to_dict()
    proposed_wire["status"] = "proposed"
    proposed = parse_portia_record(
        "support_process_participant",
        "1",
        proposed_wire,
    )

    participants = SupportProcessParticipantWorkflowService(tmp_path)
    created_participant = participants.create(_work(), proposed)
    participants.transition_lifecycle(
        support_process_participant_reference(_work(), "spp_student_1"),
        active,
        expected=created_participant.fingerprint,
        transition_id="lct_spp_student_1_cross_class_acceptance",
        reason_code="planning_confirmed",
        operation_id="op_spp_student_1_cross_class_acceptance",
    )

    root_service.transition_lifecycle(
        _work(),
        _root_record(
            status="active",
            created_at="2026-08-20T12:00:00-04:00",
            updated_at="2026-08-20T12:02:00-04:00",
        ),
        expected=created_root.fingerprint,
        transition_id="lct_sup_support_1_cross_class_acceptance",
        reason_code="planning_confirmed",
        operation_id="op_sup_support_1_cross_class_acceptance",
    )

    current = participants.require_current_use(
        support_process_participant_reference(_work(), "spp_student_1")
    )

    assert current.kind == "roster_student"
    assert current.authority is not None
    assert current.participant.record.to_dict() == fixture
    assert current.participant.record.class_id == "english10_p2"
    assert current.participant.record.work_id == "sup_support_1"
    person = current.participant.record.to_dict()["person"]
    assert person["roster_student_ref"]["class_id"] == "english10_p5"
    assert "classes/english10_p2/" in current.participant.path.as_posix()
    assert "classes/english10_p5/" not in current.participant.path.as_posix()
    assert root_service.require_current_use(_work()).record.status == "active"
