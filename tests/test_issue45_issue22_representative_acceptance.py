"""Issue #45 representative runtime acceptance for frozen Issue #22 graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    EventWorkflowService,
    FidelityWorkflowService,
    ImplementationWorkflowService,
    ParticipantWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    fidelity_reference,
    implementation_reference,
    support_process_participant_reference,
    support_process_reference,
    support_reference,
)

P22_08_ROOT = Path(
    "tests/fixtures/issue_22/positive/p22_08_support_positive_outcome"
)
P22_11_ROOT = Path(
    "tests/fixtures/issue_22/positive/p22_11_cross_year_support_continuation"
)


def _json(root: Path, name: str) -> dict[str, Any]:
    value = json.loads((root / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _record(
    root: Path,
    name: str,
    contract: str,
    version: str = "1",
) -> PortiaRecord:
    return parse_portia_record(contract, version, _json(root, name))


def _event_ref(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _bootstrap_p22_08_event(
    root: Path,
    *,
    event_file: str,
    participant_file: str,
) -> None:
    event = _record(P22_08_ROOT, event_file, "event", "2")
    participant = _record(
        P22_08_ROOT,
        participant_file,
        "event_participant",
        "3",
    )
    work = _event_ref(event)

    draft_wire = event.to_dict()
    draft_wire["status"] = "draft"
    draft = parse_portia_record("event", "2", draft_wire)

    events = EventWorkflowService(root)
    created = events.create(draft)
    ParticipantWorkflowService(root).create(work, participant)
    events.replace(event, expected=created.fingerprint)
    assert events.require_current_use(work).record.to_dict() == event.to_dict()


def _write_p22_08_roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "eng10_p2_2026",
            [
                {
                    "student_id": "stu_p22_001",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )


def _bootstrap_p22_08_planning(root: Path) -> ExactPortiaWorkRef:
    _write_p22_08_roster(root)
    _bootstrap_p22_08_event(
        root,
        event_file="event-baseline.json",
        participant_file="participant-baseline.json",
    )
    _bootstrap_p22_08_event(
        root,
        event_file="event-current.json",
        participant_file="participant-current.json",
    )

    fixture_root = _record(
        P22_08_ROOT,
        "support-process.json",
        "support_process",
    )
    work = support_process_reference(fixture_root)
    processes = SupportProcessWorkflowService(root)

    proposed_wire = fixture_root.to_dict()
    proposed_wire["status"] = "proposed"
    proposed_wire["workflow_state"] = "planning"
    proposed_wire["updated_at"] = proposed_wire["created_at"]
    proposed = parse_portia_record("support_process", "1", proposed_wire)
    created_root = processes.create(proposed)

    participants = SupportProcessParticipantWorkflowService(root)
    for index, filename in enumerate(
        (
            "support-participant-student.json",
            "support-participant-teacher.json",
        ),
        start=1,
    ):
        fixture_participant = _record(
            P22_08_ROOT,
            filename,
            "support_process_participant",
        )
        participant_id = fixture_participant.logical_id
        assert participant_id is not None
        proposed_participant_wire = fixture_participant.to_dict()
        proposed_participant_wire["status"] = "proposed"
        proposed_participant = parse_portia_record(
            "support_process_participant",
            "1",
            proposed_participant_wire,
        )
        created = participants.create(work, proposed_participant)
        participants.transition_lifecycle(
            support_process_participant_reference(work, participant_id),
            fixture_participant,
            expected=created.fingerprint,
            transition_id=f"lct_p22_08_issue45_participant_{index}",
            reason_code="planning_confirmed",
            operation_id=f"op_p22_08_issue45_participant_{index}",
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
        transition_id="lct_p22_08_issue45_process_active",
        reason_code="planning_confirmed",
        operation_id="op_p22_08_issue45_process_active",
    )
    active_planning_stored = processes.load_exact(work)
    processes.transition_workflow_state(
        work,
        fixture_root,
        expected=active_planning_stored.fingerprint,
    )

    SupportNeedWorkflowService(root).create(
        work,
        _record(P22_08_ROOT, "support-need.json", "support_need"),
    )
    SupportGoalWorkflowService(root).create(
        work,
        _record(P22_08_ROOT, "support-goal.json", "support_goal"),
    )
    SupportWorkflowService(root).create(
        work,
        _record(P22_08_ROOT, "support.json", "support"),
    )
    return work


def _materialize_p22_08_execution(
    root: Path,
) -> tuple[ExactPortiaWorkRef, tuple[PortiaRecord, ...], PortiaRecord]:
    work = _bootstrap_p22_08_planning(root)
    implementations = ImplementationWorkflowService(root)
    implementation_records: list[PortiaRecord] = []
    for name in ("imp_p22_positive_001.json", "imp_p22_positive_002.json"):
        fixture = _record(P22_08_ROOT, name, "implementation")
        created = implementations.create(work, fixture)
        implementation_id = fixture.logical_id
        assert implementation_id is not None
        current = implementations.require_current_use(
            implementation_reference(work, implementation_id)
        )
        assert created.record.to_dict() == fixture.to_dict()
        assert current.fingerprint == created.fingerprint
        implementation_records.append(current.record)

    fidelity_fixture = _record(P22_08_ROOT, "fidelity.json", "fidelity")
    fidelity = FidelityWorkflowService(root)
    created_fidelity = fidelity.create(work, fidelity_fixture)
    fidelity_id = fidelity_fixture.logical_id
    assert fidelity_id is not None
    current_fidelity = fidelity.require_current_use(
        fidelity_reference(work, fidelity_id)
    )
    assert created_fidelity.record.to_dict() == fidelity_fixture.to_dict()
    assert current_fidelity.fingerprint == created_fidelity.fingerprint
    return work, tuple(implementation_records), current_fidelity.record


def test_p22_08_round_trips_exact_implementation_and_fidelity_history(
    tmp_path: Path,
) -> None:
    work, implementations, fidelity = _materialize_p22_08_execution(tmp_path)

    assert [record.logical_id for record in implementations] == [
        "imp_p22_positive_001",
        "imp_p22_positive_002",
    ]
    assert all(
        record.field("execution_state") == "completed" for record in implementations
    )
    assert all(
        record.field("plan_ref")
        == {
            "record_kind": "support",
            "record_id": "spt_p22_positive_001",
            "contract_version": "1",
        }
        for record in implementations
    )
    assert all(
        record.field("actual_target")["record_ref"]["record_id"]
        == "spp_p22_positive_student_001"
        for record in implementations
    )
    assert all(
        record.field("implementation_provider")["participant_refs"][0]["record_id"]
        == "spp_p22_positive_teacher_001"
        for record in implementations
    )

    fidelity_wire = fidelity.to_dict()
    assert fidelity_wire["plan_ref"]["record_id"] == "spt_p22_positive_001"
    assert fidelity_wire["evaluator_ref"]["record_id"] == (
        "spp_p22_positive_teacher_001"
    )
    assert [
        value["record_id"]
        for value in fidelity_wire["scope"]["implementation_refs"]
    ] == ["imp_p22_positive_001", "imp_p22_positive_002"]
    assert [
        value["record_id"] for value in fidelity_wire["basis"]["record_refs"]
    ] == ["imp_p22_positive_001", "imp_p22_positive_002"]

    repository = PortiaRepository(tmp_path)
    paths = [
        item.path
        for item in ImplementationWorkflowService(tmp_path).list(work)
    ]
    assert len(paths) == 2
    assert paths[0] != paths[1]
    assert repository.list_work_records(work, "fidelity", version="1")


def test_p22_08_completion_and_fidelity_do_not_fabricate_or_imply_outcome(
    tmp_path: Path,
) -> None:
    work, implementations, fidelity = _materialize_p22_08_execution(tmp_path)
    repository = PortiaRepository(tmp_path)

    assert [record.field("execution_state") for record in implementations] == [
        "completed",
        "completed",
    ]
    assert fidelity.field("result") == "as_planned"
    frozen_outcome = _json(P22_08_ROOT, "outcome.json")
    assert frozen_outcome["result"] == "progress_observed"

    for contract in ("follow_up", "outcome", "reentry", "repair"):
        assert repository.list_work_records(work, contract, version="1") == ()

    assert "effective" not in fidelity.to_dict()
    assert "successful" not in fidelity.to_dict()
    assert all("effective" not in record.to_dict() for record in implementations)
    assert all("successful" not in record.to_dict() for record in implementations)


def _p22_11_work(class_id: str, work_id: str) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def _write_p22_11_roster(root: Path, year: str) -> None:
    context = _json(P22_11_ROOT, f"roster-{year}.json")
    class_id = context["class_id"]
    students = context["students"]
    assert isinstance(class_id, str)
    assert isinstance(students, list)
    rows: list[dict[str, str]] = []
    for student in students:
        assert isinstance(student, dict)
        student_id = student["student_id"]
        assert isinstance(student_id, str)
        rows.append(
            {
                "student_id": student_id,
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": "2",
            }
        )
    write_class_roster(root, create_roster(class_id, rows))


def _p22_11_proposed(contract: str, name: str) -> PortiaRecord:
    wire = _json(P22_11_ROOT, name)
    wire["status"] = "proposed"
    if contract == "support_process":
        wire["workflow_state"] = "planning"
    wire["updated_at"] = wire["created_at"]
    return parse_portia_record(contract, "1", wire)


def _activate_p22_11_participant(
    root: Path,
    work: ExactPortiaWorkRef,
    name: str,
) -> None:
    service = SupportProcessParticipantWorkflowService(root)
    proposed = _p22_11_proposed("support_process_participant", name)
    created = service.create(work, proposed)
    active_wire = proposed.to_dict()
    active_wire["status"] = "active"
    active = parse_portia_record(
        "support_process_participant",
        "1",
        active_wire,
    )
    participant_id = active.logical_id
    assert participant_id is not None
    service.transition_lifecycle(
        support_process_participant_reference(work, participant_id),
        active,
        expected=created.fingerprint,
        transition_id=f"lct_{participant_id}_issue45_p2211",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_issue45_p2211",
    )


def _activate_p22_11_root(
    root: Path,
    proposed: PortiaRecord,
) -> ExactPortiaWorkRef:
    service = SupportProcessWorkflowService(root)
    created = service.create(proposed)
    assert proposed.class_id is not None
    assert proposed.work_id is not None
    work = _p22_11_work(proposed.class_id, proposed.work_id)
    school_year = proposed.field("school_year")
    assert isinstance(school_year, str)
    year = school_year[:4]
    _activate_p22_11_participant(
        root,
        work,
        f"participant-student-{year}.json",
    )
    _activate_p22_11_participant(
        root,
        work,
        f"participant-teacher-{year}.json",
    )
    active_wire = proposed.to_dict()
    active_wire["status"] = "active"
    active = parse_portia_record("support_process", "1", active_wire)
    service.transition_lifecycle(
        work,
        active,
        expected=created.fingerprint,
        transition_id=f"lct_{work.work_id}_issue45_p2211",
        reason_code="planning_confirmed",
        operation_id=f"op_{work.work_id}_issue45_p2211",
    )
    return work


def _create_p22_11_planning_children(
    root: Path,
    work: ExactPortiaWorkRef,
    year: str,
) -> None:
    SupportNeedWorkflowService(root).create(
        work,
        _record(P22_11_ROOT, f"need-{year}.json", "support_need"),
    )
    SupportGoalWorkflowService(root).create(
        work,
        _record(P22_11_ROOT, f"goal-{year}.json", "support_goal"),
    )

    fixture_support = _record(P22_11_ROOT, f"support-{year}.json", "support")
    support_id = fixture_support.logical_id
    assert support_id is not None
    planned_wire = fixture_support.to_dict()
    planned_wire["plan_state"] = "planned"
    planned_wire["updated_at"] = planned_wire["created_at"]
    planned = parse_portia_record("support", "1", planned_wire)

    service = SupportWorkflowService(root)
    created = service.create(work, planned)
    reference = support_reference(work, support_id)
    if fixture_support.field("plan_state") == "active":
        service.transition_plan_state(
            reference,
            fixture_support,
            expected=created.fingerprint,
        )
        return

    active_wire = fixture_support.to_dict()
    active_wire["plan_state"] = "active"
    active_wire["updated_at"] = planned_wire["created_at"]
    active = parse_portia_record("support", "1", active_wire)
    active_stored = service.transition_plan_state(
        reference,
        active,
        expected=created.fingerprint,
    )
    service.transition_plan_state(
        reference,
        fixture_support,
        expected=active_stored.fingerprint,
    )


def _finish_p22_11_root(
    root: Path,
    work: ExactPortiaWorkRef,
    name: str,
) -> None:
    fixture_root = _record(P22_11_ROOT, name, "support_process")
    final_state = fixture_root.field("workflow_state")
    service = SupportProcessWorkflowService(root)
    current = service.load_exact(work)
    if final_state == "active":
        service.transition_workflow_state(
            work,
            fixture_root,
            expected=current.fingerprint,
        )
        return

    assert final_state == "completed"
    active_wire = fixture_root.to_dict()
    active_wire["workflow_state"] = "active"
    active_wire["updated_at"] = current.record.field("updated_at")
    active = parse_portia_record("support_process", "1", active_wire)
    active_stored = service.transition_workflow_state(
        work,
        active,
        expected=current.fingerprint,
    )
    service.transition_workflow_state(
        work,
        fixture_root,
        expected=active_stored.fingerprint,
    )


def _materialize_p22_11_planning(
    root: Path,
) -> tuple[ExactPortiaWorkRef, ExactPortiaWorkRef]:
    _write_p22_11_roster(root, "2026")
    _write_p22_11_roster(root, "2027")

    prior = _p22_11_proposed("support_process", "process-2026.json")
    prior_ref = _activate_p22_11_root(root, prior)
    _create_p22_11_planning_children(root, prior_ref, "2026")
    _finish_p22_11_root(root, prior_ref, "process-2026.json")

    successor = _p22_11_proposed("support_process", "process-2027.json")
    successor_ref = _activate_p22_11_root(root, successor)
    _create_p22_11_planning_children(root, successor_ref, "2027")
    _finish_p22_11_root(root, successor_ref, "process-2027.json")
    return prior_ref, successor_ref


def _implementation_context(outcome: dict[str, Any]) -> dict[str, Any]:
    basis = outcome["basis"]
    assert isinstance(basis, list)
    for item in basis:
        assert isinstance(item, dict)
        if item.get("role") == "implementation_context":
            locator = item["locator"]
            assert isinstance(locator, dict)
            reference = locator["record_ref"]
            assert isinstance(reference, dict)
            return reference
    raise AssertionError("fixture Outcome lacks implementation_context")


def test_p22_11_keeps_each_years_implementation_under_its_exact_root(
    tmp_path: Path,
) -> None:
    prior_ref, successor_ref = _materialize_p22_11_planning(tmp_path)
    service = ImplementationWorkflowService(tmp_path)

    prior_fixture = _record(
        P22_11_ROOT,
        "implementation-2026.json",
        "implementation",
    )
    successor_fixture = _record(
        P22_11_ROOT,
        "implementation-2027.json",
        "implementation",
    )
    prior_created = service.create(prior_ref, prior_fixture)
    successor_created = service.create(successor_ref, successor_fixture)

    prior = service.require_current_use(
        implementation_reference(prior_ref, "imp_p22_crossyear_2026")
    )
    successor = service.require_current_use(
        implementation_reference(successor_ref, "imp_p22_crossyear_2027")
    )
    assert prior.fingerprint == prior_created.fingerprint
    assert successor.fingerprint == successor_created.fingerprint
    assert prior.record.to_dict() == prior_fixture.to_dict()
    assert successor.record.to_dict() == successor_fixture.to_dict()
    assert prior.record.logical_id != successor.record.logical_id
    assert prior.record.class_id != successor.record.class_id
    assert prior.record.work_id != successor.record.work_id
    assert prior.record.field("plan_ref")["record_id"] == "spt_p22_crossyear_2026"
    assert successor.record.field("plan_ref")["record_id"] == (
        "spt_p22_crossyear_2027"
    )
    assert prior.path != successor.path

    prior_outcome_ref = _implementation_context(
        _json(P22_11_ROOT, "outcome-2026.json")
    )
    successor_outcome_ref = _implementation_context(
        _json(P22_11_ROOT, "outcome-2027.json")
    )
    assert prior_outcome_ref["work_ref"] == prior_ref.to_dict()
    assert prior_outcome_ref["record_ref"]["record_id"] == (
        "imp_p22_crossyear_2026"
    )
    assert successor_outcome_ref["work_ref"] == successor_ref.to_dict()
    assert successor_outcome_ref["record_ref"]["record_id"] == (
        "imp_p22_crossyear_2027"
    )

    repository = PortiaRepository(tmp_path)
    for work in (prior_ref, successor_ref):
        for contract, version in (
            ("fidelity", "1"),
            ("follow_up", "1"),
            ("outcome", "1"),
            ("reentry", "1"),
            ("repair", "1"),
            ("record_migration", "1"),
            ("ownership_correction", "1"),
        ):
            assert repository.list_work_records(
                work,
                contract,
                version=version,
            ) == ()
