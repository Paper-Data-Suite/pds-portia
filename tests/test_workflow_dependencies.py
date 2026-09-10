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
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    DependencyWorkflowService,
    LifecycleWorkflowService,
    dependency_reference,
    supported_record_lifecycle_contracts,
)
from portia.workflows.action_common import require_action_owner
from portia.workflows.dependency_lifecycle import (
    require_dependency_lifecycle_reconciled,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from tests.workflow_helpers import (
    AGENT,
    account_wire,
    event_record,
    event_ref,
    participant_record,
    role_record,
)

T0 = "2026-09-08T19:00:00-04:00"
T1 = "2026-09-08T19:05:00-04:00"


def _local_record_target(
    record_kind: str,
    record_id: str,
    version: str,
) -> dict[str, object]:
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": record_kind,
            "record_id": record_id,
            "contract_version": version,
        },
    }


def _work_target(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {
        "kind": "work",
        "work_kind": work.work_kind,
        "contract_version": work.contract_version,
    }


def _portia_work_dependency(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {"kind": "portia_work", "work_ref": work.to_dict()}


def _record_ref(
    work: ExactPortiaWorkRef,
    record_kind: str,
    record_id: str,
    version: str,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=record_kind,
            record_id=record_id,
            contract_version=version,
        ),
    )


def _portia_record_dependency(
    work: ExactPortiaWorkRef,
    record_kind: str,
    record_id: str,
    version: str,
) -> dict[str, object]:
    return {
        "kind": "portia_record",
        "work_record_ref": _record_ref(
            work,
            record_kind,
            record_id,
            version,
        ).to_dict(),
    }


def dependency_record(
    work: ExactPortiaWorkRef,
    *,
    dependency_id: str = "dep_alpha",
    status: str = "active",
    dependent: dict[str, object] | None = None,
    dependency: dict[str, object] | None = None,
    strength: str = "required",
    applies_to: str = "current_use",
    purpose: str = "workflow_prerequisite",
    created_at: str = T0,
    updated_at: str | None = None,
) -> PortiaRecord:
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "dependency",
        "module_id": "portia",
        "class_id": work.class_id,
        "work_id": work.work_id,
        "dependency_id": dependency_id,
        "status": status,
        "dependent": dependent or _work_target(work),
        "dependency": dependency or _portia_work_dependency(work),
        "strength": strength,
        "applies_to": applies_to,
        "purpose": purpose,
        "creation_source": {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at or created_at,
        "updated_by": AGENT,
    }
    return parse_portia_record("dependency", "1", data)


def _repository(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(created_at=T0, updated_at=T0))
    repository.create_work_record(
        work,
        participant_record(created_at=T0, updated_at=T0),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_beta",
            created_at=T0,
            updated_at=T0,
        ),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_gamma",
            created_at=T0,
            updated_at=T0,
        ),
    )
    return repository


def _service(tmp_path: Path) -> DependencyWorkflowService:
    repository = _repository(tmp_path)
    return DependencyWorkflowService(tmp_path, repository=repository)


def test_dependency_reference_is_exact() -> None:
    reference = dependency_reference(event_ref(), "dep_alpha")
    assert reference.record_ref.record_kind == "dependency"
    assert reference.record_ref.record_id == "dep_alpha"
    assert reference.record_ref.contract_version == "1"


def test_dependency_reference_rejects_noncurrent_owner_version() -> None:
    with pytest.raises(WorkflowOwnershipError, match="event@2"):
        dependency_reference(event_ref(version="1"), "dep_alpha")


