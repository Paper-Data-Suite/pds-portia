from __future__ import annotations

from pathlib import Path

import pytest

from portia.attention import (
    AttentionQueryService,
    FollowUpScheduleQuery,
    FollowUpScheduleQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.repository import PortiaRepository
from portia.workflows import FollowUpWorkflowService
from tests.workflow_helpers import AGENT, event_record, event_ref, participant_record

AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")
CREATED = "2026-09-20T09:00:00-04:00"


def _seed_event(tmp_path: Path) -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    repository.create_work_record(
        work,
        participant_record(
            subject={
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic student",
            },
        ),
    )
    return repository, work


def _follow_up_record(
    *,
    follow_up_id: str,
    planned_timing: dict[str, object],
    workflow_state: str = "scheduled",
    status: str = "active",
) -> PortiaRecord:
    return parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "follow_up_id": follow_up_id,
            "status": status,
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "owner": {
                "kind": "represented_human",
                "person": {
                    "kind": "local_operator",
                    "display_label": "Synthetic teacher",
                },
            },
            "purpose": {"kind": "student_check_in"},
            "planned_timing": planned_timing,
            "workflow_state": workflow_state,
            **(
                {"completed_at": CREATED}
                if workflow_state == "completed"
                else {}
            ),
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _schedule_query() -> FollowUpScheduleQuery:
    return FollowUpScheduleQuery(
        scope=PortiaAttentionScope.work_scope(event_ref()),
        as_of=AS_OF,
    )


def _attention_query(
    *,
    active_school_year: str | None = None,
) -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref()),
        as_of=AS_OF,
        active_school_year=active_school_year,
    )


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (
                str(path.relative_to(root)),
                path.read_bytes(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_schedule_query_returns_scheduled_due_and_overdue(
    tmp_path: Path,
) -> None:
    repository, work = _seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path, repository=repository)
    service.create(
        work,
        _follow_up_record(
            follow_up_id="fup_future",
            planned_timing={"kind": "date_only", "date": "2026-09-22"},
        ),
    )
    service.create(
        work,
        _follow_up_record(
            follow_up_id="fup_due",
            planned_timing={"kind": "date_only", "date": "2026-09-21"},
        ),
    )
    service.create(
        work,
        _follow_up_record(
            follow_up_id="fup_overdue",
            planned_timing={"kind": "date_only", "date": "2026-09-20"},
        ),
    )

    result = FollowUpScheduleQueryService(
        tmp_path,
        repository=repository,
    ).query(_schedule_query())

    observed = {
        item.source_ref.record_ref.record_id: item.timing.classification
        for item in result
    }
    assert observed == {
        "fup_future": "scheduled",
        "fup_due": "due",
        "fup_overdue": "overdue",
    }


@pytest.mark.parametrize(
    "workflow_state",
    ["completed", "cancelled", "unable_to_complete"],
)
def test_terminal_follow_up_is_not_current_schedule_or_attention(
    tmp_path: Path,
    workflow_state: str,
) -> None:
    repository, work = _seed_event(tmp_path)
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up_record(
            follow_up_id=f"fup_{workflow_state}",
            planned_timing={"kind": "date_only", "date": "2026-09-20"},
            workflow_state=workflow_state,
        ),
    )

    schedule = FollowUpScheduleQueryService(
        tmp_path,
        repository=repository,
    ).query(_schedule_query())
    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_attention_query())

    assert schedule == ()
    assert report.items == ()


def test_in_progress_follow_up_remains_schedule_eligible(tmp_path: Path) -> None:
    repository, work = _seed_event(tmp_path)
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up_record(
            follow_up_id="fup_in_progress",
            planned_timing={"kind": "date_only", "date": "2026-09-21"},
            workflow_state="in_progress",
        ),
    )

    result = FollowUpScheduleQueryService(
        tmp_path,
        repository=repository,
    ).query(_schedule_query())

    assert len(result) == 1
    assert result[0].timing.classification == "due"


def test_proposed_follow_up_is_not_silently_promoted_to_schedule(
    tmp_path: Path,
) -> None:
    repository, work = _seed_event(tmp_path)
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up_record(
            follow_up_id="fup_proposed",
            planned_timing={"kind": "date_only", "date": "2026-09-21"},
            status="proposed",
        ),
    )

    assert FollowUpScheduleQueryService(
        tmp_path,
        repository=repository,
    ).query(_schedule_query()) == ()


def test_attention_omits_future_schedule_and_keeps_due_overdue(
    tmp_path: Path,
) -> None:
    repository, work = _seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path, repository=repository)
    for identifier, planned in (
        ("fup_future", "2026-09-22"),
        ("fup_due", "2026-09-21"),
        ("fup_overdue", "2026-09-20"),
    ):
        service.create(
            work,
            _follow_up_record(
                follow_up_id=identifier,
                planned_timing={"kind": "date_only", "date": planned},
            ),
        )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_attention_query())

    observed = {
        item.source_ref.record_ref.record_id: (
            item.code,
            item.reason_codes,
            item.timing.classification if item.timing is not None else None,
        )
        for item in report.items
    }
    assert observed == {
        "fup_due": ("portia_follow_up_due", ("scheduled",), "due"),
        "fup_overdue": (
            "portia_follow_up_overdue",
            ("scheduled",),
            "overdue",
        ),
    }


def test_school_year_is_an_exact_filter_not_an_identity_join(
    tmp_path: Path,
) -> None:
    repository, work = _seed_event(tmp_path)
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up_record(
            follow_up_id="fup_due",
            planned_timing={"kind": "date_only", "date": "2026-09-21"},
        ),
    )

    matching = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_attention_query(active_school_year="2026-2027"))
    nonmatching = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_attention_query(active_school_year="2025-2026"))

    assert len(matching.items) == 1
    assert nonmatching.evaluation == "evaluated"
    assert nonmatching.items == ()


def test_workflow_attention_query_is_zero_write(tmp_path: Path) -> None:
    repository, work = _seed_event(tmp_path)
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up_record(
            follow_up_id="fup_due",
            planned_timing={"kind": "date_only", "date": "2026-09-21"},
        ),
    )
    before = _snapshot(tmp_path)

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_attention_query())

    assert len(report.items) == 1
    assert _snapshot(tmp_path) == before
