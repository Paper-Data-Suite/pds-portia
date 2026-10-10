from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "read_only_surfaces"

MARKERS: dict[str, tuple[str, ...]] = {
    "scripts/smoke_test_issue53_end_to_end_wheel.py": (
        "_READ_ONLY_SURFACES_PROBE = r",
        "def snapshot(root):",
        "def require_read_only(label, operation):",
        'raise RuntimeError(f"{label} mutated workspace bytes")',
        '"student timeline/view query"',
        '"attention query"',
        '"Core readiness/attention provider invocation"',
        '"teacher-reference export history verification"',
        '"exact historical predecessor loads"',
        "whole_phase_before = snapshot(workspace)",
        "whole_phase_after = snapshot(workspace)",
        "combined Issue #53 read-only phase mutated workspace bytes",
        '"whole_read_only_phase_zero_write"',
    ),
    "tests/test_issue53_end_to_end_acceptance.py": (
        "test_issue53_attention_queries_are_zero_write",
        "test_issue53_core_provider_boundary_is_zero_write",
        "test_issue53_student_view_is_snapshot_proven_read_only",
        "test_issue53_read_only_phase_snapshots_each_required_surface",
        "test_issue53_read_only_phase_uses_production_services",
        "test_issue53_read_only_phase_verifies_historical_predecessors_exactly",
        "test_issue53_read_only_phase_has_combined_byte_snapshot_guard",
    ),
    "portia/views/student.py": (
        "Composed read-only student timeline and work view for Issue #48.",
        "Completed privacy-minimized read-only student timeline/work view.",
    ),
    "portia/views/history.py": (
        "History is bounded to already-discovered focal work and exact references.",
        "never reads technical storage-history blobs and never selects currentness by",
        "Deliberate domain history attached to one history-mode discovery result.",
    ),
    "portia/pds_operations.py": (
        "Lazily evaluate Portia-owned attention for one neutral Core request.",
        "Lazily evaluate Portia-owned readiness for one neutral Core request.",
    ),
    "tests/test_teacher_menu_timeline.py": (
        "test_current_student_view_delegates_to_production_service_and_is_zero_write",
        "test_history_read_is_explicit_and_stays_zero_write",
        "test_interactive_current_timeline_view_is_zero_write",
    ),
    "tests/test_teacher_menu_attention.py": (
        "test_empty_workspace_attention_is_evaluated_and_zero_write",
    ),
    "tests/test_teacher_menu_advanced.py": (
        "test_empty_technical_inspection_is_read_only",
        "test_advanced_entry_back_is_zero_read_and_zero_write",
    ),
    "tests/test_teacher_menu_teacher_reference_export.py": (
        "test_cancel_at_exact_preview_is_zero_write",
        "test_history_surface_is_read_only_and_does_not_assign_current_authority",
    ),
    "tests/test_issue52_readiness_provider.py": (
        "test_missing_explicit_workspace_is_unavailable",
        "assert not root.exists()",
        "test_readiness_is_byte_for_byte_read_only",
    ),
    "tests/test_issue52_operations_profile.py": (
        "test_issue52_profile_loading_is_metadata_safe",
        "assert not workspace.exists()",
    ),
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _load_audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(
        _read(root, "docs/audits/portia-v0.2.0-release-audit.json")
    )
    if not isinstance(raw, dict):
        raise ValueError("release audit JSON must be an object")
    return cast(dict[str, Any], raw)


def _domain_status(audit: dict[str, Any], domain_id: str) -> str | None:
    domains = audit.get("audit_domains")
    if not isinstance(domains, list):
        return None
    for raw_domain in domains:
        if not isinstance(raw_domain, dict):
            continue
        domain = cast(dict[str, Any], raw_domain)
        if domain.get("domain_id") == domain_id:
            status = domain.get("status")
            return status if isinstance(status, str) else None
    return None


def _obligation_statuses(audit: dict[str, Any]) -> dict[str, str]:
    raw_items = audit.get("inherited_foundation_obligations")
    if not isinstance(raw_items, list):
        return {}
    result: dict[str, str] = {}
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        item = cast(dict[str, Any], raw_item)
        finding_id = item.get("finding_id")
        status = item.get("status")
        if isinstance(finding_id, str) and isinstance(status, str):
            result[finding_id] = status
    return result


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    source = _read(root, path)
    return [marker for marker in markers if marker not in source]


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, DOMAIN) != "pass":
        errors.append(f"{DOMAIN} must be recorded as pass")

    statuses = _obligation_statuses(audit)
    if not statuses or set(statuses.values()) != {"reconciled"}:
        errors.append(
            "Slice 11 must preserve the fully reconciled inherited-foundation state"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing read-only marker {marker!r}")

    docs_checks = (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 11 — Read-only surfaces",
                "Domain result: **PASS**",
                "No inherited foundation disposition changes in Slice 11.",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 11.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 11 audit result",
                "No `P54-AUD-*` finding was opened for the read-only-surfaces domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 11 — Read-only surfaces",
                "Portia Issue #54 read-only surfaces audit validation passed",
                "No production runtime code is changed by Slice 11.",
            ),
        ),
    )
    for path, markers in docs_checks:
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 11 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item
            for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == DOMAIN
        ]
        if domain_findings:
            errors.append(
                "read-only-surfaces domain is PASS but still has domain findings"
            )

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 11 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 11 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 read-only surfaces audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 read-only surfaces audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
