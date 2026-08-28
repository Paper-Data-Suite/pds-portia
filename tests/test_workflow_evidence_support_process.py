from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.errors import PortiaWireError
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.storage.errors import PortiaNotFoundError
from portia.workflows import (
    AccountWorkflowService,
    ObservationWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    account_reference,
    observation_reference,
)

TIMESTAMP = "2026-08-28T08:00:00-04:00"
AGENT = {"type": "local_operator", "display_label": "Synthetic Teacher"}


def _support_ref(*, support_id: str = "sup_alpha") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id=support_id,
        work_kind="support_process",
        contract_version="1",
    )


def _support_root(*, status: str = "active") -> PortiaRecord:
    workflow_state = "active" if status == "active" else "planning"
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": workflow_state,
            "summary": "Synthetic bounded support workflow.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic teacher-local support context.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _support_participant(*, status: str = "active") -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "participant_id": "spp_alpha",
            "status": status,
            "person": {
                "kind": "local_operator",
                "display_label": "Synthetic Participant",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _participant_target() -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_alpha",
            "contract_version": "1",
        },
    }


def _account(
    *,
    account_id: str = "acct_support_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    related_accounts: list[dict[str, object]] | None = None,
    information_origin: str = "firsthand",
) -> PortiaRecord:
    value: dict[str, object] = {
        "schema_version": "2",
        "record_type": "account",
        "module_id": "portia",
        "class_id": "class_a",
        "work_kind": "support_process",
        "work_id": "sup_alpha",
        "account_id": account_id,
        "status": status,
        "target": target or _participant_target(),
        "source": {
            "kind": "local_operator",
            "display_label": "Synthetic Source",
        },
        "information_origin": information_origin,
        "source_certainty": "stated_certain",
        "content": [
            {
                "representation": "recorded_summary",
                "text": "Synthetic support-context source contribution.",
            }
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if related_accounts is not None:
        value["related_accounts"] = related_accounts
    return parse_portia_record("account", "2", value)


def _observation(
    *,
    observation_id: str = "obs_support_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_alpha",
            "observation_id": observation_id,
            "status": status,
            "target": target or _participant_target(),
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Observer",
                },
            },
            "method": "live_direct",
            "content": {"narrative": "Synthetic directly observed support context."},
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _seed_support(
    root: Path,
    *,
    status: str = "active",
    participant_status: str = "active",
) -> PortiaRepository:
    repository = PortiaRepository(root)
    work = _support_ref()
    repository.create_work(work, _support_root(status=status))
    repository.create_work_record(
        work,
        _support_participant(status=participant_status),
    )
    return repository


def test_support_process_account_and_observation_create_resolve_list_and_current_use(
    tmp_path: Path,
) -> None:
    _seed_support(tmp_path)
    work = _support_ref()
    accounts = AccountWorkflowService(tmp_path)
    observations = ObservationWorkflowService(tmp_path)

    account = accounts.create(work, _account())
    observation = observations.create(work, _observation())

    assert accounts.require_current_use(
        account_reference(work, "acct_support_alpha")
    ).fingerprint == account.fingerprint
    assert observations.require_current_use(
        observation_reference(work, "obs_support_alpha")
    ).fingerprint == observation.fingerprint
    assert [item.record.logical_id for item in accounts.list(work)] == [
        "acct_support_alpha"
    ]
    assert [item.record.logical_id for item in observations.list(work)] == [
        "obs_support_alpha"
    ]


def test_proposed_support_process_allows_proposed_evidence_but_not_active_evidence(
    tmp_path: Path,
) -> None:
    _seed_support(tmp_path, status="proposed")
    work = _support_ref()
    service = AccountWorkflowService(tmp_path)

    service.create(
        work,
        _account(account_id="acct_support_proposed", status="proposed"),
    )
    before = tuple(item.record.logical_id for item in service.list(work))

    with pytest.raises(WorkflowPrerequisiteError, match="current evidence use"):
        service.create(
            work,
            _account(account_id="acct_support_active", status="active"),
        )

    assert tuple(item.record.logical_id for item in service.list(work)) == before


def test_active_support_evidence_requires_active_exact_participant(tmp_path: Path) -> None:
    _seed_support(tmp_path, participant_status="proposed")
    work = _support_ref()
    service = ObservationWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="target Participant must be active"):
        service.create(work, _observation())

    assert service.list(work) == ()


def test_support_process_rejects_event_target_family_before_write(tmp_path: Path) -> None:
    _seed_support(tmp_path)
    work = _support_ref()
    service = AccountWorkflowService(tmp_path)

    # The v2 wire contract is already owner-conditioned: an Event-family target
    # cannot be represented as a Support Process Account at all, so rejection
    # occurs before the workflow service receives a candidate record.
    with pytest.raises(PortiaWireError, match=r"\$.target"):
        _account(
            target={
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            }
        )

    assert service.list(work) == ()


def test_support_process_rejects_unresolved_exact_participant_before_write(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = _support_ref()
    repository.create_work(work, _support_root())
    service = AccountWorkflowService(tmp_path, repository=repository)

    # Preserve the lower-layer exact-resolution failure rather than converting
    # an unreadable/absent canonical child into a fabricated workflow identity.
    with pytest.raises(PortiaNotFoundError):
        service.create(work, _account())
    assert service.list(work) == ()


def test_support_process_v1_evidence_references_remain_prohibited() -> None:
    work = _support_ref()

    with pytest.raises(WorkflowOwnershipError, match="Event-local"):
        account_reference(work, "acct_legacy", version="1")
    with pytest.raises(WorkflowOwnershipError, match="Event-local"):
        observation_reference(work, "obs_legacy", version="1")


def test_support_process_account_cannot_claim_event_local_v1_lineage(
    tmp_path: Path,
) -> None:
    _seed_support(tmp_path)
    work = _support_ref()
    service = AccountWorkflowService(tmp_path)
    candidate = _account(
        information_origin="secondhand",
        related_accounts=[
            {
                "relation": "reports_from",
                "account_ref": {
                    "record_kind": "account",
                    "record_id": "acct_event_legacy",
                    "contract_version": "1",
                },
            }
        ],
    )

    with pytest.raises(WorkflowOwnershipError, match="Event-local"):
        service.create(work, candidate)

    assert service.list(work) == ()


def test_exact_support_evidence_remains_readable_when_owner_is_not_current(
    tmp_path: Path,
) -> None:
    repository = _seed_support(tmp_path, status="invalidated")
    work = _support_ref()
    record = _account(status="active")
    repository.create_work_record(work, record)
    service = AccountWorkflowService(tmp_path, repository=repository)
    reference = account_reference(work, "acct_support_alpha")

    assert service.load_exact(reference).record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="current evidence use"):
        service.require_current_use(reference)
