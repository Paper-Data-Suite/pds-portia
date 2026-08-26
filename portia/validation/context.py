"""Bounded external-resolution context for in-memory Portia validation."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from pds_core.routing_models import ModuleWorkRef

from portia.models.references import RosterStudentRef


class ValidationContext(Protocol):
    """Facts supplied by authoritative services without making validation do I/O."""

    def roster_student_exists(self, reference: RosterStudentRef) -> bool | None:
        """Return True/False when authoritative resolution was attempted; else None."""
        ...

    def core_work_exists(self, reference: ModuleWorkRef) -> bool | None:
        """Return True/False when authoritative resolution was attempted; else None."""
        ...


class UnknownValidationContext:
    """Default context: external existence is unknown rather than guessed."""

    def roster_student_exists(self, reference: RosterStudentRef) -> bool | None:
        del reference
        return None

    def core_work_exists(self, reference: ModuleWorkRef) -> bool | None:
        del reference
        return None


@dataclass(frozen=True, slots=True)
class KnownValidationContext:
    """Deterministic in-memory authoritative facts for callers and tests.

    An identifier absent from a supplied known set is reported as absent.  Pass
    ``None`` for a domain whose existence has not been authoritatively loaded.
    """

    roster_students: frozenset[tuple[str, str]] | None = None
    core_works: frozenset[tuple[str, str, str]] | None = None

    @classmethod
    def from_values(
        cls,
        *,
        roster_students: Iterable[RosterStudentRef] | None = None,
        core_works: Iterable[ModuleWorkRef] | None = None,
    ) -> "KnownValidationContext":
        roster_set = (
            frozenset((item.class_id, item.student_id) for item in roster_students)
            if roster_students is not None
            else None
        )
        work_set = (
            frozenset((item.module_id, item.class_id, item.work_id) for item in core_works)
            if core_works is not None
            else None
        )
        return cls(roster_students=roster_set, core_works=work_set)

    def roster_student_exists(self, reference: RosterStudentRef) -> bool | None:
        if self.roster_students is None:
            return None
        return (reference.class_id, reference.student_id) in self.roster_students

    def core_work_exists(self, reference: ModuleWorkRef) -> bool | None:
        if self.core_works is None:
            return None
        return (
            reference.module_id,
            reference.class_id,
            reference.work_id,
        ) in self.core_works
