"""#60 Slice 6A: previously received pages staged independently, without review."""

from __future__ import annotations

from pathlib import Path

import pytest
from test_issue60_slice4a_interpretation_generations import (
    CLASS,
    WORK,
    Authorized,
    _candidates,
    _inventory,
    _setup,
)
from test_issue60_slice5b_capture_proposal_persistence import (
    _event_source,
    _persist_interpretation,
)

from portia.intake.teacher import (
    TeacherPageResult,
    TeacherSourceResult,
)
from portia.intake.teacher_staging import FileTeacherPaperStagingService


def _received(source, record: str, *, status: str = "recorded") -> TeacherSourceResult:
    return TeacherSourceResult(
        source,
        (
            TeacherPageResult(
                identity=source.page_identity(1),
                status=status,  # type: ignore[arg-type]
                reason="received",
                class_id=CLASS if status == "recorded" else None,
                work_id=WORK if status == "recorded" else None,
                receipt_id=record if status == "recorded" else None,
            ),
        ),
    )


def test_received_eligible_page_stages_only_interpretation_and_attention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt = _setup(tmp_path)
    service = FileTeacherPaperStagingService(root)
    monkeypatch.setattr(
        service.generations.marks, "interpret", lambda *a, **kw: _candidates()
    )
    before = _inventory(root)
    result = service.stage_source(_received(source, receipt), authorization=auth)
    assert result.staged_pages == 1
    assert result.pages[0].status == "needs_attention"
    assert result.pages[0].reason == "partial_interpretation"
    assert result.pages[0].generation == 1
    assert result.pages[0].proposals_created == 0
    assert result.pages[0].attention_entries >= 1
    after = _inventory(root)
    assert len(after) == len(before) + 1
    assert not any("capture_review" in path for path in after)
    assert not any("capture_materialization" in path for path in after)
    assert (
        source.core_source.retained_source_path.read_bytes()
        == before[source.core_source.retained_source_path.relative_to(root).as_posix()]
    )
    restarted = FileTeacherPaperStagingService(root)
    monkeypatch.setattr(
        restarted.generations,
        "stage_marks",
        lambda *a, **kw: pytest.fail("replaying a saved generation must not rescan"),
    )
    repeated = restarted.stage_source(_received(source, receipt), authorization=auth)
    assert repeated.pages[0].generation == 1
    assert repeated.pages[0].status == "needs_attention"
    assert _inventory(root) == after


def test_existing_assisted_interpretation_is_not_replaced_by_marks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt, spec = _event_source(tmp_path)
    expected_id = _persist_interpretation(
        root,
        auth,
        receipt,
        spec,
        monkeypatch,
        literal="Unmodified described event",
    )
    service = FileTeacherPaperStagingService(root)
    monkeypatch.setattr(
        service.generations,
        "stage_marks",
        lambda *a, **kw: pytest.fail("manual generation may not be discarded"),
    )
    received = _received(source, receipt)
    first = service.stage_source(received, authorization=auth)
    assert first.pages[0].interpretation_id == expected_id
    assert first.pages[0].generation == 1
    assert first.pages[0].proposals_created == 1
    assert first.pages[0].requires_human_review
    assert first.pages[0].status == "needs_attention"  # partial is never accepted
    assert "Unmodified described event" not in repr(first)
    assert "Unmodified described event" not in str(first.summary())
    after = _inventory(root)
    second = FileTeacherPaperStagingService(root).stage_source(
        received, authorization=auth
    )
    assert second.pages[0].proposals_created == 0
    assert second.pages[0].proposals_reused == 1
    assert second.pages[0].generation == 1
    assert _inventory(root) == after
    assert not any("capture_review" in path for path in after)


def test_unaccepted_page_does_not_retain_again_or_read_protected_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt = _setup(tmp_path)
    gateway = FileTeacherPaperStagingService(root)
    monkeypatch.setattr(
        gateway.generations.pages,
        "resolve",
        lambda *a, **kw: pytest.fail("unaccepted page must not be resolved"),
    )
    before = _inventory(root)
    received = _received(source, receipt, status="needs_attention")
    result = gateway.stage_source(received, authorization=auth)
    assert result.pages[0].status == "needs_attention"
    assert result.pages[0].reason == "page_not_recorded"
    assert result.staged_pages == 0
    assert _inventory(root) == before


def test_denied_class_stops_before_protected_read_and_does_not_leak_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, source, receipt = _setup(tmp_path)
    service = FileTeacherPaperStagingService(root)
    monkeypatch.setattr(
        service.generations.pages,
        "resolve",
        lambda *a, **kw: pytest.fail("protected class read"),
    )
    denied = Authorized(False)
    before = _inventory(root)
    result = service.stage_source(_received(source, receipt), authorization=denied)
    assert result.pages[0].status == "access_denied"
    assert result.pages[0].reason == "class_access_denied"
    assert result.staged_pages == 0
    assert _inventory(root) == before
    assert denied.operations == ["capture_interpretation.teacher_stage"]


def test_locator_change_cannot_retarget_a_saved_source_page(
    tmp_path: Path,
) -> None:
    root, auth, source, receipt = _setup(tmp_path)
    wrong = TeacherSourceResult(
        source,
        (
            TeacherPageResult(
                source.page_identity(1),
                "recorded",
                "received",
                class_id=CLASS,
                work_id="cbat_other",
                receipt_id=receipt,
            ),
        ),
    )
    before = _inventory(root)
    result = FileTeacherPaperStagingService(root).stage_source(
        wrong, authorization=auth
    )
    assert result.pages[0].status in {"retryable", "conflict"}
    assert result.staged_pages == 0
    assert _inventory(root) == before


def test_missing_batch_hint_is_explicit_needs_attention_not_guessed(
    tmp_path: Path,
) -> None:
    root, auth, source, receipt = _setup(tmp_path)
    received = TeacherSourceResult(
        source,
        (
            TeacherPageResult(
                source.page_identity(1),
                "recorded",
                "received",
                class_id=CLASS,
                receipt_id=receipt,
            ),
        ),
    )
    result = FileTeacherPaperStagingService(root).stage_source(
        received, authorization=auth
    )
    assert result.pages[0].status == "needs_attention"
    assert result.pages[0].reason == "receipt_work_unavailable"
    assert result.staged_pages == 0
