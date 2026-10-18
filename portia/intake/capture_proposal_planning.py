"""#60 Slice 5A: exact, read-only Capture Proposal mapping readiness.

A plan is neither a persisted capture_proposal@1 nor human review. The only
production entry point reopens the immutable interpretation via the trusted
Page Record/history reader. No caller-supplied field values, QR text or target
path can select a canonical family or create a domain record.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Mapping

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import CapturePageSpec, resolve_capture_page_spec
from portia.intake.interpretation_history import FilePaperInterpretationHistoryService
from portia.models import PaperInterpretationV1
from portia.models.schema_runtime import load_runtime_contract_bundle, schema_id_for

EntryDisposition = Literal["proposable", "needs_attention", "context_only", "blank"]
_MAX_ENTRIES = 24
_MAX_FIELDS = 128
_MAPPING_PROFILE = ("portia_capture_roles", "1")
# Historical, intentional and contract-checked. These are not fuzzy matches.
_EVENT_SUMMARY_FIELD: dict[tuple[str, str], str] = {
    ("event_information", "event_information"): "observed_description",
    ("multi_event_information", "event_information"): "what_happened",
}


class ProposalPlanningError(ValueError):
    """A stable privacy-minimized refusal code (never a source literal)."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PlannedFieldBinding:
    """Exact supported target field and source field; no candidate value."""

    target_path: Literal["/summary"]
    field_key: str
    value_source: Literal["candidate_literal"]

    def to_wire(self) -> dict[str, object]:
        return {
            "target_path": self.target_path,
            "source_field": {
                "field_key": self.field_key,
                "value_source": self.value_source,
            },
        }


@dataclass(frozen=True, slots=True)
class ProposedTargetMapping:
    """The exact v1 proposal target shape; not a canonical Event."""

    record_kind: Literal["event"]
    contract_version: Literal["1"]
    context_kind: Literal["new_work"]
    bindings: tuple[PlannedFieldBinding, ...]
    review_flags: tuple[str, ...]

    def target_wire(self) -> dict[str, object]:
        return {
            "record_kind": self.record_kind,
            "contract_version": self.contract_version,
            "context": {"kind": self.context_kind},
        }

    def binding_wire(self) -> list[dict[str, object]]:
        return [binding.to_wire() for binding in self.bindings]


@dataclass(frozen=True, slots=True)
class EntryProposalReadiness:
    entry_key: str
    disposition: EntryDisposition
    attention_codes: tuple[str, ...] = ()
    mapping: ProposedTargetMapping | None = None

    def __post_init__(self) -> None:
        if (self.disposition == "proposable") != (self.mapping is not None):
            raise ProposalPlanningError("proposal_readiness_shape_invalid")
        if self.disposition == "needs_attention" and not self.attention_codes:
            raise ProposalPlanningError("attention_requires_reason")


@dataclass(frozen=True, slots=True)
class CaptureProposalPlan:
    """Authorized selection of one immutable interpretation, not a write."""

    page_record_id: str
    interpretation_id: str
    generation: int
    source_page_number: int
    form_id: str
    entries: tuple[EntryProposalReadiness, ...] = field(repr=False)

    @property
    def proposable_count(self) -> int:
        return sum(e.disposition == "proposable" for e in self.entries)

    @property
    def attention_count(self) -> int:
        return sum(e.disposition == "needs_attention" for e in self.entries)

    def summary(self) -> dict[str, object]:
        """No source text, person data, filenames, confidence or operator details."""
        return {
            "page_record_id": self.page_record_id,
            "interpretation_id": self.interpretation_id,
            "generation": self.generation,
            "source_page_number": self.source_page_number,
            "form_id": self.form_id,
            "proposable_entries": self.proposable_count,
            "needs_attention_entries": self.attention_count,
        }


def _check_target_contract() -> None:
    """The narrow approved /summary JSON Pointer must actually be writable."""
    schema_id = schema_id_for("event", "1")
    raw = load_runtime_contract_bundle().schemas[schema_id]
    fields = raw.get("properties")
    if not isinstance(fields, Mapping):
        raise ProposalPlanningError("event_target_contract_unavailable")
    summary = fields.get("summary")
    if not isinstance(summary, Mapping) or summary.get("type") != "string":
        raise ProposalPlanningError("event_summary_target_changed")


