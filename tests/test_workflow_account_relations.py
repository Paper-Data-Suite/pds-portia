from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage import PortiaRepository
from portia.storage.errors import PortiaNotFoundError
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    WorkflowPrerequisiteError,
    account_reference,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

LATER = "2026-08-26T12:05:00-04:00"
LATER_STILL = "2026-08-26T12:10:00-04:00"


def _relation(kind: str, account_id: str, version: str = "2") -> dict[str, object]:
    return {
        "relation": kind,
        "account_ref": {
            "record_kind": "account",
            "record_id": account_id,
            "contract_version": version,
        },
    }


def _account(
    *,
    account_id: str,
    version: str = "2",
    source_label: str = "Synthetic Source",
    information_origin: str = "firsthand",
    related_accounts: list[dict[str, object]] | None = None,
    status: str = "active",
    timestamp: str = TIMESTAMP,
) -> PortiaRecord:
    value: dict[str, object] = {
        "schema_version": version,
        "record_type": "account",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "account_id": account_id,
        "status": status,
        "target": {"kind": "event"},
        "source": {
            "kind": "local_operator",
            "display_label": source_label,
        },
        "information_origin": information_origin,
        "source_certainty": "stated_certain",
        "content": [
            {
                "representation": "recorded_summary",
                "text": f"Synthetic contribution for {account_id}.",
            }
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": AGENT,
        "updated_at": timestamp,
        "updated_by": AGENT,
    }
    if version == "2":
        value["work_kind"] = "event"
    if related_accounts is not None:
        value["related_accounts"] = related_accounts
    return parse_portia_record("account", version, value)


def _seed_event(root: Path, event_id: str = "evt_alpha") -> None:
    EventWorkflowService(root).create(
        event_record(event_id=event_id, status="draft")
    )


def _path(root: Path, account_id: str, event_id: str = "evt_alpha") -> Path:
    return (
        root
        / "classes"
        / "class_a"
        / "modules"
        / "portia"
        / "work"
        / event_id
        / "records"
        / "account"
        / f"{account_id}.json"
    )


def test_reports_from_supports_transitive_exact_v1_v2_lineage(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    repository = PortiaRepository(tmp_path)
    repository.create_work_record(
        event_ref(),
        _account(account_id="acct_origin", version="1"),
    )
    service = AccountWorkflowService(tmp_path, repository=repository)
    service.create(
        event_ref(),
        _account(
            account_id="acct_middle",
            source_label="Synthetic Reporter One",
            information_origin="secondhand",
            related_accounts=[_relation("reports_from", "acct_origin", "1")],
            timestamp=LATER,
        ),
    )
    service.create(
        event_ref(),
        _account(
            account_id="acct_final",
            source_label="Synthetic Reporter Two",
            information_origin="mixed",
            related_accounts=[_relation("reports_from", "acct_middle")],
            timestamp=LATER_STILL,
        ),
    )

    current = service.require_current_use(
        account_reference(event_ref(), "acct_final")
    )

    assert current.record.status == "active"
    assert [item.record.contract_version for item in service.list(event_ref())] == [
        "2",
        "2",
        "1",
    ]


def test_firsthand_reports_from_is_rejected_without_canonical_write(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account(account_id="acct_origin"))
    candidate = _account(
        account_id="acct_bad_origin",
        related_accounts=[_relation("reports_from", "acct_origin")],
        timestamp=LATER,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="secondhand or mixed"):
        service.create(event_ref(), candidate)

    assert not _path(tmp_path, "acct_bad_origin").exists()


def test_clarification_requires_same_represented_source(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(
        event_ref(),
        _account(account_id="acct_origin", source_label="Synthetic Source A"),
    )
    clarification = _account(
        account_id="acct_clarification",
        source_label="Synthetic Source A",
        related_accounts=[_relation("clarifies", "acct_origin")],
        timestamp=LATER,
    )

    created = service.create(event_ref(), clarification)
    assert service.require_current_use(
        account_reference(event_ref(), "acct_clarification")
    ).record.to_dict() == created.record.to_dict()

    other_source = _account(
        account_id="acct_wrong_source",
        source_label="Synthetic Source B",
        related_accounts=[_relation("clarifies", "acct_origin")],
        timestamp=LATER_STILL,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="same represented source"):
        service.create(event_ref(), other_source)
    assert not _path(tmp_path, "acct_wrong_source").exists()


def test_ordinary_create_cannot_bypass_source_evidenced_retraction(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account(account_id="acct_origin"))
    candidate = _account(
        account_id="acct_retraction_without_coordination",
        related_accounts=[_relation("retracts", "acct_origin")],
        timestamp=LATER,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="retraction workflow"):
        service.create(event_ref(), candidate)

    assert not _path(tmp_path, "acct_retraction_without_coordination").exists()
    assert service.load_exact(
        account_reference(event_ref(), "acct_origin")
    ).record.status == "active"


def test_relation_self_reference_and_duplicate_target_are_rejected(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account(account_id="acct_origin"))

    self_related = _account(
        account_id="acct_self",
        related_accounts=[_relation("clarifies", "acct_self")],
        timestamp=LATER,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="reference itself"):
        service.create(event_ref(), self_related)
    assert not _path(tmp_path, "acct_self").exists()

    duplicate = _account(
        account_id="acct_duplicate",
        information_origin="mixed",
        related_accounts=[
            _relation("reports_from", "acct_origin"),
            _relation("clarifies", "acct_origin"),
        ],
        timestamp=LATER_STILL,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="repeat one logical"):
        service.create(event_ref(), duplicate)
    assert not _path(tmp_path, "acct_duplicate").exists()


def test_relation_cannot_reach_into_another_event(tmp_path: Path) -> None:
    _seed_event(tmp_path)
    _seed_event(tmp_path, "evt_beta")
    repository = PortiaRepository(tmp_path)
    beta = _account(account_id="acct_beta_origin")
    beta_data = beta.to_dict()
    beta_data["work_id"] = "evt_beta"
    repository.create_work_record(
        event_ref(event_id="evt_beta"),
        parse_portia_record("account", "2", beta_data),
    )
    service = AccountWorkflowService(tmp_path, repository=repository)
    candidate = _account(
        account_id="acct_cross_work",
        source_label="Synthetic Reporter",
        information_origin="secondhand",
        related_accounts=[_relation("reports_from", "acct_beta_origin")],
        timestamp=LATER,
    )

    with pytest.raises(PortiaNotFoundError):
        service.create(event_ref(), candidate)

    assert not _path(tmp_path, "acct_cross_work").exists()


def test_clarification_lineage_survives_ordinary_lifecycle_transition(
    tmp_path: Path,
) -> None:
    _seed_event(tmp_path)
    service = AccountWorkflowService(tmp_path)
    service.create(event_ref(), _account(account_id="acct_origin"))
    clarification = service.create(
        event_ref(),
        _account(
            account_id="acct_clarification",
            related_accounts=[_relation("clarifies", "acct_origin")],
            timestamp=LATER,
        ),
    )
    candidate_data = clarification.record.to_dict()
    candidate_data["status"] = "invalidated"
    candidate_data["updated_at"] = LATER_STILL
    candidate = parse_portia_record("account", "2", candidate_data)

    service.transition_lifecycle(
        account_reference(event_ref(), "acct_clarification"),
        candidate,
        expected=clarification.fingerprint,
        transition_id="lct_invalidate_clarification",
        reason_code="recording_error",
    )

    assert service.load_exact(
        account_reference(event_ref(), "acct_clarification")
    ).record.status == "invalidated"
