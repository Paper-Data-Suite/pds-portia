"""Exact class-qualified Core roster resolution for Portia."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from pds_core.classes import load_class_roster
from pds_core.identifiers import IdentifierValidationError, validate_identifier
from pds_core.rosters import (
    Roster,
    RosterError,
    RosterReadError,
    RosterValidationError,
    StudentRecord,
    student_lookup,
)

from portia.identity.errors import (
    InvalidRosterIdentifierError,
    RosterAccessError,
    RosterClassMismatchError,
    RosterMalformedError,
    RosterNotFoundError,
    RosterStudentNotFoundError,
)
from portia.models.references import RosterStudentRef

RosterLoader: TypeAlias = Callable[[str | Path, str], Roster]


@dataclass(frozen=True, slots=True)
class ResolvedRosterStudent:
    """One exact Core student resolved inside one authoritative class roster."""

    reference: RosterStudentRef
    student: StudentRecord


def _validate_requested_identifier(value: str, field: str) -> str:
    try:
        return validate_identifier(value, field)
    except (IdentifierValidationError, TypeError, ValueError) as exc:
        raise InvalidRosterIdentifierError(f"invalid {field}: {value!r}") from exc


def _is_missing_file(error: BaseException) -> bool:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, FileNotFoundError):
            return True
        current = current.__cause__
    return False


def _is_class_mismatch(error: RosterValidationError) -> bool:
    return any(
        issue.code in {"class_id_mismatch", "inconsistent_roster_class_id"}
        for issue in error.issues
    )


class CoreRosterResolver:
    """Resolve only exact ``(class_id, student_id)`` Core identities.

    Display names, preferred names, local student IDs without a class, and Actor
    records are intentionally absent from this API.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        loader: RosterLoader = load_class_roster,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self._loader = loader

    def load_roster(self, class_id: str) -> Roster:
        requested_class = _validate_requested_identifier(class_id, "class_id")
        try:
            roster = self._loader(self.workspace_root, requested_class)
        except RosterValidationError as exc:
            if _is_class_mismatch(exc):
                raise RosterClassMismatchError(
                    f"Core roster authority does not match requested class {requested_class!r}"
                ) from exc
            raise RosterMalformedError(
                f"Core roster for class {requested_class!r} failed validation"
            ) from exc
        except RosterReadError as exc:
            if _is_missing_file(exc):
                raise RosterNotFoundError(
                    f"Core roster for class {requested_class!r} is absent"
                ) from exc
            raise RosterAccessError(
                f"Core roster for class {requested_class!r} could not be read"
            ) from exc
        except RosterError as exc:
            raise RosterAccessError(
                f"Core roster for class {requested_class!r} could not be accessed"
            ) from exc
        except OSError as exc:
            raise RosterAccessError(
                f"Core roster for class {requested_class!r} could not be accessed"
            ) from exc

        if not isinstance(roster, Roster):
            raise RosterMalformedError("Core roster loader returned a non-Roster value")
        if roster.class_id != requested_class:
            raise RosterClassMismatchError(
                "Core roster class_id does not match the explicitly requested class: "
                f"requested={requested_class!r}, returned={roster.class_id!r}"
            )
        for student in roster.students:
            if not isinstance(student, StudentRecord):
                raise RosterMalformedError("Core roster contains a non-StudentRecord value")
            if student.class_id != requested_class:
                raise RosterClassMismatchError(
                    "Core student class_id does not match the authoritative roster class"
                )
        return roster

    def resolve_reference(
        self, reference: RosterStudentRef
    ) -> ResolvedRosterStudent:
        """Resolve one already-typed exact class-qualified roster reference."""
        return self.resolve(reference.class_id, reference.student_id)

    def resolve(self, class_id: str, student_id: str) -> ResolvedRosterStudent:
        requested_class = _validate_requested_identifier(class_id, "class_id")
        requested_student = _validate_requested_identifier(student_id, "student_id")
        roster = self.load_roster(requested_class)
        try:
            lookup = student_lookup(roster)
        except (RosterValidationError, TypeError, ValueError) as exc:
            raise RosterMalformedError(
                f"Core roster for class {requested_class!r} cannot build an exact student lookup"
            ) from exc

        student = lookup.get(requested_student)
        if student is None:
            raise RosterStudentNotFoundError(
                "student is absent from the explicitly requested Core roster: "
                f"class_id={requested_class!r}, student_id={requested_student!r}"
            )
        if not isinstance(student, StudentRecord):
            raise RosterMalformedError("Core student lookup returned a non-StudentRecord value")
        if student.class_id != requested_class:
            raise RosterClassMismatchError(
                "Core student authority belongs to another class: "
                f"requested={requested_class!r}, returned={student.class_id!r}"
            )
        if student.student_id != requested_student:
            raise RosterMalformedError(
                "Core student lookup key disagrees with returned StudentRecord.student_id"
            )

        return ResolvedRosterStudent(
            reference=RosterStudentRef(
                class_id=requested_class,
                student_id=requested_student,
            ),
            student=student,
        )
