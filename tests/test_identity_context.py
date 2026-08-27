from __future__ import annotations

from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import (
    CoreRosterResolver,
    ResolvedIdentityValidationContext,
    RosterSnapshotValidationContext,
)
from portia.models.references import RosterStudentRef


def _roster(class_id: str):
    return create_roster(
        class_id,
        [
            {
                "student_id": "student_1",
                "last_name": "Example",
                "first_name": "A",
                "period": "1",
            }
        ],
    )


def test_positive_resolution_context_does_not_turn_unchecked_identity_into_absence(
    tmp_path: Path,
) -> None:
    write_class_roster(tmp_path, _roster("class_a"))
    resolved = CoreRosterResolver(tmp_path).resolve("class_a", "student_1")
    context = ResolvedIdentityValidationContext.from_resolutions(resolved)

    assert context.roster_student_exists(resolved.reference) is True
    assert (
        context.roster_student_exists(
            RosterStudentRef(class_id="class_a", student_id="student_unknown")
        )
        is None
    )
    assert (
        context.roster_student_exists(
            RosterStudentRef(class_id="class_b", student_id="student_1")
        )
        is None
    )


def test_complete_roster_snapshot_can_authoritatively_report_absence_in_loaded_class() -> None:
    context = RosterSnapshotValidationContext.from_rosters(_roster("class_a"))

    assert (
        context.roster_student_exists(
            RosterStudentRef(class_id="class_a", student_id="student_1")
        )
        is True
    )
    assert (
        context.roster_student_exists(
            RosterStudentRef(class_id="class_a", student_id="student_missing")
        )
        is False
    )
    assert (
        context.roster_student_exists(
            RosterStudentRef(class_id="class_b", student_id="student_1")
        )
        is None
    )


def _relationship_record(class_id: str, student_id: str):
    from portia.models import parse_portia_record

    agent = {"type": "system_process", "process_id": "identity_context_test"}
    return parse_portia_record(
        "actor_student_relationship",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor_student_relationship",
            "module_id": "portia",
            "actor_id": "actr_context",
            "relationship_id": "asrel_context",
            "status": "active",
            "student_ref": {"class_id": class_id, "student_id": student_id},
            "relationship": {"type": "caregiver"},
            "basis": {"kind": "local_operator_knowledge"},
            "review": {
                "kind": "locally_reviewed",
                "reviewed_at": "2026-08-26T12:00:00-04:00",
                "reviewed_by": agent,
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-08-26T12:00:00-04:00",
            "created_by": agent,
            "updated_at": "2026-08-26T12:00:00-04:00",
            "updated_by": agent,
        },
    )


def test_identity_context_flows_through_graph_validation_without_core_io(
    monkeypatch: object,
) -> None:
    from portia.validation import validate_record_graph

    def forbidden_core_io(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("graph validation attempted Core roster I/O")

    monkeypatch.setattr(  # type: ignore[attr-defined]
        "pds_core.classes.load_class_roster", forbidden_core_io
    )
    record = _relationship_record("class_a", "student_1")
    present = RosterSnapshotValidationContext.from_rosters(_roster("class_a"))
    present_codes = {
        finding.code for finding in validate_record_graph([record], context=present)
    }
    assert "PORTIA.GRAPH.ROSTER_STUDENT_UNRESOLVED" not in present_codes

    absent_roster = create_roster(
        "class_a",
        [
            {
                "student_id": "student_other",
                "last_name": "Other",
                "first_name": "Student",
                "period": "1",
            }
        ],
    )
    absent = RosterSnapshotValidationContext.from_rosters(absent_roster)
    absent_codes = {
        finding.code for finding in validate_record_graph([record], context=absent)
    }
    assert "PORTIA.GRAPH.ROSTER_STUDENT_UNRESOLVED" in absent_codes
