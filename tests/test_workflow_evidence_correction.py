from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaOperationPartialCommitError
from portia.storage.paths import work_storage_history_path
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    account_reference,
    observation_reference,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

LATER = "2026-08-26T12:05:00-04:00"
LATER_STILL = "2026-08-26T12:10:00-04:00"


def _supersedes(
    family: str,
    record_id: str,
    version: str,
    reason: str,
) -> list[dict[str, object]]:
    return [
        {
            "work_record_ref": {
                "work_ref": event_ref().to_dict(),
                "record_ref": {
                    "record_kind": family,
                    "record_id": record_id,
                    "contract_version": version,
                },
            },
            "reason": reason,
        }
    ]


def _account_v2(
    *,
    account_id: str = "acct_alpha",
    content: str = "Synthetic source contribution.",
    supersedes: list[dict[str, object]] | None = None,
    status: str = "active",
    timestamp: str = TIMESTAMP,
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
        "target": {"kind": "event"},
        "source": {"kind": "local_operator", "display_label": "Synthetic Source"},
        "information_origin": "firsthand",
        "source_certainty": "stated_certain",
        "content": [{"representation": "recorded_summary", "text": content}],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": AGENT,
        "updated_at": timestamp,
        "updated_by": AGENT,
    }
    if supersedes is not None:
        value["supersedes"] = supersedes
    return parse_portia_record("account", "2", value)


def _account_v1() -> PortiaRecord:
    value = _account_v2().to_dict()
    value["schema_version"] = "1"
    value.pop("work_kind")
    return parse_portia_record("account", "1", value)


def _observation_v2(
    *,
    observation_id: str = "obs_alpha",
    narrative: str = "Synthetic directly observed information.",
    supersedes: list[dict[str, object]] | None = None,
    status: str = "active",
    timestamp: str = TIMESTAMP,
) -> PortiaRecord:
    value: dict[str, object] = {
        "schema_version": "2",
        "record_type": "observation",
        "module_id": "portia",
        "class_id": "class_a",
        "work_kind": "event",
        "work_id": "evt_alpha",
        "observation_id": observation_id,
        "status": status,
        "target": {"kind": "event"},
        "observer": {
            "kind": "human",
            "human_attribution": {
                "kind": "local_operator",
                "display_label": "Synthetic Observer",
            },
        },
        "method": "live_direct",
        "content": {"narrative": narrative},
        "observation_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": AGENT,
        "updated_at": timestamp,
        "updated_by": AGENT,
    }
    if supersedes is not None:
        value["supersedes"] = supersedes
    return parse_portia_record("observation", "2", value)


def _observation_v1() -> PortiaRecord:
    value = _observation_v2().to_dict()
    value["schema_version"] = "1"
    value.pop("work_kind")
    return parse_portia_record("observation", "1", value)


def _history_path(root: Path, record: PortiaRecord, digest: str) -> Path:
    assert record.logical_id is not None
    return work_storage_history_path(
        root,
        event_ref(),
        record.contract,
        record.logical_id,
        digest,
    )


