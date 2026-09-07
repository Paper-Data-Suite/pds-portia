"""Issue #46 Slice 5a Repair identity seam and frozen harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    RepairWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    repair_reference,
)

TIMESTAMP = "2026-09-06T21:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice5a_test"}

_EXPECTED_VALID = (
    "event-planning-invited-only.json",
    "event-declined-without-agreement.json",
    "event-active-agreed-action.json",
    "event-completed-action.json",
    "event-unable-no-actions.json",
    "event-other-role-and-action.json",
    "support-planning-participant-refs.json",
    "support-active-cross-context.json",
    "support-action-withdrawn.json",
    "support-completed-nonfinancial-action.json",
    "support-proposed-import-unknown-participation.json",
    "event-focus-correction-successor.json",
)

_EXPECTED_APPLICATION_INVALID = (
    "active-event-roster-student-facilitator.json",
    "active-event-descriptive-facilitator.json",
    "active-event-unidentified-facilitator.json",
    "support-facilitator-without-operational-context.json",
    "active-event-unidentified-participant.json",
    "active-unknown-participation-state.json",
    "support-participant-other-process.json",
    "duplicate-participant-key.json",
    "action-agreed-by-unknown-key.json",
    "action-responsible-unknown-key.json",
    "duplicate-action-key.json",
    "context-other-class.json",
    "self-context-reference.json",
    "active-import-without-review.json",
    "updated-before-created.json",
    "action-completed-before-agreed.json",
    "self-supersession.json",
    "ordinary-correction-cross-work.json",
    "duplicate-consolidation-one-predecessor.json",
)

_EXPECTED_STRUCTURAL_INVALID = (
    "missing-work-kind.json",
    "event-owner-support-id.json",
    "event-owner-support-target.json",
    "event-owner-support-facilitator.json",
    "support-owner-event-facilitator.json",
    "empty-participants.json",
    "empty-context-refs.json",
    "event-participant-support-ref.json",
    "support-participant-event-person.json",
    "other-role-missing-detail.json",
    "cooperation-state-prohibited.json",
    "engagement-score-prohibited.json",
    "remorse-score-prohibited.json",
    "admission-requirement-prohibited.json",
    "apology-requirement-prohibited.json",
    "relationship-restored-field-prohibited.json",
    "other-action-missing-type-detail.json",
    "completed-action-missing-completed-at.json",
    "noncompleted-action-has-completed-at.json",
    "completed-repair-missing-completed-at.json",
    "planning-repair-has-completed-at.json",
    "financial-ledger-field-prohibited.json",
    "restorative-transcript-prohibited.json",
    "truth-finding-field-prohibited.json",
    "wrong-id-family.json",
)


def event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def support_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def repair_record() -> object:
    return parse_portia_record(
        "repair",
        "1",
        {
            "schema_version": "1",
            "record_type": "repair",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "repair_id": "rpr_alpha",
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "facilitator": {
                "kind": "represented_human",
                "person": {
                    "kind": "local_operator",
                    "display_label": "Synthetic teacher",
                },
            },
            "focus": (
                "Synthetic bounded repair focus without admission or truth finding."
            ),
            "context_refs": [
                {
                    "kind": "work",
                    "work_ref": event_ref().to_dict(),
                }
            ],
            "participants": [
                {
                    "participant_key": "student",
                    "person": {
                        "kind": "represented_human",
                        "person": {
                            "kind": "descriptive_person",
                            "description_type": "outside_student",
                            "display_label": "Synthetic student",
                        },
                    },
                    "roles": [{"kind": "person_addressing_impact"}],
                    "participation_state": "invited",
                }
            ],
            "workflow_state": "planning",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_repair_reference_accepts_both_frozen_owner_families() -> None:
    event = repair_reference(event_ref(), "rpr_event")
    support = repair_reference(support_ref(), "rpr_support")

    assert event.record_ref.record_kind == "repair"
    assert event.record_ref.contract_version == "1"
    assert event.work_ref.work_kind == "event"
    assert support.record_ref.record_kind == "repair"
    assert support.record_ref.contract_version == "1"
    assert support.work_ref.work_kind == "support_process"


def test_repair_reference_rejects_noncanonical_owner_versions() -> None:
    wrong_event = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="1",
    )

    with pytest.raises(WorkflowOwnershipError):
        repair_reference(wrong_event, "rpr_alpha")


def test_repair_harness_uses_current_repair_v1_wire_shape() -> None:
    record = repair_record()

    assert record.logical_id == "rpr_alpha"
    assert record.field("workflow_state") == "planning"
    assert record.field("participants")[0]["participation_state"] == "invited"
    assert record.field("actions") is None


def test_frozen_repair_fixture_ledger_is_exact() -> None:
    manifest_path = Path(
        "tests/schema_validation/fixtures/issue-19/repair/manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert tuple(manifest["valid"]) == _EXPECTED_VALID
    assert tuple(manifest["application_invalid"]) == _EXPECTED_APPLICATION_INVALID
    assert tuple(manifest["invalid"]) == _EXPECTED_STRUCTURAL_INVALID
    assert len(_EXPECTED_VALID) == 12
    assert len(_EXPECTED_APPLICATION_INVALID) == 19
    assert len(_EXPECTED_STRUCTURAL_INVALID) == 25


def event_record(
    *,
    event_id: str = "evt_alpha",
    class_id: str = "class_a",
    status: str = "active",
) -> PortiaRecord:
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": event_id,
            "school_year": "2026-2027",
            "status": status,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
            "occurrence": {"precision": "exact", "started_at": TIMESTAMP},
            "summary": "Synthetic bounded Event for Repair testing.",
        },
    )


def event_participant_record(
    *,
    event_id: str = "evt_alpha",
    class_id: str = "class_a",
    participant_id: str = "ep_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": event_id,
            "participant_id": participant_id,
            "status": "active",
            "subject": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic student",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_process_record(
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": work_id,
            "school_year": "2026-2027",
            "status": "active",
            "workflow_state": "active",
            "summary": "Synthetic bounded Support Process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic bounded need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_participant_record(
    participant_id: str,
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
    contexts: list[dict[str, object]],
    person: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": work_id,
            "participant_id": participant_id,
            "status": "active",
            "person": person
            or {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "contexts": contexts,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def event_target() -> dict[str, object]:
    return {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_alpha",
            "contract_version": "3",
        },
    }


def support_target() -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_student",
            "contract_version": "1",
        },
    }


def local_operator_facilitator() -> dict[str, object]:
    return {
        "kind": "represented_human",
        "person": {
            "kind": "local_operator",
            "display_label": "Synthetic teacher",
        },
    }


def support_facilitator(
    participant_id: str = "spp_coordinator",
) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "participant_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def event_repair_participant(
    *,
    key: str = "student",
    participation_state: str = "invited",
    person: dict[str, object] | None = None,
    role: str = "person_addressing_impact",
) -> dict[str, object]:
    return {
        "participant_key": key,
        "person": {
            "kind": "represented_human",
            "person": person
            or {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic student",
            },
        },
        "roles": [{"kind": role}],
        "participation_state": participation_state,
    }


def support_repair_participant(
    *,
    key: str = "student",
    participant_id: str = "spp_student",
    participation_state: str = "invited",
) -> dict[str, object]:
    return {
        "participant_key": key,
        "person": {
            "kind": "support_process_participant",
            "participant_ref": {
                "record_kind": "support_process_participant",
                "record_id": participant_id,
                "contract_version": "1",
            },
        },
        "roles": [{"kind": "person_addressing_impact"}],
        "participation_state": participation_state,
    }


def repair_work_record(
    *,
    work: ExactPortiaWorkRef | None = None,
    repair_id: str = "rpr_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    facilitator: dict[str, object] | None = None,
    context_refs: list[dict[str, object]] | None = None,
    participants: list[dict[str, object]] | None = None,
    actions: list[dict[str, object]] | None = None,
    source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = TIMESTAMP,
    workflow_state: str = "planning",
    completed_at: str | None = None,
) -> PortiaRecord:
    selected = work or event_ref()
    if target is None:
        target = event_target() if selected.work_kind == "event" else support_target()
    if facilitator is None:
        facilitator = (
            local_operator_facilitator()
            if selected.work_kind == "event"
            else support_facilitator()
        )
    if context_refs is None:
        context_refs = [{"kind": "work", "work_ref": selected.to_dict()}]
    if participants is None:
        participants = [
            event_repair_participant()
            if selected.work_kind == "event"
            else support_repair_participant()
        ]

    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "repair",
        "module_id": "portia",
        "class_id": selected.class_id,
        "work_kind": selected.work_kind,
        "work_id": selected.work_id,
        "repair_id": repair_id,
        "status": status,
        "target": target,
        "facilitator": facilitator,
        "focus": "Synthetic bounded repair focus without admission or truth finding.",
        "context_refs": context_refs,
        "participants": participants,
        "workflow_state": workflow_state,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if actions is not None:
        wire["actions"] = actions
    if completed_at is not None:
        wire["completed_at"] = completed_at
    return parse_portia_record("repair", "1", wire)


def repair_workflow_revision(
    prior: PortiaRecord,
    *,
    workflow_state: str,
    updated_at: str,
    participants: list[dict[str, object]] | None = None,
    actions: list[dict[str, object]] | None = None,
    drop_actions: bool = False,
    completed_at: str | None = None,
    status: str | None = None,
    focus: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["workflow_state"] = workflow_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if participants is not None:
        wire["participants"] = participants
    if drop_actions:
        wire.pop("actions", None)
    elif actions is not None:
        wire["actions"] = actions
    if completed_at is None:
        wire.pop("completed_at", None)
    else:
        wire["completed_at"] = completed_at
    if status is not None:
        wire["status"] = status
    if focus is not None:
        wire["focus"] = focus
    return parse_portia_record("repair", "1", wire)


def repair_lifecycle_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("repair", "1", wire)


def repair_correction_successor(
    prior: PortiaRecord,
    *,
    predecessor: ExactPortiaWorkRecordRef,
    repair_id: str = "rpr_beta",
    reason: str = "focus_corrected",
    focus: str | None = None,
    updated_at: str = "2026-09-06T21:20:00-04:00",
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["repair_id"] = repair_id
    wire["status"] = "active"
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if focus is not None:
        wire["focus"] = focus
    wire["supersedes"] = [
        {
            "work_record_ref": predecessor.to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("repair", "1", wire)


def repair_consolidation_successor(
    priors: tuple[PortiaRecord, ...],
    *,
    repair_id: str = "rpr_canonical",
    status: str = "active",
    updated_at: str = "2026-09-06T21:30:00-04:00",
) -> PortiaRecord:
    assert priors
    wire = priors[0].to_dict()
    work = ExactPortiaWorkRef(
        class_id=str(wire["class_id"]),
        work_id=str(wire["work_id"]),
        work_kind=str(wire["work_kind"]),
        contract_version="2" if wire["work_kind"] == "event" else "1",
    )
    wire["repair_id"] = repair_id
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    wire["supersedes"] = [
        {
            "work_record_ref": repair_reference(
                work,
                str(prior.logical_id),
            ).to_dict(),
            "reason": "duplicate_consolidated",
        }
        for prior in priors
    ]
    return parse_portia_record("repair", "1", wire)


def repair_work_root_successor(
    prior: PortiaRecord,
    destination_work: ExactPortiaWorkRef,
    *,
    target: dict[str, object],
    facilitator: dict[str, object],
    participants: list[dict[str, object]],
    updated_at: str = "2026-09-06T21:30:00-04:00",
    repair_id: str | None = None,
    focus: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    if not isinstance(prior_id, str):
        raise AssertionError("Repair test predecessor must have a logical ID")
    wire["class_id"] = destination_work.class_id
    wire["work_kind"] = destination_work.work_kind
    wire["work_id"] = destination_work.work_id
    wire["repair_id"] = repair_id or prior_id
    wire["status"] = "active"
    wire["target"] = target
    wire["facilitator"] = facilitator
    wire["participants"] = participants
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if focus is not None:
        wire["focus"] = focus
    wire["supersedes"] = [
        {
            "work_record_ref": {
                "work_ref": {
                    "module_id": "portia",
                    "class_id": prior.class_id,
                    "work_id": prior.work_id,
                    "work_kind": prior.work_kind,
                    "contract_version": (
                        "2" if prior.work_kind == "event" else "1"
                    ),
                },
                "record_ref": {
                    "record_kind": "repair",
                    "record_id": prior_id,
                    "contract_version": "1",
                },
            },
            "reason": "work_root_corrected",
        }
    ]
    return parse_portia_record("repair", "1", wire)


def seed_event(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), event_participant_record())
    return repository


def seed_support(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(support_ref(), support_process_record())
    repository.create_work_record(
        support_ref(),
        support_participant_record(
            "spp_student",
            contexts=[{"kind": "supported_person"}],
            person={
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic supported student",
            },
        ),
    )
    repository.create_work_record(
        support_ref(),
        support_participant_record(
            "spp_coordinator",
            contexts=[{"kind": "coordinator"}],
        ),
    )
    return repository


def test_create_load_list_and_current_event_repair(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())

    reference = repair_reference(event_ref(), "rpr_alpha")
    assert created.record.logical_id == "rpr_alpha"
    assert service.load_exact(reference).record.logical_id == "rpr_alpha"
    assert service.resolve_exact(reference).record.logical_id == "rpr_alpha"
    assert [item.record.logical_id for item in service.list_repairs(event_ref())] == [
        "rpr_alpha"
    ]
    assert service.require_current_use(reference).record.logical_id == "rpr_alpha"
    assert service.resolve_current(reference).record.logical_id == "rpr_alpha"


def test_create_load_list_and_current_support_repair(tmp_path: Path) -> None:
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        repair_work_record(work=support_ref()),
    )

    reference = repair_reference(support_ref(), "rpr_alpha")
    assert created.record.logical_id == "rpr_alpha"
    assert [item.record.logical_id for item in service.list_repairs(support_ref())] == [
        "rpr_alpha"
    ]
    assert service.require_current_use(reference).record.logical_id == "rpr_alpha"


def test_proposed_repair_preserves_descriptive_facilitator_but_is_not_current(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    facilitator = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }
    service = RepairWorkflowService(tmp_path)
    service.create(
        event_ref(),
        repair_work_record(status="proposed", facilitator=facilitator),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Repair use requires active canonical status",
    ):
        service.require_current_use(repair_reference(event_ref(), "rpr_alpha"))


def test_active_event_repair_rejects_roster_student_facilitator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    facilitator = {
        "kind": "represented_human",
        "person": {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_a",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Synthetic student"},
        },
    }

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Repair facilitator cannot use roster-student identity "
            "as operational authority"
        ),
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(facilitator=facilitator),
        )


def test_active_event_repair_rejects_descriptive_facilitator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    facilitator = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Repair facilitator requires an identified operational human",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(facilitator=facilitator),
        )


def test_active_event_repair_rejects_unidentified_participant(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    participant = event_repair_participant(
        key="unknown",
        person={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
        role="community_participant",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active Repair cannot use an unidentified participant",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(participants=[participant]),
        )


def test_active_repair_rejects_unknown_participation_state(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    participant = event_repair_participant(participation_state="unknown")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active Repair cannot use unknown participation state",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(participants=[participant]),
        )


def test_repair_rejects_duplicate_participant_key(tmp_path: Path) -> None:
    seed_event(tmp_path)
    participants = [
        event_repair_participant(key="same"),
        event_repair_participant(
            key="same",
            person={
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Different synthetic participant",
            },
            role="affected_person",
        ),
    ]

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair participant_key values must be unique",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(participants=participants),
        )


def test_support_repair_requires_operational_facilitator_context(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_participant_record(
            "spp_family",
            contexts=[{"kind": "family_or_support_person"}],
        ),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            r"Repair facilitator requires Support Process Participant context "
            r"in \{coordinator, provider_or_collaborator\}"
        ),
    ):
        RepairWorkflowService(tmp_path).create(
            support_ref(),
            repair_work_record(
                work=support_ref(),
                facilitator=support_facilitator("spp_family"),
            ),
        )


def test_support_repair_participant_must_resolve_in_owning_process(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    participant = support_repair_participant(participant_id="spp_elsewhere")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Repair participant Support Process Participant does not resolve "
            "in the owning Support Process"
        ),
    ):
        RepairWorkflowService(tmp_path).create(
            support_ref(),
            repair_work_record(work=support_ref(), participants=[participant]),
        )


def test_repair_context_must_remain_in_owning_class(tmp_path: Path) -> None:
    seed_event(tmp_path)
    other_class = ExactPortiaWorkRef(
        class_id="class_b",
        work_id="evt_beta",
        work_kind="event",
        contract_version="2",
    )

    with pytest.raises(
        WorkflowOwnershipError,
        match="Repair context must remain in the owning class",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(
                context_refs=[{"kind": "work", "work_ref": other_class.to_dict()}]
            ),
        )


def test_repair_context_cannot_reference_itself(tmp_path: Path) -> None:
    seed_event(tmp_path)
    self_ref = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair context cannot reference the Repair itself",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(
                context_refs=[
                    {"kind": "record", "record_ref": self_ref.to_dict()}
                ]
            ),
        )


def test_repair_action_agreed_by_must_name_participant_key(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    actions = [
        {
            "action_key": "conversation",
            "action_type": "follow_up_conversation",
            "description": "Synthetic bounded action.",
            "agreed_by": ["missing"],
            "completion_state": "in_progress",
        }
    ]

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair action agreed_by must reference an existing participant_key",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(actions=actions),
        )


def test_repair_action_responsible_keys_must_name_participants(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    actions = [
        {
            "action_key": "conversation",
            "action_type": "follow_up_conversation",
            "description": "Synthetic bounded action.",
            "agreed_by": ["student"],
            "responsible_participant_keys": ["missing"],
            "completion_state": "in_progress",
        }
    ]

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Repair action responsible_participant_keys must reference existing "
            "participant_key values"
        ),
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(actions=actions),
        )


def test_repair_rejects_duplicate_action_key(tmp_path: Path) -> None:
    seed_event(tmp_path)
    actions = [
        {
            "action_key": "same",
            "action_type": "follow_up_conversation",
            "description": "Synthetic first action.",
            "agreed_by": ["student"],
            "completion_state": "in_progress",
        },
        {
            "action_key": "same",
            "action_type": "restorative_action",
            "description": "Synthetic second action.",
            "agreed_by": ["student"],
            "completion_state": "planned",
        },
    ]

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair action_key values must be unique",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(actions=actions),
        )


def test_repair_rejects_action_completed_before_agreed(tmp_path: Path) -> None:
    seed_event(tmp_path)
    actions = [
        {
            "action_key": "conversation",
            "action_type": "follow_up_conversation",
            "description": "Synthetic completed action.",
            "agreed_by": ["student"],
            "completion_state": "completed",
            "agreed_at": "2026-09-06T21:30:00-04:00",
            "completed_at": "2026-09-06T21:29:00-04:00",
        }
    ]

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair action completed_at cannot precede Repair action agreed_at",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(actions=actions),
        )


def test_repair_rejects_updated_before_created(tmp_path: Path) -> None:
    seed_event(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Repair updated_at cannot precede Repair created_at",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(
                created_at="2026-09-06T22:00:00-04:00",
                updated_at="2026-09-06T21:59:00-04:00",
            ),
        )


def test_repair_workflow_progresses_planning_active_completed_without_inference(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(workflow_state="planning"),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")
    agreed_participant = event_repair_participant(
        participation_state="agreed_to_participate"
    )
    active_action = {
        "action_key": "conversation",
        "action_type": "follow_up_conversation",
        "description": "Synthetic agreed follow-up conversation.",
        "agreed_by": ["student"],
        "responsible_participant_keys": ["student"],
        "agreed_at": "2026-09-06T21:05:00-04:00",
        "completion_state": "in_progress",
    }
    active = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            created.record,
            workflow_state="active",
            updated_at="2026-09-06T21:10:00-04:00",
            participants=[agreed_participant],
            actions=[active_action],
        ),
        expected=created.fingerprint,
    )

    completed_action = dict(active_action)
    completed_action["completion_state"] = "completed"
    completed_action["completed_at"] = "2026-09-06T21:20:00-04:00"
    completed = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            active.record,
            workflow_state="completed",
            updated_at="2026-09-06T21:25:00-04:00",
            completed_at="2026-09-06T21:25:00-04:00",
            participants=[
                event_repair_participant(participation_state="participated")
            ],
            actions=[completed_action],
        ),
        expected=active.fingerprint,
    )

    assert completed.record.field("workflow_state") == "completed"
    assert completed.record.field("participants")[0]["participation_state"] == (
        "participated"
    )
    assert completed.record.field("actions")[0]["completion_state"] == "completed"
    assert completed.record.field("completed_at") == "2026-09-06T21:25:00-04:00"
    assert completed.record.field("remorse") is None
    assert completed.record.field("forgiveness") is None
    assert completed.record.field("relationship_restored") is None


def test_repair_workflow_can_cancel_without_agreed_actions(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")

    accepted = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            created.record,
            workflow_state="cancelled",
            updated_at="2026-09-06T21:10:00-04:00",
            participants=[
                event_repair_participant(participation_state="declined")
            ],
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == "cancelled"
    assert accepted.record.field("actions") is None
    assert accepted.record.field("completed_at") is None


def test_repair_workflow_can_end_unable_to_complete_without_actions(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")

    accepted = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            created.record,
            workflow_state="unable_to_complete",
            updated_at="2026-09-06T21:10:00-04:00",
            participants=[
                event_repair_participant(participation_state="unavailable")
            ],
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == "unable_to_complete"
    assert accepted.record.field("actions") is None


def test_terminal_repair_workflow_state_cannot_progress(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")
    terminal = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            created.record,
            workflow_state="cancelled",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=created.fingerprint,
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="illegal Repair workflow_state transition: cancelled -> active",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                terminal.record,
                workflow_state="active",
                updated_at="2026-09-06T21:20:00-04:00",
            ),
            expected=terminal.fingerprint,
        )


def test_repair_workflow_progression_cannot_change_canonical_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot change canonical lifecycle",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="cancelled",
                updated_at="2026-09-06T21:10:00-04:00",
                status="invalidated",
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_cannot_rewrite_focus(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite field focus",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                focus="Different synthetic focus.",
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_cannot_remove_participant(tmp_path: Path) -> None:
    seed_event(tmp_path)
    participants = [
        event_repair_participant(key="student"),
        event_repair_participant(
            key="supporter",
            person={
                "kind": "descriptive_person",
                "description_type": "family_member",
                "display_label": "Synthetic supporter",
            },
            role="supporter",
        ),
    ]
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(participants=participants),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot remove an existing participant_key",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                participants=[event_repair_participant(key="student")],
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_rejects_participant_state_reversal(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(
            participants=[
                event_repair_participant(
                    participation_state="agreed_to_participate"
                )
            ]
        ),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "illegal Repair participant-state transition: "
            "agreed_to_participate -> invited"
        ),
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                participants=[event_repair_participant()],
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_cannot_remove_agreed_action(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    action = {
        "action_key": "conversation",
        "action_type": "follow_up_conversation",
        "description": "Synthetic bounded action.",
        "agreed_by": ["student"],
        "completion_state": "planned",
    }
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(actions=[action]),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot remove an existing action_key",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                drop_actions=True,
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_cannot_rewrite_agreed_action_fact(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    action = {
        "action_key": "conversation",
        "action_type": "follow_up_conversation",
        "description": "Synthetic bounded action.",
        "agreed_by": ["student"],
        "completion_state": "planned",
    }
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(actions=[action]),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")
    rewritten = dict(action)
    rewritten["description"] = "Rewritten action fact."
    rewritten["completion_state"] = "in_progress"

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite agreed-action field description",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                actions=[rewritten],
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_rejects_action_state_reversal(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    action = {
        "action_key": "conversation",
        "action_type": "follow_up_conversation",
        "description": "Synthetic bounded action.",
        "agreed_by": ["student"],
        "completion_state": "in_progress",
    }
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(actions=[action]),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")
    reversed_action = dict(action)
    reversed_action["completion_state"] = "planned"

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="illegal Repair action-state transition: in_progress -> planned",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T21:10:00-04:00",
                actions=[reversed_action],
            ),
            expected=created.fingerprint,
        )


def test_repair_workflow_progression_rejects_stale_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")
    active = service.transition_workflow_state(
        reference,
        repair_workflow_revision(
            created.record,
            workflow_state="active",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=created.fingerprint,
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected Repair state does not match canonical bytes",
    ):
        service.transition_workflow_state(
            reference,
            repair_workflow_revision(
                active.record,
                workflow_state="cancelled",
                updated_at="2026-09-06T21:20:00-04:00",
            ),
            expected=created.fingerprint,
        )


def test_proposed_repair_can_activate_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(status="proposed"),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")
    candidate = repair_lifecycle_revision(
        created.record,
        status="active",
        updated_at="2026-09-06T21:10:00-04:00",
    )

    service.transition_lifecycle(
        reference,
        candidate,
        expected=created.fingerprint,
        transition_id="lct_rpr_activate",
        reason_code="reviewed",
        operation_id="op_rpr_activate",
    )

    accepted = service.require_current_use(reference)
    assert accepted.record.status == "active"


def test_active_repair_can_be_invalidated_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    reference = repair_reference(event_ref(), "rpr_alpha")

    service.transition_lifecycle(
        reference,
        repair_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_rpr_invalidate",
        reason_code="recording_error",
        operation_id="op_rpr_invalidate",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Repair use requires active canonical status",
    ):
        service.require_current_use(reference)


def test_repair_lifecycle_transition_cannot_rewrite_workflow_fact(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(status="proposed"),
    )
    reference = repair_reference(event_ref(), "rpr_alpha")
    wire = created.record.to_dict()
    wire["status"] = "active"
    wire["workflow_state"] = "active"
    wire["updated_at"] = "2026-09-06T21:10:00-04:00"
    wire["updated_by"] = AGENT
    candidate = parse_portia_record("repair", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary downstream lifecycle replacement cannot rewrite field workflow_state",
    ):
        service.transition_lifecycle(
            reference,
            candidate,
            expected=created.fingerprint,
            transition_id="lct_rpr_smuggle",
            reason_code="reviewed",
            operation_id="op_rpr_smuggle",
        )


def test_repair_focus_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    predecessor = repair_reference(event_ref(), "rpr_alpha")
    successor = repair_correction_successor(
        created.record,
        predecessor=predecessor,
        focus="Corrected bounded synthetic Repair focus.",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_rpr_focus_correction",
        operation_id="op_rpr_focus_correction",
    )

    old = service.load_exact(predecessor)
    current = service.require_current_use(
        repair_reference(event_ref(), "rpr_beta")
    )
    assert old.record.status == "superseded"
    assert current.record.status == "active"
    assert current.record.field("focus") == (
        "Corrected bounded synthetic Repair focus."
    )


def test_repair_correction_reason_must_match_corrected_fact(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    predecessor = repair_reference(event_ref(), "rpr_alpha")
    successor = repair_correction_successor(
        created.record,
        predecessor=predecessor,
        reason="facilitator_corrected",
        focus="Corrected bounded synthetic Repair focus.",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected fact",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_reason_mismatch",
            operation_id="op_rpr_reason_mismatch",
        )


def test_repair_correction_rejects_self_supersession(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    predecessor = repair_reference(event_ref(), "rpr_alpha")
    successor = repair_correction_successor(
        created.record,
        predecessor=predecessor,
        repair_id="rpr_alpha",
        focus="Corrected bounded synthetic Repair focus.",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="repair cannot supersede itself",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_self",
            operation_id="op_rpr_self",
        )


def test_repair_ordinary_correction_cannot_cross_work_root(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    repository = PortiaRepository(tmp_path)
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_other",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(other_work, event_record(event_id="evt_other"))
    repository.create_work_record(
        other_work,
        event_participant_record(event_id="evt_other"),
    )
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    predecessor = repair_reference(event_ref(), "rpr_alpha")
    wire = created.record.to_dict()
    wire["work_id"] = "evt_other"
    wire["repair_id"] = "rpr_beta"
    wire["focus"] = "Corrected bounded synthetic Repair focus."
    wire["updated_at"] = "2026-09-06T21:20:00-04:00"
    wire["supersedes"] = [
        {
            "work_record_ref": predecessor.to_dict(),
            "reason": "focus_corrected",
        }
    ]
    successor = parse_portia_record("repair", "1", wire)

    with pytest.raises(
        WorkflowOwnershipError,
        match="repair does not belong to the explicitly selected event work",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_cross_work",
            operation_id="op_rpr_cross_work",
        )


def test_repair_correction_does_not_silently_follow_old_reference(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    predecessor = repair_reference(event_ref(), "rpr_alpha")
    successor_reference = repair_reference(event_ref(), "rpr_beta")
    successor = repair_correction_successor(
        created.record,
        predecessor=predecessor,
        focus="Corrected bounded synthetic Repair focus.",
    )
    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_rpr_exact_history",
        operation_id="op_rpr_exact_history",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Repair use requires active canonical status",
    ):
        service.require_current_use(predecessor)
    assert service.require_current_use(successor_reference).record.status == "active"


def test_repair_duplicate_consolidation_supersedes_all_exact_predecessors(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_a"),
    )
    second = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_b"),
    )
    successor = repair_consolidation_successor(
        (first.record, second.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "rpr_dup_a": first.fingerprint,
            "rpr_dup_b": second.fingerprint,
        },
        transition_ids={
            "rpr_dup_a": "lct_rpr_dup_a_consolidate",
            "rpr_dup_b": "lct_rpr_dup_b_consolidate",
        },
        operation_id="op_rpr_duplicate_consolidation",
    )

    first_ref = repair_reference(event_ref(), "rpr_dup_a")
    second_ref = repair_reference(event_ref(), "rpr_dup_b")
    assert service.resolve_exact(first_ref).record.status == "superseded"
    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        repair_reference(event_ref(), "rpr_canonical")
    ).record.status == "active"

    for transition_id in (
        "lct_rpr_dup_a_consolidate",
        "lct_rpr_dup_b_consolidate",
    ):
        transition = service.repository.load_work_record(
            event_ref(),
            "lifecycle_transition",
            "1",
            transition_id,
        )
        assert transition.record.to_dict()["reason"] == {
            "category": "consolidation",
            "code": "duplicate_consolidated",
        }


def test_repair_duplicate_consolidation_accepts_invalidated_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_a"),
    )
    second = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_b"),
    )
    second_ref = repair_reference(event_ref(), "rpr_dup_b")
    service.transition_lifecycle(
        second_ref,
        repair_lifecycle_revision(
            second.record,
            status="invalidated",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=second.fingerprint,
        transition_id="lct_rpr_dup_b_invalidate",
        reason_code="recording_error",
        operation_id="op_rpr_dup_b_invalidate",
    )
    invalidated = service.resolve_exact(second_ref)
    successor = repair_consolidation_successor(
        (first.record, invalidated.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "rpr_dup_a": first.fingerprint,
            "rpr_dup_b": invalidated.fingerprint,
        },
        transition_ids={
            "rpr_dup_a": "lct_rpr_dup_a_consolidate",
            "rpr_dup_b": "lct_rpr_dup_b_consolidate",
        },
        operation_id="op_rpr_duplicate_with_invalidated",
    )

    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        repair_reference(event_ref(), "rpr_canonical")
    ).record.status == "active"


def test_repair_duplicate_consolidation_rejects_one_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    successor = repair_consolidation_successor((created.record,))

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two repair predecessors",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"rpr_alpha": created.fingerprint},
            transition_ids={"rpr_alpha": "lct_rpr_single"},
            operation_id="op_rpr_single_duplicate",
        )


def test_repair_duplicate_consolidation_requires_complete_expected_map(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_a"),
    )
    second = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_b"),
    )
    successor = repair_consolidation_successor(
        (first.record, second.record),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="one expected fingerprint for every predecessor",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"rpr_dup_a": first.fingerprint},
            transition_ids={
                "rpr_dup_a": "lct_rpr_dup_a",
                "rpr_dup_b": "lct_rpr_dup_b",
            },
            operation_id="op_rpr_incomplete_duplicate_expected",
        )


def test_repair_duplicate_consolidation_successor_must_be_active(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = RepairWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_a"),
    )
    second = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_dup_b"),
    )
    successor = repair_consolidation_successor(
        (first.record, second.record),
        status="invalidated",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="consolidation successor must be active",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "rpr_dup_a": first.fingerprint,
                "rpr_dup_b": second.fingerprint,
            },
            transition_ids={
                "rpr_dup_a": "lct_rpr_dup_a",
                "rpr_dup_b": "lct_rpr_dup_b",
            },
            operation_id="op_rpr_inactive_duplicate_successor",
        )


def test_repair_work_root_correction_event_to_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_reowned"),
    )
    source_reference = repair_reference(event_ref(), "rpr_reowned")
    source_root_before = repository.load_work(event_ref()).fingerprint
    destination_root_before = repository.load_work(support_ref()).fingerprint

    successor = repair_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        facilitator=support_facilitator(),
        participants=[support_repair_participant()],
    )
    service.correct_work_root(
        source_reference,
        support_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_rpr_reown_event_support",
        operation_id="op_rpr_reown_event_support",
    )

    source = service.resolve_exact(source_reference)
    destination = service.require_current_use(
        repair_reference(support_ref(), "rpr_reowned")
    )
    assert source.record.status == "superseded"
    assert destination.record.status == "active"
    assert destination.record.logical_id == "rpr_reowned"
    assert destination.record.field("focus") == created.record.field("focus")
    assert destination.record.field("context_refs") == created.record.field(
        "context_refs"
    )
    assert destination.record.field("workflow_state") == created.record.field(
        "workflow_state"
    )
    destination_participant = destination.record.field("participants")[0]
    source_participant = created.record.field("participants")[0]
    assert destination_participant["participant_key"] == source_participant[
        "participant_key"
    ]
    assert destination_participant["roles"] == source_participant["roles"]
    assert destination_participant["participation_state"] == source_participant[
        "participation_state"
    ]
    assert repository.load_work(event_ref()).fingerprint == source_root_before
    assert repository.load_work(support_ref()).fingerprint == destination_root_before

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_rpr_reown_event_support",
    )
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "work_root_corrected",
    }


def test_repair_work_root_correction_support_process_to_event(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        repair_work_record(
            work=support_ref(),
            repair_id="rpr_reowned",
        ),
    )
    source_reference = repair_reference(support_ref(), "rpr_reowned")

    successor = repair_work_root_successor(
        created.record,
        event_ref(),
        target=event_target(),
        facilitator=local_operator_facilitator(),
        participants=[event_repair_participant()],
    )
    service.correct_work_root(
        source_reference,
        event_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_rpr_reown_support_event",
        operation_id="op_rpr_reown_support_event",
    )

    assert service.resolve_exact(source_reference).record.status == "superseded"
    current = service.require_current_use(
        repair_reference(event_ref(), "rpr_reowned")
    )
    assert current.record.status == "active"
    assert current.record.field("focus") == created.record.field("focus")
    assert current.record.field("context_refs") == created.record.field(
        "context_refs"
    )


def test_repair_work_root_correction_accepts_invalidated_source(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        repair_work_record(repair_id="rpr_reowned"),
    )
    source_reference = repair_reference(event_ref(), "rpr_reowned")
    service.transition_lifecycle(
        source_reference,
        repair_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_rpr_before_reown_invalidate",
        reason_code="recording_error",
        operation_id="op_rpr_before_reown_invalidate",
    )
    invalidated = service.resolve_exact(source_reference)

    successor = repair_work_root_successor(
        invalidated.record,
        support_ref(),
        target=support_target(),
        facilitator=support_facilitator(),
        participants=[support_repair_participant()],
    )
    service.correct_work_root(
        source_reference,
        support_ref(),
        successor,
        expected=invalidated.fingerprint,
        transition_id="lct_rpr_reown_invalidated",
        operation_id="op_rpr_reown_invalidated",
    )

    assert service.resolve_exact(source_reference).record.status == "superseded"
    assert service.require_current_use(
        repair_reference(support_ref(), "rpr_reowned")
    ).record.status == "active"


def test_repair_work_root_correction_cannot_rewrite_focus(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    source_reference = repair_reference(event_ref(), "rpr_alpha")

    successor = repair_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        facilitator=support_facilitator(),
        participants=[support_repair_participant()],
        focus="Different Repair focus must use factual correction semantics.",
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite fact focus",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_bad_reown_focus",
            operation_id="op_rpr_bad_reown_focus",
        )

    assert service.resolve_exact(source_reference).fingerprint == created.fingerprint


def test_repair_work_root_correction_must_preserve_repair_id(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    source_reference = repair_reference(event_ref(), "rpr_alpha")

    successor = repair_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        facilitator=support_facilitator(),
        participants=[support_repair_participant()],
        repair_id="rpr_changed",
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction must preserve repair identity",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_bad_reown_id",
            operation_id="op_rpr_bad_reown_id",
        )


def test_repair_work_root_correction_rejects_stale_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = RepairWorkflowService(tmp_path)
    created = service.create(event_ref(), repair_work_record())
    source_reference = repair_reference(event_ref(), "rpr_alpha")

    service.transition_lifecycle(
        source_reference,
        repair_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T21:10:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_rpr_before_stale_reown",
        reason_code="recording_error",
        operation_id="op_rpr_before_stale_reown",
    )

    successor = repair_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        facilitator=support_facilitator(),
        participants=[support_repair_participant()],
    )
    with pytest.raises(
        PortiaConflictError,
        match="expected predecessor action state",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_rpr_stale_reown",
            operation_id="op_rpr_stale_reown",
        )
def test_repair_accepts_completed_event_action_fixture_shape(tmp_path: Path) -> None:
    seed_event(tmp_path)
    completed = RepairWorkflowService(tmp_path).create(
        event_ref(),
        repair_work_record(
            repair_id="rpr_event_completed",
            workflow_state="completed",
            completed_at="2026-09-06T21:30:00-04:00",
            participants=[
                event_repair_participant(participation_state="participated")
            ],
            actions=[
                {
                    "action_key": "restore",
                    "action_type": "return_or_restore_property",
                    "description": "Synthetic return of a classroom item.",
                    "agreed_by": ["student"],
                    "responsible_participant_keys": ["student"],
                    "completion_state": "completed",
                    "completed_at": "2026-09-06T21:20:00-04:00",
                }
            ],
        ),
    )

    assert completed.record.field("workflow_state") == "completed"
    assert completed.record.field("actions")[0]["completion_state"] == "completed"
    assert completed.record.field("remorse") is None
    assert completed.record.field("forgiveness") is None
    assert completed.record.field("relationship_restored") is None


def test_repair_accepts_other_role_and_other_action_fixture_shape(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    participant = {
        "participant_key": "community",
        "person": {
            "kind": "represented_human",
            "person": {
                "kind": "descriptive_person",
                "description_type": "community_member",
                "display_label": "Synthetic community participant",
            },
        },
        "roles": [
            {
                "kind": "other",
                "detail": "Synthetic bounded process-local role.",
            }
        ],
        "participation_state": "participated",
    }
    action = {
        "action_key": "other_action",
        "action_type": "other",
        "type_detail": "Synthetic locally described reparative action.",
        "description": "Synthetic bounded agreed action.",
        "agreed_by": ["community"],
        "completion_state": "planned",
    }

    created = RepairWorkflowService(tmp_path).create(
        event_ref(),
        repair_work_record(
            repair_id="rpr_event_other",
            workflow_state="active",
            participants=[participant],
            actions=[action],
        ),
    )

    assert created.record.field("participants")[0]["roles"][0]["kind"] == "other"
    assert created.record.field("actions")[0]["action_type"] == "other"


def test_support_repair_accepts_cross_work_context_fixture_shape(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_participant_record(
            "spp_peer",
            contexts=[{"kind": "supported_person"}],
            person={
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic peer",
            },
        ),
    )
    peer = support_repair_participant(
        key="peer",
        participant_id="spp_peer",
        participation_state="agreed_to_participate",
    )
    peer["roles"] = [{"kind": "affected_person"}]

    created = RepairWorkflowService(tmp_path).create(
        support_ref(),
        repair_work_record(
            work=support_ref(),
            repair_id="rpr_support_active",
            workflow_state="active",
            context_refs=[
                {"kind": "work", "work_ref": event_ref().to_dict()},
            ],
            participants=[
                support_repair_participant(
                    participation_state="agreed_to_participate"
                ),
                peer,
            ],
            actions=[
                {
                    "action_key": "community_action",
                    "action_type": "community_or_relationship_action",
                    "description": "Synthetic agreed community-oriented action.",
                    "agreed_by": ["student", "peer"],
                    "responsible_participant_keys": ["student"],
                    "completion_state": "planned",
                }
            ],
        ),
    )

    assert created.record.field("context_refs")[0]["work_ref"]["work_kind"] == "event"
    assert len(created.record.field("participants")) == 2


def test_support_repair_accepts_withdrawn_action_fixture_shape(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    created = RepairWorkflowService(tmp_path).create(
        support_ref(),
        repair_work_record(
            work=support_ref(),
            repair_id="rpr_support_withdrawn_action",
            workflow_state="active",
            participants=[
                support_repair_participant(participation_state="withdrew")
            ],
            actions=[
                {
                    "action_key": "restorative",
                    "action_type": "restorative_action",
                    "description": "Synthetic action that was later withdrawn.",
                    "agreed_by": ["student"],
                    "completion_state": "withdrawn",
                }
            ],
        ),
    )

    assert created.record.field("participants")[0]["participation_state"] == "withdrew"
    assert created.record.field("actions")[0]["completion_state"] == "withdrawn"


def test_support_repair_accepts_completed_nonfinancial_action_fixture_shape(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    created = RepairWorkflowService(tmp_path).create(
        support_ref(),
        repair_work_record(
            work=support_ref(),
            repair_id="rpr_support_completed",
            workflow_state="completed",
            completed_at="2026-09-06T21:30:00-04:00",
            participants=[
                support_repair_participant(participation_state="participated")
            ],
            actions=[
                {
                    "action_key": "replace",
                    "action_type": "repair_or_replace_property",
                    "description": "Synthetic non-financial property repair action.",
                    "agreed_by": ["student"],
                    "responsible_participant_keys": ["student"],
                    "completion_state": "completed",
                    "completed_at": "2026-09-06T21:20:00-04:00",
                }
            ],
        ),
    )

    assert created.record.field("workflow_state") == "completed"
    assert created.record.field("actions")[0]["action_type"] == (
        "repair_or_replace_property"
    )
    assert created.record.field("remorse") is None
    assert created.record.field("forgiveness") is None


def test_proposed_imported_support_repair_unknown_participation_is_readable(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    imported = repair_work_record(
        work=support_ref(),
        repair_id="rpr_support_import",
        status="proposed",
        source={
            "type": "import",
            "source_label": "Synthetic legacy repair export",
            "external_reference": "row-31",
        },
        participants=[
            support_repair_participant(participation_state="unknown")
        ],
    )
    repository.create_work_record(support_ref(), imported)

    service = RepairWorkflowService(tmp_path)
    reference = repair_reference(support_ref(), "rpr_support_import")
    assert service.load_exact(reference).record.logical_id == "rpr_support_import"
    assert service.resolve_exact(reference).record.status == "proposed"


def test_active_event_repair_rejects_unidentified_facilitator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    facilitator = {
        "kind": "represented_human",
        "person": {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    }

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Repair facilitator requires an identified operational human",
    ):
        RepairWorkflowService(tmp_path).create(
            event_ref(),
            repair_work_record(facilitator=facilitator),
        )


def test_active_imported_repair_requires_accepted_review_history(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    imported = repair_work_record(
        repair_id="rpr_imported_active",
        source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-31",
        },
    )
    repository.create_work_record(event_ref(), imported)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="paper/import activation requires accepted review history",
    ):
        RepairWorkflowService(tmp_path).require_current_use(
            repair_reference(event_ref(), "rpr_imported_active")
        )


def test_support_repair_participant_other_process_fixture_is_rejected(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    other_support = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_beta",
        work_kind="support_process",
        contract_version="1",
    )
    repository.create_work(
        other_support,
        support_process_record(work_id="sup_beta"),
    )
    repository.create_work_record(
        other_support,
        support_participant_record(
            "spp_elsewhere",
            work_id="sup_beta",
            contexts=[{"kind": "supported_person"}],
        ),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Repair participant Support Process Participant does not resolve "
            "in the owning Support Process"
        ),
    ):
        RepairWorkflowService(tmp_path).create(
            support_ref(),
            repair_work_record(
                work=support_ref(),
                participants=[
                    support_repair_participant(participant_id="spp_elsewhere")
                ],
            ),
        )


def test_repair_runtime_fixture_rejects_ordinary_correction_cross_work(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    repository = PortiaRepository(tmp_path)
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_other",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(other_work, event_record(event_id="evt_other"))
    repository.create_work_record(
        other_work,
        event_participant_record(event_id="evt_other"),
    )
    wire = repair_work_record(
        work=other_work,
        repair_id="rpr_cross_work",
    ).to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": repair_reference(
                event_ref(),
                "rpr_source",
            ).to_dict(),
            "reason": "focus_corrected",
        }
    ]
    bad = parse_portia_record("repair", "1", wire)
    repository.create_work_record(other_work, bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary repair correction cannot cross work roots",
    ):
        RepairWorkflowService(tmp_path).require_current_use(
            repair_reference(other_work, "rpr_cross_work")
        )
