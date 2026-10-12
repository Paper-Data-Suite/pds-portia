from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import CaptureReviewV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_capture_review_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (
            ROOT / "tests/fixtures/issue_20/valid/06-capture_review.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice8_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_capture_review_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("capture_review", "1", wire)

    assert isinstance(model, CaptureReviewV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["review_id"]
    assert model.work_id == wire["work_id"]
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    copy["disposition"] = "rejected"
    assert model.to_dict() == wire


def test_sequence_one_forbids_predecessor() -> None:
    wire = _fixture()
    wire["predecessor_review_id"] = "crev_previous_01"

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)


def test_later_sequence_requires_predecessor() -> None:
    wire = _fixture()
    wire["review_sequence"] = 2

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)


def test_accepted_review_forbids_reason_codes() -> None:
    wire = _fixture()
    wire["reason_codes"] = ["teacher_correction"]

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)


def test_corrected_acceptance_requires_correction_or_alternative() -> None:
    wire = _fixture()
    wire["disposition"] = "corrected_and_accepted"

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)


def test_unresolved_review_requires_unresolved_field_decision() -> None:
    wire = _fixture()
    wire["disposition"] = "unresolved"

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)


def test_system_process_cannot_be_substantive_reviewer() -> None:
    wire = _fixture()
    wire["reviewer"] = {
        "type": "system_process",
        "process_id": "not_a_human_reviewer",
    }

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_review", "1", wire)
