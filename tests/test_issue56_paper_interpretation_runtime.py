from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import PaperInterpretationV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_paper_interpretation_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/04-paper_interpretation.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice6_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_paper_interpretation_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("paper_interpretation", "1", wire)
    assert isinstance(model, PaperInterpretationV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["interpretation_id"]
    assert model.work_id == wire["work_id"]
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["generation"] = 2
    assert model.to_dict() == wire


def test_complete_interpretation_rejects_limitation_codes() -> None:
    wire = _fixture()
    wire["limitation_codes"] = ["partial_coverage"]
    with pytest.raises(PortiaWireError):
        parse_portia_record("paper_interpretation", "1", wire)


def test_partial_interpretation_requires_limitation_code() -> None:
    wire = _fixture()
    wire["interpretation_status"] = "partial"
    with pytest.raises(PortiaWireError):
        parse_portia_record("paper_interpretation", "1", wire)


def test_interpretation_requires_interpretation_identifier_prefix() -> None:
    wire = _fixture()
    wire["interpretation_id"] = "evt_not_an_interpretation"
    with pytest.raises(PortiaWireError):
        parse_portia_record("paper_interpretation", "1", wire)


def test_unmarked_source_state_round_trips_without_false_normalization() -> None:
    wire = _fixture()
    model = parse_portia_record("paper_interpretation", "1", wire)
    round_trip = model.to_dict()
    entries = round_trip["entries"]
    assert isinstance(entries, dict)
    entry = entries["entry"]
    assert isinstance(entry, dict)
    fields = entry["fields"]
    assert isinstance(fields, dict)
    contact = fields["family_contacted"]
    assert contact == {
        "capture_method": "mark_recognition",
        "recognition_state": "unmarked",
    }
