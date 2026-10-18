"""#60 Slice 3B: explicitly attributed transcription, no review or domain writes."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

import pytest

from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_CANDIDATES_V1,
    LOCAL_MARKS_V1,
    InterpretationProfileError,
    resolve_interpretation_profile,
)
from portia.intake.local_mark_candidates import (
    EntryCandidates,
    FieldCandidate,
    LocalPageCandidates,
)
from portia.intake.manual_text_candidates import (
    FileManualTextCandidateService,
    ManualStagingError,
    ManualTextSelection,
    add_one_manual_text,
)


def _baseline(index: int = 0) -> LocalPageCandidates:
    spec = installed_capture_page_specs()[index]
    entries: list[EntryCandidates] = []
    for entry in spec.entries:
        fields = tuple(
            FieldCandidate(
                source.field_key,
                source.region_key,
                source.capture_method,
                "unreadable" if source.field_type == "text" else "unmarked",
            )
            for source in entry.fields
        )
        entries.append(EntryCandidates(entry.entry_key, "unreadable", fields))
    return LocalPageCandidates(
        2,
        spec.layout_fingerprint,
        LOCAL_MARKS_V1,
        "measured_sheet_boundary_and_exact_qr_v1",
        tuple(entries),
        ("text_provider_unavailable",),
    )


def _selection(index: int = 0) -> ManualTextSelection:
    spec = installed_capture_page_specs()[index]
    for entry in spec.entries:
        for source in entry.fields:
            if source.field_type == "text":
                return ManualTextSelection(
                    entry.entry_key, source.field_key, "  As observed.\n"
                )
    raise AssertionError("all historical layouts require at least one text region")


def test_manual_profile_is_explicit_without_changing_old_historical_profiles() -> None:
    assert LOCAL_CANDIDATES_V1.manual_provider == "not_yet_implemented"
    assert LOCAL_MARKS_V1.manual_provider == "not_yet_implemented"
    assert LOCAL_ASSISTED_MARKS_V1.manual_provider == "local_operator_v1"
    assert LOCAL_ASSISTED_MARKS_V1.text_provider == "none"
    assert LOCAL_ASSISTED_MARKS_V1.mark_provider == "local_checkbox_v1"
    assert LOCAL_ASSISTED_MARKS_V1.external_network_allowed is False
    assert (
        resolve_interpretation_profile(LOCAL_ASSISTED_MARKS_V1.wire_identity())
        is LOCAL_ASSISTED_MARKS_V1
    )
    with pytest.raises(InterpretationProfileError):
        resolve_interpretation_profile(
            {**LOCAL_ASSISTED_MARKS_V1.wire_identity(), "interpreter_version": "latest"}
        )


@pytest.mark.parametrize("index", range(10))
def test_each_frozen_layout_allows_one_declared_literal_only(index: int) -> None:
    spec = installed_capture_page_specs()[index]
    original = _baseline(index)
    selection = _selection(index)
    result = add_one_manual_text(original, spec, selection)
    assert original.profile is LOCAL_MARKS_V1  # source remains unchanged
    assert result.profile is LOCAL_ASSISTED_MARKS_V1
    assert result.source_page_number == original.source_page_number
    assert result.layout_fingerprint == original.layout_fingerprint
    assert tuple(result.entry_map()) == tuple(entry.entry_key for entry in spec.entries)
    data = result.entry_map()[selection.entry_key]
    assert data["entry_state"] == "candidate"
    fields = data["fields"]
    assert isinstance(fields, dict)
    manual = fields[selection.field_key]
    assert manual == {
        "capture_method": "manual_transcription",
        "region_key": next(
            fld.region_key
            for entry in spec.entries
            for fld in entry.fields
            if entry.entry_key == selection.entry_key
            and fld.field_key == selection.field_key
        ),
        "recognition_state": "candidate_detected",
        "candidate_literal": selection.literal,
    }
    assert "normalized_value" not in manual and "confidence" not in manual
    assert "text_provider_unavailable" in result.limitation_codes
    assert result.interpretation_status == "partial"


def test_manual_does_not_overwrite_any_choice_or_other_text() -> None:
    spec = installed_capture_page_specs()[0]
    base = _baseline()
    choice = next(
        (idx, pos, fld)
        for idx, entry in enumerate(spec.entries)
        for pos, fld in enumerate(entry.fields)
        if fld.field_type == "choice"
    )
    e, f, field = choice
    old = base.entries[e]
    marked = replace(
        base,
        entries=tuple(
            replace(
                old,
                state="candidate",
                fields=tuple(
                    FieldCandidate(
                        field.field_key,
                        field.region_key,
                        "mark_recognition",
                        "ambiguous",
                        alternatives=field.choices[:2],
                    )
                    if pos == f
                    else existing
                    for pos, existing in enumerate(old.fields)
                ),
            )
            if idx == e
            else entry
            for idx, entry in enumerate(base.entries)
        ),
    )
    merged = add_one_manual_text(marked, spec, _selection())
    assert merged.entries[e].fields[f].alternatives == field.choices[:2]
    assert merged.entries[e].fields[f].state == "ambiguous"


def test_manual_rejects_nontext_missing_undeclared_or_wrong_profile() -> None:
    spec = installed_capture_page_specs()[0]
    baseline = _baseline()
    first_choice = next(
        (entry.entry_key, field.field_key)
        for entry in spec.entries
        for field in entry.fields
        if field.field_type == "choice"
    )
    for bad in (
        ManualTextSelection(*first_choice, "yes"),
        ManualTextSelection("bogus_entry", "notes", "yes"),
        ManualTextSelection("session_context", "bogus_field", "yes"),
    ):
        with pytest.raises(ManualStagingError):
            add_one_manual_text(baseline, spec, bad)
    with pytest.raises(ManualStagingError, match="manual_baseline_not_qualified"):
        add_one_manual_text(
            replace(baseline, profile=LOCAL_CANDIDATES_V1), spec, _selection()
        )
    with pytest.raises(ManualStagingError, match="manual_baseline_not_qualified"):
        add_one_manual_text(
            replace(baseline, layout_fingerprint="0" * 64), spec, _selection()
        )


def test_literal_caps_reject_whitespace_control_surrogate_and_oversize() -> None:
    for value in ("", " \t\n ", "ab\x00cd", "\ud800", "X" * 4001):
        with pytest.raises(ManualStagingError, match="invalid_manual_literal"):
            ManualTextSelection("entry_key", "field_key", value)
    spec = installed_capture_page_specs()[0]
    selection = _selection()
    maximum = next(
        field.max_characters
        for entry in spec.entries
        for field in entry.fields
        if entry.entry_key == selection.entry_key
        and field.field_key == selection.field_key
    )
    assert maximum is not None
    if maximum < 4000:
        with pytest.raises(
            ManualStagingError, match="manual_text_exceeds_historical_limit"
        ):
            add_one_manual_text(
                _baseline(),
                spec,
                replace(selection, literal="Z" * (maximum + 1)),
            )
    assert "literal='" not in repr(selection)


def test_tampered_mark_candidate_is_not_carried_forward() -> None:
    spec = installed_capture_page_specs()[0]
    base = _baseline()
    eidx, fidx, source = next(
        (i, j, field)
        for i, entry in enumerate(spec.entries)
        for j, field in enumerate(entry.fields)
        if field.field_type == "choice"
    )
    entries = list(base.entries)
    values = list(entries[eidx].fields)
    values[fidx] = FieldCandidate(
        source.field_key,
        source.region_key,
        "mark_recognition",
        "candidate_detected",
        literal="invented",
    )
    entries[eidx] = replace(entries[eidx], fields=tuple(values))
    with pytest.raises(ManualStagingError, match="unrecognized_mark_literal"):
        add_one_manual_text(replace(base, entries=tuple(entries)), spec, _selection())


class Authorized:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.operations: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.operations.append(operation)
        if class_id != "class_test" or not self.enabled:
            raise PermissionError("denied")

    def attribution(self) -> Mapping[str, object]:
        return {"type": "system_process", "process_id": "source_operator"}


def test_service_requires_trusted_gate_and_unchanged_source(tmp_path: Path) -> None:
    spec = installed_capture_page_specs()[0]
    baseline = _baseline()
    identity = tuple(spec.template_identity().items())

    class MockBatch:
        def _actor(self, authorization: Authorized) -> Mapping[str, object]:
            return dict(authorization.attribution())

    class MockPage:
        def __init__(self) -> None:
            self.calls = 0
            self.alter = False
            self.receipts = SimpleNamespace(batches=MockBatch())

        def resolve(self, *args: object, **kwargs: object) -> SimpleNamespace:
            self.calls += 1
            receipt_value = "changed" if self.alter and self.calls >= 2 else "stable"
            return SimpleNamespace(
                receipt=SimpleNamespace(to_dict=lambda: {"receipt": receipt_value}),
                plan=SimpleNamespace(layout=SimpleNamespace(layout_identity=identity)),
                retained=SimpleNamespace(page_identity=lambda n: ("scan", n)),
                source_page_number=2,
            )

    class MockMarks:
        def interpret(self, *args: object, **kwargs: object) -> LocalPageCandidates:
            assert kwargs["profile_identity"] == LOCAL_MARKS_V1.wire_identity()
            return baseline

    service = FileManualTextCandidateService(tmp_path)
    pages = MockPage()
    service.pages = pages  # type: ignore[assignment]
    service.marks = MockMarks()  # type: ignore[assignment]
    authorized = Authorized()
    outcome = service.transcribe_one(
        "class_test",
        "cbat_test",
        "prec_test",
        _selection(),
        authorization=authorized,
        profile_identity=LOCAL_ASSISTED_MARKS_V1.wire_identity(),
    )
    assert outcome.page.profile is LOCAL_ASSISTED_MARKS_V1
    assert outcome.operator == authorized.attribution()
    assert outcome.selected_entry_key == _selection().entry_key
    assert (
        authorized.operations.count("capture_interpretation.manual_transcription") == 2
    )
    assert (
        "As observed."
        in outcome.entry_map[outcome.selected_entry_key]["fields"][
            outcome.selected_field_key
        ]["candidate_literal"]
    )
    assert "As observed." not in repr(outcome)

    pages.calls = 0
    pages.alter = True
    with pytest.raises(ManualStagingError, match="manual_authority_changed"):
        service.transcribe_one(
            "class_test",
            "cbat_test",
            "prec_test",
            _selection(),
            authorization=authorized,
            profile_identity=LOCAL_ASSISTED_MARKS_V1.wire_identity(),
        )
    denied = Authorized(enabled=False)
    count = pages.calls
    with pytest.raises(PermissionError):
        service.transcribe_one(
            "class_test",
            "cbat_test",
            "prec_test",
            _selection(),
            authorization=denied,
            profile_identity=LOCAL_ASSISTED_MARKS_V1.wire_identity(),
        )
    assert pages.calls == count
    with pytest.raises(
        ManualStagingError, match="unsupported_manual_interpreter_profile"
    ):
        service.transcribe_one(
            "class_test",
            "cbat_test",
            "prec_test",
            _selection(),
            authorization=authorized,
            profile_identity=LOCAL_MARKS_V1.wire_identity(),
        )
