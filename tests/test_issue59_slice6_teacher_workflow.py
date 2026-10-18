"""#59 Slice 6: teacher-facing one-file intake and same-custody retry contracts."""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pds_core.scan_retention import RetainedSourceScan

from portia.intake.contracts import SourceFormat
from portia.intake.retention import RetainedIntakeSource, SourcePreflight
from portia.intake.teacher import (
    TeacherPageResult,
    TeacherReturnedPaperService,
    TeacherSourceResult,
)
from portia.menu import main as main_menu
from portia.menu import returned_paper as menu
from portia.menu.context import MenuSessionContext


class Authority:
    def require_access(self, class_id: str, operation: str) -> None:
        assert operation.startswith("capture_")

    def attribution(self) -> dict[str, object]:
        return {"type": "system_process", "process_id": "synthetic_test"}


def _source(tmp_path: Path, page_count: int = 3) -> RetainedIntakeSource:
    path = tmp_path / "retained.pdf"
    path.write_bytes(b"%PDF-synthetic-source")
    timestamp = datetime(2026, 10, 18, tzinfo=timezone.utc)
    core = RetainedSourceScan(
        source_scan_id="scan_synthetic_first",
        source_filename="stack.pdf",
        source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        retained_source_path=path,
        retained_source_relative_path="scans/source/2026-10-18/retained.pdf",
        intake_timestamp=timestamp,
        intake_date=timestamp.date(),
    )
    return RetainedIntakeSource(core, SourceFormat.PDF, path.stat().st_size, page_count)


def test_status_counts_and_source_page_order(tmp_path: Path) -> None:
    source = _source(tmp_path)
    result = TeacherSourceResult(
        source,
        (
            TeacherPageResult(
                source.page_identity(1), "recorded", "received", receipt_id="prec_a"
            ),
            TeacherPageResult(source.page_identity(2), "needs_attention", "missing_qr"),
            TeacherPageResult(
                source.page_identity(3),
                "already_recorded",
                "existing_received",
                receipt_id="prec_b",
            ),
        ),
    )
    assert result.status == "completed_with_exceptions"
    assert result.accepted == 2 and result.requires_attention == 1
    assert [item.identity.source_page_number for item in result.pages] == [1, 2, 3]
    with pytest.raises(FrozenInstanceError):
        result.pages[0].status = "conflict"  # type: ignore[misc]
    with pytest.raises(ValueError, match="all original"):
        TeacherSourceResult(source, result.pages[:2])
    with pytest.raises(ValueError, match="accepted page"):
        TeacherPageResult(source.page_identity(1), "recorded", "received")
    with pytest.raises(ValueError, match="unaccepted page"):
        TeacherPageResult(
            source.page_identity(1), "conflict", "bad", receipt_id="prec_a"
        )


def test_retained_retry_preserves_exact_page_identity_and_received_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, 2)
    service = TeacherReturnedPaperService(tmp_path, authorization=Authority())
    actions: list[str] = []

    def discover(retained: RetainedIntakeSource) -> object:
        assert retained is source
        actions.append("discover")
        return object()

    discovery = object()
    monkeypatch.setattr(service.discovery, "discover", discover)

    def verify(value: object, *, authorization: object) -> object:
        actions.append("verify")
        assert authorization is service.authorization
        return discovery

    monkeypatch.setattr(service.dispatch, "verify", verify)

    receipts = SimpleNamespace(
        source_routes=SimpleNamespace(
            pages=(SimpleNamespace(verified=None), SimpleNamespace(verified=None))
        ),
        pages=(
            SimpleNamespace(
                identity=source.page_identity(1),
                status="created",
                reason="received",
                record=SimpleNamespace(logical_id="prec_1"),
            ),
            SimpleNamespace(
                identity=source.page_identity(2),
                status="needs_attention",
                reason="missing_qr",
                record=None,
            ),
        ),
    )

    def record(value: object, *, authorization: object) -> object:
        actions.append("record")
        assert value is discovery and authorization is service.authorization
        return receipts

    monkeypatch.setattr(service.records, "record", record)
    one = service.resume_retained(source)
    assert one.accepted == 1 and one.requires_attention == 1
    assert one.pages[0].receipt_id == "prec_1"
    assert one.pages[1].receipt_id is None
    assert actions == ["discover", "verify", "record"]
    actions.clear()
    receipts.pages = (
        SimpleNamespace(
            identity=source.page_identity(1),
            status="reused",
            reason="existing_received",
            record=SimpleNamespace(logical_id="prec_1"),
        ),
        SimpleNamespace(
            identity=source.page_identity(2),
            status="reused",
            reason="existing_received",
            record=SimpleNamespace(logical_id="prec_2"),
        ),
    )
    again = service.resume_retained(source)
    assert again.status == "completed"
    assert again.pages[0].receipt_id == one.pages[0].receipt_id
    assert again.pages[0].identity == one.pages[0].identity
    assert actions == ["discover", "verify", "record"]


