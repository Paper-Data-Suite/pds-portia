from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import ImportProposalV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_import_proposal_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/10-import_proposal.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice12_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_import_proposal_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("import_proposal", "1", wire)
    assert isinstance(model, ImportProposalV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["proposal_id"]
    assert model.class_id == wire["class_id"]
    assert model.work_id is None
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["review_flags"] = ["changed"]
    assert model.to_dict() == wire


def test_source_value_binding_does_not_copy_candidate() -> None:
    wire = _fixture()
    wire["field_bindings"] = [
        {
            "target_path": "/location_text",
            "source_field_key": "location",
            "value_source": "source_value",
        }
    ]
    assert isinstance(parse_portia_record("import_proposal", "1", wire), ImportProposalV1)


def test_human_resolution_required_carries_no_candidate() -> None:
    wire = _fixture()
    wire["field_bindings"] = [
        {
            "target_path": "/participant_id",
            "source_field_key": "student_name",
            "value_source": "human_resolution_required",
        }
    ]
    assert isinstance(parse_portia_record("import_proposal", "1", wire), ImportProposalV1)


def test_transformed_candidate_requires_candidate_value() -> None:
    wire = _fixture()
    wire["field_bindings"] = [
        {
            "target_path": "/occurred_at",
            "source_field_key": "occurred_date",
            "value_source": "transformed_candidate",
        }
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_proposal", "1", wire)


def test_source_value_forbids_transformed_candidate() -> None:
    wire = _fixture()
    wire["field_bindings"] = [
        {
            "target_path": "/location_text",
            "source_field_key": "location",
            "value_source": "source_value",
            "transformed_candidate": "copied-value",
        }
    ]
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_proposal", "1", wire)


def test_new_work_rejects_child_record_family() -> None:
    wire = _fixture()
    target = wire["target"]
    assert isinstance(target, dict)
    target["record_kind"] = "account"
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_proposal", "1", wire)


def test_actor_is_not_an_import_target_family() -> None:
    wire = _fixture()
    target = wire["target"]
    assert isinstance(target, dict)
    target["record_kind"] = "actor"
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_proposal", "1", wire)


def test_paper_route_field_is_not_part_of_import_proposal() -> None:
    wire = _fixture()
    wire["route_id"] = "route_not_allowed_here"
    with pytest.raises(PortiaWireError):
        parse_portia_record("import_proposal", "1", wire)
