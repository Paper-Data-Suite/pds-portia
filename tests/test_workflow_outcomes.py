"""Issue #46 Slice 3a tests for core Outcome workflow authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef, ModuleWorkRecordRef
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    OutcomeWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    outcome_reference,
)

TIMESTAMP = "2026-09-06T09:00:00-04:00"
UPDATED = "2026-09-06T09:05:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice3a_test"}


class RecordingModuleBasisAuthority:
    def __init__(self, *, result: object | None = object()) -> None:
        self.result = result
        self.references: list[ModuleWorkRecordRef] = []

    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object | None:
        self.references.append(reference)
        return self.result


def event_ref(
    *,
    event_id: str = "evt_alpha",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id=event_id,
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


def event_record(
    *,
    event_id: str = "evt_alpha",
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
            "class_id": "class_a",
            "work_id": event_id,
            "school_year": "2026-2027",
            "status": status,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
            "occurrence": {"precision": "exact", "started_at": TIMESTAMP},
            "summary": "Synthetic bounded Event for Outcome testing.",
        },
    )


def event_participant_record(
    *,
    event_id: str = "evt_alpha",
    participant_id: str = "ep_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
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


def support_process_record() -> PortiaRecord:
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
            "class_id": "class_a",
            "work_id": "sup_alpha",
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


def local_operator_evaluator() -> dict[str, object]:
    return {
        "kind": "represented_human",
        "person": {
            "kind": "local_operator",
            "display_label": "Synthetic teacher",
        },
    }


def support_evaluator(
    participant_id: str = "spp_evaluator",
) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "participant_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def contextual_basis(
    work: ExactPortiaWorkRef,
    *,
    record_kind: str,
    record_id: str,
    contract_version: str,
    role: str = "contextual",
) -> dict[str, object]:
    return {
        "role": role,
        "locator": {
            "kind": "portia_record",
            "record_ref": {
                "work_ref": work.to_dict(),
                "record_ref": {
                    "record_kind": record_kind,
                    "record_id": record_id,
                    "contract_version": contract_version,
                },
            },
        },
    }


def module_basis(
    *,
    module_id: str = "quillan",
    record_module_id: str | None = None,
    contract_version: str = "1",
    role: str = "contextual",
) -> list[dict[str, object]]:
    return [
        {
            "role": role,
            "locator": {
                "kind": "module_record",
                "module_work_record_ref": {
                    "work_ref": {
                        "module_id": module_id,
                        "class_id": "class_a",
                        "work_id": "work_synthetic_1",
                    },
                    "record_ref": {
                        "module_id": record_module_id or module_id,
                        "record_kind": "reflection",
                        "record_id": "reflection_1",
                        "contract_version": contract_version,
                    },
                },
            },
        }
    ]


def outcome_record(
    *,
    work: ExactPortiaWorkRef | None = None,
    outcome_id: str = "out_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    evaluator: dict[str, object] | None = None,
    scope: dict[str, object] | None = None,
    timeframe: dict[str, object] | None = None,
    basis: list[dict[str, object]] | None = None,
    result: str = "improved",
    result_detail: str | None = None,
    source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = UPDATED,
    limitations: list[dict[str, object]] | None = None,
    supersedes: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    selected = work or event_ref()
    if target is None:
        target = event_target() if selected.work_kind == "event" else support_target()
    if evaluator is None:
        evaluator = (
            local_operator_evaluator()
            if selected.work_kind == "event"
            else support_evaluator()
        )
    if basis is None:
        if selected.work_kind == "event":
            basis = [
                contextual_basis(
                    selected,
                    record_kind="event_participant",
                    record_id="ep_alpha",
                    contract_version="3",
                )
            ]
        else:
            basis = [
                contextual_basis(
                    selected,
                    record_kind="support_process_participant",
                    record_id="spp_student",
                    contract_version="1",
                )
            ]

    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "outcome",
        "module_id": "portia",
        "class_id": selected.class_id,
        "work_kind": selected.work_kind,
        "work_id": selected.work_id,
        "outcome_id": outcome_id,
        "status": status,
        "target": target,
        "evaluator": evaluator,
        "scope": scope
        or {
            "kind": "observed_change",
            "question": "What changed within the explicitly bounded timeframe?",
        },
        "timeframe": timeframe
        or {
            "precision": "date_only",
            "date": "2026-09-05",
        },
        "basis": basis,
        "result": result,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if result_detail is not None:
        wire["result_detail"] = result_detail
    if limitations is not None:
        wire["limitations"] = limitations
    if supersedes is not None:
        wire["supersedes"] = supersedes
    return parse_portia_record("outcome", "1", wire)


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
            "spp_evaluator",
            contexts=[{"kind": "observer"}],
        ),
    )
    return repository


def test_create_load_list_and_current_event_outcome(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())

    assert created.record.logical_id == "out_alpha"
    reference = outcome_reference(event_ref(), "out_alpha")
    assert service.load_exact(reference).record.logical_id == "out_alpha"
    assert service.resolve_exact(reference).record.logical_id == "out_alpha"
    assert [item.record.logical_id for item in service.list_outcomes(event_ref())] == [
        "out_alpha"
    ]
    assert service.require_current_use(reference).record.logical_id == "out_alpha"
    assert service.resolve_current(reference).record.logical_id == "out_alpha"


def test_active_outcome_can_target_closed_event_history(tmp_path: Path) -> None:
    seed_event(tmp_path, status="closed")
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    assert created.record.status == "active"
    assert (
        service.require_current_use(
            outcome_reference(event_ref(), "out_alpha")
        ).record.logical_id
        == "out_alpha"
    )


def test_active_support_outcome_accepts_observer_evaluator(tmp_path: Path) -> None:
    seed_support(tmp_path)
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(work=support_ref()),
    )
    assert created.record.logical_id == "out_alpha"


def test_proposed_outcome_preserves_descriptive_evaluator_but_is_not_current(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    evaluator = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }
    service = OutcomeWorkflowService(tmp_path)
    service.create(
        event_ref(),
        outcome_record(status="proposed", evaluator=evaluator),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Outcome use requires active canonical status",
    ):
        service.require_current_use(
            outcome_reference(event_ref(), "out_alpha")
        )


def test_active_event_outcome_rejects_roster_student_evaluator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    evaluator = {
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
            "Outcome evaluator cannot use roster-student identity "
            "as operational authority"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(evaluator=evaluator),
        )


def test_active_event_outcome_rejects_descriptive_evaluator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    evaluator = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff",
        },
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Outcome evaluator requires an identified operational human",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(evaluator=evaluator),
        )


def test_active_support_outcome_requires_evaluator_context(tmp_path: Path) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_participant_record(
            "spp_non_evaluator",
            contexts=[{"kind": "family_or_support_person"}],
        ),
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            r"Outcome evaluator requires Support Process Participant context "
            r"in \{coordinator, observer, provider_or_collaborator\}"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            support_ref(),
            outcome_record(
                work=support_ref(),
                evaluator=support_evaluator("spp_non_evaluator"),
            ),
        )


def test_outcome_rejects_updated_before_created(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Outcome updated_at cannot precede Outcome created_at",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(
                created_at="2026-09-06T10:00:00-04:00",
                updated_at="2026-09-06T09:59:00-04:00",
            ),
        )


def test_outcome_rejects_reversed_timeframe_range(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Outcome timeframe ended_at cannot precede "
            "Outcome timeframe started_at"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(
                timeframe={
                    "precision": "range",
                    "started_at": "2026-09-05T12:00:00-04:00",
                    "ended_at": "2026-09-05T11:00:00-04:00",
                }
            ),
        )


def test_active_outcome_rejects_unknown_timeframe(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active Outcome timeframe may not be unknown",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(timeframe={"precision": "unknown"}),
        )


def test_outcome_student_perspective_basis_requires_account(tmp_path: Path) -> None:
    seed_event(tmp_path)
    basis = [
        contextual_basis(
            event_ref(),
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version="3",
            role="student_or_family_perspective",
        )
    ]
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Outcome basis role 'student_or_family_perspective' "
            "requires 'account'"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(basis=basis),
        )


def test_outcome_basis_cannot_reference_itself(tmp_path: Path) -> None:
    seed_event(tmp_path)
    basis = [
        contextual_basis(
            event_ref(),
            record_kind="outcome",
            record_id="out_alpha",
            contract_version="1",
        )
    ]
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Outcome basis cannot reference the current Outcome itself",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(basis=basis),
        )


def test_proposed_imported_outcome_with_unknown_timeframe_is_exactly_readable(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    imported = outcome_record(
        work=support_ref(),
        outcome_id="out_imported",
        status="proposed",
        timeframe={"precision": "unknown"},
        result="unable_to_determine",
        source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-1",
        },
        limitations=[{"kind": "source_unavailable"}],
    )
    repository.create_work_record(support_ref(), imported)

    service = OutcomeWorkflowService(tmp_path)
    reference = outcome_reference(support_ref(), "out_imported")
    assert service.load_exact(reference).record.logical_id == "out_imported"
    assert service.resolve_exact(reference).record.status == "proposed"


def test_active_imported_outcome_requires_accepted_review_history(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    imported = outcome_record(
        outcome_id="out_imported_active",
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
        OutcomeWorkflowService(tmp_path).require_current_use(
            outcome_reference(event_ref(), "out_imported_active")
        )


CORRECTION_UPDATED = "2026-09-06T09:30:00-04:00"


def outcome_successor(
    prior: PortiaRecord,
    *,
    outcome_id: str = "out_successor",
    reason: str,
    updated_at: str = CORRECTION_UPDATED,
    status: str = "active",
    basis: list[dict[str, object]] | None = None,
    result: str | None = None,
    timeframe: dict[str, object] | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    if not isinstance(prior_id, str):
        raise AssertionError("Outcome test predecessor must have a logical ID")
    wire["outcome_id"] = outcome_id
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if basis is not None:
        wire["basis"] = basis
    if result is not None:
        wire["result"] = result
    if timeframe is not None:
        wire["timeframe"] = timeframe
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
                    "record_kind": "outcome",
                    "record_id": prior_id,
                    "contract_version": "1",
                },
            },
            "reason": reason,
        }
    ]
    return parse_portia_record("outcome", "1", wire)


CONSOLIDATION_UPDATED = "2026-09-06T10:00:00-04:00"


def outcome_consolidation_successor(
    priors: tuple[PortiaRecord, ...],
    *,
    outcome_id: str = "out_canonical",
    status: str = "active",
    updated_at: str = CONSOLIDATION_UPDATED,
) -> PortiaRecord:
    assert priors
    wire = priors[0].to_dict()
    work = ExactPortiaWorkRef(
        class_id=str(wire["class_id"]),
        work_id=str(wire["work_id"]),
        work_kind=str(wire["work_kind"]),
        contract_version="2" if wire["work_kind"] == "event" else "1",
    )
    wire["outcome_id"] = outcome_id
    wire["status"] = status
    wire["supersedes"] = [
        {
            "work_record_ref": outcome_reference(
                work,
                str(prior.logical_id),
            ).to_dict(),
            "reason": "duplicate_consolidated",
        }
        for prior in priors
    ]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("outcome", "1", wire)


REOWNERSHIP_UPDATED = "2026-09-06T10:30:00-04:00"


def outcome_work_root_successor(
    prior: PortiaRecord,
    destination_work: ExactPortiaWorkRef,
    *,
    target: dict[str, object],
    evaluator: dict[str, object],
    updated_at: str = REOWNERSHIP_UPDATED,
    timeframe: dict[str, object] | None = None,
    outcome_id: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    if not isinstance(prior_id, str):
        raise AssertionError("Outcome test predecessor must have a logical ID")
    wire["class_id"] = destination_work.class_id
    wire["work_kind"] = destination_work.work_kind
    wire["work_id"] = destination_work.work_id
    wire["outcome_id"] = outcome_id or prior_id
    wire["status"] = "active"
    wire["target"] = target
    wire["evaluator"] = evaluator
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if timeframe is not None:
        wire["timeframe"] = timeframe
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
                    "record_kind": "outcome",
                    "record_id": prior_id,
                    "contract_version": "1",
                },
            },
            "reason": "work_root_corrected",
        }
    ]
    return parse_portia_record("outcome", "1", wire)


def support_ref_named(work_id: str) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def support_process_record_named(work_id: str) -> PortiaRecord:
    wire = support_process_record().to_dict()
    wire["work_id"] = work_id
    return parse_portia_record("support_process", "1", wire)


def support_goal_record_named(
    work_id: str,
    goal_id: str,
) -> PortiaRecord:
    return parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": work_id,
            "goal_id": goal_id,
            "status": "active",
            "target": {"kind": "support_process"},
            "description": "Synthetic bounded Outcome parity goal.",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_plan_record_named(
    work_id: str,
    support_id: str,
) -> PortiaRecord:
    return parse_portia_record(
        "support",
        "1",
        {
            "schema_version": "1",
            "record_type": "support",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": work_id,
            "support_id": support_id,
            "status": "active",
            "target": {
                "kind": "support_process_participant",
                "record_ref": {
                    "record_kind": "support_process_participant",
                    "record_id": "spp_student",
                    "contract_version": "1",
                },
            },
            "need_refs": [
                {
                    "record_kind": "support_need",
                    "record_id": "spn_synthetic",
                    "contract_version": "1",
                }
            ],
            "strategy": {
                "kind": "access",
                "procedure": "Synthetic Outcome parity support.",
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


def implementation_record_for_outcome() -> PortiaRecord:
    return parse_portia_record(
        "implementation",
        "1",
        {
            "schema_version": "1",
            "record_type": "implementation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "implementation_id": "imp_alpha",
            "status": "active",
            "plan_ref": {
                "record_kind": "support",
                "record_id": "spt_alpha",
                "contract_version": "1",
            },
            "actual_target": support_target(),
            "implementation_provider": {
                "kind": "no_human_provider",
                "reason": "environmental_condition",
            },
            "execution_state": "completed",
            "started_at": "2026-09-06T08:30:00-04:00",
            "ended_at": "2026-09-06T08:40:00-04:00",
            "summary": "Synthetic Outcome implementation context.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-06T08:45:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-09-06T08:45:00-04:00",
            "updated_by": AGENT,
        },
    )


def fidelity_record_for_outcome() -> PortiaRecord:
    return parse_portia_record(
        "fidelity",
        "1",
        {
            "schema_version": "1",
            "record_type": "fidelity",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "fidelity_id": "fid_alpha",
            "status": "active",
            "plan_ref": {
                "record_kind": "support",
                "record_id": "spt_alpha",
                "contract_version": "1",
            },
            "evaluator_ref": {
                "record_kind": "support_process_participant",
                "record_id": "spp_evaluator",
                "contract_version": "1",
            },
            "scope": {
                "kind": "one_implementation",
                "implementation_ref": {
                    "record_kind": "implementation",
                    "record_id": "imp_alpha",
                    "contract_version": "1",
                },
            },
            "result": "as_planned",
            "basis": {"kind": "direct_observation"},
            "evaluated_at": "2026-09-06T08:50:00-04:00",
            "summary": "Synthetic Outcome Fidelity context.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-06T08:55:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-09-06T08:55:00-04:00",
            "updated_by": AGENT,
        },
    )


def support_account_record_for_outcome() -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_alpha",
            "account_id": "acct_repair_perspective",
            "status": "active",
            "target": support_target(),
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic student/family perspective.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def event_reentry_record_for_outcome() -> PortiaRecord:
    return parse_portia_record(
        "reentry",
        "1",
        {
            "schema_version": "1",
            "record_type": "reentry",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "reentry_id": "ren_alpha",
            "status": "active",
            "target": event_target(),
            "coordinator": local_operator_evaluator(),
            "initiating_context": {
                "kind": "event",
                "work_ref": event_ref().to_dict(),
            },
            "planned_return": {
                "kind": "date_only",
                "date": "2026-09-07",
            },
            "planned_elements": [
                {
                    "kind": "orientation_or_check_in",
                    "description": "Synthetic Outcome parity check-in.",
                }
            ],
            "workflow_state": "planned",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_repair_record_for_outcome() -> PortiaRecord:
    return parse_portia_record(
        "repair",
        "1",
        {
            "schema_version": "1",
            "record_type": "repair",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_alpha",
            "repair_id": "rpr_alpha",
            "status": "active",
            "target": support_target(),
            "facilitator": support_evaluator(),
            "focus": "Synthetic bounded restorative focus.",
            "context_refs": [
                {
                    "kind": "work",
                    "work_ref": support_ref().to_dict(),
                }
            ],
            "participants": [
                {
                    "participant_key": "student",
                    "person": {
                        "kind": "support_process_participant",
                        "participant_ref": {
                            "record_kind": "support_process_participant",
                            "record_id": "spp_student",
                            "contract_version": "1",
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


LIFECYCLE_UPDATED = "2026-09-06T09:15:00-04:00"


def outcome_lifecycle_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str = LIFECYCLE_UPDATED,
    result: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if result is not None:
        wire["result"] = result
    return parse_portia_record("outcome", "1", wire)


def test_proposed_outcome_can_activate_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(status="proposed"),
    )
    reference = outcome_reference(event_ref(), "out_alpha")

    service.transition_lifecycle(
        reference,
        outcome_lifecycle_revision(created.record, status="active"),
        expected=created.fingerprint,
        transition_id="lct_out_activate",
        reason_code="reviewed",
        operation_id="op_out_activate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "active"
    assert service.require_current_use(reference).fingerprint == accepted.fingerprint

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_out_activate",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"
    assert transition.record.to_dict()["reason"] == {
        "category": "workflow",
        "code": "reviewed",
    }
    assert transition.record.to_dict()["target"] == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "outcome",
            "record_id": "out_alpha",
            "contract_version": "1",
        },
    }


def test_active_outcome_can_be_invalidated_and_stops_current_use(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    reference = outcome_reference(event_ref(), "out_alpha")

    service.transition_lifecycle(
        reference,
        outcome_lifecycle_revision(
            created.record,
            status="invalidated",
        ),
        expected=created.fingerprint,
        transition_id="lct_out_invalidate",
        reason_code="recording_error",
        operation_id="op_out_invalidate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "invalidated"
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active canonical status",
    ):
        service.require_current_use(reference)

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_out_invalidate",
    )
    assert transition.record.to_dict()["reason"] == {
        "category": "record_validity",
        "code": "recording_error",
    }


def test_outcome_lifecycle_cannot_rewrite_result(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record(result="improved"))
    reference = outcome_reference(event_ref(), "out_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite field result",
    ):
        service.transition_lifecycle(
            reference,
            outcome_lifecycle_revision(
                created.record,
                status="invalidated",
                result="worsened",
            ),
            expected=created.fingerprint,
            transition_id="lct_out_bad_result",
            reason_code="recording_error",
            operation_id="op_out_bad_result",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_outcome_supersession_is_reserved_for_correction(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    reference = outcome_reference(event_ref(), "out_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="correction workflow",
    ):
        service.transition_lifecycle(
            reference,
            outcome_lifecycle_revision(
                created.record,
                status="superseded",
            ),
            expected=created.fingerprint,
            transition_id="lct_out_bad_superseded",
            reason_code="recording_error",
            operation_id="op_out_bad_superseded",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_outcome_lifecycle_requires_current_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(status="proposed"),
    )
    reference = outcome_reference(event_ref(), "out_alpha")

    service.transition_lifecycle(
        reference,
        outcome_lifecycle_revision(created.record, status="active"),
        expected=created.fingerprint,
        transition_id="lct_out_activate_once",
        reason_code="reviewed",
        operation_id="op_out_activate_once",
    )

    with pytest.raises(PortiaConflictError, match="expected action state"):
        service.transition_lifecycle(
            reference,
            outcome_lifecycle_revision(
                created.record,
                status="invalidated",
                updated_at="2026-09-06T09:20:00-04:00",
            ),
            expected=created.fingerprint,
            transition_id="lct_out_stale",
            reason_code="recording_error",
            operation_id="op_out_stale",
        )


def test_outcome_lifecycle_effective_at_cannot_precede_creation(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(status="proposed"),
    )
    reference = outcome_reference(event_ref(), "out_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot precede record creation",
    ):
        service.transition_lifecycle(
            reference,
            outcome_lifecycle_revision(created.record, status="active"),
            expected=created.fingerprint,
            transition_id="lct_out_bad_effective",
            reason_code="reviewed",
            effective_at="2026-09-05T08:00:00-04:00",
            operation_id="op_out_bad_effective",
        )


def test_outcome_lifecycle_activation_resolves_module_basis_once(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority(result={"resolved": True})
    service = OutcomeWorkflowService(
        tmp_path,
        module_basis_authority=authority,
    )
    created = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_module_lifecycle",
            status="proposed",
            basis=module_basis(),
        ),
    )
    assert authority.references == []

    reference = outcome_reference(event_ref(), "out_module_lifecycle")
    service.transition_lifecycle(
        reference,
        outcome_lifecycle_revision(created.record, status="active"),
        expected=created.fingerprint,
        transition_id="lct_out_module_activate",
        reason_code="reviewed",
        operation_id="op_out_module_activate",
    )
    assert len(authority.references) == 1


def test_outcome_basis_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        event_participant_record(participant_id="ep_basis_corrected"),
    )
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(outcome_id="out_old"),
    )
    predecessor = outcome_reference(event_ref(), "out_old")
    root_before = repository.load_work(event_ref()).fingerprint
    corrected_basis = [
        contextual_basis(
            event_ref(),
            record_kind="event_participant",
            record_id="ep_basis_corrected",
            contract_version="3",
            role="current_period",
        )
    ]
    successor = outcome_successor(
        created.record,
        reason="basis_corrected",
        basis=corrected_basis,
        result="mixed",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_out_basis_correction",
        operation_id="op_out_basis_correction",
    )

    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        outcome_reference(event_ref(), "out_successor")
    )
    assert old_exact.record.status == "superseded"
    assert old_exact.record.logical_id == "out_old"
    assert current.record.status == "active"
    assert current.record.logical_id == "out_successor"
    assert current.record.field("basis") == tuple(corrected_basis)
    assert repository.load_work(event_ref()).fingerprint == root_before

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_out_basis_correction",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "basis_corrected",
    }

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(predecessor)


def test_outcome_correction_reason_must_match_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    predecessor = outcome_reference(event_ref(), "out_alpha")
    successor = outcome_successor(
        created.record,
        reason="basis_corrected",
        result="worsened",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected fact",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_out_bad_reason",
            operation_id="op_out_bad_reason",
        )

    assert service.resolve_exact(predecessor).fingerprint == created.fingerprint


def test_outcome_correction_requires_actual_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    predecessor = outcome_reference(event_ref(), "out_alpha")
    successor = outcome_successor(
        created.record,
        reason="basis_corrected",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires an actual Outcome fact change",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_out_noop",
            operation_id="op_out_noop",
        )


def test_outcome_correction_successor_must_be_active(tmp_path: Path) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        event_participant_record(participant_id="ep_basis_corrected"),
    )
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    predecessor = outcome_reference(event_ref(), "out_alpha")
    successor = outcome_successor(
        created.record,
        reason="basis_corrected",
        basis=[
            contextual_basis(
                event_ref(),
                record_kind="event_participant",
                record_id="ep_basis_corrected",
                contract_version="3",
            )
        ],
        status="invalidated",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="corrected Outcome successor must be active",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_out_inactive_successor",
            operation_id="op_out_inactive_successor",
        )


def test_outcome_correction_requires_current_expected_predecessor(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        event_participant_record(participant_id="ep_basis_corrected"),
    )
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    predecessor = outcome_reference(event_ref(), "out_alpha")
    corrected_basis = [
        contextual_basis(
            event_ref(),
            record_kind="event_participant",
            record_id="ep_basis_corrected",
            contract_version="3",
        )
    ]
    service.correct(
        predecessor,
        outcome_successor(
            created.record,
            reason="basis_corrected",
            basis=corrected_basis,
        ),
        expected=created.fingerprint,
        transition_id="lct_out_first_correction",
        operation_id="op_out_first_correction",
    )

    with pytest.raises(PortiaConflictError, match="expected predecessor action state"):
        service.correct(
            predecessor,
            outcome_successor(
                created.record,
                outcome_id="out_second_successor",
                reason="result_corrected",
                result="worsened",
                updated_at="2026-09-06T09:40:00-04:00",
            ),
            expected=created.fingerprint,
            transition_id="lct_out_stale_correction",
            operation_id="op_out_stale_correction",
        )


def test_later_timeframe_is_new_outcome_not_automatic_correction(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_period_1",
            timeframe={"precision": "date_only", "date": "2026-09-05"},
            result="improved",
        ),
    )
    second = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_period_2",
            timeframe={"precision": "date_only", "date": "2026-09-06"},
            result="no_clear_change",
            updated_at="2026-09-06T09:35:00-04:00",
        ),
    )

    assert first.record.field("supersedes") is None
    assert second.record.field("supersedes") is None
    assert service.require_current_use(
        outcome_reference(event_ref(), "out_period_1")
    ).record.status == "active"
    assert service.require_current_use(
        outcome_reference(event_ref(), "out_period_2")
    ).record.status == "active"


def test_outcome_correction_rejects_wrong_selected_predecessor(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        event_participant_record(participant_id="ep_basis_corrected"),
    )
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(outcome_id="out_alpha"),
    )
    service.create(
        event_ref(),
        outcome_record(outcome_id="out_other"),
    )
    successor = outcome_successor(
        first.record,
        reason="basis_corrected",
        basis=[
            contextual_basis(
                event_ref(),
                record_kind="event_participant",
                record_id="ep_basis_corrected",
                contract_version="3",
            )
        ],
    )

    with pytest.raises(
        WorkflowOwnershipError,
        match="must supersede the exact selected predecessor",
    ):
        service.correct(
            outcome_reference(event_ref(), "out_other"),
            successor,
            expected=first.fingerprint,
            transition_id="lct_out_wrong_predecessor",
            operation_id="op_out_wrong_predecessor",
        )


def test_outcome_duplicate_consolidation_supersedes_all_exact_predecessors(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_a"),
    )
    second = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_b"),
    )
    successor = outcome_consolidation_successor(
        (first.record, second.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "out_dup_a": first.fingerprint,
            "out_dup_b": second.fingerprint,
        },
        transition_ids={
            "out_dup_a": "lct_out_dup_a_consolidate",
            "out_dup_b": "lct_out_dup_b_consolidate",
        },
        operation_id="op_out_duplicate_consolidation",
    )

    first_ref = outcome_reference(event_ref(), "out_dup_a")
    second_ref = outcome_reference(event_ref(), "out_dup_b")
    assert service.resolve_exact(first_ref).record.status == "superseded"
    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        outcome_reference(event_ref(), "out_canonical")
    ).record.status == "active"

    for transition_id in (
        "lct_out_dup_a_consolidate",
        "lct_out_dup_b_consolidate",
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

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(first_ref)
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(second_ref)


def test_outcome_duplicate_consolidation_accepts_invalidated_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_a"),
    )
    second = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_b"),
    )
    second_ref = outcome_reference(event_ref(), "out_dup_b")
    service.transition_lifecycle(
        second_ref,
        outcome_lifecycle_revision(
            second.record,
            status="invalidated",
            updated_at="2026-09-06T09:20:00-04:00",
        ),
        expected=second.fingerprint,
        transition_id="lct_out_dup_b_invalidate",
        reason_code="recording_error",
        operation_id="op_out_dup_b_invalidate",
    )
    invalidated = service.resolve_exact(second_ref)
    successor = outcome_consolidation_successor(
        (first.record, invalidated.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "out_dup_a": first.fingerprint,
            "out_dup_b": invalidated.fingerprint,
        },
        transition_ids={
            "out_dup_a": "lct_out_dup_a_consolidate",
            "out_dup_b": "lct_out_dup_b_consolidate",
        },
        operation_id="op_out_duplicate_with_invalidated",
    )

    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        outcome_reference(event_ref(), "out_canonical")
    ).record.status == "active"


def test_outcome_duplicate_consolidation_rejects_one_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    successor = outcome_consolidation_successor((created.record,))

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two outcome predecessors",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"out_alpha": created.fingerprint},
            transition_ids={"out_alpha": "lct_out_only_duplicate"},
            operation_id="op_out_bad_single_duplicate",
        )


def test_outcome_duplicate_consolidation_requires_complete_expected_map(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_a"),
    )
    second = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_b"),
    )
    successor = outcome_consolidation_successor(
        (first.record, second.record),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="one expected fingerprint for every predecessor",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"out_dup_a": first.fingerprint},
            transition_ids={
                "out_dup_a": "lct_out_dup_a",
                "out_dup_b": "lct_out_dup_b",
            },
            operation_id="op_out_incomplete_duplicate_expected",
        )


def test_outcome_duplicate_consolidation_successor_must_be_active(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_a"),
    )
    second = service.create(
        event_ref(),
        outcome_record(outcome_id="out_dup_b"),
    )
    successor = outcome_consolidation_successor(
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
                "out_dup_a": first.fingerprint,
                "out_dup_b": second.fingerprint,
            },
            transition_ids={
                "out_dup_a": "lct_out_dup_a",
                "out_dup_b": "lct_out_dup_b",
            },
            operation_id="op_out_inactive_duplicate_successor",
        )


def test_outcome_work_root_correction_event_to_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    seed_support(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(outcome_id="out_reowned"),
    )
    source_reference = outcome_reference(event_ref(), "out_reowned")
    source_root_before = repository.load_work(event_ref()).fingerprint
    destination_root_before = repository.load_work(support_ref()).fingerprint

    successor = outcome_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        evaluator=support_evaluator(),
    )
    service.correct_work_root(
        source_reference,
        support_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_out_reown_event_support",
        operation_id="op_out_reown_event_support",
    )

    source = service.resolve_exact(source_reference)
    destination_reference = outcome_reference(
        support_ref(),
        "out_reowned",
    )
    destination = service.require_current_use(destination_reference)

    assert source.record.status == "superseded"
    assert destination.record.status == "active"
    assert destination.record.logical_id == "out_reowned"
    assert destination.record.field("scope") == created.record.field("scope")
    assert destination.record.field("timeframe") == created.record.field("timeframe")
    assert destination.record.field("basis") == created.record.field("basis")
    assert destination.record.field("result") == created.record.field("result")
    assert repository.load_work(event_ref()).fingerprint == source_root_before
    assert repository.load_work(support_ref()).fingerprint == destination_root_before

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_out_reown_event_support",
    )
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "work_root_corrected",
    }


def test_outcome_work_root_correction_support_process_to_event(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_reowned",
        ),
    )
    source_reference = outcome_reference(support_ref(), "out_reowned")

    successor = outcome_work_root_successor(
        created.record,
        event_ref(),
        target=event_target(),
        evaluator=local_operator_evaluator(),
    )
    service.correct_work_root(
        source_reference,
        event_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_out_reown_support_event",
        operation_id="op_out_reown_support_event",
    )

    assert service.resolve_exact(source_reference).record.status == "superseded"
    current = service.require_current_use(
        outcome_reference(event_ref(), "out_reowned")
    )
    assert current.record.status == "active"
    assert current.record.field("scope") == created.record.field("scope")
    assert current.record.field("basis") == created.record.field("basis")


def test_outcome_work_root_correction_cannot_rewrite_timeframe(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    source_reference = outcome_reference(event_ref(), "out_alpha")

    successor = outcome_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        evaluator=support_evaluator(),
        timeframe={
            "precision": "date_only",
            "date": "2026-09-06",
        },
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite fact timeframe",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_out_bad_reown_timeframe",
            operation_id="op_out_bad_reown_timeframe",
        )

    assert service.resolve_exact(source_reference).fingerprint == created.fingerprint


def test_outcome_work_root_correction_must_preserve_outcome_id(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    source_reference = outcome_reference(event_ref(), "out_alpha")

    successor = outcome_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        evaluator=support_evaluator(),
        outcome_id="out_changed",
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction must preserve outcome identity",
    ):
        service.correct_work_root(
            source_reference,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_out_bad_reown_id",
            operation_id="op_out_bad_reown_id",
        )


def test_outcome_work_root_correction_rejects_stale_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(event_ref(), outcome_record())
    source_reference = outcome_reference(event_ref(), "out_alpha")

    service.transition_lifecycle(
        source_reference,
        outcome_lifecycle_revision(
            created.record,
            status="invalidated",
            updated_at="2026-09-06T10:00:00-04:00",
        ),
        expected=created.fingerprint,
        transition_id="lct_out_before_reown",
        reason_code="recording_error",
        operation_id="op_out_before_reown",
    )

    successor = outcome_work_root_successor(
        created.record,
        support_ref(),
        target=support_target(),
        evaluator=support_evaluator(),
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
            transition_id="lct_out_stale_reown",
            operation_id="op_out_stale_reown",
        )


def test_outcome_accepts_recurrence_observed_with_bounded_coverage(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    created = OutcomeWorkflowService(tmp_path).create(
        event_ref(),
        outcome_record(
            outcome_id="out_recurrence_seen",
            scope={
                "kind": "recurrence_review",
                "question": "Did the defined pattern recur?",
                "coverage": {
                    "coverage_kind": "event_record_review",
                    "coverage_description": "Synthetic bounded Event review.",
                },
            },
            result="recurrence_observed",
        ),
    )
    assert created.record.field("result") == "recurrence_observed"


def test_outcome_accepts_no_recurrence_only_with_defined_coverage(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    created = OutcomeWorkflowService(tmp_path).create(
        event_ref(),
        outcome_record(
            outcome_id="out_no_recurrence",
            scope={
                "kind": "recurrence_review",
                "question": "Did the defined pattern recur?",
                "coverage": {
                    "coverage_kind": "combined",
                    "coverage_description": "Synthetic bounded observed opportunities.",
                },
            },
            timeframe={
                "precision": "range",
                "started_at": "2026-09-05T08:00:00-04:00",
                "ended_at": "2026-09-06T08:00:00-04:00",
            },
            result="no_recurrence_observed_within_defined_coverage",
        ),
    )
    assert created.record.field("result") == (
        "no_recurrence_observed_within_defined_coverage"
    )


def test_outcome_accepts_support_goal_status_scope(tmp_path: Path) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_goal_record_named("sup_alpha", "spg_alpha"),
    )
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_goal_met",
            scope={
                "kind": "goal_status",
                "goal_ref": {
                    "record_kind": "support_goal",
                    "record_id": "spg_alpha",
                    "contract_version": "1",
                },
            },
            result="met",
        ),
    )
    assert created.record.field("result") == "met"


def test_outcome_accepts_support_response_with_implementation_and_fidelity_context(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_plan_record_named("sup_alpha", "spt_alpha"),
    )
    repository.create_work_record(
        support_ref(),
        implementation_record_for_outcome(),
    )
    repository.create_work_record(
        support_ref(),
        fidelity_record_for_outcome(),
    )
    basis = [
        contextual_basis(
            support_ref(),
            record_kind="implementation",
            record_id="imp_alpha",
            contract_version="1",
            role="implementation_context",
        ),
        contextual_basis(
            support_ref(),
            record_kind="fidelity",
            record_id="fid_alpha",
            contract_version="1",
            role="fidelity_context",
        ),
    ]
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_response_progress",
            scope={
                "kind": "support_response_review",
                "plan_refs": [
                    {
                        "record_kind": "support",
                        "record_id": "spt_alpha",
                        "contract_version": "1",
                    }
                ],
                "question": "Observed response during the bounded support period.",
            },
            basis=basis,
            result="progress_observed",
        ),
    )
    assert created.record.field("result") == "progress_observed"


def test_outcome_accepts_support_response_unable_with_limitation(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_plan_record_named("sup_alpha", "spt_alpha"),
    )
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_response_unable",
            scope={
                "kind": "support_response_review",
                "plan_refs": [
                    {
                        "record_kind": "support",
                        "record_id": "spt_alpha",
                        "contract_version": "1",
                    }
                ],
                "question": "Can a bounded response conclusion be made?",
            },
            result="unable_to_determine",
            limitations=[{"kind": "insufficient_evidence"}],
        ),
    )
    assert created.record.field("result") == "unable_to_determine"


def test_outcome_accepts_adverse_review_no_change_with_coverage(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_adverse_review",
            scope={
                "kind": "unintended_or_adverse_effect_review",
                "question": "Were unintended or adverse changes observed?",
                "coverage": {
                    "coverage_kind": "direct_observation",
                    "coverage_description": "Synthetic bounded observed coverage.",
                },
            },
            result="no_change_observed_within_defined_coverage",
        ),
    )
    assert created.record.field("result") == (
        "no_change_observed_within_defined_coverage"
    )


def test_outcome_accepts_other_scope_conclusion_with_detail(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_other_conclusion",
            scope={
                "kind": "other",
                "detail": "Synthetic bounded human-defined Outcome question.",
            },
            result="conclusion",
            result_detail="Synthetic bounded evaluator conclusion.",
        ),
    )
    assert created.record.field("result") == "conclusion"


def test_outcome_accepts_event_reentry_status_without_clearance_inference(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        event_reentry_record_for_outcome(),
    )
    created = OutcomeWorkflowService(tmp_path).create(
        event_ref(),
        outcome_record(
            outcome_id="out_reentry_status",
            scope={
                "kind": "reentry_status",
                "reentry_ref": {
                    "record_kind": "reentry",
                    "record_id": "ren_alpha",
                    "contract_version": "1",
                },
            },
            result="no_clear_change",
        ),
    )
    assert created.record.field("result") == "no_clear_change"


def test_outcome_accepts_support_repair_status_with_account_perspective(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    repository.create_work_record(
        support_ref(),
        support_repair_record_for_outcome(),
    )
    repository.create_work_record(
        support_ref(),
        support_account_record_for_outcome(),
    )
    basis = [
        contextual_basis(
            support_ref(),
            record_kind="account",
            record_id="acct_repair_perspective",
            contract_version="2",
            role="student_or_family_perspective",
        )
    ]
    created = OutcomeWorkflowService(tmp_path).create(
        support_ref(),
        outcome_record(
            work=support_ref(),
            outcome_id="out_repair_status",
            scope={
                "kind": "repair_status",
                "repair_ref": {
                    "record_kind": "repair",
                    "record_id": "rpr_alpha",
                    "contract_version": "1",
                },
            },
            basis=basis,
            result="mixed",
        ),
    )
    assert created.record.field("result") == "mixed"


def test_active_event_outcome_rejects_unidentified_evaluator(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    evaluator = {
        "kind": "represented_human",
        "person": {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Outcome evaluator requires an identified operational human",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(evaluator=evaluator),
        )


def test_outcome_implementation_context_basis_requires_implementation(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    basis = [
        contextual_basis(
            event_ref(),
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version="3",
            role="implementation_context",
        )
    ]
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Outcome basis role 'implementation_context' requires 'implementation'",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(basis=basis),
        )


def test_outcome_fidelity_context_basis_requires_fidelity(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    basis = [
        contextual_basis(
            event_ref(),
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version="3",
            role="fidelity_context",
        )
    ]
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Outcome basis role 'fidelity_context' requires 'fidelity'",
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(basis=basis),
        )


def test_outcome_goal_scope_rejects_other_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    other = support_ref_named("sup_beta")
    repository.create_work(
        other,
        support_process_record_named("sup_beta"),
    )
    repository.create_work_record(
        other,
        support_goal_record_named("sup_beta", "spg_other"),
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Outcome scope goal_ref does not resolve in the owning support_process",
    ):
        OutcomeWorkflowService(tmp_path).create(
            support_ref(),
            outcome_record(
                work=support_ref(),
                scope={
                    "kind": "goal_status",
                    "goal_ref": {
                        "record_kind": "support_goal",
                        "record_id": "spg_other",
                        "contract_version": "1",
                    },
                },
                result="met",
            ),
        )


def test_outcome_plan_scope_rejects_other_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    other = support_ref_named("sup_beta")
    repository.create_work(
        other,
        support_process_record_named("sup_beta"),
    )
    repository.create_work_record(
        other,
        support_plan_record_named("sup_beta", "spt_other"),
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            r"Outcome scope plan_refs\[0\] does not resolve "
            r"in the owning support_process"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            support_ref(),
            outcome_record(
                work=support_ref(),
                scope={
                    "kind": "support_response_review",
                    "plan_refs": [
                        {
                            "record_kind": "support",
                            "record_id": "spt_other",
                            "contract_version": "1",
                        }
                    ],
                    "question": "Synthetic cross-process plan review.",
                },
                result="progress_observed",
            ),
        )


def test_outcome_rejects_self_supersession(tmp_path: Path) -> None:
    repository = seed_event(tmp_path)
    wire = outcome_record(
        outcome_id="out_self",
        result="mixed",
    ).to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": outcome_reference(
                event_ref(),
                "out_self",
            ).to_dict(),
            "reason": "result_corrected",
        }
    ]
    bad = parse_portia_record("outcome", "1", wire)
    repository.create_work_record(event_ref(), bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="outcome cannot supersede itself",
    ):
        OutcomeWorkflowService(tmp_path).require_current_use(
            outcome_reference(event_ref(), "out_self")
        )


def test_outcome_rejects_ordinary_correction_cross_work(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    repository = seed_support(tmp_path)
    wire = outcome_record(
        work=support_ref(),
        outcome_id="out_cross_work",
    ).to_dict()
    wire["result"] = "mixed"
    wire["supersedes"] = [
        {
            "work_record_ref": outcome_reference(
                event_ref(),
                "out_source",
            ).to_dict(),
            "reason": "result_corrected",
        }
    ]
    bad = parse_portia_record("outcome", "1", wire)
    repository.create_work_record(support_ref(), bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary outcome correction cannot cross work roots",
    ):
        OutcomeWorkflowService(tmp_path).require_current_use(
            outcome_reference(support_ref(), "out_cross_work")
        )


def test_active_outcome_module_basis_requires_explicit_public_authority(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Outcome module_record basis requires an explicit public "
            "resolution authority"
        ),
    ):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(basis=module_basis()),
        )


def test_active_outcome_module_basis_resolves_exact_reference_through_authority(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority(result={"resolved": True})
    service = OutcomeWorkflowService(
        tmp_path,
        module_basis_authority=authority,
    )
    created = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_module_context",
            basis=module_basis(),
            result="no_clear_change",
        ),
    )

    assert created.record.logical_id == "out_module_context"
    assert len(authority.references) == 1
    assert authority.references[0].to_dict() == {
        "work_ref": {
            "module_id": "quillan",
            "class_id": "class_a",
            "work_id": "work_synthetic_1",
        },
        "record_ref": {
            "module_id": "quillan",
            "record_kind": "reflection",
            "record_id": "reflection_1",
            "contract_version": "1",
        },
    }
    assert service.require_current_use(
        outcome_reference(event_ref(), "out_module_context")
    ).record.logical_id == "out_module_context"
    assert len(authority.references) == 2


def test_active_outcome_module_basis_fails_closed_when_authority_does_not_resolve(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority(result=None)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Outcome module_record basis did not resolve through the "
            "supplied authority"
        ),
    ):
        OutcomeWorkflowService(
            tmp_path,
            module_basis_authority=authority,
        ).create(
            event_ref(),
            outcome_record(basis=module_basis()),
        )


def test_proposed_outcome_preserves_module_basis_without_authority(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = OutcomeWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_module_proposed",
            status="proposed",
            basis=module_basis(),
        ),
    )
    assert created.record.status == "proposed"
    assert service.load_exact(
        outcome_reference(event_ref(), "out_module_proposed")
    ).record.logical_id == "out_module_proposed"


def test_proposed_outcome_module_basis_does_not_invoke_supplied_authority(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority(result={"resolved": True})
    service = OutcomeWorkflowService(
        tmp_path,
        module_basis_authority=authority,
    )
    created = service.create(
        event_ref(),
        outcome_record(
            outcome_id="out_module_proposed_authority",
            status="proposed",
            basis=module_basis(),
        ),
    )

    assert created.record.status == "proposed"
    assert authority.references == []


def test_outcome_module_basis_requires_matching_module_identity(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority()
    with pytest.raises(
        WorkflowOwnershipError,
        match="module work and record identities disagree",
    ):
        OutcomeWorkflowService(
            tmp_path,
            module_basis_authority=authority,
        ).create(
            event_ref(),
            outcome_record(
                basis=module_basis(
                    module_id="quillan",
                    record_module_id="scoreform",
                )
            ),
        )


def test_outcome_module_basis_cannot_route_portia_through_sibling_authority(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    authority = RecordingModuleBasisAuthority()
    with pytest.raises(
        WorkflowOwnershipError,
        match="Portia records must use the portia_record basis branch",
    ):
        OutcomeWorkflowService(
            tmp_path,
            module_basis_authority=authority,
        ).create(
            event_ref(),
            outcome_record(basis=module_basis(module_id="portia")),
        )


def test_outcome_rejects_wrong_work_owner(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(WorkflowOwnershipError, match="explicitly selected"):
        OutcomeWorkflowService(tmp_path).create(
            event_ref(),
            outcome_record(work=support_ref()),
        )
