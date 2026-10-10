from __future__ import annotations

import importlib.util
import json
import tomllib
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_architecture_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_architecture_audit", path)
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


def _domain_status(domain_id: str) -> str | None:
    for raw_domain in _audit()["audit_domains"]:
        assert isinstance(raw_domain, dict)
        if raw_domain["domain_id"] == domain_id:
            status = raw_domain["status"]
            assert isinstance(status, str)
            return status
    return None


def _obligation_statuses() -> dict[str, str]:
    return {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }


def test_issue54_slice6_validator_accepts_architecture_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_architecture_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("architecture_ownership") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_architecture_owned_foundation_obligations_remain_reconciled() -> None:
    statuses = _obligation_statuses()
    assert statuses["PF-AUD-009"] == "reconciled"
    assert statuses["PF-AUD-010"] == "reconciled"
    assert statuses["PF-AUD-011"] == "reconciled"


def test_issue54_runtime_dependency_surface_is_core_only() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["dependencies"] == ["pds-core>=0.6.3,<0.7"]


def test_issue54_runtime_has_no_sibling_module_imports() -> None:
    validator = _load_validator()
    assert validator._sibling_runtime_imports(ROOT) == []


def test_issue54_core_operations_profile_is_the_only_suite_entry_point() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    entry_points = project["entry-points"]
    assert entry_points == {
        "paper_data_suite.module_operations": {
            "portia": "portia.pds_operations:get_module_operations_profile"
        }
    }


def test_issue54_future_publication_producer_remains_unclaimed() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert "paper_data_suite.publication_producers" not in project["entry-points"]


def test_issue54_derived_store_remains_explicitly_nonauthoritative() -> None:
    source = (ROOT / "portia" / "storage" / "derived.py").read_text(encoding="utf-8")
    assert "Install and load derived state without treating it as canonical authority." in source


def test_issue54_executable_runtime_evidence_survives_from_issue53() -> None:
    source = (
        ROOT / "tests" / "test_issue53_end_to_end_acceptance.py"
    ).read_text(encoding="utf-8")
    assert 'expected_pds = {"pds-core", "pds-portia"}' in source
    assert '"portia.pds_operations:get_module_operations_profile"' in source
    assert '"provider_zero_write": after_invocation == baseline' in source


def test_issue54_slice6_opens_no_architecture_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    architecture_findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "architecture_ownership"
    ]
    assert architecture_findings == []
