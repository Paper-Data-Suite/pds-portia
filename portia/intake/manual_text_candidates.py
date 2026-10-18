"""#60 Slice 3B: attributed, one-region manual transcription as staging only.

The operator explicitly selects a declared historical text field and supplies
its literal content. The source stays under Core custody. This is neither OCR,
nor an attributable Capture Review, nor canonical record materialization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import CapturePageSpec, resolve_capture_page_spec
from portia.intake.historical_page_regions import FileHistoricalPageRegionService
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_MARKS_V1,
)
from portia.intake.local_mark_candidates import (
    EntryCandidates,
    EntryState,
    FieldCandidate,
    FileLocalMarkCandidateService,
    LocalPageCandidates,
)

_MAX_MANUAL_LITERAL = 4000
_KEY = re.compile(r"[a-z][a-z0-9_]*\Z")


class ManualStagingError(ValueError):
    """Privacy-safe failure identifier without any user-supplied literal."""


@dataclass(frozen=True, slots=True)
class ManualTextSelection:
    """Explicitly selected historical text region and unmodified literal."""

    entry_key: str
    field_key: str
    literal: str = field(repr=False)

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or _KEY.fullmatch(value) is None
            for value in (self.entry_key, self.field_key)
        ):
            raise ManualStagingError("invalid_manual_field_selection")
        if (
            not isinstance(self.literal, str)
            or not 1 <= len(self.literal) <= _MAX_MANUAL_LITERAL
            or not self.literal.strip()
            or any(
                (ord(char) < 32 and char not in "\t\n\r")
                or ord(char) == 127
                or 0xD800 <= ord(char) <= 0xDFFF
                for char in self.literal
            )
        ):
            raise ManualStagingError("invalid_manual_literal")


@dataclass(frozen=True, slots=True)
class AttributedManualPage:
    """Ephemeral candidate + trusted operator, not paper_interpretation@1 yet."""

    page: LocalPageCandidates = field(repr=False)
    operator: Mapping[str, object] = field(repr=False)
    selected_entry_key: str
    selected_field_key: str

    @property
    def entry_map(self) -> dict[str, dict[str, object]]:
        return self.page.entry_map()


def _validate_unmodified_mark_baseline(
    baseline: LocalPageCandidates, spec: CapturePageSpec
) -> None:
    if resolve_capture_page_spec(spec.template_identity()) is not spec:
        raise ManualStagingError("manual_historical_spec_conflict")
    if (
        not isinstance(baseline, LocalPageCandidates)
        or not isinstance(spec, CapturePageSpec)
        or baseline.profile is not LOCAL_MARKS_V1
        or baseline.layout_fingerprint != spec.layout_fingerprint
        or baseline.registration_method != "measured_sheet_boundary_and_exact_qr_v1"
        or len(baseline.entries) != len(spec.entries)
    ):
        raise ManualStagingError("manual_baseline_not_qualified")
    for observed, declared in zip(baseline.entries, spec.entries, strict=True):
        if observed.entry_key != declared.entry_key or len(observed.fields) != len(
            declared.fields
        ):
            raise ManualStagingError("manual_field_inventory_conflict")
        for current, original in zip(observed.fields, declared.fields, strict=True):
            if (
                current.field_key != original.field_key
                or current.region_key != original.region_key
                or current.capture_method != original.capture_method
            ):
                raise ManualStagingError("manual_field_inventory_conflict")
            if original.field_type == "text" and current.state != "unreadable":
                raise ManualStagingError("unexpected_prior_text_candidate")
            if original.field_type == "choice":
                if (
                    current.literal is not None
                    and current.literal not in original.choices
                ):
                    raise ManualStagingError("unrecognized_mark_literal")
                if any(value not in original.choices for value in current.alternatives):
                    raise ManualStagingError("unrecognized_mark_alternative")


def add_one_manual_text(
    baseline: LocalPageCandidates,
    spec: CapturePageSpec,
    selection: ManualTextSelection,
) -> LocalPageCandidates:
    """Pure replacement of one previously unreadable text source field.

    This does not patch a persisted interpretation generation. The caller must
    create a NEW explicitly profiled generation in a later storage slice.
    """
    if not isinstance(selection, ManualTextSelection):
        raise ManualStagingError("manual_selection_required")
    _validate_unmodified_mark_baseline(baseline, spec)
    found = False
    rebuilt: list[EntryCandidates] = []
    for entry, declared in zip(baseline.entries, spec.entries, strict=True):
        fields: list[FieldCandidate] = []
        for candidate, source_field in zip(entry.fields, declared.fields, strict=True):
            if (
                entry.entry_key == selection.entry_key
                and source_field.field_key == selection.field_key
            ):
                if found or source_field.field_type != "text":
                    raise ManualStagingError("manual_target_not_text")
                if source_field.capture_method not in {
                    "manual_transcription",
                    "handwriting_recognition",
                }:
                    raise ManualStagingError("manual_source_method_unsupported")
                if (
                    source_field.max_characters is None
                    or len(selection.literal) > source_field.max_characters
                ):
                    raise ManualStagingError("manual_text_exceeds_historical_limit")
                found = True
                candidate = FieldCandidate(
                    field_key=candidate.field_key,
                    region_key=candidate.region_key,
                    capture_method="manual_transcription",
                    state="candidate_detected",
                    literal=selection.literal,
                )
            fields.append(candidate)
        state: EntryState
        if any(item.state in {"candidate_detected", "ambiguous"} for item in fields):
            state = "candidate"
        elif any(item.state == "unreadable" for item in fields):
            state = "unreadable"
        else:
            state = "blank"
        rebuilt.append(EntryCandidates(entry.entry_key, state, tuple(fields)))
    if not found:
        raise ManualStagingError("manual_field_not_in_historical_layout")
    limitations = set(baseline.limitation_codes)
    if all(
        item.state != "unreadable"
        for entry, declared in zip(rebuilt, spec.entries, strict=True)
        for item, source in zip(entry.fields, declared.fields, strict=True)
        if source.field_type == "text"
    ):
        limitations.discard("text_provider_unavailable")
    return replace(
        baseline,
        profile=LOCAL_ASSISTED_MARKS_V1,
        entries=tuple(rebuilt),
        limitation_codes=tuple(sorted(limitations)),
    )


class FileManualTextCandidateService:
    """Authorize, reverify Core source/route, stage one operator literal only."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.pages = FileHistoricalPageRegionService(workspace_root)
        self.marks = FileLocalMarkCandidateService(workspace_root)

    def transcribe_one(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        selection: ManualTextSelection,
        *,
        authorization: CaptureAuthorization,
        profile_identity: Mapping[str, object],
    ) -> AttributedManualPage:
        if not isinstance(selection, ManualTextSelection):
            raise ManualStagingError("manual_selection_required")
        if (
            not isinstance(profile_identity, Mapping)
            or dict(profile_identity) != LOCAL_ASSISTED_MARKS_V1.wire_identity()
        ):
            raise ManualStagingError("unsupported_manual_interpreter_profile")
        if (
            authorization is None
            or not callable(getattr(authorization, "require_access", None))
            or not callable(getattr(authorization, "attribution", None))
        ):
            raise TypeError("trusted CaptureAuthorization required")
        # Protect class-sensitive reads and preserve trusted operator provenance.
        authorization.require_access(
            class_id, "capture_interpretation.manual_transcription"
        )
        operator = self.pages.receipts.batches._actor(authorization)
        before = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        spec = resolve_capture_page_spec(dict(before.plan.layout.layout_identity))
        # Mark provider remains separately versioned. It must NOT recognize text.
        baseline = self.marks.interpret(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=LOCAL_MARKS_V1.wire_identity(),
        )
        result = add_one_manual_text(baseline, spec, selection)
        authorization.require_access(
            class_id, "capture_interpretation.manual_transcription"
        )
        after = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        if (
            before.receipt.to_dict() != after.receipt.to_dict()
            or before.plan != after.plan
            or before.retained.page_identity(before.source_page_number)
            != after.retained.page_identity(after.source_page_number)
            or baseline.source_page_number != after.source_page_number
            or result.layout_fingerprint
            != dict(after.plan.layout.layout_identity).get("layout_fingerprint")
            or operator != self.pages.receipts.batches._actor(authorization)
        ):
            raise ManualStagingError("manual_authority_changed")
        return AttributedManualPage(
            result, operator, selection.entry_key, selection.field_key
        )
