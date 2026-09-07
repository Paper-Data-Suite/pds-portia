"""Issue #46 Slice 2a tests for core Follow-Up workflow authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    FollowUpWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    follow_up_reference,
)
from portia.workflows.downstream_lifecycle import downstream_lifecycle_state

TIMESTAMP = "2026-09-04T10:00:00-04:00"
UPDATED = "2026-09-04T10:05:00-04:00"
PROGRESSED = "2026-09-04T10:10:00-04:00"
COMPLETED = "2026-09-04T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice2a_test"}


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
            "summary": "Synthetic bounded Event for Follow-Up testing.",
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


def event_target(
    *,
    participant_id: str = "ep_alpha",
) -> dict[str, object]:
    return {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": participant_id,
            "contract_version": "3",
        },
    }


def support_target(
    *,
    participant_id: str = "spp_student",
) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def local_operator_owner() -> dict[str, object]:
    return {
        "kind": "represented_human",
        "person": {
            "kind": "local_operator",
            "display_label": "Synthetic teacher",
        },
    }


def follow_up_record(
    *,
    work: ExactPortiaWorkRef | None = None,
    follow_up_id: str = "fup_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    owner: dict[str, object] | None = None,
    purpose: dict[str, object] | None = None,
    planned_timing: dict[str, object] | None = None,
    workflow_state: str = "scheduled",
    source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = UPDATED,
    related_records: list[dict[str, object]] | None = None,
    supersedes: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    selected = work or event_ref()
    if target is None:
        target = (
            event_target()
            if selected.work_kind == "event"
            else support_target()
        )
    if owner is None:
        owner = (
            local_operator_owner()
            if selected.work_kind == "event"
            else {
                "kind": "support_process_participant",
                "participant_ref": {
                    "record_kind": "support_process_participant",
                    "record_id": "spp_coordinator",
                    "contract_version": "1",
                },
            }
        )
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "follow_up",
        "module_id": "portia",
        "class_id": selected.class_id,
        "work_kind": selected.work_kind,
        "work_id": selected.work_id,
        "follow_up_id": follow_up_id,
        "status": status,
        "target": target,
        "owner": owner,
        "purpose": purpose
        or (
            {"kind": "student_check_in"}
            if selected.work_kind == "event"
            else {"kind": "coordination"}
        ),
        "planned_timing": planned_timing
        or {"kind": "date_only", "date": "2026-09-05"},
        "workflow_state": workflow_state,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if related_records is not None:
        wire["related_records"] = related_records
    if supersedes is not None:
        wire["supersedes"] = supersedes
    return parse_portia_record("follow_up", "1", wire)


def follow_up_revision(
    prior: PortiaRecord,
    *,
    workflow_state: str,
    updated_at: str = PROGRESSED,
    completed_at: str | None = None,
    status: str | None = None,
    purpose: dict[str, object] | None = None,
    related_records: list[dict[str, object]] | None = None,
    omit_related_records: bool = False,
    disposition: dict[str, object] | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["workflow_state"] = workflow_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if completed_at is None:
        wire.pop("completed_at", None)
    else:
        wire["completed_at"] = completed_at
    if status is not None:
        wire["status"] = status
    if purpose is not None:
        wire["purpose"] = purpose
    if omit_related_records:
        wire.pop("related_records", None)
    elif related_records is not None:
        wire["related_records"] = related_records
    if disposition is not None:
        wire["disposition"] = disposition
    return parse_portia_record("follow_up", "1", wire)


def seed_event(
    tmp_path: Path,
    *,
    event_id: str = "evt_alpha",
    status: str = "active",
) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    work = event_ref(event_id=event_id)
    repository.create_work(
        work,
        event_record(event_id=event_id, status=status),
    )
    repository.create_work_record(
        work,
        event_participant_record(event_id=event_id),
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


def test_create_load_list_and_current_event_follow_up(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())

    assert created.record.logical_id == "fup_alpha"
    reference = follow_up_reference(event_ref(), "fup_alpha")
    assert service.load_exact(reference).record.logical_id == "fup_alpha"
    assert service.resolve_exact(reference).record.logical_id == "fup_alpha"
    assert [item.record.logical_id for item in service.list(event_ref())] == [
        "fup_alpha"
    ]
    assert [
        item.record.logical_id for item in service.list_follow_ups(event_ref())
    ] == ["fup_alpha"]
    assert service.require_current_use(reference).record.logical_id == "fup_alpha"
    assert service.resolve_current(reference).record.logical_id == "fup_alpha"


@pytest.mark.parametrize(
    ("work", "follow_up_id", "planned_timing"),
    [
        (
            event_ref(),
            "fup_event_exact",
            {
                "kind": "exact_time",
                "at": "2026-09-05T09:30:00-04:00",
            },
        ),
        (
            support_ref(),
            "fup_support_window",
            {
                "kind": "window",
                "starts_on": "2026-09-05",
                "ends_on": "2026-09-07",
            },
        ),
        (
            support_ref(),
            "fup_support_exact_window",
            {
                "kind": "window",
                "starts_at": "2026-09-05T09:00:00-04:00",
                "ends_at": "2026-09-05T11:00:00-04:00",
            },
        ),
    ],
    ids=("event-exact-time", "support-date-window", "support-exact-window"),
)
def test_follow_up_accepts_frozen_planned_timing_forms(
    tmp_path: Path,
    work: ExactPortiaWorkRef,
    follow_up_id: str,
    planned_timing: dict[str, object],
) -> None:
    if work.work_kind == "event":
        seed_event(tmp_path)
    else:
        seed_support(tmp_path)

    created = FollowUpWorkflowService(tmp_path).create(
        work,
        follow_up_record(
            work=work,
            follow_up_id=follow_up_id,
            planned_timing=planned_timing,
        ),
    )
    assert created.record.to_dict()["planned_timing"] == planned_timing


def test_active_follow_up_can_target_closed_event_history(tmp_path: Path) -> None:
    seed_event(tmp_path, status="closed")
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    assert created.record.status == "active"
    assert (
        service.require_current_use(
            follow_up_reference(event_ref(), "fup_alpha")
        ).record.logical_id
        == "fup_alpha"
    )


def test_proposed_follow_up_may_preserve_descriptive_owner_but_is_not_current(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    owner = {
        "kind": "represented_human",
        "person": {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff member",
        },
    }
    service = FollowUpWorkflowService(tmp_path)
    service.create(
        event_ref(),
        follow_up_record(status="proposed", owner=owner),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(
            follow_up_reference(event_ref(), "fup_alpha")
        )


def test_active_event_follow_up_rejects_roster_student_owner(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    person = {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": "class_a",
            "student_id": "student_1",
        },
        "display_snapshot": {"display_name": "Synthetic student"},
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "Follow-Up owner cannot use roster-student identity "
            "as operational authority"
        ),
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(
                owner={"kind": "represented_human", "person": person},
            ),
        )


def test_active_event_follow_up_rejects_descriptive_owner(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    person = {
        "kind": "descriptive_person",
        "description_type": "school_staff",
        "display_label": "Synthetic staff",
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Follow-Up owner requires an identified operational human",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(
                owner={"kind": "represented_human", "person": person},
            ),
        )


def test_active_event_follow_up_rejects_unidentified_owner(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    person = {
        "kind": "unidentified_person",
        "identity_status": "not_recorded",
        "detail": "Synthetic unknown owner.",
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="current Follow-Up owner requires an identified operational human",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(
                owner={"kind": "represented_human", "person": person},
            ),
        )



def test_active_support_follow_up_requires_exact_operational_owner(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        follow_up_record(work=support_ref(), follow_up_id="fup_support"),
    )
    assert created.record.logical_id == "fup_support"
    assert (
        service.require_current_use(
            follow_up_reference(support_ref(), "fup_support")
        ).record.logical_id
        == "fup_support"
    )


def test_support_other_purpose_with_detail_is_accepted(tmp_path: Path) -> None:
    seed_support(tmp_path)
    purpose = {
        "kind": "other",
        "detail": "Synthetic bounded coordination check.",
    }
    created = FollowUpWorkflowService(tmp_path).create(
        support_ref(),
        follow_up_record(
            work=support_ref(),
            follow_up_id="fup_support_other",
            purpose=purpose,
        ),
    )
    assert created.record.to_dict()["purpose"] == purpose


def test_supported_person_context_does_not_become_follow_up_owner(
    tmp_path: Path,
) -> None:
    seed_support(tmp_path)
    owner = {
        "kind": "support_process_participant",
        "participant_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_student",
            "contract_version": "1",
        },
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            r"Follow-Up owner requires Support Process Participant context "
            r"in \{coordinator, provider_or_collaborator\}"
        ),
    ):
        FollowUpWorkflowService(tmp_path).create(
            support_ref(),
            follow_up_record(work=support_ref(), owner=owner),
        )


def test_follow_up_rejects_reversed_date_window(tmp_path: Path) -> None:
    seed_event(tmp_path)
    planned_timing = {
        "kind": "window",
        "starts_on": "2026-09-06",
        "ends_on": "2026-09-05",
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Follow-Up ends_on cannot precede Follow-Up starts_on",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(planned_timing=planned_timing),
        )


def test_follow_up_rejects_reversed_exact_window(tmp_path: Path) -> None:
    seed_event(tmp_path)
    planned_timing = {
        "kind": "window",
        "starts_at": "2026-09-06T12:00:00-04:00",
        "ends_at": "2026-09-06T11:00:00-04:00",
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Follow-Up ends_at cannot precede Follow-Up starts_at",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(planned_timing=planned_timing),
        )



def test_follow_up_rejects_updated_before_created(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Follow-Up updated_at cannot precede Follow-Up created_at",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(
                created_at="2026-09-04T11:00:00-04:00",
                updated_at="2026-09-04T10:00:00-04:00",
            ),
        )


def test_new_follow_up_rejects_import_materialization(tmp_path: Path) -> None:
    seed_event(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry"):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(
                status="proposed",
                source={
                    "type": "import",
                    "source_label": "Synthetic import",
                    "external_reference": "row-1",
                },
            ),
        )


def test_proposed_imported_support_follow_up_remains_exactly_readable(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    imported = follow_up_record(
        work=support_ref(),
        follow_up_id="fup_imported",
        status="proposed",
        source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-1",
        },
    )
    repository.create_work_record(support_ref(), imported)

    service = FollowUpWorkflowService(tmp_path)
    reference = follow_up_reference(support_ref(), "fup_imported")
    assert service.load_exact(reference).record.logical_id == "fup_imported"
    assert service.resolve_exact(reference).record.status == "proposed"


def test_active_imported_follow_up_requires_accepted_review_history(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    imported = follow_up_record(
        follow_up_id="fup_imported_active",
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
        FollowUpWorkflowService(tmp_path).require_current_use(
            follow_up_reference(event_ref(), "fup_imported_active")
        )


def test_follow_up_related_record_must_resolve_exactly(tmp_path: Path) -> None:
    seed_event(tmp_path)
    relation = {
        "role": "context",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_missing",
                "contract_version": "3",
            },
        },
    }
    with pytest.raises(WorkflowPrerequisiteError, match="does not resolve"):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(related_records=[relation]),
        )


def test_follow_up_to_role_requires_follow_up_contract(tmp_path: Path) -> None:
    seed_event(tmp_path)
    relation = {
        "role": "follow_up_to",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Follow-Up related_records role 'follow_up_to' is incompatible",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(related_records=[relation]),
        )


def test_produced_relation_must_remain_same_work(tmp_path: Path) -> None:
    repository = seed_event(tmp_path)
    other = event_ref(event_id="evt_beta")
    repository.create_work(other, event_record(event_id="evt_beta"))
    repository.create_work_record(
        other,
        event_participant_record(event_id="evt_beta"),
    )
    relation = {
        "role": "produced",
        "record_ref": {
            "work_ref": other.to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    with pytest.raises(
        WorkflowOwnershipError,
        match=(
            "Follow-Up related_records role 'produced' "
            "must remain in the owning work"
        ),
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(related_records=[relation]),
        )


def test_follow_up_rejects_self_related_record(tmp_path: Path) -> None:
    seed_event(tmp_path)
    relation = {
        "role": "context",
        "record_ref": follow_up_reference(
            event_ref(),
            "fup_alpha",
        ).to_dict(),
    }
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Follow-Up related_records cannot reference the current record itself",
    ):
        FollowUpWorkflowService(tmp_path).create(
            event_ref(),
            follow_up_record(related_records=[relation]),
        )


def test_fresh_follow_up_rejects_supersession_history(tmp_path: Path) -> None:
    seed_event(tmp_path)
    predecessor = follow_up_reference(event_ref(), "fup_old")
    successor = follow_up_record(
        supersedes=[
            {
                "work_record_ref": predecessor.to_dict(),
                "reason": "timing_corrected",
            }
        ]
    )
    with pytest.raises(WorkflowPrerequisiteError, match="fresh Follow-Up"):
        FollowUpWorkflowService(tmp_path).create(event_ref(), successor)


def test_current_use_revalidates_bad_preexisting_supersession_topology(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    bad = follow_up_record(
        supersedes=[
            {
                "work_record_ref": follow_up_reference(
                    event_ref(),
                    "fup_alpha",
                ).to_dict(),
                "reason": "timing_corrected",
            }
        ]
    )
    repository.create_work_record(event_ref(), bad)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="follow_up cannot supersede itself",
    ):
        FollowUpWorkflowService(tmp_path).require_current_use(
            follow_up_reference(event_ref(), "fup_alpha")
        )


def test_follow_up_ordinary_correction_cannot_cross_work_roots(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    other = event_ref(event_id="evt_beta")
    repository.create_work(other, event_record(event_id="evt_beta"))
    repository.create_work_record(
        other,
        event_participant_record(event_id="evt_beta"),
    )
    bad = follow_up_record(
        supersedes=[
            {
                "work_record_ref": follow_up_reference(
                    other,
                    "fup_old",
                ).to_dict(),
                "reason": "timing_corrected",
            }
        ]
    )
    repository.create_work_record(event_ref(), bad)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary follow_up correction cannot cross work roots",
    ):
        FollowUpWorkflowService(tmp_path).require_current_use(
            follow_up_reference(event_ref(), "fup_alpha")
        )


CORRECTION_UPDATED = "2026-09-04T10:35:00-04:00"


def follow_up_successor(
    prior: PortiaRecord,
    *,
    follow_up_id: str = "fup_beta",
    reason: str = "timing_corrected",
    detail: str | None = None,
    planned_timing: dict[str, object] | None = None,
    purpose: dict[str, object] | None = None,
    completed_at: str | None | object = Ellipsis,
    workflow_state: str | None = None,
    related_records: list[dict[str, object]] | None | object = Ellipsis,
    disposition: dict[str, object] | None | object = Ellipsis,
    status: str = "active",
    updated_at: str = CORRECTION_UPDATED,
) -> PortiaRecord:
    wire = prior.to_dict()
    prior_id = prior.logical_id
    assert prior_id is not None
    work = ExactPortiaWorkRef(
        class_id=str(wire["class_id"]),
        work_id=str(wire["work_id"]),
        work_kind=str(wire["work_kind"]),
        contract_version="2" if wire["work_kind"] == "event" else "1",
    )
    wire["follow_up_id"] = follow_up_id
    wire["status"] = status
    if planned_timing is not None:
        wire["planned_timing"] = planned_timing
    if purpose is not None:
        wire["purpose"] = purpose
    if workflow_state is not None:
        wire["workflow_state"] = workflow_state
    if completed_at is not Ellipsis:
        if completed_at is None:
            wire.pop("completed_at", None)
        else:
            wire["completed_at"] = completed_at
    if related_records is not Ellipsis:
        if related_records is None:
            wire.pop("related_records", None)
        else:
            wire["related_records"] = related_records
    if disposition is not Ellipsis:
        if disposition is None:
            wire.pop("disposition", None)
        else:
            wire["disposition"] = disposition
    entry: dict[str, object] = {
        "work_record_ref": follow_up_reference(work, prior_id).to_dict(),
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    wire["supersedes"] = [entry]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("follow_up", "1", wire)


CONSOLIDATION_UPDATED = "2026-09-04T10:45:00-04:00"


def follow_up_consolidation_successor(
    priors: tuple[PortiaRecord, ...],
    *,
    follow_up_id: str = "fup_canonical",
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
    wire["follow_up_id"] = follow_up_id
    wire["status"] = status
    wire["supersedes"] = [
        {
            "work_record_ref": follow_up_reference(
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
    return parse_portia_record("follow_up", "1", wire)


WORK_ROOT_UPDATED = "2026-09-04T10:55:00-04:00"


def follow_up_work_root_successor(
    prior: PortiaRecord,
    *,
    destination_work: ExactPortiaWorkRef,
    planned_timing: dict[str, object] | None = None,
    follow_up_id: str | None = None,
    status: str = "active",
    updated_at: str = WORK_ROOT_UPDATED,
) -> PortiaRecord:
    prior_data = prior.to_dict()
    prior_id = prior.logical_id
    assert prior_id is not None
    source_kind = str(prior_data["work_kind"])
    source_work = ExactPortiaWorkRef(
        class_id=str(prior_data["class_id"]),
        work_id=str(prior_data["work_id"]),
        work_kind=source_kind,
        contract_version="2" if source_kind == "event" else "1",
    )
    wire = prior.to_dict()
    wire["class_id"] = destination_work.class_id
    wire["work_kind"] = destination_work.work_kind
    wire["work_id"] = destination_work.work_id
    wire["follow_up_id"] = follow_up_id or prior_id
    wire["status"] = status
    wire["target"] = (
        event_target()
        if destination_work.work_kind == "event"
        else support_target()
    )
    wire["owner"] = (
        local_operator_owner()
        if destination_work.work_kind == "event"
        else {
            "kind": "support_process_participant",
            "participant_ref": {
                "record_kind": "support_process_participant",
                "record_id": "spp_coordinator",
                "contract_version": "1",
            },
        }
    )
    if planned_timing is not None:
        wire["planned_timing"] = planned_timing
    wire["supersedes"] = [
        {
            "work_record_ref": follow_up_reference(
                source_work,
                prior_id,
            ).to_dict(),
            "reason": "work_root_corrected",
        }
    ]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("follow_up", "1", wire)


LIFECYCLE_UPDATED = "2026-09-04T10:25:00-04:00"


def follow_up_lifecycle_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str = LIFECYCLE_UPDATED,
    purpose: dict[str, object] | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    if purpose is not None:
        wire["purpose"] = purpose
    return parse_portia_record("follow_up", "1", wire)


def test_proposed_follow_up_can_activate_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(status="proposed"),
    )
    reference = follow_up_reference(event_ref(), "fup_alpha")

    service.transition_lifecycle(
        reference,
        follow_up_lifecycle_revision(created.record, status="active"),
        expected=created.fingerprint,
        transition_id="lct_fup_activate",
        reason_code="reviewed",
        operation_id="op_fup_activate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "active"
    current = service.require_current_use(reference)
    assert current.fingerprint == accepted.fingerprint

    transition = service.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_fup_activate",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"
    assert transition.record.to_dict()["target"] == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "follow_up",
            "record_id": "fup_alpha",
            "contract_version": "1",
        },
    }


def test_active_follow_up_can_be_invalidated_and_stops_current_use(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    reference = follow_up_reference(event_ref(), "fup_alpha")

    service.transition_lifecycle(
        reference,
        follow_up_lifecycle_revision(created.record, status="invalidated"),
        expected=created.fingerprint,
        transition_id="lct_fup_invalidate",
        reason_code="recording_error",
        operation_id="op_fup_invalidate",
    )

    accepted = service.load_exact(reference)
    assert accepted.record.status == "invalidated"
    state = downstream_lifecycle_state(
        service.repository,
        event_ref(),
        accepted.record,
    )
    assert state.selected_status == "invalidated"
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active canonical status",
    ):
        service.require_current_use(reference)


def test_follow_up_lifecycle_cannot_rewrite_purpose(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    reference = follow_up_reference(event_ref(), "fup_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite field purpose",
    ):
        service.transition_lifecycle(
            reference,
            follow_up_lifecycle_revision(
                created.record,
                status="invalidated",
                purpose={"kind": "event_review"},
            ),
            expected=created.fingerprint,
            transition_id="lct_fup_bad_purpose",
            reason_code="recording_error",
            operation_id="op_fup_bad_purpose",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_follow_up_supersession_is_reserved_for_correction(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    reference = follow_up_reference(event_ref(), "fup_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="correction workflow",
    ):
        service.transition_lifecycle(
            reference,
            follow_up_lifecycle_revision(
                created.record,
                status="superseded",
            ),
            expected=created.fingerprint,
            transition_id="lct_fup_bad_superseded",
            reason_code="recording_error",
            operation_id="op_fup_bad_superseded",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_follow_up_lifecycle_requires_current_expected_revision(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(status="proposed"),
    )
    reference = follow_up_reference(event_ref(), "fup_alpha")
    service.transition_lifecycle(
        reference,
        follow_up_lifecycle_revision(created.record, status="active"),
        expected=created.fingerprint,
        transition_id="lct_fup_activate_once",
        reason_code="reviewed",
        operation_id="op_fup_activate_once",
    )

    with pytest.raises(PortiaConflictError, match="expected action state"):
        service.transition_lifecycle(
            reference,
            follow_up_lifecycle_revision(
                created.record,
                status="invalidated",
                updated_at="2026-09-04T10:30:00-04:00",
            ),
            expected=created.fingerprint,
            transition_id="lct_fup_stale",
            reason_code="recording_error",
            operation_id="op_fup_stale",
        )


def test_follow_up_lifecycle_effective_at_cannot_precede_creation(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(status="proposed"),
    )
    reference = follow_up_reference(event_ref(), "fup_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot precede record creation",
    ):
        service.transition_lifecycle(
            reference,
            follow_up_lifecycle_revision(created.record, status="active"),
            expected=created.fingerprint,
            transition_id="lct_fup_bad_effective",
            reason_code="reviewed",
            effective_at="2026-09-03T10:00:00-04:00",
            operation_id="op_fup_bad_effective",
        )


def test_follow_up_timing_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(
            follow_up_id="fup_old",
            planned_timing={"kind": "date_only", "date": "2026-09-05"},
        ),
    )
    predecessor = follow_up_reference(event_ref(), "fup_old")
    root_before = repository.load_work(event_ref()).fingerprint
    successor = follow_up_successor(
        created.record,
        follow_up_id="fup_successor",
        reason="timing_corrected",
        planned_timing={"kind": "date_only", "date": "2026-09-06"},
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fup_timing_correction",
        operation_id="op_fup_timing_correction",
    )

    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        follow_up_reference(event_ref(), "fup_successor")
    )
    assert old_exact.record.status == "superseded"
    assert old_exact.record.field("planned_timing") == {
        "kind": "date_only",
        "date": "2026-09-05",
    }
    assert current.record.status == "active"
    assert current.record.field("planned_timing") == {
        "kind": "date_only",
        "date": "2026-09-06",
    }
    assert repository.load_work(event_ref()).fingerprint == root_before

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_fup_timing_correction",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.to_dict()["target"] == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "follow_up",
            "record_id": "fup_old",
            "contract_version": "1",
        },
    }

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(predecessor)


def test_terminal_completion_fact_correction_uses_successor_history(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    completed = service.transition_workflow_state(
        predecessor,
        follow_up_revision(
            created.record,
            workflow_state="completed",
            updated_at=COMPLETED,
            completed_at=COMPLETED,
        ),
        expected=created.fingerprint,
    )
    corrected_completed_at = "2026-09-04T10:16:00-04:00"
    successor = follow_up_successor(
        completed.record,
        reason="completion_corrected",
        completed_at=corrected_completed_at,
    )

    service.correct(
        predecessor,
        successor,
        expected=completed.fingerprint,
        transition_id="lct_fup_completion_correction",
        operation_id="op_fup_completion_correction",
    )

    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        follow_up_reference(event_ref(), "fup_beta")
    )
    assert old_exact.record.status == "superseded"
    assert old_exact.record.field("workflow_state") == "completed"
    assert old_exact.record.field("completed_at") == COMPLETED
    assert current.record.field("workflow_state") == "completed"
    assert current.record.field("completed_at") == corrected_completed_at


def test_follow_up_correction_reason_must_match_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_successor(
        created.record,
        reason="timing_corrected",
        purpose={"kind": "event_review"},
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected fact",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_bad_reason",
            operation_id="op_fup_bad_reason",
        )

    assert service.resolve_exact(predecessor).fingerprint == created.fingerprint


def test_follow_up_correction_requires_actual_material_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_successor(
        created.record,
        reason="timing_corrected",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires an actual Follow-Up fact change",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_noop_correction",
            operation_id="op_fup_noop_correction",
        )

    assert service.resolve_exact(predecessor).fingerprint == created.fingerprint


def test_follow_up_correction_successor_must_be_active(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_successor(
        created.record,
        reason="timing_corrected",
        planned_timing={"kind": "date_only", "date": "2026-09-06"},
        status="invalidated",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="corrected Follow-Up successor must be active",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_inactive_successor",
            operation_id="op_fup_inactive_successor",
        )


def test_follow_up_correction_requires_current_expected_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_successor(
        created.record,
        reason="timing_corrected",
        planned_timing={"kind": "date_only", "date": "2026-09-06"},
    )
    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fup_first_correction",
        operation_id="op_fup_first_correction",
    )

    second_successor = follow_up_successor(
        created.record,
        follow_up_id="fup_gamma",
        reason="timing_corrected",
        planned_timing={"kind": "date_only", "date": "2026-09-07"},
        updated_at="2026-09-04T10:40:00-04:00",
    )
    with pytest.raises(PortiaConflictError, match="expected predecessor action state"):
        service.correct(
            predecessor,
            second_successor,
            expected=created.fingerprint,
            transition_id="lct_fup_stale_correction",
            operation_id="op_fup_stale_correction",
        )


def test_follow_up_correction_does_not_silently_retarget_exact_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor_reference = follow_up_reference(event_ref(), "fup_beta")
    successor = follow_up_successor(
        created.record,
        reason="purpose_corrected",
        purpose={"kind": "event_review"},
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fup_exact_history",
        operation_id="op_fup_exact_history",
    )

    exact_old = service.resolve_exact(predecessor)
    exact_new = service.resolve_exact(successor_reference)
    assert exact_old.record.logical_id == "fup_alpha"
    assert exact_old.record.status == "superseded"
    assert exact_new.record.logical_id == "fup_beta"
    assert exact_new.record.status == "active"


def test_follow_up_correction_rejects_wrong_selected_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_alpha"),
    )
    service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_other"),
    )
    successor = follow_up_successor(
        first.record,
        reason="timing_corrected",
        planned_timing={"kind": "date_only", "date": "2026-09-06"},
    )

    with pytest.raises(
        WorkflowOwnershipError,
        match="must supersede the exact selected predecessor",
    ):
        service.correct(
            follow_up_reference(event_ref(), "fup_other"),
            successor,
            expected=first.fingerprint,
            transition_id="lct_fup_wrong_predecessor",
            operation_id="op_fup_wrong_predecessor",
        )


def test_follow_up_duplicate_consolidation_supersedes_all_exact_predecessors(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_a"),
    )
    second = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_b"),
    )
    successor = follow_up_consolidation_successor(
        (first.record, second.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "fup_dup_a": first.fingerprint,
            "fup_dup_b": second.fingerprint,
        },
        transition_ids={
            "fup_dup_a": "lct_fup_dup_a",
            "fup_dup_b": "lct_fup_dup_b",
        },
        operation_id="op_fup_duplicate_consolidation",
    )

    first_exact = service.resolve_exact(
        follow_up_reference(event_ref(), "fup_dup_a")
    )
    second_exact = service.resolve_exact(
        follow_up_reference(event_ref(), "fup_dup_b")
    )
    current = service.require_current_use(
        follow_up_reference(event_ref(), "fup_canonical")
    )
    assert first_exact.record.status == "superseded"
    assert second_exact.record.status == "superseded"
    assert first_exact.record.logical_id == "fup_dup_a"
    assert second_exact.record.logical_id == "fup_dup_b"
    assert current.record.status == "active"
    assert current.record.logical_id == "fup_canonical"

    for transition_id in ("lct_fup_dup_a", "lct_fup_dup_b"):
        transition = service.repository.load_work_record(
            event_ref(),
            "lifecycle_transition",
            "1",
            transition_id,
        )
        assert transition.record.field("to_status") == "superseded"
        assert transition.record.to_dict()["reason"]["category"] == "consolidation"


def test_follow_up_duplicate_consolidation_accepts_invalidated_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_a"),
    )
    second = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_b"),
    )
    second_ref = follow_up_reference(event_ref(), "fup_dup_b")
    service.transition_lifecycle(
        second_ref,
        follow_up_lifecycle_revision(
            second.record,
            status="invalidated",
            updated_at="2026-09-04T10:30:00-04:00",
        ),
        expected=second.fingerprint,
        transition_id="lct_fup_dup_b_invalidate",
        reason_code="recording_error",
        operation_id="op_fup_dup_b_invalidate",
    )
    invalidated_stored = service.resolve_exact(second_ref)
    successor = follow_up_consolidation_successor(
        (first.record, invalidated_stored.record),
    )

    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "fup_dup_a": first.fingerprint,
            "fup_dup_b": invalidated_stored.fingerprint,
        },
        transition_ids={
            "fup_dup_a": "lct_fup_dup_a_consolidate",
            "fup_dup_b": "lct_fup_dup_b_consolidate",
        },
        operation_id="op_fup_duplicate_with_invalidated",
    )

    assert service.resolve_exact(second_ref).record.status == "superseded"
    assert service.require_current_use(
        follow_up_reference(event_ref(), "fup_canonical")
    ).record.status == "active"


def test_follow_up_duplicate_consolidation_rejects_one_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(event_ref(), follow_up_record())
    successor = follow_up_consolidation_successor((created.record,))

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two follow_up predecessors",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"fup_alpha": created.fingerprint},
            transition_ids={"fup_alpha": "lct_fup_only_duplicate"},
            operation_id="op_fup_bad_single_duplicate",
        )


def test_follow_up_duplicate_consolidation_requires_complete_expected_map(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_a"),
    )
    second = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_b"),
    )
    successor = follow_up_consolidation_successor(
        (first.record, second.record),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="one expected fingerprint for every predecessor",
    ):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"fup_dup_a": first.fingerprint},
            transition_ids={
                "fup_dup_a": "lct_fup_dup_a",
                "fup_dup_b": "lct_fup_dup_b",
            },
            operation_id="op_fup_incomplete_duplicate_expected",
        )


def test_follow_up_duplicate_consolidation_successor_must_be_active(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_a"),
    )
    second = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_dup_b"),
    )
    successor = follow_up_consolidation_successor(
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
                "fup_dup_a": first.fingerprint,
                "fup_dup_b": second.fingerprint,
            },
            transition_ids={
                "fup_dup_a": "lct_fup_dup_a",
                "fup_dup_b": "lct_fup_dup_b",
            },
            operation_id="op_fup_inactive_duplicate_successor",
        )


def test_follow_up_work_root_correction_moves_event_record_to_support_process(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(
            purpose={"kind": "coordination"},
        ),
    )
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=support_ref(),
    )

    service.correct_work_root(
        predecessor,
        support_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_fup_move_to_support",
        operation_id="op_fup_move_to_support",
    )

    old_exact = service.resolve_exact(predecessor)
    new_reference = follow_up_reference(support_ref(), "fup_alpha")
    current = service.require_current_use(new_reference)
    assert old_exact.record.status == "superseded"
    assert old_exact.record.work_kind == "event"
    assert current.record.status == "active"
    assert current.record.work_kind == "support_process"
    assert current.record.logical_id == "fup_alpha"
    assert current.record.field("purpose") == old_exact.record.field("purpose")
    assert current.record.field("planned_timing") == old_exact.record.field(
        "planned_timing"
    )

    transition = repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_fup_move_to_support",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.to_dict()["reason"] == {
        "category": "correction",
        "code": "work_root_corrected",
    }


def test_follow_up_work_root_correction_moves_support_record_to_event(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        support_ref(),
        follow_up_record(
            work=support_ref(),
            follow_up_id="fup_support",
            purpose={"kind": "coordination"},
        ),
    )
    predecessor = follow_up_reference(support_ref(), "fup_support")
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=event_ref(),
    )

    service.correct_work_root(
        predecessor,
        event_ref(),
        successor,
        expected=created.fingerprint,
        transition_id="lct_fup_move_to_event",
        operation_id="op_fup_move_to_event",
    )

    assert service.resolve_exact(predecessor).record.status == "superseded"
    current = service.require_current_use(
        follow_up_reference(event_ref(), "fup_support")
    )
    assert current.record.status == "active"
    assert current.record.work_kind == "event"
    assert current.record.logical_id == "fup_support"


def test_follow_up_work_root_correction_cannot_rewrite_follow_up_fact(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(purpose={"kind": "coordination"}),
    )
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=support_ref(),
        planned_timing={"kind": "date_only", "date": "2026-09-07"},
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite fact planned_timing",
    ):
        service.correct_work_root(
            predecessor,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_bad_root_fact",
            operation_id="op_fup_bad_root_fact",
        )


def test_follow_up_work_root_correction_must_preserve_follow_up_id(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(purpose={"kind": "coordination"}),
    )
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=support_ref(),
        follow_up_id="fup_different",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="must preserve follow_up identity",
    ):
        service.correct_work_root(
            predecessor,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_bad_root_id",
            operation_id="op_fup_bad_root_id",
        )


def test_follow_up_work_root_correction_requires_current_expected_predecessor(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        follow_up_record(purpose={"kind": "coordination"}),
    )
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    progressed = service.transition_workflow_state(
        predecessor,
        follow_up_revision(
            created.record,
            workflow_state="in_progress",
            updated_at=PROGRESSED,
        ),
        expected=created.fingerprint,
    )
    successor = follow_up_work_root_successor(
        progressed.record,
        destination_work=support_ref(),
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected predecessor action state",
    ):
        service.correct_work_root(
            predecessor,
            support_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_fup_stale_root_move",
            operation_id="op_fup_stale_root_move",
        )


def test_follow_up_workflow_progresses_scheduled_to_in_progress(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state="in_progress",
    )
    accepted = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        candidate,
        expected=prior.fingerprint,
    )
    assert accepted.record.field("workflow_state") == "in_progress"
    assert accepted.record.field("completed_at") is None


def test_follow_up_workflow_can_complete_directly_from_scheduled(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state="completed",
        completed_at=COMPLETED,
    )
    accepted = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        candidate,
        expected=prior.fingerprint,
    )
    assert accepted.record.field("workflow_state") == "completed"
    assert accepted.record.field("completed_at") == COMPLETED


def test_follow_up_workflow_completes_after_in_progress(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(event_ref(), follow_up_record())
    in_progress = follow_up_revision(
        first.record,
        workflow_state="in_progress",
    )
    progressed = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        in_progress,
        expected=first.fingerprint,
    )
    completed = follow_up_revision(
        progressed.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
    )
    accepted = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        completed,
        expected=progressed.fingerprint,
    )
    assert accepted.record.field("workflow_state") == "completed"


@pytest.mark.parametrize("terminal", ["cancelled", "unable_to_complete"])
def test_follow_up_workflow_supports_noncompletion_terminal_states(
    tmp_path: Path,
    terminal: str,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state=terminal,
    )
    accepted = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        candidate,
        expected=prior.fingerprint,
    )
    assert accepted.record.field("workflow_state") == terminal
    assert accepted.record.field("completed_at") is None


def test_terminal_follow_up_requires_successor_history_for_fact_change(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(event_ref(), follow_up_record())
    completed = follow_up_revision(
        first.record,
        workflow_state="completed",
        completed_at=COMPLETED,
    )
    terminal = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        completed,
        expected=first.fingerprint,
    )
    attempted = follow_up_revision(
        terminal.record,
        workflow_state="cancelled",
        updated_at="2026-09-04T10:20:00-04:00",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="illegal Follow-Up"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            attempted,
            expected=terminal.fingerprint,
        )


def test_follow_up_workflow_progression_cannot_change_canonical_status(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state="in_progress",
        status="invalidated",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="canonical lifecycle"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            candidate,
            expected=prior.fingerprint,
        )


def test_follow_up_workflow_progression_cannot_rewrite_purpose(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state="in_progress",
        purpose={"kind": "event_review"},
    )
    with pytest.raises(WorkflowPrerequisiteError, match="field purpose"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            candidate,
            expected=prior.fingerprint,
        )


def test_follow_up_workflow_progression_rejects_stale_expected_state(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    first = service.create(event_ref(), follow_up_record())
    in_progress = follow_up_revision(
        first.record,
        workflow_state="in_progress",
    )
    progressed = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_alpha"),
        in_progress,
        expected=first.fingerprint,
    )
    completed = follow_up_revision(
        progressed.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
    )
    with pytest.raises(PortiaConflictError, match="canonical bytes"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            completed,
            expected=first.fingerprint,
        )


def test_follow_up_workflow_updated_at_cannot_move_backward(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    candidate = follow_up_revision(
        prior.record,
        workflow_state="in_progress",
        updated_at=TIMESTAMP,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            candidate,
            expected=prior.fingerprint,
        )


def test_completion_can_append_reviewed_and_produced_exact_relations(
    tmp_path: Path,
) -> None:
    repository = seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)

    prior_follow_up = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_prior"),
    )
    produced_follow_up = service.create(
        event_ref(),
        follow_up_record(follow_up_id="fup_next"),
    )
    del produced_follow_up

    reviewed = {
        "role": "reviewed",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    produced = {
        "role": "produced",
        "record_ref": follow_up_reference(
            event_ref(),
            "fup_next",
        ).to_dict(),
    }
    completed = follow_up_revision(
        prior_follow_up.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
        related_records=[reviewed, produced],
    )

    accepted = service.transition_workflow_state(
        follow_up_reference(event_ref(), "fup_prior"),
        completed,
        expected=prior_follow_up.fingerprint,
    )
    assert accepted.record.to_dict()["related_records"] == [reviewed, produced]
    assert repository.load_work(event_ref()).record.status == "active"


def test_completion_preserves_existing_context_relation(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    context = {
        "role": "context",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    prior = service.create(
        event_ref(),
        follow_up_record(related_records=[context]),
    )
    completed = follow_up_revision(
        prior.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
        omit_related_records=True,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot remove"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            completed,
            expected=prior.fingerprint,
        )


def test_completion_cannot_add_new_context_relation(tmp_path: Path) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    context = {
        "role": "context",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    completed = follow_up_revision(
        prior.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
        related_records=[context],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="reviewed or produced"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            completed,
            expected=prior.fingerprint,
        )


def test_noncompletion_progression_cannot_add_related_records(
    tmp_path: Path,
) -> None:
    seed_event(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(event_ref(), follow_up_record())
    reviewed = {
        "role": "reviewed",
        "record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    }
    in_progress = follow_up_revision(
        prior.record,
        workflow_state="in_progress",
        related_records=[reviewed],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="field related_records"):
        service.transition_workflow_state(
            follow_up_reference(event_ref(), "fup_alpha"),
            in_progress,
            expected=prior.fingerprint,
        )


def test_support_review_completion_can_attach_disposition_without_mutating_root(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior_root = repository.load_work(support_ref())

    prior = service.create(
        support_ref(),
        follow_up_record(
            work=support_ref(),
            follow_up_id="fup_support_review",
            purpose={"kind": "support_process_review"},
        ),
    )

    completed = follow_up_revision(
        prior.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
        disposition={"kind": "continue_current_support"},
    )
    accepted = service.transition_workflow_state(
        follow_up_reference(support_ref(), "fup_support_review"),
        completed,
        expected=prior.fingerprint,
    )

    assert accepted.record.field("disposition") == {
        "kind": "continue_current_support"
    }
    after_root = repository.load_work(support_ref())
    assert after_root.fingerprint == prior_root.fingerprint
    assert after_root.record.field("workflow_state") == "active"


def test_completion_disposition_does_not_create_outcome_or_process_transition(
    tmp_path: Path,
) -> None:
    repository = seed_support(tmp_path)
    service = FollowUpWorkflowService(tmp_path)
    prior = service.create(
        support_ref(),
        follow_up_record(
            work=support_ref(),
            follow_up_id="fup_support_review",
            purpose={"kind": "support_process_review"},
        ),
    )
    completed = follow_up_revision(
        prior.record,
        workflow_state="completed",
        updated_at=COMPLETED,
        completed_at=COMPLETED,
        disposition={"kind": "complete_process"},
    )
    service.transition_workflow_state(
        follow_up_reference(support_ref(), "fup_support_review"),
        completed,
        expected=prior.fingerprint,
    )

    assert repository.list_work_records(
        support_ref(),
        "outcome",
        version="1",
    ) == ()
    root = repository.load_work(support_ref())
    assert root.record.field("workflow_state") == "active"


def test_reference_owner_must_be_exact_downstream_work(tmp_path: Path) -> None:
    seed_event(tmp_path)
    bad_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="1",
    )
    with pytest.raises(WorkflowOwnershipError, match="event@2"):
        FollowUpWorkflowService(tmp_path).load_exact(
            ExactPortiaWorkRecordRef(
                work_ref=bad_work,
                record_ref=follow_up_reference(
                    event_ref(),
                    "fup_missing",
                ).record_ref,
            )
        )
