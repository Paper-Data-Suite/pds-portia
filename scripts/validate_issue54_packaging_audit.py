from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "packaging_public_surface"

MARKERS: dict[str, tuple[str, ...]] = {
    "pyproject.toml": (
        'name = "pds-portia"',
        'requires-python = ">=3.11"',
        '"pds-core>=0.6.3,<0.7"',
        'portia = "portia.cli:main"',
        '[project.entry-points."paper_data_suite.module_operations"]',
        'portia = "portia.pds_operations:get_module_operations_profile"',
        'portia = ["py.typed", "runtime-coverage.json", "_runtime_contract_bundle.json"]',
    ),
    "MANIFEST.in": (
        "recursive-include docs *.md *.json",
        "recursive-include schemas *.json",
        "recursive-include scripts *.py *.ps1 *.sh",
        "recursive-include tests *.py *.json *.md *.txt *.csv *.yaml *.yml",
        "recursive-include portia *.py *.json py.typed",
        "global-exclude __pycache__ *.py[cod]",
    ),
    "setup.py": (
        "Setuptools build hooks for the Portia runtime contract bundle.",
        'ROOT / "portia" / "_bundle_builder.py"',
        'return Path(self.build_lib) / "portia" / "_runtime_contract_bundle.json"',
        "writer(ROOT, self._bundle_output())",
    ),
    "portia/__init__.py": (
        "Portia teacher-local behavior-support package.",
        '__all__ = ["__version__"]',
    ),
    "portia/_version.py": (
        '__version__: Final[str] = "0.2.0"',
    ),
    "portia/_bundle_builder.py": (
        "Compile the modelled v0.2 schema closure into one deterministic bundle.",
        '"bundle_contract": "pds-portia.runtime-contract-bundle"',
        '"schemas": {key: schemas[key] for key in sorted(schemas)}',
    ),
    "portia/models/schema_runtime.py": (
        "The production wheel uses only the standard library.",
        'package_root = resources.files("portia")',
        'resource = package_root.joinpath("_runtime_contract_bundle.json")',
        "Portia runtime contract bundle is unavailable and no source schemas were found.",
    ),
    "scripts/check_package.py": (
        'EXPECTED_VERSION = "0.2.0"',
        '"pds-core<0.7,>=0.6.3"',
        "unexpected sibling runtime dependency",
        "jsonschema must remain a development/test dependency, not runtime",
        'if name.startswith(("docs/", "schemas/", "scripts/", "tests/", ".github/")):',
        "repository schema tree leaked into runtime wheel",
        "missing portia console entry point",
        "missing Portia module-operations entry point",
        "publication producer entry point is premature",
        "compiled runtime contract bundle is missing",
    ),
    "scripts/check_issue53_package.py": (
        '_EXPECTED_CORE_REQUIREMENT = "pds-core<0.7,>=0.6.3"',
        '_EXPECTED_CONSOLE_TARGET = "portia.cli:main"',
        '_EXPECTED_OPERATIONS_TARGET = "portia.pds_operations:get_module_operations_profile"',
        '"docs/"',
        '"scripts/"',
        '"tests/"',
        '"schemas/"',
        "unexpected sibling runtime dependency",
        "unexpected module-operations entry points",
        '"paper_data_suite.publication_producers"',
    ),
    "scripts/smoke_test_issue53_end_to_end_wheel.py": (
        'EXPECTED_CORE_VERSION: Final[str] = "0.6.4"',
        'EXPECTED_PORTIA_VERSION: Final[str] = "0.2.0"',
        'expected_pds = {"pds-core", "pds-portia"}',
        "Issue #53 isolated runtime contains unexpected PDS distributions",
        "import resolved outside the temporary venv",
        "import resolved into the source checkout",
        'env["PIP_NO_INDEX"] = "1"',
    ),
    "tests/test_package_baseline.py": (
        'assert project["dependencies"] == ["pds-core>=0.6.3,<0.7"]',
        'assert data["project"]["scripts"] == {"portia": "portia.cli:main"}',
        '"paper_data_suite.module_operations": {',
        'assert (ROOT / "portia" / "py.typed").is_file()',
    ),
    "tests/test_issue53_qualification.py": (
        "test_issue53_package_checker_covers_required_runtime_capabilities",
        "test_issue53_package_checker_rejects_sibling_runtime_dependency",
        "test_issue53_package_checker_requires_exact_entry_points",
        "test_issue53_package_checker_forbids_source_fixture_runtime_packaging",
        "test_generic_package_checker_carries_issue53_closeout_boundary",
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

    obligations = audit.get("inherited_foundation_obligations")
    if not isinstance(obligations, list) or not obligations:
        errors.append("inherited foundation obligations are unavailable")
    else:
        for raw in obligations:
            if not isinstance(raw, dict) or raw.get("status") != "reconciled":
                errors.append(
                    "Slice 12 must preserve the fully reconciled foundation state"
                )
                break

    release_contract = audit.get("release_contract")
    expected_release_contract = {
        "requires_python": ">=3.11",
        "core_requirement": "pds-core>=0.6.3,<0.7",
        "console_script": "portia = portia.cli:main",
        "module_operations_entry_point": (
            "portia = portia.pds_operations:get_module_operations_profile"
        ),
        "sibling_runtime_dependency": False,
        "publication_producer_capability": False,
    }
    if release_contract != expected_release_contract:
        errors.append(
            "release contract drifted from the audited packaging/public surface: "
            f"{release_contract!r}"
        )

    try:
        with (root / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"cannot load pyproject package metadata: {exc}")
    else:
        if project.get("dependencies") != ["pds-core>=0.6.3,<0.7"]:
            errors.append("runtime dependencies must remain Core-only")
        if project.get("scripts") != {"portia": "portia.cli:main"}:
            errors.append("console-script surface drifted")
        if project.get("entry-points") != {
            "paper_data_suite.module_operations": {
                "portia": "portia.pds_operations:get_module_operations_profile"
            }
        }:
            errors.append("plugin entry-point surface drifted")

    for path, markers in MARKERS.items():
        try:
            missing = _missing_markers(root, path, markers)
        except (OSError, UnicodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        for marker in missing:
            errors.append(f"{path}: missing packaging/public-surface marker {marker!r}")

    docs_checks = (
        (
            "docs/audits/portia-v0.2.0-release-audit.md",
            (
                "## Slice 12 — Packaging and public surface",
                "Domain result: **PASS**",
                "No inherited foundation disposition changes in Slice 12.",
                "No `P54-AUD-*` defect was identified in this domain.",
                "No production runtime code changed in Slice 12.",
            ),
        ),
        (
            "docs/audits/portia-v0.2.0-release-findings.md",
            (
                "## Slice 12 audit result",
                "No `P54-AUD-*` finding was opened for the packaging/public-surface domain.",
            ),
        ),
        (
            "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
            (
                "## Slice 12 — Packaging and public surface",
                "Portia Issue #54 packaging/public-surface audit validation passed",
                "No production runtime code is changed by Slice 12.",
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
            errors.append(f"{path}: missing Slice 12 audit marker {marker!r}")

    findings = audit.get("findings")
    if isinstance(findings, list):
        domain_findings = [
            item
            for item in findings
            if isinstance(item, dict) and item.get("audit_domain") == DOMAIN
        ]
        if domain_findings:
            errors.append(
                "packaging/public-surface domain is PASS but still has domain findings"
            )

    if audit.get("final_verdict") != "PENDING":
        errors.append("Slice 12 must not advance the final release verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        errors.append("Slice 12 must not advance release publication state")

    return errors


def main() -> int:
    errors = validate_repo(ROOT)
    if errors:
        print("Portia Issue #54 packaging/public-surface audit validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Portia Issue #54 packaging/public-surface audit validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
