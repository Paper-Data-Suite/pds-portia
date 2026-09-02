"""Issue #44 production runtime parity for the P22-08 planning subset."""

from __future__ import annotations

import json
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    support_goal_reference,
    support_need_reference,
    support_process_participant_reference,
    support_process_reference,
    support_reference,
)

FIXTURE_ROOT = Path(
    "tests/fixtures/issue_22/positive/p22_08_support_positive_outcome"
)
CLASS_ID = "eng10_p2_2026"
STUDENT_ID = "stu_p22_001"


def _record(filename: str, contract: str, version: str) -> PortiaRecord:
    value = json.loads((FIXTURE_ROOT / filename).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return parse_portia_record(contract, version, value)


def _event_ref(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _write_fixture_roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            CLASS_ID,
            [
                {
                    "student_id": STUDENT_ID,
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )


def _bootstrap_event(
    root: Path,
    *,
    event_file: str,
    participant_file: str,
) -> ExactPortiaWorkRef:
    event = _record(event_file, "event", "2")
    participant = _record(participant_file, "event_participant", "3")
    work = _event_ref(event)

    draft_wire = event.to_dict()
    draft_wire["status"] = "draft"
    draft = parse_portia_record("event", "2", draft_wire)

    events = EventWorkflowService(root)
    created = events.create(draft)
    ParticipantWorkflowService(root).create(work, participant)
    events.replace(event, expected=created.fingerprint)

    assert events.require_current_use(work).record.to_dict() == event.to_dict()
    return work


def _bootstrap_support_process(root: Path) -> ExactPortiaWorkRef:
    fixture_root = _record("support-process.json", "support_process", "1")
    work = support_process_reference(fixture_root)
    processes = SupportProcessWorkflowService(root)

    proposed_wire = fixture_root.to_dict()
    proposed_wire["status"] = "proposed"
    proposed_wire["workflow_state"] = "planning"
    proposed_wire["updated_at"] = proposed_wire["created_at"]
    proposed = parse_portia_record("support_process", "1", proposed_wire)
    created_root = processes.create(proposed)

    participants = SupportProcessParticipantWorkflowService(root)
    participant_files = (
        "support-participant-student.json",
        "support-participant-teacher.json",
    )
    for index, filename in enumerate(participant_files, start=1):
        fixture_participant = _record(
            filename,
            "support_process_participant",
            "1",
        )
        assert fixture_participant.logical_id is not None

        proposed_participant_wire = fixture_participant.to_dict()
        proposed_participant_wire["status"] = "proposed"
        proposed_participant = parse_portia_record(
            "support_process_participant",
            "1",
            proposed_participant_wire,
        )
        created = participants.create(work, proposed_participant)
        participants.transition_lifecycle(
            support_process_participant_reference(
                work,
                fixture_participant.logical_id,
            ),
            fixture_participant,
            expected=created.fingerprint,
            transition_id=f"lct_p22_08_participant_{index}",
            reason_code="planning_confirmed",
            operation_id=f"op_p22_08_participant_{index}",
        )

    active_planning_wire = fixture_root.to_dict()
    active_planning_wire["workflow_state"] = "planning"
    active_planning = parse_portia_record(
        "support_process",
        "1",
        active_planning_wire,
    )
    processes.transition_lifecycle(
        work,
        active_planning,
        expected=created_root.fingerprint,
        transition_id="lct_p22_08_support_process_active",
        reason_code="planning_confirmed",
        operation_id="op_p22_08_support_process_active",
    )

    active_planning_stored = processes.load_exact(work)
    processes.transition_workflow_state(
        work,
        fixture_root,
        expected=active_planning_stored.fingerprint,
    )

    assert processes.require_current_use(work).record.to_dict() == (
        fixture_root.to_dict()
    )
    return work


def _persist_planning_subset(root: Path) -> ExactPortiaWorkRef:
    _write_fixture_roster(root)

    baseline_event = _bootstrap_event(
        root,
        event_file="event-baseline.json",
        participant_file="participant-baseline.json",
    )
    current_event = _bootstrap_event(
        root,
        event_file="event-current.json",
        participant_file="participant-current.json",
    )
    assert baseline_event.work_id == "evt_p22_support_baseline_001"
    assert current_event.work_id == "evt_p22_support_current_001"

    work = _bootstrap_support_process(root)

    need = _record("support-need.json", "support_need", "1")
    goal = _record("support-goal.json", "support_goal", "1")
    support = _record("support.json", "support", "1")

    SupportNeedWorkflowService(root).create(work, need)
    SupportGoalWorkflowService(root).create(work, goal)
    SupportWorkflowService(root).create(work, support)

    return work


def test_p22_08_planning_subset_round_trips_exact_fixture_records(
    tmp_path: Path,
) -> None:
    work = _persist_planning_subset(tmp_path)

    process = SupportProcessWorkflowService(tmp_path).require_current_use(work)
    student = SupportProcessParticipantWorkflowService(tmp_path).require_current_use(
        support_process_participant_reference(
            work,
            "spp_p22_positive_student_001",
        )
    )
    teacher = SupportProcessParticipantWorkflowService(tmp_path).require_current_use(
        support_process_participant_reference(
            work,
            "spp_p22_positive_teacher_001",
        )
    )
    need = SupportNeedWorkflowService(tmp_path).require_current_use(
        support_need_reference(work, "spn_p22_positive_001")
    )
    goal = SupportGoalWorkflowService(tmp_path).require_current_use(
        support_goal_reference(work, "spg_p22_positive_001")
    )
    support = SupportWorkflowService(tmp_path).require_current_use(
        support_reference(work, "spt_p22_positive_001")
    )

    assert process.record.to_dict() == _record(
        "support-process.json",
        "support_process",
        "1",
    ).to_dict()
    assert student.participant.record.to_dict() == _record(
        "support-participant-student.json",
        "support_process_participant",
        "1",
    ).to_dict()
    assert teacher.participant.record.to_dict() == _record(
        "support-participant-teacher.json",
        "support_process_participant",
        "1",
    ).to_dict()
    assert need.record.to_dict() == _record(
        "support-need.json",
        "support_need",
        "1",
    ).to_dict()
    assert goal.record.to_dict() == _record(
        "support-goal.json",
        "support_goal",
        "1",
    ).to_dict()
    assert support.record.to_dict() == _record(
        "support.json",
        "support",
        "1",
    ).to_dict()


def test_p22_08_planning_links_remain_exact_and_work_local(
    tmp_path: Path,
) -> None:
    work = _persist_planning_subset(tmp_path)
    process = SupportProcessWorkflowService(tmp_path).require_current_use(work)
    support = SupportWorkflowService(tmp_path).require_current_use(
        support_reference(work, "spt_p22_positive_001")
    )

    initiation = process.record.field("initiation")
    assert initiation["kind"] == "event_context"
    assert initiation["event_ref"]["work_id"] == "evt_p22_support_baseline_001"
    assert initiation["event_ref"]["contract_version"] == "2"

    assert support.record.field("target")["record_ref"]["record_id"] == (
        "spp_p22_positive_student_001"
    )
    assert support.record.field("need_refs") == (
        {
            "record_kind": "support_need",
            "record_id": "spn_p22_positive_001",
            "contract_version": "1",
        },
    )
    assert support.record.field("goal_refs") == (
        {
            "record_kind": "support_goal",
            "record_id": "spg_p22_positive_001",
            "contract_version": "1",
        },
    )
    assert support.record.field("provider_plan")["participant_refs"] == (
        {
            "record_kind": "support_process_participant",
            "record_id": "spp_p22_positive_teacher_001",
            "contract_version": "1",
        },
    )

    repository = SupportProcessWorkflowService(tmp_path).repository
    assert repository.list_work_relationships(work) == ()


def test_p22_08_planning_subset_does_not_fabricate_downstream_records(
    tmp_path: Path,
) -> None:
    work = _persist_planning_subset(tmp_path)
    repository = SupportProcessWorkflowService(tmp_path).repository

    for contract, version in (
        ("implementation", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("outcome", "1"),
    ):
        assert repository.list_work_records(
            work,
            contract,
            version=version,
        ) == ()

    process = SupportProcessWorkflowService(tmp_path).require_current_use(work)
    assert process.record.field("workflow_state") == "active"
