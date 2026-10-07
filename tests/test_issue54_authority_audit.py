from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_authority_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_authority_audit", path)
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
    for raw in _audit()["audit_domains"]:
        assert isinstance(raw, dict)
        if raw["domain_id"] == domain_id:
            status = raw["status"]
            assert isinstance(status, str)
            return status
    return None


def _profile_keywords() -> tuple[str, ...]:
    source = (ROOT / "portia" / "pds_operations.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    call = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ModuleOperationsProfile"
    )
    return tuple(keyword.arg for keyword in call.keywords if keyword.arg is not None)


def test_issue54_slice3_validator_accepts_authority_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_teacher_local_authority_domain_is_pass_without_release_claim() -> None:
    audit = _audit()
    assert _domain_status("teacher_local_authority") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_external_policy_and_legal_nonclaim_obligations_are_reconciled() -> None:
    statuses = {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }
    assert statuses["PF-AUD-008"] == "reconciled"
    assert statuses["PF-AUD-012"] == "reconciled"
    assert statuses["PF-AUD-009"] == "pending_reaudit"
    assert statuses["PF-AUD-010"] == "pending_reaudit"


def test_issue54_determination_runtime_preserves_authority_separation() -> None:
    source = (ROOT / "portia" / "workflows" / "determinations.py").read_text(
        encoding="utf-8"
    )
    assert "teacher-local Determination requires local-operator decision-maker" in source
    assert "unsupported Determination authority context" in source
    assert "recorded-institutional Determination requires school-staff " in source
    assert "institutional decision-maker; authority provenance remains separate." in source


def test_issue54_actor_relationship_does_not_become_legal_authority() -> None:
    adr = (
        ROOT
        / "docs"
        / "decisions"
        / "0010-define-actor-directory-domain-model-and-lifecycle.md"
    ).read_text(encoding="utf-8")
    assert (
        "A teacher-recorded parent, guardian, counselor, administrator, or support\n"
        "relationship does not independently prove legal or institutional authority."
        in adr
    )
    assert "Roster-student and Actor identity authorities remain distinct." in adr


def test_issue54_response_and_export_do_not_claim_institutional_authority() -> None:
    response = (ROOT / "portia" / "workflows" / "response_common.py").read_text(
        encoding="utf-8"
    )
    export = (ROOT / "portia" / "exports" / "preparation.py").read_text(
        encoding="utf-8"
    )
    assert "recorded-institutional consequence requires Determination context" in response
    assert (
        "Local teacher reference only; this export is not a disclosure or official institutional record."
        in export
    )
    assert (
        "Participant-specific scope does not establish recipient or disclosure authorization."
        in export
    )


def test_issue54_core_suite_surface_remains_bounded_to_readiness_and_attention() -> None:
    assert _profile_keywords() == (
        "module_id",
        "supported_core_operations_contract_versions",
        "readiness_provider",
        "attention_provider",
    )


def test_issue54_slice3_opens_no_authority_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    authority_findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "teacher_local_authority"
    ]
    assert authority_findings == []
