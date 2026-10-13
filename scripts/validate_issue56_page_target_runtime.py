"""Validate Issue #56 Slice 3 Page Target runtime promotion."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from portia._bundle_builder import build_runtime_bundle
from portia.models import PageTargetV1, PageTargetV2, parse_portia_record
from portia.models.records import MODEL_REGISTRY

V1_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/capture/page-target.schema.json"
)
V2_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v2/capture/page-target.schema.json"
)
STILL_DEFERRED = {
    "import_proposal",
    "import_review",
    "import_materialization",
}


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], raw)


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
    coverage = _json(root / "portia/runtime-coverage.json")
    dispositions = coverage.get("dispositions")
    if not isinstance(dispositions, list) or "current_v0_3" not in dispositions:
        findings.append("runtime coverage vocabulary lacks current_v0_3")

    entries = _entries(root)
    proposal = entries.get(("capture_proposal", "1"))
    if proposal is None or (
        proposal.get("disposition"),
        proposal.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("capture_proposal@1 is not current_v0_3/modelled")

    review = entries.get(("capture_review", "1"))
    if review is None or (
        review.get("disposition"),
        review.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("capture_review@1 is not current_v0_3/modelled")

    materialization = entries.get(("capture_materialization", "1"))
    if materialization is None or (
        materialization.get("disposition"),
        materialization.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append(
            "capture_materialization@1 is not current_v0_3/modelled"
        )

    import_batch = entries.get(("import_batch", "1"))
    if import_batch is None or (
        import_batch.get("disposition"),
        import_batch.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("import_batch@1 is not current_v0_3/modelled")

    interpretation = entries.get(("paper_interpretation", "1"))
    if interpretation is None or (
        interpretation.get("disposition"),
        interpretation.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("paper_interpretation@1 is not current_v0_3/modelled")

    page_record = entries.get(("page_record", "1"))
    if page_record is None or (
        page_record.get("disposition"),
        page_record.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("page_record@1 is not current_v0_3/modelled")

    capture = entries.get(("capture_batch", "1"))
    if capture is None or (
        capture.get("disposition"),
        capture.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("capture_batch@1 is not current_v0_3/modelled")

    expected = {
        ("page_target", "1"): ("historical_read", True),
        ("page_target", "2"): ("current_v0_3", True),
    }
    for key, wanted in expected.items():
        entry = entries.get(key)
        actual = None if entry is None else (
            entry.get("disposition"),
            entry.get("modelled"),
        )
        if actual != wanted:
            findings.append(
                f"{key[0]}@{key[1]} runtime mismatch: "
                f"expected={wanted!r}, actual={actual!r}"
            )

    for contract in STILL_DEFERRED:
        entry = entries.get((contract, "1"))
        if entry is None or (
            entry.get("disposition"),
            entry.get("modelled"),
        ) != ("deferred_v0_3", False):
            findings.append(f"{contract}@1 was promoted prematurely")

    if MODEL_REGISTRY.get(("page_target", "1")) is not PageTargetV1:
        findings.append("MODEL_REGISTRY page_target@1 binding is wrong")
    if MODEL_REGISTRY.get(("page_target", "2")) is not PageTargetV2:
        findings.append("MODEL_REGISTRY page_target@2 binding is wrong")

    fixture = _json(
        root
        / "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    parsed = parse_portia_record("page_target", "2", fixture)
    if not isinstance(parsed, PageTargetV2) or parsed.to_dict() != fixture:
        findings.append("page_target@2 exact runtime round-trip failed")

    compiled = build_runtime_bundle(root).get("contracts")
    page_map = compiled.get("page_target") if isinstance(compiled, dict) else None
    wanted_map = {"1": V1_ID, "2": V2_ID}
    if page_map != wanted_map:
        findings.append(f"compiled Page Target map is wrong: {page_map!r}")

    source = _json(root / "portia/_runtime_contract_bundle.json")
    source_contracts = source.get("contracts")
    source_map = (
        source_contracts.get("page_target")
        if isinstance(source_contracts, dict)
        else None
    )
    if source_map != wanted_map:
        findings.append("source runtime contract bundle is stale")

    docs = (root / "docs/runtime-models.md").read_text(encoding="utf-8")
    for marker in (
        "| Page Target | v2 | v1 |",
        "current_v0_3",
        "Capture Batch, Page Target, Page Record, and Paper Interpretation",
    ):
        if marker not in docs:
            findings.append(f"runtime-model documentation missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Issue #56 Slice 3 validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #56 Slice 3 Page Target runtime validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
