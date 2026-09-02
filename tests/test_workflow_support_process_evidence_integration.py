"""Issue #44 Support-Process-owned Account/Observation integration acceptance."""

from __future__ import annotations

from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    AccountWorkflowService,
    ObservationWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    account_reference,
    observation_reference,
    support_process_participant_reference,
)

CREATED = "2026-08-31T11:00:00-04:00"
PARTICIPANT_ACTIVE = "2026-08-31T11:05:00-04:00"
PROCESS_ACTIVE = "2026-08-31T11:10:00-04:00"
EVIDENCE_TIME = "2026-08-31T11:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice12b_test"}


def support_process_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_evidence",
        work_kind="support_process",
        contract_version="1",
    )


def support_process_record(*, status: str = "proposed", updated_at: str = CREATED) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_evidence",
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": "planning",
            "summary": "Synthetic bounded support planning for evidence integration.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning context.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_record(*, status: str = "proposed", updated_at: str = CREATED) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_evidence",
            "participant_id": "spp_evidence",
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def account_record() -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_evidence",
            "account_id": "acct_support_process",
            "status": "active",
            "target": {
                "kind": "support_process_participant",
                "record_ref": {
                    "record_kind": "support_process_participant",
                    "record_id": "spp_evidence",
                    "contract_version": "1",
                },
            },
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic participant perspective recorded for planning context.",
                }
            ],
            "provided_time": {"precision": "exact", "at": EVIDENCE_TIME},
            "creation_source": {"type": "digital_entry"},
            "created_at": EVIDENCE_TIME,
            "created_by": AGENT,
            "updated_at": EVIDENCE_TIME,
            "updated_by": AGENT,
        },
    )


def observation_record() -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_evidence",
            "observation_id": "obs_support_process",
            "status": "active",
            "target": {
                "kind": "support_process_participant",
                "record_ref": {
                    "record_kind": "support_process_participant",
                    "record_id": "spp_evidence",
                    "contract_version": "1",
                },
            },
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "method": "manual_count",
            "content": {
                "measurements": [
                    {
                        "measure_type": "count",
                        "value": 2,
                        "unit": "count",
                    }
                ]
            },
            "observation_time": {"precision": "exact", "at": EVIDENCE_TIME},
            "creation_source": {"type": "digital_entry"},
            "created_at": EVIDENCE_TIME,
            "created_by": AGENT,
            "updated_at": EVIDENCE_TIME,
            "updated_by": AGENT,
        },
    )


def activate_support_process(tmp_path: Path) -> None:
    work = support_process_ref()
    processes = SupportProcessWorkflowService(tmp_path)
    process = processes.create(support_process_record())

    participants = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participants.create(work, participant_record())
    participants.transition_lifecycle(
        support_process_participant_reference(work, "spp_evidence"),
        participant_record(status="active", updated_at=PARTICIPANT_ACTIVE),
        expected=participant.fingerprint,
        transition_id="lct_spp_evidence_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_evidence_active",
    )

    processes.transition_lifecycle(
        work,
        support_process_record(status="active", updated_at=PROCESS_ACTIVE),
        expected=process.fingerprint,
        transition_id="lct_sup_evidence_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_evidence_active",
    )
    assert processes.require_current_use(work).record.status == "active"
    assert (
        participants.require_current_use(
            support_process_participant_reference(work, "spp_evidence")
        ).participant.record.status
        == "active"
    )


def test_support_process_owned_account_uses_existing_evidence_service(
    tmp_path: Path,
) -> None:
    activate_support_process(tmp_path)
    work = support_process_ref()
    service = AccountWorkflowService(tmp_path)

    created = service.create(work, account_record())
    current = service.require_current_use(
        account_reference(work, "acct_support_process")
    )

    assert created.record.contract == "account"
    assert created.record.contract_version == "2"
    assert created.record.work_kind == "support_process"
    assert current.record.logical_id == "acct_support_process"
    assert current.record.field("target")["kind"] == "support_process_participant"


def test_support_process_owned_observation_uses_existing_evidence_service(
    tmp_path: Path,
) -> None:
    activate_support_process(tmp_path)
    work = support_process_ref()
    service = ObservationWorkflowService(tmp_path)

    created = service.create(work, observation_record())
    current = service.require_current_use(
        observation_reference(work, "obs_support_process")
    )

    assert created.record.contract == "observation"
    assert created.record.contract_version == "2"
    assert created.record.work_kind == "support_process"
    assert current.record.logical_id == "obs_support_process"
    assert current.record.field("target")["kind"] == "support_process_participant"


def test_support_process_evidence_does_not_create_need_goal_or_outcome(
    tmp_path: Path,
) -> None:
    activate_support_process(tmp_path)
    work = support_process_ref()

    AccountWorkflowService(tmp_path).create(work, account_record())
    ObservationWorkflowService(tmp_path).create(work, observation_record())

    repository = AccountWorkflowService(tmp_path).repository
    assert repository.list_work_records(
        work, "support_need", version="1"
    ) == ()
    assert repository.list_work_records(
        work, "support_goal", version="1"
    ) == ()
    assert repository.list_work_records(
        work, "outcome", version="1"
    ) == ()
