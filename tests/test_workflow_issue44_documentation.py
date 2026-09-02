"""Documentation reconciliation tests for Issue #44."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_issue44_workflow_guide_retains_scope_boundaries() -> None:
    text = _text("docs/support-process-support-intervention-workflows.md")
    for phrase in (
        "planned != implemented",
        "Participant != authorized provider",
        "Need != diagnosis or permanent deficit",
        "Goal != attainment, Grade, proficiency, or Outcome",
        "planned schedule != actual occurrence",
        "Issue #45 owns Implementation/Fidelity",
        "Issue #46 owns Follow-Up/Outcome",
    ):
        assert phrase in text


def test_issue43_temporary_support_process_communication_deferral_is_reconciled() -> None:
    text = _text("docs/response-and-communication-workflows.md")
    assert "Issue #44 now supplies" in text
    assert (
        "new active/current Support Process Communication fails closed until Issue #44"
        not in text
    )


def test_readme_identifies_issue44_executable_planning_layer() -> None:
    text = _text("README.md")
    assert "### Issue #44 current implementation" in text
    assert "SupportProcessWorkflowService" in text
    assert "InterventionWorkflowService" in text
