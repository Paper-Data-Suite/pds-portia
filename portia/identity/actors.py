"""Actor Directory application services over guarded Portia persistence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, TypeAlias

from portia.identity.errors import (
    ActorContactPointNotCurrentError,
    ActorDirectoryRemovedError,
    ActorNotCurrentError,
    ActorRelationshipMalformedError,
    ActorRelationshipNotCurrentError,
)
from portia.identity.roster import CoreRosterResolver, ResolvedRosterStudent
from portia.models import PortiaRecord
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorStudentRelationshipRef,
    RosterStudentRef,
)
from portia.storage import (
    ContentFingerprint,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
    QuarantineGuard,
    StoredRecord,
)
from portia.storage.actor_directory import ActorDirectoryRepository

ActorDirectoryExactRef: TypeAlias = (
    ExactActorRef | ExactActorContactPointRef | ExactActorStudentRelationshipRef
)
ResolutionDisposition = Literal["present", "exceptionally_removed"]


@dataclass(frozen=True, slots=True)
class ActorDirectoryResolution:
    """Exact Actor-family resolution without silently following successors."""

    reference: ActorDirectoryExactRef
    disposition: ResolutionDisposition
    stored: StoredRecord | None
    removal_certificate: StoredRecord | None


@dataclass(frozen=True, slots=True)
class ResolvedActorStudentRelationship:
    """One explicit Actor relationship plus its exact current Core roster target."""

    relationship: StoredRecord
    roster_student: ResolvedRosterStudent


def _actor_target(reference: ExactActorRef) -> dict[str, object]:
    return {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor",
            "actor_ref": reference.to_dict(),
        },
    }


def _contact_target(reference: ExactActorContactPointRef) -> dict[str, object]:
    return {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor_contact_point",
            "contact_point_ref": reference.to_dict(),
        },
    }


def _relationship_target(
    reference: ExactActorStudentRelationshipRef,
) -> dict[str, object]:
    return {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor_student_relationship",
            "relationship_ref": reference.to_dict(),
        },
    }


def _target_for(reference: ActorDirectoryExactRef) -> dict[str, object]:
    if isinstance(reference, ExactActorRef):
        return _actor_target(reference)
    if isinstance(reference, ExactActorContactPointRef):
        return _contact_target(reference)
    return _relationship_target(reference)


def _record_ref(record: PortiaRecord) -> ActorDirectoryExactRef:
    logical_id = record.logical_id
    if logical_id is None:
        raise ActorRelationshipMalformedError(
            "Actor Directory record has no canonical logical identifier"
        )
    if record.contract == "actor":
        return ExactActorRef(
            actor_id=logical_id,
            contract_version=record.contract_version,
        )
    actor_id = record.field("actor_id")
    if not isinstance(actor_id, str):
        raise ActorRelationshipMalformedError(
            "Actor Directory child has no exact Actor owner"
        )
    if record.contract == "actor_contact_point":
        return ExactActorContactPointRef(
            actor_id=actor_id,
            contact_point_id=logical_id,
            contract_version=record.contract_version,
        )
    if record.contract == "actor_student_relationship":
        return ExactActorStudentRelationshipRef(
            actor_id=actor_id,
            relationship_id=logical_id,
            contract_version=record.contract_version,
        )
    raise ActorRelationshipMalformedError(
        f"unsupported Actor Directory service contract: {record.contract!r}"
    )


class ActorDirectoryService:
    """Bounded Actor Directory facade used by later Portia workflows."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: ActorDirectoryRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        roster_resolver: CoreRosterResolver | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or ActorDirectoryRepository(self.workspace_root)
        self.quarantine = quarantine or QuarantineGuard(self.workspace_root)
        self.rosters = roster_resolver or CoreRosterResolver(self.workspace_root)

    def _matching_removal(
        self, reference: ActorDirectoryExactRef
    ) -> StoredRecord | None:
        target = _target_for(reference)["actor_directory_record_ref"]
        matches: list[StoredRecord] = []
        for certificate in self.repository.list_actor_directory_removals():
            if certificate.record.field("target") == target:
                matches.append(certificate)
        if len(matches) > 1:
            raise PortiaCorruptionError(
                "multiple exceptional-removal certificates identify one exact Actor record"
            )
        return matches[0] if matches else None

    def _resolve(
        self,
        reference: ActorDirectoryExactRef,
        loader: Callable[[], StoredRecord],
    ) -> ActorDirectoryResolution:
        try:
            stored = loader()
        except PortiaNotFoundError:
            removal = self._matching_removal(reference)
            if removal is None:
                raise
            return ActorDirectoryResolution(
                reference=reference,
                disposition="exceptionally_removed",
                stored=None,
                removal_certificate=removal,
            )

        removal = self._matching_removal(reference)
        if removal is not None:
            raise PortiaRecoveryRequiredError(
                "Actor Directory payload and its exceptional-removal certificate both exist"
            )
        return ActorDirectoryResolution(
            reference=reference,
            disposition="present",
            stored=stored,
            removal_certificate=None,
        )

    @staticmethod
    def _require_present(resolution: ActorDirectoryResolution) -> StoredRecord:
        if resolution.stored is None:
            raise ActorDirectoryRemovedError(
                "requested exact Actor Directory representation was exceptionally removed"
            )
        return resolution.stored

    def resolve_actor(self, reference: ExactActorRef) -> ActorDirectoryResolution:
        return self._resolve(
            reference,
            lambda: self.repository.load_actor(
                reference.actor_id,
                version=reference.contract_version,
            ),
        )

    def load_actor(
        self,
        reference: ExactActorRef,
        *,
        require_current_use: bool = False,
    ) -> StoredRecord:
        stored = self._require_present(self.resolve_actor(reference))
        if require_current_use:
            self._require_actor_current_use(reference, stored)
        return stored

    def create_actor(self, record: PortiaRecord) -> StoredRecord:
        reference = _record_ref(record)
        if not isinstance(reference, ExactActorRef):
            raise ActorRelationshipMalformedError("create_actor requires actor@* input")
        self.quarantine.require_allowed(
            _actor_target(reference), "block_actor_directory_writes"
        )
        return self.repository.create_actor(record)

    def replace_actor(
        self,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        reference = _record_ref(record)
        if not isinstance(reference, ExactActorRef):
            raise ActorRelationshipMalformedError("replace_actor requires actor@* input")
        self.quarantine.require_allowed(
            _actor_target(reference), "block_actor_directory_writes"
        )
        return self.repository.replace_actor(record, expected=expected)

    def resolve_actor_child(
        self,
        reference: ExactActorContactPointRef | ExactActorStudentRelationshipRef,
    ) -> ActorDirectoryResolution:
        """Resolve one supported exact Actor child without successor following."""
        if isinstance(reference, ExactActorContactPointRef):
            return self.resolve_contact_point(reference)
        return self.resolve_relationship(reference)

    def load_actor_child(
        self,
        reference: ExactActorContactPointRef | ExactActorStudentRelationshipRef,
        *,
        require_current_use: bool = False,
        on_date: date | None = None,
    ) -> StoredRecord:
        """Load one supported exact Actor child with optional current-use checks."""
        if isinstance(reference, ExactActorContactPointRef):
            return self.load_contact_point(
                reference, require_current_use=require_current_use
            )
        return self.load_relationship(
            reference,
            require_current_use=require_current_use,
            on_date=on_date,
        )

    def resolve_contact_point(
        self,
        reference: ExactActorContactPointRef,
    ) -> ActorDirectoryResolution:
        return self._resolve(
            reference,
            lambda: self.repository.load_actor_child(
                reference.actor_id,
                "actor_contact_point",
                reference.contract_version,
                reference.contact_point_id,
            ),
        )

    def load_contact_point(
        self,
        reference: ExactActorContactPointRef,
        *,
        require_current_use: bool = False,
    ) -> StoredRecord:
        stored = self._require_present(self.resolve_contact_point(reference))
        if require_current_use:
            self._require_contact_current_use(reference, stored)
        return stored

    def resolve_relationship(
        self,
        reference: ExactActorStudentRelationshipRef,
    ) -> ActorDirectoryResolution:
        return self._resolve(
            reference,
            lambda: self.repository.load_actor_child(
                reference.actor_id,
                "actor_student_relationship",
                reference.contract_version,
                reference.relationship_id,
            ),
        )

    def load_relationship(
        self,
        reference: ExactActorStudentRelationshipRef,
        *,
        require_current_use: bool = False,
        on_date: date | None = None,
    ) -> StoredRecord:
        stored = self._require_present(self.resolve_relationship(reference))
        if require_current_use:
            self._require_relationship_current_use(reference, stored, on_date=on_date)
        return stored

    def create_actor_child(self, actor_id: str, record: PortiaRecord) -> StoredRecord:
        reference = _record_ref(record)
        if isinstance(reference, ExactActorRef) or reference.actor_id != actor_id:
            raise ActorRelationshipMalformedError(
                "Actor child input does not agree with the explicit Actor owner"
            )
        self.quarantine.require_allowed(
            _target_for(reference), "block_actor_directory_writes"
        )
        return self.repository.create_actor_child(actor_id, record)

    def replace_actor_child(
        self,
        actor_id: str,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        reference = _record_ref(record)
        if isinstance(reference, ExactActorRef) or reference.actor_id != actor_id:
            raise ActorRelationshipMalformedError(
                "Actor child input does not agree with the explicit Actor owner"
            )
        self.quarantine.require_allowed(
            _target_for(reference), "block_actor_directory_writes"
        )
        return self.repository.replace_actor_child(
            actor_id,
            record,
            expected=expected,
        )

    def list_relationships(
        self,
        actor_id: str,
        *,
        version: str = "1",
    ) -> tuple[StoredRecord, ...]:
        self.load_actor(ExactActorRef(actor_id=actor_id, contract_version="1"))
        return self.repository.list_actor_children(
            actor_id,
            "actor_student_relationship",
            version=version,
        )

    def resolve_student_relationship(
        self,
        reference: ExactActorStudentRelationshipRef,
        *,
        require_current_use: bool = False,
        on_date: date | None = None,
    ) -> ResolvedActorStudentRelationship:
        relationship = self.load_relationship(
            reference,
            require_current_use=require_current_use,
            on_date=on_date,
        )
        student_wire = relationship.record.field("student_ref")
        try:
            student_ref = RosterStudentRef.from_dict(student_wire)
        except Exception as exc:
            raise ActorRelationshipMalformedError(
                "Actor-to-student Relationship has malformed student_ref data"
            ) from exc
        resolved = self.rosters.resolve_reference(student_ref)
        return ResolvedActorStudentRelationship(relationship, resolved)

    def _require_actor_current_use(
        self,
        reference: ExactActorRef,
        stored: StoredRecord,
    ) -> None:
        self.quarantine.require_allowed(_actor_target(reference), "block_current_use")
        if stored.record.status != "active":
            raise ActorNotCurrentError(
                f"Actor {reference.actor_id!r} is not active for current use"
            )

    def _require_contact_current_use(
        self,
        reference: ExactActorContactPointRef,
        stored: StoredRecord,
    ) -> None:
        actor_ref = ExactActorRef(actor_id=reference.actor_id, contract_version="1")
        self.load_actor(actor_ref, require_current_use=True)
        self.quarantine.require_allowed(_contact_target(reference), "block_current_use")
        if stored.record.status != "active":
            raise ActorContactPointNotCurrentError(
                f"Contact Point {reference.contact_point_id!r} is not active for current use"
            )

    def _require_relationship_current_use(
        self,
        reference: ExactActorStudentRelationshipRef,
        stored: StoredRecord,
        *,
        on_date: date | None,
    ) -> None:
        actor_ref = ExactActorRef(actor_id=reference.actor_id, contract_version="1")
        self.load_actor(actor_ref, require_current_use=True)
        self.quarantine.require_allowed(
            _relationship_target(reference), "block_current_use"
        )
        record = stored.record
        if record.status != "active":
            raise ActorRelationshipNotCurrentError(
                f"Relationship {reference.relationship_id!r} is not active"
            )
        review = record.field("review")
        if not isinstance(review, Mapping) or review.get("kind") != "locally_reviewed":
            raise ActorRelationshipNotCurrentError(
                f"Relationship {reference.relationship_id!r} has not completed local review"
            )

        effective = record.field("effective_period")
        if effective is None:
            return
        if not isinstance(effective, Mapping):
            raise ActorRelationshipMalformedError(
                "Relationship effective_period is not an object"
            )
        effective_date = on_date or date.today()
        starts = effective.get("starts_on")
        ends = effective.get("ends_on")
        try:
            if isinstance(starts, str) and effective_date < date.fromisoformat(starts):
                raise ActorRelationshipNotCurrentError(
                    f"Relationship {reference.relationship_id!r} is not yet effective"
                )
            if isinstance(ends, str) and effective_date > date.fromisoformat(ends):
                raise ActorRelationshipNotCurrentError(
                    f"Relationship {reference.relationship_id!r} is no longer effective"
                )
        except ValueError as exc:
            raise ActorRelationshipMalformedError(
                "Relationship effective_period contains an invalid date"
            ) from exc
