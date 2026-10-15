"""Validate Issue #56 Slice 5 Page Record runtime promotion."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from portia._bundle_builder import build_runtime_bundle
from portia.models import PageRecordV1, parse_portia_record
from portia.models.records import MODEL_REGISTRY

PAGE_RECORD_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/capture/page-record.schema.json"
)
STILL_DEFERRED: set[str] = set()


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

    expected = {
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
    for key, wanted in expected.items():
        item = entries.get(key)
        actual = None if item is None else (
            item.get("disposition"),
            item.get("modelled"),
        )
        if actual != wanted:
            findings.append(
                f"{key[0]}@{key[1]} runtime mismatch: "
                f"expected={wanted!r}, actual={actual!r}"
            )

    for contract in STILL_DEFERRED:
        item = entries.get((contract, "1"))
        if item is None or (
            item.get("disposition"),
            item.get("modelled"),
        ) != ("deferred_v0_3", False):
            findings.append(f"{contract}@1 was promoted prematurely")

    for contract in ("route_registration", "retained_source_scan"):
        item = entries.get((contract, "core-0.6"))
        if item is None or (
            item.get("disposition"),
            item.get("modelled"),
            item.get("catalog_required"),
        ) != ("core_owned", False, False):
            findings.append(f"{contract}@core-0.6 ownership drifted")

    if MODEL_REGISTRY.get(("page_record", "1")) is not PageRecordV1:
        findings.append("MODEL_REGISTRY page_record@1 binding is wrong")

    fixture = _json(root / "tests/fixtures/issue_20/valid/03-page_record.json")
    parsed = parse_portia_record("page_record", "1", fixture)
    if not isinstance(parsed, PageRecordV1):
        findings.append("page_record@1 parser returned wrong runtime type")
    else:
        if parsed.to_dict() != fixture:
            findings.append("page_record@1 exact round-trip changed wire data")
        if parsed.logical_id != fixture.get("page_record_id"):
            findings.append("page_record@1 logical identity is not page_record_id")
        if parsed.work_id != fixture.get("work_id"):
            findings.append("page_record@1 Capture Batch work identity was not retained")

    schema = _json(root / "schemas/v1/capture/page-record.schema.json")
    raw = schema.get("x-portia-application-invariants")
    invariant_ids: set[str] = set()
    if not isinstance(raw, list):
        findings.append("page_record@1 application invariants are malformed")
    else:
        for item in raw:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                invariant_ids.add(item["id"])

    for required in (
        "page_record.core_route_exact_target",
        "page_record.retained_source_exactness",
        "page_record.idempotent_same_source_same_route",
        "page_record.same_route_different_source_distinct",
        "page_record.no_automatic_domain_materialization",
    ):
        if required not in invariant_ids:
            findings.append(f"page_record@1 invariant missing: {required}")

    contracts = build_runtime_bundle(root).get("contracts")
    page_record = contracts.get("page_record") if isinstance(contracts, dict) else None
    if page_record != {"1": PAGE_RECORD_ID}:
        findings.append(f"compiled Page Record map is wrong: {page_record!r}")

    source_contracts = _json(root / "portia/_runtime_contract_bundle.json").get("contracts")
    source_page_record = (
        source_contracts.get("page_record") if isinstance(source_contracts, dict) else None
    )
    if source_page_record != {"1": PAGE_RECORD_ID}:
        findings.append("source runtime bundle is stale for Page Record")

    docs = (root / "docs/runtime-models.md").read_text(encoding="utf-8")
    for marker in (
        "| Page Record | v1 | — |",
        "page_record@1 → current_v0_3",
        "Page Record remains non-domain retained-source processing state",
    ):
        if marker not in docs:
            findings.append(f"runtime-model documentation missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Issue #56 Slice 5 validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #56 Slice 5 Page Record runtime validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
