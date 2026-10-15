"""Validate Issue #56 Slice 2 classroom-capture contract decisions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

_V1_PURPOSES = {
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

_V2_ADDITIONAL_PURPOSES = {
    "classroom_observation_capture",
    "focused_monitoring_capture",
    "communication_capture",
}


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _enum(schema: dict[str, Any], *path: str) -> set[str]:
    value: Any = schema
    for key in path:
        if not isinstance(value, dict):
            raise ValueError(f"schema path is not an object: {'/'.join(path)}")
        value = value.get(key)
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"expected string enum: {'/'.join(path)}")
    return set(cast(list[str], value))


def validate(root: Path) -> tuple[str, ...]:
    findings: list[str] = []

    adr_path = (
        root
        / "docs/decisions/"
        "0021-reconcile-classroom-observation-paper-capture-with-released-runtime.md"
    )
    adr = adr_path.read_text(encoding="utf-8")
    for marker in (
        "# ADR 0021:",
        "- **Status:** Accepted",
        "Publish additive `page_target@2`",
        "Keep `observation@2` ownership unchanged",
        "No class-day Event container",
        "Positive / general / concern cues are capture aids only",
    ):
        if marker not in adr:
            findings.append(f"ADR 0021 marker missing: {marker}")

    v1 = _json(root / "schemas/v1/capture/page-target.schema.json")
    v2 = _json(root / "schemas/v2/capture/page-target.schema.json")

    try:
        v1_purposes = _enum(v1, "properties", "page_purpose", "enum")
        v2_purposes = _enum(v2, "properties", "page_purpose", "enum")
    except ValueError as exc:
        findings.append(str(exc))
    else:
        if v1_purposes != _V1_PURPOSES:
            findings.append("page_target@1 purpose vocabulary changed")
        if v2_purposes != _V1_PURPOSES | _V2_ADDITIONAL_PURPOSES:
            findings.append("page_target@2 purpose vocabulary is not exact")

    if v2.get("$id") != (
        "https://paper-data-suite.github.io/pds-portia/"
        "schemas/v2/capture/page-target.schema.json"
    ):
        findings.append("page_target@2 has unexpected $id")

    schema_version = v2.get("properties", {}).get("schema_version")
    if not isinstance(schema_version, dict) or schema_version.get("const") != "2":
        findings.append("page_target@2 does not require schema_version=2")

    defs = v2.get("$defs")
    entry_layout = defs.get("entryLayout") if isinstance(defs, dict) else None
    entry_props = (
        entry_layout.get("properties")
        if isinstance(entry_layout, dict)
        else None
    )
    if not isinstance(entry_props, dict) or "context_entry_key" not in entry_props:
        findings.append("page_target@2 lacks entry_layout.context_entry_key")

    invariants = v2.get("x-portia-application-invariants")
    invariant_ids: set[str] = set()
    if not isinstance(invariants, list):
        findings.append("page_target@2 application invariants are malformed")
    else:
        for item in invariants:
            if not isinstance(item, dict):
                continue
            invariant_id = item.get("id")
            if isinstance(invariant_id, str):
                invariant_ids.add(invariant_id)
    for required in (
        "page_target.v2_context_entry_key_declared",
        "page_target.v2_classroom_observation_source_context",
        "page_target.v2_capture_cues_not_domain_judgment",
    ):
        if required not in invariant_ids:
            findings.append(f"page_target@2 invariant missing: {required}")

    catalog = _json(root / "schemas/schema-catalog.json")
    contracts = catalog.get("contracts")
    page_versions = (
        contracts.get("page_target")
        if isinstance(contracts, dict)
        else None
    )
    if not isinstance(page_versions, dict) or "2" not in page_versions:
        findings.append("schema catalog does not contain page_target@2")
    elif page_versions["2"].get("path") != (
        "schemas/v2/capture/page-target.schema.json"
    ):
        findings.append("schema catalog page_target@2 path is unexpected")

    coverage = _json(root / "portia/runtime-coverage.json")
    raw = coverage.get("contracts")
    page_v2_entry: dict[str, Any] | None = None
    if isinstance(raw, list):
        for item in raw:
            if (
                isinstance(item, dict)
                and item.get("contract") == "page_target"
                and item.get("version") == "2"
            ):
                page_v2_entry = cast(dict[str, Any], item)
                break
    if page_v2_entry is None:
        findings.append("runtime coverage lacks page_target@2")
    else:
        if page_v2_entry.get("disposition") != "current_v0_3":
            findings.append("page_target@2 is not current_v0_3 after runtime promotion")
        if page_v2_entry.get("modelled") is not True:
            findings.append("page_target@2 is not modelled after runtime promotion")

    page_v1_entry: dict[str, Any] | None = None
    if isinstance(raw, list):
        for item in raw:
            if (
                isinstance(item, dict)
                and item.get("contract") == "page_target"
                and item.get("version") == "1"
            ):
                page_v1_entry = cast(dict[str, Any], item)
                break
    if page_v1_entry is None or (
        page_v1_entry.get("disposition"), page_v1_entry.get("modelled")
    ) != ("historical_read", True):
        findings.append("page_target@1 is not the promoted historical runtime read")

    capture_versions = (
        contracts.get("capture_batch")
        if isinstance(contracts, dict)
        else None
    )
    if not isinstance(capture_versions, dict) or set(capture_versions) != {"1"}:
        findings.append("Capture Batch was unexpectedly versioned in Slice 2")

    capture_batch = _json(
        root / "schemas/v1/capture/capture-batch.schema.json"
    )
    batch_props = capture_batch.get("properties")
    if not isinstance(batch_props, dict):
        findings.append("capture_batch@1 properties malformed")
    else:
        forbidden_session_values = {
            "session_date",
            "lesson_objective",
            "lesson_steps",
            "session_context",
        }
        if forbidden_session_values & set(batch_props):
            findings.append(
                "capture_batch@1 unexpectedly stores returned session values"
            )

    observation = _json(
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
            findings.append("observation@2 ownership changed")

    obs_invariants = observation.get("x-portia-application-invariants")
    if not isinstance(obs_invariants, list) or (
        "portia.observation.no_fake_event_requirement" not in obs_invariants
    ):
        findings.append("observation@2 lost no-fake-Event invariant")

    observation_versions = (
        contracts.get("observation")
        if isinstance(contracts, dict)
        else None
    )
    if not isinstance(observation_versions, dict) or "3" in observation_versions:
        findings.append("Slice 2 unexpectedly introduced observation@3")

    return tuple(sorted(findings))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        findings = validate(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            f"Issue #56 Slice 2 validation failed: {exc}",
            file=sys.stderr,
        )
        return 1

    if findings:
        for finding in findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1

    print(
        "Portia Issue #56 Slice 2 classroom-capture "
        "contract decision validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