def test_load_exact_and_list_do_not_follow_targets(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    record = dependency_record(
        work,
        dependency=_portia_record_dependency(
            event_ref(event_id="evt_missing"),
            "event_participant",
            "ep_missing",
            "3",
        ),
    )
    created = service.repository.create_work_record(work, record)
    reference = dependency_reference(work, "dep_alpha")

    assert service.load_exact(reference).fingerprint == created.fingerprint
    assert tuple(item.record.logical_id for item in service.list(work)) == ("dep_alpha",)


def test_resolve_local_dependent_and_portia_record_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    record = dependency_record(
        work,
        dependent=_local_record_target("event_participant", "ep_alpha", "3"),
        dependency=_portia_record_dependency(
            work,
            "event_participant",
            "ep_beta",
            "3",
        ),
    )
    service.repository.create_work_record(work, record)
    reference = dependency_reference(work, "dep_alpha")

    dependent = service.resolve_dependent(reference)
    target = service.resolve_dependency_target(reference)
    assert dependent.kind == "local_record"
    assert dependent.stored is not None
    assert dependent.stored.record.logical_id == "ep_alpha"
    assert target.kind == "portia_record"
    assert target.stored is not None
    assert target.stored.record.logical_id == "ep_beta"


def test_resolve_work_dependent_and_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    record = dependency_record(work)
    service.repository.create_work_record(work, record)

    reference = dependency_reference(work, "dep_alpha")
    dependent = service.resolve_dependent(reference)
    target = service.resolve_dependency_target(reference)
    assert dependent.kind == "work"
    assert dependent.stored is not None
    assert target.kind == "portia_work"
    assert target.stored is not None


def test_dependency_rejects_maintenance_target(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    record = dependency_record(
        work,
        dependency=_portia_record_dependency(
            work,
            "dependency",
            "dep_other",
            "1",
        ),
    )
    service.repository.create_work_record(work, record)

    with pytest.raises(WorkflowOwnershipError, match="maintenance/infrastructure"):
        service.load_exact(dependency_reference(work, "dep_alpha"))


def test_list_for_dependent_is_exact(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            dependency_id="dep_alpha",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
        ),
    )
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            dependency_id="dep_beta",
            dependent=_local_record_target("event_participant", "ep_beta", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_alpha",
                "3",
            ),
        ),
    )

    dependent = _record_ref(work, "event_participant", "ep_alpha", "3")
    assert tuple(
        item.record.logical_id for item in service.list_for_dependent(dependent)
    ) == ("dep_alpha",)


def test_list_incoming_uses_only_explicit_scope(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    target = _record_ref(work, "event_participant", "ep_beta", "3")
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
        ),
    )

    assert tuple(
        item.record.logical_id
        for item in service.list_incoming((work,), target)
    ) == ("dep_alpha",)
    with pytest.raises(WorkflowPrerequisiteError, match="at least one"):
        service.list_incoming((), target)


def test_graph_rejects_self_dependency(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(work, dependency_record(work))

    with pytest.raises(WorkflowPrerequisiteError, match="self-dependency"):
        service.require_graph_valid((work,))


def test_graph_rejects_direct_cycle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            dependency_id="dep_alpha",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
        ),
    )
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            dependency_id="dep_beta",
            dependent=_local_record_target("event_participant", "ep_beta", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_alpha",
                "3",
            ),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="cycle"):
        service.require_graph_valid((work,))


