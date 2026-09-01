from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaQuarantinedError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice2_test"}


class _BlockingQuarantine:
    def __init__(self, effect: str) -> None:
        self.effect = effect

    def require_allowed(self, _target: object, effect: str) -> None:
        if effect == self.effect:
            raise PortiaQuarantinedError(f"synthetic block: {effect}")


def support_process_ref(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
    version: str = "1",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version=version,
    )


def support_process_wire(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
    status: str = "proposed",
    workflow_state: str = "planning",
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": work_id,
        "school_year": "2026-2027",
        "status": status,
        "workflow_state": workflow_state,
        "summary": "Synthetic bounded support process.",
        "initiation": {
            "kind": "teacher_identified_need",
            "detail": "Synthetic planning need.",
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def support_process_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        support_process_wire(**kwargs),
    )


def descriptive_person(label: str = "Synthetic learner") -> dict[str, object]:
    return {
        "kind": "descriptive_person",
        "description_type": "outside_student",
        "display_label": label,
    }


def unidentified_person() -> dict[str, object]:
    return {
        "kind": "unidentified_person",
        "identity_status": "not_recorded",
        "detail": "Identity not yet known during planning.",
    }


def participant_wire(
    *,
    participant_id: str = "spp_alpha",
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
    status: str = "proposed",
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = TIMESTAMP,
    supersedes: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support_process_participant",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": work_id,
        "participant_id": participant_id,
        "status": status,
        "person": person or descriptive_person(),
        "contexts": contexts or [{"kind": "supported_person"}],
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if supersedes is not None:
        value["supersedes"] = supersedes
    return value


def participant_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        participant_wire(**kwargs),
    )


def create_root(tmp_path: Path) -> ExactPortiaWorkRef:
    reference = support_process_ref()
    SupportProcessWorkflowService(tmp_path).create(support_process_record())
    return reference


def seed_participant(
    tmp_path: Path,
    record: PortiaRecord,
) -> None:
    PortiaRepository(tmp_path).create_work_record(support_process_ref(), record)


def seed_active_root(tmp_path: Path) -> ExactPortiaWorkRef:
    reference = support_process_ref()
    PortiaRepository(tmp_path).create_work(
        reference,
        support_process_record(status="active", workflow_state="active"),
    )
    return reference


def test_reference_is_exact_support_process_participant_v1() -> None:
    reference = support_process_participant_reference(
        support_process_ref(), "spp_alpha"
    )
    assert reference.work_ref == support_process_ref()
    assert reference.record_ref.record_kind == "support_process_participant"
    assert reference.record_ref.record_id == "spp_alpha"
    assert reference.record_ref.contract_version == "1"


def test_proposed_participant_create_load_resolve_and_list(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work, participant_record())
    reference = support_process_participant_reference(work, "spp_alpha")

    assert service.load_exact(reference).path == created.path
    resolved = service.resolve_exact(reference)
    assert resolved.participant.record.logical_id == "spp_alpha"
    assert resolved.kind == "descriptive_person"
    assert resolved.authority is None
    assert [item.record.logical_id for item in service.list(work)] == ["spp_alpha"]


def test_participant_write_requires_exact_support_process_v1_owner(
    tmp_path: Path,
) -> None:
    event = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            event, participant_record()
        )


def test_participant_record_must_match_selected_owner(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    with pytest.raises(WorkflowOwnershipError):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work,
            participant_record(work_id="sup_other"),
        )


def test_new_participant_must_begin_proposed(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="must begin proposed"):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work,
            participant_record(status="active"),
        )


def test_participant_authoring_is_digital_entry_only(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    source = {
        "type": "import",
        "source_label": "synthetic legacy source",
    }
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work,
            participant_record(creation_source=source),
        )


def test_participant_update_cannot_precede_creation(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work,
            participant_record(updated_at="2026-08-31T09:59:00-04:00"),
        )


def test_fresh_participant_cannot_establish_supersession(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    predecessor = support_process_participant_reference(work, "spp_old")
    supersedes = [
        {
            "work_record_ref": predecessor.to_dict(),
            "reason": "person_corrected",
        }
    ]
    with pytest.raises(WorkflowPrerequisiteError, match="supersession history"):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work,
            participant_record(supersedes=supersedes),
        )


