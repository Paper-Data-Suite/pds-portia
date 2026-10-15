from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import ImportSourceRecordV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_import_source_record_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/09-import_source_record.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice11_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_import_source_record_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("import_source_record", "1", wire)

    assert isinstance(model, ImportSourceRecordV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["source_record_id"]
    assert model.class_id == wire["class_id"]
    assert model.work_id is None
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)

    copy = model.to_dict()
    source_fields = copy["source_fields"]
    assert isinstance(source_fields, list)
    first = source_fields[0]
    assert isinstance(first, dict)
    first["value"] = "changed"
    assert model.to_dict() == wire


def test_import_source_record_preserves_explicit_null() -> None:
    wire = _fixture()
    model = parse_portia_record("import_source_record", "1", wire)
    result = model.to_dict()
    fields = result["source_fields"]
    assert isinstance(fields, list)
    values = {
        item["field_key"]: item["value"]
        for item in fields
        if isinstance(item, dict)
    }
    assert "optional_note" in values
    assert values["optional_note"] is None


def test_import_source_record_allows_absent_normalized_field() -> None:
    wire = _fixture()
    fields = wire["source_fields"]
    assert isinstance(fields, list)
    wire["source_fields"] = [
        item
        for item in fields
        if isinstance(item, dict) and item.get("field_key") != "optional_note"
    ]

    model = parse_portia_record("import_source_record", "1", wire)
    assert isinstance(model, ImportSourceRecordV1)
    assert model.to_dict() == wire


def test_import_source_record_rejects_nested_source_object() -> None:
    wire = _fixture()
    fields = wire["source_fields"]
    assert isinstance(fields, list)
    fields.append({"field_key": "nested", "value": {"unsafe": "object"}})

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_source_record", "1", wire)


def test_import_source_record_rejects_unknown_key_origin() -> None:
    wire = _fixture()
    wire["source_record_key_origin"] = "row_number"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_source_record", "1", wire)


def test_import_source_record_rejects_wrong_local_id_prefix() -> None:
    wire = _fixture()
    wire["source_record_id"] = "ibat_not_a_source_record"

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_source_record", "1", wire)


def test_import_source_record_rejects_nested_array_payload() -> None:
    wire = _fixture()
    fields = wire["source_fields"]
    assert isinstance(fields, list)
    fields.append(
        {"field_key": "nested_array", "value": [["not-a-scalar-array"]]}
    )

    with pytest.raises(PortiaWireError):
        parse_portia_record("import_source_record", "1", wire)
