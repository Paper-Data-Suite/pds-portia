"""Validate Issue #56 Slice 14 Import Materialization runtime promotion."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from portia._bundle_builder import build_runtime_bundle
from portia.models import ImportMaterializationV1, parse_portia_record
from portia.models.base import IDENTITY_FIELDS
from portia.models.records import MODEL_REGISTRY

IMPORT_MATERIALIZATION_ID = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/imports/import-materialization.schema.json"
)


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
        ("import_proposal", "1"): ("current_v0_3", True),
        ("import_review", "1"): ("current_v0_3", True),
        ("import_materialization", "1"): ("current_v0_3", True),
    }
    for key, expected in expected_runtime.items():
        item = entries.get(key)
        actual = None if item is None else (
            item.get("disposition"),
            item.get("modelled"),
        )
        if actual != expected:
            findings.append(
                f"{key[0]}@{key[1]} runtime mismatch: "
                f"expected={expected!r}, actual={actual!r}"
            )

    remaining_deferred = sorted(
        contract
        for (contract, version), item in entries.items()
        if version == "1"
        and contract.startswith("import_")
        and item.get("disposition") == "deferred_v0_3"
    )
    if remaining_deferred:
        findings.append(
            f"import contracts remain deferred after Slice 14: {remaining_deferred!r}"
        )

    if (
        MODEL_REGISTRY.get(("import_materialization", "1"))
        is not ImportMaterializationV1
    ):
        findings.append("MODEL_REGISTRY import_materialization@1 binding is wrong")

    if "import_materialization" in IDENTITY_FIELDS:
        findings.append(
            "Import Materialization incorrectly invents a standalone logical ID"
        )

    fixture = _json(
        root / "tests/fixtures/issue_20/valid/12-import_materialization.json"
    )
    parsed = parse_portia_record("import_materialization", "1", fixture)
    if not isinstance(parsed, ImportMaterializationV1):
        findings.append("import_materialization@1 parser returned wrong runtime type")
    else:
        if parsed.to_dict() != fixture:
            findings.append(
                "import_materialization@1 exact round-trip changed wire data"
            )
        if parsed.logical_id is not None:
            findings.append("import_materialization@1 must not fabricate logical_id")
        if parsed.class_id != fixture.get("class_id"):
            findings.append("import_materialization@1 class scope was not retained")
        if parsed.work_id is not None:
            findings.append("import_materialization@1 must not fabricate work identity")

    schema = _json(root / "schemas/v1/imports/import-materialization.schema.json")
    raw_invariants = schema.get("x-portia-application-invariants")
    invariant_ids: set[str] = set()
    if not isinstance(raw_invariants, list):
        findings.append("import_materialization@1 application invariants are malformed")
    else:
        for item in raw_invariants:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                invariant_ids.add(item["id"])

    for required in (
        "import_materialization.lineage_exactness",
        "import_materialization.batch_identity_exactness",
        "import_materialization.source_record_identity_exactness",
        "import_materialization.review_must_authorize_next_step",
        "import_materialization.review_is_not_domain_judgment",
        "import_materialization.operation_reuse",
        "import_materialization.operation_journal_exactness",
        "import_materialization.lock_and_preflight_reuse",
        "import_materialization.results_exactness",
        "import_materialization.produced_vs_affected",
        "import_materialization.import_creation_source",
        "import_materialization.source_artifact_alignment",
        "import_materialization.source_assertions_not_judgments",
        "import_materialization.no_import_time_as_domain_time",
        "import_materialization.context_exactness",
        "import_materialization.no_duplicate_canonical_records",
        "import_materialization.unchanged_replay_idempotent",
        "import_materialization.changed_source_or_mapping_preserves_history",
        "import_materialization.missing_later_source_not_deletion",
        "import_materialization.receipt_after_canonical_acceptance",
        "import_materialization.later_review_or_correction_preserves_history",
        "import_materialization.no_raw_source_payload",
        "import_materialization.not_quarantine",
    ):
        if required not in invariant_ids:
            findings.append(f"import_materialization@1 invariant missing: {required}")

    contracts = build_runtime_bundle(root).get("contracts")
    built = (
        contracts.get("import_materialization")
        if isinstance(contracts, dict)
        else None
    )
    if built != {"1": IMPORT_MATERIALIZATION_ID}:
        findings.append(f"compiled Import Materialization map is wrong: {built!r}")

    source_contracts = _json(
        root / "portia/_runtime_contract_bundle.json"
    ).get("contracts")
    source = (
        source_contracts.get("import_materialization")
        if isinstance(source_contracts, dict)
        else None
    )
    if source != {"1": IMPORT_MATERIALIZATION_ID}:
        findings.append("source runtime bundle is stale for Import Materialization")

    docs = (root / "docs/runtime-models.md").read_text(encoding="utf-8")
    for marker in (
        "| Import Materialization | v1 | — |",
        "import_materialization@1 → current_v0_3",
        "Import Materialization remains an immutable operational receipt",
        "All accepted Issue #56 paper/import operational contract families are now",
    ):
        if marker not in docs:
            findings.append(f"runtime-model documentation missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Issue #56 Slice 14 validation failed: {exc}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print(
        "Portia Issue #56 Slice 14 Import Materialization runtime validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
