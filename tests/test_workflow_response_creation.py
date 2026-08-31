"""Focused Slice 2 tests for production Response creation."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import ResponseWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "response"
)


def _response(path: str, *, section: str = "valid") -> PortiaRecord:
    value = json.loads((_FIXTURE_ROOT / section / path).read_text(encoding="utf-8"))
    return parse_portia_record("response", "1", value)


def _event_for(record: PortiaRecord, *, version: str = "2") -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version=version,
    )


def _owner(*, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        contract="event",
        contract_version="2",
        status=status,
    )


def _participant(*, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        contract="event_participant",
        contract_version="3",
        logical_id="ep_student_a",
        status=status,
    )


def _service(
    tmp_path: Path,
    *,
    owner_status: str = "active",
    participant_status: str = "active",
) -> tuple[ResponseWorkflowService, Mock, Mock, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=_owner(status=owner_status)
    )
    repository.load_work_record.return_value = SimpleNamespace(
        record=_participant(status=participant_status)
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    quarantine = Mock()
    contexts = Mock()
    service = ResponseWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=quarantine,
        context_assembler=contexts,
    )
    return service, repository, quarantine, contexts


@pytest.mark.parametrize(
    "filename",
    [
        "event-classroom-management.json",
        "participant-redirection.json",
        "support-access.json",
        "event-safety-protective.json",
        "teacher-local-consequence.json",
        "referral-attempted.json",
    ],
)
def test_slice2_valid_response_fixtures_create(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _response(filename)
    work = _event_for(candidate)
    service, repository, quarantine, _contexts = _service(tmp_path)

    stored = service.create(work, candidate)

    assert stored.record == "stored"
    repository.create_work_record.assert_called_once_with(work, candidate)
    assert quarantine.require_allowed.call_count >= 2


def test_participant_target_resolves_exact_event_participant_v3(
    tmp_path: Path,
) -> None:
    candidate = _response("participant-redirection.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.load_work_record.assert_called_once_with(
        work,
        "event_participant",
        "3",
        "ep_student_a",
    )


def test_inactive_participant_cannot_receive_active_response(
    tmp_path: Path,
) -> None:
    candidate = _response("participant-redirection.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        participant_status="superseded",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="target Participant must be active",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_active_response_requires_current_event_owner(tmp_path: Path) -> None:
    candidate = _response("event-classroom-management.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        owner_status="draft",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active Response creation requires Event status",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_wrong_explicit_event_owner_is_rejected_before_persistence(
    tmp_path: Path,
) -> None:
    candidate = _response("event-classroom-management.json")
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


@pytest.mark.parametrize(
    "filename",
    [
        "updated-before-created.json",
        "started-after-updated.json",
        "ended-before-started.json",
        "ended-after-updated.json",
        "active-import.json",
        "active-paper-ingested.json",
        "digital-active-unknown-execution.json",
        "in-progress-with-ended-at.json",
        "roster-student-provider-consequence.json",
    ],
)
def test_slice2_frozen_application_invalid_cases_fail_closed(
    tmp_path: Path,
    filename: str,
) -> None:
    candidate = _response(filename, section="application-invalid")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_fresh_creation_rejects_supersession_successor(tmp_path: Path) -> None:
    candidate = _response("successor-correction.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="coordinated successor path",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_new_response_authoring_is_digital_entry_only(tmp_path: Path) -> None:
    candidate = _response("import-unknown-proposed.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="digital_entry only",
    ):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_provider_and_recorder_are_not_equated_by_creation_service(
    tmp_path: Path,
) -> None:
    base = _response("event-classroom-management.json").to_dict()
    base["created_by"] = {
        "type": "local_operator",
        "display_label": "Synthetic recorder",
    }
    base["updated_by"] = dict(base["created_by"])
    candidate = parse_portia_record("response", "1", base)
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)


@pytest.mark.parametrize(
    "family",
    [
        "classroom_management",
        "environmental_or_instructional",
        "support_access",
        "de_escalation",
        "safety_or_protective",
        "referral_or_handoff",
        "restorative_or_repair",
        "other",
    ],
)
def test_non_consequence_action_families_do_not_require_determination(
    tmp_path: Path,
    family: str,
) -> None:
    base = _response("event-classroom-management.json").to_dict()
    base["action"] = {
        "family": family,
        "description": f"Synthetic bounded {family} action.",
    }
    candidate = parse_portia_record("response", "1", base)
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)


def test_response_creation_uses_canonical_repository_not_direct_filesystem(
    tmp_path: Path,
) -> None:
    candidate = _response("event-classroom-management.json")
    work = _event_for(candidate)
    service, repository, _quarantine, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)
    assert not (tmp_path / "classes").exists()
