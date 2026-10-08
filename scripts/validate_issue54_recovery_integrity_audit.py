from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "recovery_error_integrity"

MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md": (
        "One-file atomic replacement does not imply graph-wide atomicity.",
        "A file may be durable even if final verification or journal publication fails.",
        "Accepted canonical records are not deleted to simulate rollback.",
        "Recovery against unchanged state is idempotent.",
        "Recovery does not invent missing history or choose authority from timestamps or greatest revisions.",
        "Repair may bypass only a named ordinary gate required for the approved repair.",
    ),
    "portia/storage/orchestration.py": (
        "Partial durable success is surfaced for explicit recovery; accepted",
        "canonical bytes are never deleted to imitate rollback.",
        "Publish the bounded canonical-gate write set without fictitious rollback.",
        "PortiaOperationPartialCommitError",
    ),
    "portia/storage/recovery.py": (
        "Non-mutating recovery classification for one exact operation series.",
        "Conservative recovery facade; inspection is separate from explicit repair.",
        "quarantine_or_manual_review",
        "PortiaAmbiguousRecoveryError",
    ),
    "portia/workflows/recovery.py": (
        "Bounded workflow recovery over durable Operation Journal evidence.",
        "Inspect one operation without mutating durable recovery state.",
        "Ambiguous or branched state stays fail-closed.",
        "generic recovery execution requires exact recovering journal evidence",
        "recovery cannot select an indeterminate canonical result",
        "recovery did not prove every canonical gate",
        "def resume_incomplete(",
    ),
    "portia/workflows/integrity.py": (
        "Evaluate the exact current operation revision without mutating state.",
        "Recovery topology is deliberately checked before and after evaluation.",
        "Persist review evidence for one exact current fresh finding evaluation.",
        "Fail closed when an exact current finding applies one named effect.",
        "Shared workflow guard combining Quarantine and current Integrity Findings.",
        "def require_operation_completion(",
    ),
    "portia/validation/graph.py": (
        "Production in-memory application validation for Portia v0.2 records.",
        "class GraphValidationOptions:",
        "require_internal_resolution: bool = False",
        "def validate_record_graph(",
    ),
    "portia/workflows/common.py": (
        "validate_record_graph(",
        "GraphValidationOptions(require_internal_resolution=True)",
        "raise WorkflowValidationError(findings)",
    ),
    "tests/test_storage_orchestration.py": (
        "test_failure_after_first_publish_preserves_lock_and_partial_success",
        "test_failure_before_first_publish_releases_lock_without_canonical_effect",
        "test_candidate_fingerprint_must_match_journaled_intent",
    ),
    "tests/test_issue53_end_to_end_acceptance.py": (
        "test_issue53_recovery_resumes_only_remaining_exact_writes",
        "test_issue53_recovery_releases_locks_cleans_staging_and_is_idempotent",
        "test_issue53_integrity_rebuilds_clean_completed_operation_projection",
        "test_issue53_fresh_reload_proves_terminal_recovery_and_no_staging",
    ),
    "tests/test_application_validation.py": (
        "test_duplicate_exact_identity_is_an_application_finding",
        "test_record_chronology_is_application_validated",
        "test_planned_schedule_chronology_and_duration_are_application_validated",
    ),
    "tests/test_runtime_issue22_application.py": (
        'entry.disposition == "covered_by_37"',
        "GraphValidationOptions(require_internal_resolution=True)",
    ),
    "README.md": (
        "15 positive and 37 schema-valid graph-invalid scenarios",
        "schema validity alone does not establish correct",
        "in-memory application validation;",
    ),
}


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _load_audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(_read(root, "docs/audits/portia-v0.2.0-release-audit.json"))
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

    expected_statuses = {
        "PF-AUD-005": "reconciled",
        "PF-AUD-006": "pending_reaudit",
        "PF-AUD-007": "reconciled",
        "PF-AUD-008": "reconciled",
        "PF-AUD-009": "reconciled",
        "PF-AUD-010": "reconciled",
        "PF-AUD-011": "reconciled",
        "PF-AUD-012": "reconciled",
    }
    actual_statuses = _obligation_statuses(audit)
    if actual_statuses != expected_statuses:
        errors.append(
            "foundation obligation status map drifted after Slice 8: "
            f"expected={expected_statuses!r}, actual={actual_statuses!r}"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing recovery/integrity marker {marker!r}")

    for path, markers in (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 8 — Recovery, error handling, and Integrity",
                "Domain result: **PASS**",
                "PF-AUD-005 is reconciled by this slice.",
                "PF-AUD-007 is reconciled by this slice.",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 8.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 8 audit result",
                "No `P54-AUD-*` finding was opened for the recovery/error/Integrity domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 8 — Recovery, error handling, and Integrity",
                "Portia Issue #54 recovery/error/Integrity audit validation passed",
                "No production runtime code is changed by Slice 8.",
            ),
        ),
    ):
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 8 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == DOMAIN
        ]
        if domain_findings:
            errors.append("recovery/error/Integrity domain is PASS but still has domain findings")

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 8 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 8 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 recovery/error/Integrity audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 recovery/error/Integrity audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
