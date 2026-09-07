from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.repository import PortiaRepository
from portia.workflows.action_common import require_action_owner
from portia.workflows.downstream_common import DownstreamWorkflowAuthority
from portia.workflows.downstream_supersession import (
    DOWNSTREAM_CORRECTION_REASONS,
    downstream_supersession_topology,
    require_downstream_work_root_correction_predecessor,
    require_duplicate_downstream_consolidation_predecessors,
    require_exact_downstream_correction_predecessor,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

TIMESTAMP = "2026-09-04T10:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue46_slice1b_test"}


def event_ref(
    *,
    work_id: str = "evt_alpha",
    class_id: str = "class_a",
    version: str = "2",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="event",
        contract_version=version,
    )


def support_process_ref(
    *,
    work_id: str = "sup_alpha",
    class_id: str = "class_a",
    version: str = "1",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version=version,
    )


def event_record(
    *,
    work_id: str = "evt_alpha",
    class_id: str = "class_a",
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
            "work_id": work_id,
            "school_year": "2026-2027",
            "status": "active",
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
            "occurrence": {"precision": "exact", "started_at": TIMESTAMP},
            "summary": "Synthetic event for Issue #46 Slice 1b.",
        },
    )


def event_participant_record(
    *,
    participant_id: str = "ep_alpha",
    work_id: str = "evt_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": work_id,
            "participant_id": participant_id,
            "status": "active",
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


def exact_record_ref(
    work: ExactPortiaWorkRef,
    kind: str,
    record_id: str,
    *,
    version: str = "1",
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=kind,
            record_id=record_id,
            contract_version=version,
        ),
    )


def follow_up_record(
    *,
    record_id: str,
    work: ExactPortiaWorkRef | None = None,
    status: str = "active",
    supersedes: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    owner = work or event_ref()
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "follow_up",
        "module_id": "portia",
        "class_id": owner.class_id,
        "work_kind": owner.work_kind,
        "work_id": owner.work_id,
        "follow_up_id": record_id,
        "status": status,
        "target": {"kind": owner.work_kind},
        "purpose": {"kind": "event_review"},
        "planned_timing": {"kind": "date_only", "date": "2026-09-10"},
        "workflow_state": "scheduled",
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if owner.work_kind == "event":
        data["owner"] = {
            "kind": "represented_human",
            "person": {
                "kind": "local_operator",
                "display_label": "Synthetic teacher",
            },
        }
    else:
        data["owner"] = {
            "kind": "support_process_participant",
            "participant_ref": {
                "record_kind": "support_process_participant",
                "record_id": "spp_alpha",
                "contract_version": "1",
            },
        }
        data["purpose"] = {"kind": "support_process_review"}
    if supersedes is not None:
        data["supersedes"] = supersedes
    return parse_portia_record("follow_up", "1", data)


@pytest.mark.parametrize(
    "contract",
    ["follow_up", "outcome", "reentry", "repair"],
)
@pytest.mark.parametrize("work", [event_ref(), support_process_ref()])
def test_shared_persistence_owner_gate_accepts_all_downstream_families(
    contract: str,
    work: ExactPortiaWorkRef,
) -> None:
    require_action_owner(work, contract=contract)


@pytest.mark.parametrize(
    ("work", "contract"),
    [
        (event_ref(version="1"), "follow_up"),
        (support_process_ref(version="2"), "repair"),
    ],
)
def test_shared_persistence_owner_gate_remains_version_exact(
    work: ExactPortiaWorkRef,
    contract: str,
) -> None:
    with pytest.raises(WorkflowOwnershipError, match="event@2"):
        require_action_owner(work, contract=contract)


def test_exact_related_record_resolution_loads_named_revision_only(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), event_participant_record())
    authority = DownstreamWorkflowAuthority(tmp_path)
    reference = exact_record_ref(
        event_ref(),
        "event_participant",
        "ep_alpha",
        version="3",
    )

    resolution = authority.resolve_exact_work_record(
        event_ref(),
        reference.to_dict(),
        field_name="related record",
    )

    assert resolution.reference == reference
    assert resolution.stored.record.logical_id == "ep_alpha"
    assert resolution.stored.record.contract_version == "3"


