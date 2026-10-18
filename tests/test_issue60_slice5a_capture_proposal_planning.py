"""#60 Slice 5A: source-bound proposal readiness, no persisted proposals."""

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

from portia.capture.form_catalog import CapturePageSpec, installed_capture_page_specs
from portia.intake.capture_proposal_planning import (
    FileCaptureProposalPlanningService,
    ProposalPlanningError,
    plan_historical_capture_mappings,
)
from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
)
from portia.intake.interpretation_history import FilePaperInterpretationHistoryService


def _spec(name: str) -> CapturePageSpec:
    return next(s for s in installed_capture_page_specs() if s.form_id == name)


def _map(
    spec: CapturePageSpec,
    *,
    entry_key: str | None = None,
    field_key: str | None = None,
    literal: str | None = None,
    mark_token: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {}
    for entry in spec.entries:
        if entry_key != entry.entry_key:
            result[entry.entry_key] = {"entry_state": "unreadable"}
            continue
        fields: dict[str, object] = {}
        for original in entry.fields:
            if original.field_type == "choice":
                field: dict[str, object] = {
                    "capture_method": "mark_recognition",
                    "region_key": original.region_key,
                    "recognition_state": "unmarked",
                }
                if mark_token is not None and mark_token in original.choices:
                    field["recognition_state"] = "candidate_detected"
                    field["candidate_literal"] = mark_token
            else:
                field = {
                    "capture_method": original.capture_method,
                    "region_key": original.region_key,
                    "recognition_state": "unreadable",
                }
                if field_key == original.field_key and literal is not None:
                    field["capture_method"] = "manual_transcription"
                    field["recognition_state"] = "candidate_detected"
                    field["candidate_literal"] = literal
            fields[original.field_key] = field
        result[entry.entry_key] = {"entry_state": "candidate", "fields": fields}
    return result


def test_event_information_has_one_explicit_source_to_contract_mapping() -> None:
    spec = _spec("event_information")
    entries = _map(
        spec,
        entry_key="event_01",
        field_key="observed_description",
        literal="Unedited firsthand notes",
    )
    plan = plan_historical_capture_mappings(spec, entries)
    assert plan[0].disposition == "needs_attention"  # source context uninspected
    assert plan[1].disposition == "proposable"
    mapping = plan[1].mapping
    assert mapping is not None
    assert mapping.target_wire() == {
        "record_kind": "event",
        "contract_version": "1",
        "context": {"kind": "new_work"},
    }
    assert mapping.binding_wire() == [
        {
            "target_path": "/summary",
            "source_field": {
                "field_key": "observed_description",
                "value_source": "candidate_literal",
            },
        }
    ]
    assert "human_review_required" in mapping.review_flags
    assert "canonical" in " ".join(mapping.review_flags)
    assert "Unedited firsthand notes" not in repr(plan)


def test_multi_event_slots_remain_independently_reviewable() -> None:
    spec = _spec("multi_event_information")
    entries = _map(
        spec, entry_key="event_02", field_key="what_happened", literal="Literal B"
    )
    result = plan_historical_capture_mappings(spec, entries)
    assert [item.disposition for item in result] == [
        "needs_attention",
        "needs_attention",
        "proposable",
    ]
    assert result[2].mapping is not None
    assert result[2].mapping.bindings[0].field_key == "what_happened"


def test_detected_people_without_summary_cannot_fabricate_event() -> None:
    spec = _spec("event_information")
    results = plan_historical_capture_mappings(
        spec,
        _map(
            spec, entry_key="event_01", field_key="persons_reported", literal="Person"
        ),
    )
    assert results[1].disposition == "needs_attention"
    assert results[1].attention_codes == ("summary_candidate_unavailable",)
    assert results[1].mapping is None


def test_context_candidate_never_makes_a_standalone_domain_proposal() -> None:
    spec = _spec("event_information")
    result = plan_historical_capture_mappings(
        spec,
        _map(spec, entry_key="event_context", field_key="location", literal="Room 2"),
    )
    assert result[0].disposition == "context_only"
    assert result[0].mapping is None


def test_ambiguous_observation_mapping_is_not_silently_selected() -> None:
    spec = _spec("daily_classroom_observation")
    entries = _map(spec, entry_key="observation_01", mark_token="positive")
    result = plan_historical_capture_mappings(spec, entries)
    assert result[1].disposition == "needs_attention"
    assert result[1].attention_codes == ("target_family_choice_required",)
    assert result[1].mapping is None


@pytest.mark.parametrize(
    "name,key",
    [
        ("communication_log", "communication_01"),
        ("follow_up", "follow_up_01"),
        ("support_implementation", "implementation_01"),
        ("focused_monitoring", "monitoring_01"),
        ("support_process_evidence", "support_evidence_01"),
    ],
)
def test_single_family_is_not_automatic_mapping_without_exact_target_path(
    name: str,
    key: str,
) -> None:
    spec = _spec(name)
    selected = next(e for e in spec.entries if e.entry_key == key)
    first_text = next(f for f in selected.fields if f.field_type == "text")
    result = plan_historical_capture_mappings(
        spec,
        _map(spec, entry_key=key, field_key=first_text.field_key, literal="Evidence"),
    )
    proposed = next(p for p in result if p.entry_key == key)
    assert proposed.disposition == "needs_attention"
    assert proposed.attention_codes == ("target_mapping_not_qualified",)
    assert proposed.mapping is None


def test_undeclared_field_or_entry_is_not_accepted() -> None:
    spec = _spec("event_information")
    entries = _map(
        spec, entry_key="event_01", field_key="observed_description", literal="X"
    )
    entries["fabricated"] = {"entry_state": "candidate"}
    with pytest.raises(ProposalPlanningError, match="entry_inventory_conflict"):
        plan_historical_capture_mappings(spec, entries)
    del entries["fabricated"]
    entry = entries["event_01"]
    assert isinstance(entry, dict)
    fields = entry["fields"]
    assert isinstance(fields, dict)
    del fields["observed_description"]
    with pytest.raises(ProposalPlanningError, match="field_inventory_conflict"):
        plan_historical_capture_mappings(spec, entries)


def test_candidate_without_qualified_manual_literal_is_not_proposable() -> None:
    spec = _spec("event_information")
    entries = _map(
        spec, entry_key="event_01", field_key="observed_description", literal="X"
    )
    item = entries["event_01"]
    assert isinstance(item, dict)
    fields = item["fields"]
    assert isinstance(fields, dict)
    summary = fields["observed_description"]
    assert isinstance(summary, dict)
    summary["capture_method"] = "handwriting_recognition"
    with pytest.raises(ProposalPlanningError, match="unqualified_summary_candidate"):
        plan_historical_capture_mappings(spec, entries)


def test_verified_generation_readiness_does_not_create_proposals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    writer = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        writer.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    saved = writer.stage_marks(CLASS, WORK, receipt, authorization=auth).record
    assert saved.logical_id is not None
    original = _inventory(root)
    service = FileCaptureProposalPlanningService(root)
    plan = service.plan(CLASS, WORK, receipt, saved.logical_id, 1, authorization=auth)
    assert plan.proposable_count == 0
    assert plan.attention_count >= 1
    assert plan.summary()["proposable_entries"] == 0
    assert _inventory(root) == original
    assert not any("capture_proposal" in path for path in original)
    assert "capture_proposal.plan" in auth.operations
    with pytest.raises(ProposalPlanningError, match="generation_not_found"):
        service.plan(CLASS, WORK, receipt, saved.logical_id, 2, authorization=auth)


def test_revoked_access_blocks_before_history_inspection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, _source, receipt = _setup(tmp_path)
    service = FileCaptureProposalPlanningService(root)
    monkeypatch.setattr(
        service.history,
        "history",
        lambda *args, **kwargs: pytest.fail("class data read without authority"),
    )
    denied = Authorized(False)
    with pytest.raises(PermissionError):
        service.plan(CLASS, WORK, receipt, "pint_fake", 1, authorization=denied)
    assert denied.operations == ["capture_proposal.plan"]


def test_history_drift_during_planning_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    writer = FilePaperInterpretationGenerationService(root)
    monkeypatch.setattr(
        writer.marks, "interpret", lambda *args, **kwargs: _candidates()
    )
    saved = writer.stage_marks(CLASS, WORK, receipt, authorization=auth).record
    assert saved.logical_id is not None
    service = FileCaptureProposalPlanningService(root)
    original = service.history.history
    calls = 0

    def changed(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        result = original(*args, **kwargs)
        if calls == 2:
            return result.__class__(
                result.page_record_id, result.source_page_number, ()
            )
        return result

    monkeypatch.setattr(service.history, "history", changed)
    with pytest.raises(ProposalPlanningError, match="history_changed"):
        service.plan(CLASS, WORK, receipt, saved.logical_id, 1, authorization=auth)


def test_read_only_plan_requires_explicit_interpretation_generation(
    tmp_path: Path,
) -> None:
    root, auth, _source, receipt = _setup(tmp_path)
    history = FilePaperInterpretationHistoryService(root).history(
        CLASS, WORK, receipt, authorization=auth
    )
    assert history.generation_count == 0
    with pytest.raises(ProposalPlanningError, match="generation_not_found"):
        FileCaptureProposalPlanningService(root).plan(
            CLASS, WORK, receipt, "pint_missing", 1, authorization=auth
        )
