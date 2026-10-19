"""#60 Slice 5B: real source-backed immutable capture proposal persistence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path
from PIL import Image
from test_issue60_slice4a_interpretation_generations import (
    ACTOR,
    CLASS,
    WORK,
    Authorized,
    _candidates,
    _fixture,
    _inventory,
    _setup,
)

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.capture.form_catalog import CapturePageSpec, installed_capture_page_specs
from portia.intake import (
    FilePageRouteDispatchService,
    FileRetainFirstIntakeService,
    PageQrDiscovery,
    SourceQrDiscovery,
)
from portia.intake.capture_proposal_persistence import (
    FileCaptureProposalPersistenceService,
)
from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
)
from portia.intake.interpretation_profiles import LOCAL_ASSISTED_MARKS_V1
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
from portia.models import CaptureBatchV1, CaptureProposalV1, PageTargetV2
from portia.storage.errors import PortiaCorruptionError


def _event_source(tmp_path: Path, form_id: str = "event_information"):
    root = tmp_path / "workspace"
    root.mkdir()
    meta = class_metadata_path(root, CLASS)
    meta.parent.mkdir(parents=True)
    write_class_metadata(
        meta,
        create_class_metadata(
            CLASS, "2026-2027", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc)
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(root)
    batches.create_or_load(
        CaptureBatchV1(_fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    pages = FilePageTargetService(root, batch_service=batches)
    routes = FilePageRouteService(root, batch_service=batches, page_service=pages)
    spec = next(
        item for item in installed_capture_page_specs() if item.form_id == form_id
    )
    wire = _fixture(
        "tests/fixtures/issue_56/slice_2/valid/page-target-v2-classroom-observation.json"
    )
    wire.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id="ptgt_event_first",
        page_index=1,
        page_purpose=spec.page_purpose,
        capture_mode=spec.capture_mode,
        template_identity=spec.template_identity(),
        entry_layout=spec.entry_layout(),
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    target = pages.create_or_load(PageTargetV2(wire), authorization=auth)
    registered = routes.register_or_load(target, authorization=auth)
    assert registered.locator is not None
    scan = tmp_path / "returned.png"
    Image.new("RGB", (800, 1000), "white").save(scan)
    source = FileRetainFirstIntakeService(root).admit_and_retain(scan)
    discovery = SourceQrDiscovery(
        source,
        (
            PageQrDiscovery(
                source.page_identity(1), "candidate_unverified", registered.locator
            ),
        ),
    )
    verified = FilePageRouteDispatchService(root).verify(discovery, authorization=auth)
    recorded = FilePageRecordService(root).record(verified, authorization=auth)
    assert recorded.accepted == 1
    receipt = recorded.pages[0].record
    assert receipt is not None and receipt.logical_id is not None
    return root, auth, source, receipt.logical_id, spec


def _manual_event_candidates(
    spec: CapturePageSpec, literal: str
) -> LocalPageCandidates:
    populated = False
    entries: list[EntryCandidates] = []
    for entry in spec.entries:
        fields: list[FieldCandidate] = []
        for original in entry.fields:
            if original.field_type == "choice":
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    "mark_recognition",
                    "unmarked",
                )
            elif (
                original.field_key in {"observed_description", "what_happened"}
                and not populated
            ):
                populated = True
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    "manual_transcription",
                    "candidate_detected",
                    literal=literal,
                )
            else:
                field = FieldCandidate(
                    original.field_key,
                    original.region_key,
                    original.capture_method,
                    "unreadable",
                )
            fields.append(field)
        state = (
            "candidate"
            if any(f.state == "candidate_detected" for f in fields)
            else "unreadable"
        )
        entries.append(EntryCandidates(entry.entry_key, state, tuple(fields)))
    assert populated
    return LocalPageCandidates(
        1,
        spec.layout_fingerprint,
        LOCAL_ASSISTED_MARKS_V1,
        "measured_sheet_boundary_and_exact_qr_v1",
        tuple(entries),
        ("text_provider_unavailable",),
    )


def _persist_interpretation(
    root: Path,
    auth: Authorized,
    receipt: str,
    spec: CapturePageSpec,
    monkeypatch: pytest.MonkeyPatch,
    literal: str = "Unmodified handwritten description",
) -> str:
    generations = FilePaperInterpretationGenerationService(root)
    selection_field = (
        "observed_description"
        if spec.form_id == "event_information"
        else "what_happened"
    )
    key = "event_01"
    staged = AttributedManualPage(
        _manual_event_candidates(spec, literal), ACTOR, key, selection_field
    )
    monkeypatch.setattr(
        generations.manual, "transcribe_one", lambda *args, **kwargs: staged
    )
    result = generations.stage_manual(
        CLASS,
        WORK,
        receipt,
        ManualTextSelection(key, selection_field, literal),
        authorization=auth,
    )
    assert result.record.logical_id is not None
    assert result.record.field("generation") == 1
    return result.record.logical_id


def test_exact_event_candidate_persists_one_reusable_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt, spec = _event_source(tmp_path)
    interpretation = _persist_interpretation(root, auth, receipt, spec, monkeypatch)
    before = _inventory(root)
    service = FileCaptureProposalPersistenceService(root)
    created = service.stage(CLASS, WORK, receipt, interpretation, 1, authorization=auth)
    assert created.created == 1 and created.reused == 0
    assert len(created.records) == 1
    proposal = created.records[0]
    assert isinstance(proposal, CaptureProposalV1)
    assert proposal.field("page_target_id") == "ptgt_event_first"
    assert proposal.field("entry_key") == "event_01"
    assert proposal.to_dict()["interpretation_ref"] == {
        "contract_version": "1",
        "interpretation_id": interpretation,
        "generation": 1,
    }
    assert proposal.to_dict()["target"] == {
        "record_kind": "event",
        "contract_version": "1",
        "context": {"kind": "new_work"},
    }
    assert proposal.to_dict()["field_bindings"] == [
        {
            "target_path": "/summary",
            "source_field": {
                "field_key": "observed_description",
                "value_source": "candidate_literal",
            },
        }
    ]
    assert "human_review_required" in proposal.to_dict()["review_flags"]
    after = _inventory(root)
    new_files = set(after) - set(before)
    assert len(new_files) == 1 and "capture_proposal" in next(iter(new_files))
    assert b"Unmodified handwritten description" not in next(
        iter(after[k] for k in new_files)
    )
    assert "Unmodified handwritten description" not in str(created.summary())
    assert (
        source.core_source.retained_source_path.read_bytes()
        == before[source.core_source.retained_source_path.relative_to(root).as_posix()]
    )
    restarted = FileCaptureProposalPersistenceService(root)
    reused = restarted.stage(
        CLASS, WORK, receipt, interpretation, 1, authorization=auth
    )
    assert reused.created == 0 and reused.reused == 1
    assert reused.records == created.records
    assert _inventory(root) == after
    assert "capture_proposal.persist" in auth.operations
    assert not any("capture_review" in path for path in after)


def test_unresolved_form_does_not_emit_empty_or_fabricated_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    generations = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        generations.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    saved = generations.stage_marks(CLASS, WORK, receipt, authorization=auth).record
    assert saved.logical_id is not None
    before = _inventory(root)
    service = FileCaptureProposalPersistenceService(root)
    result = service.stage(
        CLASS, WORK, receipt, saved.logical_id, 1, authorization=auth
    )
    assert result.created == result.reused == 0
    assert result.attention_entries >= 1
    assert result.records == ()
    assert _inventory(root) == before


def test_permission_denial_before_planning_or_storage_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, _source, receipt, _spec = _event_source(tmp_path)
    service = FileCaptureProposalPersistenceService(root)
    monkeypatch.setattr(
        service.planner,
        "plan",
        lambda *args, **kwargs: pytest.fail("unauthorized proposal plan read"),
    )
    denied = Authorized(False)
    with pytest.raises(PermissionError):
        service.stage(CLASS, WORK, receipt, "pint_fake", 1, authorization=denied)
    assert denied.operations == ["capture_proposal.persist"]


def test_changed_core_bytes_prevent_proposal_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, source, receipt, spec = _event_source(tmp_path)
    interpretation = _persist_interpretation(root, auth, receipt, spec, monkeypatch)
    original = source.core_source.retained_source_path
    original.write_bytes(original.read_bytes() + b"changed since intake")
    before = _inventory(root)
    with pytest.raises((RuntimeError, ValueError)):
        FileCaptureProposalPersistenceService(root).stage(
            CLASS, WORK, receipt, interpretation, 1, authorization=auth
        )
    assert _inventory(root) == before


def test_corrupted_proposal_inventory_fails_closed_on_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt, spec = _event_source(tmp_path)
    interpretation = _persist_interpretation(root, auth, receipt, spec, monkeypatch)
    service = FileCaptureProposalPersistenceService(root)
    service.stage(CLASS, WORK, receipt, interpretation, 1, authorization=auth)
    path = next(service._collection(CLASS, WORK).glob("*.json"))
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved["entry_key"] = "event_02"
    path.write_text(json.dumps(saved), encoding="utf-8")
    before = _inventory(root)
    with pytest.raises(PortiaCorruptionError):
        FileCaptureProposalPersistenceService(root).stage(
            CLASS, WORK, receipt, interpretation, 1, authorization=auth
        )
    assert _inventory(root) == before


def test_wrong_generation_makes_no_proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt, spec = _event_source(tmp_path)
    interpretation = _persist_interpretation(root, auth, receipt, spec, monkeypatch)
    before = _inventory(root)
    with pytest.raises(ValueError, match="generation_not_found"):
        FileCaptureProposalPersistenceService(root).stage(
            CLASS, WORK, receipt, interpretation, 3, authorization=auth
        )
    assert _inventory(root) == before
