from __future__ import annotations

import re
from pathlib import Path

from portia.exports import (
    PROJECTION_DECISION_ALGORITHM,
    TEACHER_REFERENCE_ARTIFACT_FORMAT,
    TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE,
    TEACHER_REFERENCE_CONFIRMATION,
    TEACHER_REFERENCE_EXPORT_PURPOSES,
    TEACHER_REFERENCE_RENDERER_ID,
    TEACHER_REFERENCE_WORK_ROOTS,
)
from portia.menu.main import PRIMARY_TASKS

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_issue51_closed_surface_identity_is_exact() -> None:
    assert TEACHER_REFERENCE_EXPORT_PURPOSES == (
        "teacher_current",
        "participant_specific",
    )
    assert tuple(item.exact_key for item in TEACHER_REFERENCE_WORK_ROOTS) == (
        ("event", "2"),
        ("support_process", "1"),
    )
    assert PROJECTION_DECISION_ALGORITHM == "portia_projection_decision_v1"
    assert TEACHER_REFERENCE_RENDERER_ID == "portia_deliberate_export_artifact_v1"
    assert TEACHER_REFERENCE_ARTIFACT_FORMAT == "html"
    assert TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE == "text/html"
    assert TEACHER_REFERENCE_CONFIRMATION == "EXPORT"


def test_issue51_uses_issue88_execution_and_recovery_authority() -> None:
    execution = _read("portia/exports/execution.py")
    recovery = _read("portia/exports/recovery.py")
    for marker in (
        "stage_deliberate_export_candidates",
        "commit_deliberate_export_candidates",
        "recover_deliberate_export_committed_revision",
        "finalize_deliberate_export",
    ):
        assert marker in execution
    for marker in (
        "recover_deliberate_export_provenance",
        "recover_deliberate_export_committed_revision",
        "finalize_deliberate_export",
    ):
        assert marker in recovery
    assert "self.revalidate(preparation)" in execution
    execute_body = execution[execution.index("    def execute(") :]
    assert "self.prepare(" not in execute_body
    assert "PreparationService(" not in execute_body


def test_issue51_preparation_history_and_menu_boundaries_are_mechanical() -> None:
    preparation = _read("portia/exports/preparation.py")
    history = _read("portia/exports/history.py")
    menu = _read("portia/menu/teacher_reference_export.py")

    for forbidden in (
        "stage_deliberate_export_candidates",
        "commit_deliberate_export_candidates",
        "OperationJournalStore(",
        "exclusive_create(",
    ):
        assert forbidden not in preparation
    for forbidden in ("exclusive_create(", "guarded_replace(", "stage_bytes("):
        assert forbidden not in history

    assert len(PRIMARY_TASKS) == 8
    assert all(task.label != "Export" for task in PRIMARY_TASKS)
    assert "Export this work for teacher reference" in menu
    assert "Export this student's view of this work" in menu
    assert "View prior exports for this work" in menu
    assert "official record" in menu
    assert "disclosure" in menu
    assert "delivery" in menu


def test_issue51_runtime_dependency_direction_remains_core_only() -> None:
    pyproject = _read("pyproject.toml")
    runtime = pyproject.split("[project.optional-dependencies]", 1)[0].casefold()
    assert "pds-core>=0.6.3,<0.7" in runtime
    for sibling in (
        "pds-concord",
        "pds-meridian",
        "pds-quillan",
        "pds-scoreform",
        "pds-vitrine",
    ):
        assert sibling not in runtime


def test_issue51_acceptance_matrix_accounts_for_all_98_cases() -> None:
    matrix = _read("docs/validation/issue-51-acceptance-matrix.md")
    numbers = {
        int(value)
        for value in re.findall(r"^\|\s*(\d+)\s*\|", matrix, flags=re.MULTILINE)
    }
    assert numbers == set(range(1, 99))
