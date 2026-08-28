from __future__ import annotations

import json
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import RosterNotFoundError
from portia.models import PortiaRecord, parse_portia_record
from portia.workflows import (
    EventWorkflowService,
    ObservationWorkflowService,
    ParticipantWorkflowService,
    WorkflowPrerequisiteError,
    observation_reference,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
)


def _write_roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Synthetic",
                    "first_name": "Observer",
                    "period": "2",
                }
            ],
        ),
    )


def _observation_record(
    *,
    observation_id: str = "obs_alpha",
    status: str = "active",
    observer: dict[str, object] | None = None,
    method: str = "manual_count",
    content: dict[str, object] | None = None,
    creation_source: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "observation_id": observation_id,
            "status": status,
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "observer": observer
            or {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "method": method,
            "content": content
            or {
                "measurements": [
                    {"measure_type": "count", "value": 3, "unit": "count"}
                ]
            },
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": creation_source or {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _draft_event_with_unknown_participant(root: Path) -> None:
    EventWorkflowService(root).create(event_record(status="draft"))
    ParticipantWorkflowService(root).create(
        event_ref(),
        participant_record(
            subject={"kind": "unknown_person", "reason": "identity_not_known"}
        ),
    )


def test_create_active_observation_v2_resolves_roster_human_observer(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path)
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(
        observer={
            "kind": "human",
            "human_attribution": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Synthetic Observer"},
            },
        },
    )

    service = ObservationWorkflowService(tmp_path)
    created = service.create(event_ref(), observation)
    current = service.require_current_use(
        observation_reference(event_ref(), "obs_alpha")
    )

    assert created.record.contract_version == "2"
    assert current.record.to_dict() == observation.to_dict()


def test_missing_roster_observer_rejects_before_canonical_write(
    tmp_path: Path,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(
        observer={
            "kind": "human",
            "human_attribution": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Synthetic Observer"},
            },
        },
    )

    with pytest.raises(RosterNotFoundError):
        ObservationWorkflowService(tmp_path).create(event_ref(), observation)

    path = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/observation"
        / "obs_alpha.json"
    )
    assert not path.exists()


def test_instrument_observer_with_instrumented_method_is_current_use(
    tmp_path: Path,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(
        observer={
            "kind": "instrument",
            "instrument_type": "counter",
            "instrument_label": "Synthetic Counter",
        },
        method="instrumented",
    )

    service = ObservationWorkflowService(tmp_path)
    service.create(event_ref(), observation)

    assert (
        service.require_current_use(observation_reference(event_ref(), "obs_alpha"))
        .record.status
        == "active"
    )


@pytest.mark.parametrize(
    ("observer", "method", "message"),
    [
        (
            {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "instrumented",
            "human Observation observer",
        ),
        (
            {
                "kind": "instrument",
                "instrument_type": "counter",
                "instrument_label": "Synthetic Counter",
            },
            "manual_count",
            "instrument Observation observer",
        ),
    ],
)
def test_observer_method_mismatch_is_zero_write(
    tmp_path: Path,
    observer: dict[str, object],
    method: str,
    message: str,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(observer=observer, method=method)

    with pytest.raises(WorkflowPrerequisiteError, match=message):
        ObservationWorkflowService(tmp_path).create(event_ref(), observation)

    path = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/observation"
        / "obs_alpha.json"
    )
    assert not path.exists()


@pytest.mark.parametrize(
    ("method", "content", "message"),
    [
        (
            "manual_count",
            {
                "measurements": [
                    {
                        "measure_type": "duration",
                        "value": 10,
                        "unit": "seconds",
                    }
                ]
            },
            "count or percentage",
        ),
        (
            "manual_timing",
            {
                "measurements": [
                    {"measure_type": "count", "value": 2, "unit": "count"}
                ]
            },
            "duration or latency",
        ),
    ],
)
def test_manual_method_requires_compatible_measurement(
    tmp_path: Path,
    method: str,
    content: dict[str, object],
    message: str,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(method=method, content=content)

    with pytest.raises(WorkflowPrerequisiteError, match=message):
        ObservationWorkflowService(tmp_path).create(event_ref(), observation)


def test_proposed_observation_is_exactly_readable_but_not_current_use(
    tmp_path: Path,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    service = ObservationWorkflowService(tmp_path)
    service.create(event_ref(), _observation_record(status="proposed"))
    reference = observation_reference(event_ref(), "obs_alpha")

    assert service.load_exact(reference).record.status == "proposed"
    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        service.require_current_use(reference)


def test_non_digital_observation_creation_is_deferred_and_zero_write(
    tmp_path: Path,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    observation = _observation_record(
        status="proposed",
        creation_source={
            "type": "import",
            "source_label": "Synthetic deferred import",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry"):
        ObservationWorkflowService(tmp_path).create(event_ref(), observation)

    path = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/observation"
        / "obs_alpha.json"
    )
    assert not path.exists()


def test_v1_observation_remains_current_use_eligible_without_migration(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path)
    _draft_event_with_unknown_participant(tmp_path)
    fixture = Path(
        "tests/schema_validation/fixtures/issue-15/observation/valid/"
        "minimum-active.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    value["target"]["record_ref"]["record_id"] = "ep_alpha"
    value["observer"]["human_attribution"]["roster_student_ref"] = {
        "class_id": "class_a",
        "student_id": "student_1",
    }
    observation = parse_portia_record("observation", "1", value)
    repository = ObservationWorkflowService(tmp_path).repository
    repository.create_work_record(event_ref(), observation)
    service = ObservationWorkflowService(tmp_path, repository=repository)

    current = service.require_current_use(
        observation_reference(event_ref(), "obs_direct_1", version="1")
    )

    assert current.record.contract_version == "1"
