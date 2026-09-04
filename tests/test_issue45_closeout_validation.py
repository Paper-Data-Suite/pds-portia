"""Closeout guards for Issue #45 documentation and mechanical validation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_issue45_workflows.py"
GUIDE = ROOT / "docs" / "implementation-and-fidelity-workflows.md"
VALIDATION = (
    ROOT
    / "docs"
    / "validation"
    / "issue-45-implementation-and-fidelity-workflows-validation.md"
)
README = ROOT / "README.md"
PLANNING_GUIDE = ROOT / "docs" / "support-process-support-intervention-workflows.md"


def test_issue45_mechanical_validator_accepts_current_tree() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #45 workflow validation passed" in result.stdout


def test_issue45_documentation_preserves_semantic_and_issue_boundaries() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    for required in (
        "planned Support / Intervention != actual Implementation",
        "Implementation != Fidelity",
        "Fidelity != Outcome",
        "execution_state=completed != successful",
        "result=as_planned != effective",
        "Issue #46",
    ):
        assert required in guide

    readme = README.read_text(encoding="utf-8")
    assert "### Issue #45 current implementation" in readme
    assert (
        "fails closed until Issue #44 supplies production Support Process authority"
        not in readme
    )

    planning = PLANNING_GUIDE.read_text(encoding="utf-8")
    assert (
        "Issue #45 now supplies the production application/workflow layer"
        in planning
    )


def test_issue45_validation_record_documents_observed_final_closeout() -> None:
    text = VALIDATION.read_text(encoding="utf-8")
    for required in (
        "**Status:** final repository qualification passed",
        "238 passed",
        "62 schema-valid runtime scenarios",
        "38 structural-invalid fixtures",
        "Slice 9 observed distribution qualification",
        "Portia Issue #45 package inventory validation passed",
        "Portia installed-wheel Issue #45 Implementation/Fidelity smoke test passed",
        "2,646 tests passed",
        "Portia Issue #45 repository qualification passed",
        "final local Issue #45 closeout evidence",
    ):
        assert required in text
    assert "Final repository qualification is not yet claimed" not in text
