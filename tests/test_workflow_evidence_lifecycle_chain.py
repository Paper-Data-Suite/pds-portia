from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    account_reference,
)
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.evidence_lifecycle import (
    build_evidence_lifecycle_transition,
    evidence_lifecycle_state,
    require_evidence_lifecycle_reconciled,
)
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


def _setup(root: Path, record: PortiaRecord) -> tuple[PortiaRepository, PortiaRecord]:
    EventWorkflowService(root).create(event_record(status="draft"))
    repository = PortiaRepository(root)
    repository.create_work_record(event_ref(), record)
    return repository, record


def test_no_lifecycle_history_is_valid_for_initial_canonical_status(tmp_path: Path) -> None:
    repository, account = _setup(tmp_path, _account(status="active"))

    state = require_evidence_lifecycle_reconciled(repository, event_ref(), account)

    assert state.transitions == ()
    assert state.head is None
    assert state.selected_status is None


def test_build_first_activation_transition_has_no_previous(tmp_path: Path) -> None:
    repository, account = _setup(tmp_path, _account())
    candidate = _revised(account, status="active", updated_at=LATER)

    transition = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        account,
        candidate,
        transition_id="lct_activate_alpha",
        reason_code="review_completed",
    )

    assert transition.field("previous_transition") is None
    assert transition.field("target") == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "account",
            "record_id": "acct_alpha",
            "contract_version": "2",
        },
    }
    assert transition.field("from_status") == "proposed"
    assert transition.field("to_status") == "active"
    assert transition.field("reason") == {
        "category": "workflow",
        "code": "review_completed",
    }


def test_next_transition_points_to_selected_history_head(tmp_path: Path) -> None:
    repository, proposed = _setup(tmp_path, _account())
    active = _revised(proposed, status="active", updated_at=LATER)
    activation = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        proposed,
        active,
        transition_id="lct_activate_alpha",
        reason_code="review_completed",
    )
    repository.create_work_record(event_ref(), activation)
    prior = repository.load_work_record(event_ref(), "account", "2", "acct_alpha")
    stored_active = repository.replace_work_record(
        event_ref(), active, expected=prior.fingerprint
    )
    invalidated = _revised(active, status="invalidated", updated_at=LATER_STILL)

    transition = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        stored_active.record,
        invalidated,
        transition_id="lct_invalidate_alpha",
        reason_code="recording_error",
    )

    previous = transition.field("previous_transition")
    assert previous is not None
    assert previous["record_id"] == "lct_activate_alpha"
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "invalidated"


def test_lifecycle_chain_rejects_two_roots(tmp_path: Path) -> None:
    repository, account = _setup(tmp_path, _account(status="active"))
    invalidated = _revised(account, status="invalidated", updated_at=LATER)
    first = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        account,
        invalidated,
        transition_id="lct_first",
        reason_code="wrong_source",
    )
    duplicate_root_data = first.to_dict()
    duplicate_root_data["transition_id"] = "lct_second"
    duplicate_root = parse_portia_record(
        "lifecycle_transition", "1", duplicate_root_data
    )
    repository.create_work_record(event_ref(), first)
    repository.create_work_record(event_ref(), duplicate_root)

    with pytest.raises(WorkflowPrerequisiteError, match="exactly one root"):
        evidence_lifecycle_state(repository, event_ref(), account)


def test_lifecycle_chain_rejects_missing_predecessor(tmp_path: Path) -> None:
    repository, account = _setup(tmp_path, _account(status="active"))
    invalidated = _revised(account, status="invalidated", updated_at=LATER)
    transition = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        account,
        invalidated,
        transition_id="lct_invalidate_alpha",
        reason_code="wrong_target",
    )
    data = transition.to_dict()
    data["previous_transition"] = {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_missing",
        "contract_version": "1",
    }
    repository.create_work_record(
        event_ref(), parse_portia_record("lifecycle_transition", "1", data)
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing predecessor"):
        evidence_lifecycle_state(repository, event_ref(), account)


def test_current_use_fails_closed_when_history_head_disagrees_with_account(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    created = service.create(event_ref(), _account(status="active"))
    invalidated = _revised(created.record, status="invalidated", updated_at=LATER)
    transition = build_evidence_lifecycle_transition(
        service.repository,
        event_ref(),
        created.record,
        invalidated,
        transition_id="lct_invalidate_alpha",
        reason_code="invalid_provenance",
    )
    service.repository.create_work_record(event_ref(), transition)

    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_current_use(account_reference(event_ref(), "acct_alpha"))


def test_retraction_and_supersession_remain_deferred(tmp_path: Path) -> None:
    repository, active = _setup(tmp_path, _account(status="active"))
    retracted = _revised(active, status="retracted", updated_at=LATER)
    with pytest.raises(WorkflowPrerequisiteError, match="retraction"):
        build_evidence_lifecycle_transition(
            repository,
            event_ref(),
            active,
            retracted,
            transition_id="lct_retract_alpha",
            reason_code="source_retracted",
        )

    superseded = _revised(active, status="superseded", updated_at=LATER)
    with pytest.raises(WorkflowPrerequisiteError, match="supersession"):
        build_evidence_lifecycle_transition(
            repository,
            event_ref(),
            active,
            superseded,
            transition_id="lct_supersede_alpha",
            reason_code="corrected_by_successor",
        )


def test_observation_invalidation_uses_observation_reason_vocabulary(
    tmp_path: Path,
) -> None:
    repository, observation = _setup(tmp_path, _observation())
    invalidated = _revised(observation, status="invalidated", updated_at=LATER)

    transition = build_evidence_lifecycle_transition(
        repository,
        event_ref(),
        observation,
        invalidated,
        transition_id="lct_obs_invalid",
        reason_code="wrong_observer",
    )
    assert transition.field("reason") == {
        "category": "record_validity",
        "code": "wrong_observer",
    }

    with pytest.raises(WorkflowPrerequisiteError, match="not valid"):
        build_evidence_lifecycle_transition(
            repository,
            event_ref(),
            observation,
            invalidated,
            transition_id="lct_obs_wrong_reason",
            reason_code="wrong_source",
        )


def test_other_reason_requires_nonempty_detail(tmp_path: Path) -> None:
    repository, account = _setup(tmp_path, _account())
    candidate = _revised(account, status="active", updated_at=LATER)

    with pytest.raises(WorkflowPrerequisiteError, match="requires detail"):
        build_evidence_lifecycle_transition(
            repository,
            event_ref(),
            account,
            candidate,
            transition_id="lct_other",
            reason_code="other",
        )
