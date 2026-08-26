from __future__ import annotations

import json
from pathlib import Path

from portia.models import EventV2, parse_portia_record
from portia.validation import GraphValidationOptions, validate_record_graph

REPO_ROOT = Path(__file__).resolve().parents[1]
EVENT_PATH = (
    REPO_ROOT
    / "tests/fixtures/issue_22/positive/p22_01_positive_classroom_event/records/event.json"
)
SUPPORT_PATH = (
    REPO_ROOT
    / "tests/fixtures/issue_22/positive/p22_08_support_positive_outcome/support.json"
)


def _event_wire() -> dict[str, object]:
    value = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _codes(*records: EventV2) -> set[str]:
    return {
        finding.code
        for finding in validate_record_graph(
            records,
            options=GraphValidationOptions(require_internal_resolution=True),
        )
    }


def test_duplicate_exact_identity_is_an_application_finding() -> None:
    first = parse_portia_record("event", "2", _event_wire())
    second = parse_portia_record("event", "2", _event_wire())
    assert isinstance(first, EventV2)
    assert isinstance(second, EventV2)
    assert "PORTIA.GRAPH.DUPLICATE_IDENTITY" in _codes(first, second)


def test_self_supersession_is_rejected_without_following_successor() -> None:
    wire = _event_wire()
    wire["supersedes"] = [
        {
            "module_id": "portia",
            "class_id": wire["class_id"],
            "work_id": wire["work_id"],
            "work_kind": "event",
            "contract_version": "2",
        }
    ]
    record = parse_portia_record("event", "2", wire)
    assert isinstance(record, EventV2)
    assert "PORTIA.GRAPH.SELF_SUPERSESSION" in _codes(record)


def test_record_chronology_is_application_validated() -> None:
    wire = _event_wire()
    wire["created_at"] = "2026-08-25T13:00:00-04:00"
    wire["updated_at"] = "2026-08-25T12:00:00-04:00"
    record = parse_portia_record("event", "2", wire)
    assert isinstance(record, EventV2)
    assert "PORTIA.GRAPH.TIMESTAMP_ORDER" in _codes(record)


def test_module_work_record_nested_module_ids_must_agree() -> None:
    wire = _event_wire()
    wire["instructional_context"] = {
        "type": "assessment",
        "external_refs": [
            {
                "work_ref": {
                    "module_id": "scoreform",
                    "class_id": wire["class_id"],
                    "work_id": "assessment_1",
                },
                "record_ref": {
                    "module_id": "quillan",
                    "record_kind": "response",
                    "record_id": "response_1",
                    "contract_version": None,
                },
            }
        ],
    }
    record = parse_portia_record("event", "2", wire)
    assert isinstance(record, EventV2)
    assert "PORTIA.GRAPH.MODULE_ID_MISMATCH" in _codes(record)


def test_planned_schedule_chronology_and_duration_are_application_validated() -> None:
    value = json.loads(SUPPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    schedule = value["schedule"]
    assert isinstance(schedule, dict)
    schedule["window"] = {"starts_on": "2026-08-28", "ends_on": "2026-08-19"}
    schedule["planned_duration"] = {
        "kind": "range_minutes",
        "minimum_minutes": 30,
        "maximum_minutes": 10,
    }
    record = parse_portia_record("support", "1", value)
    codes = {finding.code for finding in validate_record_graph([record])}
    assert "PORTIA.GRAPH.PLANNED_SCHEDULE_WINDOW_ORDER" in codes
    assert "PORTIA.GRAPH.PLANNED_SCHEDULE_DURATION_ORDER" in codes
