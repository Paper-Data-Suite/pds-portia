"""Validate the Portia v0.2.0 Issue #54 release-audit foundation."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name

STARTING_COMMIT = "d2cca3b7d8eb59087016d4da60e623960758a729"
STARTING_TREE = "33067ffdd35047d2c6ac575cc7d21969c2a3862b"
TARGET_VERSION = "0.2.0"
EXPECTED_CORE_SPECIFIER = SpecifierSet(">=0.6.3,<0.7")
EXPECTED_CONSOLE_TARGET = "portia.cli:main"
EXPECTED_OPERATIONS_TARGET = "portia.pds_operations:get_module_operations_profile"

CURRENT_CORE = {
    "version": "0.6.4",
    "filename": "pds_core-0.6.4-py3-none-any.whl",
    "sha256": "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b",
    "source_commit": "152d1c65064c4f8fe55249ff2ca3379d7c4d6ccb",
}
HISTORICAL_CORE = {
    "version": "0.6.3",
    "filename": "pds_core-0.6.3-py3-none-any.whl",
    "sha256": "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
}

ALLOWED_CLASSIFICATIONS = {
    "BLOCKER",
    "MAJOR",
    "MINOR",
    "ACCEPTED LIMITATION",
    "DEFERRED / FUTURE",
}
ALLOWED_FINDING_STATUS = {"open", "resolved", "accepted"}
ALLOWED_DOMAIN_STATUS = {"pending", "pass", "blocked", "not_applicable"}
ALLOWED_VERDICTS = {"PENDING", "BLOCKED", "RELEASED — VERIFIED"}

REQUIRED_DOMAIN_IDS = (
    "ethical_neutrality_epistemic_distinctions",
    "teacher_local_authority",
    "sensitive_data_minimization_privacy",
    "record_distinction_identity",
    "architecture_ownership",
    "storage_path_history_compatibility",
    "recovery_error_integrity",
    "teacher_usability_workload",
    "menu_terminology",
    "read_only_surfaces",
    "packaging_public_surface",
    "documentation_reconciliation",
    "release_contract_mechanical",
    "cumulative_repository_qualification",
    "python_platform_qualification",
)

REQUIRED_FOUNDATION_REAUDITS = (
    "PF-AUD-005",
    "PF-AUD-006",
    "PF-AUD-007",
    "PF-AUD-008",
    "PF-AUD-009",
    "PF-AUD-010",
    "PF-AUD-011",
    "PF-AUD-012",
)

REQUIRED_FILES = (
    "RELEASE_NOTES_v0.2.0.md",
    "docs/audits/portia-v0.2.0-release-audit.md",
    "docs/audits/portia-v0.2.0-release-audit.json",
    "docs/audits/portia-v0.2.0-release-findings.md",
    "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
    "scripts/validate_issue54_release_audit.py",
    "tests/test_issue54_release_audit.py",
)

SIBLING_DISTRIBUTIONS = {
    "scoreform",
    "pds-scoreform",
    "quillan",
    "pds-quillan",
    "concord",
    "pds-concord",
    "meridian",
    "pds-meridian",
    "vitrine",
    "pds-vitrine",
    "paper-data-suite",
    "pds-paper-data-suite",
}
SIBLING_IMPORT_ROOTS = {
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
    "paper_data_suite",
}

FINDING_ID_RE = re.compile(r"^P54-AUD-\d{3}$")
VERSION_RE = re.compile(r'__version__:\s*Final\[str\]\s*=\s*"([^"]+)"')


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json_object(path: Path) -> dict[str, Any]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return cast(dict[str, Any], value)


def _load_project(root: Path) -> dict[str, Any]:
    with (root / "pyproject.toml").open("rb") as handle:
        raw: object = tomllib.load(handle)
    if not isinstance(raw, dict):
        raise ValueError("pyproject.toml must parse as an object")
    project = cast(dict[str, Any], raw).get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml is missing [project]")
    return cast(dict[str, Any], project)


def _version_from_source(root: Path) -> str:
    text = (root / "portia" / "_version.py").read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if match is None:
        raise ValueError("could not parse portia.__version__")
    return match.group(1)


def _validate_release_identity(root: Path, errors: list[str]) -> None:
    try:
        project = _load_project(root)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot inspect pyproject.toml: {exc}")
        return

    if project.get("name") != "pds-portia":
        errors.append("distribution name must remain pds-portia")
    try:
        source_version = _version_from_source(root)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    else:
        if source_version != TARGET_VERSION:
            errors.append(f"Portia source version must remain {TARGET_VERSION}")

    if project.get("requires-python") != ">=3.11":
        errors.append("Requires-Python must remain exactly >=3.11")

    raw_dependencies = project.get("dependencies")
    if not isinstance(raw_dependencies, list):
        errors.append("project.dependencies must be a list")
        return

    requirements: list[Requirement] = []
    for item in raw_dependencies:
        if not isinstance(item, str):
            errors.append("project.dependencies entries must be strings")
            continue
        try:
            requirements.append(Requirement(item))
        except ValueError as exc:
            errors.append(f"invalid dependency {item!r}: {exc}")

    core_requirements = [
        requirement
        for requirement in requirements
        if canonicalize_name(requirement.name) == "pds-core"
    ]
    if len(core_requirements) != 1:
        errors.append("Portia must declare exactly one pds-core runtime dependency")
    else:
        core = core_requirements[0]
        if core.specifier != EXPECTED_CORE_SPECIFIER:
            errors.append("Core runtime dependency must remain pds-core>=0.6.3,<0.7")
        if core.url is not None or core.marker is not None or core.extras:
            errors.append("Core runtime dependency must remain ordinary and unconditional")

    sibling_names = {canonicalize_name(name) for name in SIBLING_DISTRIBUTIONS}
    for requirement in requirements:
        if canonicalize_name(requirement.name) in sibling_names:
            errors.append(f"unexpected sibling runtime dependency: {requirement}")

    scripts = project.get("scripts")
    if scripts != {"portia": EXPECTED_CONSOLE_TARGET}:
        errors.append(
            "console script must remain exactly portia = portia.cli:main"
        )

    entry_points = project.get("entry-points")
    if not isinstance(entry_points, dict):
        errors.append("project.entry-points must be present")
        return
    entry_points = cast(dict[str, Any], entry_points)
    operations = entry_points.get("paper_data_suite.module_operations")
    if operations != {"portia": EXPECTED_OPERATIONS_TARGET}:
        errors.append(
            "paper_data_suite.module_operations must expose exactly the Portia provider"
        )
    if "paper_data_suite.publication_producers" in entry_points:
        errors.append("Portia v0.2.0 must not advertise a publication-producer entry point")


def _import_roots(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name.split(".", 1)[0] for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module.split(".", 1)[0],)
    return ()


def _validate_sibling_import_isolation(root: Path, errors: list[str]) -> None:
    offenders: list[str] = []
    for path in sorted((root / "portia").rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"cannot inspect {path.relative_to(root)}: {exc}")
            continue
        for node in ast.walk(tree):
            for import_root in _import_roots(node):
                if import_root in SIBLING_IMPORT_ROOTS:
                    offenders.append(
                        f"{path.relative_to(root).as_posix()}:"
                        f"{getattr(node, 'lineno', '?')}:{import_root}"
                    )
    if offenders:
        errors.append("production imports sibling PDS applications: " + ", ".join(offenders))


def _require_mapping(
    value: object,
    label: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    return cast(dict[str, Any], value)


def _validate_core_record(
    actual: object,
    expected: dict[str, str],
    label: str,
    errors: list[str],
) -> None:
    mapping = _require_mapping(actual, label, errors)
    if mapping is None:
        return
    for key, expected_value in expected.items():
        if mapping.get(key) != expected_value:
            errors.append(f"{label}.{key} must be {expected_value!r}")


def _validate_audit_state(root: Path, errors: list[str]) -> None:
    audit_path = root / "docs" / "audits" / "portia-v0.2.0-release-audit.json"
    try:
        audit = _load_json_object(audit_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"cannot parse release-audit JSON: {exc}")
        return

    exact_fields: dict[str, object] = {
        "audit_record_kind": "pds-portia.v0.2.0-release-audit",
        "audit_record_version": "1",
        "audit_issue": 54,
        "umbrella_issue": 35,
        "target_distribution": "pds-portia",
        "target_version": TARGET_VERSION,
        "starting_portia_commit": STARTING_COMMIT,
        "starting_portia_tree": STARTING_TREE,
        "phase": "phase_1_audit_in_progress",
    }
    for key, expected in exact_fields.items():
        if audit.get(key) != expected:
            errors.append(f"release audit {key} must be {expected!r}")

    verdict = audit.get("final_verdict")
    if verdict not in ALLOWED_VERDICTS:
        errors.append(f"invalid final_verdict: {verdict!r}")

    baseline = _require_mapping(
        audit.get("baseline_qualification"),
        "baseline_qualification",
        errors,
    )
    if baseline is not None:
        if baseline.get("status") != "passed_before_slice_1":
            errors.append("baseline qualification must be captured before Slice 1 edits")
        if baseline.get("qualified_commit") != STARTING_COMMIT:
            errors.append("baseline qualification must bind the exact #53 handoff commit")
        if baseline.get("qualified_tree") != STARTING_TREE:
            errors.append("baseline qualification must bind the exact #53 handoff tree")
        if (
            baseline.get("terminal_message")
            != "Portia Issue #53 repository qualification passed"
        ):
            errors.append("baseline qualification terminal message is not exact")
        for field in ("captured_at_utc", "python_version", "host_platform"):
            value = baseline.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"baseline qualification {field} must be populated")

    core = _require_mapping(audit.get("core_qualification"), "core_qualification", errors)
    if core is not None:
        _validate_core_record(core.get("current"), CURRENT_CORE, "core_qualification.current", errors)
        _validate_core_record(
            core.get("historical"),
            HISTORICAL_CORE,
            "core_qualification.historical",
            errors,
        )

    domains = audit.get("audit_domains")
    seen_domains: list[str] = []
    if not isinstance(domains, list):
        errors.append("audit_domains must be a list")
    else:
        for item in domains:
            if not isinstance(item, dict):
                errors.append("audit_domains entries must be objects")
                continue
            item_map = cast(dict[str, Any], item)
            domain_id = item_map.get("domain_id")
            status = item_map.get("status")
            if not isinstance(domain_id, str):
                errors.append("audit domain_id must be a string")
                continue
            seen_domains.append(domain_id)
            if status not in ALLOWED_DOMAIN_STATUS:
                errors.append(f"{domain_id}: invalid audit-domain status {status!r}")
        if tuple(seen_domains) != REQUIRED_DOMAIN_IDS:
            errors.append("audit_domains must preserve the exact Issue #54 domain order")

    inherited = audit.get("inherited_foundation_obligations")
    inherited_ids: list[str] = []
    if not isinstance(inherited, list):
        errors.append("inherited_foundation_obligations must be a list")
    else:
        for item in inherited:
            if not isinstance(item, dict):
                errors.append("inherited foundation obligations must be objects")
                continue
            item_map = cast(dict[str, Any], item)
            finding_id = item_map.get("finding_id")
            if not isinstance(finding_id, str):
                errors.append("inherited foundation finding_id must be a string")
                continue
            inherited_ids.append(finding_id)
            if item_map.get("status") not in {"pending_reaudit", "reconciled"}:
                errors.append(f"{finding_id}: invalid inherited obligation status")
        if tuple(inherited_ids) != REQUIRED_FOUNDATION_REAUDITS:
            errors.append("foundation re-audit obligations are incomplete or reordered")

    findings = audit.get("findings")
    findings_list: list[dict[str, Any]] = []
    if not isinstance(findings, list):
        errors.append("findings must be a list")
    else:
        for raw in findings:
            if not isinstance(raw, dict):
                errors.append("finding entries must be objects")
                continue
            finding = cast(dict[str, Any], raw)
            findings_list.append(finding)
            for field in (
                "finding_id",
                "audit_domain",
                "classification",
                "summary",
                "exact_evidence",
                "affected_files_or_contracts",
                "expected_behavior",
                "observed_problem",
                "risk_or_consequence",
                "required_disposition",
                "resolution",
                "validation_evidence",
                "follow_up_issue_if_any",
                "status",
            ):
                if field not in finding:
                    errors.append(f"finding missing required field {field!r}")
            finding_id = finding.get("finding_id")
            if not isinstance(finding_id, str) or FINDING_ID_RE.fullmatch(finding_id) is None:
                errors.append(f"invalid finding_id: {finding_id!r}")
            if finding.get("classification") not in ALLOWED_CLASSIFICATIONS:
                errors.append(f"{finding_id}: invalid classification")
            if finding.get("status") not in ALLOWED_FINDING_STATUS:
                errors.append(f"{finding_id}: invalid status")

    finding_ids = [finding.get("finding_id") for finding in findings_list]
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate Issue #54 finding IDs")

    declared_counts = audit.get("finding_counts")
    if not isinstance(declared_counts, dict):
        errors.append("finding_counts must be an object")
    else:
        actual_counts = {classification: 0 for classification in ALLOWED_CLASSIFICATIONS}
        for finding in findings_list:
            classification = finding.get("classification")
            if isinstance(classification, str) and classification in actual_counts:
                actual_counts[classification] += 1
        if declared_counts != actual_counts:
            errors.append(
                f"finding_counts mismatch: declared={declared_counts}, actual={actual_counts}"
            )

    unresolved_actual = sorted(
        str(finding.get("finding_id"))
        for finding in findings_list
        if finding.get("status") == "open"
    )
    unresolved_declared = audit.get("unresolved_finding_ids")
    if not isinstance(unresolved_declared, list):
        errors.append("unresolved_finding_ids must be a list")
    elif sorted(str(value) for value in unresolved_declared) != unresolved_actual:
        errors.append("unresolved_finding_ids must match open findings")

    publication = _require_mapping(
        audit.get("release_publication"),
        "release_publication",
        errors,
    )
    if publication is not None:
        publication_status = publication.get("status")
        if publication_status not in {
            "not_started",
            "candidate_qualified",
            "published",
            "verified",
        }:
            errors.append(f"invalid release publication status: {publication_status!r}")
        if verdict == "RELEASED — VERIFIED" and publication_status != "verified":
            errors.append("RELEASED — VERIFIED requires verified publication state")

    unresolved_high = [
        finding
        for finding in findings_list
        if finding.get("status") == "open"
        and finding.get("classification") in {"BLOCKER", "MAJOR"}
    ]
    if verdict == "RELEASED — VERIFIED" and unresolved_high:
        errors.append("RELEASED — VERIFIED cannot retain open BLOCKER/MAJOR findings")

    if audit.get("synthetic_only_confirmation") is not True:
        errors.append("synthetic_only_confirmation must be true")
    if audit.get("sibling_repository_modification_confirmation") is not True:
        errors.append("sibling_repository_modification_confirmation must be true")


def _validate_documentation_wiring(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing Issue #54 release-audit file: {relative}")

    checks = {
        "docs/README.md": (
            "portia-v0.2.0-release-audit.md",
            "issue-54-v0.2.0-release-audit-validation.md",
        ),
        "docs/audits/README.md": (
            "portia-v0.2.0-release-audit.json",
            "portia-v0.2.0-release-findings.md",
        ),
        "docs/audits/portia-v0.2.0-release-audit.md": (
            "Final verdict: **PENDING**",
            "Portia Issue #53 repository qualification passed",
            "RELEASED — VERIFIED",
        ),
        "docs/audits/portia-v0.2.0-release-findings.md": (
            "BLOCKER",
            "MAJOR",
            "ACCEPTED LIMITATION",
            "DEFERRED / FUTURE",
        ),
    }
    for relative, markers in checks.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative}: missing required marker {marker!r}")


def validate_repo(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    _validate_documentation_wiring(root, errors)
    _validate_release_identity(root, errors)
    _validate_sibling_import_isolation(root, errors)
    _validate_audit_state(root, errors)
    return errors


def main() -> int:
    root = repo_root_from_script()
    try:
        errors = validate_repo(root)
    except Exception as exc:  # noqa: BLE001 - bounded validator terminal
        print(f"Issue #54 release-audit validation failed: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Portia Issue #54 release-audit foundation validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
