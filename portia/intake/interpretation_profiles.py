"""#60 Slice 1: exact, read-only authority for paper interpretation profiles.

A printed capture method specifies what a field *expects*, not what a machine
has successfully recognized. This module does not access scan content, select
students, perform recognition, create proposals, or write persistent records.
Later providers must be introduced with an explicit profile-version decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from portia.capture.form_catalog import (
    CapturePageSpec,
    CaptureRectangle,
    installed_capture_page_specs,
    resolve_capture_page_spec,
)
from portia.models import PageTargetV2

# Only these four wire keys are allowed in paper_interpretation@1's profile.
# Backends and policy flags belong in the pinned local registry, not the wire.
_INTERPRETER_ID = "portia_local_candidates"
_INTERPRETER_VERSION = "1"
_MAPPING_PROFILE_ID = "portia_capture_roles"
_MAPPING_VERSION = "1"

FieldAvailability = Literal["unavailable"]
ManualAvailability = Literal["not_yet_implemented"]
MappingDisposition = Literal[
    "context_only", "requires_target_choice", "mapping_not_yet_implemented"
]


class InterpretationProfileError(ValueError):
    """No exact, supported historical interpretation profile is available."""


@dataclass(frozen=True, slots=True)
class InterpretationProfile:
    """Finite local profile; an identity is never a floating `latest` alias.

    Scan acquisition/QR support in #59 does NOT count as handwriting/mark OCR.
    No cloud/OCR service may be selected implicitly from installed packages.
    """

    interpreter_id: str
    interpreter_version: str
    mapping_profile_id: str
    mapping_version: str
    text_provider: Literal["none"]
    mark_provider: Literal["none", "local_checkbox_v1"]
    manual_provider: ManualAvailability
    external_network_allowed: Literal[False]

    def wire_identity(self) -> dict[str, str]:
        """Exactly the frozen PaperInterpretationV1 interpreter_profile keys."""
        return {
            "interpreter_id": self.interpreter_id,
            "interpreter_version": self.interpreter_version,
            "mapping_profile_id": self.mapping_profile_id,
            "mapping_version": self.mapping_version,
        }


LOCAL_CANDIDATES_V1 = InterpretationProfile(
    interpreter_id=_INTERPRETER_ID,
    interpreter_version=_INTERPRETER_VERSION,
    mapping_profile_id=_MAPPING_PROFILE_ID,
    mapping_version=_MAPPING_VERSION,
    text_provider="none",
    mark_provider="none",
    manual_provider="not_yet_implemented",
    external_network_allowed=False,
)


# Separate immutable identity: never silently add marks to older v1 profile.
LOCAL_MARKS_V1 = InterpretationProfile(
    interpreter_id="portia_local_marks",
    interpreter_version="1",
    mapping_profile_id=_MAPPING_PROFILE_ID,
    mapping_version=_MAPPING_VERSION,
    text_provider="none",
    mark_provider="local_checkbox_v1",
    manual_provider="not_yet_implemented",
    external_network_allowed=False,
)


def resolve_interpretation_profile(
    identity: Mapping[str, object],
) -> InterpretationProfile:
    """Only exact, pinned profiles. No floating versions or fallback."""
    if not isinstance(identity, Mapping):
        raise InterpretationProfileError("unsupported_interpreter_or_mapping_profile")
    for profile in (LOCAL_CANDIDATES_V1, LOCAL_MARKS_V1):
        if dict(identity) == profile.wire_identity():
            return profile
    raise InterpretationProfileError("unsupported_interpreter_or_mapping_profile")


@dataclass(frozen=True, slots=True)
class CaptureFieldSupport:
    """Exact source field; recognition support is separate from form intent."""

    field_key: str
    region_key: str
    label: str
    field_type: Literal["text", "choice"]
    declared_method: Literal[
        "handwriting_recognition", "manual_transcription", "mark_recognition"
    ]
    rectangle: CaptureRectangle
    max_characters: int | None
    choices: tuple[str, ...]
    automatic_availability: FieldAvailability
    manual_availability: ManualAvailability


@dataclass(frozen=True, slots=True)
class CaptureEntrySupport:
    entry_key: str
    source_role: str
    permitted_mapped_record_kinds: tuple[str, ...]
    mapping_disposition: MappingDisposition
    fields: tuple[CaptureFieldSupport, ...]


@dataclass(frozen=True, slots=True)
class CaptureLayoutSupport:
    """Support matrix for exactly one frozen physical paper layout."""

    form_id: str
    label: str
    page_role: str
    page_ordinal: int
    context_entry_key: str
    layout_identity: tuple[tuple[str, str | int], ...]
    entries: tuple[CaptureEntrySupport, ...]

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def field_count(self) -> int:
        return sum(len(entry.fields) for entry in self.entries)


@dataclass(frozen=True, slots=True)
class HistoricalInterpretationPlan:
    """Read-only plan, NOT proof of authorization or retained-page custody.

    Slice 2 must independently authorize and reload the persisted Page Target,
    Batch, Page Record, route, and Core-retained scan *before* using this plan.
    """

    profile: InterpretationProfile
    layout: CaptureLayoutSupport


def _entry_disposition(
    source_role: str, permitted: tuple[str, ...]
) -> MappingDisposition:
    if source_role.endswith("_context") or source_role == "session_context":
        if permitted:
            raise InterpretationProfileError("context_must_not_map_to_domain")
        return "context_only"
    if not permitted or len(permitted) > 1:
        return "requires_target_choice"
    # Only a target-kind hint: no field-to-contract paths or proposal writing.
    return "mapping_not_yet_implemented"


def support_for_capture_spec(spec: CapturePageSpec) -> CaptureLayoutSupport:
    """Inventory only a catalog-authenticated, exact historical layout.

    A caller-produced lookalike is rejected even if its field keys happen to
    match a known form. A changed fingerprint is an unsupported old/new layout.
    """
    if not isinstance(spec, CapturePageSpec):
        raise InterpretationProfileError("historical_capture_spec_required")
    exact = resolve_capture_page_spec(spec.template_identity())
    if exact is not spec:
        raise InterpretationProfileError("untrusted_capture_spec_instance")
    entries: list[CaptureEntrySupport] = []
    for entry in exact.entries:
        fields = tuple(
            CaptureFieldSupport(
                field_key=field.field_key,
                region_key=field.region_key,
                label=field.label,
                field_type=field.field_type,
                declared_method=field.capture_method,
                rectangle=field.rectangle,
                max_characters=field.max_characters,
                choices=field.choices,
                automatic_availability="unavailable",
                manual_availability="not_yet_implemented",
            )
            for field in entry.fields
        )
        entries.append(
            CaptureEntrySupport(
                entry_key=entry.entry_key,
                source_role=entry.source_role,
                permitted_mapped_record_kinds=entry.permitted_mapped_record_kinds,
                mapping_disposition=_entry_disposition(
                    entry.source_role, entry.permitted_mapped_record_kinds
                ),
                fields=fields,
            )
        )
    if not entries or entries[0].entry_key != exact.context_entry_key:
        raise InterpretationProfileError("historical_context_layout_invalid")
    return CaptureLayoutSupport(
        form_id=exact.form_id,
        label=exact.label,
        page_role=exact.page_role,
        page_ordinal=exact.page_ordinal,
        context_entry_key=exact.context_entry_key,
        layout_identity=tuple(exact.template_identity().items()),
        entries=tuple(entries),
    )


def inventory_historical_layout_support() -> tuple[CaptureLayoutSupport, ...]:
    """All ten installed historical layouts; never generic fallbacks."""
    return tuple(
        support_for_capture_spec(spec) for spec in installed_capture_page_specs()
    )


def plan_historical_interpretation(
    page_target: object,
    *,
    profile_identity: Mapping[str, object],
) -> HistoricalInterpretationPlan:
    """Pure exact-version planner, NOT eligibility or authorization.

    Historical PageTargetV1 lacks the v2 seven-element capture/layout binding
    required by #58. Do not infer it from a matching form name or latest spec.
    """
    profile = resolve_interpretation_profile(profile_identity)
    if not isinstance(page_target, PageTargetV2):
        raise InterpretationProfileError("page_target_v1_not_interpretable")
    raw = page_target.to_dict()
    identity = raw.get("template_identity")
    if not isinstance(identity, dict):
        raise InterpretationProfileError("historical_template_identity_missing")
    spec = resolve_capture_page_spec(identity)
    # This independently checks entry keys, purpose, status and context policy.
    spec.assert_page_target_exact(page_target)
    return HistoricalInterpretationPlan(
        profile=profile, layout=support_for_capture_spec(spec)
    )
