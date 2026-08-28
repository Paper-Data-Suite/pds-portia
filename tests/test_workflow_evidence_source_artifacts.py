from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaNotFoundError
from portia.storage.fingerprint import fingerprint_bytes
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    ParticipantWorkflowService,
    WorkflowPrerequisiteError,
    account_reference,
    observation_reference,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
)

LATER = "2026-08-28T10:35:00-04:00"


def _seed_event(root: Path, *, participant: bool = False) -> None:
    EventWorkflowService(root).create(event_record(status="draft"))
    if participant:
        ParticipantWorkflowService(root).create(
            event_ref(),
            participant_record(
                subject={"kind": "unknown_person", "reason": "identity_not_known"}
            ),
        )


def _workspace_artifact(
    root: Path,
    *,
    relative_path: str = "source-artifacts/synthetic-evidence.txt",
    content: bytes = b"Synthetic source artifact.\n",
) -> dict[str, object]:
    path = root.joinpath(*relative_path.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "kind": "workspace_file",
        "path": relative_path,
        "fingerprint": fingerprint_bytes(content).to_dict(),
    }


def _portia_record_artifact(
    *,
    record_kind: str = "event_participant",
    record_id: str = "ep_alpha",
    version: str = "3",
) -> dict[str, object]:
    return {
        "kind": "portia_work_record",
        "work_record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": record_kind,
                "record_id": record_id,
                "contract_version": version,
            },
        },
    }


def _supersedes(
    family: str,
    record_id: str,
    reason: str,
) -> list[dict[str, object]]:
    return [
        {
            "work_record_ref": {
                "work_ref": event_ref().to_dict(),
                "record_ref": {
                    "record_kind": family,
                    "record_id": record_id,
                    "contract_version": "2",
                },
            },
            "reason": reason,
        }
    ]


