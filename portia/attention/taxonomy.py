"""Stable native Portia attention taxonomy for Issue #49."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from portia.models.errors import PortiaLocalValidationError

AttentionClass: TypeAlias = Literal["workflow", "recovery", "integrity"]
AttentionTimingRequirement: TypeAlias = Literal["due", "overdue"]

ATTENTION_CLASSES: Final[tuple[AttentionClass, ...]] = (
    "workflow",
    "recovery",
    "integrity",
)


@dataclass(frozen=True, slots=True)
class PortiaAttentionDefinition:
    """One code-owned native attention meaning.

    Definition order is deterministic presentation order only. It is not
    urgency, severity, risk, or a recommendation ranking.
    """

    code: str
    label: str
    count_unit: str
    attention_class: AttentionClass
    definition_order: int
    semantic_authority: str
    timing_classification: AttentionTimingRequirement | None = None


ATTENTION_DEFINITIONS: Final[tuple[PortiaAttentionDefinition, ...]] = (
    PortiaAttentionDefinition(
        code="portia_follow_up_due",
        label="Follow-Ups due",
        count_unit="follow_ups",
        attention_class="workflow",
        definition_order=0,
        semantic_authority="FollowUpWorkflowService and explicit planned timing",
        timing_classification="due",
    ),
    PortiaAttentionDefinition(
        code="portia_follow_up_overdue",
        label="Follow-Ups overdue",
        count_unit="follow_ups",
        attention_class="workflow",
        definition_order=1,
        semantic_authority="FollowUpWorkflowService and explicit planned timing",
        timing_classification="overdue",
    ),
    PortiaAttentionDefinition(
        code="portia_review_incomplete",
        label="Reviews incomplete",
        count_unit="reviews",
        attention_class="workflow",
        definition_order=2,
        semantic_authority="ReviewWorkflowService",
    ),
    PortiaAttentionDefinition(
        code="portia_integrity_conflict",
        label="Integrity conflicts requiring review",
        count_unit="integrity_findings",
        attention_class="integrity",
        definition_order=3,
        semantic_authority=(
            "integrity_finding@2 and Issue #47 reconciliation authority"
        ),
    ),
    PortiaAttentionDefinition(
        code="portia_integrity_review_required",
        label="Integrity findings requiring review",
        count_unit="integrity_findings",
        attention_class="integrity",
        definition_order=4,
        semantic_authority=(
            "integrity_finding@2 and Issue #47 operator authority"
        ),
    ),
    PortiaAttentionDefinition(
        code="portia_recovery_required",
        label="Recovery required",
        count_unit="recovery_scopes",
        attention_class="recovery",
        definition_order=5,
        semantic_authority="OperationRecovery and RecoveryWorkflowService",
    ),
    PortiaAttentionDefinition(
        code="portia_quarantine_active",
        label="Active Quarantine",
        count_unit="quarantines",
        attention_class="integrity",
        definition_order=6,
        semantic_authority="QuarantineGuard and QuarantineWorkflowService",
    ),
    PortiaAttentionDefinition(
        code="portia_derived_state_stale",
        label="Derived state stale",
        count_unit="derived_projections",
        attention_class="recovery",
        definition_order=7,
        semantic_authority="DerivedStore source-snapshot freshness authority",
    ),
    PortiaAttentionDefinition(
        code="portia_support_process_review_due",
        label="Support Processes due for review",
        count_unit="support_processes",
        attention_class="workflow",
        definition_order=8,
        semantic_authority="SupportProcessWorkflowService review_on",
        timing_classification="due",
    ),
    PortiaAttentionDefinition(
        code="portia_support_process_review_overdue",
        label="Support Processes overdue for review",
        count_unit="support_processes",
        attention_class="workflow",
        definition_order=9,
        semantic_authority="SupportProcessWorkflowService review_on",
        timing_classification="overdue",
    ),
    PortiaAttentionDefinition(
        code="portia_support_process_dependency_attention",
        label="Support Process dependency attention",
        count_unit="support_processes",
        attention_class="workflow",
        definition_order=10,
        semantic_authority="DependencyWorkflowService gate evaluation",
    ),
)

ATTENTION_DEFINITION_BY_CODE: Final[dict[str, PortiaAttentionDefinition]] = {
    definition.code: definition for definition in ATTENTION_DEFINITIONS
}

if len(ATTENTION_DEFINITION_BY_CODE) != len(ATTENTION_DEFINITIONS):
    raise RuntimeError("Portia attention definition codes must be unique.")

if tuple(
    definition.definition_order for definition in ATTENTION_DEFINITIONS
) != tuple(range(len(ATTENTION_DEFINITIONS))):
    raise RuntimeError(
        "Portia attention definition order must be contiguous and stable."
    )


def require_attention_definition(code: object) -> PortiaAttentionDefinition:
    """Resolve one known native code and fail closed for unknown vocabulary."""
    if not isinstance(code, str):
        raise PortiaLocalValidationError("attention code must be a string")
    try:
        return ATTENTION_DEFINITION_BY_CODE[code]
    except KeyError as exc:
        raise PortiaLocalValidationError(
            f"unknown Portia attention code: {code!r}"
        ) from exc


def require_attention_class(value: object) -> AttentionClass:
    """Validate one member of the closed native attention-class vocabulary."""
    if value not in ATTENTION_CLASSES:
        raise PortiaLocalValidationError(
            f"unsupported Portia attention class: {value!r}"
        )
    return value
