from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

from portia.menu.main import ADVANCED_TASK, PRIMARY_TASKS, render_main_menu

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_usability_audit.py"
    spec = importlib.util.spec_from_file_location("issue54_usability_audit", path)
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


def test_issue54_slice9_validator_accepts_teacher_usability_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_teacher_usability_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("teacher_usability_workload") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_all_foundation_obligations_are_reconciled_after_slice9() -> None:
    statuses = _statuses()
    assert set(statuses) == {
        "PF-AUD-005",
        "PF-AUD-006",
        "PF-AUD-007",
        "PF-AUD-008",
        "PF-AUD-009",
        "PF-AUD-010",
        "PF-AUD-011",
        "PF-AUD-012",
    }
    assert set(statuses.values()) == {"reconciled"}


def test_issue54_routine_menu_stays_task_oriented_and_advanced_is_separate() -> None:
    assert len(PRIMARY_TASKS) == 8
    assert ADVANCED_TASK not in PRIMARY_TASKS
    rendered = render_main_menu()
    for label in (
        "Record Event",
        "Add Information",
        "Record Response / Communication",
        "Manage Support",
        "Complete Follow-Up",
        "View Timeline",
        "Correct / Retract",
        "Attention Needed",
    ):
        assert label in rendered
    assert "Advanced Portia tools" in rendered


def test_issue54_advanced_tools_do_not_offer_generic_record_mutation() -> None:
    source = (ROOT / "portia" / "menu" / "advanced.py").read_text(encoding="utf-8")
    assert "Raw record JSON and filesystem paths are intentionally not displayed." in source
    assert "These screens are read-only inspection." in source
    assert "No generic JSON editor, forced current pointer, or cross-work move is provided." in source
    assert "raw filesystem mutation, arbitrary JSON editing" in source


def test_issue54_manual_export_review_is_bounded_to_include_or_omit() -> None:
    source = (
        ROOT / "portia" / "menu" / "teacher_reference_export.py"
    ).read_text(encoding="utf-8")
    assert "1. Include exact source content" in source
    assert "2. Omit this content" in source
    assert "does not summarize, rewrite, sanitize, or automatically" in source
    assert "Preparation and preview are read-only." in source
    assert "type EXPORT exactly" in source


def test_issue54_menu_write_confirmation_remains_explicit_and_cancellable() -> None:
    source = (ROOT / "portia" / "menu" / "prompts.py").read_text(encoding="utf-8")
    assert "Require an action-specific uppercase confirmation before a write." in source
    assert "press Enter to cancel" in source
    assert "No canonical Portia record is written until confirmation succeeds." in source


def test_issue54_existing_zero_write_and_read_only_regressions_remain_present() -> None:
    advanced = (ROOT / "tests" / "test_teacher_menu_advanced.py").read_text(
        encoding="utf-8"
    )
    export = (
        ROOT / "tests" / "test_teacher_menu_teacher_reference_export.py"
    ).read_text(encoding="utf-8")
    timeline = (ROOT / "tests" / "test_teacher_menu_timeline.py").read_text(
        encoding="utf-8"
    )
    assert "test_empty_technical_inspection_is_read_only" in advanced
    assert "test_cancel_at_exact_preview_is_zero_write" in export
    assert "test_interactive_current_timeline_view_is_zero_write" in timeline


def test_issue54_slice9_opens_no_usability_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "teacher_usability_workload"
    ]
    assert findings == []
