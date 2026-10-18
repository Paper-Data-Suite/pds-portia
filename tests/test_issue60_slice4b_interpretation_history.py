"""#60 Slice 4B: recovered, schema-exact interpretation history; synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_issue60_slice4a_interpretation_generations import (
    ACTOR,
    CLASS,
    WORK,
    Authorized,
    _candidates,
    _inventory,
    _setup,
)

from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
    InterpretationGenerationError,
)
from portia.intake.interpretation_history import FilePaperInterpretationHistoryService
from portia.intake.interpretation_profiles import LOCAL_ASSISTED_MARKS_V1
from portia.intake.manual_text_candidates import (
    AttributedManualPage,
    ManualTextSelection,
)
from portia.storage.errors import PortiaCorruptionError


def _path(root: Path) -> Path:
    folder = FilePaperInterpretationGenerationService(root)._collection(CLASS, WORK)
    return next(folder.glob("*.json"))


def _change(path: Path, change: object) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    assert callable(change)
    change(value)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


def _write_marks(
    root: Path, auth: Authorized, receipt: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(service.marks, "interpret", lambda *a, **k: _candidates())
    assert (
        service.stage_marks(CLASS, WORK, receipt, authorization=auth).disposition
        == "created"
    )


def test_empty_history_is_authorized_read_only_and_not_interpreted(
    tmp_path: Path,
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    before = _inventory(root)
    history = FilePaperInterpretationHistoryService(root).history(
        CLASS, WORK, receipt, authorization=auth
    )
    assert history.generation_count == 0
    assert history.latest is None
    assert history.summary()["current_status"] == "not_interpreted"
    assert history.summary()["current_generation"] is None
    assert not history.needs_attention
    assert _inventory(root) == before


def test_restart_recovers_exact_marks_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    before = _inventory(root)
    result = FilePaperInterpretationHistoryService(root).history(
        CLASS, WORK, receipt, authorization=auth
    )
    assert result.generation_count == 1
    assert result.latest is not None
    assert result.latest.field("generation") == 1
    assert result.summary() == {
        "page_record_id": receipt,
        "source_page_number": 1,
        "generation_count": 1,
        "current_generation": 1,
        "current_status": "partial",
        "needs_attention": True,
    }
    assert "session_context" not in repr(result)
    assert _inventory(root) == before
    assert not any(
        "capture_review" in path or "capture_proposal" in path for path in before
    )


def test_two_profiles_are_historical_and_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    writer = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(writer.marks, "interpret", lambda *a, **k: _candidates())
    one = writer.stage_marks(CLASS, WORK, receipt, authorization=auth)
    assisted = AttributedManualPage(
        _candidates(LOCAL_ASSISTED_MARKS_V1, "  exact human input  "),
        ACTOR,
        "session_context",
        "session_date",
    )
    monkeypatch.setattr(writer.manual, "transcribe_one", lambda *a, **k: assisted)
    two = writer.stage_manual(
        CLASS,
        WORK,
        receipt,
        ManualTextSelection("session_context", "session_date", "  exact human input  "),
        authorization=auth,
    )
    before = _inventory(root)
    history = FilePaperInterpretationHistoryService(root).history(
        CLASS, WORK, receipt, authorization=auth
    )
    assert tuple(item.field("generation") for item in history.records) == (1, 2)
    assert history.records == (one.record, two.record)
    assert history.latest == two.record
    assert "exact human input" not in str(history.summary())
    assert _inventory(root) == before


def test_generation_gap_is_not_repaired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    _change(_path(root), lambda item: item.update(generation=3))
    before = _inventory(root)
    with pytest.raises(PortiaCorruptionError, match="generation_history_gap"):
        FilePaperInterpretationHistoryService(root).history(
            CLASS, WORK, receipt, authorization=auth
        )
    assert _inventory(root) == before


def test_context_entry_can_never_gain_a_domain_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    _change(
        _path(root),
        lambda item: item["entries"]["session_context"].update(
            mapped_record_kind="event"
        ),
    )
    with pytest.raises(PortiaCorruptionError, match="mapping_not_declared"):
        FilePaperInterpretationHistoryService(root).history(
            CLASS, WORK, receipt, authorization=auth
        )


def test_undeclared_historical_entry_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    _change(
        _path(root),
        lambda item: item["entries"].update(fabricated={"entry_state": "blank"}),
    )
    with pytest.raises(PortiaCorruptionError, match="entry_inventory_conflict"):
        FilePaperInterpretationHistoryService(root).history(
            CLASS, WORK, receipt, authorization=auth
        )


def test_tampered_retained_source_prevents_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    original = source.core_source.retained_source_path
    original.write_bytes(original.read_bytes() + b"tampered")
    before = _inventory(root)
    with pytest.raises((RuntimeError, ValueError)):
        FilePaperInterpretationHistoryService(root).history(
            CLASS, WORK, receipt, authorization=auth
        )
    assert _inventory(root) == before


def test_permission_denied_before_protected_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, _source, receipt = _setup(tmp_path)
    reader = FilePaperInterpretationHistoryService(root)
    monkeypatch.setattr(reader, "_page", lambda *a, **k: pytest.fail("protected read"))
    denied = Authorized(False)
    with pytest.raises(PermissionError):
        reader.history(CLASS, WORK, receipt, authorization=denied)
    assert denied.operations == ["capture_interpretation.history"]


def test_history_change_during_read_blocks_stale_view(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    _write_marks(root, auth, receipt, monkeypatch)
    reader = FilePaperInterpretationHistoryService(root)
    original = reader._read
    calls = 0

    def switched(page: object):
        nonlocal calls
        calls += 1
        result = original(page)  # type: ignore[arg-type]
        return result if calls == 1 else ()

    monkeypatch.setattr(reader, "_read", switched)
    with pytest.raises(
        InterpretationGenerationError, match="history_changed_during_read"
    ):
        reader.history(CLASS, WORK, receipt, authorization=auth)
