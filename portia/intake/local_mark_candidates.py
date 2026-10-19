"""#60 Slice 3A: source-faithful local checkbox candidates, never accepted facts.

Only an authorized FileMeasuredRegionService can provide real source crops.
The pure classifier is independently testable; it requires visibly measurable
printed checkbox frames, adequate resolution and unambiguous interior ink.
Unrecognized handwriting/text remains unreadable, NEVER blank or transcribed.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Literal, Mapping

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import (
    CaptureField,
    CapturePageSpec,
    CaptureRectangle,
    resolve_capture_page_spec,
)
from portia.intake.interpretation_profiles import LOCAL_MARKS_V1, InterpretationProfile
from portia.intake.measured_regions import (
    QUALIFIED_REGISTRATION_METHODS,
    FieldRegionPixels,
    FileMeasuredRegionService,
    MeasuredPageRegions,
)

RecognitionState = Literal[
    "blank", "unmarked", "unreadable", "ambiguous", "candidate_detected"
]
EntryState = Literal["blank", "unreadable", "candidate"]

_MAX_MARK_FIELDS = 120
_MIN_BOX_PIXELS = 12
_MIN_FRAME_DARK_RATIO = 0.29
_STRONG_INK_FRACTION = 0.13
_WEAK_INK_FRACTION = 0.025


class LocalRecognitionError(ValueError):
    """Stable failure code; never include source content or local paths."""


@dataclass(frozen=True, slots=True)
class FieldCandidate:
    field_key: str
    region_key: str
    capture_method: Literal[
        "handwriting_recognition", "manual_transcription", "mark_recognition"
    ]
    state: RecognitionState
    literal: str | None = None
    alternatives: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state == "candidate_detected":
            if not self.literal or self.alternatives:
                raise LocalRecognitionError("invalid_detected_candidate")
        elif self.state == "ambiguous":
            if self.literal is not None or not 2 <= len(self.alternatives) <= 16:
                raise LocalRecognitionError("invalid_ambiguous_candidate")
            if len(set(self.alternatives)) != len(self.alternatives):
                raise LocalRecognitionError("duplicate_mark_alternatives")
        elif self.literal is not None or self.alternatives:
            raise LocalRecognitionError("noncandidate_cannot_have_literal")

    def to_wire(self) -> dict[str, object]:
        """Exact paper_interpretation@1 field vocabulary, not a persisted record."""
        item: dict[str, object] = {
            "capture_method": self.capture_method,
            "region_key": self.region_key,
            "recognition_state": self.state,
        }
        if self.literal is not None:
            item["candidate_literal"] = self.literal
        if self.alternatives:
            item["alternatives"] = [
                {"candidate_literal": value} for value in self.alternatives
            ]
        return item


@dataclass(frozen=True, slots=True)
class EntryCandidates:
    entry_key: str
    state: EntryState
    fields: tuple[FieldCandidate, ...]

    def to_wire(self) -> dict[str, object]:
        data: dict[str, object] = {"entry_state": self.state}
        if self.state == "candidate":
            data["fields"] = {item.field_key: item.to_wire() for item in self.fields}
        return data


@dataclass(frozen=True, slots=True)
class LocalPageCandidates:
    """Ephemeral, not a paper_interpretation record or a review decision."""

    source_page_number: int
    layout_fingerprint: str
    profile: InterpretationProfile
    registration_method: str
    entries: tuple[EntryCandidates, ...] = dataclass_field(repr=False)
    limitation_codes: tuple[str, ...] = ()

    @property
    def interpretation_status(self) -> Literal["complete", "partial"]:
        return "partial" if self.limitation_codes else "complete"

    def entry_map(self) -> dict[str, dict[str, object]]:
        return {entry.entry_key: entry.to_wire() for entry in self.entries}


def _pixel(region: FieldRegionPixels, x: int, y: int) -> int:
    return region.pixels[y * region.width + x]


def _box_intervals(
    box: CaptureRectangle, field_rect: CaptureRectangle, region: FieldRegionPixels
) -> tuple[int, int, int, int] | None:
    scale_x = region.width / field_rect.width
    scale_y = region.height / field_rect.height
    x0 = round((box.x - field_rect.x) * scale_x)
    y0 = round((box.y - field_rect.y) * scale_y)
    x1 = round((box.right - field_rect.x) * scale_x)
    y1 = round((box.bottom - field_rect.y) * scale_y)
    if (
        x0 < 0
        or y0 < 0
        or x1 >= region.width
        or y1 >= region.height
        or x1 - x0 < _MIN_BOX_PIXELS
        or y1 - y0 < _MIN_BOX_PIXELS
    ):
        return None
    return x0, y0, x1, y1


def _edge_strength(
    region: FieldRegionPixels, x0: int, y0: int, x1: int, y1: int
) -> tuple[float, ...]:
    """Require observed print frame on all four sides, not merely light paper."""
    midx = range(x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4)
    midy = range(y0 + (y1 - y0) // 4, y1 - (y1 - y0) // 4)
    strengths = []
    for side in range(4):
        best = 0.0
        for offset in (0, 1, 2):
            if side == 0:
                samples = [_pixel(region, x, y0 + offset) for x in midx]
            elif side == 1:
                samples = [_pixel(region, x, y1 - offset) for x in midx]
            elif side == 2:
                samples = [_pixel(region, x0 + offset, y) for y in midy]
            else:
                samples = [_pixel(region, x1 - offset, y) for y in midy]
            if samples:
                best = max(best, sum(v < 125 for v in samples) / len(samples))
        strengths.append(best)
    return tuple(strengths)


def _interior_ink(
    region: FieldRegionPixels, x0: int, y0: int, x1: int, y1: int
) -> tuple[float, float]:
    dx, dy = x1 - x0, y1 - y0
    xlo, xhi = x0 + round(dx * 0.29), x0 + round(dx * 0.71)
    ylo, yhi = y0 + round(dy * 0.29), y0 + round(dy * 0.71)
    samples = [_pixel(region, x, y) for y in range(ylo, yhi) for x in range(xlo, xhi)]
    if not samples:
        return 0.0, 1.0
    dark = sum(value < 115 for value in samples) / len(samples)
    possibly_ink = sum(115 <= value < 232 for value in samples) / len(samples)
    return dark, possibly_ink


def _read_mark(field: CaptureField, region: FieldRegionPixels) -> FieldCandidate:
    """No probability/negative inference: inspect exact printed checkbox interiors."""
    if field.field_type != "choice" or field.capture_method != "mark_recognition":
        raise LocalRecognitionError("not_a_declared_choice_region")
    if len(field.choices) < 2 or len(field.choices) > 5:
        raise LocalRecognitionError("unsupported_choice_inventory")
    rect = field.rectangle
    unit = (rect.width - 12) // len(field.choices)
    observed: list[str] = []
    uncertain = False
    for index, token in enumerate(field.choices):
        checkbox = CaptureRectangle(rect.x + 6 + index * unit, rect.y + 13, 8, 8)
        bounds = _box_intervals(checkbox, rect, region)
        if bounds is None:
            uncertain = True
            continue
        if min(_edge_strength(region, *bounds)) < _MIN_FRAME_DARK_RATIO:
            uncertain = True
            continue
        dark, gray = _interior_ink(region, *bounds)
        if dark >= _STRONG_INK_FRACTION:
            observed.append(token)
        elif dark >= _WEAK_INK_FRACTION or gray >= 0.11:
            uncertain = True
    if uncertain:
        return FieldCandidate(
            field.field_key, field.region_key, "mark_recognition", "unreadable"
        )
    if len(observed) >= 2:
        return FieldCandidate(
            field.field_key,
            field.region_key,
            "mark_recognition",
            "ambiguous",
            alternatives=tuple(observed),
        )
    if observed:
        return FieldCandidate(
            field.field_key,
            field.region_key,
            "mark_recognition",
            "candidate_detected",
            literal=observed[0],
        )
    return FieldCandidate(
        field.field_key, field.region_key, "mark_recognition", "unmarked"
    )


def interpret_registered_fields(
    regions: MeasuredPageRegions, spec: CapturePageSpec
) -> LocalPageCandidates:
    """Pure local classifier; callers MUST obtain pixels through authorized service.

    A fabricated MeasuredPageRegions object is NOT class/access/source evidence.
    No network, OCR, transcript, roster or domain inference happens here.
    """
    if not isinstance(regions, MeasuredPageRegions) or not isinstance(
        spec, CapturePageSpec
    ):
        raise LocalRecognitionError("invalid_recognition_inputs")
    if resolve_capture_page_spec(spec.template_identity()) != spec:
        raise LocalRecognitionError("historical_spec_not_installed")
    if regions.layout_fingerprint != spec.layout_fingerprint:
        raise LocalRecognitionError("layout_fingerprint_conflict")
    if regions.registration.method not in QUALIFIED_REGISTRATION_METHODS:
        raise LocalRecognitionError("unqualified_registration_provider")
    declared = {
        (entry.entry_key, field.field_key, field.region_key): field
        for entry in spec.entries
        for field in entry.fields
    }
    if len(declared) > _MAX_MARK_FIELDS or len(regions.fields) != len(declared):
        raise LocalRecognitionError("field_inventory_mismatch")
    indexed: dict[tuple[str, str, str], FieldRegionPixels] = {}
    for region in regions.fields:
        identity = (region.entry_key, region.field_key, region.region_key)
        if identity not in declared or identity in indexed:
            raise LocalRecognitionError("field_identity_conflict")
        indexed[identity] = region
    if set(indexed) != set(declared):
        raise LocalRecognitionError("field_inventory_mismatch")
    limitations: set[str] = set()
    entries: list[EntryCandidates] = []
    for entry in spec.entries:
        candidates: list[FieldCandidate] = []
        for field in entry.fields:
            region = indexed[(entry.entry_key, field.field_key, field.region_key)]
            if field.field_type == "choice":
                detected = _read_mark(field, region)
                if detected.state == "unreadable":
                    limitations.add("mark_quality_insufficient")
            else:
                detected = FieldCandidate(
                    field.field_key,
                    field.region_key,
                    field.capture_method,
                    "unreadable",
                )
                limitations.add("text_provider_unavailable")
            candidates.append(detected)
        states = {candidate.state for candidate in candidates}
        state: EntryState
        if "candidate_detected" in states or "ambiguous" in states:
            state = "candidate"
        elif "unreadable" in states:
            state = "unreadable"
        else:
            state = "blank"  # All verified checkboxes unmarked; never a negative fact.
        entries.append(EntryCandidates(entry.entry_key, state, tuple(candidates)))
    return LocalPageCandidates(
        regions.source_page_number,
        regions.layout_fingerprint,
        LOCAL_MARKS_V1,
        regions.registration.method,
        tuple(entries),
        tuple(sorted(limitations)),
    )


class FileLocalMarkCandidateService:
    """The only production doorway: exact #59/#60 custody, region CV, reread."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.regions = FileMeasuredRegionService(workspace_root)

    def interpret(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
        profile_identity: Mapping[str, object],
    ) -> LocalPageCandidates:
        if dict(profile_identity) != LOCAL_MARKS_V1.wire_identity():
            raise LocalRecognitionError("unsupported_mark_interpreter_profile")
        # The first protected read and the last read both require class authority.
        source = self.regions.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        spec = resolve_capture_page_spec(dict(source.plan.layout.layout_identity))
        extracted = self.regions.extract(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        interpreted = interpret_registered_fields(extracted, spec)
        verified = self.regions.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        if (
            source.receipt.to_dict() != verified.receipt.to_dict()
            or source.plan != verified.plan
            or source.retained.page_identity(source.source_page_number)
            != verified.retained.page_identity(verified.source_page_number)
        ):
            raise LocalRecognitionError("authority_changed_during_recognition")
        return interpreted
