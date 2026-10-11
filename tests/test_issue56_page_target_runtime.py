from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import (
    PageTargetV1,
    PageTargetV2,
    PortiaLocalValidationError,
    parse_portia_record,
)
from scripts.validate_issue56_page_target_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_issue56_slice3_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_page_target_v1_is_exact_historical_read() -> None:
    wire = _fixture("tests/fixtures/issue_20/valid/02-page_target.json")
    model = parse_portia_record("page_target", "1", wire)
    assert isinstance(model, PageTargetV1)
    assert model.contract_version == "1"
    assert model.to_dict() == wire


def test_page_target_v2_is_exact_immutable_current_read() -> None:
    wire = _fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    model = parse_portia_record("page_target", "2", wire)
    assert isinstance(model, PageTargetV2)
    assert model.contract_version == "2"
    assert model.logical_id == "ptgt_classroom_20261011"
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["status"] = "cancelled"
    assert model.to_dict() == wire


def test_page_target_v2_rejects_undeclared_context_entry() -> None:
    wire = deepcopy(
        _fixture(
            "tests/fixtures/issue_56/slice_2/valid/"
            "page-target-v2-classroom-observation.json"
        )
    )
    layout = wire["entry_layout"]
    assert isinstance(layout, dict)
    layout["context_entry_key"] = "missing_entry"
    with pytest.raises(
        PortiaLocalValidationError,
        match="context_entry_key must name one declared entry_key",
    ):
        parse_portia_record("page_target", "2", wire)
