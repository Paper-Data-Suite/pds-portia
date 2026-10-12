from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest

from portia.models import CaptureProposalV1, PortiaWireError, parse_portia_record
from scripts.validate_issue56_capture_proposal_runtime import validate

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    value = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/05-capture_proposal.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue56_slice7_runtime_validator_has_no_findings() -> None:
    assert validate(ROOT) == ()


def test_capture_proposal_v1_is_exact_immutable_runtime_read() -> None:
    wire = _fixture()
    model = parse_portia_record("capture_proposal", "1", wire)
    assert isinstance(model, CaptureProposalV1)
    assert model.contract_version == "1"
    assert model.logical_id == wire["proposal_id"]
    assert model.work_id == wire["work_id"]
    assert model.to_dict() == wire
    assert isinstance(model._data, MappingProxyType)
    copy = model.to_dict()
    copy["review_flags"] = ["changed"]
    assert model.to_dict() == wire


def test_capture_proposal_requires_proposal_identifier_prefix() -> None:
    wire = _fixture()
    wire["proposal_id"] = "evt_not_a_capture_proposal"
    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_proposal", "1", wire)


def test_new_work_context_only_allows_event_or_support_process() -> None:
    wire = _fixture()
    target = wire["target"]
    assert isinstance(target, dict)
    target["record_kind"] = "observation"
    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_proposal", "1", wire)


def test_field_binding_target_path_must_be_absolute() -> None:
    wire = _fixture()
    bindings = wire["field_bindings"]
    assert isinstance(bindings, list)
    binding = bindings[0]
    assert isinstance(binding, dict)
    binding["target_path"] = "location_text"
    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_proposal", "1", wire)


def test_proposal_cannot_copy_candidate_value_into_source_field() -> None:
    wire = _fixture()
    bindings = wire["field_bindings"]
    assert isinstance(bindings, list)
    binding = bindings[0]
    assert isinstance(binding, dict)
    source = binding["source_field"]
    assert isinstance(source, dict)
    source["candidate_literal"] = "Room 214"
    with pytest.raises(PortiaWireError):
        parse_portia_record("capture_proposal", "1", wire)
