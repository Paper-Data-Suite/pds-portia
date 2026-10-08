from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_read_only_audit.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_read_only_audit",
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


def test_issue54_slice11_validator_accepts_read_only_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_read_only_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("read_only_surfaces") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_foundation_reconciliation_state_is_unchanged() -> None:
    statuses = {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }
    assert set(statuses.values()) == {"reconciled"}


def test_issue54_installed_probe_snapshots_each_required_surface() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    probe = source.split('_READ_ONLY_SURFACES_PROBE = r"""', 1)[1].split(
        '"""\n\n_DEEP_PATH_INTEGRATION_PROBE',
        1,
    )[0]
    for marker in (
        '"student timeline/view query"',
        '"attention query"',
        '"Core readiness/attention provider invocation"',
        '"teacher-reference export history verification"',
        '"exact historical predecessor loads"',
        'raise RuntimeError(f"{label} mutated workspace bytes")',
        "whole_phase_before = snapshot(workspace)",
        "whole_phase_after = snapshot(workspace)",
    ):
        assert marker in probe


def test_issue54_installed_probe_uses_directory_and_byte_hash_snapshot() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    probe = source.split('_READ_ONLY_SURFACES_PROBE = r"""', 1)[1].split(
        '"""\n\n_DEEP_PATH_INTEGRATION_PROBE',
        1,
    )[0]
    assert "if path.is_dir()" in probe
    assert "hashlib.sha256(path.read_bytes()).hexdigest()" in probe
    assert '"whole_read_only_phase_zero_write"' in probe


def test_issue54_read_only_probe_uses_production_services_not_fixtures() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    probe = source.split('_READ_ONLY_SURFACES_PROBE = r"""', 1)[1].split(
        '"""\n\n_DEEP_PATH_INTEGRATION_PROBE',
        1,
    )[0]
    for marker in (
        "StudentTimelineService(workspace).generate(student_query)",
        "AttentionQueryService(workspace).query(attention_query)",
        'diagnose_core_providers(provider_kind="module_operations")',
        "invoke_module_operations(profile, request)",
        "TeacherReferenceExportHistoryService(workspace).list_for_work(",
        "accounts.load_exact(",
        "supports.load_exact(",
    ):
        assert marker in probe


def test_issue54_menu_and_provider_zero_write_regressions_remain_present() -> None:
    required = {
        "tests/test_teacher_menu_timeline.py": (
            "test_current_student_view_delegates_to_production_service_and_is_zero_write",
            "test_history_read_is_explicit_and_stays_zero_write",
            "test_interactive_current_timeline_view_is_zero_write",
        ),
        "tests/test_teacher_menu_attention.py": (
            "test_empty_workspace_attention_is_evaluated_and_zero_write",
        ),
        "tests/test_teacher_menu_advanced.py": (
            "test_empty_technical_inspection_is_read_only",
        ),
        "tests/test_teacher_menu_teacher_reference_export.py": (
            "test_cancel_at_exact_preview_is_zero_write",
            "test_history_surface_is_read_only_and_does_not_assign_current_authority",
        ),
        "tests/test_issue52_readiness_provider.py": (
            "test_readiness_is_byte_for_byte_read_only",
        ),
    }
    for relative, markers in required.items():
        source = (ROOT / relative).read_text(encoding="utf-8")
        for marker in markers:
            assert marker in source


def test_issue54_metadata_discovery_does_not_create_workspace() -> None:
    source = (ROOT / "tests" / "test_issue52_operations_profile.py").read_text(
        encoding="utf-8"
    )
    assert "test_issue52_profile_loading_is_metadata_safe" in source
    assert "assert not workspace.exists()" in source


def test_issue54_slice11_opens_no_read_only_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "read_only_surfaces"
    ]
    assert findings == []
