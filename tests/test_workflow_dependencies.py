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
from tests.workflow_helpers import AGENT, event_record, event_ref, participant_record

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
