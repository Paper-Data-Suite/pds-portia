from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import parse_portia_record
from portia.storage import PortiaRepository
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    RoleWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    role_reference,
)
from tests.workflow_helpers import (
    account_wire,
    event_record,
    event_ref,
    participant_record,
    role_record,
)


def _seed(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    events = EventWorkflowService(root)
    created = events.create(event_record(status="draft"))
    ParticipantWorkflowService(root).create(event_ref(), participant_record())
    events.replace(
        event_record(updated_at="2026-08-26T12:05:00-04:00"),
        expected=created.fingerprint,
    )


def _reported(account_id: str = "acct_alpha", version: str = "1") -> object:
    return role_record(
        role_type="reported_involved",
        basis=[
            {
                "kind": "account_ref",
                "record_ref": {
                    "record_kind": "account",
                    "record_id": account_id,
                    "contract_version": version,
                },
            }
        ],
    )


def test_role_is_optional_and_neutral_present_role_round_trips(tmp_path: Path) -> None:
    _seed(tmp_path)
    service = RoleWorkflowService(tmp_path)
    assert service.list(event_ref()) == ()
    service.create(event_ref(), role_record())
    assert service.require_current_use(
        role_reference(event_ref(), "epr_alpha")
    ).record.field("role_type") == "present"


def test_reported_involved_requires_qualifying_exact_account(tmp_path: Path) -> None:
    _seed(tmp_path)
    service = RoleWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError):
        service.create(event_ref(), _reported())  # type: ignore[arg-type]

    account = parse_portia_record("account", "1", account_wire())
    PortiaRepository(tmp_path).create_work_record(event_ref(), account)
    service.create(event_ref(), _reported())  # type: ignore[arg-type]
    assert service.list_for_participant(event_ref(), "ep_alpha")


@pytest.mark.parametrize(
    ("status", "participant_id", "source_kind"),
    [
        ("retracted", "ep_alpha", "local_operator"),
        ("active", "ep_other", "local_operator"),
        ("active", "ep_alpha", "unidentified_person"),
    ],
)
def test_nonqualifying_account_cannot_activate_role(
    tmp_path: Path, status: str, participant_id: str, source_kind: str
) -> None:
    _seed(tmp_path)
    account = parse_portia_record(
        "account",
        "1",
        account_wire(
            status=status,
            participant_id=participant_id,
            source_kind=source_kind,
        ),
    )
    PortiaRepository(tmp_path).create_work_record(event_ref(), account)
    with pytest.raises(WorkflowPrerequisiteError):
        RoleWorkflowService(tmp_path).create(
            event_ref(), _reported()  # type: ignore[arg-type]
        )


def test_wrong_version_or_other_event_account_does_not_qualify(tmp_path: Path) -> None:
    _seed(tmp_path)
    repository = PortiaRepository(tmp_path)
    account = parse_portia_record("account", "1", account_wire())
    stored = repository.create_work_record(event_ref(), account)
    with pytest.raises(WorkflowPrerequisiteError):
        RoleWorkflowService(tmp_path).create(
            event_ref(), _reported(version="2")  # type: ignore[arg-type]
        )
    assert repository.load_work_record(
        event_ref(), "account", "1", "acct_alpha"
    ).fingerprint == stored.fingerprint

    EventWorkflowService(tmp_path).create(
        event_record(event_id="evt_beta", status="draft")
    )
    other_wire = account_wire(account_id="acct_other")
    other_wire["work_id"] = "evt_beta"
    other = parse_portia_record("account", "1", other_wire)
    repository.create_work_record(event_ref(event_id="evt_beta"), other)
    with pytest.raises(WorkflowPrerequisiteError):
        RoleWorkflowService(tmp_path).create(
            event_ref(), _reported(account_id="acct_other")  # type: ignore[arg-type]
        )


def test_persisted_role_cannot_be_retargeted_in_place(tmp_path: Path) -> None:
    _seed(tmp_path)
    participants = ParticipantWorkflowService(tmp_path)
    participants.create(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    service = RoleWorkflowService(tmp_path)
    created = service.create(event_ref(), role_record())
    with pytest.raises(WorkflowOwnershipError):
        service.replace(
            event_ref(),
            role_record(participant_id="ep_other"),
            expected=created.fingerprint,
        )
    assert service.load_exact(role_reference(event_ref(), "epr_alpha")).record.field(
        "target"
    )["record_ref"]["record_id"] == "ep_alpha"


def test_active_role_is_accepted_under_draft_event_but_is_not_current(
    tmp_path: Path,
) -> None:
    write_class_roster(
        tmp_path,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    ParticipantWorkflowService(tmp_path).create(event_ref(), participant_record())
    service = RoleWorkflowService(tmp_path)
    created = service.create(event_ref(), role_record())
    assert created.record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError):
        service.require_current_use(role_reference(event_ref(), "epr_alpha"))


def test_role_lifecycle_provenance_and_active_assertion_are_immutable(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    service = RoleWorkflowService(tmp_path)
    created = service.create(event_ref(), role_record())
    canonical = created.path.read_bytes()
    for candidate in (
        role_record(
            role_type="directly_involved",
            updated_at="2026-08-26T12:10:00-04:00",
        ),
        role_record(
            created_at="2026-08-26T12:00:01-04:00",
            updated_at="2026-08-26T12:10:00-04:00",
        ),
    ):
        with pytest.raises(WorkflowPrerequisiteError):
            service.replace(event_ref(), candidate, expected=created.fingerprint)
        assert created.path.read_bytes() == canonical

    terminal = service.replace(
        event_ref(),
        role_record(status="invalidated", updated_at="2026-08-26T12:10:00-04:00"),
        expected=created.fingerprint,
    )
    terminal_bytes = terminal.path.read_bytes()
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            event_ref(),
            role_record(updated_at="2026-08-26T12:15:00-04:00"),
            expected=terminal.fingerprint,
        )
    assert terminal.path.read_bytes() == terminal_bytes
