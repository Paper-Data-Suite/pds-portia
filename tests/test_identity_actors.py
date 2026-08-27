from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import (
    ActorContactPointNotCurrentError,
    ActorDirectoryRemovedError,
    ActorDirectoryService,
    ActorRelationshipMalformedError,
    ActorRelationshipNotCurrentError,
    CoreRosterResolver,
    RosterClassMismatchError,
    RosterStudentNotFoundError,
)
from portia.models import parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorStudentRelationshipRef,
)
from portia.storage import (
    ActorDirectoryRepository,
    PortiaConflictError,
    PortiaNotFoundError,
    PortiaQuarantinedError,
)

_TIMESTAMP = "2026-08-26T12:00:00-04:00"
_AGENT = {"type": "system_process", "process_id": "identity_test"}


def _actor_wire(
    actor_id: str = "actr_guardian",
    *,
    status: str = "active",
    display_name: str = "Morgan Example",
    updated_at: str = _TIMESTAMP,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "actor",
        "module_id": "portia",
        "actor_id": actor_id,
        "status": status,
        "display": {"display_name": display_name},
        "actor_category": {"kind": "family_or_caregiver"},
        "creation_source": {"type": "digital_entry"},
        "created_at": _TIMESTAMP,
        "created_by": _AGENT,
        "updated_at": updated_at,
        "updated_by": _AGENT,
    }


def _contact_wire(
    *,
    actor_id: str = "actr_guardian",
    contact_point_id: str = "acp_guardian_email",
    status: str = "active",
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "actor_contact_point",
        "module_id": "portia",
        "actor_id": actor_id,
        "contact_point_id": contact_point_id,
        "status": status,
        "contact": {
            "kind": "email",
            "address": "synthetic.guardian@example.invalid",
            "label": "personal",
        },
        "use_preference": "preferred",
        "source": {"kind": "local_operator_knowledge"},
        "verification": {
            "kind": "locally_confirmed",
            "verified_at": _TIMESTAMP,
            "verified_by": _AGENT,
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": _TIMESTAMP,
        "created_by": _AGENT,
        "updated_at": _TIMESTAMP,
        "updated_by": _AGENT,
    }


def _relationship_wire(
    *,
    actor_id: str = "actr_guardian",
    relationship_id: str = "asrel_guardian_student",
    class_id: str = "class_a",
    student_id: str = "student_17",
    status: str = "active",
    review_kind: str = "locally_reviewed",
    effective_period: dict[str, object] | None = None,
) -> dict[str, object]:
    review: dict[str, object]
    if review_kind == "locally_reviewed":
        review = {
            "kind": "locally_reviewed",
            "reviewed_at": _TIMESTAMP,
            "reviewed_by": _AGENT,
        }
    else:
        review = {"kind": "unreviewed"}
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "actor_student_relationship",
        "module_id": "portia",
        "actor_id": actor_id,
        "relationship_id": relationship_id,
        "status": status,
        "student_ref": {"class_id": class_id, "student_id": student_id},
        "relationship": {"type": "guardian"},
        "basis": {"kind": "local_operator_knowledge"},
        "review": review,
        "creation_source": {"type": "digital_entry"},
        "created_at": _TIMESTAMP,
        "created_by": _AGENT,
        "updated_at": _TIMESTAMP,
        "updated_by": _AGENT,
    }
    if effective_period is not None:
        wire["effective_period"] = effective_period
    return wire


def _write_roster(tmp_path: Path, class_id: str, student_id: str = "student_17") -> None:
    write_class_roster(
        tmp_path,
        create_roster(
            class_id,
            [
                {
                    "student_id": student_id,
                    "last_name": "Example",
                    "first_name": "Student",
                    "period": "2",
                }
            ],
        ),
    )


def _actor_ref(actor_id: str = "actr_guardian") -> ExactActorRef:
    return ExactActorRef(actor_id=actor_id, contract_version="1")


