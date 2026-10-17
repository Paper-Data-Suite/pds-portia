"""Issue #57 closeout wiring and immutable packaging inventory checks."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_issue57_closeout import (
    RUNTIME_FILES,
    SDIST_FILES,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]


def test_issue57_closeout_source_and_qualification_wiring() -> None:
    assert validate(ROOT) == ()


def test_capture_runtime_and_sdist_inventory_are_distinct() -> None:
    assert RUNTIME_FILES
    assert SDIST_FILES
    assert not (RUNTIME_FILES & SDIST_FILES)
    assert all(path.startswith("portia/capture/") for path in RUNTIME_FILES)
    assert all(not path.startswith("portia/") for path in SDIST_FILES)


def test_issue57_final_closeout_fails_closed_on_missing_source(tmp_path: Path) -> None:
    findings = validate(tmp_path)
    assert any("required Issue #57 source missing" in message for message in findings)
    assert any("missing qualification wiring" in message for message in findings)
