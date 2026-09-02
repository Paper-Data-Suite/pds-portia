"""Focused tests for the Issue #44 mechanical workflow validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.validate_issue44_workflows import findings

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_issue44_workflows.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue44_validator_accepts_repository_surface() -> None:
    result = _run(ROOT)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "Portia Issue #44 workflow validation passed" in result.stdout


def test_issue44_validator_detects_missing_runtime_surface(tmp_path: Path) -> None:
    errors = findings(tmp_path)
    assert any("portia/workflows/support_processes.py" in error for error in errors)
    assert any("Issue #44 documentation" in error for error in errors)


def test_issue44_validator_has_no_runtime_import_dependency() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    assert "from portia" not in text
    assert "import portia" not in text
    assert "ast.parse" in text
