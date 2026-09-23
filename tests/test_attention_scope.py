from __future__ import annotations

import pytest

from portia.attention import (
    FollowUpScheduleQuery,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef


def _event_ref(*, class_id: str = "class-1") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id="evt_issue49",
        work_kind="event",
        contract_version="2",
    )


def test_scope_requires_explicit_workspace_class_or_work() -> None:
    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionScope()


def test_workspace_scope_is_explicit_and_cannot_be_combined() -> None:
    scope = PortiaAttentionScope.workspace_scope()
    assert scope.kind == "workspace"

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionScope(workspace=True, class_id="class-1")


def test_exact_class_and_work_scope_are_structural_and_consistent() -> None:
    class_scope = PortiaAttentionScope.class_scope("class-1")
    assert class_scope.kind == "class"

    work = _event_ref()
    work_scope = PortiaAttentionScope.work_scope(
        work,
        class_id="class-1",
    )
    assert work_scope.kind == "work"

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionScope.work_scope(work, class_id="class-2")


def test_attention_query_requires_explicit_offset_as_of_and_known_filters() -> None:
    scope = PortiaAttentionScope.class_scope("class-1")
    as_of = ExplicitOffsetTimestamp("2026-09-21T19:00:00-04:00")
    query = PortiaAttentionQuery(
        scope=scope,
        as_of=as_of,
        active_school_year="2026-2027",
        attention_codes=("portia_follow_up_due",),
        attention_classes=("workflow",),
    )
    assert query.as_of is as_of

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionQuery(  # type: ignore[arg-type]
            scope=scope,
            as_of="2026-09-21T19:00:00-04:00",
        )

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionQuery(
            scope=scope,
            as_of=as_of,
            attention_codes=("portia_future_unknown_code",),
        )


def test_follow_up_schedule_query_is_separate_from_attention_query() -> None:
    scope = PortiaAttentionScope.work_scope(_event_ref())
    as_of = ExplicitOffsetTimestamp("2026-09-21T19:00:00-04:00")
    schedule_query = FollowUpScheduleQuery(scope=scope, as_of=as_of)

    assert schedule_query.scope is scope
    assert not isinstance(schedule_query, PortiaAttentionQuery)