def _relationship_ref(
    actor_id: str = "actr_guardian",
    relationship_id: str = "asrel_guardian_student",
) -> ExactActorStudentRelationshipRef:
    return ExactActorStudentRelationshipRef(
        actor_id=actor_id,
        relationship_id=relationship_id,
        contract_version="1",
    )


def test_actor_create_load_and_guarded_replace_round_trip(tmp_path: Path) -> None:
    service = ActorDirectoryService(tmp_path)
    actor = parse_portia_record("actor", "1", _actor_wire())
    created = service.create_actor(actor)

    loaded = service.load_actor(_actor_ref())
    assert loaded.record.to_dict() == actor.to_dict()
    assert loaded.fingerprint == created.fingerprint

    replacement = parse_portia_record(
        "actor",
        "1",
        _actor_wire(display_name="Morgan Updated", updated_at="2026-08-26T12:05:00-04:00"),
    )
    service.replace_actor(replacement, expected=created.fingerprint)

    with pytest.raises(PortiaConflictError):
        service.replace_actor(replacement, expected=created.fingerprint)



def test_contact_point_access_uses_exact_actor_child_reference(tmp_path: Path) -> None:
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    contact = parse_portia_record("actor_contact_point", "1", _contact_wire())
    service.create_actor_child("actr_guardian", contact)
    reference = ExactActorContactPointRef(
        actor_id="actr_guardian",
        contact_point_id="acp_guardian_email",
        contract_version="1",
    )

    loaded = service.load_actor_child(reference, require_current_use=True)
    assert loaded.record.logical_id == "acp_guardian_email"
    assert service.resolve_actor_child(reference).disposition == "present"


def test_inactive_contact_point_is_not_current_use_eligible(tmp_path: Path) -> None:
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    contact = parse_portia_record(
        "actor_contact_point", "1", _contact_wire(status="inactive")
    )
    service.create_actor_child("actr_guardian", contact)
    reference = ExactActorContactPointRef(
        actor_id="actr_guardian",
        contact_point_id="acp_guardian_email",
        contract_version="1",
    )

    assert service.load_contact_point(reference).record.status == "inactive"
    with pytest.raises(ActorContactPointNotCurrentError):
        service.load_contact_point(reference, require_current_use=True)

def test_explicit_relationship_resolves_only_its_exact_class_qualified_student(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    relationship = parse_portia_record(
        "actor_student_relationship", "1", _relationship_wire()
    )
    service.create_actor_child("actr_guardian", relationship)

    resolved = service.resolve_student_relationship(_relationship_ref())

    assert resolved.roster_student.reference.class_id == "class_a"
    assert resolved.roster_student.reference.student_id == "student_17"
    assert resolved.relationship.record.logical_id == "asrel_guardian_student"


def test_multiple_explicit_class_relationships_do_not_create_global_person_identity(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a")
    _write_roster(tmp_path, "class_b")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))

    first = parse_portia_record(
        "actor_student_relationship",
        "1",
        _relationship_wire(relationship_id="asrel_a", class_id="class_a"),
    )
    second = parse_portia_record(
        "actor_student_relationship",
        "1",
        _relationship_wire(relationship_id="asrel_b", class_id="class_b"),
    )
    service.create_actor_child("actr_guardian", first)
    service.create_actor_child("actr_guardian", second)

    relationships = service.list_relationships("actr_guardian")
    assert {record.record.logical_id for record in relationships} == {"asrel_a", "asrel_b"}
    assert (
        service.resolve_student_relationship(
            _relationship_ref(relationship_id="asrel_a")
        ).roster_student.reference
        != service.resolve_student_relationship(
            _relationship_ref(relationship_id="asrel_b")
        ).roster_student.reference
    )


