from __future__ import annotations

import json
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef, RosterStudentRef
from portia.storage import PortiaRepository
from portia.views import (
    StudentTimelineFilter,
    StudentTimelineQuery,
    StudentTimelineService,
    StudentViewScope,
)
from tests.workflow_helpers import event_record, event_ref, participant_record

_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "issue_22"
    / "positive"
    / "p22_04_correction_supersession_disagreement"
    / "records"
)


def _write_roster(root: Path, class_id: str, student_id: str) -> None:
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
            ],
        ),
    )


def _record_from_fixture(name: str):
    value = json.loads((_FIXTURE / name).read_text(encoding="utf-8"))
    version = str(value["schema_version"])
    contract = (
        str(value["work_kind"])
        if value["record_type"] == "portia_work"
        else str(value["record_type"])
    )
    return parse_portia_record(contract, version, value)


def _seed_correction_case(root: Path) -> tuple[ExactPortiaWorkRef, RosterStudentRef]:
    class_id = "eng10_p2_2026"
    student_id = "stu_p22_001"
    _write_roster(root, class_id, student_id)
    repository = PortiaRepository(root)
    event = _record_from_fixture("event.json")
    work = ExactPortiaWorkRef(
        class_id=class_id,
        work_id="evt_p22_correction_001",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(work, event)
    for name in (
        "participant.json",
        "account-predecessor.json",
        "account-successor.json",
        "disagreement.json",
        "transition-predecessor-active.json",
        "transition-predecessor-superseded.json",
        "transition-successor-active.json",
    ):
        repository.create_work_record(work, _record_from_fixture(name))
    return work, RosterStudentRef(class_id=class_id, student_id=student_id)


def _history_query(
    work: ExactPortiaWorkRef,
    student: RosterStudentRef,
) -> StudentTimelineQuery:
    return StudentTimelineQuery(
        StudentViewScope(
            focal_students=(student,),
            allowed_works=(work,),
            history_allowed=True,
        ),
        mode="history",
    )


def test_history_keeps_current_frontier_and_exact_correction_context(
    tmp_path: Path,
) -> None:
    work, student = _seed_correction_case(tmp_path)

    result = StudentTimelineService(tmp_path).generate(
        _history_query(work, student)
    )

    current_accounts = [
        entry.navigation.record_id
        for entry in result.entries
        if entry.history_kind == "current_representation"
        and entry.semantic_type == "account"
    ]
    assert current_accounts == ["acct_p22_corrected_blue"]

    predecessor = next(
        entry
        for entry in result.entries
        if entry.history_kind == "historical_representation"
        and entry.navigation.record_id == "acct_p22_original_red"
    )
    assert predecessor.status == "superseded"
    assert predecessor.semantic_type == "account"
    assert all(
        field.value is None
        for field in predecessor.fields
        if field.name == "content"
    )

    disagreement = next(
        entry
        for entry in result.entries
        if entry.history_kind == "statement_of_disagreement"
    )
    assert disagreement.disposition == "requires_manual_review"
    assert disagreement.target_refs == (predecessor.target_refs[0],)
    assert disagreement.fields == (
        disagreement.fields[0],
    )
    assert disagreement.fields[0].name == "statement"
    assert disagreement.fields[0].value is None

    selected_transitions = {
        entry.navigation.record_id
        for entry in result.entries
        if entry.history_kind == "lifecycle_transition"
        and any(
            field.name == "history_selection"
            and field.value == "selected"
            for field in entry.fields
        )
    }
    assert "lct_p22_original_superseded" in selected_transitions
    assert "lct_p22_corrected_active" in selected_transitions

    assert len(result.works) == 1
    assert result.works[0].history_available is True
    assert result.works[0].school_year == "2026-2027"


def test_current_view_exposes_history_indicator_but_not_history_detail(
    tmp_path: Path,
) -> None:
    work, student = _seed_correction_case(tmp_path)
    query = StudentTimelineQuery(
        StudentViewScope(
            focal_students=(student,),
            allowed_works=(work,),
        )
    )

    result = StudentTimelineService(tmp_path).generate(query)

    assert result.history is None
    assert result.works[0].history_available is True
    assert all(
        entry.history_kind == "current_representation"
        for entry in result.entries
    )


def test_history_filter_can_select_disagreement_without_widening_privacy(
    tmp_path: Path,
) -> None:
    work, student = _seed_correction_case(tmp_path)

    result = StudentTimelineService(tmp_path).generate(
        _history_query(work, student),
        filters=StudentTimelineFilter(
            record_families=("statement_of_disagreement",),
        ),
    )

    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.history_kind == "statement_of_disagreement"
    assert entry.disposition == "requires_manual_review"
    assert all(field.value is None for field in entry.fields)


def test_exceptional_removal_is_unavailable_not_reconstructed(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    repository.create_work_record(work, participant_record())

    missing_account_id = "acct_removed_history"
    disagreement = parse_portia_record(
        "statement_of_disagreement",
        "1",
        {
            "schema_version": "1",
            "record_type": "statement_of_disagreement",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "disagreement_id": "sod_removed_history",
            "status": "active",
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "account",
                    "record_id": missing_account_id,
                    "contract_version": "2",
                },
            },
            "source": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
            "positions": ["disputes_accuracy"],
            "statement": {
                "representation": "recorded_summary",
                "text": "Synthetic removed-history disagreement.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-20T12:00:00-04:00",
            "created_by": {
                "type": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "updated_at": "2026-09-20T12:00:00-04:00",
            "updated_by": {
                "type": "local_operator",
                "display_label": "Synthetic Teacher",
            },
        },
    )
    repository.create_work_record(work, disagreement)

    removal = parse_portia_record(
        "exceptional_removal",
        "1",
        {
            "schema_version": "1",
            "record_type": "exceptional_removal",
            "module_id": "portia",
            "class_id": "class_a",
            "removal_id": "rmv_removed_history",
            "target": {
                "kind": "work_record",
                "work_record_ref": {
                    "work_ref": work.to_dict(),
                    "record_ref": {
                        "record_kind": "account",
                        "record_id": missing_account_id,
                        "contract_version": "2",
                    },
                },
            },
            "reason": {
                "category": "privacy_requirement",
                "code": "prohibited_sensitive_payload",
            },
            "authorization": {
                "decision_reference": "synthetic-history-removal",
                "authorized_by": {
                    "type": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "content_evidence": {
                "kind": "salted_sha256",
                "salt": "c2FsdA==",
                "digest": "a" * 64,
                "byte_length": 1,
            },
            "lifecycle_snapshot": {"status": "invalidated"},
            "effective_at": "2026-09-20T12:30:00-04:00",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-20T12:31:00-04:00",
            "created_by": {
                "type": "local_operator",
                "display_label": "Synthetic Teacher",
            },
        },
    )
    repository.create_exceptional_removal(removal)

    result = StudentTimelineService(tmp_path).generate(
        StudentTimelineQuery(
            StudentViewScope(
                focal_students=(
                    RosterStudentRef(
                        class_id="class_a",
                        student_id="student_1",
                    ),
                ),
                allowed_works=(work,),
                history_allowed=True,
            ),
            mode="history",
        )
    )

    removed = next(
        entry
        for entry in result.entries
        if entry.history_kind == "exceptional_removal"
    )
    assert removed.disposition == "unavailable"
    assert removed.fields == ()
    assert removed.reason_code == "historical_representation_unavailable"
    assert removed.navigation.scope == "class_record"
    assert all(
        "Synthetic removed-history disagreement" != field.value
        for entry in result.entries
        for field in entry.fields
    )


def test_migration_context_does_not_follow_out_of_scope_legacy_source(
    tmp_path: Path,
) -> None:
    class_id = "eng10_g22_015"
    student_id = "stu_g22_015"
    _write_roster(tmp_path, class_id, student_id)
    repository = PortiaRepository(tmp_path)
    work = ExactPortiaWorkRef(
        class_id=class_id,
        work_id="evt_g22_015",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(
        work,
        parse_portia_record(
            "event",
            "2",
            json.loads(
                (
                    Path(__file__).parent
                    / "fixtures"
                    / "issue_22"
                    / "graph-invalid"
                    / "g22_015_migration_retargets_historical_ref"
                    / "event-v2.json"
                ).read_text(encoding="utf-8")
            ),
        ),
    )
    repository.create_work_record(
        work,
        participant_record(
            class_id=class_id,
            event_id="evt_g22_015",
            participant_id="ep_g22_015",
            subject={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": class_id,
                    "student_id": student_id,
                },
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
        ),
    )
    migration_value = json.loads(
        (
            Path(__file__).parent
            / "fixtures"
            / "issue_22"
            / "graph-invalid"
            / "g22_015_migration_retargets_historical_ref"
            / "migration.json"
        ).read_text(encoding="utf-8")
    )
    repository.create_work_record(
        work,
        parse_portia_record("record_migration", "1", migration_value),
    )

    result = StudentTimelineService(tmp_path).generate(
        _history_query(
            work,
            RosterStudentRef(class_id=class_id, student_id=student_id),
        )
    )

    migration = next(
        entry for entry in result.entries if entry.history_kind == "record_migration"
    )
    assert migration.target_refs == (work,)
    assert migration.reason_code == "record_migration_exists"
    assert migration.fields == ()


def test_legacy_history_does_not_infer_prior_membership(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a", "student_1")
    legacy = event_ref(version="1")
    query = StudentTimelineQuery(
        StudentViewScope(
            focal_students=(
                RosterStudentRef(class_id="class_a", student_id="student_1"),
            ),
            allowed_works=(legacy,),
            history_allowed=True,
        ),
        mode="history",
    )

    with pytest.raises(
        PortiaLocalValidationError,
        match="exact historical participant authority",
    ):
        StudentTimelineService(tmp_path).generate(query)
