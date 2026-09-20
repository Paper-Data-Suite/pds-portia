from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRosterStudentCollisionRef,
    ExactActorStudentRelationshipRef,
)
from portia.storage import PortiaRecoveryRequiredError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    ExceptionalRemovalAuthority,
    ExceptionalRemovalWorkflowService,
    RecoveryWorkflowService,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import event_record, event_ref, participant_record

_TIME = "2026-09-18T12:00:00-04:00"
_OPERATOR = {"type": "local_operator", "display_label": "Synthetic teacher"}
_AUTHORIZATION = {
    "decision_reference": "local-decision-47",
    "authorized_by": _OPERATOR,
}
_REASON = {"category": "privacy_requirement", "code": "privacy_request"}


def _authority(*, governance: str = "clear") -> ExceptionalRemovalAuthority:
    return ExceptionalRemovalAuthority(
        enabled=True,
        governance_state=governance,  # type: ignore[arg-type]
    )


def _participant_target() -> dict[str, object]:
    return {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }


def _work_target() -> dict[str, object]:
    return {"kind": "work", "work_ref": event_ref().to_dict()}


def _accepted_participant(root: Path) -> PortiaRepository:
    repository = PortiaRepository(root)
    repository.create_work(event_ref(), event_record(status="draft"))
    repository.create_work_record(event_ref(), participant_record())
    return repository


def _service(root: Path) -> ExceptionalRemovalWorkflowService:
    return ExceptionalRemovalWorkflowService(
        root,
        authority=_authority(),
        entropy=lambda count: b"s" * count,
        clock=lambda: _TIME,
    )


