"""#59 Slice 7: restart recovery and hostile Core-retained inventory handling."""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfWriter

from portia.intake.recovery import (
    FileCoreRetainedSourceRecoveryService,
    RetainedRecoveryError,
)
from portia.intake.retention import FileRetainFirstIntakeService, IntakeSourceError
from portia.intake.teacher import TeacherReturnedPaperService
from portia.menu import returned_paper as menu
from portia.menu.context import MenuSessionContext


def _pdf(path: Path, count: int = 3) -> Path:
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=612, height=792)
    with path.open("wb") as stream:
        writer.write(stream)
    return path


def _intake(tmp_path: Path, suffix: str = "pdf", count: int = 3):
    root = tmp_path / "workspace"
    root.mkdir(exist_ok=True)
    original = tmp_path / f"scan.{suffix}"
    if suffix == "pdf":
        _pdf(original, count)
    else:
        Image.new("RGB", (200, 200), "white").save(original)
    retained = FileRetainFirstIntakeService(root).admit_and_retain(original)
    return root, original, retained


def test_restart_preserves_exact_core_source_and_original_page_numbers(
    tmp_path: Path,
) -> None:
    root, _file, retained = _intake(tmp_path, count=3)
    before = retained.core_source.retained_source_path.read_bytes()
    recovered_service = FileCoreRetainedSourceRecoveryService(root)
    candidates = recovered_service.recent()
    assert len(candidates) == 1
    assert candidates[0].source_scan_id == retained.core_source.source_scan_id
    result = recovered_service.load(candidates[0])
    assert result.page_count == 3
    assert result.byte_count == retained.byte_count
    assert result.core_source.source_scan_id == retained.core_source.source_scan_id
    assert result.core_source.source_sha256 == hashlib.sha256(before).hexdigest()
    assert result.core_source.retained_source_path.read_bytes() == before
    assert [result.page_identity(n).source_page_number for n in (1, 2, 3)] == [1, 2, 3]
    assert list((root / "scans" / "source").rglob("*.pdf")) == [
        retained.core_source.retained_source_path
    ]
    # Original name is not reconstructible from Core's sanitized retained leaf.
    assert (
        result.core_source.source_filename
        == result.core_source.retained_source_path.name
    )


@pytest.mark.parametrize("suffix", ["jpg", "png"])
def test_restart_accepts_exact_core_retained_image(tmp_path: Path, suffix: str) -> None:
    root, _file, retained = _intake(tmp_path, suffix)
    recovery = FileCoreRetainedSourceRecoveryService(root)
    reloaded = recovery.load(recovery.recent()[0])
    assert reloaded.page_count == 1
    assert reloaded.source_format == retained.source_format
    assert reloaded.page_identity(1) == retained.page_identity(1)


def test_listing_is_read_only_and_does_not_retain_or_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _file, _retained = _intake(tmp_path)
    recovery = FileCoreRetainedSourceRecoveryService(root)

    def do_not_decode(*args: object, **kwargs: object) -> None:
        raise AssertionError("listing may not read PDF contents")

    monkeypatch.setattr(recovery.intake, "preflight", do_not_decode)
    assert len(recovery.recent()) == 1
    with pytest.raises(ValueError):
        recovery.recent(limit=0)
    with pytest.raises(ValueError):
        recovery.recent(limit=65)
    with pytest.raises(ValueError):
        recovery.recent(limit=True)


def test_changed_retained_content_blocks_resume_without_deletion(
    tmp_path: Path,
) -> None:
    root, _file, retained = _intake(tmp_path)
    service = FileCoreRetainedSourceRecoveryService(root)
    candidate = service.recent()[0]
    stored = retained.core_source.retained_source_path
    original = stored.read_bytes()
    stored.write_bytes(original + b"% changed after Core custody\n")
    with pytest.raises(RetainedRecoveryError):
        service.load(candidate)
    assert stored.read_bytes() != original
    assert stored.exists()