def test_proposed_participant_may_preserve_unidentified_person(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    service.create(work, participant_record(person=unidentified_person()))
    resolved = service.resolve_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    assert resolved.kind == "unidentified_person"
    assert resolved.authority is None


def test_activation_candidate_rejects_unidentified_person(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot be unidentified"):
        service.require_activation_candidate(
            work,
            participant_record(status="active", person=unidentified_person()),
        )


def test_activation_candidate_accepts_bounded_descriptive_person(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    candidate = participant_record(status="active")
    accepted = SupportProcessParticipantWorkflowService(
        tmp_path
    ).require_activation_candidate(work, candidate)
    assert accepted.logical_id == "spp_alpha"
    assert accepted.status == "active"


def test_duplicate_local_operator_is_rejected_as_same_logical_person(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    first = {"kind": "local_operator", "display_label": "Synthetic teacher"}
    second = {"kind": "local_operator", "display_label": "Renamed teacher"}
    service.create(work, participant_record(person=first))
    with pytest.raises(WorkflowPrerequisiteError, match="duplicate logical human"):
        service.create(
            work,
            participant_record(participant_id="spp_beta", person=second),
        )


def test_descriptive_labels_are_not_used_as_identity_matching(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    service.create(work, participant_record())
    service.create(work, participant_record(participant_id="spp_beta"))
    assert len(service.list(work)) == 2


@pytest.mark.parametrize(
    ("status", "workflow_state"),
    [
        ("invalidated", "completed"),
        ("superseded", "completed"),
        ("active", "completed"),
        ("active", "discontinued"),
        ("active", "cancelled"),
    ],
)
def test_terminal_or_noncurrent_process_blocks_new_participant_authoring(
    tmp_path: Path,
    status: str,
    workflow_state: str,
) -> None:
    work = support_process_ref()
    PortiaRepository(tmp_path).create_work(
        work,
        support_process_record(status=status, workflow_state=workflow_state),
    )
    with pytest.raises(WorkflowPrerequisiteError):
        SupportProcessParticipantWorkflowService(tmp_path).create(
            work, participant_record()
        )


def test_participant_write_honors_quarantine(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    blocked = SupportProcessParticipantWorkflowService(
        tmp_path,
        quarantine=_BlockingQuarantine("block_work_writes"),  # type: ignore[arg-type]
    )
    with pytest.raises(PortiaQuarantinedError):
        blocked.create(work, participant_record())


def test_root_activation_requires_active_supported_person(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="supported_person"):
        SupportProcessWorkflowService(tmp_path).require_activation_eligibility(work)


def test_root_activation_rejects_collaborator_only_participant(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    seed_participant(
        tmp_path,
        participant_record(
            status="active",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="supported_person"):
        SupportProcessWorkflowService(tmp_path).require_activation_eligibility(work)


def test_root_activation_accepts_active_supported_descriptive_person(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    root = SupportProcessWorkflowService(tmp_path).require_activation_eligibility(work)
    assert root.record.status == "proposed"
    assert root.record.field("workflow_state") == "planning"


def test_root_activation_rejects_active_unidentified_supported_person(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    seed_participant(
        tmp_path,
        participant_record(status="active", person=unidentified_person()),
    )
    with pytest.raises(WorkflowPrerequisiteError):
        SupportProcessWorkflowService(tmp_path).require_activation_eligibility(work)


def test_activation_eligibility_honors_current_use_quarantine(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    blocked = SupportProcessWorkflowService(
        tmp_path,
        quarantine=_BlockingQuarantine("block_current_use"),  # type: ignore[arg-type]
    )
    with pytest.raises(PortiaQuarantinedError):
        blocked.require_activation_eligibility(work)


def test_exact_historical_resolution_does_not_require_current_parent(
    tmp_path: Path,
) -> None:
    work = support_process_ref()
    PortiaRepository(tmp_path).create_work(
        work,
        support_process_record(status="superseded", workflow_state="completed"),
    )
    seed_participant(tmp_path, participant_record(status="superseded"))
    resolved = SupportProcessParticipantWorkflowService(tmp_path).resolve_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    assert resolved.participant.record.status == "superseded"


def test_current_participant_use_requires_active_parent_and_participant(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    resolved = SupportProcessParticipantWorkflowService(tmp_path).require_current_use(
        support_process_participant_reference(work, "spp_alpha")
    )
    assert resolved.participant.record.status == "active"
    assert resolved.kind == "descriptive_person"


def test_cross_class_roster_identity_is_resolved_without_changing_owner(
    tmp_path: Path,
) -> None:
    from typing import cast

    from portia.identity.roster import ResolvedRosterStudent
    from portia.validation import KnownValidationContext
    from portia.workflows.context import (
        AuthoritativeWorkflowContext,
        roster_references,
    )

    class _Rosters:
        def __init__(self) -> None:
            self.seen: list[object] = []

        def resolve_reference(self, reference: object) -> ResolvedRosterStudent:
            self.seen.append(reference)
            return cast(ResolvedRosterStudent, object())

    class _Actors:
        pass

    class _Context:
        def __init__(self) -> None:
            self.rosters = _Rosters()
            self.actors = _Actors()

        def assemble(
            self,
            records: object,
            *,
            require_actor_current_use: bool = False,
        ) -> AuthoritativeWorkflowContext:
            del require_actor_current_use
            assert isinstance(records, tuple)
            references = roster_references(records)
            return AuthoritativeWorkflowContext(
                validation=KnownValidationContext.from_values(
                    roster_students=references
                ),
                roster_students=(),
                actors=(),
            )

    work = create_root(tmp_path)
    context = _Context()
    person = {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": "class_b",
            "student_id": "student_2",
        },
        "display_snapshot": {"display_name": "Synthetic learner"},
    }
    service = SupportProcessParticipantWorkflowService(
        tmp_path,
        context_assembler=context,  # type: ignore[arg-type]
    )
    created = service.create(work, participant_record(person=person))

    assert created.record.class_id == "class_a"
    assert created.record.work_id == "sup_alpha"
    assert len(context.rosters.seen) >= 1
    reference = context.rosters.seen[0]
    assert getattr(reference, "class_id") == "class_b"
    assert getattr(reference, "student_id") == "student_2"


def test_activation_candidate_defers_paper_and_import_review_history(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    source = {
        "type": "import",
        "source_label": "synthetic legacy source",
    }
    with pytest.raises(WorkflowPrerequisiteError, match="review history is deferred"):
        SupportProcessParticipantWorkflowService(
            tmp_path
        ).require_activation_candidate(
            work,
            participant_record(status="active", creation_source=source),
        )


# Slice 9d — Support Process Participant correction.
CORRECTION_UPDATE = "2026-08-31T10:20:00-04:00"


def _participant_successor(
    prior: PortiaRecord,
    *,
    participant_id: str = "spp_beta",
    reason: str,
    detail: str | None = None,
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
    updated_at: str = CORRECTION_UPDATE,
) -> PortiaRecord:
    prior_id = prior.logical_id
    assert prior_id is not None
    wire = prior.to_dict()
    wire["participant_id"] = participant_id
    if person is not None:
        wire["person"] = person
    if contexts is not None:
        wire["contexts"] = contexts
    entry: dict[str, object] = {
        "work_record_ref": support_process_participant_reference(
            support_process_ref(),
            prior_id,
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
    return parse_portia_record(
        "support_process_participant",
        "1",
        wire,
    )


def test_participant_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="contexts_corrected",
        contexts=[
            {"kind": "supported_person"},
            {"kind": "observer"},
        ],
    )

    service.correct(
        support_process_participant_reference(work, "spp_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_spp_slice9d_contexts",
        operation_id="op_spp_slice9d_contexts",
    )

    historical = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    current = service.require_current_use(
        support_process_participant_reference(work, "spp_beta")
    )
    assert historical.record.status == "superseded"
    assert current.participant.record.status == "active"
    assert current.participant.record.field("contexts") == (
        {"kind": "supported_person"},
        {"kind": "observer"},
    )


def test_participant_correction_records_correction_reason(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="person_corrected",
        person=descriptive_person("Corrected synthetic learner"),
    )
    service.correct(
        support_process_participant_reference(work, "spp_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_spp_slice9d_person",
        operation_id="op_spp_slice9d_person",
    )

    transition = service.repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_spp_slice9d_person",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "person_corrected",
    }


def test_participant_correction_can_replace_proposed_record(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work, participant_record())
    successor = _participant_successor(
        created.record,
        reason="contexts_corrected",
        contexts=[{"kind": "observer"}],
    )
    service.correct(
        support_process_participant_reference(work, "spp_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spp_slice9d_proposed",
        operation_id="op_spp_slice9d_proposed",
    )
    assert service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        support_process_participant_reference(work, "spp_beta")
    ).record.status == "proposed"


def test_participant_correction_requires_new_identity(tmp_path: Path) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work, participant_record())
    successor = _participant_successor(
        created.record,
        participant_id="spp_alpha",
        reason="contexts_corrected",
        contexts=[{"kind": "observer"}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="new canonical identity"):
        service.correct(
            support_process_participant_reference(work, "spp_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spp_slice9d_same_id",
            operation_id="op_spp_slice9d_same_id",
        )


def test_participant_correction_reason_must_match_changed_fact(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work, participant_record())
    successor = _participant_successor(
        created.record,
        reason="person_corrected",
        contexts=[{"kind": "observer"}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            support_process_participant_reference(work, "spp_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spp_slice9d_mismatch",
            operation_id="op_spp_slice9d_mismatch",
        )


def test_active_participant_correction_may_preserve_same_person(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="contexts_corrected",
        contexts=[
            {"kind": "supported_person"},
            {"kind": "coordinator"},
        ],
    )
    service.correct(
        support_process_participant_reference(work, "spp_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_spp_slice9d_same_person",
        operation_id="op_spp_slice9d_same_person",
    )
    resolved = service.require_current_use(
        support_process_participant_reference(work, "spp_beta")
    )
    assert resolved.kind == "descriptive_person"


def test_active_participant_person_correction_revalidates_current_use(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="person_corrected",
        person=unidentified_person(),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot be unidentified"):
        service.correct(
            support_process_participant_reference(work, "spp_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_spp_slice9d_unidentified",
            operation_id="op_spp_slice9d_unidentified",
        )


def test_participant_correction_rejects_reserved_topology_reason(
    tmp_path: Path,
) -> None:
    work = create_root(tmp_path)
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work, participant_record())
    successor = _participant_successor(
        created.record,
        reason="work_root_corrected",
        contexts=[{"kind": "observer"}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="dedicated topology path"):
        service.correct(
            support_process_participant_reference(work, "spp_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spp_slice9d_reserved",
            operation_id="op_spp_slice9d_reserved",
        )


def test_superseded_participant_remains_exact_history_not_current(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="contexts_corrected",
        contexts=[
            {"kind": "supported_person"},
            {"kind": "observer"},
        ],
    )
    service.correct(
        support_process_participant_reference(work, "spp_alpha"),
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_spp_slice9d_history",
        operation_id="op_spp_slice9d_history",
    )

    assert service.resolve_exact(
        support_process_participant_reference(work, "spp_alpha")
    ).participant.record.status == "superseded"
    with pytest.raises(WorkflowPrerequisiteError, match="not active for current use"):
        service.require_current_use(
            support_process_participant_reference(work, "spp_alpha")
        )


def test_participant_correction_cannot_remove_final_supported_person(
    tmp_path: Path,
) -> None:
    work = seed_active_root(tmp_path)
    seed_participant(tmp_path, participant_record(status="active"))
    service = SupportProcessParticipantWorkflowService(tmp_path)
    predecessor = service.load_exact(
        support_process_participant_reference(work, "spp_alpha")
    )
    successor = _participant_successor(
        predecessor.record,
        reason="contexts_corrected",
        contexts=[{"kind": "observer"}],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot lose its final active supported_person",
    ):
        service.correct(
            support_process_participant_reference(work, "spp_alpha"),
            successor,
            expected=predecessor.fingerprint,
            transition_id="lct_spp_slice9d_final_supported_person",
            operation_id="op_spp_slice9d_final_supported_person",
        )
