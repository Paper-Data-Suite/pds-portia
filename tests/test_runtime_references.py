from __future__ import annotations

from pds_core.routing_models import ModuleRecordRef, ModuleWorkRef

from portia.models import (
    ActorRef,
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorStudentRelationshipRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    LocalRecordRef,
    ModuleWorkRecordRef,
    PortiaWorkRecordRef,
    PortiaWorkRef,
    RosterStudentRef,
)


def test_roster_student_identity_is_class_qualified() -> None:
    first = RosterStudentRef(class_id="eng10_p2", student_id="001")
    second = RosterStudentRef(class_id="eng10_p3", student_id="001")
    assert first != second
    assert first.to_dict() == {"class_id": "eng10_p2", "student_id": "001"}


def test_actor_ref_does_not_contain_roster_or_display_identity() -> None:
    reference = ActorRef(actor_id="actr_family_001")
    assert reference.to_dict() == {"actor_id": "actr_family_001"}


def test_local_record_ref_preserves_explicit_null_contract_version() -> None:
    reference = LocalRecordRef.from_dict(
        {"record_kind": "external_record", "record_id": "record_1", "contract_version": None}
    )
    assert reference.contract_version is None
    assert "contract_version" in reference.to_dict()
    assert reference.to_dict()["contract_version"] is None


def test_portia_work_record_ref_preserves_explicit_scope() -> None:
    reference = PortiaWorkRecordRef(
        work_ref=PortiaWorkRef(
            class_id="eng10_p2",
            work_id="evt_001",
            work_kind="event",
            contract_version="2",
        ),
        record_ref=LocalRecordRef(
            record_kind="observation",
            record_id="obs_001",
            contract_version="2",
        ),
    )
    assert reference.to_dict()["work_ref"]["work_id"] == "evt_001"  # type: ignore[index]


def test_module_work_record_ref_reuses_core_models() -> None:
    reference = ModuleWorkRecordRef(
        work_ref=ModuleWorkRef(module_id="scoreform", class_id="eng10_p2", work_id="assessment_1"),
        record_ref=ModuleRecordRef(
            module_id="scoreform",
            record_kind="response",
            record_id="response_1",
            contract_version=None,
        ),
    )
    wire = reference.to_dict()
    assert wire["work_ref"]["module_id"] == "scoreform"  # type: ignore[index]
    assert wire["record_ref"]["contract_version"] is None  # type: ignore[index]


def test_exact_references_preserve_historical_contract_identity() -> None:
    reference = ExactPortiaWorkRecordRef(
        work_ref=ExactPortiaWorkRef(
            class_id="eng10_p2",
            work_id="evt_001",
            work_kind="event",
            contract_version="1",
        ),
        record_ref=ExactLocalRecordRef(
            record_kind="observation",
            record_id="obs_001",
            contract_version="1",
        ),
    )
    assert reference.to_dict()["work_ref"]["contract_version"] == "1"  # type: ignore[index]
    assert reference.to_dict()["record_ref"]["contract_version"] == "1"  # type: ignore[index]


def test_exact_actor_family_references_are_typed_without_roster_substitution() -> None:
    actor = ExactActorRef(actor_id="actr_family_001", contract_version="1")
    contact = ExactActorContactPointRef(
        actor_id=actor.actor_id,
        contact_point_id="acp_family_email_001",
        contract_version="1",
    )
    relationship = ExactActorStudentRelationshipRef(
        actor_id=actor.actor_id,
        relationship_id="asrel_family_student_001",
        contract_version="1",
    )
    assert contact.actor_id == actor.actor_id
    assert relationship.actor_id == actor.actor_id


def test_core_module_id_equality_is_application_not_structural_validation() -> None:
    reference = ModuleWorkRecordRef(
        work_ref=ModuleWorkRef(
            module_id="scoreform", class_id="eng10_p2", work_id="assessment_1"
        ),
        record_ref=ModuleRecordRef(
            module_id="quillan",
            record_kind="response",
            record_id="response_1",
            contract_version=None,
        ),
    )
    assert reference.work_ref.module_id != reference.record_ref.module_id
