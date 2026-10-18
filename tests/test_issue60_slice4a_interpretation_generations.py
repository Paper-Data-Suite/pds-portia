"""#60 Slice 4A: immutable interpretation generation evidence on synthetic paper."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path
from PIL import Image

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake import (
    FilePageRouteDispatchService,
    FileRetainFirstIntakeService,
    PageQrDiscovery,
    SourceQrDiscovery,
)
from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
    InterpretationGenerationError,
)
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_MARKS_V1,
)
from portia.intake.local_mark_candidates import (
    EntryCandidates,
    FieldCandidate,
    LocalPageCandidates,
)
from portia.intake.manual_text_candidates import (
    AttributedManualPage,
    ManualTextSelection,
)
from portia.intake.page_records import FilePageRecordService
from portia.models import CaptureBatchV1, PageTargetV2, PaperInterpretationV1
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError

CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}
ROOT = Path(__file__).resolve().parents[1]


class Authorized:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.operations: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.operations.append(operation)
        if class_id != CLASS or not self.allowed:
            raise PermissionError("denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def _fixture(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _setup(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = class_metadata_path(workspace, CLASS)
    path.parent.mkdir(parents=True)
    write_class_metadata(
        path,
        create_class_metadata(
            CLASS, "2026-2027", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc)
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(workspace)
    batches.create_or_load(
        CaptureBatchV1(_fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    targets = FilePageTargetService(workspace, batch_service=batches)
    routes = FilePageRouteService(
        workspace, batch_service=batches, page_service=targets
    )
    spec = installed_capture_page_specs()[0]
    raw = _fixture(
        "tests/fixtures/issue_56/slice_2/valid/page-target-v2-classroom-observation.json"
    )
    raw.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id="ptgt_first",
        page_index=5,
        template_identity=spec.template_identity(),
        entry_layout=spec.entry_layout(),
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    target = targets.create_or_load(PageTargetV2(raw), authorization=auth)
    registered = routes.register_or_load(target, authorization=auth)
    assert registered.locator is not None
    scan = tmp_path / "returned.png"
    Image.new("RGB", (800, 1000), "white").save(scan)
    source = FileRetainFirstIntakeService(workspace).admit_and_retain(scan)
    discovery = SourceQrDiscovery(
        source,
        (
            PageQrDiscovery(
                source.page_identity(1), "candidate_unverified", registered.locator
            ),
        ),
    )
    routed = FilePageRouteDispatchService(workspace).verify(
        discovery, authorization=auth
    )
    received = FilePageRecordService(workspace).record(routed, authorization=auth)
    assert received.accepted == 1
    receipt = received.pages[0].record
    assert receipt is not None
    return workspace, auth, source, receipt.logical_id


def _candidates(
    profile=LOCAL_MARKS_V1, manual_literal: str | None = None
) -> LocalPageCandidates:
    spec = installed_capture_page_specs()[0]
    entries = []
    touched = False
    for entry in spec.entries:
        fields = []
        for original in entry.fields:
            if original.field_type == "choice":
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    "mark_recognition",
                    "unmarked",
                )
            elif manual_literal is not None and not touched:
                touched = True
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    "manual_transcription",
                    "candidate_detected",
                    literal=manual_literal,
                )
            else:
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    original.capture_method,
                    "unreadable",
                )
            fields.append(field)
        states = {field.state for field in fields}
        state = (
            "candidate"
            if "candidate_detected" in states
            else "unreadable"
            if "unreadable" in states
            else "blank"
        )
        entries.append(EntryCandidates(entry.entry_key, state, tuple(fields)))
    return LocalPageCandidates(
        1,
        spec.layout_fingerprint,
        profile,
        "measured_sheet_boundary_and_exact_qr_v1",
        tuple(entries),
        ("text_provider_unavailable",),
    )


def _inventory(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_same_profile_replay_preserves_exact_one_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        service.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    before = _inventory(root)
    first = service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    assert first.disposition == "created"
    assert isinstance(first.record, PaperInterpretationV1)
    assert first.record.field("generation") == 1
    assert first.record.field("page_record_id") == identifier
    assert first.record.field("interpretation_status") == "partial"
    assert first.record.field("interpreter_profile") is not None
    after_first = _inventory(root)
    assert len(after_first) == len(before) + 1
    second = service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    assert second.disposition == "reused"
    assert second.record == first.record
    assert _inventory(root) == after_first
    assert (
        retained.core_source.retained_source_path.read_bytes()
        == before[
            retained.core_source.retained_source_path.relative_to(root).as_posix()
        ]
    )
    assert not any(
        "capture_review" in path or "capture_proposal" in path for path in after_first
    )


def test_manual_profile_appends_preserved_second_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        service.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    first = service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    staged = AttributedManualPage(
        _candidates(LOCAL_ASSISTED_MARKS_V1, "  exact transcription  "),
        ACTOR,
        "session_context",
        "session_date",
    )
    monkeypatch.setattr(
        service.manual, "transcribe_one", lambda *args, **kwargs: staged
    )
    second = service.stage_manual(
        CLASS,
        WORK,
        identifier,
        ManualTextSelection(
            "session_context", "session_date", "  exact transcription  "
        ),
        authorization=auth,
    )
    assert second.disposition == "created"
    assert second.record.field("generation") == 2
    assert first.record.field("generation") == 1
    assert second.record.logical_id != first.record.logical_id
    assert (
        service.stage_manual(
            CLASS,
            WORK,
            identifier,
            ManualTextSelection(
                "session_context", "session_date", "  exact transcription  "
            ),
            authorization=auth,
        ).disposition
        == "reused"
    )
    assert len(service._inventory(CLASS, WORK)) == 2


def test_changed_manual_literal_same_profile_is_conflict_not_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    holder = ["One"]

    def manual(*args: object, **kwargs: object) -> AttributedManualPage:
        return AttributedManualPage(
            _candidates(LOCAL_ASSISTED_MARKS_V1, holder[0]),
            ACTOR,
            "session_context",
            "session_date",
        )

    monkeypatch.setattr(service.manual, "transcribe_one", manual)
    service.stage_manual(
        CLASS,
        WORK,
        identifier,
        ManualTextSelection("session_context", "session_date", "One"),
        authorization=auth,
    )
    before = _inventory(root)
    holder[0] = "Two"
    with pytest.raises(PortiaConflictError, match="same_profile_changed_candidates"):
        service.stage_manual(
            CLASS,
            WORK,
            identifier,
            ManualTextSelection("session_context", "session_date", "Two"),
            authorization=auth,
        )
    assert _inventory(root) == before


def test_source_tampering_prevents_replay_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        service.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    source_path = retained.core_source.retained_source_path
    source_path.write_bytes(source_path.read_bytes() + b"corrupt")
    after = _inventory(root)
    with pytest.raises((RuntimeError, ValueError)):
        service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    assert _inventory(root) == after


def test_permission_denial_blocks_without_reading_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, _retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        service.pages, "resolve", lambda *args, **kwargs: pytest.fail("protected read")
    )
    denied = Authorized(False)
    with pytest.raises(PermissionError):
        service.stage_marks(CLASS, WORK, identifier, authorization=denied)
    assert denied.operations == ["capture_interpretation.persist"]


def test_invalid_field_inventory_refuses_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    invalid = replace(_candidates(), source_page_number=2)
    monkeypatch.setattr(service.marks, "interpret", lambda *args, **kwargs: invalid)
    with pytest.raises(
        InterpretationGenerationError, match="physical_source_page_conflict"
    ):
        service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    assert service._inventory(CLASS, WORK) == ()


def test_corrupt_history_refuses_replay_or_new_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _retained, identifier = _setup(tmp_path)
    service = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        service.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    service.stage_marks(CLASS, WORK, identifier, authorization=auth)
    folder = service._collection(CLASS, WORK)
    path = next(folder.glob("*.json"))
    path.write_bytes(
        path.read_bytes().replace(b'"generation":1', b'"generation":1,"generation":1')
    )
    with pytest.raises(PortiaCorruptionError):
        service.stage_marks(CLASS, WORK, identifier, authorization=auth)
