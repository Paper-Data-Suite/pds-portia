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
from portia.workflows import DependencyWorkflowService, dependency_reference
from portia.workflows.errors import WorkflowPrerequisiteError
from tests.workflow_helpers import AGENT, event_record, event_ref, participant_record

T0 = "2026-09-09T18:00:00-04:00"
T1 = "2026-09-09T18:10:00-04:00"
T2 = "2026-09-09T18:20:00-04:00"


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


def _supersession_edge(
    work: ExactPortiaWorkRef,
    predecessor_id: str,
    reason: str,
    *,
    detail: str | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "work_record_ref": dependency_reference(work, predecessor_id).to_dict(),
        "reason": reason,
    }
    if detail is not None:
        value["detail"] = detail
    return value


def _dependency(
    work: ExactPortiaWorkRef,
    *,
    dependency_id: str,
    status: str = "active",
    dependent_id: str = "ep_alpha",
    target_id: str = "ep_beta",
    strength: str = "required",
    applies_to: str = "current_use",
    purpose: str = "workflow_prerequisite",
    detail: str | None = None,
    supersedes: list[dict[str, object]] | None = None,
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
        "dependent": _local_record_target(
            "event_participant",
            dependent_id,
            "3",
        ),
        "dependency": _portia_record_dependency(
            work,
            "event_participant",
            target_id,
            "3",
        ),
        "strength": strength,
        "applies_to": applies_to,
        "purpose": purpose,
        "creation_source": {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at or created_at,
        "updated_by": AGENT,
    }
    if detail is not None:
        data["detail"] = detail
    if supersedes is not None:
        data["supersedes"] = supersedes
    return parse_portia_record("dependency", "1", data)


def _service(tmp_path: Path) -> DependencyWorkflowService:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(created_at=T0, updated_at=T0))
    for participant_id in ("ep_alpha", "ep_beta", "ep_gamma"):
        repository.create_work_record(
            work,
            participant_record(
                participant_id=participant_id,
                created_at=T0,
                updated_at=T0,
            ),
        )
    return DependencyWorkflowService(tmp_path, repository=repository)


def test_dependency_correction_is_journaled_reconciled_and_exact(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(work, "dep_alpha", "dependency_target_corrected")
        ],
        created_at=T1,
        updated_at=T1,
    )

    service.correct(
        dependency_reference(work, "dep_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_dep_alpha_superseded",
        operation_id="op_dependency_correction",
    )

    predecessor = service.load_exact(dependency_reference(work, "dep_alpha"))
    accepted_successor = service.load_exact(
        dependency_reference(work, "dep_successor")
    )
    transition = service.repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_dep_alpha_superseded",
    )
    assert predecessor.record.logical_id == "dep_alpha"
    assert predecessor.record.status == "superseded"
    assert accepted_successor.record.logical_id == "dep_successor"
    assert accepted_successor.record.status == "active"
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "dependency_target_corrected",
    }
    assert service.require_graph_valid((work,)).live_edge_count == 1
    assert service.repository.load_work_record(
        work,
        "event_participant",
        "3",
        "ep_alpha",
    ).record.status == "active"


def test_dependency_correction_reason_must_match_exact_material_dimension(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        target_id="ep_gamma",
        supersedes=[_supersession_edge(work, "dep_alpha", "purpose_corrected")],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="does not exactly match"):
        service.correct(
            dependency_reference(work, "dep_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_dep_bad_reason",
        )
    assert tuple(item.record.logical_id for item in service.list(work)) == ("dep_alpha",)


def test_dependency_correction_can_replace_historical_invalidated_predecessor(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_alpha", status="invalidated"),
    )
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        status="invalidated",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(work, "dep_alpha", "dependency_target_corrected")
        ],
        created_at=T1,
        updated_at=T1,
    )

    service.correct(
        dependency_reference(work, "dep_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_dep_invalidated_superseded",
    )
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        dependency_reference(work, "dep_successor")
    ).record.status == "invalidated"


