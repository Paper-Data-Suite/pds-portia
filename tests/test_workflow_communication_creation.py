"""Focused Slice 5 tests for Event-owned Communication creation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.workflows import CommunicationWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "communication"
)


def _wire(path: str, *, section: str = "valid") -> dict[str, object]:
    return json.loads(
        (_FIXTURE_ROOT / section / path).read_text(encoding="utf-8")
    )


def _communication(path: str, *, section: str = "valid") -> PortiaRecord:
    return parse_portia_record("communication", "1", _wire(path, section=section))


def _without_endpoints(path: str, *, section: str = "valid") -> PortiaRecord:
    value = _wire(path, section=section)
    recipients = value["recipients"]
    assert isinstance(recipients, list)
    for recipient in recipients:
        assert isinstance(recipient, dict)
        recipient.pop("endpoint_ref", None)
    return parse_portia_record("communication", "1", value)


def _work_for(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    assert record.work_kind in {"event", "support_process"}
    version = "2" if record.work_kind == "event" else "1"
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind=record.work_kind,
        contract_version=version,
    )


def _owner(*, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        contract="event",
        contract_version="2",
        status=status,
    )


def _service(
    tmp_path: Path,
    *,
    owner_status: str = "active",
) -> tuple[CommunicationWorkflowService, Mock, Mock, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=_owner(status=owner_status)
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    quarantine = Mock()
    contexts = Mock()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=quarantine,
        context_assembler=contexts,
    )
    return service, repository, quarantine, contexts


@pytest.mark.parametrize(
    "filename",
    [
        "student-in-person.json",
        "incoming-family-phone.json",
    ],
)
def test_slice5_basic_event_communication_fixtures_create(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _communication(filename)
    work = _work_for(candidate)
    service, repository, quarantine, _contexts = _service(tmp_path)

    stored = service.create(work, candidate)

    assert stored.record == "stored"
    repository.create_work_record.assert_called_once_with(work, candidate)
    assert quarantine.require_allowed.call_count == 2


def test_actor_recipient_without_endpoint_creates_before_slice6(
    tmp_path: Path,
) -> None:
    candidate = _without_endpoints("completed-family-phone.json")
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.actors.load_actor.assert_called_once_with(
        ExactActorRef(actor_id="actr_family_001", contract_version="1"),
        require_current_use=True,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_recipient_unavailable_without_endpoint_is_a_valid_attempt(
    tmp_path: Path,
) -> None:
    candidate = _without_endpoints("recipient-unavailable-phone.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)


def test_multiple_logical_recipients_create_without_participant_inference(
    tmp_path: Path,
) -> None:
    candidate = _without_endpoints("multi-recipient-email.json")
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.actors.load_actor.assert_called_once()
    contexts.rosters.resolve_reference.assert_called_once_with(
        RosterStudentRef(
            class_id="class_ela10_p2",
            student_id="student_a",
        )
    )
    repository.load_work_record.assert_not_called()


def test_roster_recipient_resolves_identity_not_event_participation(
    tmp_path: Path,
) -> None:
    candidate = _communication("student-in-person.json")
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.rosters.resolve_reference.assert_called_once_with(
        RosterStudentRef(
            class_id="class_ela10_p2",
            student_id="student_a",
        )
    )
    repository.load_work_record.assert_not_called()


def test_proposed_actor_recipient_requires_exact_but_not_current_actor(
    tmp_path: Path,
) -> None:
    value = _without_endpoints("completed-family-phone.json").to_dict()
    value["status"] = "proposed"
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(
        tmp_path,
        owner_status="draft",
    )

    service.create(work, candidate)

    contexts.actors.load_actor.assert_called_once_with(
        ExactActorRef(actor_id="actr_family_001", contract_version="1"),
        require_current_use=False,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_active_communication_requires_current_event_owner(tmp_path: Path) -> None:
    candidate = _communication("student-in-person.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        owner_status="draft",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active Communication creation requires Event status",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_wrong_explicit_event_owner_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    candidate = _communication("student-in-person.json")
    assert candidate.class_id is not None
    work = ExactPortiaWorkRef(
        class_id=candidate.class_id,
        work_id="evt_other_issue43",
        work_kind="event",
        contract_version="2",
    )
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowOwnershipError,
        match="explicitly selected Event",
    ):
        service.create(work, candidate)

    repository.load_work.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_support_process_owner_fails_closed_until_issue44(tmp_path: Path) -> None:
    candidate = _communication(
        "support-process-owner-before-issue18.json",
        section="application-invalid",
    )
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Issue #44 authority",
    ):
        service.create(work, candidate)

    repository.load_work.assert_not_called()
    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize(
    "filename",
    [
        "updated-before-created.json",
        "started-after-updated.json",
        "ended-before-started.json",
        "ended-after-updated.json",
        "digital-unknown-method.json",
        "digital-unknown-purpose.json",
        "digital-unknown-act-state.json",
        "digital-unknown-privacy.json",
        "digital-unknown-participation.json",
        "duplicate-logical-recipient.json",
        "unavailable-with-participation.json",
    ],
)
def test_slice5_frozen_application_invalid_semantics_fail_closed(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _communication(filename, section="application-invalid")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize(
    "filename",
    [
        "active-import.json",
        "active-paper-ingested.json",
    ],
)
def test_new_communication_authoring_is_digital_entry_only(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _communication(filename, section="application-invalid")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="digital_entry only",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_historical_import_fixture_remains_readable_but_not_newly_authored(
    tmp_path: Path,
) -> None:
    candidate = _communication("import-unknown-proposed.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="digital_entry only",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize(
    "filename",
    [
        "active-unidentified-sender.json",
        "active-unidentified-recipient.json",
    ],
)
def test_active_communication_requires_identified_people(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _communication(filename, section="application-invalid")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="identified represented human",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize(
    "filename",
    [
        "completed-family-phone.json",
        "recipient-unavailable-phone.json",
        "multi-recipient-email.json",
    ],
)
def test_contact_point_bearing_creation_uses_exact_slice6_authority(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _communication(filename)
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.actors.load_contact_point.assert_called_once_with(
        ExactActorContactPointRef(
            actor_id="actr_family_001",
            contact_point_id="acp_family_phone_001",
            contract_version="1",
        ),
        require_current_use=True,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_endpoint_actor_mismatch_is_rejected_before_contact_point_load(
    tmp_path: Path,
) -> None:
    candidate = _communication(
        "endpoint-actor-mismatch.json",
        section="application-invalid",
    )
    work = _work_for(candidate)
    service, repository, _quarantine, contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Contact Point Actor does not match recipient Actor",
    ):
        service.create(work, candidate)

    contexts.actors.load_contact_point.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_relation_bearing_creation_uses_exact_slice7_authority(
    tmp_path: Path,
) -> None:
    candidate = _without_endpoints("response-relation.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.load_work_record.assert_called_once()
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_external_attachment_creation_uses_slice8_inert_metadata(
    tmp_path: Path,
) -> None:
    candidate = _without_endpoints("external-record-attachment.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_fresh_creation_rejects_communication_successor(tmp_path: Path) -> None:
    candidate = _without_endpoints("successor-correction.json")
    work = _work_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=r"coordinated correct\(\) path",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_communication_creation_uses_repository_and_quarantine_only(
    tmp_path: Path,
) -> None:
    candidate = _communication("student-in-person.json")
    work = _work_for(candidate)
    service, repository, quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)
    assert quarantine.require_allowed.call_count == 2
    assert not list(tmp_path.rglob("*.json"))