def test_related_record_set_guards_identity_role_self_and_scope(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), event_participant_record())
    authority = DownstreamWorkflowAuthority(tmp_path)
    participant_ref = exact_record_ref(
        event_ref(),
        "event_participant",
        "ep_alpha",
        version="3",
    )
    policy = {"context": frozenset({"event_participant"})}
    item = {"role": "context", "record_ref": participant_ref.to_dict()}

    resolved = authority.resolve_related_records(
        event_ref(),
        [item],
        field_name="related_records",
        allowed_roles=frozenset({"context"}),
        role_contracts=policy,
    )
    assert resolved[0].role == "context"
    assert resolved[0].reference == participant_ref

    with pytest.raises(WorkflowPrerequisiteError, match="repeat"):
        authority.resolve_related_records(
            event_ref(),
            [item, item],
            field_name="related_records",
            allowed_roles=frozenset({"context"}),
            role_contracts=policy,
        )

    distinct_roles = authority.resolve_related_records(
        event_ref(),
        [
            item,
            {"role": "reviewed", "record_ref": participant_ref.to_dict()},
        ],
        field_name="related_records",
        allowed_roles=frozenset({"context", "reviewed"}),
        role_contracts={
            "context": frozenset({"event_participant"}),
            "reviewed": frozenset({"event_participant"}),
        },
    )
    assert tuple(value.role for value in distinct_roles) == ("context", "reviewed")

    with pytest.raises(WorkflowPrerequisiteError, match="incompatible"):
        authority.resolve_related_records(
            event_ref(),
            [item],
            field_name="related_records",
            allowed_roles=frozenset({"context"}),
            role_contracts={"context": frozenset({"response"})},
        )

    with pytest.raises(WorkflowPrerequisiteError, match="itself"):
        authority.resolve_related_records(
            event_ref(),
            [
                {
                    "role": "context",
                    "record_ref": exact_record_ref(
                        event_ref(), "follow_up", "fup_self"
                    ).to_dict(),
                }
            ],
            field_name="related_records",
            allowed_roles=frozenset({"context"}),
            role_contracts={"context": frozenset({"follow_up"})},
            self_reference=exact_record_ref(
                event_ref(), "follow_up", "fup_self"
            ),
        )

    with pytest.raises(WorkflowOwnershipError, match="owning work"):
        authority.resolve_related_records(
            event_ref(),
            [
                {
                    "role": "produced",
                    "record_ref": exact_record_ref(
                        event_ref(work_id="evt_beta"),
                        "event_participant",
                        "ep_beta",
                        version="3",
                    ).to_dict(),
                }
            ],
            field_name="related_records",
            allowed_roles=frozenset({"produced"}),
            role_contracts={"produced": frozenset({"event_participant"})},
            same_work_roles=frozenset({"produced"}),
        )


def test_related_record_set_rejects_cross_class_before_resolution(
    tmp_path: Path,
) -> None:
    authority = DownstreamWorkflowAuthority(tmp_path)
    with pytest.raises(WorkflowOwnershipError, match="owning class"):
        authority.resolve_related_records(
            event_ref(),
            [
                {
                    "role": "context",
                    "record_ref": exact_record_ref(
                        event_ref(class_id="class_b"),
                        "event_participant",
                        "ep_other",
                        version="3",
                    ).to_dict(),
                }
            ],
            field_name="related_records",
            allowed_roles=frozenset({"context"}),
            role_contracts={"context": frozenset({"event_participant"})},
        )


