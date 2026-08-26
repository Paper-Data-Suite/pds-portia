"""Validate Issue #37 runtime coverage, bundle construction, and model registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from portia._bundle_builder import RuntimeBundleBuildError, build_runtime_bundle
from portia.models import audit_coverage_against_catalog, runtime_coverage
from portia.models.records import MODEL_REGISTRY, assert_registry_matches_coverage
from portia.validation.issue22_parity import parity_by_id


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    catalog_path = root / "schemas" / "schema-catalog.json"
    findings.extend(audit_coverage_against_catalog(catalog_path))
    try:
        assert_registry_matches_coverage()
        bundle = build_runtime_bundle(root)
    except (RuntimeError, RuntimeBundleBuildError) as exc:
        findings.append(str(exc))
        return tuple(sorted(findings))

    contract_map = bundle.get("contracts")
    schemas = bundle.get("schemas")
    if not isinstance(contract_map, dict) or not isinstance(schemas, dict):
        findings.append("compiled runtime bundle is malformed")
    else:
        bundled_pairs = {
            (contract, version)
            for contract, versions in contract_map.items()
            if isinstance(contract, str) and isinstance(versions, dict)
            for version in versions
            if isinstance(version, str)
        }
        if bundled_pairs != set(MODEL_REGISTRY):
            findings.append("compiled bundle contract set does not match model registry")
        if not schemas:
            findings.append("compiled bundle contains no schemas")

    corpus_path = root / "tests" / "fixtures" / "issue_22" / "corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    scenarios = corpus.get("scenarios") if isinstance(corpus, dict) else None
    if not isinstance(scenarios, list):
        findings.append("Issue #22 corpus scenario list is malformed")
    else:
        scenario_ids: set[str] = set()
        for item in scenarios:
            if not isinstance(item, dict):
                continue
            scenario_id = item.get("scenario_id")
            if isinstance(scenario_id, str):
                scenario_ids.add(scenario_id)
        parity_ids = set(parity_by_id())
        if scenario_ids != parity_ids:
            findings.append(
                "Issue #22 parity matrix drift: "
                f"missing={sorted(scenario_ids - parity_ids)}, "
                f"extra={sorted(parity_ids - scenario_ids)}"
            )

    entries = runtime_coverage()
    if not any(entry.disposition == "deferred_v0_3" for entry in entries):
        findings.append("runtime coverage does not record the v0.3 paper/import deferral")
    if not any(entry.disposition == "core_owned" for entry in entries):
        findings.append("runtime coverage does not record Core-owned contract boundaries")
    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Runtime-model validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print(
        "Portia Issue #37 runtime-model validation passed: "
        f"{len(MODEL_REGISTRY)} modelled contract versions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
