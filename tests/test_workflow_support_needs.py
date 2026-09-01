"""Focused Slice 5 tests for Support Need application authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    support_need_reference,
    support_process_participant_reference,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-08-31T10:05:00-04:00"
ROOT_UPDATED = "2026-08-31T10:10:00-04:00"
NEED_CREATED = "2026-08-31T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice5_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record(
    *, status: str = "proposed", updated_at: str = TIMESTAMP
) -> PortiaRecord:
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
            "workflow_state": "planning",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_record(
    participant_id: str = "spp_alpha",
    *,
    status: str = "proposed",
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
    updated_at: str = TIMESTAMP,
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
            "status": status,
            "person": person
            or {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic learner {participant_id}",
            },
            "contexts": contexts or [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def need_record(
    *,
    need_id: str = "spn_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    need_kind: str = "access",
    source: dict[str, object] | None = None,
    updated_at: str = NEED_CREATED,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support_need",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "need_id": need_id,
        "status": status,
        "target": target or {"kind": "support_process"},
        "need_kind": need_kind,
        "description": "Synthetic bounded support-planning need.",
        "creation_source": source or {"type": "digital_entry"},
        "created_at": NEED_CREATED,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if need_kind == "other":
        wire["kind_detail"] = "Synthetic bounded other-kind detail."
    return parse_portia_record("support_need", "1", wire)


def participant_target(participant_id: str) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def participant_set_target(*participant_ids: str) -> dict[str, object]:
    return {
        "kind": "support_process_participants",
        "targets": [participant_target(value) for value in participant_ids],
    }


def _active_process(tmp_path: Path) -> tuple[SupportProcessWorkflowService, object]:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participant_service.create(work_ref(), participant_record())
    active_participant = participant_record(
        status="active",
        updated_at=PARTICIPANT_UPDATED,
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_alpha"),
        active_participant,
        expected=participant.fingerprint,
        transition_id="lct_spp_slice5_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice5_active",
    )
    active_root = root_record(status="active", updated_at=ROOT_UPDATED)
    root_service.transition_lifecycle(
        work_ref(),
        active_root,
        expected=root.fingerprint,
        transition_id="lct_sup_slice5_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice5_active",
    )
    return root_service, participant_service


def test_reference_is_exact_support_process_local_need() -> None:
    reference = support_need_reference(work_ref(), "spn_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "support_need"
    assert reference.record_ref.record_id == "spn_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_event_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        support_need_reference(wrong, "spn_alpha")


def test_proposed_need_can_be_authored_while_process_is_planning(
    tmp_path: Path,
) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record(status="proposed"))
    assert created.record.status == "proposed"
    loaded = service.load_exact(support_need_reference(work_ref(), "spn_alpha"))
    assert loaded.record == created.record


def test_fresh_need_cannot_begin_invalidated(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="begin proposed or active"):
        service.create(work_ref(), need_record(status="invalidated"))


def test_updated_at_cannot_precede_created_at(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        service.create(
            work_ref(),
            need_record(status="proposed", updated_at="2026-08-31T10:14:00-04:00"),
        )


def test_import_candidate_is_not_materialized_by_digital_authoring(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    imported = need_record(
        status="proposed",
        source={"type": "import", "source_label": "Synthetic historical import"},
    )
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        service.create(work_ref(), imported)


def test_fresh_need_cannot_establish_supersession_history(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    wire = need_record(status="proposed").to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": support_need_reference(
                work_ref(), "spn_predecessor"
            ).to_dict(),
            "reason": "description_corrected",
        }
    ]
    candidate = parse_portia_record("support_need", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="supersession history"):
        SupportNeedWorkflowService(tmp_path).create(work_ref(), candidate)


def test_active_whole_process_need_requires_current_process(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.create(work_ref(), need_record())


def test_active_whole_process_need_is_current_qualified(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    current = service.require_current_use(
        support_need_reference(work_ref(), "spn_alpha")
    )
    assert current.fingerprint == created.fingerprint
    assert current.record.field("target") == {"kind": "support_process"}


def test_active_participant_target_resolves_exact_current_participant(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        need_record(target=participant_target("spp_alpha")),
    )
    assert created.record.field("target") == participant_target("spp_alpha")
    assert service.require_current_use(
        support_need_reference(work_ref(), "spn_alpha")
    ).record == created.record


def test_unresolved_participant_target_is_rejected(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="does not resolve"):
        service.create(
            work_ref(),
            need_record(target=participant_target("spp_missing")),
        )


def test_active_need_rejects_noncurrent_participant_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_planned",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="not active for current use"):
        service.create(
            work_ref(),
            need_record(target=participant_target("spp_planned")),
        )


def test_proposed_need_may_pin_existing_proposed_participant(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        need_record(status="proposed", target=participant_target("spp_alpha")),
    )
    assert created.record.status == "proposed"


def test_participant_set_target_accepts_distinct_logical_people(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(work_ref(), participant_record("spp_alpha"))
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_beta",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        need_record(
            status="proposed",
            target=participant_set_target("spp_alpha", "spp_beta"),
        ),
    )
    assert created.record.logical_id == "spn_alpha"


def test_participant_set_rejects_two_records_for_same_logical_person(
    tmp_path: Path,
) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    same_person = {"kind": "local_operator", "display_label": "Synthetic operator"}
    first = participant_record("spp_alpha", person=same_person)
    second = participant_record(
        "spp_alias",
        person=same_person,
        contexts=[{"kind": "provider_or_collaborator"}],
    )
    root_service.repository.create_work_record(work_ref(), first)
    root_service.repository.create_work_record(work_ref(), second)
    service = SupportNeedWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="repeats a logical"):
        service.create(
            work_ref(),
            need_record(
                status="proposed",
                target=participant_set_target("spp_alpha", "spp_alias"),
            ),
        )


def test_multiple_distinct_needs_may_address_same_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    target = participant_target("spp_alpha")
    service.create(work_ref(), need_record(need_id="spn_access", target=target))
    service.create(
        work_ref(),
        need_record(
            need_id="spn_routine",
            target=target,
            need_kind="organizational_or_routine",
        ),
    )
    assert {item.record.logical_id for item in service.list(work_ref())} == {
        "spn_access",
        "spn_routine",
    }


def test_other_kind_remains_bounded_schema_semantics(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(
        work_ref(), need_record(status="proposed", need_kind="other")
    )
    assert created.record.field("kind_detail") == "Synthetic bounded other-kind detail."


def test_current_use_requires_active_need(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    service.create(work_ref(), need_record(status="proposed"))
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(support_need_reference(work_ref(), "spn_alpha"))


def test_current_use_rejects_lifecycle_head_disagreement(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    transition = parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "transition_id": "lct_spn_mismatch",
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "support_need",
                    "record_id": "spn_alpha",
                    "contract_version": "1",
                },
            },
            "previous_transition": None,
            "from_status": "proposed",
            "to_status": "invalidated",
            "reason": {"category": "record_validity", "code": "recording_error"},
            "effective_at": NEED_CREATED,
            "creation_source": {"type": "digital_entry"},
            "created_at": NEED_CREATED,
            "created_by": AGENT,
        },
    )
    service.repository.create_work_record(work_ref(), transition)
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_current_use(
            support_need_reference(work_ref(), created.record.logical_id or "missing")
        )


def test_exact_read_does_not_follow_lifecycle_or_successor_state(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record(status="proposed"))
    exact = service.resolve_exact(support_need_reference(work_ref(), "spn_alpha"))
    assert exact.fingerprint == created.fingerprint
    assert exact.record.status == "proposed"


# Slice 9b — Support Need lifecycle mutation and correction.
NEED_UPDATE_1 = "2026-08-31T10:20:00-04:00"
NEED_UPDATE_2 = "2026-08-31T10:25:00-04:00"


def _need_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str = NEED_UPDATE_1,
    description: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    if description is not None:
        wire["description"] = description
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("support_need", "1", wire)


def _need_successor(
    prior: PortiaRecord,
    *,
    need_id: str = "spn_beta",
    reason: str,
    detail: str | None = None,
    description: str | None = None,
    target: dict[str, object] | None = None,
    need_kind: str | None = None,
    updated_at: str = NEED_UPDATE_1,
) -> PortiaRecord:
    predecessor_id = prior.logical_id
    assert predecessor_id is not None
    wire = prior.to_dict()
    wire["need_id"] = need_id
    if description is not None:
        wire["description"] = description
    if target is not None:
        wire["target"] = target
    if need_kind is not None:
        wire["need_kind"] = need_kind
        if need_kind == "other":
            wire["kind_detail"] = "Corrected bounded other-kind detail."
        else:
            wire.pop("kind_detail", None)
    entry: dict[str, object] = {
        "work_record_ref": support_need_reference(
            work_ref(), predecessor_id
        ).to_dict(),
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    wire["supersedes"] = [entry]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("support_need", "1", wire)


def test_need_lifecycle_activation_persists_transition_and_current_use(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record(status="proposed"))
    candidate = _need_revision(created.record, status="active")
    service.transition_lifecycle(
        support_need_reference(work_ref(), "spn_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spn_slice9b_active",
        reason_code="planning_confirmed",
        operation_id="op_spn_slice9b_active",
    )
    accepted = service.require_current_use(
        support_need_reference(work_ref(), "spn_alpha")
    )
    assert accepted.record.status == "active"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spn_slice9b_active",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_need_lifecycle_activation_requires_current_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_pending",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        need_record(
            status="proposed",
            target=participant_target("spp_pending"),
        ),
    )
    candidate = _need_revision(created.record, status="active")
    with pytest.raises(WorkflowPrerequisiteError, match="not active for current use"):
        service.transition_lifecycle(
            support_need_reference(work_ref(), "spn_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_pending_target",
            reason_code="planning_confirmed",
            operation_id="op_spn_slice9b_pending_target",
        )


def test_need_lifecycle_cannot_rewrite_description(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record(status="proposed"))
    candidate = _need_revision(
        created.record,
        status="active",
        description="This substantive rewrite is not a lifecycle change.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="description"):
        service.transition_lifecycle(
            support_need_reference(work_ref(), "spn_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_rewrite",
            reason_code="planning_confirmed",
            operation_id="op_spn_slice9b_rewrite",
        )


def test_need_lifecycle_invalidation_removes_current_use(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    candidate = _need_revision(created.record, status="invalidated")
    service.transition_lifecycle(
        support_need_reference(work_ref(), "spn_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spn_slice9b_invalidated",
        reason_code="recording_error",
        operation_id="op_spn_slice9b_invalidated",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(
            support_need_reference(work_ref(), "spn_alpha")
        )


def test_need_lifecycle_supersession_is_reserved_for_correction(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    candidate = _need_revision(created.record, status="superseded")
    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        service.transition_lifecycle(
            support_need_reference(work_ref(), "spn_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_superseded",
            reason_code="recording_error",
            operation_id="op_spn_slice9b_superseded",
        )


def test_need_correction_supersedes_exact_predecessor_and_qualifies_successor(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        reason="description_corrected",
        description="Corrected bounded support-planning need.",
    )
    service.correct(
        support_need_reference(work_ref(), "spn_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spn_slice9b_corrected",
        operation_id="op_spn_slice9b_corrected",
    )
    predecessor = service.load_exact(
        support_need_reference(work_ref(), "spn_alpha")
    )
    accepted = service.require_current_use(
        support_need_reference(work_ref(), "spn_beta")
    )
    assert predecessor.record.status == "superseded"
    assert accepted.record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(
            support_need_reference(work_ref(), "spn_alpha")
        )


def test_need_correction_records_reason_on_lifecycle_transition(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        reason="kind_corrected",
        need_kind="skill_or_strategy",
    )
    service.correct(
        support_need_reference(work_ref(), "spn_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spn_slice9b_reason",
        operation_id="op_spn_slice9b_reason",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spn_slice9b_reason",
    )
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "kind_corrected",
    }


def test_need_correction_can_replace_proposed_planning_record(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record(status="proposed"))
    successor = _need_successor(
        created.record,
        reason="description_corrected",
        description="Corrected proposed Need description.",
    )
    service.correct(
        support_need_reference(work_ref(), "spn_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spn_slice9b_proposed",
        operation_id="op_spn_slice9b_proposed",
    )
    assert service.load_exact(
        support_need_reference(work_ref(), "spn_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        support_need_reference(work_ref(), "spn_beta")
    ).record.status == "proposed"


def test_need_correction_requires_new_identity(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        need_id="spn_alpha",
        reason="description_corrected",
        description="Corrected Need under an invalid reused identity.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="new canonical identity"):
        service.correct(
            support_need_reference(work_ref(), "spn_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_same_id",
            operation_id="op_spn_slice9b_same_id",
        )


def test_need_correction_reason_must_match_corrected_fact(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        reason="target_corrected",
        description="Only the description actually changed.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            support_need_reference(work_ref(), "spn_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_reason_mismatch",
            operation_id="op_spn_slice9b_reason_mismatch",
        )


def test_active_need_correction_revalidates_current_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_pending",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        reason="target_corrected",
        target=participant_target("spp_pending"),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="not active for current use"):
        service.correct(
            support_need_reference(work_ref(), "spn_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_stale_target",
            operation_id="op_spn_slice9b_stale_target",
        )


def test_need_reserved_topology_reason_fails_closed(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportNeedWorkflowService(tmp_path)
    created = service.create(work_ref(), need_record())
    successor = _need_successor(
        created.record,
        reason="duplicate_consolidated",
        description="A topology-heavy reason must use its dedicated path.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="dedicated topology path"):
        service.correct(
            support_need_reference(work_ref(), "spn_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spn_slice9b_reserved",
            operation_id="op_spn_slice9b_reserved",
        )
