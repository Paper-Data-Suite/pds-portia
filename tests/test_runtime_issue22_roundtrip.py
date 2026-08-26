from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.records import MODEL_REGISTRY
from portia.validation.issue22_parity import parity_by_id

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"


def _object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _safe_path(base: Path, relative: str) -> Path:
    candidate = (base / relative).resolve()
    candidate.relative_to(CORPUS_ROOT.resolve())
    return candidate


def test_issue22_parity_matrix_covers_every_scenario_exactly_once() -> None:
    corpus = _object(CORPUS_ROOT / "corpus.json")
    scenarios = corpus["scenarios"]
    assert isinstance(scenarios, list)
    ids = {
        item["scenario_id"]
        for item in scenarios
        if isinstance(item, dict) and isinstance(item.get("scenario_id"), str)
    }
    assert set(parity_by_id()) == ids


def test_all_modelled_issue22_public_records_round_trip() -> None:
    corpus = _object(CORPUS_ROOT / "corpus.json")
    scenarios = corpus["scenarios"]
    assert isinstance(scenarios, list)
    exercised: set[tuple[str, str]] = set()
    for scenario_entry in scenarios:
        assert isinstance(scenario_entry, dict)
        scenario_path_text = scenario_entry.get("path")
        assert isinstance(scenario_path_text, str)
        scenario_path = _safe_path(CORPUS_ROOT, scenario_path_text)
        scenario = _object(scenario_path)
        for collection_name in (
            "records",
            "operational_contract_fixtures",
            "derived_contract_fixtures",
        ):
            descriptors = scenario.get(collection_name, [])
            assert isinstance(descriptors, list)
            for descriptor in descriptors:
                assert isinstance(descriptor, Mapping)
                contract = descriptor.get("contract")
                version = descriptor.get("version")
                relative = descriptor.get("fixture_path")
                if not (
                    isinstance(contract, str)
                    and isinstance(version, str)
                    and isinstance(relative, str)
                ):
                    continue
                key = (contract, version)
                if key not in MODEL_REGISTRY:
                    continue
                wire = _object(_safe_path(scenario_path.parent, relative))
                model = parse_portia_record(contract, version, wire)
                assert model.to_dict() == wire, f"round-trip drift: {contract}@{version}"
                exercised.add(key)
    # Issue #22 need not contain every specialized administrative positive record,
    # but it must exercise the primary executable families.
    for key in {
        ("event", "2"),
        ("event_participant", "3"),
        ("event_participant_role", "3"),
        ("account", "2"),
        ("observation", "2"),
        ("review", "1"),
        ("determination", "1"),
        ("response", "1"),
        ("communication", "1"),
        ("support_process", "1"),
        ("implementation", "1"),
        ("follow_up", "1"),
        ("outcome", "1"),
    }:
        assert key in exercised
