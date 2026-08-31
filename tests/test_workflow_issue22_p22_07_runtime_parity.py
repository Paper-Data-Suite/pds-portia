from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import cast

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import ActorDirectoryService, CoreRosterResolver
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorStudentRelationshipRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaRepository, StoredRecord
from portia.workflows import (
    CommunicationWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    ResponseWorkflowService,
    communication_reference,
    event_reference,
    response_reference,
)
from portia.workflows.context import WorkflowContextAssembler

FIXTURE_ROOT = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "issue_22"
    / "positive"
    / "p22_07_response_family_communication"
)
CLASS_ID = "eng10_p2_2026"
STUDENT_ID = "stu_p22_001"
ACTOR_ID = "actr_p22_family_001"
CONTACT_ID = "acp_p22_family_email_001"
RELATIONSHIP_ID = "asrel_p22_family_001"
EVENT_ID = "evt_p22_family_comm_001"
PARTICIPANT_ID = "ep_p22_family_comm_001"
RESPONSE_ID = "rsp_p22_family_001"
COMMUNICATION_ID = "comm_p22_family_001"


@dataclass(frozen=True, slots=True)
class _P2207Runtime:
    work: ExactPortiaWorkRef
    repository: PortiaRepository
    actors: ActorDirectoryService
    response_service: ResponseWorkflowService
    communication_service: CommunicationWorkflowService
    stored: dict[str, StoredRecord]


def _load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _fixture_record(name: str, contract: str, version: str) -> PortiaRecord:
    return parse_portia_record(
        contract,
        version,
        _load_object(FIXTURE_ROOT / "records" / name),
    )


def _seed_core_roster(workspace: Path) -> CoreRosterResolver:
    roster = create_roster(
        CLASS_ID,
        [
            {
                "student_id": STUDENT_ID,
                "last_name": "Student A",
                "first_name": "Synthetic",
                "period": "2",
                "preferred_name": "Synthetic Student A",
            }
        ],
    )
    write_class_roster(workspace, roster)
    return CoreRosterResolver(workspace)


def _build_p22_07(workspace: Path) -> _P2207Runtime:
    roster = _seed_core_roster(workspace)
    actors = ActorDirectoryService(workspace, roster_resolver=roster)
    contexts = WorkflowContextAssembler(
        workspace,
        roster_resolver=roster,
        actor_directory=actors,
    )
    repository = PortiaRepository(workspace)

    actor = _fixture_record("actor.json", "actor", "1")
    contact = _fixture_record(
        "actor-contact-point.json",
        "actor_contact_point",
        "1",
    )
    relationship = _fixture_record(
        "actor-student-relationship.json",
        "actor_student_relationship",
        "1",
    )
    active_event = _fixture_record("event.json", "event", "2")
    participant = _fixture_record(
        "participant.json",
        "event_participant",
        "3",
    )
    response = _fixture_record("response.json", "response", "1")
    communication = _fixture_record(
        "communication.json",
        "communication",
        "1",
    )

    stored: dict[str, StoredRecord] = {}
    stored["actor"] = actors.create_actor(actor)
    stored["actor_contact_point"] = actors.create_actor_child(ACTOR_ID, contact)
    stored["actor_student_relationship"] = actors.create_actor_child(
        ACTOR_ID,
        relationship,
    )

    event_service = EventWorkflowService(
        workspace,
        repository=repository,
        context_assembler=contexts,
    )
    participant_service = ParticipantWorkflowService(
        workspace,
        repository=repository,
        context_assembler=contexts,
    )
    response_service = ResponseWorkflowService(
        workspace,
        repository=repository,
        context_assembler=contexts,
    )
    communication_service = CommunicationWorkflowService(
        workspace,
        repository=repository,
        context_assembler=contexts,
    )

    draft_wire = active_event.to_dict()
    draft_wire["status"] = "draft"
    draft_wire["updated_at"] = draft_wire["created_at"]
    draft_event = parse_portia_record("event", "2", draft_wire)
    created_event = event_service.create(draft_event)
    work = event_reference(active_event)

    stored["event_participant"] = participant_service.create(work, participant)
    stored["event"] = event_service.replace(
        active_event,
        expected=created_event.fingerprint,
    )
    stored["response"] = response_service.create(work, response)
    stored["communication"] = communication_service.create(work, communication)

    return _P2207Runtime(
        work=work,
        repository=repository,
        actors=actors,
        response_service=response_service,
        communication_service=communication_service,
        stored=stored,
    )


