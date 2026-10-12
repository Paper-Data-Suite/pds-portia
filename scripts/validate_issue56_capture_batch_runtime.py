"""Validate Issue #56 Slice 4 Capture Batch runtime promotion."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from portia._bundle_builder import build_runtime_bundle
from portia.models import CaptureBatchV1, parse_portia_record
from portia.models.records import MODEL_REGISTRY

CAPTURE_BATCH_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/capture/capture-batch.schema.json"
)
STILL_DEFERRED = {
    "capture_proposal",
    "capture_review",
    "capture_materialization",
    "import_batch",
    "import_source_record",
    "import_proposal",
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

    for key, expected in {
        ("page_target", "1"): ("historical_read", True),
        ("page_target", "2"): ("current_v0_3", True),
    }.items():
        entry = entries.get(key)
        actual = None if entry is None else (
            entry.get("disposition"),
            entry.get("modelled"),
        )
        if actual != expected:
            findings.append(f"{key[0]}@{key[1]} runtime disposition drifted")

    for contract in STILL_DEFERRED:
        entry = entries.get((contract, "1"))
        if entry is None or (
            entry.get("disposition"),
            entry.get("modelled"),
        ) != ("deferred_v0_3", False):
            findings.append(f"{contract}@1 was promoted prematurely")

    if MODEL_REGISTRY.get(("capture_batch", "1")) is not CaptureBatchV1:
        findings.append("MODEL_REGISTRY capture_batch@1 binding is wrong")

    fixture = _json(root / "tests/fixtures/issue_20/valid/01-capture_batch.json")
    parsed = parse_portia_record("capture_batch", "1", fixture)
    if not isinstance(parsed, CaptureBatchV1):
        findings.append("capture_batch@1 parser returned wrong runtime type")
    else:
        if parsed.to_dict() != fixture:
            findings.append("capture_batch@1 exact round-trip changed wire data")
        if parsed.logical_id != fixture.get("work_id"):
            findings.append("capture_batch@1 logical identity is not work_id")
        if parsed.work_kind != "capture_batch":
            findings.append("capture_batch@1 work_kind was not preserved")

    batch_schema = _json(root / "schemas/v1/capture/capture-batch.schema.json")
    raw_invariants = batch_schema.get("x-portia-application-invariants")
    invariant_ids: set[str] = set()
    if isinstance(raw_invariants, list):
        for item in raw_invariants:
            if not isinstance(item, dict):
                continue
            invariant_id = item.get("id")
            if isinstance(invariant_id, str):
                invariant_ids.add(invariant_id)
    else:
        findings.append("capture_batch@1 application invariants are malformed")

    for required in (
        "capture_batch.non_domain_work_root",
        "capture_batch.lifecycle_authorization",
    ):
        if required not in invariant_ids:
            findings.append(f"capture_batch@1 invariant missing: {required}")

    work_ref = _json(root / "schemas/v1/references/portia-work-ref.schema.json")
    properties = work_ref.get("properties")
    work_kind = properties.get("work_kind") if isinstance(properties, dict) else None
    enum = work_kind.get("enum") if isinstance(work_kind, dict) else None
    work_kinds = set(enum) if isinstance(enum, list) else set()
    if work_kinds != {"event", "support_process"}:
        findings.append(
            "portia_work_ref@1 domain work kinds changed during Capture Batch promotion"
        )

    catalog = _json(root / "schemas/schema-catalog.json")
    contracts = catalog.get("contracts")
    portia_work_ref = (
        contracts.get("portia_work_ref") if isinstance(contracts, dict) else None
    )
    if not isinstance(portia_work_ref, dict) or set(portia_work_ref) != {"1"}:
        findings.append("PortiaWorkRef was unexpectedly versioned for Capture Batch")

    built = build_runtime_bundle(root)
    built_contracts = built.get("contracts")
    built_capture = (
        built_contracts.get("capture_batch")
        if isinstance(built_contracts, dict)
        else None
    )
    if built_capture != {"1": CAPTURE_BATCH_ID}:
        findings.append(f"compiled Capture Batch map is wrong: {built_capture!r}")

    source = _json(root / "portia/_runtime_contract_bundle.json")
    source_contracts = source.get("contracts")
    source_capture = (
        source_contracts.get("capture_batch")
        if isinstance(source_contracts, dict)
        else None
    )
    if source_capture != {"1": CAPTURE_BATCH_ID}:
        findings.append("source runtime contract bundle is stale for Capture Batch")

    docs = (root / "docs/runtime-models.md").read_text(encoding="utf-8")
    for marker in (
        "| Capture Batch | v1 | — |",
        "capture_batch@1 → current_v0_3",
        "Capture Batch remains operational rather than behavior-domain work",
    ):
        if marker not in docs:
            findings.append(f"runtime-model documentation missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Issue #56 Slice 4 validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #56 Slice 4 Capture Batch runtime validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
