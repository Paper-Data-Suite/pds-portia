"""Documentation guards for the Issue #43 executable workflow boundary."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "response-and-communication-workflows.md"
VALIDATION = (
    ROOT
    / "docs"
    / "validation"
    / "issue-43-response-and-communication-workflows-validation.md"
)


def test_issue43_guide_documents_public_service_surface() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    for phrase in (
        "ResponseWorkflowService",
        "CommunicationWorkflowService",
        "response_reference(...)",
        "communication_reference(...)",
        "require_current_use()",
        "transition_lifecycle(...)",
        "correct(...)",
    ):
        assert phrase in text


def test_issue43_guide_preserves_epistemic_and_history_boundaries() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    for phrase in (
        "Response is not evidence",
        "Communication is not an Account",
        "completed Communication != recipient participation",
        "later communication attempt is not a correction",
        "never silently follow successors",
        "no Amendment operation",
    ):
        assert phrase in text


def test_issue43_guide_reconciles_support_process_runtime_activation() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "Issue #43 implements the Communication" in text
    assert "Issue #44 now supplies" in text
    assert "Support Process Communication" in text
    assert "without changing `communication@1`" in text
    assert "fails closed until Issue #44" not in text


def test_issue43_validation_records_frozen_runtime_acceptance() -> None:
    text = VALIDATION.read_text(encoding="utf-8")
    for phrase in (
        "Total runtime scenarios:        76",
        "P22-07",
        "233 passing tests",
        "tests/test_workflow_issue17_runtime_parity.py",
        "tests/test_workflow_issue22_p22_07_runtime_parity.py",
    ):
        assert phrase in text
