"""Protect Issue #22 graph-evidence provenance after Issue #56 page_target@2."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _json(relative: str) -> dict[str, object]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_issue22_manifest_versions_match_live_catalog() -> None:
    catalog = _json("schemas/schema-catalog.json")["contracts"]
    manifest = _json("tests/fixtures/issue_22/contract-coverage.json")
    assert isinstance(catalog, dict)
    assert len(manifest["contracts"]) == len(catalog) == 163
    indexed = {item["contract"]: item for item in manifest["contracts"]}
    assert set(indexed) == set(catalog)
    for contract, versions in catalog.items():
        assert indexed[contract]["catalog_versions"] == sorted(versions, key=int)


def test_issue56_page_target_advancement_does_not_rewrite_p22_graph_evidence() -> None:
    manifest = _json("tests/fixtures/issue_22/contract-coverage.json")
    page_target = next(
        item for item in manifest["contracts"] if item["contract"] == "page_target"
    )
    assert page_target["catalog_versions"] == ["1", "2"]
    assert page_target["current_version"] == "2"
    assert page_target["disposition"] == "positive_graph"
    assert page_target["evidence"] == "P22-05"
    assert "v1" in page_target["rationale"]
    assert "v2" in page_target["rationale"]
    scenario = _json(
        "tests/fixtures/issue_22/positive/"
        "p22_05_paper_capture_materialization/scenario.json"
    )
    target_versions = [
        rec["version"] for rec in scenario["records"]
        if rec["contract"] == "page_target"
    ]
    assert target_versions == ["1"]


def test_issue22_documentation_distinguishes_new_v2_from_old_v1_coverage() -> None:
    doc = (ROOT / "docs/validation/issue-22-contract-coverage-matrix.md").read_text(
        encoding="utf-8"
    )
    assert "| `page_target` | 2 (P22-05 used v1) | positive_graph |" in doc
    assert "P22-05` synthetic graph continues to use **v1**" in doc
    assert "not be read as evidence that it exercised v2" in doc
    assert "test_issue_56_page_target_v2.py" in doc
