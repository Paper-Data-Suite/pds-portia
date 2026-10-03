"""Presentation-neutral owner-action identity for native Portia attention."""

from __future__ import annotations

from typing import Final, Literal, TypeAlias

from portia.attention.taxonomy import ATTENTION_DEFINITION_BY_CODE
from portia.models.errors import PortiaLocalValidationError

PortiaAttentionActionId: TypeAlias = Literal[
    "open_complete_follow_up",
    "open_add_information",
    "open_manage_support",
    "open_advanced_tools",
]

PORTIA_ATTENTION_ACTION_IDS: Final[tuple[PortiaAttentionActionId, ...]] = (
    "open_complete_follow_up",
    "open_add_information",
    "open_manage_support",
    "open_advanced_tools",
)

PORTIA_ATTENTION_ACTION_ID_BY_CODE: Final[
    dict[str, PortiaAttentionActionId]
] = {
    "portia_follow_up_due": "open_complete_follow_up",
    "portia_follow_up_overdue": "open_complete_follow_up",
    "portia_review_incomplete": "open_add_information",
    "portia_integrity_conflict": "open_advanced_tools",
    "portia_integrity_review_required": "open_advanced_tools",
    "portia_recovery_required": "open_advanced_tools",
    "portia_quarantine_active": "open_advanced_tools",
    "portia_derived_state_stale": "open_advanced_tools",
    "portia_support_process_review_due": "open_manage_support",
    "portia_support_process_review_overdue": "open_manage_support",
    "portia_support_process_dependency_attention": "open_manage_support",
}

if set(PORTIA_ATTENTION_ACTION_ID_BY_CODE) != set(ATTENTION_DEFINITION_BY_CODE):
    raise RuntimeError(
        "Portia attention owner-action mapping must cover the exact native taxonomy."
    )
if set(PORTIA_ATTENTION_ACTION_ID_BY_CODE.values()) != set(
    PORTIA_ATTENTION_ACTION_IDS
):
    raise RuntimeError(
        "Portia attention owner-action mapping must use the exact action vocabulary."
    )


def require_portia_attention_action_id(
    code: object,
) -> PortiaAttentionActionId:
    """Resolve one known native code to its opaque Portia owner-action ID."""

    if not isinstance(code, str):
        raise PortiaLocalValidationError("attention action code must be a string")
    try:
        value = PORTIA_ATTENTION_ACTION_ID_BY_CODE[code]
    except KeyError as exc:
        raise PortiaLocalValidationError(
            f"unknown Portia attention action code: {code!r}"
        ) from exc
    return value


__all__ = [
    "PORTIA_ATTENTION_ACTION_ID_BY_CODE",
    "PORTIA_ATTENTION_ACTION_IDS",
    "PortiaAttentionActionId",
    "require_portia_attention_action_id",
]
