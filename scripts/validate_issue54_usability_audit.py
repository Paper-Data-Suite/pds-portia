from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "teacher_usability_workload"

MARKERS: dict[str, tuple[str, ...]] = {
    "docs/task-oriented-teacher-menu.md": (
        "## Eight teacher tasks",
        "**Advanced Portia tools** remains the bounded expert escape hatch for exact",
        "Routine screens do not dump raw",
        "Every consequential teacher write has an action-specific preview and explicit",
        "Advanced mode does not provide raw filesystem mutation, arbitrary JSON editing,",
        "## zero-write navigation",
    ),
    "portia/menu/main.py": (
        "Task-oriented teacher-menu entry point for Portia.",
        "PRIMARY_TASKS: tuple[MenuTask, ...]",
        '"Advanced Portia tools"',
        "Viewing or navigating the menu does not create canonical Portia records.",
    ),
    "portia/menu/navigation.py": (
        "Portia teacher-menu navigation built on Core B/M/Q semantics.",
        "Parse H plus Core-owned B/M/Q navigation semantics.",
    ),
    "portia/menu/prompts.py": (
        "Controlled teacher-facing prompts for Portia menu workflows.",
        "Selection is by exact listed position; names are display aids only.",
        "Require an action-specific uppercase confirmation before a write.",
        "No canonical Portia record is written until confirmation succeeds.",
    ),
    "portia/menu/selectors.py": (
        "Return exact roster choices without using names as identity.",
        "Return evidence-write-eligible event@2 choices for one exact Core class.",
    ),
    "portia/menu/advanced.py": (
        "Bounded expert inspection and exact administration routing for Portia.",
        "Raw record JSON and filesystem paths are intentionally not displayed.",
        "These screens are read-only inspection.",
        "No generic JSON editor, forced current pointer, or cross-work move is provided.",
        "raw filesystem mutation, arbitrary JSON editing",
    ),
    "portia/menu/teacher_reference_export.py": (
        "Portia does not summarize, rewrite, sanitize, or automatically ",
        "1. Include exact source content",
        "2. Omit this content",
        "Preparation and preview are read-only. No export operation begins ",
        "review the exact outgoing HTML and type EXPORT exactly.",
    ),
    "scripts/validate_teacher_menu.py": (
        "menu session context became durable state",
        "menu application layer contains direct canonical mutation call",
        "Issue #50 must not add durable teacher-menu/session schemas",
    ),
    "tests/test_teacher_menu_advanced.py": (
        "test_empty_technical_inspection_is_read_only",
        "test_advanced_help_rejects_generic_mutation_language",
    ),
    "tests/test_teacher_menu_teacher_reference_export.py": (
        "test_main_menu_keeps_eight_routine_tasks_and_no_export_root",
        "test_cancel_at_exact_preview_is_zero_write",
        "test_contextual_help_explains_export_boundary",
    ),
    "tests/test_teacher_menu_correction.py": (
        "test_correct_retract_menu_entry_is_zero_read_until_work_selection",
        "test_main_menu_routes_to_correct_retract",
    ),
    "tests/test_teacher_menu_timeline.py": (
        "test_interactive_current_timeline_view_is_zero_write",
        "test_main_menu_routes_to_timeline_surface_without_workspace_read",
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
    expected_ids = {
        "PF-AUD-005",
        "PF-AUD-006",
        "PF-AUD-007",
        "PF-AUD-008",
        "PF-AUD-009",
        "PF-AUD-010",
        "PF-AUD-011",
        "PF-AUD-012",
    }
    if set(statuses) != expected_ids:
        errors.append(
            "foundation obligation identity set drifted: "
            f"expected={sorted(expected_ids)!r}, actual={sorted(statuses)!r}"
        )
    for finding_id in sorted(expected_ids):
        if statuses.get(finding_id) != "reconciled":
            errors.append(
                "all inherited foundation obligations must be reconciled after Slice 9: "
                f"{finding_id}={statuses.get(finding_id)!r}"
            )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing teacher-usability marker {marker!r}")

    docs_checks = (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 9 — Teacher usability and workload",
                "Domain result: **PASS**",
                "PF-AUD-006 is reconciled by this slice.",
                "All inherited foundation obligations are now reconciled.",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 9.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 9 audit result",
                "No `P54-AUD-*` finding was opened for the teacher-usability/workload domain.",
                "PF-AUD-006 is **Reconciled**",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 9 — Teacher usability and workload",
                "Portia Issue #54 teacher usability/workload audit validation passed",
                "No production runtime code is changed by Slice 9.",
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
            errors.append(f"{path}: missing Slice 9 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item
            for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == DOMAIN
        ]
        if domain_findings:
            errors.append(
                "teacher-usability/workload domain is PASS but still has domain findings"
            )

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 9 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 9 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 teacher usability/workload audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 teacher usability/workload audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
