from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import (
    RosterIssue,
    RosterReadError,
    RosterValidationError,
    create_roster,
)

from portia.identity import (
    CoreRosterResolver,
    InvalidRosterIdentifierError,
    RosterAccessError,
    RosterClassMismatchError,
    RosterMalformedError,
    RosterNotFoundError,
    RosterStudentNotFoundError,
)


def _students(
    *,
    student_id: str = "student_17",
    first_name: str = "Alex",
    last_name: str = "Smith",
    preferred_name: str = "",
) -> list[dict[str, str]]:
    return [
        {
            "student_id": student_id,
            "last_name": last_name,
            "first_name": first_name,
            "period": "2",
            "preferred_name": preferred_name,
        }
    ]


def test_exact_class_and_student_resolution_uses_core_public_roster_api(tmp_path: Path) -> None:
    roster = create_roster("class_a", _students())
    write_class_roster(tmp_path, roster)

    resolved = CoreRosterResolver(tmp_path).resolve("class_a", "student_17")

    assert resolved.reference.class_id == "class_a"
    assert resolved.reference.student_id == "student_17"
    assert resolved.student.class_id == "class_a"
    assert resolved.student.student_id == "student_17"


def test_same_local_student_id_in_two_classes_remains_two_identities(tmp_path: Path) -> None:
    write_class_roster(tmp_path, create_roster("class_a", _students(first_name="Alex")))
    write_class_roster(tmp_path, create_roster("class_b", _students(first_name="Alex")))
    resolver = CoreRosterResolver(tmp_path)

    first = resolver.resolve("class_a", "student_17")
    second = resolver.resolve("class_b", "student_17")

    assert first.reference != second.reference
    assert first.student.class_id == "class_a"
    assert second.student.class_id == "class_b"


def test_matching_display_and_preferred_names_do_not_merge_roster_identity(
    tmp_path: Path,
) -> None:
    write_class_roster(
        tmp_path,
        create_roster(
            "class_a",
            _students(student_id="student_a", preferred_name="Sam"),
        ),
    )
    write_class_roster(
        tmp_path,
        create_roster(
            "class_b",
            _students(student_id="student_b", preferred_name="Sam"),
        ),
    )
    resolver = CoreRosterResolver(tmp_path)

    first = resolver.resolve("class_a", "student_a")
    second = resolver.resolve("class_b", "student_b")

    assert first.reference != second.reference
    assert not hasattr(resolver, "resolve_by_name")
    assert not hasattr(resolver, "find_best_match")


def test_student_identifier_matching_is_exact_without_case_or_whitespace_normalization(
    tmp_path: Path,
) -> None:
    write_class_roster(
        tmp_path,
        create_roster("class_a", _students(student_id="Student_17")),
    )
    resolver = CoreRosterResolver(tmp_path)

    assert resolver.resolve("class_a", "Student_17").reference.student_id == "Student_17"
    with pytest.raises(RosterStudentNotFoundError):
        resolver.resolve("class_a", "student_17")
    with pytest.raises(InvalidRosterIdentifierError):
        resolver.resolve("class_a", " Student_17 ")


def test_name_change_does_not_change_class_qualified_identity(tmp_path: Path) -> None:
    write_class_roster(
        tmp_path,
        create_roster("class_a", _students(first_name="Alex", preferred_name="Lex")),
    )
    before = CoreRosterResolver(tmp_path).resolve("class_a", "student_17")

    write_class_roster(
        tmp_path,
        create_roster("class_a", _students(first_name="Alexandra", preferred_name="A")),
        overwrite=True,
    )
    after = CoreRosterResolver(tmp_path).resolve("class_a", "student_17")

    assert before.reference == after.reference
    assert before.student.first_name != after.student.first_name


def test_absent_student_is_distinct_from_absent_roster(tmp_path: Path) -> None:
    write_class_roster(tmp_path, create_roster("class_a", _students()))
    resolver = CoreRosterResolver(tmp_path)

    with pytest.raises(RosterStudentNotFoundError):
        resolver.resolve("class_a", "student_missing")
    with pytest.raises(RosterNotFoundError):
        resolver.resolve("class_missing", "student_17")


def test_invalid_identifier_fails_before_roster_access(tmp_path: Path) -> None:
    resolver = CoreRosterResolver(tmp_path)

    with pytest.raises(InvalidRosterIdentifierError):
        resolver.resolve("../class_a", "student_17")
    with pytest.raises(InvalidRosterIdentifierError):
        resolver.resolve("class_a", "student 17")


def test_malformed_roster_is_distinct_from_access_failure(tmp_path: Path) -> None:
    def malformed_loader(_root: str | Path, _class_id: str):
        raise RosterValidationError(
            (RosterIssue(code="bad_data", message="synthetic malformed roster"),)
        )

    def denied_loader(_root: str | Path, _class_id: str):
        try:
            raise PermissionError("synthetic denied")
        except PermissionError as cause:
            raise RosterReadError(tmp_path / "roster.csv", "synthetic denied") from cause

    with pytest.raises(RosterMalformedError):
        CoreRosterResolver(tmp_path, loader=malformed_loader).resolve(
            "class_a", "student_17"
        )
    with pytest.raises(RosterAccessError):
        CoreRosterResolver(tmp_path, loader=denied_loader).resolve(
            "class_a", "student_17"
        )


def test_returned_wrong_class_is_rejected_even_when_student_id_exists(tmp_path: Path) -> None:
    wrong = create_roster("class_b", _students())

    def wrong_loader(_root: str | Path, _class_id: str):
        return wrong

    with pytest.raises(RosterClassMismatchError):
        CoreRosterResolver(tmp_path, loader=wrong_loader).resolve(
            "class_a", "student_17"
        )


def test_core_class_mismatch_validation_error_maps_to_integrity_failure(tmp_path: Path) -> None:
    def mismatch_loader(_root: str | Path, _class_id: str):
        raise RosterValidationError(
            (
                RosterIssue(
                    code="class_id_mismatch",
                    message="synthetic authoritative mismatch",
                ),
            )
        )

    with pytest.raises(RosterClassMismatchError):
        CoreRosterResolver(tmp_path, loader=mismatch_loader).load_roster("class_a")


def test_roster_lookup_has_no_portia_canonical_write_side_effect(tmp_path: Path) -> None:
    write_class_roster(tmp_path, create_roster("class_a", _students()))
    portia_root = tmp_path / "portia"
    assert not portia_root.exists()

    CoreRosterResolver(tmp_path).resolve("class_a", "student_17")

    assert not portia_root.exists()