def _read_entry(
    form: CapturePageSpec,
    declared: object,
    wire: object,
) -> EntryProposalReadiness:
    """Pure, prevalidated historical content -> bounded mapping readiness."""
    # 'declared' is always a frozen CaptureEntry supplied by a frozen spec.
    from portia.capture.form_catalog import CaptureEntry

    if not isinstance(declared, CaptureEntry) or not isinstance(wire, dict):
        raise ProposalPlanningError("interpretation_entry_invalid")
    if set(wire) - {"entry_state", "fields", "mapped_record_kind"}:
        raise ProposalPlanningError("interpretation_entry_unrecognized_keys")
    state = wire.get("entry_state")
    if state not in {"blank", "unreadable", "candidate"}:
        raise ProposalPlanningError("interpretation_entry_state_invalid")
    if state != "candidate":
        if "fields" in wire:
            raise ProposalPlanningError("noncandidate_has_fields")
        if state == "blank":
            return EntryProposalReadiness(declared.entry_key, "blank")
        return EntryProposalReadiness(
            declared.entry_key, "needs_attention", ("entry_unreadable",)
        )
    fields = wire.get("fields")
    if not isinstance(fields, dict) or set(fields) != {
        f.field_key for f in declared.fields
    }:
        raise ProposalPlanningError("historical_field_inventory_conflict")
    if not declared.permitted_mapped_record_kinds:
        return EntryProposalReadiness(declared.entry_key, "context_only")
    if len(declared.permitted_mapped_record_kinds) != 1:
        return EntryProposalReadiness(
            declared.entry_key, "needs_attention", ("target_family_choice_required",)
        )
    family = declared.permitted_mapped_record_kinds[0]
    if wire.get("mapped_record_kind") not in {None, family}:
        raise ProposalPlanningError("interpretation_mapped_kind_conflict")
    source_key = _EVENT_SUMMARY_FIELD.get((form.form_id, declared.source_role))
    if (
        family != "event"
        or source_key is None
        or form.page_purpose not in {"new_event_capture", "multi_entry_event_capture"}
    ):
        return EntryProposalReadiness(
            declared.entry_key, "needs_attention", ("target_mapping_not_qualified",)
        )
    source_def = next((f for f in declared.fields if f.field_key == source_key), None)
    value = fields.get(source_key)
    if (
        source_def is None
        or not isinstance(value, dict)
        or source_def.field_type != "text"
    ):
        raise ProposalPlanningError("historical_summary_field_conflict")
    if value.get("recognition_state") != "candidate_detected":
        return EntryProposalReadiness(
            declared.entry_key, "needs_attention", ("summary_candidate_unavailable",)
        )
    literal = value.get("candidate_literal")
    if (
        value.get("capture_method") != "manual_transcription"
        or not isinstance(literal, str)
        or not literal.strip()
        or source_def.max_characters is None
        or len(literal) > source_def.max_characters
    ):
        raise ProposalPlanningError("unqualified_summary_candidate")
    _check_target_contract()
    # Context fields and other candidate slots are deliberately not copied.
    return EntryProposalReadiness(
        declared.entry_key,
        "proposable",
        mapping=ProposedTargetMapping(
            "event",
            "1",
            "new_work",
            (PlannedFieldBinding("/summary", source_key, "candidate_literal"),),
            (
                "human_review_required",
                "missing_required_canonical_details",
                "other_source_fields_unmapped",
            ),
        ),
    )


def plan_historical_capture_mappings(
    spec: CapturePageSpec,
    entries: Mapping[str, object],
) -> tuple[EntryProposalReadiness, ...]:
    """Testable planner only, not proof of eligibility or source provenance.

    Only FileCaptureProposalPlanningService.plan establishes authorization and
    exact saved interpretation lineage. This pure function NEVER persists.
    """
    if not isinstance(spec, CapturePageSpec) or not isinstance(entries, Mapping):
        raise ProposalPlanningError("invalid_proposal_planner_input")
    if resolve_capture_page_spec(spec.template_identity()) != spec:
        raise ProposalPlanningError("unknown_historical_form")
    if (
        not 1 <= len(spec.entries) <= _MAX_ENTRIES
        or sum(len(e.fields) for e in spec.entries) > _MAX_FIELDS
        or set(entries) != {e.entry_key for e in spec.entries}
    ):
        raise ProposalPlanningError("historical_entry_inventory_conflict")
    return tuple(
        _read_entry(spec, item, entries[item.entry_key]) for item in spec.entries
    )


class FileCaptureProposalPlanningService:
    """Authorized read-only mapping plan for an explicitly selected generation."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.history = FilePaperInterpretationHistoryService(workspace_root)

    def plan(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        interpretation_id: str,
        generation: int,
        *,
        authorization: CaptureAuthorization,
    ) -> CaptureProposalPlan:
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization required")
        authorization.require_access(class_id, "capture_proposal.plan")
        if not isinstance(interpretation_id, str) or type(generation) is not int:
            raise ProposalPlanningError("interpretation_selection_invalid")
        before = self.history.history(
            class_id, work_id, page_record_id, authorization=authorization
        )
        matches = [
            r
            for r in before.records
            if r.logical_id == interpretation_id and r.field("generation") == generation
        ]
        if len(matches) != 1:
            raise ProposalPlanningError("interpretation_generation_not_found")
        selected: PaperInterpretationV1 = matches[0]
        profile = selected.to_dict().get("interpreter_profile")
        if (
            not isinstance(profile, dict)
            or (profile.get("mapping_profile_id"), profile.get("mapping_version"))
            != _MAPPING_PROFILE
        ):
            raise ProposalPlanningError("unqualified_mapping_profile")
        layout = selected.to_dict().get("layout_snapshot")
        if not isinstance(layout, dict):
            raise ProposalPlanningError("historical_layout_missing")
        spec = resolve_capture_page_spec(layout)
        raw = selected.to_dict().get("entries")
        if not isinstance(raw, dict):
            raise ProposalPlanningError("interpretation_entries_invalid")
        plans = plan_historical_capture_mappings(spec, raw)
        after = self.history.history(
            class_id, work_id, page_record_id, authorization=authorization
        )
        if before != after:
            raise ProposalPlanningError("interpretation_history_changed")
        return CaptureProposalPlan(
            page_record_id,
            interpretation_id,
            generation,
            before.source_page_number,
            spec.form_id,
            plans,
        )
