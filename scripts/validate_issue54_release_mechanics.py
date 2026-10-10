"""Validate Issue #54 Slice 14 release-contract/mechanical state."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "release_contract_mechanical"
VERSION_RE = re.compile(r'__version__:\s*Final\[str\]\s*=\s*"([^"]+)"')


def _read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _audit(root: Path) -> dict[str, Any]:
    raw: object = json.loads(
        _read(root, "docs/audits/portia-v0.2.0-release-audit.json")
    )
    if not isinstance(raw, dict):
        raise ValueError("release audit must be a JSON object")
    return cast(dict[str, Any], raw)


def _domain_statuses(audit: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    raw_domains = audit.get("audit_domains")
    if not isinstance(raw_domains, list):
        return result
    for raw in raw_domains:
        if not isinstance(raw, dict):
            continue
        domain_id = raw.get("domain_id")
        status = raw.get("status")
        if isinstance(domain_id, str) and isinstance(status, str):
            result[domain_id] = status
    return result


def validate_repo(root: Path = ROOT) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        audit = _audit(root)
        statuses = _domain_statuses(audit)
        if statuses.get(DOMAIN) != "pass":
            errors.append(f"{DOMAIN} must be recorded as pass")
        if statuses.get("cumulative_repository_qualification") != "pending":
            errors.append("Slice 14 must leave cumulative qualification pending")
        if statuses.get("python_platform_qualification") != "pending":
            errors.append("Slice 14 must leave Python/platform qualification pending")

        earlier = (
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
        )
        for domain_id in earlier:
            if statuses.get(domain_id) != "pass":
                errors.append(f"earlier audit domain regressed: {domain_id}")

        if audit.get("unresolved_finding_ids") != []:
            errors.append("Slice 14 requires zero unresolved Issue #54 findings")

        obligations = audit.get("inherited_foundation_obligations")
        if not isinstance(obligations, list) or any(
            not isinstance(item, dict) or item.get("status") != "reconciled"
            for item in obligations
        ):
            errors.append("all inherited foundation obligations must remain reconciled")

        expected_contract = {
            "requires_python": ">=3.11",
            "core_requirement": "pds-core>=0.6.3,<0.7",
            "console_script": "portia = portia.cli:main",
            "module_operations_entry_point": (
                "portia = portia.pds_operations:get_module_operations_profile"
            ),
            "sibling_runtime_dependency": False,
            "publication_producer_capability": False,
        }
        if audit.get("release_contract") != expected_contract:
            errors.append("machine release contract drifted from v0.2.0 boundary")

        publication = audit.get("release_publication")
        if not isinstance(publication, dict):
            errors.append("release publication state is unavailable")
        else:
            if publication.get("status") != "not_started":
                errors.append("Slice 14 must not advance release publication state")
            for field in (
                "release_commit",
                "release_tree",
                "tag",
                "github_release_url",
                "wheel_filename",
                "wheel_sha256",
                "sdist_filename",
                "sdist_sha256",
                "sha256sums_sha256",
            ):
                if publication.get(field) is not None:
                    errors.append(f"Slice 14 must not freeze publication field {field}")
        if audit.get("final_verdict") != "PENDING":
            errors.append("Slice 14 must retain PENDING final verdict")

        with (root / "pyproject.toml").open("rb") as handle:
            data = tomllib.load(handle)
        project = data.get("project")
        build = data.get("build-system")
        if not isinstance(project, dict) or not isinstance(build, dict):
            errors.append("pyproject project/build-system metadata is unavailable")
        else:
            if project.get("name") != "pds-portia":
                errors.append("distribution must remain pds-portia")
            if project.get("requires-python") != ">=3.11":
                errors.append("Requires-Python must remain >=3.11")
            if project.get("dependencies") != ["pds-core>=0.6.3,<0.7"]:
                errors.append("runtime dependency must remain Core-only")
            if project.get("scripts") != {"portia": "portia.cli:main"}:
                errors.append("console entry point drifted")
            if project.get("entry-points") != {
                "paper_data_suite.module_operations": {
                    "portia": "portia.pds_operations:get_module_operations_profile"
                }
            }:
                errors.append("module-operations entry point drifted")
            if build.get("build-backend") != "setuptools.build_meta":
                errors.append("build backend drifted")
            if build.get("requires") != ["setuptools>=77"]:
                errors.append("build requirement drifted")

        version_source = _read(root, "portia/_version.py")
        match = VERSION_RE.search(version_source)
        if match is None or match.group(1) != "0.2.0":
            errors.append("authoritative source version must remain 0.2.0")

        package_checker = _read(root, "scripts/check_issue54_release_package.py")
        for marker in (
            'EXPECTED_WHEEL: Final[str] = "pds_portia-0.2.0-py3-none-any.whl"',
            'EXPECTED_SDIST: Final[str] = "pds_portia-0.2.0.tar.gz"',
            "dist must contain exactly the two Issue #54 candidate artifacts",
            "paper_data_suite.publication_producers",
            "release_contract_mechanical",
            "candidate wheel SHA-256 (NOT FINAL)",
            "Phase 2 must rebuild from exact qualified main",
        ):
            if marker not in package_checker:
                errors.append(
                    f"release package checker missing mechanical marker {marker!r}"
                )

        generic = _read(root, "scripts/check_package.py")
        for marker in (
            "_ISSUE54_REQUIRED_SDIST_FILES",
            '"RELEASE_NOTES_v0.2.0.md"',
            '"docs/audits/portia-v0.2.0-release-audit.json"',
            '"scripts/check_issue54_release_package.py"',
            '"scripts/validate_issue54_release_mechanics.py"',
        ):
            if marker not in generic:
                errors.append(
                    f"generic package checker missing Issue #54 marker {marker!r}"
                )

        notes = _read(root, "RELEASE_NOTES_v0.2.0.md")
        if (
            "Status: **release candidate; publication pending Issue #54 Phase 2 verification**"
            not in notes
        ):
            errors.append("release notes must remain candidate-scoped")

        docs = {
            "docs/audits/portia-v0.2.0-release-audit.md": (
                "## Slice 14 — Release contract and mechanical qualification",
                "Domain result: **PASS**",
                "No `P54-AUD-*` finding was opened in Slice 14.",
                "Final verdict remains **PENDING**",
            ),
            "docs/audits/portia-v0.2.0-release-findings.md": (
                "## Slice 14 audit result",
                "No `P54-AUD-*` finding was opened for the release-contract/mechanical domain.",
            ),
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md": (
                "## Slice 14 — Release contract and mechanical qualification",
                "Portia Issue #54 release/package validation passed",
                "Portia Issue #54 release-contract/mechanical audit validation passed",
                "Candidate hashes are diagnostic only",
            ),
        }
        for relative, markers in docs.items():
            source = _read(root, relative)
            for marker in markers:
                if marker not in source:
                    errors.append(f"{relative}: missing Slice 14 marker {marker!r}")

        mypy_files = set(data.get("tool", {}).get("mypy", {}).get("files", []))
        for required in (
            "scripts/check_issue54_release_package.py",
            "scripts/validate_issue54_release_mechanics.py",
        ):
            if required not in mypy_files:
                errors.append(f"strict mypy scope missing {required}")
    except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"mechanical audit inspection failed: {exc}")
    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 release-contract/mechanical audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 release-contract/mechanical audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
