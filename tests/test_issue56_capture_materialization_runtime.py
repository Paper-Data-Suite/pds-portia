from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import (
    CaptureMaterializationV1,
    PortiaWireError,
    parse_portia_record,
)
from scripts.validate_issue56_capture_materialization_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (
            ROOT / "tests/fixtures/issue_20/valid/07-capture_materialization.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice9_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_capture_materialization_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("capture_materialization", "1", wire)

    assert isinstance(model, CaptureMaterializationV1)
    assert model.contract_version == "1"
    assert model.logical_id is None
    assert model.work_id == wire["work_id"]
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    copy["canonical_results"] = []
    assert model.to_dict() == wire


def test_materialization_requires_at_least_one_canonical_result() -> None:
    wire = _fixture()
    wire["canonical_results"] = []

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_materialization", "1", wire)


def test_materialization_requires_exact_operation_journal_revision() -> None:
    wire = _fixture()
    operation_ref = wire["operation_journal_ref"]
    assert isinstance(operation_ref, dict)
    del operation_ref["journal_revision"]

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_materialization", "1", wire)


def test_materialization_rejects_unknown_result_relation() -> None:
    wire = _fixture()
    results = wire["canonical_results"]
    assert isinstance(results, list)
    first = results[0]
    assert isinstance(first, dict)
    first["result_relation"] = "mutated"

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_materialization", "1", wire)


def test_materialization_receipt_does_not_embed_raw_source_payload() -> None:
    wire = _fixture()
    wire["raw_scan_bytes"] = "not-allowed"

    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_materialization", "1", wire)
