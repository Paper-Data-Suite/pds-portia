"""Focused Slice 6 tests for exact Communication Contact Point authority."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactActorContactPointRef, ExactPortiaWorkRef
from portia.workflows import CommunicationWorkflowService
from portia.workflows.errors import WorkflowPrerequisiteError

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


def _work_for(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _service(tmp_path: Path) -> tuple[CommunicationWorkflowService, Mock, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="event",
            contract_version="2",
            status="active",
        )
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    contexts = Mock()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=contexts,
    )
    return service, repository, contexts


def test_active_endpoint_uses_exact_current_contact_point(tmp_path: Path) -> None:
    candidate = _communication("completed-family-phone.json")
    work = _work_for(candidate)
    service, repository, contexts = _service(tmp_path)

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


def test_proposed_endpoint_pins_exact_history_without_current_gate(
    tmp_path: Path,
) -> None:
    value = _wire("completed-family-phone.json")
    value["status"] = "proposed"
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.actors.load_contact_point.assert_called_once_with(
        ExactActorContactPointRef(
            actor_id="actr_family_001",
            contact_point_id="acp_family_phone_001",
            contract_version="1",
        ),
        require_current_use=False,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_exact_endpoint_error_propagates_without_successor_following(
    tmp_path: Path,
) -> None:
    candidate = _communication("completed-family-phone.json")
    work = _work_for(candidate)
    service, repository, contexts = _service(tmp_path)
    contexts.actors.load_contact_point.side_effect = RuntimeError(
        "exact Contact Point is not current"
    )

    with pytest.raises(RuntimeError, match="exact Contact Point is not current"):
        service.create(work, candidate)

    contexts.actors.load_contact_point.assert_called_once_with(
        ExactActorContactPointRef(
            actor_id="actr_family_001",
            contact_point_id="acp_family_phone_001",
            contract_version="1",
        ),
        require_current_use=True,
    )
    repository.create_work_record.assert_not_called()


def test_endpoint_actor_mismatch_fails_before_contact_authority(tmp_path: Path) -> None:
    candidate = _communication(
        "endpoint-actor-mismatch.json",
        section="application-invalid",
    )
    work = _work_for(candidate)
    service, repository, contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Contact Point Actor does not match",
    ):
        service.create(work, candidate)

    contexts.actors.load_contact_point.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_recipient_unavailable_endpoint_does_not_claim_delivery(tmp_path: Path) -> None:
    candidate = _communication("recipient-unavailable-phone.json")
    work = _work_for(candidate)
    service, repository, contexts = _service(tmp_path)

    service.create(work, candidate)

    contexts.actors.load_contact_point.assert_called_once()
    repository.create_work_record.assert_called_once_with(work, candidate)
    assert candidate.field("act_state") == "recipient_unavailable"
    recipients = candidate.field("recipients")
    assert isinstance(recipients, tuple)
    assert recipients[0]["participation"] == "not_established"
