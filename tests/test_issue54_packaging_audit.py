from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any, cast

import portia

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_packaging_audit.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_packaging_audit",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _audit() -> dict[str, Any]:
    raw: object = json.loads(
        (ROOT / "docs" / "audits" / "portia-v0.2.0-release-audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def _project() -> dict[str, Any]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        raw = tomllib.load(handle)["project"]
    assert isinstance(raw, dict)
    return cast(dict[str, Any], raw)


def _domain_status(domain_id: str) -> str | None:
    for raw_domain in _audit()["audit_domains"]:
        assert isinstance(raw_domain, dict)
        if raw_domain["domain_id"] == domain_id:
            status = raw_domain["status"]
            assert isinstance(status, str)
            return status
    return None


def test_issue54_slice12_validator_accepts_packaging_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_packaging_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("packaging_public_surface") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_runtime_dependency_and_entry_point_surface_is_exact() -> None:
    project = _project()
    assert project["dependencies"] == ["pds-core>=0.6.3,<0.7"]
    assert project["scripts"] == {"portia": "portia.cli:main"}
    assert project["entry-points"] == {
        "paper_data_suite.module_operations": {
            "portia": "portia.pds_operations:get_module_operations_profile"
        }
    }


def test_issue54_root_package_public_surface_is_minimal() -> None:
    assert portia.__all__ == ["__version__"]
    assert portia.__version__ == "0.2.0"


def test_issue54_wheel_boundary_excludes_repository_content_and_raw_schema_tree() -> None:
    source = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    assert 'if name.startswith(("docs/", "schemas/", "scripts/", "tests/", ".github/")):' in source
    assert "repository schema tree leaked into runtime wheel" in source
    assert "compiled runtime contract bundle is missing" in source


def test_issue54_sdist_retains_auditable_repository_material() -> None:
    manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
    for marker in (
        "recursive-include docs *.md *.json",
        "recursive-include schemas *.json",
        "recursive-include scripts *.py *.ps1 *.sh",
        "recursive-include tests *.py *.json *.md *.txt *.csv *.yaml *.yml",
    ):
        assert marker in manifest


def test_issue54_runtime_schema_delivery_is_compiled_bundle_not_repository_tree() -> None:
    setup_source = (ROOT / "setup.py").read_text(encoding="utf-8")
    runtime_source = (
        ROOT / "portia" / "models" / "schema_runtime.py"
    ).read_text(encoding="utf-8")
    assert '_runtime_contract_bundle.json' in setup_source
    assert 'resources.files("portia")' in runtime_source
    assert 'joinpath("_runtime_contract_bundle.json")' in runtime_source


def test_issue54_package_checkers_reject_unintended_plugin_and_sibling_surfaces() -> None:
    generic = (ROOT / "scripts" / "check_package.py").read_text(encoding="utf-8")
    dedicated = (
        ROOT / "scripts" / "check_issue53_package.py"
    ).read_text(encoding="utf-8")
    assert "unexpected sibling runtime dependency" in generic
    assert "unexpected sibling runtime dependency" in dedicated
    assert "paper_data_suite.publication_producers" in generic
    assert "paper_data_suite.publication_producers" in dedicated
    assert "paper_data_suite.modules" in generic
    assert "paper_data_suite.modules" in dedicated


def test_issue54_isolated_installed_acceptance_requires_only_core_and_portia() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert 'expected_pds = {"pds-core", "pds-portia"}' in source
    assert "import resolved outside the temporary venv" in source
    assert "import resolved into the source checkout" in source
    assert 'env["PIP_NO_INDEX"] = "1"' in source


def test_issue54_slice12_opens_no_packaging_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "packaging_public_surface"
    ]
    assert findings == []
