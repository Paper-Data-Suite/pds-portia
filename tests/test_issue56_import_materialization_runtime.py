from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import (
    ImportMaterializationV1,
    PortiaWireError,
    parse_portia_record,
)
from portia.models.base import IDENTITY_FIELDS
from scripts.validate_issue56_import_materialization_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (
            ROOT / "tests/fixtures/issue_20/valid/12-import_materialization.json"
        ).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice14_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_import_materialization_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("import_materialization", "1", wire)

    assert isinstance(model, ImportMaterializationV1)
    assert model.contract_version == "1"
    assert model.logical_id is None
    assert model.class_id == wire["class_id"]
    assert model.work_id is None
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    copy["canonical_results"] = []
    assert model.to_dict() == wire


def test_import_materialization_has_no_standalone_identity_field() -> None:
    assert "import_materialization" not in IDENTITY_FIELDS


def test_import_materialization_rejects_invented_materialization_id() -> None:
    wire = _fixture()
    wire["materialization_id"] = "imat_not_a_public_contract"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_materialization", "1", wire)


def test_import_materialization_requires_at_least_one_canonical_result() -> None:
    wire = _fixture()
    wire["canonical_results"] = []

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_materialization", "1", wire)


def test_import_materialization_requires_exact_review_contract_version() -> None:
    wire = _fixture()
    review_ref = wire["review_ref"]
    assert isinstance(review_ref, dict)
    review_ref["contract_version"] = "2"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_materialization", "1", wire)


def test_import_materialization_rejects_copied_source_payload() -> None:
    wire = _fixture()
    wire["source_payload"] = {"student": "copied source row"}

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_materialization", "1", wire)
