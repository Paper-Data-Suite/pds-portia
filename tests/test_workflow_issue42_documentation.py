"""Focused documentation contract for the Issue #42 judgment workflow guide."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "review-classification-hypothesis-determination-workflows.md"
VALIDATION = (
    ROOT
    / "docs"
    / "validation"
    / "issue-42-review-classification-hypothesis-determination-workflows-validation.md"
)
README = ROOT / "README.md"


def test_issue42_workflow_guide_covers_public_semantic_boundaries() -> None:
    text = GUIDE.read_text(encoding="utf-8")

    required = (
        "# Review, Classification, Hypothesis, and Determination workflows",
        "ReviewWorkflowService",
        "ClassificationWorkflowService",
        "HypothesisWorkflowService",
        "DeterminationWorkflowService",
        "Exact history versus current/consequential use",
        "ModuleJudgmentEvidenceAuthority",
        "Digital authoring and imported historical records",
        "Determination reconsideration and reversal",
        "P22-02",
        "P22-04",
        "Review != finding",
        "Hypothesis != fact or diagnosis",
        "Determination != Response",
    )
    missing = [value for value in required if value not in text]

    assert missing == []


def test_issue42_validation_and_readme_navigation_are_reconciled() -> None:
    validation = " ".join(VALIDATION.read_text(encoding="utf-8").split())
    readme = " ".join(README.read_text(encoding="utf-8").split())

    validation_required = (
        "# Issue #42 Review, Classification, Hypothesis, and Determination workflow validation",
        "ReviewWorkflowService",
        "ClassificationWorkflowService",
        "HypothesisWorkflowService",
        "DeterminationWorkflowService",
        "historical-pinning behavior",
        "active import history failing closed for current use",
        "ModuleJudgmentEvidenceAuthority",
        "P22-02",
        "P22-04",
        "Final repository/package qualification **passed on 2026-08-30**",
        "python scripts/validate_repository.py --core-wheel",
        "Portia Issue #42 repository qualification passed",
        "isolated installed-wheel smoke",
    )
    readme_required = (
        "### Issue #42 current implementation",
        "docs/review-classification-hypothesis-determination-workflows.md",
    )

    assert [value for value in validation_required if value not in validation] == []
    assert [value for value in readme_required if value not in readme] == []
