from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.paths import work_storage_history_path
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

LATER = "2026-08-26T12:05:00-04:00"
LATER_STILL = "2026-08-26T12:10:00-04:00"


def _source(label: str = "Synthetic Source") -> dict[str, object]:
    return {"kind": "local_operator", "display_label": label}


def _account_v2(
    *,
    account_id: str = "acct_alpha",
    status: str = "active",
    source: dict[str, object] | None = None,
    target: dict[str, object] | None = None,
    related_accounts: list[dict[str, object]] | None = None,
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    value: dict[str, object] = {
        "schema_version": "2",
        "record_type": "account",
        "module_id": "portia",
        "class_id": "class_a",
        "work_kind": "event",
        "work_id": "evt_alpha",
        "account_id": account_id,
        "status": status,
        "target": target or {"kind": "event"},
        "source": source or _source(),
        "information_origin": "firsthand",
        "source_certainty": "stated_certain",
        "content": [
            {
                "representation": "recorded_summary",
                "text": f"Synthetic contribution for {account_id}.",
            }
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": updated_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if related_accounts is not None:
        value["related_accounts"] = related_accounts
    return parse_portia_record("account", "2", value)


def _account_v1(*, account_id: str = "acct_v1_alpha") -> PortiaRecord:
    return parse_portia_record(
        "account",
        "1",
        {
            "schema_version": "1",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": "active",
            "target": {"kind": "event"},
            "source": _source(),
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic historical contribution.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _retraction(
    predecessor_id: str,
    *,
    predecessor_version: str = "2",
    account_id: str = "acct_retract_alpha",
    status: str = "active",
    source: dict[str, object] | None = None,
    target: dict[str, object] | None = None,
) -> PortiaRecord:
    return _account_v2(
        account_id=account_id,
        status=status,
        source=source,
        target=target,
        related_accounts=[
            {
                "relation": "retracts",
                "account_ref": {
                    "record_kind": "account",
                    "record_id": predecessor_id,
                    "contract_version": predecessor_version,
                },
            }
        ],
        updated_at=LATER,
    )


def _history_path(root: Path, prior: PortiaRecord, digest: str) -> Path:
    assert prior.logical_id is not None
    return work_storage_history_path(
        root,
        event_ref(),
        "account",
        prior.logical_id,
        digest,
    )


def test_same_source_v2_retraction_creates_new_account_and_retracts_predecessor(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    before = predecessor.path.read_bytes()
    retraction = _retraction("acct_alpha")

    result = service.retract(
        account_reference(event_ref(), "acct_alpha"),
        retraction,
        expected=predecessor.fingerprint,
        transition_id="lct_retract_alpha",
        operation_id="op_retract_alpha",
    )

    assert result.accepted_steps == (
        "step_history",
        "step_retraction",
        "step_transition",
        "step_evidence",
    )
    historical = service.load_exact(account_reference(event_ref(), "acct_alpha"))
    assert historical.record.status == "retracted"
    assert _history_path(
        tmp_path, predecessor.record, predecessor.fingerprint.digest
    ).read_bytes() == before
    current_retraction = service.require_current_use(
        account_reference(event_ref(), "acct_retract_alpha")
    )
    assert current_retraction.record.status == "active"
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_retract_alpha"
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "retracted"
    assert transition.record.field("reason")["code"] == "source_retracted"


def test_v1_predecessor_remains_v1_after_v2_retraction(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.repository.create_work_record(event_ref(), _account_v1())

    service.retract(
        account_reference(event_ref(), "acct_v1_alpha", version="1"),
        _retraction("acct_v1_alpha", predecessor_version="1"),
        expected=predecessor.fingerprint,
        transition_id="lct_retract_v1",
    )

    old = service.load_exact(
        account_reference(event_ref(), "acct_v1_alpha", version="1")
    )
    assert old.record.contract_version == "1"
    assert old.record.status == "retracted"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_retract_alpha")
    ).record.contract_version == "2"


def test_different_source_retraction_is_zero_write(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    before = predecessor.path.read_bytes()

    with pytest.raises(WorkflowPrerequisiteError, match="same represented source"):
        service.retract(
            account_reference(event_ref(), "acct_alpha"),
            _retraction("acct_alpha", source=_source("Different Synthetic Source")),
            expected=predecessor.fingerprint,
            transition_id="lct_retract_alpha",
        )

    assert predecessor.path.read_bytes() == before
    assert not _history_path(
        tmp_path, predecessor.record, predecessor.fingerprint.digest
    ).exists()
    assert not (
        predecessor.path.parent / "acct_retract_alpha.json"
    ).exists()
    assert not (
        predecessor.path.parent.parent
        / "lifecycle_transition/lct_retract_alpha.json"
    ).exists()


@pytest.mark.parametrize(
    ("predecessor_status", "retraction_status", "reason_code", "match"),
    [
        ("proposed", "active", "source_retracted", "active predecessor"),
        ("active", "proposed", "source_retracted", "must be active"),
        ("active", "active", "wrong_source", "source_retracted"),
    ],
)
def test_retraction_preflight_rejects_ineligible_state_or_reason(
    tmp_path: Path,
    predecessor_status: str,
    retraction_status: str,
    reason_code: str,
    match: str,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(
        event_ref(), _account_v2(status=predecessor_status)
    )
    before = predecessor.path.read_bytes()

    with pytest.raises(WorkflowPrerequisiteError, match=match):
        service.retract(
            account_reference(event_ref(), "acct_alpha"),
            _retraction("acct_alpha", status=retraction_status),
            expected=predecessor.fingerprint,
            transition_id="lct_retract_alpha",
            reason_code=reason_code,
        )

    assert predecessor.path.read_bytes() == before
    assert not (predecessor.path.parent / "acct_retract_alpha.json").exists()


def test_unidentified_source_cannot_establish_retraction_identity(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    unidentified = {
        "kind": "unidentified_person",
        "identity_status": "not_recorded",
        "detail": "Synthetic unidentified source",
    }
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(
        event_ref(), _account_v2(source=unidentified)
    )

    with pytest.raises(WorkflowPrerequisiteError, match="cannot establish"):
        service.retract(
            account_reference(event_ref(), "acct_alpha"),
            _retraction("acct_alpha", source=unidentified),
            expected=predecessor.fingerprint,
            transition_id="lct_retract_alpha",
        )


def test_teacher_only_status_toggle_cannot_retract_account(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    candidate_data = deepcopy(predecessor.record.to_dict())
    candidate_data["status"] = "retracted"
    candidate_data["updated_at"] = LATER
    candidate = parse_portia_record("account", "2", candidate_data)

    with pytest.raises(WorkflowPrerequisiteError, match="source-evidenced"):
        service.transition_lifecycle(
            account_reference(event_ref(), "acct_alpha"),
            candidate,
            expected=predecessor.fingerprint,
            transition_id="lct_toggle_retract",
            reason_code="source_retracted",
        )

    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "active"


def test_retraction_does_not_mutate_role_and_role_current_use_fails(
    tmp_path: Path,
) -> None:
    events = EventWorkflowService(tmp_path)
    draft = events.create(event_record(status="draft"))
    ParticipantWorkflowService(tmp_path).create(
        event_ref(),
        participant_record(
            subject={"kind": "unknown_person", "reason": "identity_not_known"}
        ),
    )
    events.replace(
        event_record(status="active", updated_at=LATER),
        expected=draft.fingerprint,
    )
    participant_target = {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_alpha",
            "contract_version": "3",
        },
    }
    accounts = AccountWorkflowService(tmp_path)
    predecessor = accounts.create(
        event_ref(), _account_v2(target=participant_target)
    )
    roles = RoleWorkflowService(tmp_path)
    role = roles.create(
        event_ref(),
        role_record(
            role_type="reported_involved",
            basis=[
                {
                    "kind": "account_ref",
                    "record_ref": {
                        "record_kind": "account",
                        "record_id": "acct_alpha",
                        "contract_version": "2",
                    },
                }
            ],
        ),
    )
    before_role = role.path.read_bytes()
    assert roles.require_current_use(
        role_reference(event_ref(), "epr_alpha")
    ).record.status == "active"

    accounts.retract(
        account_reference(event_ref(), "acct_alpha"),
        _retraction("acct_alpha", target=participant_target),
        expected=predecessor.fingerprint,
        transition_id="lct_retract_role_basis",
    )

    assert role.path.read_bytes() == before_role
    with pytest.raises(WorkflowPrerequisiteError, match="active, attributable"):
        roles.require_current_use(role_reference(event_ref(), "epr_alpha"))