def test_dependency_correction_rejects_cycle_in_post_replacement_graph(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.create(
        work,
        _dependency(
            work,
            dependency_id="dep_existing",
            dependent_id="ep_gamma",
            target_id="ep_alpha",
        ),
    )
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(work, "dep_alpha", "dependency_target_corrected")
        ],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="introduce a cycle"):
        service.correct(
            dependency_reference(work, "dep_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_dep_cycle",
        )
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.status == "active"


def test_dependency_correction_rejects_competing_declared_successor(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    service.repository.create_work_record(
        work,
        _dependency(
            work,
            dependency_id="dep_pending",
            status="proposed",
            target_id="ep_gamma",
            supersedes=[
                _supersession_edge(
                    work,
                    "dep_alpha",
                    "dependency_target_corrected",
                )
            ],
            created_at=T1,
            updated_at=T1,
        ),
    )
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(work, "dep_alpha", "dependency_target_corrected")
        ],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="already has a declared"):
        service.correct(
            dependency_reference(work, "dep_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_dep_competing",
        )


def test_dependency_self_supersession_is_rejected_before_write(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    successor = _dependency(
        work,
        dependency_id="dep_alpha",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(work, "dep_alpha", "dependency_target_corrected")
        ],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="supersede itself"):
        service.correct(
            dependency_reference(work, "dep_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_dep_self",
        )


def test_dependency_duplicate_consolidation_repairs_duplicate_active_graph(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    first = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_one"),
    )
    second = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_two"),
    )
    successor = _dependency(
        work,
        dependency_id="dep_combined",
        supersedes=[
            _supersession_edge(work, "dep_one", "duplicate_consolidated"),
            _supersession_edge(work, "dep_two", "duplicate_consolidated"),
        ],
        created_at=T1,
        updated_at=T1,
    )

    service.consolidate_duplicates(
        work,
        successor,
        expected={"dep_one": first.fingerprint, "dep_two": second.fingerprint},
        transition_ids={
            "dep_one": "lct_dep_one_consolidated",
            "dep_two": "lct_dep_two_consolidated",
        },
        reason_detail="Reviewed duplicate captures of the same dependency condition.",
        operation_id="op_dependency_consolidation",
    )

    assert service.load_exact(
        dependency_reference(work, "dep_one")
    ).record.status == "superseded"
    assert service.load_exact(
        dependency_reference(work, "dep_two")
    ).record.status == "superseded"
    assert service.load_exact(
        dependency_reference(work, "dep_combined")
    ).record.status == "active"
    for transition_id in (
        "lct_dep_one_consolidated",
        "lct_dep_two_consolidated",
    ):
        transition = service.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        assert transition.record.field("reason") == {
            "category": "consolidation",
            "code": "duplicate_consolidated",
            "detail": "Reviewed duplicate captures of the same dependency condition.",
        }
    assert service.require_graph_valid((work,)).live_edge_count == 1


def test_dependency_duplicate_consolidation_rejects_material_dimension_difference(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    first = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_one"),
    )
    second = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_two", strength="advisory"),
    )
    successor = _dependency(
        work,
        dependency_id="dep_combined",
        supersedes=[
            _supersession_edge(work, "dep_one", "duplicate_consolidated"),
            _supersession_edge(work, "dep_two", "duplicate_consolidated"),
        ],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="identical dependent"):
        service.consolidate_duplicates(
            work,
            successor,
            expected={"dep_one": first.fingerprint, "dep_two": second.fingerprint},
            transition_ids={
                "dep_one": "lct_dep_one_bad_consolidation",
                "dep_two": "lct_dep_two_bad_consolidation",
            },
            reason_detail="These are not actually duplicates.",
        )


def test_dependency_duplicate_consolidation_requires_review_detail(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    first = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_one"),
    )
    second = service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_two"),
    )
    successor = _dependency(
        work,
        dependency_id="dep_combined",
        supersedes=[
            _supersession_edge(work, "dep_one", "duplicate_consolidated"),
            _supersession_edge(work, "dep_two", "duplicate_consolidated"),
        ],
        created_at=T1,
        updated_at=T1,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="requires review detail"):
        service.consolidate_duplicates(
            work,
            successor,
            expected={"dep_one": first.fingerprint, "dep_two": second.fingerprint},
            transition_ids={
                "dep_one": "lct_dep_one_no_detail",
                "dep_two": "lct_dep_two_no_detail",
            },
            reason_detail="",
        )


def test_broken_active_dependency_successor_fails_closed_without_following(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _dependency(work, dependency_id="dep_alpha"),
    )
    service.repository.create_work_record(
        work,
        _dependency(
            work,
            dependency_id="dep_successor",
            target_id="ep_gamma",
            supersedes=[
                _supersession_edge(
                    work,
                    "dep_alpha",
                    "dependency_target_corrected",
                )
            ],
            created_at=T1,
            updated_at=T1,
        ),
    )

    evaluation = service.evaluate_condition(
        dependency_reference(work, "dep_successor"),
        gate="current_use",
    )
    assert evaluation.condition == "indeterminate"
    assert evaluation.reason == "declaration_supersession_unreconciled"
    with pytest.raises(WorkflowPrerequisiteError, match="exact predecessor superseded"):
        service.require_graph_valid((work,))
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.logical_id == "dep_alpha"