def test_v2_account_material_correction_creates_active_successor(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    prior_bytes = predecessor.path.read_bytes()
    successor = _account_v2(
        account_id="acct_corrected",
        content="Corrected synthetic source contribution.",
        supersedes=_supersedes(
            "account", "acct_alpha", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )

    result = service.correct(
        account_reference(event_ref(), "acct_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_account",
        operation_id="op_correct_account",
    )

    assert result.accepted_steps == (
        "step_history",
        "step_successor",
        "step_transition",
        "step_evidence",
    )
    historical = service.load_exact(account_reference(event_ref(), "acct_alpha"))
    assert historical.record.status == "superseded"
    assert _history_path(
        tmp_path, predecessor.record, predecessor.fingerprint.digest
    ).read_bytes() == prior_bytes
    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        service.require_current_use(account_reference(event_ref(), "acct_alpha"))
    current = service.require_current_use(
        account_reference(event_ref(), "acct_corrected")
    )
    assert current.record.field("content")[0]["text"].startswith("Corrected")
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_correct_account"
    )
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason")["code"] == "corrected_by_successor"


def test_v1_account_predecessor_remains_v1_after_v2_correction(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.repository.create_work_record(event_ref(), _account_v1())
    successor = _account_v2(
        account_id="acct_corrected",
        content="Corrected v1 synthetic contribution.",
        supersedes=_supersedes(
            "account", "acct_alpha", "1", "statement_corrected"
        ),
        timestamp=LATER,
    )

    service.correct(
        account_reference(event_ref(), "acct_alpha", version="1"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_account_v1",
    )

    old = service.load_exact(
        account_reference(event_ref(), "acct_alpha", version="1")
    )
    assert old.record.contract_version == "1"
    assert old.record.status == "superseded"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_corrected")
    ).record.contract_version == "2"


def test_v2_observation_material_correction_creates_active_successor(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ObservationWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _observation_v2())
    successor = _observation_v2(
        observation_id="obs_corrected",
        narrative="Corrected synthetic directly observed information.",
        supersedes=_supersedes(
            "observation",
            "obs_alpha",
            "2",
            "observation_content_corrected",
        ),
        timestamp=LATER,
    )

    service.correct(
        observation_reference(event_ref(), "obs_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_observation",
    )

    old = service.load_exact(observation_reference(event_ref(), "obs_alpha"))
    assert old.record.status == "superseded"
    current = service.require_current_use(
        observation_reference(event_ref(), "obs_corrected")
    )
    assert current.record.field("content")["narrative"].startswith("Corrected")


def test_v1_observation_predecessor_remains_v1_after_v2_correction(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ObservationWorkflowService(tmp_path)
    predecessor = service.repository.create_work_record(event_ref(), _observation_v1())
    successor = _observation_v2(
        observation_id="obs_corrected",
        narrative="Corrected historical observation.",
        supersedes=_supersedes(
            "observation",
            "obs_alpha",
            "1",
            "observation_content_corrected",
        ),
        timestamp=LATER,
    )

    service.correct(
        observation_reference(event_ref(), "obs_alpha", version="1"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_observation_v1",
    )

    old = service.load_exact(
        observation_reference(event_ref(), "obs_alpha", version="1")
    )
    assert old.record.contract_version == "1"
    assert old.record.status == "superseded"
    assert service.require_current_use(
        observation_reference(event_ref(), "obs_corrected")
    ).record.contract_version == "2"


def test_wrong_exact_predecessor_is_rejected_before_any_write(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    before = predecessor.path.read_bytes()
    successor = _account_v2(
        account_id="acct_corrected",
        supersedes=_supersedes(
            "account", "acct_other", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )

    with pytest.raises(WorkflowOwnershipError, match="exact selected predecessor"):
        service.correct(
            account_reference(event_ref(), "acct_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_correct_account",
        )

    assert predecessor.path.read_bytes() == before
    assert not (predecessor.path.parent / "acct_corrected.json").exists()
    assert not _history_path(
        tmp_path, predecessor.record, predecessor.fingerprint.digest
    ).exists()


def test_material_correction_rejects_multiple_predecessors(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    supersedes = _supersedes(
        "account", "acct_alpha", "2", "statement_corrected"
    )
    supersedes.extend(
        _supersedes("account", "acct_alpha", "1", "statement_corrected")
    )
    successor = _account_v2(
        account_id="acct_corrected",
        supersedes=supersedes,
        timestamp=LATER,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="exactly one"):
        service.correct(
            account_reference(event_ref(), "acct_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_correct_account",
        )


def test_partial_correction_successor_is_not_current_before_predecessor_supersession(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    successor = _account_v2(
        account_id="acct_corrected",
        content="Corrected synthetic source contribution.",
        supersedes=_supersedes(
            "account", "acct_alpha", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )

    def fail_after_successor(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_successor":
            raise RuntimeError("synthetic correction partial commit")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        service.correct(
            account_reference(event_ref(), "acct_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_correct_account",
            operation_id="op_correct_partial",
            fault_hook=fail_after_successor,
        )

    assert exc_info.value.accepted_steps == ("step_history", "step_successor")
    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="predecessor to be superseded"):
        service.require_current_use(
            account_reference(event_ref(), "acct_corrected")
        )


def test_material_correction_rejects_clone_without_evidence_change(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    successor = _account_v2(
        account_id="acct_corrected",
        supersedes=_supersedes(
            "account", "acct_alpha", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="primary-evidence change"):
        service.correct(
            account_reference(event_ref(), "acct_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_correct_account",
        )

    assert not (predecessor.path.parent / "acct_corrected.json").exists()


def test_second_material_correction_resolves_exact_supersession_ancestry(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    first = service.create(event_ref(), _account_v2())
    second_record = _account_v2(
        account_id="acct_corrected",
        content="First corrected contribution.",
        supersedes=_supersedes(
            "account", "acct_alpha", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )
    service.correct(
        account_reference(event_ref(), "acct_alpha"),
        second_record,
        expected=first.fingerprint,
        transition_id="lct_correct_account",
    )
    second = service.load_exact(
        account_reference(event_ref(), "acct_corrected")
    )
    third_record = _account_v2(
        account_id="acct_corrected_again",
        content="Second corrected contribution.",
        supersedes=_supersedes(
            "account", "acct_corrected", "2", "statement_corrected"
        ),
        timestamp=LATER_STILL,
    )

    service.correct(
        account_reference(event_ref(), "acct_corrected"),
        third_record,
        expected=second.fingerprint,
        transition_id="lct_correct_account_again",
    )

    assert service.load_exact(
        account_reference(event_ref(), "acct_corrected")
    ).record.status == "superseded"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_corrected_again")
    ).record.status == "active"


def test_corrected_successor_can_later_transition_without_losing_exact_ancestry(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account_v2())
    successor = _account_v2(
        account_id="acct_corrected",
        content="Corrected synthetic source contribution.",
        supersedes=_supersedes(
            "account", "acct_alpha", "2", "statement_corrected"
        ),
        timestamp=LATER,
    )
    service.correct(
        account_reference(event_ref(), "acct_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_account",
    )
    current = service.load_exact(
        account_reference(event_ref(), "acct_corrected")
    )
    candidate_data = deepcopy(current.record.to_dict())
    candidate_data["status"] = "invalidated"
    candidate_data["updated_at"] = LATER_STILL
    candidate = parse_portia_record("account", "2", candidate_data)

    service.transition_lifecycle(
        account_reference(event_ref(), "acct_corrected"),
        candidate,
        expected=current.fingerprint,
        transition_id="lct_invalidate_corrected",
        reason_code="wrong_source",
    )

    exact = service.load_exact(
        account_reference(event_ref(), "acct_corrected")
    )
    assert exact.record.status == "invalidated"
    assert exact.record.field("supersedes")[0]["work_record_ref"]["record_ref"][
        "record_id"
    ] == "acct_alpha"
