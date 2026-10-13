"""Validate Issue #56 Slice 6 Paper Interpretation runtime promotion."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from portia._bundle_builder import build_runtime_bundle
from portia.models import PaperInterpretationV1, parse_portia_record
from portia.models.records import MODEL_REGISTRY

PAPER_INTERPRETATION_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/capture/paper-interpretation.schema.json"
)
STILL_DEFERRED = {
    "import_review",
    "import_materialization",
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _entries(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    raw = _json(root / "portia/runtime-coverage.json").get("contracts")
    if not isinstance(raw, list):
        raise ValueError("runtime coverage contracts are malformed")
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        contract = item.get("contract")
        version = item.get("version")
        if isinstance(contract, str) and isinstance(version, str):
            result[(contract, version)] = cast(dict[str, Any], item)
    return result


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    entries = _entries(root)
    expected_runtime = {
        ("capture_batch", "1"): ("current_v0_3", True),
        ("page_target", "1"): ("historical_read", True),
        ("page_target", "2"): ("current_v0_3", True),
        ("page_record", "1"): ("current_v0_3", True),
        ("paper_interpretation", "1"): ("current_v0_3", True),
        ("capture_proposal", "1"): ("current_v0_3", True),
        ("capture_review", "1"): ("current_v0_3", True),
        ("capture_materialization", "1"): ("current_v0_3", True),
        ("import_batch", "1"): ("current_v0_3", True),
        ("import_source_record", "1"): ("current_v0_3", True),
    }
    for key, expected in expected_runtime.items():
        item = entries.get(key)
        actual = None if item is None else (
            item.get("disposition"), item.get("modelled")
        )
        if actual != expected:
            findings.append(
                f"{key[0]}@{key[1]} runtime mismatch: "
                f"expected={expected!r}, actual={actual!r}"
            )

    for contract in STILL_DEFERRED:
        item = entries.get((contract, "1"))
        if item is None or (
            item.get("disposition"), item.get("modelled")
        ) != ("deferred_v0_3", False):
            findings.append(f"{contract}@1 was promoted prematurely")

    if MODEL_REGISTRY.get(("paper_interpretation", "1")) is not PaperInterpretationV1:
        findings.append("MODEL_REGISTRY paper_interpretation@1 binding is wrong")

    fixture = _json(root / "tests/fixtures/issue_20/valid/04-paper_interpretation.json")
    parsed = parse_portia_record("paper_interpretation", "1", fixture)
    if not isinstance(parsed, PaperInterpretationV1):
        findings.append("paper_interpretation@1 parser returned wrong runtime type")
    else:
        if parsed.to_dict() != fixture:
            findings.append("paper_interpretation@1 exact round-trip changed wire data")
        if parsed.logical_id != fixture.get("interpretation_id"):
            findings.append("paper_interpretation@1 logical identity is not interpretation_id")
        if parsed.work_id != fixture.get("work_id"):
            findings.append("paper_interpretation@1 Capture Batch work identity was not retained")

    schema = _json(root / "schemas/v1/capture/paper-interpretation.schema.json")
    raw = schema.get("x-portia-application-invariants")
    invariant_ids: set[str] = set()
    if not isinstance(raw, list):
        findings.append("paper_interpretation@1 application invariants are malformed")
    else:
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                invariant_ids.add(item["id"])

    for required in (
        "paper_interpretation.same_profile_replay_idempotent",
        "paper_interpretation.changed_profile_new_generation",
        "paper_interpretation.immutable_generation",
        "paper_interpretation.uncertainty_is_not_negative",
        "paper_interpretation.candidate_not_confirmed",
        "paper_interpretation.confidence_review_priority_only",
        "paper_interpretation.no_identity_or_judgment_inference",
        "paper_interpretation.no_automatic_materialization",
    ):
        if required not in invariant_ids:
            findings.append(f"paper_interpretation@1 invariant missing: {required}")

    contracts = build_runtime_bundle(root).get("contracts")
    built = contracts.get("paper_interpretation") if isinstance(contracts, dict) else None
    if built != {"1": PAPER_INTERPRETATION_ID}:
        findings.append(f"compiled Paper Interpretation map is wrong: {built!r}")

    source_contracts = _json(root / "portia/_runtime_contract_bundle.json").get("contracts")
    source = (
        source_contracts.get("paper_interpretation")
        if isinstance(source_contracts, dict)
        else None
    )
    if source != {"1": PAPER_INTERPRETATION_ID}:
        findings.append("source runtime bundle is stale for Paper Interpretation")

    docs = (root / "docs/runtime-models.md").read_text(encoding="utf-8")
    for marker in (
        "| Paper Interpretation | v1 | — |",
        "paper_interpretation@1 → current_v0_3",
        "Paper Interpretation remains immutable machine/manual staging data",
    ):
        if marker not in docs:
            findings.append(f"runtime-model documentation missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Issue #56 Slice 6 validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #56 Slice 6 Paper Interpretation runtime validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
