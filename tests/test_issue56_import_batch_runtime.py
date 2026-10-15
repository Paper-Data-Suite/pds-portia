from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import ImportBatchV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_import_batch_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (
            ROOT / "tests/fixtures/issue_20/valid/08-import_batch.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice10_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_import_batch_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("import_batch", "1", wire)

    assert isinstance(model, ImportBatchV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["import_batch_id"]
    assert model.class_id == wire["class_id"]
    assert model.status == "open"
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    copy["status"] = "failed"
    assert model.to_dict() == wire


def test_open_batch_forbids_finished_at() -> None:
    wire = _fixture()
    wire["finished_at"] = "2026-08-14T11:41:00-04:00"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_batch", "1", wire)


def test_open_batch_forbids_failure_codes() -> None:
    wire = _fixture()
    wire["failure_codes"] = ["source_read_failed"]

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_batch", "1", wire)


def test_completed_batch_requires_finished_at() -> None:
    wire = _fixture()
    wire["status"] = "completed"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_batch", "1", wire)


def test_failed_batch_requires_finished_at_and_failure_code() -> None:
    wire = _fixture()
    wire["status"] = "failed"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_batch", "1", wire)


def test_completed_batch_with_finished_at_round_trips() -> None:
    wire = _fixture()
    wire["status"] = "completed"
    wire["finished_at"] = "2026-08-14T11:41:00-04:00"

    model = parse_portia_record("import_batch", "1", wire)
    assert isinstance(model, ImportBatchV1)
    assert model.to_dict() == wire


def test_failed_batch_with_failure_code_round_trips() -> None:
    wire = _fixture()
    wire["status"] = "failed"
    wire["failure_codes"] = ["source_read_failed"]
    wire["finished_at"] = "2026-08-14T11:41:00-04:00"

    model = parse_portia_record("import_batch", "1", wire)
    assert isinstance(model, ImportBatchV1)
    assert model.to_dict() == wire
