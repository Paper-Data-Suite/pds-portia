from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, cast

from portia.menu.main import PRIMARY_TASKS, render_main_menu
from portia.menu.navigation import navigation_labels_with_help

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue54_menu_terminology_audit.py"
    spec = importlib.util.spec_from_file_location(
        "issue54_menu_terminology_audit",
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


def test_issue54_slice10_validator_accepts_menu_terminology_audit() -> None:
    validator = _load_validator()
    assert validator.validate_repo(ROOT) == []


def test_issue54_menu_terminology_domain_pass_does_not_claim_release() -> None:
    audit = _audit()
    assert _domain_status("menu_terminology") == "pass"
    assert audit["final_verdict"] == "PENDING"
    assert audit["release_publication"]["status"] == "not_started"


def test_issue54_foundation_reconciliation_state_is_unchanged() -> None:
    statuses = {
        entry["finding_id"]: entry["status"]
        for entry in _audit()["inherited_foundation_obligations"]
    }
    assert set(statuses.values()) == {"reconciled"}


def test_issue54_primary_task_labels_remain_teacher_facing_and_distinct() -> None:
    labels = tuple(task.label for task in PRIMARY_TASKS)
    assert labels == (
        "Record Event",
        "Add Information",
        "Record Response / Communication",
        "Manage Support",
        "Complete Follow-Up",
        "View Timeline",
        "Correct / Retract",
        "Attention Needed",
    )
    rendered = render_main_menu()
    for label in labels:
        assert label in rendered


def test_issue54_navigation_labels_remain_consistent() -> None:
    assert navigation_labels_with_help() == (
        "H. Help",
        "B. Back",
        "M. Main Menu",
        "Q. Quit",
    )


def test_issue54_judgment_terms_remain_explicitly_distinct() -> None:
    information = (ROOT / "portia" / "menu" / "information.py").read_text(
        encoding="utf-8"
    )
    judgment = (ROOT / "portia" / "menu" / "judgment.py").read_text(
        encoding="utf-8"
    )
    assert 'print("3. Review recorded Accounts / Observations")' in information
    assert 'print("4. Start a Review")' in information
    assert 'print("5. Record a Classification")' in information
    assert 'print("6. Record a Hypothesis")' in information
    assert 'print("7. Record a Determination")' in information
    assert "Review, Classification, Hypothesis, and Determination remain distinct." in information
    assert "A Hypothesis remains provisional" in judgment
    assert "Authority: Teacher-local review" in judgment


def test_issue54_response_communication_and_outcome_terms_do_not_collapse() -> None:
    source = (
        ROOT / "portia" / "menu" / "response_communication.py"
    ).read_text(encoding="utf-8")
    assert "Response records a bounded action; it does not establish effectiveness." in source
    assert "Communication records a communication act or attempt" in source
    assert "delivery, reading, understanding, or agreement." in source
    assert "does not record effectiveness or Outcome." in source


def test_issue54_support_delivery_fidelity_and_outcome_terms_do_not_collapse() -> None:
    support = (ROOT / "portia" / "menu" / "support.py").read_text(encoding="utf-8")
    delivery_tests = (
        ROOT / "tests" / "test_teacher_menu_support_delivery.py"
    ).read_text(encoding="utf-8")
    assert "Canonical activation does not prove implementation, fidelity, effectiveness, or Outcome." in support
    assert "test_prepare_fidelity_is_plan_adherence_not_outcome" in delivery_tests


def test_issue54_attention_term_remains_nonranking() -> None:
    source = (ROOT / "portia" / "menu" / "attention.py").read_text(encoding="utf-8")
    assert "Attention is workflow state, not a behavior score, risk score, " in source
    assert "urgency ranking, or recommendation." in source
    assert "It is not student risk, severity, or priority." in source


def test_issue54_teacher_reference_term_remains_local_and_nonofficial() -> None:
    source = (
        ROOT / "portia" / "menu" / "teacher_reference_export.py"
    ).read_text(encoding="utf-8")
    assert "This is a local teacher reference." in source
    assert "not an official record, disclosure " in source
    assert "does not by itself authorize disclosure" in source


def test_issue54_slice10_opens_no_menu_terminology_finding_when_no_defect_was_found() -> None:
    audit = _audit()
    findings = [
        finding
        for finding in audit["findings"]
        if finding.get("audit_domain") == "menu_terminology"
    ]
    assert findings == []
