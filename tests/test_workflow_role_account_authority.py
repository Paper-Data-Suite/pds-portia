from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaOperationPartialCommitError
from portia.storage.fingerprint import fingerprint_bytes
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    RoleWorkflowService,
    WorkflowPrerequisiteError,
    account_reference,
    role_reference,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
    role_record,
)

LATER = "2026-08-28T10:50:00-04:00"


def _seed_active_event(root: Path) -> None:
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
    draft = events.create(event_record(status="draft"))
    ParticipantWorkflowService(root).create(event_ref(), participant_record())
    events.replace(
        event_record(status="active", updated_at="2026-08-26T12:05:00-04:00"),
        expected=draft.fingerprint,
    )


def _workspace_artifact(
    root: Path,
    *,
    relative_path: str = "source-artifacts/role-basis.txt",
    content: bytes = b"Synthetic role basis artifact.\n",
) -> dict[str, object]:
    path = root.joinpath(*relative_path.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "kind": "workspace_file",
        "path": relative_path,
        "fingerprint": fingerprint_bytes(content).to_dict(),
    }


def _account(
    *,
    account_id: str = "acct_alpha",
    source_artifacts: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    value: dict[str, object] = {
        "schema_version": "2",
        "record_type": "account",
        "module_id": "portia",
        "class_id": "class_a",
        "work_kind": "event",
        "work_id": "evt_alpha",
        "account_id": account_id,
        "status": "active",
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
        "source": {
            "kind": "local_operator",
            "display_label": "Synthetic Source",
        },
        "information_origin": "firsthand",
        "source_certainty": "stated_certain",
        "content": [
            {
                "representation": "recorded_summary",
                "text": "Synthetic role-basis source contribution.",
            }
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if source_artifacts is not None:
        value["source_artifacts"] = source_artifacts
    return parse_portia_record("account", "2", value)


def _reported_role(*account_ids: str) -> PortiaRecord:
    return role_record(
        role_type="reported_involved",
        basis=[
            {
                "kind": "account_ref",
                "record_ref": {
                    "record_kind": "account",
                    "record_id": account_id,
                    "contract_version": "2",
                },
            }
            for account_id in account_ids
        ],
    )


def _revised(record: PortiaRecord, *, status: str) -> PortiaRecord:
    value = record.to_dict()
    value["status"] = status
    value["updated_at"] = LATER
    return parse_portia_record(record.contract, record.contract_version, value)


def test_reported_involved_rechecks_workspace_artifact_authority(
    tmp_path: Path,
) -> None:
    _seed_active_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    accounts = AccountWorkflowService(tmp_path)
    accounts.create(event_ref(), _account(source_artifacts=[artifact]))
    roles = RoleWorkflowService(tmp_path)
    role = roles.create(event_ref(), _reported_role("acct_alpha"))
    role_bytes = role.path.read_bytes()

    assert roles.require_current_use(
        role_reference(event_ref(), "epr_alpha")
    ).record.status == "active"

    (tmp_path / "source-artifacts/role-basis.txt").write_bytes(
        b"Changed after the Role was created.\n"
    )

    with pytest.raises(WorkflowPrerequisiteError, match="active, attributable"):
        roles.require_current_use(role_reference(event_ref(), "epr_alpha"))
    assert role.path.read_bytes() == role_bytes


def test_reported_involved_rechecks_account_lifecycle_reconciliation(
    tmp_path: Path,
) -> None:
    _seed_active_event(tmp_path)
    accounts = AccountWorkflowService(tmp_path)
    predecessor = accounts.create(event_ref(), _account())
    roles = RoleWorkflowService(tmp_path)
    role = roles.create(event_ref(), _reported_role("acct_alpha"))
    role_bytes = role.path.read_bytes()

    def fail_after_transition(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_transition":
            raise RuntimeError("synthetic lifecycle partial commit")

    with pytest.raises(PortiaOperationPartialCommitError):
        accounts.transition_lifecycle(
            account_reference(event_ref(), "acct_alpha"),
            _revised(predecessor.record, status="invalidated"),
            expected=predecessor.fingerprint,
            transition_id="lct_invalidate_role_basis",
            reason_code="wrong_source",
            operation_id="op_role_basis_partial",
            fault_hook=fail_after_transition,
        )

    # The canonical Account bytes remain active, but the accepted lifecycle head
    # says invalidated.  Role current-use must honor the Account reconciliation
    # failure rather than reading status alone.
    assert accounts.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="active, attributable"):
        roles.require_current_use(role_reference(event_ref(), "epr_alpha"))
    assert role.path.read_bytes() == role_bytes


def test_one_stale_account_does_not_poison_another_qualifying_basis(
    tmp_path: Path,
) -> None:
    _seed_active_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    accounts = AccountWorkflowService(tmp_path)
    accounts.create(
        event_ref(),
        _account(account_id="acct_stale", source_artifacts=[artifact]),
    )
    accounts.create(event_ref(), _account(account_id="acct_current"))
    roles = RoleWorkflowService(tmp_path)
    roles.create(
        event_ref(),
        _reported_role("acct_stale", "acct_current"),
    )

    (tmp_path / "source-artifacts/role-basis.txt").write_bytes(
        b"Changed after the Role was created.\n"
    )

    assert roles.require_current_use(
        role_reference(event_ref(), "epr_alpha")
    ).record.status == "active"
