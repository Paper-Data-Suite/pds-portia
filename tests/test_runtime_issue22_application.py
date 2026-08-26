from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import MODEL_REGISTRY, PortiaRecord, parse_portia_record
from portia.validation import (
    GraphValidationOptions,
    parity_by_id,
    validate_record_graph,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"


def _load_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _scenario(scenario_id: str) -> tuple[Path, dict[str, object]]:
    corpus = _load_object(CORPUS_ROOT / "corpus.json")
    entries = corpus["scenarios"]
    assert isinstance(entries, list)
    for item in entries:
        if isinstance(item, dict) and item.get("scenario_id") == scenario_id:
            relative = item.get("path")
            assert isinstance(relative, str)
            path = CORPUS_ROOT / relative
            return path, _load_object(path)
    raise AssertionError(f"missing Issue #22 scenario: {scenario_id}")


def _modelled_records(scenario_path: Path, scenario: dict[str, object]) -> tuple[PortiaRecord, ...]:
    descriptors = scenario.get("records")
    assert isinstance(descriptors, list)
    records: list[PortiaRecord] = []
    for descriptor in descriptors:
        assert isinstance(descriptor, dict)
        contract = descriptor.get("contract")
        version = descriptor.get("version")
        relative = descriptor.get("fixture_path")
        assert isinstance(contract, str)
        assert isinstance(version, str)
        assert isinstance(relative, str)
        if (contract, version) not in MODEL_REGISTRY:
            continue
        records.append(
            parse_portia_record(
                contract,
                version,
                _load_object(scenario_path.parent / relative),
            )
        )
    return tuple(records)


POSITIVE_SCENARIOS = tuple(
    entry.scenario_id
    for entry in parity_by_id().values()
    if entry.disposition == "covered_by_37" and entry.scenario_id.startswith("P22-")
)

INVALID_SCENARIOS = tuple(
    entry.scenario_id
    for entry in parity_by_id().values()
    if entry.disposition == "covered_by_37" and entry.scenario_id.startswith("G22-")
)


@pytest.mark.parametrize("scenario_id", POSITIVE_SCENARIOS)
def test_covered_issue22_positive_graphs_pass_production_validation(
    scenario_id: str,
) -> None:
    path, scenario = _scenario(scenario_id)
    records = _modelled_records(path, scenario)
    findings = validate_record_graph(
        records,
        options=GraphValidationOptions(require_internal_resolution=True),
    )
    assert findings == (), (scenario_id, findings)


@pytest.mark.parametrize("scenario_id", INVALID_SCENARIOS)
def test_covered_issue22_invalid_graphs_produce_mapped_production_finding(
    scenario_id: str,
) -> None:
    path, scenario = _scenario(scenario_id)
    records = _modelled_records(path, scenario)
    findings = validate_record_graph(
        records,
        options=GraphValidationOptions(require_internal_resolution=True),
    )
    codes = {finding.code for finding in findings}
    expected = set(parity_by_id()[scenario_id].production_codes)
    assert expected
    assert codes & expected, (scenario_id, expected, findings)