def test_graph_rejects_indirect_cycle(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    edges = (
        ("dep_alpha", "ep_alpha", "ep_beta"),
        ("dep_beta", "ep_beta", "ep_gamma"),
        ("dep_gamma", "ep_gamma", "ep_alpha"),
    )
    for dependency_id, source_id, target_id in edges:
        service.repository.create_work_record(
            work,
            dependency_record(
                work,
                dependency_id=dependency_id,
                dependent=_local_record_target(
                    "event_participant",
                    source_id,
                    "3",
                ),
                dependency=_portia_record_dependency(
                    work,
                    "event_participant",
                    target_id,
                    "3",
                ),
            ),
        )

    with pytest.raises(WorkflowPrerequisiteError, match="cycle"):
        service.require_graph_valid((work,))


def test_graph_rejects_duplicate_active_semantic_declaration(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    for dependency_id in ("dep_alpha", "dep_beta"):
        service.repository.create_work_record(
            work,
            dependency_record(
                work,
                dependency_id=dependency_id,
                dependent=_local_record_target(
                    "event_participant",
                    "ep_alpha",
                    "3",
                ),
                dependency=_portia_record_dependency(
                    work,
                    "event_participant",
                    "ep_beta",
                    "3",
                ),
            ),
        )

    with pytest.raises(WorkflowPrerequisiteError, match="duplicate active"):
        service.require_graph_valid((work,))


def test_graph_requires_explicit_cross_work_closure(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    other = event_ref(event_id="evt_beta")
    service.repository.create_work(
        other,
        event_record(event_id="evt_beta", created_at=T0, updated_at=T0),
    )
    service.repository.create_work_record(
        work,
        dependency_record(work, dependency=_portia_work_dependency(other)),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="scope is incomplete"):
        service.require_graph_valid((work,))
    resolution = service.require_graph_valid((work, other))
    assert resolution.live_edge_count == 1


def test_graph_detects_cross_work_cycle_in_explicit_scope(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = event_ref()
    second = event_ref(event_id="evt_beta")
    service.repository.create_work(
        second,
        event_record(event_id="evt_beta", created_at=T0, updated_at=T0),
    )
    service.repository.create_work_record(
        first,
        dependency_record(first, dependency=_portia_work_dependency(second)),
    )
    service.repository.create_work_record(
        second,
        dependency_record(
            second,
            dependency_id="dep_beta",
            dependency=_portia_work_dependency(first),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="cycle"):
        service.require_graph_valid((first, second))


def test_invalidated_historical_edge_is_not_live_cycle_authority(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="invalidated",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_alpha",
                "3",
            ),
        ),
    )

    resolution = service.require_graph_valid((work,))
    assert resolution.live_edge_count == 0


def _participant_dependency(
    work: ExactPortiaWorkRef,
    *,
    dependency_id: str = "dep_alpha",
    status: str = "proposed",
    dependent_id: str = "ep_alpha",
    target_id: str = "ep_beta",
    updated_at: str = T0,
) -> PortiaRecord:
    return dependency_record(
        work,
        dependency_id=dependency_id,
        status=status,
        dependent=_local_record_target("event_participant", dependent_id, "3"),
        dependency=_portia_record_dependency(
            work,
            "event_participant",
            target_id,
            "3",
        ),
        updated_at=updated_at,
    )


def test_dependency_lifecycle_empty_history_is_reconciled(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    stored = service.repository.create_work_record(
        work,
        _participant_dependency(work),
    )

    state = require_dependency_lifecycle_reconciled(
        service.repository,
        work,
        stored.record,
    )
    assert state.transitions == ()
    assert state.head is None
    assert state.selected_status is None


def test_dependency_activation_is_journaled_and_reconciled(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.repository.create_work_record(
        work,
        _participant_dependency(work),
    )
    candidate = _participant_dependency(work, status="active", updated_at=T1)

    service.transition_lifecycle(
        dependency_reference(work, "dep_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_dependency_active",
        reason_code="review_confirmed",
        operation_id="op_dependency_active",
    )

    accepted = service.load_exact(dependency_reference(work, "dep_alpha"))
    assert accepted.record.status == "active"
    state = require_dependency_lifecycle_reconciled(
        service.repository,
        work,
        accepted.record,
    )
    assert state.selected_status == "active"
    assert state.head is not None
    assert state.head.record.field("reason") == {
        "category": "workflow",
        "code": "review_confirmed",
    }
    journal = OperationJournalStore(tmp_path).load_current("op_dependency_active")
    assert journal.revision.field("operation_kind") == "transition_lifecycle"
    assert journal.revision.field("state") == "completed"


def test_dependency_activation_requires_review_confirmed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.repository.create_work_record(
        work,
        _participant_dependency(work),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="review_confirmed"):
        service.transition_lifecycle(
            dependency_reference(work, "dep_alpha"),
            _participant_dependency(work, status="active", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_dependency_bad_active",
            reason_code="teacher_confirmed",
            operation_id="op_dependency_bad_active",
        )


def test_dependency_activation_rejects_conflicting_active_condition(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(
            work,
            dependency_id="dep_existing",
            status="active",
        ),
    )
    prior = service.repository.create_work_record(
        work,
        _participant_dependency(work),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="existing active semantic"):
        service.transition_lifecycle(
            dependency_reference(work, "dep_alpha"),
            _participant_dependency(work, status="active", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_dependency_duplicate_active",
            reason_code="review_confirmed",
            operation_id="op_dependency_duplicate_active",
        )


def test_dependency_invalidation_is_journaled_without_cascade(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )
    candidate = _participant_dependency(work, status="invalidated", updated_at=T1)

    service.transition_lifecycle(
        dependency_reference(work, "dep_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_dependency_invalidated",
        reason_code="entered_in_error",
        operation_id="op_dependency_invalidated",
    )

    accepted = service.load_exact(dependency_reference(work, "dep_alpha"))
    assert accepted.record.status == "invalidated"
    state = require_dependency_lifecycle_reconciled(
        service.repository,
        work,
        accepted.record,
    )
    assert state.selected_status == "invalidated"
    assert state.head is not None
    assert state.head.record.field("reason") == {
        "category": "record_validity",
        "code": "entered_in_error",
    }
    assert service.repository.load_work_record(
        work,
        "event_participant",
        "3",
        "ep_alpha",
    ).record.status == "active"


def test_dependency_ordinary_lifecycle_cannot_supersede(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="correction or consolidation"):
        service.transition_lifecycle(
            dependency_reference(work, "dep_alpha"),
            _participant_dependency(work, status="superseded", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_dependency_superseded",
            reason_code="dependency_target_corrected",
            operation_id="op_dependency_superseded",
        )


def test_dependency_action_owner_gate_accepts_current_work_roots() -> None:
    work = event_ref()
    require_action_owner(work, contract="dependency")
    require_action_owner(
        ExactPortiaWorkRef(
            class_id=work.class_id,
            work_id="sup_alpha",
            work_kind="support_process",
            contract_version="1",
        ),
        contract="dependency",
    )
    with pytest.raises(WorkflowOwnershipError, match="event@2 or support_process@1"):
        require_action_owner(event_ref(version="1"), contract="dependency")


def test_generic_lifecycle_reads_dependency_but_does_not_yet_dispatch_mutation(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    stored = service.repository.create_work_record(
        work,
        _participant_dependency(work),
    )
    lifecycle = LifecycleWorkflowService(
        tmp_path,
        repository=service.repository,
    )

    assert ("dependency", "1") in supported_record_lifecycle_contracts()
    assert ("dependency", "1") not in lifecycle.supported_transition_contracts()
    resolution = lifecycle.load_history(dependency_reference(work, "dep_alpha"))
    assert resolution.record_id == "dep_alpha"
    assert resolution.canonical_status == stored.record.status
    assert resolution.selected_status is None



def test_dependency_activation_cross_work_requires_explicit_graph_closure(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    other = event_ref(event_id="evt_beta")
    service.repository.create_work(
        other,
        event_record(event_id="evt_beta", created_at=T0, updated_at=T0),
    )
    prior_record = dependency_record(
        work,
        status="proposed",
        dependency=_portia_work_dependency(other),
    )
    prior = service.repository.create_work_record(work, prior_record)
    candidate = dependency_record(
        work,
        status="active",
        dependency=_portia_work_dependency(other),
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="scope is incomplete"):
        service.transition_lifecycle(
            dependency_reference(work, "dep_alpha"),
            candidate,
            expected=prior.fingerprint,
            transition_id="lct_dependency_cross_work_missing_scope",
            reason_code="review_confirmed",
            operation_id="op_dependency_cross_work_missing_scope",
        )

    service.transition_lifecycle(
        dependency_reference(work, "dep_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_dependency_cross_work_active",
        reason_code="review_confirmed",
        operation_id="op_dependency_cross_work_active",
        graph_works=(work, other),
    )
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.status == "active"


def test_dependency_create_persists_fresh_proposed_declaration(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()

    created = service.create(work, _participant_dependency(work))

    assert created.record.logical_id == "dep_alpha"
    assert created.record.status == "proposed"
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).fingerprint == created.fingerprint


def test_dependency_create_accepts_active_declaration_after_full_preflight(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()

    created = service.create(
        work,
        _participant_dependency(work, status="active"),
    )

    assert created.record.status == "active"
    assert service.require_graph_valid((work,)).live_edge_count == 1


def test_dependency_create_rejects_nonfresh_lifecycle_state(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()

    with pytest.raises(WorkflowPrerequisiteError, match="begin proposed or active"):
        service.create(
            work,
            _participant_dependency(work, status="invalidated"),
        )
    assert service.list(work) == ()


def test_dependency_create_rejects_advisory_authorization_basis(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_local_record_target("event_participant", "ep_alpha", "3"),
        dependency=_portia_record_dependency(
            work,
            "event_participant",
            "ep_beta",
            "3",
        ),
        strength="advisory",
        purpose="authorization_basis",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="requires required strength"):
        service.create(work, candidate)
    assert service.list(work) == ()


def test_dependency_create_rejects_completion_scope_on_child_record(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_local_record_target("event_participant", "ep_alpha", "3"),
        dependency=_portia_record_dependency(
            work,
            "event_participant",
            "ep_beta",
            "3",
        ),
        applies_to="completion",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="not supported for this child"):
        service.create(work, candidate)
    assert service.list(work) == ()


def test_dependency_create_allows_event_completion_scope(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_work_target(work),
        dependency=_portia_record_dependency(
            work,
            "event_participant",
            "ep_beta",
            "3",
        ),
        applies_to="completion",
    )

    created = service.create(work, candidate)
    assert created.record.field("applies_to") == "completion"


def test_dependency_create_rejects_intrinsic_role_basis_duplicate(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    account = parse_portia_record("account", "1", account_wire())
    service.repository.create_work_record(work, account)
    service.repository.create_work_record(
        work,
        role_record(
            role_type="reported_involved",
            basis=[
                {
                    "kind": "account_ref",
                    "record_ref": {
                        "record_kind": "account",
                        "record_id": "acct_alpha",
                        "contract_version": "1",
                    },
                }
            ],
        ),
    )
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_local_record_target("event_participant_role", "epr_alpha", "3"),
        dependency=_portia_record_dependency(
            work,
            "account",
            "acct_alpha",
            "1",
        ),
        purpose="evidentiary_support",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="intrinsic.*Role basis"):
        service.create(work, candidate)
    assert service.list(work) == ()


def test_dependency_create_rejects_self_dependency_before_write(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()

    with pytest.raises(WorkflowPrerequisiteError, match="self-dependent"):
        service.create(
            work,
            dependency_record(work, status="proposed"),
        )
    assert service.list(work) == ()


def test_dependency_create_requires_explicit_cross_work_graph_closure(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    other = event_ref(event_id="evt_beta")
    service.repository.create_work(
        other,
        event_record(event_id="evt_beta", created_at=T0, updated_at=T0),
    )
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_local_record_target("event_participant", "ep_alpha", "3"),
        dependency=_portia_work_dependency(other),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="scope is incomplete"):
        service.create(work, candidate)
    assert service.list(work) == ()

    created = service.create(work, candidate, graph_works=(work, other))
    assert created.record.logical_id == "dep_alpha"


def test_dependency_create_rejects_cycle_before_canonical_write(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(
            work,
            dependency_id="dep_existing",
            status="active",
            dependent_id="ep_beta",
            target_id="ep_alpha",
        ),
    )
    candidate = _participant_dependency(
        work,
        dependency_id="dep_alpha",
        status="proposed",
        dependent_id="ep_alpha",
        target_id="ep_beta",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="introduce a cycle"):
        service.create(work, candidate)
    assert tuple(item.record.logical_id for item in service.list(work)) == (
        "dep_existing",
    )


def test_dependency_create_rejects_duplicate_active_condition_before_write(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(
            work,
            dependency_id="dep_existing",
            status="active",
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="existing active semantic"):
        service.create(
            work,
            _participant_dependency(
                work,
                dependency_id="dep_alpha",
                status="active",
            ),
        )
    assert tuple(item.record.logical_id for item in service.list(work)) == (
        "dep_existing",
    )


def test_dependency_module_read_uses_exact_core_reference_shape(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    module_target: dict[str, object] = {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "pds-scoreform",
                "class_id": work.class_id,
                "work_id": "work_assessment_001",
            },
            "record_ref": {
                "module_id": "pds-scoreform",
                "record_kind": "score_result",
                "record_id": "score_001",
                "contract_version": "1",
            },
        },
    }
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="proposed",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=module_target,
        ),
    )

    resolved = service.resolve_dependency_target(
        dependency_reference(work, "dep_alpha")
    )
    assert resolved.kind == "module_record"
    assert resolved.stored is None


def test_dependency_create_fails_closed_for_sibling_module_target(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    module_target: dict[str, object] = {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "pds-scoreform",
                "class_id": work.class_id,
                "work_id": "work_assessment_001",
            },
            "record_ref": {
                "module_id": "pds-scoreform",
                "record_kind": "score_result",
                "record_id": "score_001",
                "contract_version": "1",
            },
        },
    }
    candidate = dependency_record(
        work,
        status="proposed",
        dependent=_local_record_target("event_participant", "ep_alpha", "3"),
        dependency=module_target,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="producer compatibility"):
        service.create(work, candidate)
    assert service.list(work) == ()


def test_dependency_module_read_rejects_module_id_mismatch(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    module_target: dict[str, object] = {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "pds-scoreform",
                "class_id": work.class_id,
                "work_id": "work_assessment_001",
            },
            "record_ref": {
                "module_id": "pds-quillan",
                "record_kind": "score_result",
                "record_id": "score_001",
                "contract_version": "1",
            },
        },
    }
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="proposed",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=module_target,
        ),
    )

    with pytest.raises(WorkflowOwnershipError, match="disagree on module_id"):
        service.load_exact(dependency_reference(work, "dep_alpha"))


def _replace_participant_status(
    service: DependencyWorkflowService,
    participant_id: str,
    *,
    status: str,
    created_at: str = T0,
    updated_at: str = T1,
) -> None:
    work = event_ref()
    prior = service.repository.load_work_record(
        work,
        "event_participant",
        "3",
        participant_id,
    )
    service.repository.replace_work_record(
        work,
        participant_record(
            participant_id=participant_id,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
        ),
        expected=prior.fingerprint,
    )


def _active_disagreement_for_participant(
    participant_id: str,
    *,
    disagreement_id: str = "sod_dependency_target",
) -> PortiaRecord:
    return parse_portia_record(
        "statement_of_disagreement",
        "1",
        {
            "schema_version": "1",
            "record_type": "statement_of_disagreement",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "disagreement_id": disagreement_id,
            "status": "active",
            "target": _local_record_target(
                "event_participant",
                participant_id,
                "3",
            ),
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic represented source",
            },
            "positions": ["disputes_accuracy"],
            "statement": {
                "representation": "recorded_summary",
                "text": "Synthetic disagreement for dependency evaluation.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": T0,
            "updated_by": AGENT,
        },
    )


def test_dependency_condition_inactive_declaration_is_not_currently_evaluated(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="proposed"),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "not_currently_evaluated"
    assert evaluation.reason == "declaration_not_active"


def test_dependency_condition_scope_mismatch_is_not_currently_evaluated(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "not_currently_evaluated"
    assert evaluation.reason == "scope_not_selected"


def test_dependency_condition_active_exact_target_is_satisfied(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "satisfied"
    assert evaluation.reason == "target_status_satisfies_initial_policy"


def test_dependency_condition_invalidated_target_is_unsatisfied(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(service, "ep_beta", status="invalidated")
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "unsatisfied"
    assert evaluation.reason == "target_status_is_ineligible"


def test_dependency_condition_superseded_target_requires_review(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(service, "ep_beta", status="superseded")
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "review_required"
    assert evaluation.reason == "target_status_requires_review"


def test_dependency_condition_missing_exact_target_is_unsatisfied(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(
            work,
            status="active",
            target_id="ep_missing",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "unsatisfied"
    assert evaluation.reason == "exact_target_missing"


def test_dependency_condition_unsupported_exact_contract_is_indeterminate(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "99",
            ),
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "indeterminate"
    assert evaluation.reason == "target_contract_policy_unavailable"


def test_dependency_condition_sibling_module_semantics_are_indeterminate(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    module_target: dict[str, object] = {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "pds-scoreform",
                "class_id": work.class_id,
                "work_id": "work_assessment_001",
            },
            "record_ref": {
                "module_id": "pds-scoreform",
                "record_kind": "score_result",
                "record_id": "score_001",
                "contract_version": "1",
            },
        },
    }
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=module_target,
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "indeterminate"
    assert evaluation.reason == "external_module_semantics_unavailable"


def test_dependency_condition_active_disagreement_requires_review(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )
    service.repository.create_work_record(
        work,
        _active_disagreement_for_participant("ep_beta"),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="current_use",
    )
    assert evaluation.condition == "review_required"
    assert evaluation.reason == "target_has_active_disagreement"


def test_dependency_gate_required_unsatisfied_condition_blocks(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(service, "ep_beta", status="invalidated")
    service.repository.create_work_record(
        work,
        _participant_dependency(work, status="active"),
    )

    gate = service.evaluate_gate(
        _record_ref(work, "event_participant", "ep_alpha", "3"),
        gate="current_use",
    )
    assert gate.required_gate_satisfied is False
    assert gate.required_blockers == ("dep_alpha",)
    assert gate.advisory_attention == ()


def test_dependency_gate_advisory_condition_surfaces_attention_without_blocking(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(service, "ep_beta", status="invalidated")
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            strength="advisory",
            purpose="contextual_support",
        ),
    )

    gate = service.evaluate_gate(
        _record_ref(work, "event_participant", "ep_alpha", "3"),
        gate="current_use",
    )
    assert gate.required_gate_satisfied is True
    assert gate.required_blockers == ()
    assert gate.advisory_attention == ("dep_alpha",)


def test_dependency_activation_gate_requires_exact_temporal_context(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="activation",
    )
    assert evaluation.condition == "indeterminate"
    assert evaluation.reason == "exact_temporal_context_required"


def test_dependency_activation_gate_satisfies_current_revision_at_effective_time(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="activation",
        evaluated_at=T0,
    )
    assert evaluation.condition == "satisfied"


def test_dependency_activation_gate_refuses_future_target_revision(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(
        service,
        "ep_beta",
        status="active",
        created_at=T0,
        updated_at=T1,
    )
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="activation",
        evaluated_at=T0,
    )
    assert evaluation.condition == "indeterminate"
    assert evaluation.reason == "target_revision_postdates_evaluation"


def test_dependency_gate_scope_mismatch_does_not_block(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    gate = service.evaluate_gate(
        _record_ref(work, "event_participant", "ep_alpha", "3"),
        gate="current_use",
    )
    assert gate.required_gate_satisfied is True
    assert gate.required_blockers == ()
    assert gate.conditions[0].condition == "not_currently_evaluated"


def test_dependency_activation_gate_knows_target_did_not_yet_exist(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    _replace_participant_status(
        service,
        "ep_beta",
        status="active",
        created_at=T1,
        updated_at=T1,
    )
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_alpha"),
        gate="activation",
        evaluated_at=T0,
    )
    assert evaluation.condition == "unsatisfied"
    assert evaluation.reason == "target_not_yet_created"


def test_dependency_required_indeterminate_condition_blocks_selected_gate(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        dependency_record(
            work,
            status="active",
            dependent=_local_record_target("event_participant", "ep_alpha", "3"),
            dependency=_portia_record_dependency(
                work,
                "event_participant",
                "ep_beta",
                "3",
            ),
            applies_to="activation",
        ),
    )

    gate = service.evaluate_gate(
        _record_ref(work, "event_participant", "ep_alpha", "3"),
        gate="activation",
    )
    assert gate.required_gate_satisfied is False
    assert gate.required_blockers == ("dep_alpha",)
    assert gate.conditions[0].condition == "indeterminate"


def test_dependency_gate_rejects_unknown_gate(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()

    with pytest.raises(WorkflowPrerequisiteError, match="unsupported Dependency gate"):
        service.evaluate_gate(
            _record_ref(work, "event_participant", "ep_alpha", "3"),
            gate="retirement",
        )
