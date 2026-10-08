from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_DOMAIN = "architecture_ownership"

SIBLING_IMPORT_ROOTS = frozenset(
    {
        "scoreform",
        "pds_scoreform",
        "quillan",
        "pds_quillan",
        "concord",
        "pds_concord",
        "meridian",
        "pds_meridian",
        "vitrine",
        "pds_vitrine",
        "sunset",
        "pds_sunset",
    }
)

MARKERS: dict[str, tuple[str, ...]] = {
    "docs/decisions/0002-define-portia-module-boundaries.md": (
        "pds-portia -> pds-core",
        "Core will not depend on Portia.",
        "Sibling modules are not mandatory runtime dependencies.",
        "The originating module remains authoritative for the referenced record.",
        "Foundational Portia workflows must remain usable without sibling modules being installed.",
    ),
    "docs/decisions/0003-adopt-teacher-local-initial-deployment.md": (
        "teacher-local, classroom-focused Paper Data Suite module",
        "The initial release will use the existing local PDS workspace and shared Core class and roster infrastructure.",
        "Exports are derived artifacts, not canonical Portia records.",
        "Portia should not automatically send exports by email, publish them, or copy them into other modules.",
    ),
    "docs/decisions/0004-define-portia-identity-ownership-and-storage.md": (
        "Core remains authoritative for workspace selection, classes, rosters, and roster-local student identity.",
        "Every Event and Support Process has exactly one owning class and one canonical class-scoped work root.",
        "Each relationship has one canonical record; reverse links and histories are derived.",
    ),
    "portia/pds_operations.py": (
        "Installed Portia module-operations profile for Core v1.",
        "Lazily evaluate Portia-owned attention for one neutral Core request.",
        "Lazily evaluate Portia-owned readiness for one neutral Core request.",
        "Return Portia's validated Core v1 operations profile.",
    ),
    "portia/storage/derived.py": (
        "Install and load derived state without treating it as canonical authority.",
    ),
    "README.md": (
        "No `pds-sunset` dependency exists.",
        "Core v0.6 `intervention_record_set` remains a future privacy-minimized",
        "publication projection over Portia-native authority.",
        "Issue #52 exposes Portia through Core module-operations contract v1 with exactly",
        "one installed profile: `paper_data_suite.module_operations / portia`.",
        "Neither provider performs canonical writes",
    ),
    "tests/test_issue53_end_to_end_acceptance.py": (
        'expected_pds = {"pds-core", "pds-portia"}',
        '"portia.pds_operations:get_module_operations_profile"',
        '"provider_zero_write": after_invocation == baseline',
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
    obligations = audit.get("inherited_foundation_obligations")
    if not isinstance(obligations, list):
        return {}
    result: dict[str, str] = {}
    for raw_obligation in obligations:
        if not isinstance(raw_obligation, dict):
            continue
        obligation = cast(dict[str, Any], raw_obligation)
        finding_id = obligation.get("finding_id")
        status = obligation.get("status")
        if isinstance(finding_id, str) and isinstance(status, str):
            result[finding_id] = status
    return result


def _missing_markers(root: Path, path: str, markers: tuple[str, ...]) -> list[str]:
    content = _read(root, path)
    return [marker for marker in markers if marker not in content]


def _import_roots(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            roots.append(node.module.split(".", 1)[0])
    return tuple(roots)


def _sibling_runtime_imports(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted((root / "portia").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        try:
            roots = _import_roots(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError) as exc:
            violations.append(f"{relative}: cannot inspect imports: {exc}")
            continue
        for imported_root in roots:
            if imported_root in SIBLING_IMPORT_ROOTS:
                violations.append(
                    f"{relative}: imports sibling runtime module {imported_root!r}"
                )
    return violations


def _project_contract(root: Path) -> dict[str, Any]:
    with (root / "pyproject.toml").open("rb") as handle:
        raw = tomllib.load(handle)
    project = raw.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml has no [project] table")
    return cast(dict[str, Any], project)


def validate_repo(root: Path = ROOT) -> list[str]:
    errors: list[str] = []

    try:
        audit = _load_audit(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"cannot load release audit JSON: {exc}"]

    if _domain_status(audit, ARCHITECTURE_DOMAIN) != "pass":
        errors.append(f"{ARCHITECTURE_DOMAIN} must be recorded as pass")

    expected_statuses = {
        "PF-AUD-005": "pending_reaudit",
        "PF-AUD-006": "pending_reaudit",
        "PF-AUD-007": "pending_reaudit",
        "PF-AUD-008": "reconciled",
        "PF-AUD-009": "reconciled",
        "PF-AUD-010": "reconciled",
        "PF-AUD-011": "reconciled",
        "PF-AUD-012": "reconciled",
    }
    actual_statuses = _obligation_statuses(audit)
    if actual_statuses != expected_statuses:
        errors.append(
            "foundation obligation status map drifted: "
            f"expected {expected_statuses!r}; found {actual_statuses!r}"
        )

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing architecture marker {marker!r}")

    try:
        project = _project_contract(root)
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        errors.append(f"cannot read project contract: {exc}")
    else:
        if project.get("dependencies") != ["pds-core>=0.6.3,<0.7"]:
            errors.append("runtime dependency surface must remain Core-only")
        if project.get("scripts") != {"portia": "portia.cli:main"}:
            errors.append("console-script surface drifted")
        entry_points = project.get("entry-points")
        if not isinstance(entry_points, dict):
            errors.append("project entry-points table is missing")
        else:
            if entry_points.get("paper_data_suite.module_operations") != {
                "portia": "portia.pds_operations:get_module_operations_profile"
            }:
                errors.append("module-operations entry point drifted")
            if "paper_data_suite.publication_producers" in entry_points:
                errors.append(
                    "future Core intervention publication must remain unclaimed"
                )

    errors.extend(_sibling_runtime_imports(root))

    docs_checks = (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 6 — Architecture and ownership",
                "Domain result: **PASS**",
                "PF-AUD-009, PF-AUD-010, and PF-AUD-011 are reconciled",
                "PF-AUD-007 remains pending",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 6.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 6 audit result",
                "No `P54-AUD-*` finding was opened for the architecture / ownership domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 6 — Architecture and ownership",
                "Portia Issue #54 architecture/ownership audit validation passed",
                "No production runtime code is changed by Slice 6.",
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
            errors.append(f"{path}: missing Slice 6 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        architecture_findings = [
            finding
            for finding in findings
            if isinstance(finding, dict)
            and finding.get("audit_domain") == ARCHITECTURE_DOMAIN
        ]
        if architecture_findings:
            errors.append(
                "architecture domain is recorded PASS but still has domain findings"
            )

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 architecture/ownership audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 architecture/ownership audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
