from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import PageRecordV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_page_record_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/03-page_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice5_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_page_record_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("page_record", "1", wire)
    assert isinstance(model, PageRecordV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["page_record_id"]
    assert model.work_id == wire["work_id"]
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["processing_state"] = "failed"
    assert model.to_dict() == wire


def test_page_record_failed_state_requires_failure_detail() -> None:
    wire = _fixture()
    wire["processing_state"] = "failed"
    with pytest.raises(PortiaWireError):
        parse_portia_record("page_record", "1", wire)


def test_page_record_nonfailed_state_rejects_failure_detail() -> None:
    wire = _fixture()
    wire["failure_detail"] = "not allowed for received"
    with pytest.raises(PortiaWireError):
        parse_portia_record("page_record", "1", wire)


def test_page_record_requires_page_record_identifier_prefix() -> None:
    wire = _fixture()
    wire["page_record_id"] = "evt_not_a_page_record"
    with pytest.raises(PortiaWireError):
        parse_portia_record("page_record", "1", wire)
