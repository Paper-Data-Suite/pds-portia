"""#60 Slice 4B: restart-safe, read-only immutable interpretation history.

A history is keyed by an already persisted Page Record; neither a caller's
candidate, a bare QR, nor an interpretation filename establishes provenance.
Every read checks Core retention, historical Page Target, active route, profile
and exact entry/field semantics. No source text appears in ordinary summaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, cast

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import (
    CaptureEntry,
    CaptureField,
    CapturePageSpec,
    resolve_capture_page_spec,
)
from portia.intake.historical_page_regions import AuthorizedHistoricalPage
from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
    InterpretationGenerationError,
    _require_same_page,
)
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_MARKS_V1,
    InterpretationProfile,
    resolve_interpretation_profile,
)
from portia.models import PaperInterpretationV1
from portia.storage.errors import PortiaCorruptionError


@dataclass(frozen=True, slots=True)
class InterpretationHistory:
    """Authorized history: candidate literals are hidden from repr and summary.

    Records are inspectable by an explicitly authorized caller, but this object
    is neither review approval nor a materialization instruction.
    """

    page_record_id: str
    source_page_number: int
    records: tuple[PaperInterpretationV1, ...] = field(repr=False)

    @property
    def generation_count(self) -> int:
        return len(self.records)

    @property
    def latest(self) -> PaperInterpretationV1 | None:
        return self.records[-1] if self.records else None

    @property
    def needs_attention(self) -> bool:
        return (
            self.latest is not None
            and self.latest.field("interpretation_status") == "partial"
        )

    def summary(self) -> dict[str, object]:
        """No scan paths, OCR literals, actor detail, field content, or raw QR."""
        return {
            "page_record_id": self.page_record_id,
            "source_page_number": self.source_page_number,
            "generation_count": self.generation_count,
            "current_generation": self.latest.field("generation")
            if self.latest
            else None,
            "current_status": self.latest.field("interpretation_status")
            if self.latest
            else "not_interpreted",
            "needs_attention": self.needs_attention,
        }


def _require_field(
    value: object, declared: CaptureField, profile: InterpretationProfile
) -> str:
    if not isinstance(value, dict):
        raise PortiaCorruptionError("interpretation_field_not_object")
    if value.get("region_key") != declared.region_key:
        raise PortiaCorruptionError("interpretation_region_key_conflict")
    state = value.get("recognition_state")
    literal = value.get("candidate_literal")
    alternatives = value.get("alternatives")
    method = value.get("capture_method")
    if declared.field_type == "choice":
        if method != "mark_recognition" or state not in {
            "unmarked",
            "unreadable",
            "ambiguous",
            "candidate_detected",
        }:
            raise PortiaCorruptionError(
                "interpretation_choice_method_or_state_conflict"
            )
        if profile.mark_provider != "local_checkbox_v1" and state != "unreadable":
            raise PortiaCorruptionError("interpretation_mark_provider_not_qualified")
        if state == "candidate_detected" and literal not in declared.choices:
            raise PortiaCorruptionError("interpretation_unknown_mark_choice")
        if state == "ambiguous":
            if not isinstance(alternatives, list) or len(alternatives) > len(
                declared.choices
            ):
                raise PortiaCorruptionError("interpretation_mark_alternatives_conflict")
            choices = [
                item.get("candidate_literal")
                for item in alternatives
                if isinstance(item, dict)
            ]
            if len(choices) != len(alternatives) or any(
                token not in declared.choices for token in choices
            ):
                raise PortiaCorruptionError("interpretation_unknown_mark_alternative")
    else:
        if method == "manual_transcription" and state == "candidate_detected":
            if profile is not LOCAL_ASSISTED_MARKS_V1:
                raise PortiaCorruptionError("interpretation_manual_profile_conflict")
            if (
                not isinstance(literal, str)
                or declared.max_characters is None
                or len(literal) > declared.max_characters
            ):
                raise PortiaCorruptionError("interpretation_manual_literal_limit")
        elif method == declared.capture_method and state == "unreadable":
            # The historical form may *declare* a manual-transcription field,
            # but an unreadable candidate is not a claimed manual operation.
            if profile.text_provider != "none":
                raise PortiaCorruptionError(
                    "interpretation_unqualified_text_recognition"
                )
        else:
            raise PortiaCorruptionError("interpretation_text_method_conflict")
    return cast(str, state)


def _require_entry(
    saved: object, declared: CaptureEntry, profile: InterpretationProfile
) -> None:
    if not isinstance(saved, dict):
        raise PortiaCorruptionError("interpretation_entry_not_object")
    state = saved.get("entry_state")
    mapped = saved.get("mapped_record_kind")
    if mapped is not None and (
        len(declared.permitted_mapped_record_kinds) != 1
        or mapped != declared.permitted_mapped_record_kinds[0]
    ):
        raise PortiaCorruptionError("interpretation_mapping_not_declared")
    if state != "candidate":
        if state not in ("blank", "unreadable") or "fields" in saved:
            raise PortiaCorruptionError("interpretation_entry_state_conflict")
        return
    fields = saved.get("fields")
    if not isinstance(fields, dict) or set(fields) != {
        item.field_key for item in declared.fields
    }:
        raise PortiaCorruptionError("interpretation_field_inventory_conflict")
    states = [
        _require_field(fields[field.field_key], field, profile)
        for field in declared.fields
    ]
    if not any(item in {"candidate_detected", "ambiguous"} for item in states):
        raise PortiaCorruptionError("interpretation_candidate_without_detection")


def _require_historical_entries(
    record: PaperInterpretationV1, spec: CapturePageSpec, profile: InterpretationProfile
) -> None:
    saved = record.to_dict()
    entries = saved.get("entries")
    if not isinstance(entries, dict) or set(entries) != {
        entry.entry_key for entry in spec.entries
    }:
        raise PortiaCorruptionError("interpretation_entry_inventory_conflict")
    for declared in spec.entries:
        _require_entry(entries[declared.entry_key], declared, profile)
    if saved.get("interpretation_status") == "complete" and saved.get(
        "limitation_codes"
    ):
        raise PortiaCorruptionError("interpretation_complete_has_limitations")
    if saved.get("interpretation_status") == "partial" and not saved.get(
        "limitation_codes"
    ):
        raise PortiaCorruptionError("interpretation_partial_without_limitations")


class FilePaperInterpretationHistoryService:
    """Recover candidate history without mutating the batch or Core original."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.generations = FilePaperInterpretationGenerationService(workspace_root)

    def history(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> InterpretationHistory:
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization required")
        authorization.require_access(class_id, "capture_interpretation.history")
        # The receipt and retained source are reloaded before any interpretation
        # inventory read. Profile selection cannot bypass this authority.
        page = self._page(
            class_id, work_id, page_record_id, authorization=authorization
        )
        history = self._read(page)
        # Double read detects ordinary concurrent mutation without taking a
        # write lock or creating a temporary sidecar. Never report a drifting view.
        if history != self._read(page):
            raise InterpretationGenerationError(
                "interpretation_history_changed_during_read"
            )
        last = self._page(
            class_id, work_id, page_record_id, authorization=authorization
        )
        _require_same_page(page, last)
        return InterpretationHistory(page_record_id, page.source_page_number, history)

    def _page(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> AuthorizedHistoricalPage:
        return self.generations.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=LOCAL_MARKS_V1.wire_identity(),
        )

    def _read(
        self, page: AuthorizedHistoricalPage
    ) -> tuple[PaperInterpretationV1, ...]:
        all_records = self.generations._inventory(page.class_id, page.work_id)
        records = [
            record
            for record in all_records
            if record.field("page_record_id") == page.page_record_id
        ]
        ordered = sorted(records, key=lambda item: cast(int, item.field("generation")))
        if tuple(item.field("generation") for item in ordered) != tuple(
            range(1, len(ordered) + 1)
        ):
            raise PortiaCorruptionError(
                "interpretation_generation_history_gap_or_duplicate"
            )
        spec = resolve_capture_page_spec(dict(page.plan.layout.layout_identity))
        seen: set[tuple[str, ...]] = set()
        for saved in ordered:
            profile = resolve_interpretation_profile(
                cast(Mapping[str, object], saved.to_dict()["interpreter_profile"])
            )
            self.generations._lineage(saved, page, profile)
            identity = tuple(profile.wire_identity().values())
            if identity in seen:
                raise PortiaCorruptionError("duplicate_interpretation_profile_history")
            seen.add(identity)
            _require_historical_entries(saved, spec, profile)
        return tuple(ordered)
