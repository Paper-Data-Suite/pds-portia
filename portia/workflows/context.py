"""Authoritative I/O assembly outside Portia's pure graph validator."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from portia.identity import ActorDirectoryService, CoreRosterResolver
from portia.identity.roster import ResolvedRosterStudent
from portia.models import PortiaRecord
from portia.models.references import ExactActorRef, RosterStudentRef
from portia.storage.repository import StoredRecord
from portia.validation import KnownValidationContext


def _walk(value: object) -> tuple[object, ...]:
    values: list[object] = [value]
    if isinstance(value, Mapping):
        for child in value.values():
            values.extend(_walk(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            values.extend(_walk(child))
    return tuple(values)


def roster_references(records: Sequence[PortiaRecord]) -> tuple[RosterStudentRef, ...]:
    """Discover every distinct exact roster identity in a proposed graph."""
    found: dict[tuple[str, str], RosterStudentRef] = {}
    for record in records:
        for value in _walk(record.to_dict()):
            if not isinstance(value, Mapping):
                continue
            candidate: object | None = None
            if value.get("kind") == "roster_student":
                candidate = value.get("roster_student_ref")
            elif set(value) == {"class_id", "student_id"}:
                candidate = value
            if candidate is None:
                continue
            try:
                reference = RosterStudentRef.from_dict(candidate)
            except Exception:
                continue
            found[(reference.class_id, reference.student_id)] = reference
    return tuple(found[key] for key in sorted(found))


def actor_references(records: Sequence[PortiaRecord]) -> tuple[ExactActorRef, ...]:
    """Discover exact Actor identities without name/contact matching."""
    found: dict[str, ExactActorRef] = {}
    for record in records:
        for value in _walk(record.to_dict()):
            if not isinstance(value, Mapping) or value.get("kind") != "actor":
                continue
            actor_ref = value.get("actor_ref")
            actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
            if isinstance(actor_id, str):
                found[actor_id] = ExactActorRef(
                    actor_id=actor_id, contract_version="1"
                )
    return tuple(found[key] for key in sorted(found))


@dataclass(frozen=True, slots=True)
class AuthoritativeWorkflowContext:
    """Complete facts queried for one bounded proposed graph."""

    validation: KnownValidationContext
    roster_students: tuple[ResolvedRosterStudent, ...]
    actors: tuple[StoredRecord, ...]


class WorkflowContextAssembler:
    """Resolve all relevant #39 identity authorities before validation."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        roster_resolver: CoreRosterResolver | None = None,
        actor_directory: ActorDirectoryService | None = None,
    ) -> None:
        self.rosters = roster_resolver or CoreRosterResolver(workspace_root)
        self.actors = actor_directory or ActorDirectoryService(workspace_root)

    def assemble(
        self,
        records: Sequence[PortiaRecord],
        *,
        require_actor_current_use: bool = False,
    ) -> AuthoritativeWorkflowContext:
        roster_results = tuple(
            self.rosters.resolve_reference(reference)
            for reference in roster_references(records)
        )
        actor_results = tuple(
            self.actors.load_actor(
                reference,
                require_current_use=require_actor_current_use,
            )
            for reference in actor_references(records)
        )
        # Every roster reference in this graph was queried before a closed known
        # set is supplied. Core-work authority was not queried and remains None.
        validation = KnownValidationContext.from_values(
            roster_students=(item.reference for item in roster_results),
            core_works=None,
        )
        return AuthoritativeWorkflowContext(
            validation=validation,
            roster_students=roster_results,
            actors=actor_results,
        )
