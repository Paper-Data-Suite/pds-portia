from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import RosterNotFoundError
from portia.models import parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef, RosterStudentRef
from portia.storage.repository import PortiaRepository
from portia.views import (
    StudentTimelineQuery,
    StudentViewScope,
    StudentWorkDiscoveryService,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
    relationship_record,
)


def _write_roster(
    root: Path,
    class_id: str,
    *student_ids: str,
) -> None:
    write_class_roster(
        root,
        create_roster(
            class_id,
            [
                {
                    "student_id": student_id,
                    "last_name": "Synthetic",
                    "first_name": "Student",
                    "period": "2",
                }
                for student_id in student_ids
            ],
        ),
    )


def _student(
    class_id: str = "class_a",
    student_id: str = "student_1",
) -> RosterStudentRef:
    return RosterStudentRef(class_id=class_id, student_id=student_id)


def _event_subject(
    class_id: str,
    student_id: str,
    *,
    display_name: str = "Same Display",
) -> dict[str, object]:
    return {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": class_id,
            "student_id": student_id,
        },
        "display_snapshot": {"display_name": display_name},
    }


def _support_ref(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def _support_root(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
):
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
            "status": "active",
            "workflow_state": "active",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _support_participant(
    *,
    participant_id: str = "spp_alpha",
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
):
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
            "status": "active",
            "person": person
            or {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": class_id,
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Same Display"},
            },
            "contexts": contexts or [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _query(
    *students: RosterStudentRef,
    allowed_class_ids: tuple[str, ...] = (),
    exact_works: tuple[ExactPortiaWorkRef, ...] = (),
) -> StudentTimelineQuery:
    return StudentTimelineQuery(
        scope=StudentViewScope(
            focal_students=students,
            allowed_class_ids=allowed_class_ids,
        ),
        exact_works=exact_works,
    )


def _seed_event(
    root: Path,
    *,
    class_id: str,
    event_id: str,
    participant_id: str,
    student_class_id: str,
    student_id: str,
) -> None:
    repository = PortiaRepository(root)
    work = event_ref(class_id=class_id, event_id=event_id)
    repository.create_work(
        work,
        event_record(class_id=class_id, event_id=event_id),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id=participant_id,
            class_id=class_id,
            event_id=event_id,
            subject=_event_subject(student_class_id, student_id),
        ),
    )


def test_default_single_class_discovers_only_exact_focal_membership(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1", "student_2")
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        student_class_id="class_a",
        student_id="student_1",
    )
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_other",
        participant_id="ep_other",
        student_class_id="class_a",
        student_id="student_2",
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    assert result.resolved_students == (_student(),)
    assert [work.work_ref.work_id for work in result.works] == ["evt_alpha"]
    match = result.works[0].focal_matches[0]
    assert match.student_ref == _student()
    assert match.participant_ref.record_ref.record_id == "ep_alpha"


def test_same_display_name_or_actor_identity_does_not_create_focal_match(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    repository = PortiaRepository(tmp_path)
    work = event_ref(event_id="evt_alpha")
    repository.create_work(work, event_record(event_id="evt_alpha"))
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_descriptive",
            event_id="evt_alpha",
            subject={
                "kind": "descriptive_person",
                "description_type": "visitor",
                "display_label": "Synthetic Student",
            },
        ),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_actor",
            event_id="evt_alpha",
            subject={
                "kind": "actor",
                "actor_ref": {"actor_id": "actr_same_name"},
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
        ),
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    assert result.works == ()


def test_same_local_student_id_in_two_classes_is_never_merged(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    _write_roster(tmp_path, "class_b", "student_1")
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_a",
        participant_id="ep_a",
        student_class_id="class_a",
        student_id="student_1",
    )
    _seed_event(
        tmp_path,
        class_id="class_b",
        event_id="evt_b",
        participant_id="ep_b",
        student_class_id="class_b",
        student_id="student_1",
    )

    only_a = StudentWorkDiscoveryService(tmp_path).discover(
        _query(_student("class_a", "student_1"))
    )
    both = StudentWorkDiscoveryService(tmp_path).discover(
        _query(
            _student("class_a", "student_1"),
            _student("class_b", "student_1"),
        )
    )

    assert [work.work_ref.work_id for work in only_a.works] == ["evt_a"]
    assert [work.work_ref.work_id for work in both.works] == ["evt_a", "evt_b"]
    matched_classes = {
        match.student_ref.class_id
        for work in both.works
        for match in work.focal_matches
    }
    assert matched_classes == {"class_a", "class_b"}


def test_cross_class_event_requires_deliberate_work_owner_scope(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_b", "student_1")
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_cross",
        participant_id="ep_cross",
        student_class_id="class_b",
        student_id="student_1",
    )
    service = StudentWorkDiscoveryService(tmp_path)

    default = service.discover(_query(_student("class_b", "student_1")))
    deliberate = service.discover(
        _query(
            _student("class_b", "student_1"),
            allowed_class_ids=("class_a",),
        )
    )

    assert default.works == ()
    assert [work.work_ref.work_id for work in deliberate.works] == ["evt_cross"]
    assert deliberate.works[0].focal_matches[0].student_ref.class_id == "class_b"
    assert deliberate.works[0].work_ref.class_id == "class_a"


def test_exact_work_narrowing_does_not_scan_other_matching_work(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    for event_id, participant_id in (
        ("evt_alpha", "ep_alpha"),
        ("evt_beta", "ep_beta"),
    ):
        _seed_event(
            tmp_path,
            class_id="class_a",
            event_id=event_id,
            participant_id=participant_id,
            student_class_id="class_a",
            student_id="student_1",
        )

    selected = event_ref(event_id="evt_beta")
    result = StudentWorkDiscoveryService(tmp_path).discover(
        _query(_student(), exact_works=(selected,))
    )

    assert result.work_refs == (selected,)


def test_support_process_match_preserves_context_without_recasting_role(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    repository = PortiaRepository(tmp_path)
    work = _support_ref()
    repository.create_work(work, _support_root())
    repository.create_work_record(
        work,
        _support_participant(
            contexts=[
                {"kind": "supported_person"},
                {"kind": "observer"},
            ]
        ),
    )
    repository.create_work_record(
        work,
        _support_participant(
            participant_id="spp_collaborator",
            person={
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    assert [item.work_ref.work_id for item in result.works] == ["sup_alpha"]
    match = result.works[0].focal_matches[0]
    assert match.participant_ref.record_ref.record_id == "spp_alpha"
    assert match.contexts == ("supported_person", "observer")


def test_focal_roster_participant_remains_exact_even_when_context_is_collaborator(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    repository = PortiaRepository(tmp_path)
    work = _support_ref()
    repository.create_work(work, _support_root())
    repository.create_work_record(
        work,
        _support_participant(contexts=[{"kind": "provider_or_collaborator"}]),
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    match = result.works[0].focal_matches[0]
    assert match.student_ref == _student()
    assert match.contexts == ("provider_or_collaborator",)


def test_related_work_is_context_only_when_both_works_match_independently(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1", "student_2")
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        student_class_id="class_a",
        student_id="student_1",
    )
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_beta",
        participant_id="ep_beta",
        student_class_id="class_a",
        student_id="student_1",
    )
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_unrelated",
        participant_id="ep_unrelated",
        student_class_id="class_a",
        student_id="student_2",
    )
    repository = PortiaRepository(tmp_path)
    repository.create_work_record(
        event_ref(event_id="evt_alpha"),
        relationship_record(
            source_event="evt_alpha",
            target_event="evt_beta",
            relationship_id="rel_in_scope",
        ),
    )
    repository.create_work_record(
        event_ref(event_id="evt_alpha"),
        relationship_record(
            source_event="evt_alpha",
            target_event="evt_unrelated",
            relationship_id="rel_outside_focal",
        ),
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    assert result.work_refs == (
        event_ref(event_id="evt_alpha"),
        event_ref(event_id="evt_beta"),
    )
    alpha = result.works[0]
    relationship_ids = [
        item.relationship_ref.record_ref.record_id
        for item in alpha.related_context
    ]
    assert relationship_ids == ["rel_in_scope"]
    assert alpha.related_context[0].target_work == event_ref(event_id="evt_beta")


def test_related_work_target_outside_scope_is_never_loaded_or_traversed(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    _seed_event(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        student_class_id="class_a",
        student_id="student_1",
    )
    repository = PortiaRepository(tmp_path)
    repository.create_work_record(
        event_ref(event_id="evt_alpha"),
        relationship_record(
            source_event="evt_alpha",
            target_event="evt_missing",
            relationship_id="rel_missing_target",
        ),
    )

    result = StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))

    assert result.work_refs == (event_ref(event_id="evt_alpha"),)
    assert result.works[0].related_context == ()


def test_missing_roster_authority_is_not_treated_as_empty_history(
    tmp_path: Path,
) -> None:
    with pytest.raises(RosterNotFoundError):
        StudentWorkDiscoveryService(tmp_path).discover(_query(_student()))


def test_explicit_legacy_work_discovery_fails_closed_until_history_slice(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    legacy = event_ref(version="1")
    query = StudentTimelineQuery(
        scope=StudentViewScope(
            focal_students=(_student(),),
            allowed_works=(legacy,),
            history_allowed=True,
        ),
        mode="history",
        exact_works=(legacy,),
    )

    with pytest.raises(
        PortiaLocalValidationError,
        match="history expansion is deferred",
    ):
        StudentWorkDiscoveryService(tmp_path).discover(query)
