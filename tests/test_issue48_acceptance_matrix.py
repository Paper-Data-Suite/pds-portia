"""Closeout acceptance matrix for the Issue #48 student view."""

from __future__ import annotations

import hashlib
from dataclasses import fields
from pathlib import Path
from typing import get_args

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef, RosterStudentRef
from portia.storage import PortiaRepository
from portia.views import (
    STUDENT_VIEW_PROJECTION_INVENTORY,
    HistoryEntryKind,
    StudentTimelineFilter,
    StudentTimelineQuery,
    StudentTimelineService,
    StudentViewScope,
    contract_rule,
    projection_rule,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, participant_record


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _roster(root: Path, *student_ids: str) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": student_id,
                    "last_name": "Same",
                    "first_name": "Student",
                    "period": "2",
                }
                for student_id in student_ids
            ],
        ),
    )


def _support_work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_issue48_closeout",
        work_kind="support_process",
        contract_version="1",
    )


def _support_root():
    work = _support_work()
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": work.class_id,
            "work_id": work.work_id,
            "school_year": "2026-2027",
            "status": "active",
            "workflow_state": "active",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _support_participant():
    work = _support_work()
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": work.class_id,
            "work_id": work.work_id,
            "participant_id": "spp_issue48_closeout",
            "status": "active",
            "person": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Same Student"},
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_issue48_registry_preserves_semantic_families_and_no_score_surface() -> None:
    expected = {
        ("account", "2"): ("evidence", "account"),
        ("observation", "2"): ("evidence", "observation"),
        ("review", "1"): ("judgment", "judgment"),
        ("classification", "1"): ("judgment", "judgment"),
        ("hypothesis", "1"): ("judgment", "judgment"),
        ("determination", "1"): ("judgment", "judgment"),
        ("response", "1"): ("response", "response"),
        ("communication", "1"): ("response", "communication"),
        ("support", "1"): ("support", "support"),
        ("intervention", "1"): ("support", "support"),
        ("implementation", "1"): ("implementation", "implementation"),
        ("fidelity", "1"): ("implementation", "fidelity"),
        ("follow_up", "1"): ("follow_up", "follow_up"),
        ("outcome", "1"): ("follow_up", "outcome"),
        ("reentry", "1"): ("follow_up", "reentry"),
        ("repair", "1"): ("follow_up", "repair"),
    }
    for key, (category, adapter) in expected.items():
        rule = projection_rule(*key)
        assert rule.category == category
        assert rule.adapter == adapter

    filter_fields = {field.name for field in fields(StudentTimelineFilter)}
    forbidden = {"severity", "risk", "offender", "score", "ranking", "tier"}
    assert filter_fields.isdisjoint(forbidden)
    projected_names = {
        name
        for rule in STUDENT_VIEW_PROJECTION_INVENTORY.values()
        for name in (
            *rule.safe_scalar_fields,
            *rule.manual_review_fields,
            *rule.withheld_fields,
        )
    }
    assert all(
        not any(token in name for token in forbidden)
        for name in projected_names
    )


def test_issue48_exact_identity_ignores_equal_roster_names(tmp_path: Path) -> None:
    _roster(tmp_path, "student_1", "student_2")
    repository = PortiaRepository(tmp_path)
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_equal_names",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(
        work,
        event_record(class_id="class_a", event_id="evt_equal_names"),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_equal_names",
            class_id="class_a",
            event_id="evt_equal_names",
            subject={
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_2",
                },
                "display_snapshot": {"display_name": "Same Student"},
            },
        ),
    )
    query = StudentTimelineQuery(
        StudentViewScope(
            focal_students=(
                RosterStudentRef(class_id="class_a", student_id="student_1"),
            ),
        )
    )

    result = StudentTimelineService(tmp_path, repository=repository).generate(query)

    assert result.works == ()
    assert result.entries == ()


def test_issue48_generation_is_read_only_and_groups_event_and_support(
    tmp_path: Path,
) -> None:
    _roster(tmp_path, "student_1")
    repository = PortiaRepository(tmp_path)
    event = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_issue48_closeout",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(
        event,
        event_record(class_id="class_a", event_id=event.work_id),
    )
    repository.create_work_record(
        event,
        participant_record(
            participant_id="ep_issue48_closeout",
            class_id="class_a",
            event_id=event.work_id,
        ),
    )
    support = _support_work()
    repository.create_work(support, _support_root())
    repository.create_work_record(support, _support_participant())
    query = StudentTimelineQuery(
        StudentViewScope(
            focal_students=(
                RosterStudentRef(class_id="class_a", student_id="student_1"),
            ),
            allowed_works=(event, support),
        )
    )
    service = StudentTimelineService(tmp_path, repository=repository)
    before = _snapshot(tmp_path)

    first = service.generate(query)
    second = service.generate(
        query,
        filters=StudentTimelineFilter(sort_direction="descending"),
    )
    after = _snapshot(tmp_path)

    assert {work.work_ref.work_kind for work in first.works} == {
        "event",
        "support_process",
    }
    assert {work.work_ref for work in second.works} == {event, support}
    assert before == after


def test_issue48_foreign_sources_and_sibling_payloads_remain_separate() -> None:
    account = projection_rule("account", "2")
    observation = projection_rule("observation", "2")
    communication = projection_rule("communication", "1")
    assert "source_artifacts" in account.withheld_fields
    assert "source_artifacts" in observation.withheld_fields
    assert "attachments" in communication.withheld_fields
    assert "recipients" in communication.withheld_fields
    safe = {
        name
        for rule in STUDENT_VIEW_PROJECTION_INVENTORY.values()
        for name in rule.safe_scalar_fields
    }
    assert "endpoint_ref" not in safe
    assert "path" not in safe
    assert "retained_source_path" not in safe


def test_issue48_history_inventory_keeps_correction_families_explicit() -> None:
    assert contract_rule("lifecycle_transition", "1").surface == "history_context"
    assert contract_rule("amendment", "1").surface == "history_context"
    assert (
        contract_rule("statement_of_disagreement", "1").surface
        == "history_context"
    )
    assert contract_rule("record_migration", "1").surface == "administrative_context"
    assert (
        contract_rule("ownership_correction", "2").surface
        == "administrative_context"
    )
    assert (
        contract_rule("exceptional_removal", "1").surface
        == "administrative_context"
    )
    kinds = set(get_args(HistoryEntryKind))
    assert {
        "amendment",
        "statement_of_disagreement",
        "record_migration",
        "ownership_correction",
        "exceptional_removal",
    }.issubset(kinds)