def test_work_record_removal_is_certificate_first_and_exact(tmp_path: Path) -> None:
    repository = _accepted_participant(tmp_path)
    service = _service(tmp_path)
    target = _participant_target()
    assessment = service.assess_removal(
        target=target,
        reason=_REASON,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    original = assessment.canonical_bytes

    result = service.exceptionally_remove(
        assessment,
        reason=_REASON,
        authorization=_AUTHORIZATION,
        effective_at=_TIME,
    )

    assert result.operation.revision.contract_version == "3"
    assert result.operation.revision.field("state") == "completed"
    assert result.resolution.disposition == "exceptionally_removed"
    assert result.certificate.path.is_file()
    assert not assessment.stored.path.exists()
    certificate = result.certificate.record.to_dict()
    evidence = certificate["content_evidence"]
    assert isinstance(evidence, dict)
    salt = base64.b64decode(str(evidence["salt"]), validate=True)
    assert evidence["digest"] == hashlib.sha256(salt + original).hexdigest()
    assert evidence["byte_length"] == len(original)
    assert certificate["lifecycle_snapshot"] == {"status": "active"}
    assert result.certificate.path.parent != assessment.stored.path.parent
    with pytest.raises(PortiaRecoveryRequiredError):
        service.require_current_use(target)
    assert repository.list_exceptional_removals("class_a") == (result.certificate,)


def test_policy_and_complete_review_fail_closed_before_mutation(tmp_path: Path) -> None:
    _accepted_participant(tmp_path)
    blocked = ExceptionalRemovalWorkflowService(
        tmp_path,
        authority=_authority(governance="unknown"),
    )
    with pytest.raises(WorkflowPrerequisiteError):
        blocked.assess_removal(
            target=_participant_target(),
            reason=_REASON,
            authorization=_AUTHORIZATION,
            integrity_clearance="clear",
        )

    service = _service(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError):
        service.assess_removal(
            target=_participant_target(),
            reason={"category": "other", "code": "incorrect"},
            authorization=_AUTHORIZATION,
            integrity_clearance="clear",
        )
    assessment = service.assess_removal(
        target=_work_target(),
        reason=_REASON,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    with pytest.raises(WorkflowPrerequisiteError):
        service.exceptionally_remove(
            assessment,
            reason=_REASON,
            authorization=_AUTHORIZATION,
            child_dispositions={},
            effective_at=_TIME,
        )
    assert assessment.stored.path.is_file()


def test_interrupted_absence_recovers_without_second_certificate(tmp_path: Path) -> None:
    _accepted_participant(tmp_path)
    service = _service(tmp_path)
    assessment = service.assess_removal(
        target=_participant_target(),
        reason=_REASON,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )

    def fail_after_absence(point: str, _step: str | None) -> None:
        if point == "after_payload_absence":
            raise RuntimeError("synthetic interruption")

    with pytest.raises(RuntimeError, match="synthetic interruption"):
        service.exceptionally_remove(
            assessment,
            reason=_REASON,
            authorization=_AUTHORIZATION,
            operation_id="op_11111111111111111111111111111111",
            removal_id="rmv_11111111111111111111111111111111",
            quarantine_id="qnt_11111111111111111111111111111111",
            effective_at=_TIME,
            fault_hook=fail_after_absence,
        )

    partial = service.operations.load_current("op_11111111111111111111111111111111")
    recovered = RecoveryWorkflowService(tmp_path).resume_exceptional_removal(
        "op_11111111111111111111111111111111",
        expected_pointer=partial.pointer_fingerprint,
        authority=_authority(),
    )
    assert recovered.resolution.disposition == "exceptionally_removed"
    assert len(service.repository.list_exceptional_removals("class_a")) == 1
    current = service.operations.load_current("op_11111111111111111111111111111111")
    replay = RecoveryWorkflowService(tmp_path).resume_exceptional_removal(
        "op_11111111111111111111111111111111",
        expected_pointer=current.pointer_fingerprint,
        authority=_authority(),
    )
    assert replay.operation.pointer_fingerprint == current.pointer_fingerprint


def test_work_root_removes_selected_child_with_linked_certificate(tmp_path: Path) -> None:
    _accepted_participant(tmp_path)
    service = _service(tmp_path)
    assessment = service.assess_removal(
        target=_work_target(),
        reason=_REASON,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    assert len(assessment.children) == 1
    child_path = assessment.children[0].relative_path
    parent = service.exceptionally_remove(
        assessment,
        reason=_REASON,
        authorization=_AUTHORIZATION,
        child_dispositions={child_path: "exceptionally_removed"},
        removal_id="rmv_22222222222222222222222222222222",
        effective_at=_TIME,
    )
    certificates = service.repository.list_exceptional_removals("class_a")
    assert len(certificates) == 2
    child = next(item for item in certificates if item != parent.certificate)
    assert child.record.field("parent_removal") == {
        "module_id": "portia",
        "class_id": "class_a",
        "removal_id": "rmv_22222222222222222222222222222222",
        "contract_version": "1",
    }
    assert not assessment.stored.path.exists()
    assert not assessment.children[0].relative_path.endswith("work.json")


def test_actor_child_removal_preserves_only_opaque_identity(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    actor = parse_portia_record(
        "actor",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor",
            "module_id": "portia",
            "actor_id": "actr_removal",
            "status": "active",
            "display": {"display_name": "Sensitive Actor Sentinel"},
            "actor_category": {"kind": "family_or_caregiver"},
            "creation_source": {"type": "digital_entry"},
            "created_at": _TIME,
            "created_by": _OPERATOR,
            "updated_at": _TIME,
            "updated_by": _OPERATOR,
        },
    )
    repository.create_actor(actor)
    contact = parse_portia_record(
        "actor_contact_point",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor_contact_point",
            "module_id": "portia",
            "actor_id": "actr_removal",
            "contact_point_id": "acp_removal",
            "status": "active",
            "contact": {
                "kind": "email",
                "address": "sensitive-sentinel@example.invalid",
                "label": "personal",
            },
            "use_preference": "preferred",
            "source": {"kind": "local_operator_knowledge"},
            "verification": {
                "kind": "locally_confirmed",
                "verified_at": _TIME,
                "verified_by": _OPERATOR,
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": _TIME,
            "created_by": _OPERATOR,
            "updated_at": _TIME,
            "updated_by": _OPERATOR,
        },
    )
    repository.create_actor_child("actr_removal", contact)
    reference = ExactActorContactPointRef(
        actor_id="actr_removal",
        contact_point_id="acp_removal",
        contract_version="1",
    )
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor_contact_point",
            "contact_point_ref": reference.to_dict(),
        },
    }
    service = _service(tmp_path)
    ground = {"code": "prohibited_sensitive_payload"}
    assessment = service.assess_removal(
        target=target,
        reason=ground,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    result = service.exceptionally_remove(
        assessment,
        reason=ground,
        authorization=_AUTHORIZATION,
        effective_at=_TIME,
    )
    durable = result.certificate.path.read_text(encoding="utf-8")
    assert "sensitive-sentinel" not in durable
    assert result.certificate.record.field("retained_identity_evidence") == target[
        "actor_directory_record_ref"
    ]
    assert result.resolution.disposition == "exceptionally_removed"


def test_actor_relationship_removal_uses_exact_relationship_branch(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    actor_wire = {
        "schema_version": "1",
        "record_type": "actor",
        "module_id": "portia",
        "actor_id": "actr_relationship",
        "status": "active",
        "display": {"display_name": "Synthetic Relationship Actor"},
        "actor_category": {"kind": "family_or_caregiver"},
        "creation_source": {"type": "digital_entry"},
        "created_at": _TIME,
        "created_by": _OPERATOR,
        "updated_at": _TIME,
        "updated_by": _OPERATOR,
    }
    repository.create_actor(parse_portia_record("actor", "1", actor_wire))
    relationship = parse_portia_record(
        "actor_student_relationship",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor_student_relationship",
            "module_id": "portia",
            "actor_id": "actr_relationship",
            "relationship_id": "asrel_removal",
            "status": "active",
            "student_ref": {"class_id": "class_a", "student_id": "student_1"},
            "relationship": {"type": "guardian"},
            "basis": {"kind": "local_operator_knowledge"},
            "review": {
                "kind": "locally_reviewed",
                "reviewed_at": _TIME,
                "reviewed_by": _OPERATOR,
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": _TIME,
            "created_by": _OPERATOR,
            "updated_at": _TIME,
            "updated_by": _OPERATOR,
        },
    )
    repository.create_actor_child("actr_relationship", relationship)
    reference = ExactActorStudentRelationshipRef(
        actor_id="actr_relationship",
        relationship_id="asrel_removal",
        contract_version="1",
    )
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor_student_relationship",
            "relationship_ref": reference.to_dict(),
        },
    }
    service = _service(tmp_path)
    ground = {"code": "binding_legal_or_administrative_requirement"}
    assessment = service.assess_removal(
        target=target,
        reason=ground,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    result = service.exceptionally_remove(
        assessment,
        reason=ground,
        authorization=_AUTHORIZATION,
        effective_at=_TIME,
    )
    assert result.resolution.disposition == "exceptionally_removed"


def test_actor_collision_removal_uses_published_exact_branch(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    actor_id = "actr_student_collision"
    repository.create_actor(
        parse_portia_record(
            "actor",
            "1",
            {
                "schema_version": "1",
                "record_type": "actor",
                "module_id": "portia",
                "actor_id": actor_id,
                "status": "inactive",
                "display": {"display_name": "Synthetic Collision Actor"},
                "actor_category": {"kind": "family_or_caregiver"},
                "creation_source": {"type": "digital_entry"},
                "created_at": _TIME,
                "created_by": _OPERATOR,
                "updated_at": _TIME,
                "updated_by": _OPERATOR,
            },
        )
    )
    fixture = (
        Path(__file__).parent
        / "schema_validation/fixtures/issue-14/actor-roster-student-collision/valid/student-statement.json"
    )
    collision_wire = json.loads(fixture.read_text(encoding="utf-8"))
    collision = parse_portia_record(
        "actor_roster_student_collision", "1", collision_wire
    )
    repository.create_actor_child(actor_id, collision)
    reference = ExactActorRosterStudentCollisionRef(
        actor_id=actor_id,
        collision_id=str(collision.logical_id),
        contract_version="1",
    )
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor_roster_student_collision",
            "collision_ref": reference.to_dict(),
        },
    }
    service = _service(tmp_path)
    ground = {"code": "binding_legal_or_administrative_requirement"}
    result = service.exceptionally_remove(
        service.assess_removal(
            target=target,
            reason=ground,
            authorization=_AUTHORIZATION,
            integrity_clearance="clear",
        ),
        reason=ground,
        authorization=_AUTHORIZATION,
        effective_at=_TIME,
    )
    assert result.resolution.disposition == "exceptionally_removed"


def test_actor_root_removal_requires_and_executes_complete_child_disposition(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    actor = parse_portia_record(
        "actor",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor",
            "module_id": "portia",
            "actor_id": "actr_root_removal",
            "status": "active",
            "display": {"display_name": "Synthetic Root Actor"},
            "actor_category": {"kind": "family_or_caregiver"},
            "creation_source": {"type": "digital_entry"},
            "created_at": _TIME,
            "created_by": _OPERATOR,
            "updated_at": _TIME,
            "updated_by": _OPERATOR,
        },
    )
    repository.create_actor(actor)
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor",
            "actor_ref": {
                "actor_id": "actr_root_removal",
                "contract_version": "1",
            },
        },
    }
    service = _service(tmp_path)
    ground = {"code": "binding_legal_or_administrative_requirement"}
    assessment = service.assess_removal(
        target=target,
        reason=ground,
        authorization=_AUTHORIZATION,
        integrity_clearance="clear",
    )
    assert assessment.children == ()
    result = service.exceptionally_remove(
        assessment,
        reason=ground,
        authorization=_AUTHORIZATION,
        child_dispositions={},
        effective_at=_TIME,
    )
    assert result.resolution.disposition == "exceptionally_removed"