def test_actor_id_and_actor_display_are_never_roster_identity_substitutes(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(
        parse_portia_record(
            "actor", "1", _actor_wire(display_name="Student Example")
        )
    )

    resolver = CoreRosterResolver(tmp_path)
    with pytest.raises(RosterStudentNotFoundError):
        resolver.resolve("class_a", "actr_guardian")
    with pytest.raises(RosterStudentNotFoundError):
        resolver.resolve("class_a", "Student_Example")


def test_relationship_rejects_authoritative_core_result_from_another_class(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path, "class_b")
    wrong_roster = create_roster(
        "class_b",
        [
            {
                "student_id": "student_17",
                "last_name": "Example",
                "first_name": "Student",
                "period": "2",
            }
        ],
    )

    def wrong_loader(_root: str | Path, _class_id: str):
        return wrong_roster

    resolver = CoreRosterResolver(tmp_path, loader=wrong_loader)
    service = ActorDirectoryService(tmp_path, roster_resolver=resolver)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    service.create_actor_child(
        "actr_guardian",
        parse_portia_record("actor_student_relationship", "1", _relationship_wire()),
    )

    with pytest.raises(RosterClassMismatchError):
        service.resolve_student_relationship(_relationship_ref())


def test_relationship_missing_target_student_remains_roster_absence(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    service.create_actor_child(
        "actr_guardian",
        parse_portia_record(
            "actor_student_relationship",
            "1",
            _relationship_wire(student_id="student_missing"),
        ),
    )

    with pytest.raises(RosterStudentNotFoundError):
        service.resolve_student_relationship(_relationship_ref())


def test_actor_child_owner_mismatch_is_rejected_before_persistence(tmp_path: Path) -> None:
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    wrong_owner = parse_portia_record(
        "actor_student_relationship",
        "1",
        _relationship_wire(actor_id="actr_other"),
    )

    with pytest.raises(ActorRelationshipMalformedError):
        service.create_actor_child("actr_guardian", wrong_owner)

    assert not (
        tmp_path
        / "portia"
        / "actors"
        / "actr_guardian"
        / "records"
        / "actor_student_relationship"
        / "asrel_guardian_student.json"
    ).exists()


def test_current_relationship_requires_active_status(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    service.create_actor_child(
        "actr_guardian",
        parse_portia_record(
            "actor_student_relationship",
            "1",
            _relationship_wire(status="proposed"),
        ),
    )

    with pytest.raises(ActorRelationshipNotCurrentError):
        service.resolve_student_relationship(
            _relationship_ref(),
            require_current_use=True,
            on_date=date(2026, 8, 26),
        )


def test_current_relationship_requires_local_review(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    service.create_actor_child(
        "actr_guardian",
        parse_portia_record(
            "actor_student_relationship",
            "1",
            _relationship_wire(status="active", review_kind="unreviewed"),
        ),
    )

    with pytest.raises(ActorRelationshipNotCurrentError):
        service.resolve_student_relationship(
            _relationship_ref(),
            require_current_use=True,
            on_date=date(2026, 8, 26),
        )


@pytest.mark.parametrize(
    ("effective_period", "on_date"),
    [
        ({"starts_on": "2026-09-01"}, date(2026, 8, 26)),
        ({"ends_on": "2026-08-20"}, date(2026, 8, 26)),
    ],
)
def test_current_relationship_requires_effective_period(
    tmp_path: Path,
    effective_period: dict[str, object],
    on_date: date,
) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    service.create_actor_child(
        "actr_guardian",
        parse_portia_record(
            "actor_student_relationship",
            "1",
            _relationship_wire(effective_period=effective_period),
        ),
    )

    with pytest.raises(ActorRelationshipNotCurrentError):
        service.resolve_student_relationship(
            _relationship_ref(),
            require_current_use=True,
            on_date=on_date,
        )


def test_exact_superseded_relationship_is_not_silently_followed(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    service = ActorDirectoryService(tmp_path)
    service.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    relationship = parse_portia_record(
        "actor_student_relationship",
        "1",
        _relationship_wire(status="superseded"),
    )
    service.create_actor_child("actr_guardian", relationship)

    loaded = service.load_relationship(_relationship_ref())
    assert loaded.record.status == "superseded"
    with pytest.raises(ActorRelationshipNotCurrentError):
        service.load_relationship(_relationship_ref(), require_current_use=True)


class _BlockingQuarantine:
    def __init__(self, blocked_effect: str) -> None:
        self.blocked_effect = blocked_effect
        self.requests: list[tuple[object, str]] = []

    def require_allowed(self, requested_target: object, effect: str) -> None:
        self.requests.append((requested_target, effect))
        if effect == self.blocked_effect:
            raise PortiaQuarantinedError(f"synthetic quarantine blocks {effect}")


def test_quarantine_blocks_actor_directory_write_without_mutating_lifecycle(
    tmp_path: Path,
) -> None:
    repository = ActorDirectoryRepository(tmp_path)
    actor = parse_portia_record("actor", "1", _actor_wire())
    repository.create_actor(actor)
    before = repository.load_actor("actr_guardian").record.to_dict()
    guard = _BlockingQuarantine("block_actor_directory_writes")
    service = ActorDirectoryService(
        tmp_path,
        repository=repository,
        quarantine=guard,  # type: ignore[arg-type]
    )
    replacement = parse_portia_record(
        "actor",
        "1",
        _actor_wire(display_name="Blocked Update", updated_at="2026-08-26T12:05:00-04:00"),
    )

    with pytest.raises(PortiaQuarantinedError):
        service.replace_actor(
            replacement,
            expected=repository.load_actor("actr_guardian").fingerprint,
        )

    assert repository.load_actor("actr_guardian").record.to_dict() == before


def test_current_use_quarantine_does_not_block_exact_historical_read(tmp_path: Path) -> None:
    repository = ActorDirectoryRepository(tmp_path)
    repository.create_actor(parse_portia_record("actor", "1", _actor_wire()))
    guard = _BlockingQuarantine("block_current_use")
    service = ActorDirectoryService(
        tmp_path,
        repository=repository,
        quarantine=guard,  # type: ignore[arg-type]
    )

    assert service.load_actor(_actor_ref()).record.status == "active"
    with pytest.raises(PortiaQuarantinedError):
        service.load_actor(_actor_ref(), require_current_use=True)


def test_exceptional_removal_resolves_distinctly_from_never_existed(tmp_path: Path) -> None:
    repository = ActorDirectoryRepository(tmp_path)
    actor = parse_portia_record("actor", "1", _actor_wire())
    created = repository.create_actor(actor)
    actor_ref = _actor_ref()
    removal_wire = {
        "schema_version": "1",
        "record_type": "actor_directory_exceptional_removal",
        "module_id": "portia",
        "removal_id": "rmv_actor_test",
        "target": {"kind": "actor", "actor_ref": actor_ref.to_dict()},
        "original_workspace_relative_path": "portia/actors/actr_guardian/actor.json",
        "original_contract_version": "1",
        "original_fingerprint": created.fingerprint.digest,
        "original_byte_length": created.fingerprint.byte_length,
        "ground": {"code": "synthetic_or_test_record"},
        "authorization": {
            "decision_reference": "synthetic identity regression",
            "authorized_by": {
                "type": "local_operator",
                "display_label": "Synthetic Tester",
            },
        },
        "removed_at": "2026-08-26T12:10:00-04:00",
        "removed_by": _AGENT,
        "operation_ref": {"operation_id": "op_identity_removal"},
        "retained_identity_evidence": {
            "kind": "actor",
            "actor_ref": actor_ref.to_dict(),
        },
    }
    removal = parse_portia_record(
        "actor_directory_exceptional_removal", "1", removal_wire
    )
    repository.create_actor_directory_removal(removal)
    created.path.unlink()

    service = ActorDirectoryService(tmp_path, repository=repository)
    resolution = service.resolve_actor(actor_ref)

    assert resolution.disposition == "exceptionally_removed"
    assert resolution.stored is None
    assert resolution.removal_certificate is not None
    with pytest.raises(ActorDirectoryRemovedError):
        service.load_actor(actor_ref)
    with pytest.raises(PortiaNotFoundError):
        service.load_actor(_actor_ref("actr_never_existed"))
