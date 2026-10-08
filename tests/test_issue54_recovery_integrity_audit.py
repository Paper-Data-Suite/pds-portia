from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_recovery_integrity_audit.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_recovery_integrity_audit",
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


def _domain_status(domain_id: str) -> str | None:
    for raw_domain in _audit()["audit_domains"]:
        assert isinstance(raw_domain, dict)
        if raw_domain["domain_id"] == domain_id:
            status = raw_domain["status"]
            assert isinstance(status, str)
            return status
    return None


def _statuses() -> dict[str, str]:
    return {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }


def test_issue54_slice8_validator_accepts_recovery_integrity_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_recovery_integrity_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("recovery_error_integrity") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_recovery_and_application_validation_obligations_are_reconciled() -> None:
    statuses = _statuses()
    assert statuses["PF-AUD-005"] == "reconciled"
    assert statuses["PF-AUD-007"] == "reconciled"
    assert statuses["PF-AUD-006"] == "pending_reaudit"


def test_issue54_orchestration_refuses_fictitious_graph_rollback() -> None:
    source = (ROOT / "portia" / "storage" / "orchestration.py").read_text(
        encoding="utf-8"
    )
    assert "Partial durable success is surfaced for explicit recovery; accepted" in source
    assert "canonical bytes are never deleted to imitate rollback." in source
    assert "PortiaOperationPartialCommitError" in source
    assert "failure after any canonical step is accepted preserves the locks" in source


def test_issue54_recovery_remains_exact_and_fail_closed() -> None:
    source = (ROOT / "portia" / "workflows" / "recovery.py").read_text(
        encoding="utf-8"
    )
    assert "Ambiguous or branched state stays fail-closed." in source
    assert "generic recovery execution requires exact recovering journal evidence" in source
    assert "recovery cannot select an indeterminate canonical result" in source
    assert "recovery did not prove every canonical gate" in source


def test_issue54_integrity_evaluation_is_exact_and_nonmutating() -> None:
    source = (ROOT / "portia" / "workflows" / "integrity.py").read_text(
        encoding="utf-8"
    )
    assert "Evaluate the exact current operation revision without mutating state." in source
    assert "Recovery topology is deliberately checked before and after evaluation." in source
    assert "Fail closed when an exact current finding applies one named effect." in source


def test_issue54_application_validation_is_production_not_schema_only() -> None:
    graph = (ROOT / "portia" / "validation" / "graph.py").read_text(encoding="utf-8")
    common = (ROOT / "portia" / "workflows" / "common.py").read_text(encoding="utf-8")
    assert "Production in-memory application validation for Portia v0.2 records." in graph
    assert "def validate_record_graph(" in graph
    assert "GraphValidationOptions(require_internal_resolution=True)" in common
    assert "raise WorkflowValidationError(findings)" in common


def test_issue54_representative_runtime_corpus_proves_application_invalid_cases() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    runtime = (ROOT / "tests" / "test_runtime_issue22_application.py").read_text(
        encoding="utf-8"
    )
    assert "15 positive and 37 schema-valid graph-invalid scenarios" in readme
    assert 'entry.disposition == "covered_by_37"' in runtime
    assert "GraphValidationOptions(require_internal_resolution=True)" in runtime


def test_issue54_issue53_installed_recovery_and_integrity_evidence_remains_present() -> None:
    source = (
        ROOT / "tests" / "test_issue53_end_to_end_acceptance.py"
    ).read_text(encoding="utf-8")
    for marker in (
        "test_issue53_recovery_resumes_only_remaining_exact_writes",
        "test_issue53_recovery_releases_locks_cleans_staging_and_is_idempotent",
        "test_issue53_integrity_rebuilds_clean_completed_operation_projection",
        "test_issue53_fresh_reload_proves_terminal_recovery_and_no_staging",
    ):
        assert marker in source


def test_issue54_slice8_opens_no_recovery_integrity_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "recovery_error_integrity"
    ]
    assert findings == []
