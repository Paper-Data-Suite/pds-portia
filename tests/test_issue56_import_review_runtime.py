from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import ImportReviewV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_import_review_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/11-import_review.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice13_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_import_review_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("import_review", "1", wire)
    assert isinstance(model, ImportReviewV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["review_id"]
    assert model.class_id == wire["class_id"]
    assert model.work_id is None
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["disposition"] = "rejected"
    assert model.to_dict() == wire


def test_sequence_one_forbids_predecessor() -> None:
    wire = _fixture()
    wire["predecessor_review_id"] = "irev_prior_01"
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_later_sequence_requires_predecessor() -> None:
    wire = _fixture()
    wire["review_sequence"] = 2
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_accepted_forbids_field_reviews_and_reason_codes() -> None:
    wire = _fixture()
    wire["field_reviews"] = [
        {"target_path": "/location_text", "decision": "accept_candidate"}
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_corrected_and_accepted_requires_correction() -> None:
    wire = _fixture()
    wire["disposition"] = "corrected_and_accepted"
    wire["field_reviews"] = [
        {"target_path": "/location_text", "decision": "accept_candidate"}
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_correct_decision_requires_confirmed_value() -> None:
    wire = _fixture()
    wire["disposition"] = "corrected_and_accepted"
    wire["field_reviews"] = [
        {"target_path": "/occurred_at", "decision": "correct"}
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_unresolved_requires_leave_unresolved_field_review() -> None:
    wire = _fixture()
    wire["disposition"] = "unresolved"
    wire["field_reviews"] = [
        {"target_path": "/location_text", "decision": "accept_candidate"}
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_rejected_requires_reason_code_and_no_field_reviews() -> None:
    wire = _fixture()
    wire["disposition"] = "rejected"
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_review", "1", wire)


def test_corrected_fixture_round_trips() -> None:
    wire = json.loads(
        (
            ROOT
            / "tests/fixtures/issue_20/valid_scenarios/08-corrected_import_review.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(wire, dict)
    model = parse_portia_record("import_review", "1", wire)
    assert isinstance(model, ImportReviewV1)
    assert model.to_dict() == wire
