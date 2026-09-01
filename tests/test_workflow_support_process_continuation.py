"""Issue #44 Slice 10b tests for exact cross-year continuation authority."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaNotFoundError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)
from portia.workflows.support_process_continuation import (
    support_process_continuation_ancestry,
    support_process_continuation_predecessor,
)

FIXTURE_ROOT = Path(
    "tests/fixtures/issue_22/positive/"
    "p22_11_cross_year_support_continuation"
)
AGENT = {"type": "system_process", "process_id": "issue44_slice10b_test"}
T0 = "2026-08-31T10:00:00-04:00"
T1 = "2026-08-31T10:05:00-04:00"
T2 = "2026-08-31T10:10:00-04:00"


def work_ref(class_id: str, work_id: str) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def root_record(
    *,
    class_id: str,
    work_id: str,
    school_year: str,
    continues_from: ExactPortiaWorkRef | None = None,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": work_id,
        "school_year": school_year,
        "status": "proposed",
        "workflow_state": "planning",
        "summary": "Synthetic bounded cross-year Support Process.",
        "initiation": {
            "kind": "teacher_identified_need",
            "detail": "Synthetic bounded new-year planning need.",
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": T0,
        "created_by": AGENT,
        "updated_at": T0,
        "updated_by": AGENT,
    }
    if continues_from is not None:
        wire["continues_from"] = continues_from.to_dict()
    return parse_portia_record("support_process", "1", wire)


def participant_record(
    *,
    class_id: str,
    work_id: str,
    participant_id: str,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": work_id,
            "participant_id": participant_id,
            "status": "proposed",
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic supported person",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": T0,
            "updated_by": AGENT,
        },
    )


def active_participant(record: PortiaRecord) -> PortiaRecord:
    wire = record.to_dict()
    wire["status"] = "active"
    wire["updated_at"] = T1
    return parse_portia_record("support_process_participant", "1", wire)


def active_root(record: PortiaRecord) -> PortiaRecord:
    wire = record.to_dict()
    wire["status"] = "active"
    wire["updated_at"] = T2
    return parse_portia_record("support_process", "1", wire)


def create_active_process(
    root: Path,
    record: PortiaRecord,
    *,
    participant_id: str,
) -> tuple[SupportProcessWorkflowService, ExactPortiaWorkRef]:
    service = SupportProcessWorkflowService(root)
    created = service.create(record)
    assert record.class_id is not None
    assert record.work_id is not None
    reference = work_ref(record.class_id, record.work_id)

    participant_service = SupportProcessParticipantWorkflowService(root)
    participant = participant_record(
        class_id=reference.class_id,
        work_id=reference.work_id,
        participant_id=participant_id,
    )
    stored_participant = participant_service.create(reference, participant)
    participant_service.transition_lifecycle(
        support_process_participant_reference(reference, participant_id),
        active_participant(participant),
        expected=stored_participant.fingerprint,
        transition_id=f"lct_{participant_id}_active",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_active",
    )
    service.transition_lifecycle(
        reference,
        active_root(record),
        expected=created.fingerprint,
        transition_id=f"lct_{reference.work_id}_active",
        reason_code="planning_confirmed",
        operation_id=f"op_{reference.work_id}_active",
    )
    return service, reference


def test_continuation_resolves_exact_predecessor_without_mutating_it(
    tmp_path: Path,
) -> None:
    prior_service = SupportProcessWorkflowService(tmp_path)
    stored_prior = prior_service.create(
        root_record(
            class_id="class_prior",
            work_id="sup_prior",
            school_year="2026-2027",
        )
    )
    prior_ref = work_ref("class_prior", "sup_prior")
    prior_bytes = prior_service.load_exact(prior_ref).fingerprint

    successor = root_record(
        class_id="class_next",
        work_id="sup_next",
        school_year="2027-2028",
        continues_from=prior_ref,
    )
    created = SupportProcessWorkflowService(tmp_path).create(successor)

    resolved = support_process_continuation_predecessor(
        PortiaRepository(tmp_path),
        created.record,
    )
    assert resolved is not None
    assert resolved.fingerprint == stored_prior.fingerprint
    assert prior_service.load_exact(prior_ref).fingerprint == prior_bytes
    assert prior_service.load_exact(prior_ref).record.status == "proposed"
    assert PortiaRepository(tmp_path).list_work_records(
        prior_ref,
        "lifecycle_transition",
        version="1",
    ) == ()


def test_missing_exact_continuation_predecessor_is_zero_write(
    tmp_path: Path,
) -> None:
    successor = root_record(
        class_id="class_next",
        work_id="sup_next",
        school_year="2027-2028",
        continues_from=work_ref("class_prior", "sup_missing"),
    )

    with pytest.raises(PortiaNotFoundError):
        SupportProcessWorkflowService(tmp_path).create(successor)

    assert not (
        tmp_path
        / "classes/class_next/modules/portia/work/sup_next/work.json"
    ).exists()


def test_continuation_never_substitutes_another_available_process(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(
        root_record(
            class_id="class_prior",
            work_id="sup_other",
            school_year="2026-2027",
        )
    )
    successor = root_record(
        class_id="class_next",
        work_id="sup_next",
        school_year="2027-2028",
        continues_from=work_ref("class_prior", "sup_requested"),
    )

    with pytest.raises(PortiaNotFoundError):
        SupportProcessWorkflowService(tmp_path).create(successor)


def test_continuation_requires_distinct_work_id_even_across_classes(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(
        root_record(
            class_id="class_prior",
            work_id="sup_same",
            school_year="2026-2027",
        )
    )
    successor = root_record(
        class_id="class_next",
        work_id="sup_same",
        school_year="2027-2028",
        continues_from=work_ref("class_prior", "sup_same"),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="distinct work_id",
    ):
        SupportProcessWorkflowService(tmp_path).create(successor)


def test_continuation_does_not_clone_predecessor_children(
    tmp_path: Path,
) -> None:
    prior_ref = work_ref("class_prior", "sup_prior")
    SupportProcessWorkflowService(tmp_path).create(
        root_record(
            class_id=prior_ref.class_id,
            work_id=prior_ref.work_id,
            school_year="2026-2027",
        )
    )
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        prior_ref,
        participant_record(
            class_id=prior_ref.class_id,
            work_id=prior_ref.work_id,
            participant_id="spp_prior",
        ),
    )

    next_ref = work_ref("class_next", "sup_next")
    SupportProcessWorkflowService(tmp_path).create(
        root_record(
            class_id=next_ref.class_id,
            work_id=next_ref.work_id,
            school_year="2027-2028",
            continues_from=prior_ref,
        )
    )

    assert participant_service.list(prior_ref)
    assert SupportProcessParticipantWorkflowService(tmp_path).list(next_ref) == ()


def test_continued_process_bootstraps_new_supported_person_and_activates(
    tmp_path: Path,
) -> None:
    prior_service, prior_ref = create_active_process(
        tmp_path,
        root_record(
            class_id="class_prior",
            work_id="sup_prior",
            school_year="2026-2027",
        ),
        participant_id="spp_prior",
    )
    prior_before = prior_service.load_exact(prior_ref)

    next_service, next_ref = create_active_process(
        tmp_path,
        root_record(
            class_id="class_next",
            work_id="sup_next",
            school_year="2027-2028",
            continues_from=prior_ref,
        ),
        participant_id="spp_next",
    )

    assert next_service.require_current_use(next_ref).record.status == "active"
    prior_after = prior_service.load_exact(prior_ref)
    assert prior_after.fingerprint == prior_before.fingerprint
    assert prior_after.record.status == "active"


def test_continued_root_accepts_new_year_need_and_goal_without_cloning(
    tmp_path: Path,
) -> None:
    _, prior_ref = create_active_process(
        tmp_path,
        root_record(
            class_id="class_prior",
            work_id="sup_prior",
            school_year="2026-2027",
        ),
        participant_id="spp_prior",
    )
    _, next_ref = create_active_process(
        tmp_path,
        root_record(
            class_id="class_next",
            work_id="sup_next",
            school_year="2027-2028",
            continues_from=prior_ref,
        ),
        participant_id="spp_next",
    )

    need = parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": next_ref.class_id,
            "work_id": next_ref.work_id,
            "need_id": "spn_next",
            "status": "proposed",
            "target": {"kind": "support_process"},
            "need_kind": "access",
            "description": "Synthetic current-year bounded Need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": T2,
            "created_by": AGENT,
            "updated_at": T2,
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
            "class_id": next_ref.class_id,
            "work_id": next_ref.work_id,
            "goal_id": "spg_next",
            "status": "proposed",
            "target": {"kind": "support_process"},
            "description": "Synthetic current-year bounded Goal.",
            "creation_source": {"type": "digital_entry"},
            "created_at": T2,
            "created_by": AGENT,
            "updated_at": T2,
            "updated_by": AGENT,
        },
    )

    SupportNeedWorkflowService(tmp_path).create(next_ref, need)
    SupportGoalWorkflowService(tmp_path).create(next_ref, goal)

    assert [item.record.logical_id for item in SupportNeedWorkflowService(
        tmp_path
    ).list(next_ref)] == ["spn_next"]
    assert [item.record.logical_id for item in SupportGoalWorkflowService(
        tmp_path
    ).list(next_ref)] == ["spg_next"]
    assert SupportNeedWorkflowService(tmp_path).list(prior_ref) == ()
    assert SupportGoalWorkflowService(tmp_path).list(prior_ref) == ()


def test_reverse_continuation_lookup_is_derived_from_forward_roots(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    prior_ref = work_ref("class_prior", "sup_prior")
    service.create(
        root_record(
            class_id=prior_ref.class_id,
            work_id=prior_ref.work_id,
            school_year="2026-2027",
        )
    )
    service.create(
        root_record(
            class_id="class_next",
            work_id="sup_next",
            school_year="2027-2028",
            continues_from=prior_ref,
        )
    )

    successors = tuple(
        item
        for item in service.list("class_next")
        if item.record.to_dict().get("continues_from") == prior_ref.to_dict()
    )
    assert [item.record.work_id for item in successors] == ["sup_next"]
    assert "continued_by" not in service.load_exact(prior_ref).record.to_dict()


def test_continuation_ancestry_resolves_multi_year_chain_exactly(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    first_ref = work_ref("class_2026", "sup_2026")
    second_ref = work_ref("class_2027", "sup_2027")
    third_ref = work_ref("class_2028", "sup_2028")

    service.create(
        root_record(
            class_id=first_ref.class_id,
            work_id=first_ref.work_id,
            school_year="2026-2027",
        )
    )
    service.create(
        root_record(
            class_id=second_ref.class_id,
            work_id=second_ref.work_id,
            school_year="2027-2028",
            continues_from=first_ref,
        )
    )
    third = service.create(
        root_record(
            class_id=third_ref.class_id,
            work_id=third_ref.work_id,
            school_year="2028-2029",
            continues_from=second_ref,
        )
    )

    ancestry = support_process_continuation_ancestry(
        PortiaRepository(tmp_path),
        third.record,
    )
    assert [
        (item.record.class_id, item.record.work_id)
        for item in ancestry
    ] == [
        ("class_2027", "sup_2027"),
        ("class_2026", "sup_2026"),
    ]


def _fixture(name: str) -> dict[str, object]:
    value = json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write_fixture_roster(root: Path, year: str) -> None:
    context = _fixture(f"roster-{year}.json")
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


def _proposed_fixture_record(contract: str, name: str) -> PortiaRecord:
    wire = _fixture(name)
    wire["status"] = "proposed"
    if contract == "support_process":
        wire["workflow_state"] = "planning"
    wire["updated_at"] = wire["created_at"]
    return parse_portia_record(contract, "1", wire)


def _activate_fixture_participant(
    root: Path,
    work: ExactPortiaWorkRef,
    name: str,
) -> None:
    service = SupportProcessParticipantWorkflowService(root)
    proposed = _proposed_fixture_record("support_process_participant", name)
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
        transition_id=f"lct_{participant_id}_p2211",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_p2211",
    )


def _activate_fixture_root(
    root: Path,
    proposed: PortiaRecord,
) -> ExactPortiaWorkRef:
    service = SupportProcessWorkflowService(root)
    created = service.create(proposed)
    assert proposed.class_id is not None
    assert proposed.work_id is not None
    work = work_ref(proposed.class_id, proposed.work_id)
    school_year = proposed.field("school_year")
    assert isinstance(school_year, str)
    year = school_year[:4]
    _activate_fixture_participant(
        root,
        work,
        f"participant-student-{year}.json",
    )
    _activate_fixture_participant(
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
        transition_id=f"lct_{work.work_id}_p2211",
        reason_code="planning_confirmed",
        operation_id=f"op_{work.work_id}_p2211",
    )
    return work


def test_p22_11_planning_subset_executes_through_production_services(
    tmp_path: Path,
) -> None:
    _write_fixture_roster(tmp_path, "2026")
    _write_fixture_roster(tmp_path, "2027")

    prior = _proposed_fixture_record("support_process", "process-2026.json")
    prior_ref = _activate_fixture_root(tmp_path, prior)

    successor = _proposed_fixture_record(
        "support_process",
        "process-2027.json",
    )
    successor_ref = _activate_fixture_root(tmp_path, successor)

    assert successor.field("continues_from") == prior_ref.to_dict()
    assert prior_ref != successor_ref

    for year, work in (("2026", prior_ref), ("2027", successor_ref)):
        SupportNeedWorkflowService(tmp_path).create(
            work,
            parse_portia_record("support_need", "1", _fixture(f"need-{year}.json")),
        )
        SupportGoalWorkflowService(tmp_path).create(
            work,
            parse_portia_record("support_goal", "1", _fixture(f"goal-{year}.json")),
        )
        SupportWorkflowService(tmp_path).create(
            work,
            parse_portia_record("support", "1", _fixture(f"support-{year}.json")),
        )

    prior_need_ids = {
        item.record.logical_id
        for item in SupportNeedWorkflowService(tmp_path).list(prior_ref)
    }
    next_need_ids = {
        item.record.logical_id
        for item in SupportNeedWorkflowService(tmp_path).list(successor_ref)
    }
    prior_goal_ids = {
        item.record.logical_id
        for item in SupportGoalWorkflowService(tmp_path).list(prior_ref)
    }
    next_goal_ids = {
        item.record.logical_id
        for item in SupportGoalWorkflowService(tmp_path).list(successor_ref)
    }
    prior_support_ids = {
        item.record.logical_id
        for item in SupportWorkflowService(tmp_path).list(prior_ref)
    }
    next_support_ids = {
        item.record.logical_id
        for item in SupportWorkflowService(tmp_path).list(successor_ref)
    }

    assert prior_need_ids.isdisjoint(next_need_ids)
    assert prior_goal_ids.isdisjoint(next_goal_ids)
    assert prior_support_ids.isdisjoint(next_support_ids)
    assert SupportProcessWorkflowService(tmp_path).load_exact(
        prior_ref
    ).record.status == "active"
    assert SupportProcessWorkflowService(tmp_path).load_exact(
        successor_ref
    ).record.status == "active"