def _account(
    *,
    account_id: str = "acct_alpha",
    status: str = "active",
    source_artifacts: list[dict[str, object]] | None = None,
    supersedes: list[dict[str, object]] | None = None,
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
        "content": [
            {
                "representation": "recorded_summary",
                "text": "Synthetic source contribution.",
            }
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": AGENT,
        "updated_at": timestamp,
        "updated_by": AGENT,
    }
    if source_artifacts is not None:
        value["source_artifacts"] = source_artifacts
    if supersedes is not None:
        value["supersedes"] = supersedes
    return parse_portia_record("account", "2", value)


def _observation(
    *,
    observation_id: str = "obs_alpha",
    status: str = "active",
    method: str = "artifact_review",
    source_artifacts: list[dict[str, object]] | None = None,
    supersedes: list[dict[str, object]] | None = None,
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
        "method": method,
        "content": {"narrative": "Synthetic directly observed artifact content."},
        "observation_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": AGENT,
        "updated_at": timestamp,
        "updated_by": AGENT,
    }
    if source_artifacts is not None:
        value["source_artifacts"] = source_artifacts
    if supersedes is not None:
        value["supersedes"] = supersedes
    return parse_portia_record("observation", "2", value)


def test_artifact_review_workspace_file_is_current_use_eligible(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    service = ObservationWorkflowService(tmp_path)

    created = service.create(
        event_ref(),
        _observation(source_artifacts=[artifact]),
    )
    current = service.require_current_use(
        observation_reference(event_ref(), "obs_alpha")
    )

    assert created.record.field("method") == "artifact_review"
    assert current.record.logical_id == "obs_alpha"


def test_artifact_review_requires_source_artifact_before_write(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    service = ObservationWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="requires at least one"):
        service.create(event_ref(), _observation(source_artifacts=None))

    assert not (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/observation/obs_alpha.json"
    ).exists()


def test_workspace_file_fingerprint_mismatch_rejects_before_write(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    path = tmp_path / "source-artifacts/synthetic-evidence.txt"
    path.write_bytes(b"Changed before evidence creation.\n")

    with pytest.raises(WorkflowPrerequisiteError, match="fingerprint"):
        ObservationWorkflowService(tmp_path).create(
            event_ref(),
            _observation(source_artifacts=[artifact]),
        )

    assert not (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/observation/obs_alpha.json"
    ).exists()


def test_workspace_file_change_blocks_current_use_but_not_exact_history(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    service = ObservationWorkflowService(tmp_path)
    service.create(event_ref(), _observation(source_artifacts=[artifact]))
    reference = observation_reference(event_ref(), "obs_alpha")

    (tmp_path / "source-artifacts/synthetic-evidence.txt").write_bytes(
        b"Changed after evidence creation.\n"
    )

    assert service.load_exact(reference).record.logical_id == "obs_alpha"
    with pytest.raises(WorkflowPrerequisiteError, match="fingerprint"):
        service.require_current_use(reference)


def test_exact_portia_work_record_artifact_resolves_without_dereference(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path, participant=True)
    service = AccountWorkflowService(tmp_path)
    artifact = _portia_record_artifact()

    service.create(event_ref(), _account(source_artifacts=[artifact]))

    assert (
        service.require_current_use(account_reference(event_ref(), "acct_alpha"))
        .record.logical_id
        == "acct_alpha"
    )


def test_missing_exact_portia_work_record_artifact_rejects_before_write(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    artifact = _portia_record_artifact(record_id="ep_missing")

    with pytest.raises(PortiaNotFoundError):
        AccountWorkflowService(tmp_path).create(
            event_ref(),
            _account(source_artifacts=[artifact]),
        )

    assert not (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/account/acct_alpha.json"
    ).exists()


_DEFERRED_ARTIFACTS = (
    (
        "paper_capture",
        {
            "kind": "paper_capture",
            "route_id": "route_alpha",
            "page_record_id": "page_alpha",
        },
    ),
    (
        "module_work_record",
        {
            "kind": "module_work_record",
            "module_work_record_ref": {
                "work_ref": {
                    "module_id": "quillan",
                    "class_id": "class_a",
                    "work_id": "work_alpha",
                },
                "record_ref": {
                    "module_id": "quillan",
                    "record_kind": "result",
                    "record_id": "result_alpha",
                    "contract_version": "1",
                },
            },
        },
    ),
    (
        "external_record",
        {
            "kind": "external_record",
            "system_label": "Synthetic External System",
            "external_reference": "synthetic-record-alpha",
        },
    ),
)


@pytest.mark.parametrize(("kind", "artifact"), _DEFERRED_ARTIFACTS)
def test_deferred_artifact_branch_is_preserved_proposed_but_rejected_active(
    tmp_path: Path,
    kind: str,
    artifact: dict[str, object],
) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    proposed_id = f"acct_proposed_{kind}"
    active_id = f"acct_active_{kind}"

    service.create(
        event_ref(),
        _account(
            account_id=proposed_id,
            status="proposed",
            source_artifacts=[artifact],
        ),
    )
    exact = service.load_exact(account_reference(event_ref(), proposed_id))
    assert exact.record.field("source_artifacts") is not None

    with pytest.raises(WorkflowPrerequisiteError, match="outside Issue #41"):
        service.create(
            event_ref(),
            _account(account_id=active_id, source_artifacts=[artifact]),
        )


def test_deferred_artifact_branch_blocks_activation_before_write(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    artifact = {
        "kind": "external_record",
        "system_label": "Synthetic External System",
        "external_reference": "synthetic-record-alpha",
    }
    service = AccountWorkflowService(tmp_path)
    stored = service.create(
        event_ref(),
        _account(status="proposed", source_artifacts=[artifact]),
    )
    candidate_data = stored.record.to_dict()
    candidate_data["status"] = "active"
    candidate_data["updated_at"] = LATER
    candidate = parse_portia_record("account", "2", candidate_data)

    with pytest.raises(WorkflowPrerequisiteError, match="outside Issue #41"):
        service.transition_lifecycle(
            account_reference(event_ref(), "acct_alpha"),
            candidate,
            expected=stored.fingerprint,
            transition_id="lct_activate_external_artifact",
            reason_code="review_completed",
        )

    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "proposed"


def test_missing_workspace_artifact_does_not_block_invalidation(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    service = AccountWorkflowService(tmp_path)
    stored = service.create(event_ref(), _account(source_artifacts=[artifact]))
    (tmp_path / "source-artifacts/synthetic-evidence.txt").unlink()
    candidate_data = stored.record.to_dict()
    candidate_data["status"] = "invalidated"
    candidate_data["updated_at"] = LATER
    candidate = parse_portia_record("account", "2", candidate_data)

    service.transition_lifecycle(
        account_reference(event_ref(), "acct_alpha"),
        candidate,
        expected=stored.fingerprint,
        transition_id="lct_invalidate_artifact_account",
        reason_code="invalid_provenance",
    )

    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "invalidated"


def test_account_artifact_only_correction_uses_provenance_reason(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    first = _workspace_artifact(
        tmp_path,
        relative_path="source-artifacts/account-first.txt",
        content=b"Synthetic first account artifact.\n",
    )
    second = _workspace_artifact(
        tmp_path,
        relative_path="source-artifacts/account-second.txt",
        content=b"Synthetic corrected account artifact.\n",
    )
    service = AccountWorkflowService(tmp_path)
    predecessor = service.create(event_ref(), _account(source_artifacts=[first]))
    successor = _account(
        account_id="acct_corrected",
        source_artifacts=[second],
        supersedes=_supersedes("account", "acct_alpha", "provenance_corrected"),
        timestamp=LATER,
    )

    service.correct(
        account_reference(event_ref(), "acct_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_account_artifact",
    )

    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "superseded"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_corrected")
    ).record.status == "active"


def test_observation_artifact_only_correction_uses_provenance_reason(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    first = _workspace_artifact(
        tmp_path,
        relative_path="source-artifacts/observation-first.txt",
        content=b"Synthetic first observation artifact.\n",
    )
    second = _workspace_artifact(
        tmp_path,
        relative_path="source-artifacts/observation-second.txt",
        content=b"Synthetic corrected observation artifact.\n",
    )
    service = ObservationWorkflowService(tmp_path)
    predecessor = service.create(
        event_ref(),
        _observation(source_artifacts=[first]),
    )
    successor = _observation(
        observation_id="obs_corrected",
        source_artifacts=[second],
        supersedes=_supersedes(
            "observation", "obs_alpha", "provenance_corrected"
        ),
        timestamp=LATER,
    )

    service.correct(
        observation_reference(event_ref(), "obs_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_correct_observation_artifact",
    )

    assert service.load_exact(
        observation_reference(event_ref(), "obs_alpha")
    ).record.status == "superseded"
    assert service.require_current_use(
        observation_reference(event_ref(), "obs_corrected")
    ).record.status == "active"
