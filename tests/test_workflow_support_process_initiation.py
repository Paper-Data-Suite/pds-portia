"""Focused Issue #44 Slice 10a tests for Support Process initiation authority."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaNotFoundError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, account_wire, event_record

FIXTURES = Path("tests/schema_validation/fixtures")
ROOT_CLASS = "class_issue44_init"
ROOT_ID = "sup_issue44_init"
PARTICIPANT_ID = "spp_issue44_init"
PARTICIPANT_UPDATED = "2026-08-31T12:05:00-04:00"
ROOT_UPDATED = "2026-08-31T12:10:00-04:00"
CORRECTION_UPDATED = "2026-08-31T12:15:00-04:00"


def support_ref(work_id: str = ROOT_ID) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=ROOT_CLASS,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def support_root(
    initiation: dict[str, object],
    *,
    work_id: str = ROOT_ID,
    status: str = "proposed",
    workflow_state: str = "planning",
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": ROOT_CLASS,
            "work_id": work_id,
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": workflow_state,
            "summary": "Synthetic bounded initiation-authority process.",
            "initiation": initiation,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def support_participant(
    *,
    work_id: str = ROOT_ID,
    status: str = "proposed",
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": ROOT_CLASS,
            "work_id": work_id,
            "participant_id": PARTICIPANT_ID,
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic supported person",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def support_need() -> PortiaRecord:
    return parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": ROOT_CLASS,
            "work_id": ROOT_ID,
            "need_id": "spn_issue44_init",
            "status": "proposed",
            "target": {"kind": "support_process"},
            "need_kind": "access",
            "description": "Synthetic bounded initiation-linked Need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": ROOT_UPDATED,
            "created_by": AGENT,
            "updated_at": ROOT_UPDATED,
            "updated_by": AGENT,
        },
    )


def support_goal() -> PortiaRecord:
    return parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": ROOT_CLASS,
            "work_id": ROOT_ID,
            "goal_id": "spg_issue44_init",
            "status": "proposed",
            "target": {"kind": "support_process"},
            "description": "Synthetic bounded initiation-linked Goal.",
            "planned_criteria": "Synthetic criteria for later review.",
            "measurement_approach": "Synthetic later-review approach.",
            "creation_source": {"type": "digital_entry"},
            "created_at": ROOT_UPDATED,
            "created_by": AGENT,
            "updated_at": ROOT_UPDATED,
            "updated_by": AGENT,
        },
    )


def event_work(
    class_id: str,
    work_id: str,
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="event",
        contract_version="2",
    )


def seed_event(
    root: Path,
    *,
    class_id: str = "class_issue44_source",
    work_id: str = "evt_issue44_source",
    status: str = "active",
) -> ExactPortiaWorkRef:
    work = event_work(class_id, work_id)
    PortiaRepository(root).create_work(
        work,
        event_record(
            class_id=class_id,
            event_id=work_id,
            status=status,
        ),
    )
    return work


def fixture_value(path: str) -> dict[str, object]:
    value = json.loads((FIXTURES / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def seed_fixture_record(
    root: Path,
    *,
    contract: str,
    fixture_path: str,
) -> tuple[ExactPortiaWorkRef, PortiaRecord]:
    value = fixture_value(fixture_path)
    class_id = value["class_id"]
    work_id = value["work_id"]
    assert isinstance(class_id, str)
    assert isinstance(work_id, str)
    work = event_work(class_id, work_id)
    repository = PortiaRepository(root)
    repository.create_work(
        work,
        event_record(
            class_id=class_id,
            event_id=work_id,
            status="active",
        ),
    )
    record = parse_portia_record(contract, "1", value)
    repository.create_work_record(work, record)
    return work, record


def exact_record_ref(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> dict[str, object]:
    identity = record.logical_id
    assert identity is not None
    return {
        "work_ref": work.to_dict(),
        "record_ref": {
            "record_kind": record.contract,
            "record_id": identity,
            "contract_version": record.contract_version,
        },
    }


def test_event_context_resolves_exact_event2(tmp_path: Path) -> None:
    event = seed_event(tmp_path)
    root = support_root(
        {
            "kind": "event_context",
            "event_ref": event.to_dict(),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.field("initiation") == root.field("initiation")


def test_event_context_accepts_exact_historical_noncurrent_event(
    tmp_path: Path,
) -> None:
    event = seed_event(tmp_path, status="cancelled")
    root = support_root(
        {
            "kind": "event_context",
            "event_ref": event.to_dict(),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_event_context_missing_exact_source_is_zero_write(tmp_path: Path) -> None:
    missing = event_work("class_issue44_source", "evt_issue44_missing")
    root = support_root(
        {
            "kind": "event_context",
            "event_ref": missing.to_dict(),
        }
    )

    with pytest.raises(PortiaNotFoundError):
        SupportProcessWorkflowService(tmp_path).create(root)

    assert not (
        tmp_path
        / f"classes/{ROOT_CLASS}/modules/portia/work/{ROOT_ID}/work.json"
    ).exists()


def test_event_context_never_silently_follows_another_event(tmp_path: Path) -> None:
    seed_event(
        tmp_path,
        class_id="class_issue44_source",
        work_id="evt_issue44_successor",
    )
    requested = event_work("class_issue44_source", "evt_issue44_predecessor")
    root = support_root(
        {
            "kind": "event_context",
            "event_ref": requested.to_dict(),
        }
    )

    with pytest.raises(PortiaNotFoundError):
        SupportProcessWorkflowService(tmp_path).create(root)


def test_review_context_resolves_exact_review1(tmp_path: Path) -> None:
    work, review = seed_fixture_record(
        tmp_path,
        contract="review",
        fixture_path=(
            "issue-16/review/valid/"
            "completed-without-finding-or-evidence.json"
        ),
    )
    root = support_root(
        {
            "kind": "review_context",
            "record_ref": exact_record_ref(work, review),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_determination_context_resolves_exact_determination1(
    tmp_path: Path,
) -> None:
    work, determination = seed_fixture_record(
        tmp_path,
        contract="determination",
        fixture_path="issue-16/determination/valid/insufficient-information.json",
    )
    root = support_root(
        {
            "kind": "determination_context",
            "record_ref": exact_record_ref(work, determination),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_response_handoff_resolves_exact_response1(tmp_path: Path) -> None:
    work, response = seed_fixture_record(
        tmp_path,
        contract="response",
        fixture_path="issue-17/response/valid/referral-attempted.json",
    )
    root = support_root(
        {
            "kind": "response_handoff",
            "record_ref": exact_record_ref(work, response),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_represented_request_resolves_exact_account1(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = seed_event(tmp_path, class_id="class_a", work_id="evt_alpha")
    account = parse_portia_record("account", "1", account_wire())
    repository.create_work_record(work, account)
    root = support_root(
        {
            "kind": "represented_request",
            "record_ref": exact_record_ref(work, account),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_represented_request_resolves_exact_communication1(tmp_path: Path) -> None:
    work, communication = seed_fixture_record(
        tmp_path,
        contract="communication",
        fixture_path=(
            "issue-17/communication/valid/incoming-family-phone.json"
        ),
    )
    root = support_root(
        {
            "kind": "represented_request",
            "record_ref": exact_record_ref(work, communication),
        }
    )

    created = SupportProcessWorkflowService(tmp_path).create(root)

    assert created.record.status == "proposed"


def test_event_context_root_accepts_proposed_need_planning(
    tmp_path: Path,
) -> None:
    event = seed_event(tmp_path)
    SupportProcessWorkflowService(tmp_path).create(
        support_root(
            {
                "kind": "event_context",
                "event_ref": event.to_dict(),
            }
        )
    )

    created = SupportNeedWorkflowService(tmp_path).create(
        support_ref(),
        support_need(),
    )

    assert created.record.logical_id == "spn_issue44_init"


def test_event_context_root_accepts_proposed_goal_planning(
    tmp_path: Path,
) -> None:
    event = seed_event(tmp_path)
    SupportProcessWorkflowService(tmp_path).create(
        support_root(
            {
                "kind": "event_context",
                "event_ref": event.to_dict(),
            }
        )
    )

    created = SupportGoalWorkflowService(tmp_path).create(
        support_ref(),
        support_goal(),
    )

    assert created.record.logical_id == "spg_issue44_init"


def test_imported_history_remains_invalid_for_digital_bootstrap(
    tmp_path: Path,
) -> None:
    root = support_root(
        {
            "kind": "imported_history",
            "detail": "Synthetic imported history should require import provenance.",
        }
    )

    with pytest.raises(WorkflowPrerequisiteError, match="imported_history"):
        SupportProcessWorkflowService(tmp_path).create(root)


def test_initiation_correction_can_select_exact_event_context(tmp_path: Path) -> None:
    event = seed_event(tmp_path)
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(
        support_root(
            {
                "kind": "teacher_identified_need",
                "detail": "Original bounded local initiation.",
            }
        )
    )
    successor_wire = created.record.to_dict()
    successor_wire["work_id"] = "sup_issue44_init_corrected"
    successor_wire["initiation"] = {
        "kind": "event_context",
        "event_ref": event.to_dict(),
    }
    successor_wire["supersedes"] = [
        {
            "work_ref": support_ref().to_dict(),
            "reason": "initiation_corrected",
        }
    ]
    successor_wire["created_at"] = CORRECTION_UPDATED
    successor_wire["updated_at"] = CORRECTION_UPDATED
    successor = parse_portia_record("support_process", "1", successor_wire)

    service.correct(
        support_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_issue44_init_correction",
        operation_id="op_issue44_init_correction",
    )

    corrected = service.load_exact(
        support_ref("sup_issue44_init_corrected")
    )
    assert corrected.record.field("initiation") == successor.field("initiation")


def test_event_context_root_can_complete_participant_bootstrap_and_activate(
    tmp_path: Path,
) -> None:
    event = seed_event(tmp_path)
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(
        support_root(
            {
                "kind": "event_context",
                "event_ref": event.to_dict(),
            }
        )
    )
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participant_service.create(
        support_ref(),
        support_participant(),
    )
    active_participant = support_participant(
        status="active",
        updated_at=PARTICIPANT_UPDATED,
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(
            support_ref(),
            PARTICIPANT_ID,
        ),
        active_participant,
        expected=participant.fingerprint,
        transition_id="lct_issue44_init_participant",
        reason_code="planning_confirmed",
        operation_id="op_issue44_init_participant",
    )

    active_wire = root.record.to_dict()
    active_wire["status"] = "active"
    active_wire["updated_at"] = ROOT_UPDATED
    active_root = parse_portia_record("support_process", "1", active_wire)
    root_service.transition_lifecycle(
        support_ref(),
        active_root,
        expected=root.fingerprint,
        transition_id="lct_issue44_init_root",
        reason_code="planning_confirmed",
        operation_id="op_issue44_init_root",
    )

    current = root_service.require_current_use(support_ref())
    assert current.record.status == "active"
