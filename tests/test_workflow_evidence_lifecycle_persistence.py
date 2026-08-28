from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import (
    PortiaConflictError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.paths import work_storage_history_path
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    account_reference,
    observation_reference,
)
from portia.workflows.evidence_lifecycle import require_evidence_lifecycle_reconciled
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

LATER = "2026-08-26T12:05:00-04:00"
LATER_STILL = "2026-08-26T12:10:00-04:00"


def _account(*, status: str = "proposed", updated_at: str = TIMESTAMP) -> PortiaRecord:
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
            "account_id": "acct_alpha",
            "status": status,
            "target": {"kind": "event"},
            "source": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic source contribution.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _observation(*, status: str = "active", updated_at: str = TIMESTAMP) -> PortiaRecord:
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
            "observation_id": "obs_alpha",
            "status": status,
            "target": {"kind": "event"},
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "method": "live_direct",
            "content": {"narrative": "Synthetic directly observed information."},
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _revised(record: PortiaRecord, *, status: str, updated_at: str) -> PortiaRecord:
    data = deepcopy(record.to_dict())
    data["status"] = status
    data["updated_at"] = updated_at
    return parse_portia_record(record.contract, record.contract_version, data)


def _history_path(root: Path, record: PortiaRecord, digest: str) -> Path:
    assert record.logical_id is not None
    return work_storage_history_path(
        root,
        event_ref(),
        record.contract,
        record.logical_id,
        digest,
    )


def test_account_activation_coordinates_history_transition_and_replacement(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    created = service.create(event_ref(), _account())
    prior_bytes = created.path.read_bytes()
    candidate = _revised(created.record, status="active", updated_at=LATER)

    result = service.transition_lifecycle(
        account_reference(event_ref(), "acct_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_activate_alpha",
        reason_code="review_completed",
        operation_id="op_account_activate_alpha",
    )

    assert result.accepted_steps == (
        "step_history",
        "step_transition",
        "step_evidence",
    )
    history = _history_path(tmp_path, created.record, created.fingerprint.digest)
    assert history.read_bytes() == prior_bytes
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_activate_alpha"
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"
    current = service.load_exact(account_reference(event_ref(), "acct_alpha"))
    assert current.record.status == "active"
    state = require_evidence_lifecycle_reconciled(
        service.repository, event_ref(), current.record
    )
    assert state.selected_status == "active"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "active"


def test_second_account_transition_links_previous_head_and_preserves_active_bytes(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    proposed = service.create(event_ref(), _account())
    active_candidate = _revised(proposed.record, status="active", updated_at=LATER)
    service.transition_lifecycle(
        account_reference(event_ref(), "acct_alpha"),
        active_candidate,
        expected=proposed.fingerprint,
        transition_id="lct_activate_alpha",
        reason_code="review_completed",
    )
    active = service.load_exact(account_reference(event_ref(), "acct_alpha"))
    active_bytes = active.path.read_bytes()
    invalidated = _revised(
        active.record, status="invalidated", updated_at=LATER_STILL
    )

    service.transition_lifecycle(
        account_reference(event_ref(), "acct_alpha"),
        invalidated,
        expected=active.fingerprint,
        transition_id="lct_invalidate_alpha",
        reason_code="wrong_source",
    )

    history = _history_path(tmp_path, active.record, active.fingerprint.digest)
    assert history.read_bytes() == active_bytes
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_invalidate_alpha"
    )
    previous = transition.record.field("previous_transition")
    assert previous is not None
    assert previous["record_id"] == "lct_activate_alpha"
    current = service.load_exact(account_reference(event_ref(), "acct_alpha"))
    assert current.record.status == "invalidated"
    assert require_evidence_lifecycle_reconciled(
        service.repository, event_ref(), current.record
    ).selected_status == "invalidated"


def test_stale_expected_fingerprint_writes_nothing(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    created = service.create(event_ref(), _account())
    before = created.path.read_bytes()
    candidate = _revised(created.record, status="active", updated_at=LATER)
    stale = ContentFingerprint(
        algorithm="sha256",
        digest="0" * 64,
        byte_length=created.fingerprint.byte_length,
    )

    with pytest.raises(PortiaConflictError, match="expected evidence state"):
        service.transition_lifecycle(
            account_reference(event_ref(), "acct_alpha"),
            candidate,
            expected=stale,
            transition_id="lct_activate_alpha",
            reason_code="review_completed",
        )

    assert created.path.read_bytes() == before
    assert not _history_path(tmp_path, created.record, created.fingerprint.digest).exists()
    assert not (
        created.path.parent.parent / "lifecycle_transition/lct_activate_alpha.json"
    ).exists()


def test_partial_commit_after_history_preserves_recovery_evidence(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    created = service.create(event_ref(), _account())
    before = created.path.read_bytes()
    candidate = _revised(created.record, status="active", updated_at=LATER)

    def fail_after_history(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_history":
            raise RuntimeError("synthetic lifecycle partial commit")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        service.transition_lifecycle(
            account_reference(event_ref(), "acct_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_activate_alpha",
            reason_code="review_completed",
            operation_id="op_account_partial_alpha",
            fault_hook=fail_after_history,
        )

    assert exc_info.value.accepted_steps == ("step_history",)
    assert _history_path(
        tmp_path, created.record, created.fingerprint.digest
    ).read_bytes() == before
    assert created.path.read_bytes() == before
    assert not (
        created.path.parent.parent / "lifecycle_transition/lct_activate_alpha.json"
    ).exists()


def test_observation_invalidation_uses_same_coordinated_persistence(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ObservationWorkflowService(tmp_path)
    created = service.create(event_ref(), _observation())
    candidate = _revised(created.record, status="invalidated", updated_at=LATER)

    result = service.transition_lifecycle(
        observation_reference(event_ref(), "obs_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_obs_invalid",
        reason_code="wrong_observer",
    )

    assert result.accepted_steps[-2:] == ("step_transition", "step_evidence")
    current = service.load_exact(observation_reference(event_ref(), "obs_alpha"))
    assert current.record.status == "invalidated"
    assert require_evidence_lifecycle_reconciled(
        service.repository, event_ref(), current.record
    ).selected_status == "invalidated"