def test_p22_07_executes_through_production_services_and_exact_current_use(
    tmp_path: Path,
) -> None:
    runtime = _build_p22_07(tmp_path)
    expected = _load_object(FIXTURE_ROOT / "expected.json")
    scenario = _load_object(FIXTURE_ROOT / "scenario.json")

    actor = runtime.actors.load_actor(
        ExactActorRef(actor_id=ACTOR_ID, contract_version="1"),
        require_current_use=True,
    )
    contact = runtime.actors.load_contact_point(
        ExactActorContactPointRef(
            actor_id=ACTOR_ID,
            contact_point_id=CONTACT_ID,
            contract_version="1",
        ),
        require_current_use=True,
    )
    relationship = runtime.actors.resolve_student_relationship(
        ExactActorStudentRelationshipRef(
            actor_id=ACTOR_ID,
            relationship_id=RELATIONSHIP_ID,
            contract_version="1",
        ),
        require_current_use=True,
        on_date=date(2026, 8, 15),
    )
    response = runtime.response_service.require_current_use(
        response_reference(runtime.work, RESPONSE_ID)
    )
    communication = runtime.communication_service.require_current_use(
        communication_reference(runtime.work, COMMUNICATION_ID)
    )

    actor_display = cast(dict[str, object], actor.record.to_dict()["display"])
    contact_value = cast(dict[str, object], contact.record.to_dict()["contact"])

    assert actor.record.logical_id == expected["actor_id"]
    assert actor_display["display_name"] == expected["actor_display_name"]
    assert contact.record.logical_id == expected["contact_point_id"]
    assert contact_value["kind"] == expected["contact_kind"]
    assert contact_value["address"] == expected["contact_address"]
    assert relationship.relationship.record.logical_id == expected["relationship_id"]
    assert relationship.roster_student.reference.student_id == STUDENT_ID
    assert runtime.stored["event"].record.logical_id == expected["event_id"]
    participant_id = runtime.stored["event_participant"].record.logical_id
    assert participant_id == expected["participant_id"]
    response_wire = response.record.to_dict()
    response_action = cast(dict[str, object], response_wire["action"])
    communication_wire = communication.record.to_dict()
    communication_method = cast(dict[str, object], communication_wire["method"])
    communication_purpose = cast(dict[str, object], communication_wire["purpose"])

    assert response.record.logical_id == expected["response_id"]
    assert response_action["family"] == expected["response_family"]
    assert response_wire["execution_state"] == expected["response_execution_state"]
    assert communication.record.logical_id == expected["communication_id"]
    assert communication_method["kind"] == expected["communication_method"]
    assert communication_purpose["kind"] == expected["communication_purpose"]
    assert communication_wire["act_state"] == expected["communication_act_state"]

    descriptors = scenario["records"]
    assert isinstance(descriptors, list)
    expected_paths: dict[str, str] = {}
    for descriptor in descriptors:
        assert isinstance(descriptor, dict)
        contract = descriptor.get("contract")
        canonical_path = descriptor.get("canonical_path")
        assert isinstance(contract, str)
        assert isinstance(canonical_path, str)
        expected_paths[contract] = canonical_path
    assert set(runtime.stored) == set(expected_paths)
    for contract, stored in runtime.stored.items():
        assert stored.path.relative_to(tmp_path).as_posix() == expected_paths[contract]


def test_p22_07_keeps_family_contact_relationship_and_participation_distinct(
    tmp_path: Path,
) -> None:
    runtime = _build_p22_07(tmp_path)
    expected = _load_object(FIXTURE_ROOT / "expected.json")

    actor_wire = runtime.stored["actor"].record.to_dict()
    contact_wire = runtime.stored["actor_contact_point"].record.to_dict()
    relationship_wire = runtime.stored["actor_student_relationship"].record.to_dict()
    participant_wire = runtime.stored["event_participant"].record.to_dict()
    communication_wire = runtime.stored["communication"].record.to_dict()

    actor_category = cast(dict[str, object], actor_wire["actor_category"])
    verification = cast(dict[str, object], contact_wire["verification"])
    relationship_value = cast(dict[str, object], relationship_wire["relationship"])
    recipients = cast(list[object], communication_wire["recipients"])
    recipient = cast(dict[str, object], recipients[0])
    recipient_person = cast(dict[str, object], recipient["person"])
    recipient_actor = cast(dict[str, object], recipient_person["actor_ref"])
    participant_subject = cast(dict[str, object], participant_wire["subject"])
    roster_ref = cast(dict[str, object], participant_subject["roster_student_ref"])

    assert actor_category["kind"] == expected["actor_category"]
    assert verification["kind"] == expected["contact_verification"]
    assert relationship_value["type"] == expected["relationship_type"]
    assert relationship_wire["student_ref"] == expected["relationship_student_ref"]
    assert recipient_person["kind"] == "actor"
    assert recipient_actor["actor_id"] == ACTOR_ID
    assert recipient["participation"] == expected["recipient_participation"]
    assert participant_subject["kind"] == "roster_student"
    assert roster_ref["student_id"] == STUDENT_ID

    assert "consent" not in contact_wire
    assert "delivery" not in contact_wire
    assert "legal_guardianship" not in relationship_wire
    assert "disclosure_permission" not in relationship_wire
    assert "delivery_status" not in communication_wire
    assert "read_status" not in communication_wire
    assert "understanding_status" not in communication_wire

    relations = cast(list[object], communication_wire["relations"])
    relation = cast(dict[str, object], relations[0])
    assert relation["relation"] == expected["communication_response_relation"]
    expected_response_ref = response_reference(runtime.work, RESPONSE_ID).to_dict()
    assert relation["record_ref"] == expected_response_ref


def test_p22_07_does_not_fabricate_judgment_support_or_outcome_records(
    tmp_path: Path,
) -> None:
    runtime = _build_p22_07(tmp_path)
    expected = _load_object(FIXTURE_ROOT / "expected.json")

    forbidden = expected["forbidden_contracts"]
    assert isinstance(forbidden, list)
    for contract in forbidden:
        assert isinstance(contract, str)
        assert runtime.repository.list_work_records(
            runtime.work,
            contract,
            version="1",
        ) == ()

    assert runtime.repository.list_works(
        CLASS_ID,
        work_kind="support_process",
        version="1",
    ) == ()
    assert [
        item.record.logical_id
        for item in runtime.repository.list_event_participants(runtime.work)
    ] == [PARTICIPANT_ID]
    response_ids = [
        item.record.logical_id for item in runtime.response_service.list(runtime.work)
    ]
    assert response_ids == [RESPONSE_ID]
    assert [
        item.record.logical_id
        for item in runtime.communication_service.list(runtime.work)
    ] == [COMMUNICATION_ID]
