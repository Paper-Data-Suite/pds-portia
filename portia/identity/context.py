"""I/O-free validation-context adapters for authoritative identity facts."""

from __future__ import annotations

from dataclasses import dataclass

from pds_core.rosters import Roster
from pds_core.routing_models import ModuleWorkRef

from portia.identity.roster import ResolvedRosterStudent
from portia.models.references import RosterStudentRef


@dataclass(frozen=True, slots=True)
class ResolvedIdentityValidationContext:
    """Positive-only identity facts from successful exact resolutions.

    A missing pair is unknown, not absent, because resolving one student does not
    prove that every other roster identity has been authoritatively checked.
    """

    roster_students: frozenset[tuple[str, str]]

    @classmethod
    def from_resolutions(
        cls, *resolutions: ResolvedRosterStudent
    ) -> "ResolvedIdentityValidationContext":
        return cls(
            frozenset(
                (item.reference.class_id, item.reference.student_id)
                for item in resolutions
            )
        )

    def roster_student_exists(self, reference: RosterStudentRef) -> bool | None:
        key = (reference.class_id, reference.student_id)
        return True if key in self.roster_students else None

    def core_work_exists(self, reference: ModuleWorkRef) -> bool | None:
        del reference
        return None


@dataclass(frozen=True, slots=True)
class RosterSnapshotValidationContext:
    """Class-scoped authority from complete successfully loaded Core rosters."""

    roster_students: frozenset[tuple[str, str]]
    authoritative_classes: frozenset[str]

    @classmethod
    def from_rosters(cls, *rosters: Roster) -> "RosterSnapshotValidationContext":
        students: set[tuple[str, str]] = set()
        classes: set[str] = set()
        for roster in rosters:
            classes.add(roster.class_id)
            for student in roster.students:
                if student.class_id != roster.class_id:
                    raise ValueError(
                        "cannot build validation context from a class-mismatched roster"
                    )
                students.add((roster.class_id, student.student_id))
        return cls(frozenset(students), frozenset(classes))

    def roster_student_exists(self, reference: RosterStudentRef) -> bool | None:
        if reference.class_id not in self.authoritative_classes:
            return None
        return (reference.class_id, reference.student_id) in self.roster_students

    def core_work_exists(self, reference: ModuleWorkRef) -> bool | None:
        del reference
        return None
