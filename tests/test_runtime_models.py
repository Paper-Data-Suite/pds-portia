from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia._bundle_builder import RUNTIME_VALUE_SCHEMA_IDS, build_runtime_bundle
from portia.models import (
    EventV1,
    EventV2,
    PortiaWireError,
    audit_coverage_against_catalog,
    parse_portia_record,
    runtime_coverage,
)
from portia.models.records import MODEL_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[1]


def _json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_runtime_coverage_matches_live_catalog_and_registry() -> None:
    assert audit_coverage_against_catalog(REPO_ROOT / "schemas" / "schema-catalog.json") == ()
    modelled = {
        (entry.contract, entry.version) for entry in runtime_coverage() if entry.modelled
    }
    assert modelled == set(MODEL_REGISTRY)
    assert any(entry.disposition == "deferred_v0_3" for entry in runtime_coverage())
    assert any(entry.disposition == "core_owned" for entry in runtime_coverage())


def test_runtime_value_schema_roots_are_live_catalog_entries() -> None:
    catalog = _json(REPO_ROOT / "schemas" / "schema-catalog.json")
    contracts = catalog.get("contracts")
    assert isinstance(contracts, dict)
    catalog_schema_ids = {
        schema_id
        for versions in contracts.values()
        if isinstance(versions, dict)
        for entry in versions.values()
        if isinstance(entry, dict)
        for schema_id in [entry.get("schema_id")]
        if isinstance(schema_id, str)
    }
    assert RUNTIME_VALUE_SCHEMA_IDS <= catalog_schema_ids


def test_runtime_bundle_contains_only_modelled_contract_map() -> None:
    bundle = build_runtime_bundle(REPO_ROOT)
    contracts = bundle["contracts"]
    assert isinstance(contracts, dict)
    pairs = {
        (contract, version)
        for contract, versions in contracts.items()
        if isinstance(contract, str) and isinstance(versions, dict)
        for version in versions
        if isinstance(version, str)
    }
    assert pairs == set(MODEL_REGISTRY)
    assert "capture_batch" not in contracts
    assert "import_batch" not in contracts
    schemas = bundle["schemas"]
    assert isinstance(schemas, dict)
    assert RUNTIME_VALUE_SCHEMA_IDS <= set(schemas)


def test_event_v2_is_immutable_and_round_trips_without_normalization() -> None:
    path = (
        REPO_ROOT
        / "tests/fixtures/issue_22/positive/p22_01_positive_classroom_event/records/event.json"
    )
    wire = _json(path)
    model = parse_portia_record("event", "2", wire)
    assert isinstance(model, EventV2)
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    with pytest.raises(TypeError):
        model._data["status"] = "closed"  # type: ignore[index]
    assert not hasattr(model, "__dict__")
    with pytest.raises((AttributeError, TypeError)):
        model.extra_state = "not allowed"  # type: ignore[attr-defined]
    copy = model.to_dict()
    copy["status"] = "cancelled"
    assert model.to_dict() == wire


def test_historical_event_remains_historical_on_parse() -> None:
    path = (
        REPO_ROOT
        / "tests/schema_validation/fixtures/migrations/event_v1_to_v2/minimal-draft.json"
    )
    migration_fixture = _json(path)
    wire = migration_fixture.get("source_v1")
    assert isinstance(wire, dict)
    model = parse_portia_record("event", "1", wire)
    assert isinstance(model, EventV1)
    assert model.contract_version == "1"
    assert model.to_dict() == wire


def test_unknown_event_field_is_rejected() -> None:
    path = (
        REPO_ROOT
        / "tests/fixtures/issue_22/positive/p22_01_positive_classroom_event/records/event.json"
    )
    wire = _json(path)
    wire["not_a_public_field"] = True
    with pytest.raises(PortiaWireError, match="unknown field"):
        parse_portia_record("event", "2", wire)


def test_wrong_contract_version_is_not_silently_migrated() -> None:
    path = (
        REPO_ROOT
        / "tests/fixtures/issue_22/positive/p22_01_positive_classroom_event/records/event.json"
    )
    wire = _json(path)
    with pytest.raises(PortiaWireError):
        parse_portia_record("event", "1", wire)
