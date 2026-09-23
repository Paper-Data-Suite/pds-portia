from __future__ import annotations

from pathlib import Path

import pytest

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.repository import PortiaRepository
from portia.workflows import ReviewWorkflowService
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")


def _seed_event(tmp_path: Path) -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    return repository, work


def _review_record(
    *,
    review_id: str,
    review_state: str,
    status: str = "active",
) -> PortiaRecord:
    return parse_portia_record(
        "review",
        "1",
        {
            "schema_version": "1",
            "record_type": "review",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "review_id": review_id,
            "status": status,
            "review_state": review_state,
            "trigger": {"kind": "routine_review"},
            "question": {
                "kind": "evidence_review",
                "text": "What exact information is available?",
            },
            "target": {"kind": "event"},
            "reviewer": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "evidence_considered": [],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _query() -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref()),
        as_of=AS_OF,
    )


@pytest.mark.parametrize(
    "review_state",
    ["open", "in_review", "awaiting_information"],
)
def test_active_incomplete_review_is_attention(
    tmp_path: Path,
    review_state: str,
) -> None:
    repository, work = _seed_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,
        _review_record(
            review_id=f"rvw_{review_state}",
            review_state=review_state,
        ),
    )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_query())

    assert len(report.items) == 1
    item = report.items[0]
    assert item.code == "portia_review_incomplete"
    assert item.reason_codes == (review_state,)
    assert item.source_ref.record_ref.record_id == f"rvw_{review_state}"


@pytest.mark.parametrize("review_state", ["completed", "cancelled"])
def test_terminal_review_is_not_incomplete_attention(
    tmp_path: Path,
    review_state: str,
) -> None:
    repository, work = _seed_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,
        _review_record(
            review_id=f"rvw_{review_state}",
            review_state=review_state,
        ),
    )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_query())

    assert report.items == ()


def test_proposed_review_is_not_current_attention(tmp_path: Path) -> None:
    repository, work = _seed_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,
        _review_record(
            review_id="rvw_proposed",
            review_state="open",
            status="proposed",
        ),
    )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_query())

    assert report.items == ()


def test_completed_review_without_determination_is_not_incomplete(
    tmp_path: Path,
) -> None:
    repository, work = _seed_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,
        _review_record(
            review_id="rvw_complete_no_determination",
            review_state="completed",
        ),
    )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(_query())

    assert report.items == ()
