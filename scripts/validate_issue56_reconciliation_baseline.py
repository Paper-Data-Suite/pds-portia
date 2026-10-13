"""Validate Issue #56 Slice 1 capture/import reconciliation baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

_RELEASE_COMMIT = "83cfe05ef6b03d8453fdb60d1a1702f138d5293d"
_RELEASE_TREE = "2050bd1c7aabb47ccf2df4a8285c7a61ac360f2e"
_RELEASE_WHEEL_SHA256 = (
    "7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550"
)
_CORE_065_SHA256 = (
    "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
)

_DEFERRED_CAPTURE_IMPORT: tuple[str, ...] = ()

_CORE_OWNED: tuple[str, ...] = (
    "module_work_ref",
    "module_record_ref",
    "route_locator",
    "route_registration",
    "retained_source_scan",
)

_PAGE_TARGET_V1_PURPOSES = {
    "new_event_capture",
    "event_evidence_capture",
    "support_process_evidence_capture",
    "follow_up_capture",
    "implementation_capture",
    "fidelity_capture",
    "reentry_capture",
    "repair_capture",
    "multi_entry_event_capture",
    "other",
}

_V03_FIRST_CLASS_PURPOSE_CANDIDATES = {
    "classroom_observation_capture",
    "focused_monitoring_capture",
    "communication_capture",
}

_CAPTURE_REVIEW_V1_DISPOSITIONS = {
    "accepted",
    "corrected_and_accepted",
    "rejected",
    "unresolved",
}

_CAPTURE_REVIEW_V1_FIELD_DECISIONS = {
    "accept_candidate",
    "correct",
    "select_alternative",
    "mark_unreadable",
    "leave_unresolved",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _enum(schema: dict[str, Any], *path: str) -> set[str]:
    current: Any = schema
    for key in path:
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"missing schema path: {'/'.join(path)}")
        current = current[key]
    if not isinstance(current, list) or not all(
        isinstance(item, str) for item in current
    ):
        raise ValueError(
            f"expected string enum at schema path: {'/'.join(path)}"
        )
    return set(cast(list[str], current))


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []

    audit = _load_json(root / "docs/audits/portia-v0.2.0-release-audit.json")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict):
        findings.append("release audit lacks release_publication object")
    else:
        expected_publication = {
            "status": "verified",
            "release_commit": _RELEASE_COMMIT,
            "release_tree": _RELEASE_TREE,
            "tag": "v0.2.0",
            "wheel_sha256": _RELEASE_WHEEL_SHA256,
        }
        for key, expected in expected_publication.items():
            if publication.get(key) != expected:
                findings.append(
                    f"release publication drift for {key}: "
                    f"expected {expected!r}, found {publication.get(key)!r}"
                )

    core = audit.get("core_qualification")
    current_core = core.get("current") if isinstance(core, dict) else None
    if not isinstance(current_core, dict):
        findings.append("release audit lacks current Core qualification")
    else:
        if current_core.get("version") != "0.6.5":
            findings.append("current Core qualification is not 0.6.5")
        if current_core.get("sha256") != _CORE_065_SHA256:
            findings.append("current Core 0.6.5 wheel digest drifted")

    coverage = _load_json(root / "portia/runtime-coverage.json")
    raw_entries = coverage.get("contracts")
    if not isinstance(raw_entries, list):
        findings.append("runtime coverage contracts are malformed")
        entries: dict[tuple[str, str], dict[str, Any]] = {}
    else:
        entries = {}
        for item in raw_entries:
            if not isinstance(item, dict):
                continue
            contract = item.get("contract")
            version = item.get("version")
            if isinstance(contract, str) and isinstance(version, str):
                entries[(contract, version)] = cast(dict[str, Any], item)

    for contract in _DEFERRED_CAPTURE_IMPORT:
        entry = entries.get((contract, "1"))
        if entry is None:
            findings.append(f"missing runtime coverage entry: {contract}@1")
            continue
        if entry.get("disposition") != "deferred_v0_3":
            findings.append(
                f"{contract}@1 is no longer the Slice 1 deferred_v0_3 baseline"
            )
        if entry.get("modelled") is not False:
            findings.append(f"{contract}@1 is unexpectedly modelled at Slice 1")

    capture_proposal = entries.get(("capture_proposal", "1"))
    if capture_proposal is None or (
        capture_proposal.get("disposition"),
        capture_proposal.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("capture_proposal@1 is not the current v0.3 runtime contract")

    capture_review_runtime = entries.get(("capture_review", "1"))
    if capture_review_runtime is None or (
        capture_review_runtime.get("disposition"),
        capture_review_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append(
            "capture_review@1 is not the current v0.3 runtime contract"
        )

    capture_materialization_runtime = entries.get(("capture_materialization", "1"))
    if capture_materialization_runtime is None or (
        capture_materialization_runtime.get("disposition"),
        capture_materialization_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append(
            "capture_materialization@1 is not the current v0.3 runtime contract"
        )

    import_batch_runtime = entries.get(("import_batch", "1"))
    if import_batch_runtime is None or (
        import_batch_runtime.get("disposition"),
        import_batch_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("import_batch@1 is not the current v0.3 runtime contract")

    import_source_record_runtime = entries.get(("import_source_record", "1"))
    if import_source_record_runtime is None or (
        import_source_record_runtime.get("disposition"),
        import_source_record_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append(
            "import_source_record@1 is not the current v0.3 runtime contract"
        )

    import_proposal_runtime = entries.get(("import_proposal", "1"))
    if import_proposal_runtime is None or (
        import_proposal_runtime.get("disposition"),
        import_proposal_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("import_proposal@1 is not the current v0.3 runtime contract")

    import_review_runtime = entries.get(("import_review", "1"))
    if import_review_runtime is None or (
        import_review_runtime.get("disposition"),
        import_review_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("import_review@1 is not the current v0.3 runtime contract")

    import_materialization_runtime = entries.get(("import_materialization", "1"))
    if import_materialization_runtime is None or (
        import_materialization_runtime.get("disposition"),
        import_materialization_runtime.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append(
            "import_materialization@1 is not the current v0.3 runtime contract"
        )

    paper_interpretation = entries.get(("paper_interpretation", "1"))
    if paper_interpretation is None or (
        paper_interpretation.get("disposition"),
        paper_interpretation.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("paper_interpretation@1 is not the current v0.3 runtime contract")

    page_record = entries.get(("page_record", "1"))
    if page_record is None or (
        page_record.get("disposition"),
        page_record.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("page_record@1 is not current_v0_3/modelled")

    capture_batch = entries.get(("capture_batch", "1"))
    if capture_batch is None or (
        capture_batch.get("disposition"),
        capture_batch.get("modelled"),
    ) != ("current_v0_3", True):
        findings.append("capture_batch@1 is not the current v0.3 runtime contract")

    page_v1 = entries.get(("page_target", "1"))
    page_v2 = entries.get(("page_target", "2"))
    if page_v1 is None or (
        page_v1.get("disposition"), page_v1.get("modelled")
    ) != ("historical_read", True):
        findings.append("page_target@1 is not the promoted historical runtime read")
    if page_v2 is None or (
        page_v2.get("disposition"), page_v2.get("modelled")
    ) != ("current_v0_3", True):
        findings.append("page_target@2 is not the current v0.3 runtime contract")

    for contract in _CORE_OWNED:
        entry = entries.get((contract, "core-0.6"))
        if entry is None:
            findings.append(
                f"missing Core-owned coverage entry: {contract}@core-0.6"
            )
            continue
        if entry.get("disposition") != "core_owned":
            findings.append(f"{contract}@core-0.6 is no longer Core-owned")
        if entry.get("modelled") is not False:
            findings.append(
                f"{contract}@core-0.6 is unexpectedly Portia-modelled"
            )
        if entry.get("catalog_required") is not False:
            findings.append(
                f"{contract}@core-0.6 unexpectedly requires "
                "Portia schema catalog entry"
            )

    catalog = _load_json(root / "schemas/schema-catalog.json")
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict):
        findings.append("schema catalog contracts object is malformed")
    else:
        for contract in _DEFERRED_CAPTURE_IMPORT:
            versions = contracts.get(contract)
            if not isinstance(versions, dict) or "1" not in versions:
                findings.append(f"published schema missing: {contract}@1")

    page_target = _load_json(
        root / "schemas/v1/capture/page-target.schema.json"
    )
    try:
        purposes = _enum(
            page_target, "properties", "page_purpose", "enum"
        )
    except ValueError as exc:
        findings.append(str(exc))
    else:
        if purposes != _PAGE_TARGET_V1_PURPOSES:
            findings.append(
                "page_target@1 purpose vocabulary drifted "
                "from accepted Slice 1 baseline"
            )
        unexpected = purposes & _V03_FIRST_CLASS_PURPOSE_CANDIDATES
        if unexpected:
            findings.append(
                "page_target@1 was silently expanded with v0.3 "
                f"first-class purposes: {sorted(unexpected)}"
            )

    capture_batch = _load_json(
        root / "schemas/v1/capture/capture-batch.schema.json"
    )
    batch_props = capture_batch.get("properties")
    if not isinstance(batch_props, dict):
        findings.append("capture_batch@1 properties are malformed")
    else:
        session_fields = {
            "session_date",
            "lesson_objective",
            "lesson_steps",
            "session_context",
        }
        present = session_fields & set(batch_props)
        if present:
            findings.append(
                "capture_batch@1 was silently expanded with "
                f"class-session fields: {sorted(present)}"
            )

    observation = _load_json(
        root / "schemas/v2/observations/observation.schema.json"
    )
    try:
        work_kinds = _enum(
            observation, "properties", "work_kind", "enum"
        )
    except ValueError as exc:
        findings.append(str(exc))
    else:
        if work_kinds != {"event", "support_process"}:
            findings.append(
                "observation@2 ownership baseline drifted "
                "from Event/Support Process"
            )

    observation_invariants = observation.get(
        "x-portia-application-invariants"
    )
    if not isinstance(observation_invariants, list) or (
        "portia.observation.no_fake_event_requirement"
        not in observation_invariants
    ):
        findings.append("observation@2 lost no-fake-Event invariant")

    capture_review = _load_json(
        root / "schemas/v1/capture/capture-review.schema.json"
    )
    try:
        dispositions = _enum(
            capture_review, "properties", "disposition", "enum"
        )
        field_decisions = _enum(
            capture_review,
            "$defs",
            "fieldReview",
            "properties",
            "decision",
            "enum",
        )
    except ValueError as exc:
        findings.append(str(exc))
    else:
        if dispositions != _CAPTURE_REVIEW_V1_DISPOSITIONS:
            findings.append(
                "capture_review@1 disposition vocabulary drifted"
            )
        if field_decisions != _CAPTURE_REVIEW_V1_FIELD_DECISIONS:
            findings.append(
                "capture_review@1 field-decision vocabulary drifted"
            )

    adr = (
        root
        / "docs/decisions/"
        "0016-define-paper-assisted-capture-pds2-routing-and-import-contracts.md"
    ).read_text(encoding="utf-8")
    required_adr_markers = (
        "- **Status:** Accepted",
        "printed page ≠ domain Event",
        "OCR/mark candidate ≠ confirmed value",
        "Capture Review is an operational human-confirmation record",
        "Human review does not replace domain judgment",
    )
    for marker in required_adr_markers:
        if marker not in adr:
            findings.append(f"ADR 0016 baseline marker missing: {marker}")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Issue #56 Slice 1 validation failed: {exc}",
            file=sys.stderr,
        )
        return 1
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    print(
        "Portia Issue #56 Slice 1 reconciliation baseline validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
