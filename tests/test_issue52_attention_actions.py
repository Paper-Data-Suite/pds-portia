from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pds_core.module_operations import ModuleOperationsRequest

import portia.attention_provider as provider
from portia.attention import (
    ATTENTION_DEFINITION_BY_CODE,
    PORTIA_ATTENTION_ACTION_ID_BY_CODE,
    PORTIA_ATTENTION_ACTION_IDS,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionScope,
    PortiaAttentionSummary,
    require_portia_attention_action_id,
)
from portia.menu.attention import ATTENTION_ROUTE_BY_CODE, attention_route
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError

_EXPECTED_ACTIONS = {
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

_EXPECTED_MENU_ROUTE_BY_ACTION = {
    "open_complete_follow_up": "complete_follow_up",
    "open_add_information": "add_information",
    "open_manage_support": "manage_support",
    "open_advanced_tools": "advanced_inspection",
}


def _query() -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.class_scope("class_a"),
        as_of=ExplicitOffsetTimestamp("2026-10-01T00:00:00-04:00"),
    )


def test_owner_action_mapping_is_closed_over_native_attention_taxonomy() -> None:
    assert PORTIA_ATTENTION_ACTION_ID_BY_CODE == _EXPECTED_ACTIONS
    assert set(PORTIA_ATTENTION_ACTION_ID_BY_CODE) == set(
        ATTENTION_DEFINITION_BY_CODE
    )
    assert set(PORTIA_ATTENTION_ACTION_ID_BY_CODE.values()) == set(
        PORTIA_ATTENTION_ACTION_IDS
    )


def test_owner_action_ids_are_opaque_bounded_identity_only() -> None:
    assert PORTIA_ATTENTION_ACTION_IDS == (
        "open_complete_follow_up",
        "open_add_information",
        "open_manage_support",
        "open_advanced_tools",
    )
    for action_id in PORTIA_ATTENTION_ACTION_IDS:
        assert ":" not in action_id
        assert "/" not in action_id
        assert "\\" not in action_id
        assert "." not in action_id


def test_unknown_future_native_code_fails_closed() -> None:
    with pytest.raises(
        PortiaLocalValidationError,
        match="unknown Portia attention action code",
    ):
        require_portia_attention_action_id("portia_future_attention")


@pytest.mark.parametrize(
    ("code", "action_id"),
    tuple(_EXPECTED_ACTIONS.items()),
)
def test_core_projection_emits_exact_portia_owner_action(
    tmp_path: Path,
    code: str,
    action_id: str,
) -> None:
    definition = ATTENTION_DEFINITION_BY_CODE[code]
    native = PortiaAttentionReport(
        query=_query(),
        evaluation="evaluated",
        summaries=(
            PortiaAttentionSummary(
                code=definition.code,
                label=definition.label,
                count=1,
                count_unit=definition.count_unit,
                attention_class=definition.attention_class,
            ),
        ),
    )

    shared = provider._project_native_report(
        native,
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            class_id="class_a",
        ),
    )

    assert len(shared.summaries) == 1
    action = shared.summaries[0].action
    assert action is not None
    assert action.module_id == "portia"
    assert action.action_id == action_id


def test_teacher_menu_routes_are_derived_from_same_owner_action_authority() -> None:
    expected = {
        code: _EXPECTED_MENU_ROUTE_BY_ACTION[action_id]
        for code, action_id in PORTIA_ATTENTION_ACTION_ID_BY_CODE.items()
    }
    assert ATTENTION_ROUTE_BY_CODE == expected
    for code, route in expected.items():
        assert attention_route(code) == route
    assert attention_route("portia_future_attention") is None


def test_core_provider_does_not_import_teacher_menu_to_obtain_actions() -> None:
    source = inspect.getsource(provider)
    assert "portia.menu" not in source
    assert "require_portia_attention_action_id" in source


def test_action_projection_does_not_execute_or_mutate_any_route(
    tmp_path: Path,
) -> None:
    definition = ATTENTION_DEFINITION_BY_CODE["portia_review_incomplete"]
    native = PortiaAttentionReport(
        query=_query(),
        evaluation="evaluated",
        summaries=(
            PortiaAttentionSummary(
                code=definition.code,
                label=definition.label,
                count=1,
                count_unit=definition.count_unit,
                attention_class=definition.attention_class,
            ),
        ),
    )
    before = tuple(tmp_path.rglob("*"))

    shared = provider._project_native_report(
        native,
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            class_id="class_a",
        ),
    )

    assert shared.summaries[0].action is not None
    assert tuple(tmp_path.rglob("*")) == before == ()


def test_action_module_contains_no_clock_or_execution_surface() -> None:
    import portia.attention.actions as actions

    source = inspect.getsource(actions)
    assert "datetime" not in source
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "launch_" not in source
    assert "workspace_root" not in source
