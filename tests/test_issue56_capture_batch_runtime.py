from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import (
    CaptureBatchV1,
    PortiaWireError,
    parse_portia_record,
)
from scripts.validate_issue56_capture_batch_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/01-capture_batch.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice4_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_capture_batch_v1_is_exact_immutable_current_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("capture_batch", "1", wire)
    assert isinstance(model, CaptureBatchV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["work_id"]
    assert model.work_id == wire["work_id"]
    assert model.work_kind == "capture_batch"
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    copy["status"] = "cancelled"
    assert model.to_dict() == wire


def test_capture_batch_requires_capture_batch_identifier_prefix() -> None:
    wire = _fixture()
    wire["work_id"] = "evt_not_a_capture_batch"
    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_batch", "1", wire)


def test_capture_batch_is_not_portia_domain_work_ref() -> None:
    schema = json.loads(
        (ROOT / "schemas/v1/references/portia-work-ref.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["properties"]["work_kind"]["enum"] == [
        "event",
        "support_process",
    ]