def test_superseded_dependency_without_effective_successor_is_broken_graph(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.repository.create_work_record(
        work,
        _dependency(
            work,
            dependency_id="dep_orphan",
            status="superseded",
        ),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="exactly one effective direct successor",
    ):
        service.require_graph_valid((work,))


def test_abandoned_proposed_replacement_does_not_block_later_correction(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(work, _dependency(work, dependency_id="dep_alpha"))
    pending = service.repository.create_work_record(
        work,
        _dependency(
            work,
            dependency_id="dep_pending",
            status="proposed",
            target_id="ep_gamma",
            supersedes=[
                _supersession_edge(
                    work,
                    "dep_alpha",
                    "dependency_target_corrected",
                )
            ],
            created_at=T1,
            updated_at=T1,
        ),
    )
    abandoned = _dependency(
        work,
        dependency_id="dep_pending",
        status="invalidated",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(
                work,
                "dep_alpha",
                "dependency_target_corrected",
            )
        ],
        created_at=T1,
        updated_at=T2,
    )
    service.transition_lifecycle(
        dependency_reference(work, "dep_pending"),
        abandoned,
        expected=pending.fingerprint,
        transition_id="lct_dep_pending_abandoned",
        reason_code="entered_in_error",
    )

    successor = _dependency(
        work,
        dependency_id="dep_successor",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(
                work,
                "dep_alpha",
                "dependency_target_corrected",
            )
        ],
        created_at=T2,
        updated_at=T2,
    )
    service.correct(
        dependency_reference(work, "dep_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_dep_alpha_after_abandonment",
    )

    assert service.load_exact(
        dependency_reference(work, "dep_pending")
    ).record.status == "invalidated"
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        dependency_reference(work, "dep_successor")
    ).record.status == "active"
    assert service.require_graph_valid((work,)).live_edge_count == 1


def test_pending_dependency_replacement_cannot_activate_as_ordinary_lifecycle(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    work = event_ref()
    service.create(work, _dependency(work, dependency_id="dep_alpha"))
    pending = service.repository.create_work_record(
        work,
        _dependency(
            work,
            dependency_id="dep_pending",
            status="proposed",
            target_id="ep_gamma",
            supersedes=[
                _supersession_edge(
                    work,
                    "dep_alpha",
                    "dependency_target_corrected",
                )
            ],
            created_at=T1,
            updated_at=T1,
        ),
    )
    candidate = _dependency(
        work,
        dependency_id="dep_pending",
        status="active",
        target_id="ep_gamma",
        supersedes=[
            _supersession_edge(
                work,
                "dep_alpha",
                "dependency_target_corrected",
            )
        ],
        created_at=T1,
        updated_at=T2,
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires correction/consolidation authority",
    ):
        service.transition_lifecycle(
            dependency_reference(work, "dep_pending"),
            candidate,
            expected=pending.fingerprint,
            transition_id="lct_dep_pending_illegal_activation",
            reason_code="review_confirmed",
        )

    assert service.load_exact(
        dependency_reference(work, "dep_pending")
    ).record.status == "proposed"
    assert service.load_exact(
        dependency_reference(work, "dep_alpha")
    ).record.status == "active"


def test_material_dependency_detail_correction_uses_other_reason(tmp_path: Path) -> None:
    service = _service(tmp_path)
    work = event_ref()
    prior = service.create(
        work,
        _dependency(
            work,
            dependency_id="dep_alpha",
            detail="Initial contextual explanation.",
        ),
    )
    successor = _dependency(
        work,
        dependency_id="dep_successor",
        detail="Materially corrected contextual explanation.",
        supersedes=[
            _supersession_edge(
                work,
                "dep_alpha",
                "other",
                detail="Material dependency detail corrected after review.",
            )
        ],
        created_at=T1,
        updated_at=T1,
    )

    service.correct(
        dependency_reference(work, "dep_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_dep_detail_corrected",
    )

    transition = service.repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_dep_detail_corrected",
    )
    assert transition.record.field("reason") == {
        "category": "other",
        "code": "other",
        "detail": "Material dependency detail corrected after review.",
    }