@pytest.mark.parametrize(
    ("stage", "expected"),
    [
        ("discovery", "page_discovery_unavailable"),
        ("dispatch", "route_verification_unavailable"),
        ("receipts", "page_receipts_need_recovery"),
    ],
)
def test_interrupted_stages_keep_all_page_numbers_and_retryable_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str, expected: str
) -> None:
    service = TeacherReturnedPaperService(tmp_path, authorization=Authority())
    source = _source(tmp_path)

    def fail(*args: object, **kwargs: object) -> Any:
        raise RuntimeError("private scan text must not appear in public outcomes")

    monkeypatch.setattr(
        service.discovery,
        "discover",
        fail if stage == "discovery" else lambda *_: object(),
    )
    monkeypatch.setattr(
        service.dispatch,
        "verify",
        fail if stage == "dispatch" else lambda *_a, **_kw: object(),
    )
    monkeypatch.setattr(service.records, "record", fail)
    result = service.resume_retained(source)
    assert result.status == "retained_needs_attention"
    assert result.requires_attention == 3
    assert [p.identity.source_page_number for p in result.pages] == [1, 2, 3]
    assert {p.reason for p in result.pages} == {expected}
    assert "private scan text" not in repr(result)


def test_process_file_retains_only_once_then_uses_same_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, 1)
    service = TeacherReturnedPaperService(tmp_path, authorization=Authority())
    calls: list[str] = []

    def retain(file: Path) -> RetainedIntakeSource:
        assert file == tmp_path / "stack.pdf"
        calls.append("retain")
        return source

    monkeypatch.setattr(service.retention, "admit_and_retain", retain)

    def resume(retained: RetainedIntakeSource) -> TeacherSourceResult:
        assert retained is source
        calls.append("resume")
        return TeacherReturnedPaperService._interrupted(
            source, "page_discovery_unavailable"
        )

    monkeypatch.setattr(service, "resume_retained", resume)
    assert service.process_file(tmp_path / "stack.pdf").requires_attention == 1
    assert calls == ["retain", "resume"]


def test_main_menu_keeps_existing_tasks_and_adds_scan_import() -> None:
    assert main_menu.PRIMARY_TASKS[-1].key == "8"
    assert main_menu.CAPTURE_TASK.key == "10"
    assert "10. Create Paper Capture Forms" in main_menu.render_main_menu()
    assert "11. Scan / Import Returned Paper" in main_menu.render_main_menu()


def test_menu_confirmation_precedes_retention_and_exposes_page_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, 2)
    status = TeacherSourceResult(
        source,
        (
            TeacherPageResult(
                source.page_identity(1),
                "recorded",
                "received",
                receipt_id="prec_a",
                class_id="class_synthetic",
                form_name="daily_classroom_observation",
                page_target_index=5,
                template_page_ordinal=2,
            ),
            TeacherPageResult(source.page_identity(2), "needs_attention", "missing_qr"),
        ),
    )
    state = MenuSessionContext()
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: tmp_path)
    calls: list[str] = []

    class FakeService:
        def inspect(self, file: Path) -> SourcePreflight:
            calls.append("inspect")
            return SourcePreflight(file, SourceFormat.PDF, 100, 2, "a" * 64)

        def process_file(self, file: Path) -> TeacherSourceResult:
            calls.append("process")
            return status

    def select(*args: object, **kwargs: object) -> str:
        return "new"

    def confirm(*args: object, **kwargs: object) -> bool:
        calls.append("confirm")
        return True

    monkeypatch.setattr(menu, "select_one", select)
    monkeypatch.setattr(
        menu, "prompt_text", lambda *a, **k: str(tmp_path / "batch.pdf")
    )
    monkeypatch.setattr(menu, "confirm_write", confirm)
    monkeypatch.setattr(menu, "_review", lambda result: calls.append("review"))
    menu.launch_returned_paper_menu(state, service=FakeService())  # type: ignore[arg-type]
    assert calls == ["inspect", "confirm", "process", "review"]
    assert state.last_retained_paper is source


def test_menu_retry_does_not_retire_or_reretain_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _source(tmp_path, 1)
    state = MenuSessionContext(last_retained_paper=source)
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: tmp_path)
    calls: list[str] = []

    class FakeService:
        def resume_retained(
            self, source_value: RetainedIntakeSource
        ) -> TeacherSourceResult:
            assert source_value is source
            calls.append("replayed")
            return TeacherReturnedPaperService._interrupted(
                source, "page_discovery_unavailable"
            )

    monkeypatch.setattr(menu, "select_one", lambda *a, **k: "retry")
    monkeypatch.setattr(menu, "_review", lambda result: calls.append("review"))
    menu.launch_returned_paper_menu(state, service=FakeService())  # type: ignore[arg-type]
    assert calls == ["replayed", "review"]


def test_operator_details_only_show_source_position_and_verified_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _source(tmp_path, 1)
    item = TeacherPageResult(source.page_identity(1), "needs_attention", "missing_qr")
    monkeypatch.setattr(menu, "clear_screen", lambda: None)
    monkeypatch.setattr(menu, "pause_for_user", lambda: None)
    menu._show_page(item)
    rendered = capsys.readouterr().out
    assert "Original source page: 1" in rendered
    assert "check the page or rescan" in rendered
    assert source.core_source.source_sha256 not in rendered
    assert "PDS2|" not in rendered
