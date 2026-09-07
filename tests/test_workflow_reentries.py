"""Issue #46 Slice 4a tests for core Reentry workflow authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    ReentryWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    reentry_reference,
)

TIMESTAMP = "2026-09-06T09:00:00-04:00"
UPDATED = "2026-09-06T09:05:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice4a_test"}


def event_ref(
    *,
    event_id: str = "evt_alpha",
    class_id: str = "class_a",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=event_id,
        work_kind="event",
        contract_version="2",
    )


def support_ref(
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


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
            "summary": "Synthetic bounded Event for Reentry testing.",
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


def local_operator_coordinator() -> dict[str, object]:
    return {
        "kind": "represented_human",
        "person": {
            "kind": "local_operator",
            "display_label": "Synthetic teacher",
        },
    }


def support_coordinator(
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


def event_context(
    *,
    class_id: str = "class_a",
    event_id: str = "evt_alpha",
) -> dict[str, object]:
    return {
        "kind": "event",
        "work_ref": event_ref(
            class_id=class_id,
            event_id=event_id,
        ).to_dict(),
    }


def support_context(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
) -> dict[str, object]:
    return {
        "kind": "support_process",
        "work_ref": support_ref(
            class_id=class_id,
            work_id=work_id,
        ).to_dict(),
    }


def support_plan_record(
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
    support_id: str = "spt_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "support",
        "1",
        {
            "schema_version": "1",
            "record_type": "support",
            "module_id": "portia",
            "class_id": class_id,
            "work_id": work_id,
            "support_id": support_id,
            "status": "active",
            "target": {
                "kind": "support_process",
            },
            "need_refs": [
                {
                    "record_kind": "support_need",
                    "record_id": "spn_alpha",
                    "contract_version": "1",
                }
            ],
            "strategy": {
                "kind": "access",
                "procedure": "Synthetic Reentry support plan.",
            },
            "provider_plan": {
                "kind": "no_assigned_provider",
                "reason": "access_condition",
            },
            "schedule": {
                "kind": "as_needed",
                "planned_duration": {"kind": "minutes", "minutes": 5},
            },
            "plan_state": "active",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def exact_work_record_ref(
    work: ExactPortiaWorkRef,
    *,
    record_kind: str,
    record_id: str,
    contract_version: str = "1",
) -> dict[str, object]:
    return {
        "work_ref": work.to_dict(),
        "record_ref": {
            "record_kind": record_kind,
            "record_id": record_id,
            "contract_version": contract_version,
        },
    }


def determination_record(
    *,
    determination_id: str = "det_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "determination",
        "1",
        {
            "schema_version": "1",
            "record_type": "determination",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "determination_id": determination_id,
            "status": "active",
            "target": event_target(),
            "question": "What bounded next step is appropriate?",
            "decision_maker": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "authority_context": {
                "kind": "teacher_local",
                "scope": "teacher_review",
            },
            "process_basis": {
                "kind": "teacher_local",
                "process_label": "Synthetic teacher-local review",
            },
            "outcome": {"kind": "insufficient_information"},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def response_record(
    *,
    response_id: str = "rsp_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "response",
        "1",
        {
            "schema_version": "1",
            "record_type": "response",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "response_id": response_id,
            "status": "active",
            "target": event_target(),
            "provider": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "action": {
                "family": "classroom_management",
                "description": "Synthetic bounded teacher-local response.",
            },
            "execution_state": "completed",
            "started_at": TIMESTAMP,
            "ended_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def communication_record(
    *,
    communication_id: str = "comm_reentry",
) -> PortiaRecord:
    return parse_portia_record(
        "communication",
        "1",
        {
            "schema_version": "1",
            "record_type": "communication",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_alpha",
            "communication_id": communication_id,
            "status": "active",
            "sender": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "recipients": [
                {
                    "person": {
                        "kind": "local_operator",
                        "display_label": "Synthetic collaborator",
                    },
                    "participation": "participated",
                }
            ],
            "method": {"kind": "in_person"},
            "purpose": {"kind": "reentry_or_repair"},
            "act_state": "completed",
            "privacy_scope": "ordinary",
            "started_at": TIMESTAMP,
            "ended_at": TIMESTAMP,
            "summary": "Synthetic bounded Reentry coordination communication.",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def intervention_record(
    *,
    work_id: str = "sup_beta",
    intervention_id: str = "int_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "intervention",
        "1",
        {
            "schema_version": "1",
            "record_type": "intervention",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": work_id,
            "intervention_id": intervention_id,
            "status": "proposed",
            "target": {"kind": "support_process"},
            "need_refs": [
                {
                    "record_kind": "support_need",
                    "record_id": "spn_alpha",
                    "contract_version": "1",
                }
            ],
            "goal_refs": [
                {
                    "record_kind": "support_goal",
                    "record_id": "spg_alpha",
                    "contract_version": "1",
                }
            ],
            "strategy": {
                "kind": "routine_or_structure",
                "procedure": "Synthetic bounded repeated support routine.",
            },
            "provider_plan": {
                "kind": "no_assigned_provider",
                "reason": "access_condition",
            },
            "schedule": {
                "kind": "as_needed",
                "planned_duration": {"kind": "minutes", "minutes": 10},
            },
            "monitoring_approach": "Synthetic bounded monitoring plan.",
            "plan_state": "planned",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_plan_ref(
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
    support_id: str = "spt_alpha",
) -> dict[str, object]:
    return {
        "work_ref": support_ref(
            work_id=work_id,
            class_id=class_id,
        ).to_dict(),
        "record_ref": {
            "record_kind": "support",
            "record_id": support_id,
            "contract_version": "1",
        },
    }


def reentry_record(
    *,
    work: ExactPortiaWorkRef | None = None,
    reentry_id: str = "ren_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    coordinator: dict[str, object] | None = None,
    initiating_context: dict[str, object] | None = None,
    planned_return: dict[str, object] | None = None,
    planned_elements: list[dict[str, object]] | None = None,
    support_refs: list[dict[str, object]] | None = None,
    workflow_state: str = "planned",
    completed_at: str | None = None,
    source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = UPDATED,
) -> PortiaRecord:
    selected = work or event_ref()
    if target is None:
        target = event_target() if selected.work_kind == "event" else support_target()
    if coordinator is None:
        coordinator = (
            local_operator_coordinator()
            if selected.work_kind == "event"
            else support_coordinator()
        )
    if initiating_context is None:
        initiating_context = (
            event_context()
            if selected.work_kind == "event"
            else support_context()
        )

    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "reentry",
        "module_id": "portia",
        "class_id": selected.class_id,
        "work_kind": selected.work_kind,
        "work_id": selected.work_id,
        "reentry_id": reentry_id,
        "status": status,
        "target": target,
        "coordinator": coordinator,
        "initiating_context": initiating_context,
        "planned_return": planned_return
        or {
            "kind": "date_only",
            "date": "2026-09-07",
        },
        "planned_elements": planned_elements
        or [
            {
                "kind": "orientation_or_check_in",
                "description": "Synthetic bounded teacher-local check-in.",
            }
        ],
        "workflow_state": workflow_state,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if support_refs is not None:
        wire["support_refs"] = support_refs
    if completed_at is not None:
        wire["completed_at"] = completed_at
    return parse_portia_record("reentry", "1", wire)


def reentry_successor(
    prior: PortiaRecord,
    *,
    reentry_id: str = "ren_successor",
    reason: str,
    updated_at: str = "2026-09-06T09:30:00-04:00",
    status: str = "active",
    planned_return: dict[str, object] | None = None,
    planned_elements: list[dict[str, object]] | None = None,
    workflow_state: str | None = None,
    completed_at: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    if not isinstance(prior_id, str):
        raise AssertionError("Reentry test predecessor must have a logical ID")
    wire["reentry_id"] = reentry_id
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if planned_return is not None:
        wire["planned_return"] = planned_return
    if planned_elements is not None:
        wire["planned_elements"] = planned_elements
    if workflow_state is not None:
        wire["workflow_state"] = workflow_state
    if completed_at is None:
        if workflow_state is not None and workflow_state != "completed":
            wire.pop("completed_at", None)
    else:
        wire["completed_at"] = completed_at
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
                    "record_kind": "reentry",
                    "record_id": prior_id,
                    "contract_version": "1",
                },
            },
            "reason": reason,
        }
    ]
    return parse_portia_record("reentry", "1", wire)


def reentry_consolidation_successor(
    priors: tuple[PortiaRecord, ...],
    *,
    reentry_id: str = "ren_canonical",
    status: str = "active",
    updated_at: str = "2026-09-06T10:00:00-04:00",
) -> PortiaRecord:
    assert priors
    wire = priors[0].to_dict()
    work = ExactPortiaWorkRef(
        class_id=str(wire["class_id"]),
        work_id=str(wire["work_id"]),
        work_kind=str(wire["work_kind"]),
        contract_version="2" if wire["work_kind"] == "event" else "1",
    )
    wire["reentry_id"] = reentry_id
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    wire["supersedes"] = [
        {
            "work_record_ref": reentry_reference(
                work,
                str(prior.logical_id),
            ).to_dict(),
            "reason": "duplicate_consolidated",
        }
        for prior in priors
    ]
    return parse_portia_record("reentry", "1", wire)


def reentry_work_root_successor(
    prior: PortiaRecord,
    destination_work: ExactPortiaWorkRef,
    *,
    target: dict[str, object],
    coordinator: dict[str, object],
    updated_at: str = "2026-09-06T10:30:00-04:00",
    reentry_id: str | None = None,
    planned_return: dict[str, object] | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    if not isinstance(prior_id, str):
        raise AssertionError("Reentry test predecessor must have a logical ID")
    wire["class_id"] = destination_work.class_id
    wire["work_kind"] = destination_work.work_kind
    wire["work_id"] = destination_work.work_id
    wire["reentry_id"] = reentry_id or prior_id
    wire["status"] = "active"
    wire["target"] = target
    wire["coordinator"] = coordinator
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if planned_return is not None:
        wire["planned_return"] = planned_return
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
                    "record_kind": "reentry",
                    "record_id": prior_id,
                    "contract_version": "1",
                },
            },
            "reason": "work_root_corrected",
        }
    ]
    return parse_portia_record("reentry", "1", wire)


def reentry_lifecycle_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str = "2026-09-06T09:15:00-04:00",
    planned_return: dict[str, object] | None = None,
    workflow_state: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if planned_return is not None:
        wire["planned_return"] = planned_return
    if workflow_state is not None:
        wire["workflow_state"] = workflow_state
    return parse_portia_record("reentry", "1", wire)


def reentry_workflow_revision(
    prior: PortiaRecord,
    *,
    workflow_state: str,
    updated_at: str = "2026-09-06T09:15:00-04:00",
    completed_at: str | None = None,
    planned_elements: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["workflow_state"] = workflow_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if completed_at is None:
        wire.pop("completed_at", None)
    else:
        wire["completed_at"] = completed_at
    if planned_elements is not None:
        wire["planned_elements"] = planned_elements
    return parse_portia_record("reentry", "1", wire)


def seed_event(
    tmp_path: Path,
    *,
    status: str = "active",
) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record(status=status))
    repository.create_work_record(
        event_ref(),
        event_participant_record(),
    )
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


def test_create_load_list_and_current_event_reentry(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())

    reference = reentry_reference(event_ref(), "ren_alpha")
    assert created.record.logical_id == "ren_alpha"
    assert service.load_exact(reference).record.logical_id == "ren_alpha"
    assert service.resolve_exact(reference).record.logical_id == "ren_alpha"
    assert [item.record.logical_id for item in service.list_reentries(event_ref())] == [
        "ren_alpha"
    ]
    assert service.require_current_use(reference).record.logical_id == "ren_alpha"
    assert service.resolve_current(reference).record.logical_id == "ren_alpha"


def test_active_reentry_can_target_closed_event_history(tmp_path: Path) -> None:
    seed_event(tmp_path, status="closed")
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    assert created.record.status == "active"
    assert service.require_current_use(
        reentry_reference(event_ref(), "ren_alpha")
    ).record.status == "active"


def test_active_support_reentry_accepts_coordinator_context(tmp_path: Path) -> None:
    seed_support(tmp_path)
    created = ReentryWorkflowService(tmp_path).create(
        support_ref(),
        reentry_record(work=support_ref()),
    )
    assert created.record.logical_id == "ren_alpha"


def test_proposed_reentry_preserves_descriptive_coordinator_but_not_current(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    coordinator = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }
    service = ReentryWorkflowService(tmp_path)
    service.create(
        event_ref(),
        reentry_record(
            status="proposed",
            coordinator=coordinator,
        ),
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.require_current_use(
            reentry_reference(event_ref(), "ren_alpha")
        )


def test_active_event_reentry_rejects_roster_student_coordinator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    coordinator = {
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
            "Reentry coordinator cannot use roster-student identity "
            "as operational authority"
        ),
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(coordinator=coordinator),
        )


def test_active_support_reentry_requires_operational_coordinator_context(
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
            r"Reentry coordinator requires Support Process Participant context "
            r"in \{coordinator, provider_or_collaborator\}"
        ),
    ):
        ReentryWorkflowService(tmp_path).create(
            support_ref(),
            reentry_record(
                work=support_ref(),
                coordinator=support_coordinator("spp_family"),
            ),
        )


def test_reentry_rejects_updated_before_created(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Reentry updated_at cannot precede Reentry created_at",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                created_at="2026-09-06T10:00:00-04:00",
                updated_at="2026-09-06T09:59:00-04:00",
            ),
        )


def test_reentry_rejects_reversed_date_window(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Reentry ends_on cannot precede Reentry starts_on",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                planned_return={
                    "kind": "window",
                    "starts_on": "2026-09-08",
                    "ends_on": "2026-09-07",
                }
            ),
        )


def test_reentry_rejects_reversed_exact_window(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Reentry ends_at cannot precede Reentry starts_at",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                planned_return={
                    "kind": "window",
                    "starts_at": "2026-09-08T09:00:00-04:00",
                    "ends_at": "2026-09-08T08:59:00-04:00",
                }
            ),
        )


def test_reentry_rejects_initiating_context_other_class(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowOwnershipError,
        match="initiating context must remain in the owning class",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                initiating_context=event_context(
                    class_id="class_b",
                    event_id="evt_beta",
                ),
            ),
        )


def test_event_reentry_accepts_exact_support_plan_link(tmp_path: Path) -> None:
    repository = seed_event(tmp_path)
    repository.create_work(support_ref(), support_process_record())
    repository.create_work_record(
        support_ref(),
        support_plan_record(),
    )
    created = ReentryWorkflowService(tmp_path).create(
        event_ref(),
        reentry_record(
            support_refs=[support_plan_ref()],
        ),
    )
    assert created.record.logical_id == "ren_alpha"


def test_reentry_support_plan_rejects_other_class(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowOwnershipError,
        match="Reentry support plan must remain in the owning class",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                support_refs=[
                    support_plan_ref(
                        class_id="class_b",
                        work_id="sup_beta",
                        support_id="spt_beta",
                    )
                ],
            ),
        )


def test_support_owned_reentry_plan_must_share_process(tmp_path: Path) -> None:
    repository = seed_support(tmp_path)
    other = support_ref(work_id="sup_beta")
    repository.create_work(
        other,
        support_process_record(work_id="sup_beta"),
    )
    repository.create_work_record(
        other,
        support_plan_record(
            work_id="sup_beta",
            support_id="spt_beta",
        ),
    )
    with pytest.raises(
        WorkflowOwnershipError,
        match="Support-Process-owned Reentry plan must share process",
    ):
        ReentryWorkflowService(tmp_path).create(
            support_ref(),
            reentry_record(
                work=support_ref(),
                support_refs=[
                    support_plan_ref(
                        work_id="sup_beta",
                        support_id="spt_beta",
                    )
                ],
            ),
        )


def test_reentry_accepts_minimal_external_initiating_context(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    created = ReentryWorkflowService(tmp_path).create(
        event_ref(),
        reentry_record(
            initiating_context={
                "kind": "external_or_restricted_process",
                "system_label": "Synthetic external system",
                "reference_id": "external-123",
                "status_label": "return planned",
            },
        ),
    )
    assert created.record.logical_id == "ren_alpha"


def test_proposed_imported_reentry_is_exactly_readable(tmp_path: Path) -> None:
    repository = seed_support(tmp_path)
    imported = reentry_record(
        work=support_ref(),
        reentry_id="ren_imported",
        status="proposed",
        source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-1",
        },
    )
    repository.create_work_record(support_ref(), imported)

    service = ReentryWorkflowService(tmp_path)
    reference = reentry_reference(support_ref(), "ren_imported")
    assert service.load_exact(reference).record.logical_id == "ren_imported"
    assert service.resolve_exact(reference).record.status == "proposed"


def test_active_imported_reentry_requires_accepted_review_history(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    imported = reentry_record(
        reentry_id="ren_imported_active",
        source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-1",
        },
    )
    repository.create_work_record(event_ref(), imported)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="paper/import activation requires accepted review history",
    ):
        ReentryWorkflowService(tmp_path).require_current_use(
            reentry_reference(event_ref(), "ren_imported_active")
        )


def test_reentry_planned_can_progress_to_active(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")

    accepted = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state="active",
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == "active"
    assert accepted.record.field("completed_at") is None
    assert service.require_current_use(reference).fingerprint == accepted.fingerprint


def test_reentry_planned_can_be_recorded_directly_completed(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")

    accepted = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state="completed",
            completed_at="2026-09-06T08:55:00-04:00",
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == "completed"
    assert accepted.record.field("completed_at") == "2026-09-06T08:55:00-04:00"
    # Completion is only a factual process state. Current exact use remains
    # possible and no clearance/outcome record is manufactured.
    assert service.require_current_use(reference).record.field(
        "workflow_state"
    ) == "completed"


def test_reentry_active_can_progress_to_completed(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(workflow_state="active"),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    accepted = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state="completed",
            completed_at="2026-09-06T09:10:00-04:00",
        ),
        expected=created.fingerprint,
    )
    assert accepted.record.field("workflow_state") == "completed"


@pytest.mark.parametrize("terminal", ["cancelled", "unable_to_complete"])
def test_reentry_planned_can_progress_to_noncompletion_terminal(
    tmp_path: Path,
    terminal: str,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")

    accepted = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state=terminal,
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == terminal
    assert accepted.record.field("completed_at") is None


def test_reentry_terminal_workflow_state_cannot_progress_again(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="active"))
    reference = reentry_reference(event_ref(), "ren_alpha")
    terminal = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state="completed",
            completed_at="2026-09-06T09:10:00-04:00",
        ),
        expected=created.fingerprint,
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="illegal Reentry workflow_state transition: completed -> cancelled",
    ):
        service.transition_workflow_state(
            reference,
            reentry_workflow_revision(
                terminal.record,
                workflow_state="cancelled",
                updated_at="2026-09-06T09:20:00-04:00",
            ),
            expected=terminal.fingerprint,
        )


def test_reentry_workflow_progression_cannot_rewrite_planned_elements(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "ordinary Reentry workflow-state progression cannot rewrite "
            "field planned_elements"
        ),
    ):
        service.transition_workflow_state(
            reference,
            reentry_workflow_revision(
                created.record,
                workflow_state="active",
                planned_elements=[
                    {
                        "kind": "academic_access",
                        "description": "Improperly rewritten plan element.",
                    }
                ],
            ),
            expected=created.fingerprint,
        )


def test_reentry_workflow_progression_requires_active_canonical_status(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(
            status="proposed",
            workflow_state="planned",
        ),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.transition_workflow_state(
            reference,
            reentry_workflow_revision(
                created.record,
                workflow_state="active",
            ),
            expected=created.fingerprint,
        )


def test_reentry_workflow_progression_rejects_stale_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")
    accepted = service.transition_workflow_state(
        reference,
        reentry_workflow_revision(
            created.record,
            workflow_state="active",
        ),
        expected=created.fingerprint,
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected Reentry state does not match canonical bytes",
    ):
        service.transition_workflow_state(
            reference,
            reentry_workflow_revision(
                accepted.record,
                workflow_state="completed",
                updated_at="2026-09-06T09:25:00-04:00",
                completed_at="2026-09-06T09:20:00-04:00",
            ),
            expected=created.fingerprint,
        )


def test_reentry_workflow_progression_rejects_backdated_update(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record(workflow_state="planned"))
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Reentry updated_at cannot precede Reentry prior updated_at",
    ):
        service.transition_workflow_state(
            reference,
            reentry_workflow_revision(
                created.record,
                workflow_state="active",
                updated_at="2026-09-06T09:04:00-04:00",
            ),
            expected=created.fingerprint,
        )


def test_proposed_reentry_can_activate_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(
            status="proposed",
            workflow_state="planned",
        ),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    service.transition_lifecycle(
        reference,
        reentry_lifecycle_revision(
            created.record,
            status="active",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_activate",
        reason_code="reviewed",
        operation_id="op_ren_activate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "active"
    assert accepted.record.field("workflow_state") == "planned"
    assert service.require_current_use(reference).fingerprint == accepted.fingerprint

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_ren_activate",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"
    assert transition.record.to_dict()["reason"] == {
        "category": "workflow",
        "code": "reviewed",
    }


def test_active_reentry_can_be_invalidated_and_stops_current_use(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    reference = reentry_reference(event_ref(), "ren_alpha")

    service.transition_lifecycle(
        reference,
        reentry_lifecycle_revision(
            created.record,
            status="invalidated",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_invalidate",
        reason_code="recording_error",
        operation_id="op_ren_invalidate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "invalidated"
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.require_current_use(reference)

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_ren_invalidate",
    )
    assert transition.record.to_dict()["reason"] == {
        "category": "record_validity",
        "code": "recording_error",
    }


def test_proposed_reentry_can_be_invalidated_without_activation(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(status="proposed"),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    service.transition_lifecycle(
        reference,
        reentry_lifecycle_revision(
            created.record,
            status="invalidated",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_proposed_invalid",
        reason_code="recording_error",
        operation_id="op_ren_proposed_invalid",
    )

    assert service.load_exact(reference).record.status == "invalidated"


def test_reentry_lifecycle_cannot_rewrite_planned_return(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(status="proposed"),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "ordinary downstream lifecycle replacement cannot rewrite "
            "field planned_return"
        ),
    ):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="active",
                planned_return={
                    "kind": "date_only",
                    "date": "2026-09-08",
                },
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_bad_plan",
            reason_code="reviewed",
            operation_id="op_ren_bad_plan",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_reentry_lifecycle_cannot_rewrite_workflow_state(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(
            status="proposed",
            workflow_state="planned",
        ),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "ordinary downstream lifecycle replacement cannot rewrite "
            "field workflow_state"
        ),
    ):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="active",
                workflow_state="active",
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_bad_state",
            reason_code="reviewed",
            operation_id="op_ren_bad_state",
        )


def test_reentry_supersession_is_reserved_for_correction(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="downstream supersession requires the correction workflow",
    ):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="superseded",
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_bad_superseded",
            reason_code="recording_error",
            operation_id="op_ren_bad_superseded",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_reentry_lifecycle_requires_current_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(status="proposed"),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    service.transition_lifecycle(
        reference,
        reentry_lifecycle_revision(
            created.record,
            status="active",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_activate_once",
        reason_code="reviewed",
        operation_id="op_ren_activate_once",
    )

    with pytest.raises(PortiaConflictError):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="invalidated",
                updated_at="2026-09-06T09:20:00-04:00",
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_stale",
            reason_code="recording_error",
            operation_id="op_ren_stale",
        )


def test_reentry_lifecycle_effective_at_cannot_precede_creation(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(status="proposed"),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="downstream lifecycle effective_at cannot precede record creation",
    ):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="active",
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_bad_effective",
            reason_code="reviewed",
            effective_at="2026-09-05T08:00:00-04:00",
            operation_id="op_ren_bad_effective",
        )


def test_reentry_activation_revalidates_operational_coordinator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    descriptive = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(
            status="proposed",
            coordinator=descriptive,
        ),
    )
    reference = reentry_reference(event_ref(), "ren_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry coordinator requires an identified operational human",
    ):
        service.transition_lifecycle(
            reference,
            reentry_lifecycle_revision(
                created.record,
                status="active",
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_bad_authority",
            reason_code="reviewed",
            operation_id="op_ren_bad_authority",
        )

    assert service.load_exact(reference).record.status == "proposed"


def test_reentry_timing_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_old"),
    )
    predecessor = reentry_reference(event_ref(), "ren_old")
    successor = reentry_successor(
        created.record,
        reason="timing_corrected",
        planned_return={
            "kind": "date_only",
            "date": "2026-09-08",
        },
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_ren_timing_correction",
        operation_id="op_ren_timing_correction",
    )

    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        reentry_reference(event_ref(), "ren_successor")
    )
    assert old_exact.record.status == "superseded"
    assert current.record.status == "active"
    assert current.record.field("planned_return") == {
        "kind": "date_only",
        "date": "2026-09-08",
    }

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_ren_timing_correction",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "timing_corrected",
    }

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.require_current_use(predecessor)


def test_reentry_correction_reason_must_match_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    predecessor = reentry_reference(event_ref(), "ren_alpha")
    successor = reentry_successor(
        created.record,
        reason="timing_corrected",
        planned_elements=[
            {
                "kind": "academic_access",
                "description": "Corrected bounded academic access plan.",
            }
        ],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected fact",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_ren_bad_reason",
            operation_id="op_ren_bad_reason",
        )


def test_reentry_correction_requires_actual_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    predecessor = reentry_reference(event_ref(), "ren_alpha")
    successor = reentry_successor(
        created.record,
        reason="timing_corrected",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires an actual Reentry fact change",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_ren_noop",
            operation_id="op_ren_noop",
        )


def test_reentry_correction_successor_must_be_active(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    predecessor = reentry_reference(event_ref(), "ren_alpha")
    successor = reentry_successor(
        created.record,
        reason="timing_corrected",
        status="invalidated",
        planned_return={
            "kind": "date_only",
            "date": "2026-09-08",
        },
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="corrected Reentry successor must be active",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_ren_inactive_successor",
            operation_id="op_ren_inactive_successor",
        )


def test_reentry_correction_rejects_wrong_selected_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_first"),
    )
    second = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_other"),
    )
    successor = reentry_successor(
        first.record,
        reason="timing_corrected",
        planned_return={
            "kind": "date_only",
            "date": "2026-09-08",
        },
    )

    with pytest.raises(
        WorkflowOwnershipError,
        match="must supersede the exact selected predecessor",
    ):
        service.correct(
            reentry_reference(event_ref(), "ren_other"),
            successor,
            expected=second.fingerprint,
            transition_id="lct_ren_wrong_predecessor",
            operation_id="op_ren_wrong_predecessor",
        )


def test_reentry_correction_requires_current_expected_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    predecessor = reentry_reference(event_ref(), "ren_alpha")
    service.correct(
        predecessor,
        reentry_successor(
            created.record,
            reason="timing_corrected",
            planned_return={
                "kind": "date_only",
                "date": "2026-09-08",
            },
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_first_correction",
        operation_id="op_ren_first_correction",
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected predecessor action state",
    ):
        service.correct(
            predecessor,
            reentry_successor(
                created.record,
                reentry_id="ren_second_successor",
                reason="plan_element_corrected",
                updated_at="2026-09-06T09:40:00-04:00",
                planned_elements=[
                    {
                        "kind": "academic_access",
                        "description": "Synthetic corrected access plan.",
                    }
                ],
            ),
            expected=created.fingerprint,
            transition_id="lct_ren_stale_correction",
            operation_id="op_ren_stale_correction",
        )


def test_reentry_completion_correction_can_correct_completion_facts(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(
            workflow_state="completed",
            completed_at="2026-09-06T08:45:00-04:00",
        ),
    )
    predecessor = reentry_reference(event_ref(), "ren_alpha")
    successor = reentry_successor(
        created.record,
        reason="completion_corrected",
        workflow_state="unable_to_complete",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_ren_completion_correction",
        operation_id="op_ren_completion_correction",
    )
    current = service.require_current_use(
        reentry_reference(event_ref(), "ren_successor")
    )
    assert current.record.field("workflow_state") == "unable_to_complete"
    assert current.record.field("completed_at") is None


def test_reentry_duplicate_consolidation_supersedes_all_exact_predecessors(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_a"),
    )
    second = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_b"),
    )
    successor = reentry_consolidation_successor(
        (first.record, second.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "ren_dup_a": first.fingerprint,
            "ren_dup_b": second.fingerprint,
        },
        transition_ids={
            "ren_dup_a": "lct_ren_dup_a_consolidate",
            "ren_dup_b": "lct_ren_dup_b_consolidate",
        },
        operation_id="op_ren_duplicate_consolidation",
    )

    first_ref = reentry_reference(event_ref(), "ren_dup_a")
    second_ref = reentry_reference(event_ref(), "ren_dup_b")
    assert service.resolve_exact(first_ref).record.status == "superseded"
    assert service.resolve_exact(second_ref).record.status == "superseded"
    current = service.require_current_use(
        reentry_reference(event_ref(), "ren_canonical")
    )
    assert current.record.status == "active"

    for transition_id in (
        "lct_ren_dup_a_consolidate",
        "lct_ren_dup_b_consolidate",
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

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.require_current_use(first_ref)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry use requires active canonical status",
    ):
        service.require_current_use(second_ref)


def test_reentry_duplicate_consolidation_accepts_invalidated_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_a"),
    )
    second = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_b"),
    )
    second_ref = reentry_reference(event_ref(), "ren_dup_b")
    service.transition_lifecycle(
        second_ref,
        reentry_lifecycle_revision(
            second.record,
            status="invalidated",
            updated_at="2026-09-06T09:20:00-04:00",
        ),
        expected=second.fingerprint,
        transition_id="lct_ren_dup_b_invalidate",
        reason_code="recording_error",
        operation_id="op_ren_dup_b_invalidate",
    )
    invalidated = service.resolve_exact(second_ref)
    successor = reentry_consolidation_successor(
        (first.record, invalidated.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "ren_dup_a": first.fingerprint,
            "ren_dup_b": invalidated.fingerprint,
        },
        transition_ids={
            "ren_dup_a": "lct_ren_dup_a_consolidate",
            "ren_dup_b": "lct_ren_dup_b_consolidate",
        },
        operation_id="op_ren_duplicate_with_invalidated",
    )

    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        reentry_reference(event_ref(), "ren_canonical")
    ).record.status == "active"


def test_reentry_duplicate_consolidation_rejects_one_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    successor = reentry_consolidation_successor((created.record,))

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two reentry predecessors",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"ren_alpha": created.fingerprint},
            transition_ids={"ren_alpha": "lct_ren_only_duplicate"},
            operation_id="op_ren_bad_single_duplicate",
        )


def test_reentry_duplicate_consolidation_requires_complete_expected_map(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_a"),
    )
    second = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_b"),
    )
    successor = reentry_consolidation_successor(
        (first.record, second.record),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="one expected fingerprint for every predecessor",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"ren_dup_a": first.fingerprint},
            transition_ids={
                "ren_dup_a": "lct_ren_dup_a",
                "ren_dup_b": "lct_ren_dup_b",
            },
            operation_id="op_ren_incomplete_duplicate_expected",
        )


def test_reentry_duplicate_consolidation_successor_must_be_active(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_a"),
    )
    second = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_dup_b"),
    )
    successor = reentry_consolidation_successor(
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
                "ren_dup_a": first.fingerprint,
                "ren_dup_b": second.fingerprint,
            },
            transition_ids={
                "ren_dup_a": "lct_ren_dup_a",
                "ren_dup_b": "lct_ren_dup_b",
            },
            operation_id="op_ren_inactive_duplicate_successor",
        )


def test_reentry_work_root_correction_event_to_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_reowned"),
    )
    source_reference = reentry_reference(event_ref(), "ren_reowned")
    source_root_before = repository.load_work(event_ref()).fingerprint
    destination_root_before = repository.load_work(support_ref()).fingerprint

    successor = reentry_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        coordinator=support_coordinator(),
    )
    service.correct_work_root(
        source_reference,
        support_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_ren_reown_event_support",
        operation_id="op_ren_reown_event_support",
    )

    source = service.resolve_exact(source_reference)
    destination_reference = reentry_reference(
        support_ref(),
        "ren_reowned",
    )
    destination = service.require_current_use(destination_reference)

    assert source.record.status == "superseded"
    assert destination.record.status == "active"
    assert destination.record.logical_id == "ren_reowned"
    assert (
        destination.record.field("initiating_context")
        == created.record.field("initiating_context")
    )
    assert (
        destination.record.field("planned_return")
        == created.record.field("planned_return")
    )
    assert (
        destination.record.field("planned_elements")
        == created.record.field("planned_elements")
    )
    assert (
        destination.record.field("workflow_state")
        == created.record.field("workflow_state")
    )
    assert repository.load_work(event_ref()).fingerprint == source_root_before
    assert repository.load_work(support_ref()).fingerprint == destination_root_before

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_ren_reown_event_support",
    )
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "work_root_corrected",
    }


def test_reentry_work_root_correction_support_process_to_event(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        reentry_record(
            work=support_ref(),
            reentry_id="ren_reowned",
        ),
    )
    source_reference = reentry_reference(support_ref(), "ren_reowned")

    successor = reentry_work_root_successor(
        created.record,
        event_ref(),
        target=event_target(),
        coordinator=local_operator_coordinator(),
    )
    service.correct_work_root(
        source_reference,
        event_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_ren_reown_support_event",
        operation_id="op_ren_reown_support_event",
    )

    assert service.resolve_exact(source_reference).record.status == "superseded"
    current = service.require_current_use(
        reentry_reference(event_ref(), "ren_reowned")
    )
    assert current.record.status == "active"
    assert (
        current.record.field("initiating_context")
        == created.record.field("initiating_context")
    )
    assert (
        current.record.field("planned_return")
        == created.record.field("planned_return")
    )


def test_reentry_work_root_correction_accepts_invalidated_source(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        reentry_record(reentry_id="ren_reowned"),
    )
    source_reference = reentry_reference(event_ref(), "ren_reowned")
    service.transition_lifecycle(
        source_reference,
        reentry_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T10:00:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_before_reown_invalidate",
        reason_code="recording_error",
        operation_id="op_ren_before_reown_invalidate",
    )
    invalidated = service.resolve_exact(source_reference)

    successor = reentry_work_root_successor(
        invalidated.record,
        support_ref(),
        target=support_target(),
        coordinator=support_coordinator(),
    )
    service.correct_work_root(
        source_reference,
        support_ref(),
        successor,
        expected=invalidated.fingerprint,
        transition_id="lct_ren_reown_invalidated",
        operation_id="op_ren_reown_invalidated",
    )

    assert service.resolve_exact(source_reference).record.status == "superseded"
    assert service.require_current_use(
        reentry_reference(support_ref(), "ren_reowned")
    ).record.status == "active"


def test_reentry_work_root_correction_cannot_rewrite_planned_return(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    source_reference = reentry_reference(event_ref(), "ren_alpha")

    successor = reentry_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        coordinator=support_coordinator(),
        planned_return={
            "kind": "date_only",
            "date": "2026-09-09",
        },
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite fact planned_return",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_ren_bad_reown_timing",
            operation_id="op_ren_bad_reown_timing",
        )

    assert service.resolve_exact(source_reference).fingerprint == created.fingerprint


def test_reentry_work_root_correction_must_preserve_reentry_id(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    source_reference = reentry_reference(event_ref(), "ren_alpha")

    successor = reentry_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        coordinator=support_coordinator(),
        reentry_id="ren_changed",
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction must preserve reentry identity",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_ren_bad_reown_id",
            operation_id="op_ren_bad_reown_id",
        )


def test_reentry_work_root_correction_rejects_stale_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = ReentryWorkflowService(tmp_path)
    created = service.create(event_ref(), reentry_record())
    source_reference = reentry_reference(event_ref(), "ren_alpha")

    service.transition_lifecycle(
        source_reference,
        reentry_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T10:00:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_ren_before_stale_reown",
        reason_code="recording_error",
        operation_id="op_ren_before_stale_reown",
    )

    successor = reentry_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        coordinator=support_coordinator(),
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
            transition_id="lct_ren_stale_reown",
            operation_id="op_ren_stale_reown",
        )


def test_reentry_accepts_exact_response_initiating_context(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        response_record(),
    )
    created = ReentryWorkflowService(tmp_path).create(
        event_ref(),
        reentry_record(
            reentry_id="ren_response",
            initiating_context={
                "kind": "response",
                "record_ref": exact_work_record_ref(
                    event_ref(),
                    record_kind="response",
                    record_id="rsp_alpha",
                ),
            },
            planned_return={
                "kind": "exact_time",
                "at": "2026-09-07T08:30:00-04:00",
            },
            workflow_state="active",
        ),
    )
    assert created.record.logical_id == "ren_response"


def test_reentry_accepts_date_window_determination_context(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        determination_record(),
    )
    created = ReentryWorkflowService(tmp_path).create(
        event_ref(),
        reentry_record(
            reentry_id="ren_det",
            initiating_context={
                "kind": "determination",
                "record_ref": exact_work_record_ref(
                    event_ref(),
                    record_kind="determination",
                    record_id="det_alpha",
                ),
            },
            planned_return={
                "kind": "window",
                "starts_on": "2026-09-07",
                "ends_on": "2026-09-08",
            },
            planned_elements=[
                {
                    "kind": "orientation_or_check_in",
                    "description": "Synthetic bounded check-in.",
                },
                {
                    "kind": "academic_access",
                    "description": "Synthetic bounded class-material access.",
                },
            ],
        ),
    )
    assert created.record.logical_id == "ren_det"


def test_event_reentry_accepts_exact_support_and_intervention_links(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    alpha = support_ref()
    beta = support_ref(work_id="sup_beta")
    repository.create_work(alpha, support_process_record())
    repository.create_work_record(
        alpha,
        support_plan_record(),
    )
    repository.create_work(
        beta,
        support_process_record(work_id="sup_beta"),
    )
    repository.create_work_record(
        beta,
        intervention_record(),
    )

    created = ReentryWorkflowService(tmp_path).create(
        event_ref(),
        reentry_record(
            reentry_id="ren_links",
            planned_elements=[
                {
                    "kind": "communication",
                    "description": "Synthetic bounded coordination element.",
                }
            ],
            support_refs=[
                support_plan_ref(),
                exact_work_record_ref(
                    beta,
                    record_kind="intervention",
                    record_id="int_alpha",
                ),
            ],
        ),
    )
    assert len(created.record.field("support_refs")) == 2


def test_support_reentry_accepts_exact_window_communication_context(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        communication_record(),
    )
    repository.create_work_record(
        support_ref(),
        support_plan_record(),
    )
    created = ReentryWorkflowService(tmp_path).create(
        support_ref(),
        reentry_record(
            work=support_ref(),
            reentry_id="ren_sp_com",
            initiating_context={
                "kind": "communication",
                "record_ref": exact_work_record_ref(
                    support_ref(),
                    record_kind="communication",
                    record_id="comm_reentry",
                ),
            },
            planned_return={
                "kind": "window",
                "starts_at": "2026-09-07T08:00:00-04:00",
                "ends_at": "2026-09-07T10:00:00-04:00",
            },
            planned_elements=[
                {
                    "kind": "schedule_or_environment",
                    "description": "Synthetic bounded first-transition adjustment.",
                },
                {
                    "kind": "support_handoff",
                    "description": "Synthetic bounded existing-plan handoff.",
                },
            ],
            support_refs=[support_plan_ref()],
            workflow_state="active",
        ),
    )
    assert created.record.logical_id == "ren_sp_com"


def test_support_reentry_accepts_completed_event_context_without_clearance_inference(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    seed_event(tmp_path)
    created = ReentryWorkflowService(tmp_path).create(
        support_ref(),
        reentry_record(
            work=support_ref(),
            reentry_id="ren_sp_done",
            initiating_context=event_context(),
            workflow_state="completed",
            completed_at="2026-09-07T09:15:00-04:00",
        ),
    )
    assert created.record.field("workflow_state") == "completed"
    assert created.record.field("completed_at") == "2026-09-07T09:15:00-04:00"


def test_support_reentry_accepts_other_context_and_other_planned_element(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    created = ReentryWorkflowService(tmp_path).create(
        support_ref(),
        reentry_record(
            work=support_ref(),
            reentry_id="ren_other",
            initiating_context={
                "kind": "other",
                "detail": "Synthetic bounded initiating classroom context.",
            },
            planned_elements=[
                {
                    "kind": "other",
                    "description": "Synthetic bounded teacher-local return element.",
                }
            ],
        ),
    )
    assert created.record.logical_id == "ren_other"


def test_active_event_reentry_rejects_unidentified_coordinator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    coordinator = {
        "kind": "represented_human",
        "person": {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Reentry coordinator requires an identified operational human",
    ):
        ReentryWorkflowService(tmp_path).create(
            event_ref(),
            reentry_record(
                reentry_id="ren_unid",
                coordinator=coordinator,
            ),
        )


def test_reentry_rejects_self_supersession(tmp_path: Path) -> None:
    repository = seed_event(tmp_path)
    wire = reentry_record(
        reentry_id="ren_self",
    ).to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": reentry_reference(
                event_ref(),
                "ren_self",
            ).to_dict(),
            "reason": "timing_corrected",
        }
    ]
    bad = parse_portia_record("reentry", "1", wire)
    repository.create_work_record(event_ref(), bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="reentry cannot supersede itself",
    ):
        ReentryWorkflowService(tmp_path).require_current_use(
            reentry_reference(event_ref(), "ren_self")
        )


def test_reentry_rejects_ordinary_correction_cross_work(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    repository = seed_support(tmp_path)
    wire = reentry_record(
        work=support_ref(),
        reentry_id="ren_cross_work",
    ).to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": reentry_reference(
                event_ref(),
                "ren_source",
            ).to_dict(),
            "reason": "timing_corrected",
        }
    ]
    bad = parse_portia_record("reentry", "1", wire)
    repository.create_work_record(support_ref(), bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary reentry correction cannot cross work roots",
    ):
        ReentryWorkflowService(tmp_path).require_current_use(
            reentry_reference(support_ref(), "ren_cross_work")
        )
