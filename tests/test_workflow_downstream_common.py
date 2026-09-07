from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    follow_up_reference,
    outcome_reference,
    reentry_reference,
    repair_reference,
)
from portia.workflows.downstream_common import (
    DownstreamWorkflowAuthority,
    parse_explicit_timestamp,
    require_date_order,
    require_downstream_owner,
    require_timestamp_order,
)

TIMESTAMP = "2026-09-04T10:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice1a_test"}


def event_ref(*, version: str = "2") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version=version,
    )


def support_process_ref(*, version: str = "1") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version=version,
    )


def event_record(*, status: str = "active") -> PortiaRecord:
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "school_year": "2026-2027",
            "status": status,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
            "occurrence": {"precision": "exact", "started_at": TIMESTAMP},
            "summary": "Synthetic event for Issue #46 Slice 1a.",
        },
    )


def event_participant_record(
    *,
    participant_id: str = "ep_alpha",
    status: str = "active",
) -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "participant_id": participant_id,
            "status": status,
            "subject": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic {participant_id}",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def support_process_record(*, status: str = "active") -> PortiaRecord:
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
            "workflow_state": "active",
            "summary": "Synthetic support process for Issue #46 Slice 1a.",
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


def support_process_participant_record(
    *,
    participant_id: str = "spp_alpha",
    contexts: list[dict[str, object]] | None = None,
    status: str = "active",
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
            "person": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
            "contexts": contexts or [{"kind": "provider_or_collaborator"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


@pytest.mark.parametrize(
    ("builder", "kind", "record_id"),
    [
        (follow_up_reference, "follow_up", "fup_alpha"),
        (outcome_reference, "outcome", "out_alpha"),
        (reentry_reference, "reentry", "ren_alpha"),
        (repair_reference, "repair", "rpr_alpha"),
    ],
)
@pytest.mark.parametrize("work", [event_ref(), support_process_ref()])
def test_public_reference_builders_are_exact_v1(
    builder: object,
    kind: str,
    record_id: str,
    work: ExactPortiaWorkRef,
) -> None:
    reference = builder(work, record_id)  # type: ignore[operator]
    assert reference.work_ref == work
    assert reference.record_ref.record_kind == kind
    assert reference.record_ref.record_id == record_id
    assert reference.record_ref.contract_version == "1"


def test_downstream_owner_union_is_exact() -> None:
    require_downstream_owner(event_ref())
    require_downstream_owner(support_process_ref())
    with pytest.raises(WorkflowOwnershipError, match="event@2"):
        require_downstream_owner(event_ref(version="1"))
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        require_downstream_owner(support_process_ref(version="2"))


def test_owner_resolution_does_not_follow_successors(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record(status="closed"))
    resolved = DownstreamWorkflowAuthority(tmp_path).load_owner_exact(event_ref())
    assert resolved.record.work_id == "evt_alpha"
    assert resolved.record.status == "closed"


def test_event_target_must_match_event_owner(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    authority = DownstreamWorkflowAuthority(tmp_path)

    result = authority.resolve_target(
        event_ref(),
        {"kind": "event"},
        require_current_use=False,
    )
    assert result.owner.record.work_id == "evt_alpha"
    assert result.participants == ()

    with pytest.raises(WorkflowOwnershipError, match="Event-local target"):
        authority.resolve_target(
            event_ref(),
            {"kind": "support_process"},
            require_current_use=False,
        )


def test_event_participant_target_resolves_exact_v3(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(
        event_ref(),
        event_participant_record(),
    )
    authority = DownstreamWorkflowAuthority(tmp_path)
    result = authority.resolve_target(
        event_ref(),
        {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
        require_current_use=True,
    )
    assert [item.record.logical_id for item in result.participants] == ["ep_alpha"]


def test_support_process_target_must_match_support_process_owner(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(support_process_ref(), support_process_record())
    authority = DownstreamWorkflowAuthority(tmp_path)

    result = authority.resolve_target(
        support_process_ref(),
        {"kind": "support_process"},
        require_current_use=False,
    )
    assert result.owner.record.work_id == "sup_alpha"
    assert result.participants == ()

    with pytest.raises(WorkflowOwnershipError, match="Support Process-local target"):
        authority.resolve_target(
            support_process_ref(),
            {"kind": "event"},
            require_current_use=False,
        )


def test_support_process_operational_context_is_explicit(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(support_process_ref(), support_process_record())
    repository.create_work_record(
        support_process_ref(),
        support_process_participant_record(),
    )
    authority = DownstreamWorkflowAuthority(tmp_path)
    reference = {
        "record_kind": "support_process_participant",
        "record_id": "spp_alpha",
        "contract_version": "1",
    }
    accepted = authority.require_support_process_operational_participant(
        support_process_ref(),
        reference,
        field_name="Follow-Up owner",
        allowed_contexts=frozenset({"provider_or_collaborator", "coordinator"}),
        require_current_use=True,
    )
    assert accepted.participant.record.logical_id == "spp_alpha"


def test_supported_person_context_does_not_become_operational_authority(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(support_process_ref(), support_process_record())
    repository.create_work_record(
        support_process_ref(),
        support_process_participant_record(
            contexts=[{"kind": "supported_person"}],
        ),
    )
    authority = DownstreamWorkflowAuthority(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="provider_or_collaborator"):
        authority.require_support_process_operational_participant(
            support_process_ref(),
            {
                "record_kind": "support_process_participant",
                "record_id": "spp_alpha",
                "contract_version": "1",
            },
            field_name="Follow-Up owner",
            allowed_contexts=frozenset(
                {"provider_or_collaborator", "coordinator"}
            ),
            require_current_use=True,
        )


def test_event_operational_human_accepts_local_operator(tmp_path: Path) -> None:
    authority = DownstreamWorkflowAuthority(tmp_path)
    authority.require_event_operational_human(
        {"kind": "local_operator", "display_label": "Synthetic teacher"},
        field_name="Follow-Up owner",
        require_current_use=True,
    )


@pytest.mark.parametrize(
    "person",
    [
        {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_a",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Synthetic learner"},
        },
        {
            "kind": "descriptive_person",
            "description_type": "outside_person",
            "display_label": "Synthetic person",
        },
        {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
            "detail": "Synthetic unknown person.",
        },
    ],
)
def test_current_event_operational_human_rejects_nonoperational_identity(
    tmp_path: Path,
    person: dict[str, object],
) -> None:
    authority = DownstreamWorkflowAuthority(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError):
        authority.require_event_operational_human(
            person,
            field_name="Outcome evaluator",
            require_current_use=True,
        )


def test_proposed_history_may_preserve_unidentified_operational_attribution(
    tmp_path: Path,
) -> None:
    authority = DownstreamWorkflowAuthority(tmp_path)
    authority.require_event_operational_human(
        {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
            "detail": "Synthetic imported uncertainty.",
        },
        field_name="Follow-Up owner",
        require_current_use=False,
    )


def test_explicit_timestamp_requires_offset() -> None:
    assert parse_explicit_timestamp(
        "2026-09-04T10:00:00-04:00",
        field_name="completed_at",
    ).utcoffset() is not None
    with pytest.raises(WorkflowPrerequisiteError, match="explicit offset"):
        parse_explicit_timestamp(
            "2026-09-04T10:00:00",
            field_name="completed_at",
        )


def test_shared_chronology_helpers_preserve_precision() -> None:
    require_timestamp_order(
        "2026-09-04T10:00:00-04:00",
        "2026-09-04T10:30:00-04:00",
        earlier_name="starts_at",
        later_name="ends_at",
    )
    require_date_order(
        "2026-09-04",
        "2026-09-05",
        earlier_name="starts_on",
        later_name="ends_on",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede"):
        require_timestamp_order(
            "2026-09-04T10:30:00-04:00",
            "2026-09-04T10:00:00-04:00",
            earlier_name="starts_at",
            later_name="ends_at",
        )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede"):
        require_date_order(
            "2026-09-05",
            "2026-09-04",
            earlier_name="starts_on",
            later_name="ends_on",
        )
