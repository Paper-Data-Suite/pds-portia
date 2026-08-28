from __future__ import annotations

import json
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import RosterNotFoundError
from portia.models import PortiaRecord, parse_portia_record
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    WorkflowPrerequisiteError,
    account_reference,
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
                    "first_name": "Source",
                    "period": "2",
                }
            ],
        ),
    )


def _account_record(
    *,
    account_id: str = "acct_alpha",
    status: str = "active",
    source: dict[str, object] | None = None,
    creation_source: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": status,
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "source": source
            or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic source contribution.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
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


def test_create_active_account_v2_resolves_roster_source_under_draft_event(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path)
    _draft_event_with_unknown_participant(tmp_path)
    account = _account_record(
        source={
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_a",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Synthetic Source"},
        }
    )

    service = AccountWorkflowService(tmp_path)
    created = service.create(event_ref(), account)
    current = service.require_current_use(account_reference(event_ref(), "acct_alpha"))

    assert created.record.contract_version == "2"
    assert current.record.to_dict() == account.to_dict()


def test_missing_roster_source_rejects_account_before_canonical_write(
    tmp_path: Path,
) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    account = _account_record(
        source={
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_a",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Synthetic Source"},
        }
    )

    with pytest.raises(RosterNotFoundError):
        AccountWorkflowService(tmp_path).create(event_ref(), account)

    path = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/account/acct_alpha.json"
    )
    assert not path.exists()


def test_non_digital_account_creation_is_deferred_and_zero_write(tmp_path: Path) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    account = _account_record(
        status="proposed",
        creation_source={
            "type": "import",
            "source_label": "Synthetic deferred import",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry"):
        AccountWorkflowService(tmp_path).create(event_ref(), account)

    path = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/account/acct_alpha.json"
    )
    assert not path.exists()


def test_proposed_account_is_exactly_readable_but_not_current_use(tmp_path: Path) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account_record(status="proposed"))
    reference = account_reference(event_ref(), "acct_alpha")

    assert service.load_exact(reference).record.status == "proposed"
    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        service.require_current_use(reference)


def test_active_account_remains_current_evidence_for_closed_event(tmp_path: Path) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    events = EventWorkflowService(tmp_path)
    draft = events.load_exact(event_ref())
    active = events.replace(
        event_record(status="active", updated_at="2026-08-26T12:05:00-04:00"),
        expected=draft.fingerprint,
    )
    events.replace(
        event_record(status="closed", updated_at="2026-08-26T12:10:00-04:00"),
        expected=active.fingerprint,
    )
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account_record())

    current = service.require_current_use(account_reference(event_ref(), "acct_alpha"))

    assert current.record.status == "active"


def test_v1_account_remains_current_use_eligible_without_migration(tmp_path: Path) -> None:
    _draft_event_with_unknown_participant(tmp_path)
    fixture = Path(
        "tests/schema_validation/fixtures/issue-15/account/valid/minimum-active.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    value["target"]["record_ref"]["record_id"] = "ep_alpha"
    value["source"] = {"kind": "local_operator", "display_label": "Synthetic Teacher"}
    account = parse_portia_record("account", "1", value)
    repository = AccountWorkflowService(tmp_path).repository
    repository.create_work_record(event_ref(), account)
    service = AccountWorkflowService(tmp_path, repository=repository)

    current = service.require_current_use(
        account_reference(event_ref(), "acct_student_report_1", version="1")
    )

    assert current.record.contract_version == "1"
