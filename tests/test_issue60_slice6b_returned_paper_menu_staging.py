"""#60 Slice 6B: optional STAGE consent, per-page reporting, and menu recovery."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_issue59_slice6_teacher_workflow import _source

from portia.intake.teacher import TeacherPageResult, TeacherSourceResult
from portia.intake.teacher_staging import TeacherStagedPage, TeacherStagingSummary
from portia.menu import returned_paper as menu
from portia.menu import returned_paper_staging as flow
from portia.menu.context import MenuSessionContext


def _received(tmp_path: Path) -> TeacherSourceResult:
    original = _source(tmp_path, 3)
    return TeacherSourceResult(
        original,
        (
            TeacherPageResult(
                original.page_identity(1),
                "recorded",
                "received",
                class_id="class_synthetic",
                work_id="cbat_synthetic",
                receipt_id="prec_first",
            ),
            TeacherPageResult(
                original.page_identity(2), "needs_attention", "missing_qr"
            ),
            TeacherPageResult(
                original.page_identity(3),
                "already_recorded",
                "existing_received",
                class_id="class_synthetic",
                work_id="cbat_synthetic",
                receipt_id="prec_last",
            ),
        ),
    )


def _staging() -> TeacherStagingSummary:
    return TeacherStagingSummary(
        (
            TeacherStagedPage(
                1,
                "needs_attention",
                "partial_interpretation",
                "pint_a",
                1,
                1,
                0,
                2,
            ),
            TeacherStagedPage(2, "needs_attention", "page_not_recorded"),
            TeacherStagedPage(
                3,
                "review_required",
                "candidate_review_required",
                "pint_b",
                2,
                0,
                1,
                0,
            ),
        )
    )


class FakeStager:
    def __init__(self, result: TeacherStagingSummary) -> None:
        self.result = result
        self.calls: list[tuple[TeacherSourceResult, object]] = []

    def stage_source(
        self, received: TeacherSourceResult, *, authorization: object
    ) -> TeacherStagingSummary:
        self.calls.append((received, authorization))
        return self.result


def test_decline_is_a_noop_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _received(tmp_path)
    stager = FakeStager(_staging())
    authority = object()
    recorded: list[str] = []
    monkeypatch.setattr(
        flow,
        "confirm_write",
        lambda title, verb, lines, *, help_text: recorded.append(verb) or False,
    )
    monkeypatch.setattr(
        flow,
        "_review_staging",
        lambda *_: pytest.fail("no staging summary"),
    )
    flow.offer_stage(
        original,
        tmp_path,
        authorization=authority,
        service=stager,  # type: ignore[arg-type]
    )
    assert recorded == ["STAGE"]
    assert stager.calls == []


def test_acceptance_uses_one_original_source_and_shows_page_level_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _received(tmp_path)
    expected = _staging()
    stager = FakeStager(expected)
    authority = object()
    seen: list[tuple[str, Any]] = []

    def confirm(
        title: str, verb: str, lines: tuple[str, ...], *, help_text: str
    ) -> bool:
        assert verb == "STAGE"
        assert "Verified Page Records: 2" in lines
        assert "Pages requiring intake follow-up: 1" in lines
        seen.append(("confirm", verb))
        return True

    monkeypatch.setattr(flow, "confirm_write", confirm)
    monkeypatch.setattr(
        flow, "_display", lambda title, lines: seen.append(("display", (title, lines)))
    )
    monkeypatch.setattr(
        flow,
        "select_one",
        lambda title, values, labels, **kwargs: values[0],
    )
    flow.offer_stage(
        original,
        tmp_path,
        authorization=authority,
        service=stager,  # type: ignore[arg-type]
    )
    assert stager.calls == [(original, authority)]
    assert [item[0] for item in seen] == ["confirm", "display", "display"]
    summary = seen[1][1][1]
    assert "Pages needing attention: 2" in summary
    assert "New Capture Proposals: 1" in summary
    assert "Reused Capture Proposals: 1" in summary
    assert "manual follow-up" in str(seen[-1])
    assert "student" not in str(seen).lower()


def test_unaccepted_source_does_not_prompt_or_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, 1)
    unaccepted = TeacherSourceResult(
        source,
        (TeacherPageResult(source.page_identity(1), "needs_attention", "missing_qr"),),
    )
    monkeypatch.setattr(
        flow, "confirm_write", lambda *_args, **_kwargs: pytest.fail("no prompt")
    )
    stager = FakeStager(_staging())
    flow.offer_stage(unaccepted, tmp_path, authorization=object(), service=stager)  # type: ignore[arg-type]
    assert stager.calls == []


def test_staging_output_order_is_checked_before_display(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = _received(tmp_path)
    tampered = TeacherStagingSummary((_staging().pages[1], _staging().pages[0]))
    monkeypatch.setattr(
        flow, "_display", lambda *_: pytest.fail("not a matching source")
    )
    with pytest.raises(ValueError, match="source_order_conflict"):
        flow._review_staging(original, tampered)


def test_display_is_privacy_minimized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    original = _received(tmp_path)
    monkeypatch.setattr(flow, "clear_screen", lambda: None)
    monkeypatch.setattr(flow, "pause_for_user", lambda: None)
    monkeypatch.setattr(flow, "print_menu_header", lambda *_: None)
    flow._show_page(_staging().pages[0])
    output = capsys.readouterr().out
    assert "Source candidates and proposals are not confirmed facts" in output
    assert "Original source page: 1" in output
    assert "Proposals created: 1" in output
    assert original.source.core_source.source_sha256 not in output
    assert "stack.pdf" not in output
    assert "PDS2|" not in output


def test_existing_menu_adds_staging_only_after_receipt_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _received(tmp_path)
    state = MenuSessionContext(last_retained_paper=result.source)
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: tmp_path)
    actions: list[str] = []

    class FakeGateway:
        def resume_retained(self, value: object) -> TeacherSourceResult:
            assert value is result.source
            actions.append("reuse_existing_source")
            return result

    fake_staging = FakeStager(_staging())
    monkeypatch.setattr(menu, "select_one", lambda *_args, **_kwargs: "retry")
    monkeypatch.setattr(menu, "_review", lambda *_: actions.append("receipt_review"))

    def offer(
        received: TeacherSourceResult,
        root: object,
        *,
        authorization: object,
        service: object,
    ) -> None:
        assert received is result and root == tmp_path and service is fake_staging
        actions.append("staging_offer")

    monkeypatch.setattr(menu, "offer_stage", offer)
    menu.launch_returned_paper_menu(
        state,
        service=FakeGateway(),
        staging_service=fake_staging,  # type: ignore[arg-type]
    )
    assert actions == ["reuse_existing_source", "receipt_review", "staging_offer"]
    assert state.last_retained_paper is result.source


def test_staging_error_reports_possible_partial_commit_and_preserves_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _received(tmp_path)
    state = MenuSessionContext(last_retained_paper=result.source)
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: tmp_path)
    shown: list[str] = []

    class FakeGateway:
        def resume_retained(self, value: object) -> TeacherSourceResult:
            return result

    monkeypatch.setattr(menu, "select_one", lambda *_a, **_k: "retry")
    monkeypatch.setattr(menu, "_review", lambda *_: None)
    monkeypatch.setattr(
        menu,
        "offer_stage",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("private text")),
    )
    monkeypatch.setattr(menu, "_show", lambda title, lines: shown.extend(lines))
    menu.launch_returned_paper_menu(
        state,
        service=FakeGateway(),
        staging_service=FakeStager(_staging()),  # type: ignore[arg-type]
    )
    assert any("may already be saved" in item for item in shown)
    assert "private text" not in "".join(shown)
    assert state.last_retained_paper is result.source