def test_forged_source_id_digest_or_path_is_rejected(tmp_path: Path) -> None:
    root, _file, _retained = _intake(tmp_path)
    recovery = FileCoreRetainedSourceRecoveryService(root)
    original = recovery.recent()[0]
    for forged in (
        dataclasses.replace(original, source_scan_id="scan_another"),
        dataclasses.replace(original, digest_prefix="f" * 12),
        dataclasses.replace(original, relative_path="../outside.pdf"),
    ):
        with pytest.raises((RetainedRecoveryError, IntakeSourceError)):
            recovery.load(forged)


def test_invalid_core_filenames_and_foreign_layouts_not_selected(
    tmp_path: Path,
) -> None:
    root, _file, _retained = _intake(tmp_path)
    root_dir = root / "scans" / "source"
    (root_dir / "not-a-date").mkdir()
    (root_dir / "not-a-date" / "fake.pdf").write_bytes(b"%PDF-")
    old = root_dir / "2026-10-17"
    old.mkdir()
    (old / "20261018T150001123456Z__paper__aaaaaaaaaaaa.pdf").write_bytes(b"%PDF-")
    (old / "20261017T150001123456Z__paper__aaaaaaaaaaaa.tiff").write_bytes(b"X")
    assert len(FileCoreRetainedSourceRecoveryService(root).recent()) == 1


def test_linked_core_inventory_is_never_followed(
    tmp_path: Path,
) -> None:
    root, _file, _retained = _intake(tmp_path)
    date_root = root / "scans" / "source" / "2026-10-17"
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    try:
        date_root.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink privilege unavailable")
    with pytest.raises((RetainedRecoveryError, IntakeSourceError)):
        FileCoreRetainedSourceRecoveryService(root).recent()


def test_inventory_limit_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.intake import recovery as module

    root, _file, _retained = _intake(tmp_path)
    monkeypatch.setattr(module, "_MAX_INVENTORY_ENTRIES", 1)
    with pytest.raises(RetainedRecoveryError, match="too large"):
        FileCoreRetainedSourceRecoveryService(root).recent()


def test_menu_resume_after_restart_never_calls_core_retention(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _file, retained = _intake(tmp_path, count=2)
    recovery = FileCoreRetainedSourceRecoveryService(root)
    selected = recovery.recent()[0]
    state = MenuSessionContext()
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: root)
    seen: list[str] = []

    class Gateway:
        def recent_retained(self):
            seen.append("list")
            return (selected,)

        def resume_recovered(self, candidate):
            assert candidate == selected
            seen.append("resume")
            return TeacherReturnedPaperService._interrupted(
                retained, "route_verification_unavailable"
            )

        def process_file(self, file):
            raise AssertionError("recovery must not re-retain original bytes")

    def choose(title, choices, labels, *, help_text):
        if "Scan / Import" in title:
            return "recover"
        return selected

    monkeypatch.setattr(menu, "select_one", choose)
    monkeypatch.setattr(menu, "_review", lambda result: seen.append("review"))
    menu.launch_returned_paper_menu(state, service=Gateway())  # type: ignore[arg-type]
    assert seen == ["list", "resume", "review"]
    assert state.last_retained_paper is retained


def test_menu_empty_core_inventory_is_actionable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = MenuSessionContext()
    monkeypatch.setattr(MenuSessionContext, "resolve_workspace", lambda self: tmp_path)
    seen: list[str] = []

    class Gateway:
        def recent_retained(self):
            return ()

    monkeypatch.setattr(menu, "select_one", lambda *a, **k: "recover")
    monkeypatch.setattr(menu, "_show", lambda title, lines: seen.extend(lines))
    menu.launch_returned_paper_menu(state, service=Gateway())  # type: ignore[arg-type]
    assert any("no compatible" in phrase.lower() for phrase in seen)
    assert state.last_retained_paper is None