def test_frozen_correction_vocabularies_are_family_specific() -> None:
    assert "owner_corrected" in DOWNSTREAM_CORRECTION_REASONS["follow_up"]
    assert "evaluator_corrected" in DOWNSTREAM_CORRECTION_REASONS["outcome"]
    assert "coordinator_corrected" in DOWNSTREAM_CORRECTION_REASONS["reentry"]
    assert "facilitator_corrected" in DOWNSTREAM_CORRECTION_REASONS["repair"]
    assert "owner_corrected" not in DOWNSTREAM_CORRECTION_REASONS["outcome"]


def test_ordinary_correction_requires_one_exact_same_work_predecessor() -> None:
    prior = exact_record_ref(event_ref(), "follow_up", "fup_prior")
    successor = follow_up_record(
        record_id="fup_next",
        supersedes=[
            {
                "work_record_ref": prior.to_dict(),
                "reason": "timing_corrected",
            }
        ],
    )
    assert (
        require_exact_downstream_correction_predecessor(
            event_ref(),
            prior,
            successor,
        )
        == "timing_corrected"
    )

    wrong = exact_record_ref(event_ref(), "follow_up", "fup_wrong")
    with pytest.raises(WorkflowOwnershipError, match="exact selected predecessor"):
        require_exact_downstream_correction_predecessor(
            event_ref(),
            wrong,
            successor,
        )


def test_duplicate_consolidation_requires_multiple_same_work_predecessors() -> None:
    refs = [
        exact_record_ref(event_ref(), "follow_up", "fup_a"),
        exact_record_ref(event_ref(), "follow_up", "fup_b"),
    ]
    successor = follow_up_record(
        record_id="fup_merged",
        supersedes=[
            {
                "work_record_ref": reference.to_dict(),
                "reason": "duplicate_consolidated",
            }
            for reference in refs
        ],
    )
    assert (
        require_duplicate_downstream_consolidation_predecessors(
            event_ref(),
            successor,
        )
        == tuple(refs)
    )

    one = follow_up_record(
        record_id="fup_bad_merge",
        supersedes=[
            {
                "work_record_ref": refs[0].to_dict(),
                "reason": "duplicate_consolidated",
            }
        ],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="two"):
        require_duplicate_downstream_consolidation_predecessors(
            event_ref(),
            one,
        )


def test_work_root_correction_is_one_to_one_and_preserves_identity() -> None:
    source = event_ref()
    destination = support_process_ref()
    predecessor = exact_record_ref(source, "follow_up", "fup_move")
    successor = follow_up_record(
        record_id="fup_move",
        work=destination,
        supersedes=[
            {
                "work_record_ref": predecessor.to_dict(),
                "reason": "work_root_corrected",
            }
        ],
    )
    assert (
        require_downstream_work_root_correction_predecessor(
            destination,
            predecessor,
            successor,
        )
        == source
    )

    changed_id = follow_up_record(
        record_id="fup_changed",
        work=destination,
        supersedes=[
            {
                "work_record_ref": predecessor.to_dict(),
                "reason": "work_root_corrected",
            }
        ],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="preserve"):
        downstream_supersession_topology(changed_id)


def test_supersession_rejects_mixed_reasons_and_self_reference() -> None:
    first = exact_record_ref(event_ref(), "follow_up", "fup_a")
    second = exact_record_ref(event_ref(), "follow_up", "fup_b")
    mixed = follow_up_record(
        record_id="fup_next",
        supersedes=[
            {
                "work_record_ref": first.to_dict(),
                "reason": "timing_corrected",
            },
            {
                "work_record_ref": second.to_dict(),
                "reason": "purpose_corrected",
            },
        ],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="mixed"):
        downstream_supersession_topology(mixed)

    self_ref = exact_record_ref(event_ref(), "follow_up", "fup_self")
    self_successor = follow_up_record(
        record_id="fup_self",
        supersedes=[
            {
                "work_record_ref": self_ref.to_dict(),
                "reason": "timing_corrected",
            }
        ],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="itself"):
        downstream_supersession_topology(self_successor)
