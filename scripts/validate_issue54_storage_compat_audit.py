from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
STORAGE_DOMAIN = "storage_path_history_compatibility"

MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0004-define-portia-identity-ownership-and-storage.md": (
        "Each canonical record has exactly one authoritative location.",
        "Roster changes do not silently rewrite historical display snapshots.",
        "Unresolved historical references must be reported rather than silently repaired.",
        "The prior work remains historically intact.",
        "Portia must not silently fabricate missing canonical records from derived views.",
    ),
    "docs/decisions/0008-define-lifecycle-correction-and-migration-contracts.md": (
        "Append-only lifecycle-transition records preserve the accepted history of status changes.",
        "A mismatch is an integrity finding. Portia does not silently choose one side or rewrite history.",
        "Neither state deletes the historical record.",
        "Exact references never silently follow successors.",
        "Representation or contract-version migration is distinct from semantic correction:",
    ),
    "portia/storage/generated_paths.py": (
        "Bounded generated-path primitives for Portia-owned filesystem infrastructure.",
        "Return one fixed-length opaque token for Portia-owned filesystem use.",
        "destination filename is",
        "intentionally not embedded in the temporary leaf.",
        "Return one bounded work technical-storage revision leaf.",
        "Return one bounded Actor technical-storage revision leaf.",
    ),
    "portia/storage/paths.py": (
        "Return the bounded writer path for one work technical storage revision.",
        "Return the pre-Issue-92 work storage-history path for exact compatibility.",
        "Return the bounded writer path for one Actor technical storage revision.",
        "Return the pre-Issue-92 Actor storage-history path for compatibility.",
        "Return the bounded writer root for one exact derived projection scope.",
        "Return the pre-Issue-92 derived root for exact reader compatibility.",
    ),
    "portia/storage/migration_representations.py": (
        "It does not choose a current representation and never migrates during reads.",
        "The version namespace is canonical migration evidence.",
        "Resolve exactly the requested work version, never a version winner.",
        "Resolve exactly the requested child version without implicit migration.",
    ),
    "portia/views/currentness.py": (
        "The view layer does not invent a second lifecycle engine.",
        "representation-currentness rule",
    ),
    "tests/test_generated_paths_issue92.py": (
        "test_generated_path_token_length_does_not_expand_with_identity_text",
        "test_staging_candidate_length_does_not_expand_with_destination",
        "test_storage_revision_leaf_does_not_expand_with_record_identity",
    ),
    "tests/test_derived_paths_issue92.py": (
        "test_legacy_derived_generation_loads_without_migration",
        "test_new_generation_cuts_over_from_legacy_without_rewriting_legacy",
    ),
    "tests/test_storage_migration_representations.py": (
        "test_missing_record_version_never_selects_current_version",
        "test_record_exact_old_version_is_final_superseded_source_after_switch",
    ),
    "tests/test_student_view_work_history.py": (
        "test_history_keeps_current_frontier_and_exact_correction_context",
        "test_exceptional_removal_is_unavailable_not_reconstructed",
        "test_migration_context_does_not_follow_out_of_scope_legacy_source",
    ),
    "tests/test_issue92_qualification.py": (
        'assert smoke.CORE_064_FILENAME == "pds_core-0.6.4-py3-none-any.whl"',
        "assert smoke.TARGET_DEEP_WORKSPACE_LENGTH == 119",
    ),
    "scripts/validate_repository.py": (
        'expected_core_version != "0.6.4"',
        'expected_historical_core_version != "0.6.3"',
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


def _function_names(source: str) -> frozenset[str]:
    tree = ast.parse(source)
    return frozenset(
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    )


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, STORAGE_DOMAIN) != "pass":
        errors.append(f"{STORAGE_DOMAIN} must be recorded as pass")

    statuses = _obligation_statuses(audit)
    if statuses.get("PF-AUD-005") != "pending_reaudit":
        errors.append(
            "PF-AUD-005 must remain pending until the recovery/error/Integrity audit"
        )
    if statuses.get("PF-AUD-007") != "pending_reaudit":
        errors.append(
            "PF-AUD-007 must remain pending until the recovery/error/Integrity audit"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing storage/history marker {marker!r}")

    try:
        paths_source = _read(root, "portia/storage/paths.py")
    except (OSError, UnicodeError) as exc:
        errors.append(f"cannot read storage paths: {exc}")
    else:
        names = _function_names(paths_source)
        required = {
            "work_storage_history_path",
            "legacy_work_storage_history_path",
            "actor_storage_history_path",
            "legacy_actor_storage_history_path",
            "derived_projection_root",
            "legacy_derived_projection_root",
            "derived_generation_root",
            "legacy_derived_generation_root",
            "derived_metadata_path",
            "legacy_derived_metadata_path",
            "derived_data_path",
            "legacy_derived_data_path",
            "derived_current_path",
            "legacy_derived_current_path",
        }
        missing = sorted(required - names)
        if missing:
            errors.append(
                "bounded writer / legacy reader path helpers drifted: "
                f"missing {missing!r}"
            )

    core = audit.get("core_qualification")
    if not isinstance(core, dict):
        errors.append("release audit has no Core qualification state")
    else:
        current = core.get("current")
        historical = core.get("historical")
        if not isinstance(current, dict) or current.get("version") != "0.6.4":
            errors.append("current storage/path authority must remain Core 0.6.4")
        if not isinstance(historical, dict) or historical.get("version") != "0.6.3":
            errors.append("historical compatibility authority must remain Core 0.6.3")

    for path, markers in (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 7 — Storage, path, history, and compatibility",
                "Domain result: **PASS**",
                "PF-AUD-005 and PF-AUD-007 remain pending",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 7.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 7 audit result",
                "No `P54-AUD-*` finding was opened for the storage/path/history/compatibility domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 7 — Storage, path, history, and compatibility",
                "Portia Issue #54 storage/path/history compatibility audit validation passed",
                "No production runtime code is changed by Slice 7.",
            ),
        ),
    ):
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing Slice 7 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item
            for item in findings
            if isinstance(item, dict)
            and item.get("audit_domain") == STORAGE_DOMAIN
        ]
        if domain_findings:
            errors.append(
                "storage/path/history domain is PASS but still has domain findings"
            )

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print(
            "Portia Issue #54 storage/path/history compatibility audit "
            "validation failed:"
        )
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Portia Issue #54 storage/path/history compatibility audit "
        "validation passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
