"""Focused Slice 7 tests for exact Communication related-record authority."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
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


def _service(tmp_path: Path) -> tuple[CommunicationWorkflowService, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="event",
            contract_version="2",
            status="active",
        )
    )
    repository.load_work_record.return_value = SimpleNamespace(
        record=SimpleNamespace(status="superseded")
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    return service, repository


def _reference(record: PortiaRecord) -> ExactPortiaWorkRecordRef:
    relations = record.field("relations")
    assert isinstance(relations, tuple)
    return ExactPortiaWorkRecordRef.from_dict(relations[0]["record_ref"])


@pytest.mark.parametrize(
    "filename,target_kind",
    [
        ("determination-notice.json", "determination"),
        ("response-relation.json", "response"),
        ("account-relation.json", "account"),
    ],
)
def test_frozen_typed_relation_fixtures_resolve_exact_history(
    tmp_path: Path,
    filename: str,
    target_kind: str,
) -> None:
    candidate = _communication(filename)
    work = _work_for(candidate)
    service, repository = _service(tmp_path)
    reference = _reference(candidate)

    service.create(work, candidate)

    assert reference.record_ref.record_kind == target_kind
    repository.load_work_record.assert_called_once_with(
        reference.work_ref,
        target_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_relation_target_may_be_exact_superseded_history(tmp_path: Path) -> None:
    candidate = _communication("response-relation.json")
    work = _work_for(candidate)
    service, repository = _service(tmp_path)
    repository.load_work_record.return_value = SimpleNamespace(
        record=SimpleNamespace(status="superseded")
    )

    service.create(work, candidate)

    repository.create_work_record.assert_called_once_with(work, candidate)


def test_responds_to_same_work_communication_resolves_exactly(tmp_path: Path) -> None:
    value = _wire("student-in-person.json")
    value["relations"] = [
        {
            "relation": "responds_to",
            "record_ref": {
                "work_ref": {
                    "module_id": "portia",
                    "class_id": value["class_id"],
                    "work_id": value["work_id"],
                    "work_kind": "event",
                    "contract_version": "2",
                },
                "record_ref": {
                    "record_kind": "communication",
                    "record_id": "comm_prior_001",
                    "contract_version": "1",
                },
            },
        }
    ]
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    reference = _reference(candidate)
    repository.load_work_record.assert_called_once_with(
        reference.work_ref,
        "communication",
        "1",
        "comm_prior_001",
    )


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("determination-relation-wrong-kind.json", "conveys_determination"),
        ("response-relation-wrong-kind.json", "relates_to_response"),
        ("account-relation-wrong-kind.json", "account_from_communication"),
        ("responds-to-wrong-kind.json", "responds_to"),
    ],
)
def test_frozen_relation_kind_mismatches_fail_before_target_io(
    tmp_path: Path,
    filename: str,
    expected: str,
) -> None:
    candidate = _communication(filename, section="application-invalid")
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match=expected):
        service.create(work, candidate)

    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize(
    "filename,message",
    [
        ("responds-to-self.json", "relate to itself"),
        ("responds-to-other-work.json", "within the owning work"),
    ],
)
def test_frozen_responds_to_scope_rules_fail_closed(
    tmp_path: Path,
    filename: str,
    message: str,
) -> None:
    candidate = _communication(filename, section="application-invalid")
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match=message):
        service.create(work, candidate)

    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_generic_relation_cannot_point_to_same_communication(tmp_path: Path) -> None:
    value = _wire("student-in-person.json")
    value["relations"] = [
        {
            "relation": "other",
            "detail": "Historical context only.",
            "record_ref": {
                "work_ref": {
                    "module_id": "portia",
                    "class_id": value["class_id"],
                    "work_id": value["work_id"],
                    "work_kind": "event",
                    "contract_version": "2",
                },
                "record_ref": {
                    "record_kind": "communication",
                    "record_id": value["communication_id"],
                    "contract_version": "1",
                },
            },
        }
    ]
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="relate to itself"):
        service.create(work, candidate)

    repository.load_work_record.assert_not_called()


def test_logically_duplicate_relations_rejected_even_if_detail_differs(
    tmp_path: Path,
) -> None:
    value = _wire("student-in-person.json")
    reference = {
        "work_ref": {
            "module_id": "portia",
            "class_id": value["class_id"],
            "work_id": value["work_id"],
            "work_kind": "event",
            "contract_version": "2",
        },
        "record_ref": {
            "record_kind": "review",
            "record_id": "rev_context_001",
            "contract_version": "1",
        },
    }
    value["relations"] = [
        {"relation": "other", "detail": "First label.", "record_ref": reference},
        {"relation": "other", "detail": "Second label.", "record_ref": reference},
    ]
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="same logical"):
        service.create(work, candidate)

    assert repository.load_work_record.call_count == 1
    repository.create_work_record.assert_not_called()


def test_generic_notifies_about_resolves_exact_portia_context(tmp_path: Path) -> None:
    value = _wire("student-in-person.json")
    value["relations"] = [
        {
            "relation": "notifies_about",
            "record_ref": {
                "work_ref": {
                    "module_id": "portia",
                    "class_id": value["class_id"],
                    "work_id": value["work_id"],
                    "work_kind": "event",
                    "contract_version": "2",
                },
                "record_ref": {
                    "record_kind": "review",
                    "record_id": "rev_context_001",
                    "contract_version": "1",
                },
            },
        }
    ]
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    reference = _reference(candidate)
    repository.load_work_record.assert_called_once_with(
        reference.work_ref,
        "review",
        "1",
        "rev_context_001",
    )


def test_exact_relation_resolution_error_propagates_without_successor_following(
    tmp_path: Path,
) -> None:
    candidate = _communication("response-relation.json")
    work = _work_for(candidate)
    service, repository = _service(tmp_path)
    repository.load_work_record.side_effect = RuntimeError(
        "exact related record is unavailable"
    )

    with pytest.raises(RuntimeError, match="exact related record is unavailable"):
        service.create(work, candidate)

    repository.load_work_record.assert_called_once()
    repository.create_work_record.assert_not_called()
