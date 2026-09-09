from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaOperationPartialCommitError
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    LifecycleWorkflowService,
    StatementOfDisagreementWorkflowService,
    disagreement_reference,
    supported_record_lifecycle_contracts,
)
from portia.workflows.disagreement_lifecycle import (
    require_disagreement_lifecycle_reconciled,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from tests.workflow_helpers import AGENT, event_record, event_ref, participant_record

T0 = "2026-09-08T17:00:00-04:00"
T1 = "2026-09-08T17:05:00-04:00"
T2 = "2026-09-08T17:10:00-04:00"


def _target(record_kind: str = "event_participant", record_id: str = "ep_alpha", version: str = "3") -> dict[str, object]:
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": record_kind,
            "record_id": record_id,
            "contract_version": version,
        },
    }


def disagreement_record(
    *,
    disagreement_id: str = "sod_alpha",
    status: str = "proposed",
    target: dict[str, object] | None = None,
    source: dict[str, object] | None = None,
    positions: list[str] | None = None,
    supersedes: list[dict[str, object]] | None = None,
    created_at: str = T0,
    updated_at: str = T0,
    statement_text: str = "Synthetic source disputes the recorded context.",
    representation: str = "recorded_summary",
) -> PortiaRecord:
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "statement_of_disagreement",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "disagreement_id": disagreement_id,
        "status": status,
        "target": target or _target(),
        "source": source
        or {
            "kind": "local_operator",
            "display_label": "Synthetic represented source",
        },
        "positions": positions or ["disputes_accuracy"],
        "statement": {
            "representation": representation,
            "text": statement_text,
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if supersedes is not None:
        data["supersedes"] = supersedes
    return parse_portia_record("statement_of_disagreement", "1", data)


def _supersedes(
    *predecessor_ids: str,
    reason: str,
    detail: str | None = None,
) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for predecessor_id in predecessor_ids:
        value: dict[str, object] = {
            "work_record_ref": disagreement_reference(
                event_ref(), predecessor_id
            ).to_dict(),
            "reason": reason,
        }
        if detail is not None:
            value["detail"] = detail
        values.append(value)
    return values


def _repository(tmp_path: Path, *, participant_status: str = "active") -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record(created_at=T0, updated_at=T0))
    repository.create_work_record(
        event_ref(),
        participant_record(status=participant_status, created_at=T0, updated_at=T0),
    )
    return repository


def _service(tmp_path: Path, *, participant_status: str = "active") -> StatementOfDisagreementWorkflowService:
    repository = _repository(tmp_path, participant_status=participant_status)
    return StatementOfDisagreementWorkflowService(tmp_path, repository=repository)


def test_reference_is_exact_same_work_disagreement() -> None:
    reference = disagreement_reference(event_ref(), "sod_alpha")
    assert reference.record_ref.record_kind == "statement_of_disagreement"
    assert reference.record_ref.record_id == "sod_alpha"
    assert reference.record_ref.contract_version == "1"


def test_create_load_list_and_resolve_exact(tmp_path: Path) -> None:
    service = _service(tmp_path)
    created = service.create(event_ref(), disagreement_record())
    reference = disagreement_reference(event_ref(), "sod_alpha")
    assert service.load_exact(reference).fingerprint == created.fingerprint
    assert service.resolve_exact(reference).record == created.record
    assert tuple(item.record.logical_id for item in service.list(event_ref())) == (
        "sod_alpha",
    )


def test_active_disagreement_can_be_current_at_creation(tmp_path: Path) -> None:
    service = _service(tmp_path)
    created = service.create(event_ref(), disagreement_record(status="active"))
    current = service.require_current_use(disagreement_reference(event_ref(), "sod_alpha"))
    assert current.fingerprint == created.fingerprint


def test_disagreement_can_pin_historical_inactive_target(tmp_path: Path) -> None:
    service = _service(tmp_path, participant_status="invalidated")
    service.create(event_ref(), disagreement_record(status="active"))
    current = service.require_current_use(disagreement_reference(event_ref(), "sod_alpha"))
    assert current.record.field("target") == _target()


def test_disagreement_cannot_target_another_disagreement(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(event_ref(), disagreement_record(disagreement_id="sod_first"))
    with pytest.raises(WorkflowOwnershipError, match="human-meaningful"):
        service.create(
            event_ref(),
            disagreement_record(
                disagreement_id="sod_second",
                target=_target("statement_of_disagreement", "sod_first", "1"),
            ),
        )


def test_disagreement_cannot_target_lifecycle_infrastructure(tmp_path: Path) -> None:
    service = _service(tmp_path)
    with pytest.raises(WorkflowOwnershipError, match="human-meaningful"):
        service.create(
            event_ref(),
            disagreement_record(target=_target("lifecycle_transition", "lct_alpha", "1")),
        )


def test_current_use_requires_active_status(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(event_ref(), disagreement_record())
    with pytest.raises(WorkflowPrerequisiteError, match="requires active"):
        service.require_current_use(disagreement_reference(event_ref(), "sod_alpha"))


def test_activation_is_journaled_and_reconciled(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record())
    candidate = disagreement_record(status="active", updated_at=T1)
    service.transition_lifecycle(
        disagreement_reference(event_ref(), "sod_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_active",
        reason_code="review_confirmed",
        operation_id="op_disagreement_active",
    )
    accepted = service.require_current_use(disagreement_reference(event_ref(), "sod_alpha"))
    state = require_disagreement_lifecycle_reconciled(
        service.repository,
        event_ref(),
        accepted.record,
    )
    assert state.selected_status == "active"
    assert state.head is not None
    assert state.head.record.field("reason") == {
        "category": "workflow",
        "code": "review_confirmed",
    }
    assert OperationJournalStore(tmp_path).load_current("op_disagreement_active").revision.field("state") == "completed"


def test_activation_rejects_nonreview_reason(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record())
    with pytest.raises(WorkflowPrerequisiteError, match="review_confirmed"):
        service.transition_lifecycle(
            disagreement_reference(event_ref(), "sod_alpha"),
            disagreement_record(status="active", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_disagreement_bad_active",
            reason_code="teacher_confirmed",
            operation_id="op_disagreement_bad_active",
        )


def test_withdrawal_requires_actual_source_withdrawal_reason(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    candidate = disagreement_record(status="withdrawn", updated_at=T1)
    service.transition_lifecycle(
        disagreement_reference(event_ref(), "sod_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_withdrawn",
        reason_code="source_withdrew",
        operation_id="op_disagreement_withdrawn",
    )
    accepted = service.load_exact(disagreement_reference(event_ref(), "sod_alpha"))
    assert accepted.record.status == "withdrawn"
    with pytest.raises(WorkflowPrerequisiteError, match="requires active"):
        service.require_current_use(disagreement_reference(event_ref(), "sod_alpha"))


def test_withdrawal_rejects_generic_resolution_reason(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    with pytest.raises(WorkflowPrerequisiteError, match="actual source withdrawal"):
        service.transition_lifecycle(
            disagreement_reference(event_ref(), "sod_alpha"),
            disagreement_record(status="withdrawn", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_disagreement_bad_withdrawn",
            reason_code="issue_resolved",
            operation_id="op_disagreement_bad_withdrawn",
        )


def test_invalidation_is_distinct_from_source_withdrawal(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    candidate = disagreement_record(status="invalidated", updated_at=T1)
    service.transition_lifecycle(
        disagreement_reference(event_ref(), "sod_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_invalid",
        reason_code="entered_in_error",
        operation_id="op_disagreement_invalid",
    )
    accepted = service.load_exact(disagreement_reference(event_ref(), "sod_alpha"))
    assert accepted.record.status == "invalidated"


def test_ordinary_lifecycle_cannot_rewrite_statement_text(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record())
    with pytest.raises(WorkflowPrerequisiteError, match="cannot rewrite field statement"):
        service.transition_lifecycle(
            disagreement_reference(event_ref(), "sod_alpha"),
            disagreement_record(
                status="active",
                updated_at=T1,
                statement_text="Materially different disputed position.",
            ),
            expected=prior.fingerprint,
            transition_id="lct_disagreement_rewrite",
            reason_code="review_confirmed",
            operation_id="op_disagreement_rewrite",
        )


def test_ordinary_lifecycle_cannot_directly_supersede(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    with pytest.raises(WorkflowPrerequisiteError, match="supersession requires"):
        service.transition_lifecycle(
            disagreement_reference(event_ref(), "sod_alpha"),
            disagreement_record(status="superseded", updated_at=T1),
            expected=prior.fingerprint,
            transition_id="lct_disagreement_superseded",
            reason_code="statement_corrected",
            operation_id="op_disagreement_superseded",
        )


def test_generic_lifecycle_registry_and_dispatch_include_disagreement(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    service = StatementOfDisagreementWorkflowService(tmp_path, repository=repository)
    prior = service.create(event_ref(), disagreement_record(disagreement_id="sod_generic"))
    candidate = disagreement_record(
        disagreement_id="sod_generic",
        status="active",
        updated_at=T2,
    )
    assert ("statement_of_disagreement", "1") in supported_record_lifecycle_contracts()
    generic = LifecycleWorkflowService(tmp_path, repository=repository)
    generic.transition(
        disagreement_reference(event_ref(), "sod_generic"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_generic",
        reason_code="review_confirmed",
        operation_id="op_disagreement_generic",
    )
    resolution = generic.require_corrected_history_reconciled(
        disagreement_reference(event_ref(), "sod_generic")
    )
    assert resolution.selected_status == "active"


def test_action_owner_gate_accepts_both_disagreement_work_roots() -> None:
    from portia.models.references import ExactPortiaWorkRef
    from portia.workflows.action_common import require_action_owner

    require_action_owner(event_ref(), contract="statement_of_disagreement")
    require_action_owner(
        ExactPortiaWorkRef(
            class_id="class_a",
            work_id="sup_alpha",
            work_kind="support_process",
            contract_version="1",
        ),
        contract="statement_of_disagreement",
    )
    with pytest.raises(
        WorkflowOwnershipError,
        match="event@2 or support_process@1",
    ):
        require_action_owner(
            ExactPortiaWorkRef(
                class_id="class_a",
                work_id="evt_alpha",
                work_kind="event",
                contract_version="1",
            ),
            contract="statement_of_disagreement",
        )



def test_material_correction_creates_successor_and_supersedes_predecessor(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_corrected",
        status="active",
        supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
        created_at=T1,
        updated_at=T1,
        statement_text="Synthetic source disputes the corrected recorded context.",
    )
    service.correct(
        disagreement_reference(event_ref(), "sod_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_corrected",
        operation_id="op_disagreement_corrected",
    )

    predecessor = service.load_exact(disagreement_reference(event_ref(), "sod_alpha"))
    assert predecessor.record.status == "superseded"
    current = service.require_current_use(
        disagreement_reference(event_ref(), "sod_corrected")
    )
    assert current.record.field("statement") == successor.field("statement")
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_disagreement_corrected"
    )
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "statement_corrected",
    }
    journal = OperationJournalStore(tmp_path).load_current("op_disagreement_corrected")
    assert journal.revision.field("operation_kind") == "activate_successor"
    assert journal.revision.field("state") == "completed"


def test_material_correction_can_preserve_withdrawn_successor_state(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    service.transition_lifecycle(
        disagreement_reference(event_ref(), "sod_alpha"),
        disagreement_record(status="withdrawn", updated_at=T1),
        expected=prior.fingerprint,
        transition_id="lct_disagreement_prior_withdrawn",
        reason_code="source_withdrew",
        operation_id="op_disagreement_prior_withdrawn",
    )
    withdrawn = service.load_exact(disagreement_reference(event_ref(), "sod_alpha"))
    successor = disagreement_record(
        disagreement_id="sod_corrected_withdrawn",
        status="withdrawn",
        supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
        created_at=T2,
        updated_at=T2,
        statement_text="Corrected summary of the withdrawn source statement.",
    )
    service.correct(
        disagreement_reference(event_ref(), "sod_alpha"),
        successor,
        expected=withdrawn.fingerprint,
        transition_id="lct_disagreement_withdrawn_corrected",
        operation_id="op_disagreement_withdrawn_corrected",
    )
    accepted = service.load_exact(
        disagreement_reference(event_ref(), "sod_corrected_withdrawn")
    )
    assert accepted.record.status == "withdrawn"


def test_material_correction_reason_must_match_changed_fact(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_bad_reason",
        status="active",
        supersedes=_supersedes("sod_alpha", reason="source_corrected"),
        created_at=T1,
        updated_at=T1,
        statement_text="Materially corrected statement text only.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            disagreement_reference(event_ref(), "sod_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_disagreement_bad_reason",
            operation_id="op_disagreement_bad_reason",
        )


def test_material_correction_rejects_duplicate_consolidation_reason(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_not_correction",
        status="active",
        supersedes=_supersedes(
            "sod_alpha",
            "sod_other",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="dedicated.*consolidation"):
        service.correct(
            disagreement_reference(event_ref(), "sod_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_disagreement_not_correction",
        )


def test_material_correction_effective_time_cannot_precede_successor_acceptance(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_late_acceptance",
        status="active",
        supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
        created_at=T2,
        updated_at=T2,
        statement_text="Corrected after review.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="before successor acceptance"):
        service.correct(
            disagreement_reference(event_ref(), "sod_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_disagreement_early_effective",
            effective_at=T1,
        )


def test_other_material_correction_preserves_generic_other_reason_shape(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_other_reason",
        status="active",
        supersedes=_supersedes(
            "sod_alpha",
            reason="other",
            detail="Reviewed material correction not covered by a recognized code.",
        ),
        created_at=T1,
        updated_at=T1,
        statement_text="Reviewed material correction.",
    )
    service.correct(
        disagreement_reference(event_ref(), "sod_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_disagreement_other_reason",
        operation_id="op_disagreement_other_reason",
    )
    transition = service.repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_disagreement_other_reason"
    )
    assert transition.record.field("reason") == {
        "category": "other",
        "code": "other",
        "detail": "Reviewed material correction not covered by a recognized code.",
    }


def test_current_use_rejects_declared_but_ineffective_successor(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.create(event_ref(), disagreement_record(status="active"))
    successor = disagreement_record(
        disagreement_id="sod_broken_frontier",
        status="active",
        supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
        created_at=T1,
        updated_at=T1,
        statement_text="Declared successor before predecessor supersession.",
    )
    service.repository.create_work_record(event_ref(), successor)
    with pytest.raises(WorkflowPrerequisiteError, match="exact predecessor superseded"):
        service.require_current_use(
            disagreement_reference(event_ref(), "sod_broken_frontier")
        )


def _create_duplicate_pair(
    service: StatementOfDisagreementWorkflowService,
    *,
    second_source: dict[str, object] | None = None,
    second_positions: list[str] | None = None,
) -> tuple[object, object]:
    first = service.create(
        event_ref(),
        disagreement_record(disagreement_id="sod_dup_a", status="active"),
    )
    second = service.create(
        event_ref(),
        disagreement_record(
            disagreement_id="sod_dup_b",
            status="active",
            source=second_source,
            positions=second_positions,
        ),
    )
    return first, second


def test_duplicate_consolidation_supersedes_complete_set(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(service)
    successor = disagreement_record(
        disagreement_id="sod_dup_current",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
        statement_text="Reviewed synthesis of the duplicate captures.",
    )
    service.consolidate_duplicates(
        event_ref(),
        successor,
        expected={
            "sod_dup_a": first.fingerprint,
            "sod_dup_b": second.fingerprint,
        },
        transition_ids={
            "sod_dup_a": "lct_disagreement_dup_a",
            "sod_dup_b": "lct_disagreement_dup_b",
        },
        reason_detail="Reviewed as duplicate captures of one originating statement.",
        operation_id="op_disagreement_duplicates",
    )

    assert service.load_exact(
        disagreement_reference(event_ref(), "sod_dup_a")
    ).record.status == "superseded"
    assert service.load_exact(
        disagreement_reference(event_ref(), "sod_dup_b")
    ).record.status == "superseded"
    assert service.require_current_use(
        disagreement_reference(event_ref(), "sod_dup_current")
    ).record.status == "active"
    for transition_id in ("lct_disagreement_dup_a", "lct_disagreement_dup_b"):
        transition = service.repository.load_work_record(
            event_ref(), "lifecycle_transition", "1", transition_id
        )
        assert transition.record.field("reason") == {
            "category": "consolidation",
            "code": "duplicate_consolidated",
            "detail": "Reviewed as duplicate captures of one originating statement.",
        }
    journal = OperationJournalStore(tmp_path).load_current("op_disagreement_duplicates")
    assert journal.revision.field("operation_kind") == "consolidate_duplicates"
    assert journal.revision.field("state") == "completed"


def test_duplicate_consolidation_requires_review_detail(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(service)
    successor = disagreement_record(
        disagreement_id="sod_dup_missing_detail",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="requires review detail"):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "sod_dup_a": first.fingerprint,
                "sod_dup_b": second.fingerprint,
            },
            transition_ids={
                "sod_dup_a": "lct_disagreement_missing_a",
                "sod_dup_b": "lct_disagreement_missing_b",
            },
            reason_detail="",
        )


def test_duplicate_consolidation_requires_complete_expected_set(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, _second = _create_duplicate_pair(service)
    successor = disagreement_record(
        disagreement_id="sod_dup_incomplete_expected",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="every predecessor"):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={"sod_dup_a": first.fingerprint},
            transition_ids={
                "sod_dup_a": "lct_disagreement_expected_a",
                "sod_dup_b": "lct_disagreement_expected_b",
            },
            reason_detail="Reviewed duplicate capture set.",
        )


def test_duplicate_consolidation_rejects_mixed_sources(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(
        service,
        second_source={
            "kind": "local_operator",
            "display_label": "Different represented source",
        },
    )
    successor = disagreement_record(
        disagreement_id="sod_dup_mixed_source",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="same represented source"):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "sod_dup_a": first.fingerprint,
                "sod_dup_b": second.fingerprint,
            },
            transition_ids={
                "sod_dup_a": "lct_disagreement_mixed_source_a",
                "sod_dup_b": "lct_disagreement_mixed_source_b",
            },
            reason_detail="Incorrectly proposed as duplicates.",
        )


def test_duplicate_consolidation_rejects_mixed_positions(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(
        service,
        second_positions=["disputes_context"],
    )
    successor = disagreement_record(
        disagreement_id="sod_dup_mixed_positions",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="same material positions"):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "sod_dup_a": first.fingerprint,
                "sod_dup_b": second.fingerprint,
            },
            transition_ids={
                "sod_dup_a": "lct_disagreement_mixed_positions_a",
                "sod_dup_b": "lct_disagreement_mixed_positions_b",
            },
            reason_detail="Incorrectly proposed as duplicates.",
        )


def test_duplicate_consolidation_preserves_source_withdrawal(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(service)
    service.transition_lifecycle(
        disagreement_reference(event_ref(), "sod_dup_a"),
        disagreement_record(
            disagreement_id="sod_dup_a",
            status="withdrawn",
            updated_at=T1,
        ),
        expected=first.fingerprint,
        transition_id="lct_disagreement_dup_withdrawn",
        reason_code="source_withdrew",
        operation_id="op_disagreement_dup_withdrawn",
    )
    withdrawn = service.load_exact(disagreement_reference(event_ref(), "sod_dup_a"))
    successor = disagreement_record(
        disagreement_id="sod_dup_bad_active",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T2,
        updated_at=T2,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="preserve actual source withdrawal"):
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "sod_dup_a": withdrawn.fingerprint,
                "sod_dup_b": second.fingerprint,
            },
            transition_ids={
                "sod_dup_a": "lct_disagreement_preserve_a",
                "sod_dup_b": "lct_disagreement_preserve_b",
            },
            reason_detail="Same originating statement; withdrawal remains effective.",
        )


def test_duplicate_consolidation_partial_commit_preserves_durable_successor(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    first, second = _create_duplicate_pair(service)
    successor = disagreement_record(
        disagreement_id="sod_dup_partial",
        status="active",
        supersedes=_supersedes(
            "sod_dup_a",
            "sod_dup_b",
            reason="duplicate_consolidated",
        ),
        created_at=T1,
        updated_at=T1,
    )

    def fault(event: str, identifier: str | None) -> None:
        if event == "after_publish" and identifier == "step_successor":
            raise RuntimeError("synthetic interruption after successor acceptance")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        service.consolidate_duplicates(
            event_ref(),
            successor,
            expected={
                "sod_dup_a": first.fingerprint,
                "sod_dup_b": second.fingerprint,
            },
            transition_ids={
                "sod_dup_a": "lct_disagreement_partial_a",
                "sod_dup_b": "lct_disagreement_partial_b",
            },
            reason_detail="Reviewed as duplicate captures of one statement.",
            operation_id="op_disagreement_dup_partial",
            fault_hook=fault,
        )

    assert "step_successor" in exc_info.value.accepted_steps
    durable = service.load_exact(disagreement_reference(event_ref(), "sod_dup_partial"))
    assert durable.record.logical_id == "sod_dup_partial"
    assert service.load_exact(
        disagreement_reference(event_ref(), "sod_dup_a")
    ).fingerprint == first.fingerprint
    assert service.load_exact(
        disagreement_reference(event_ref(), "sod_dup_b")
    ).fingerprint == second.fingerprint
    journal = OperationJournalStore(tmp_path).load_current("op_disagreement_dup_partial")
    assert journal.revision.field("state") == "failed"


def test_material_correction_rejects_competing_declared_successor(tmp_path: Path) -> None:
    service = _service(tmp_path)
    prior = service.create(event_ref(), disagreement_record(status="active"))
    service.repository.create_work_record(
        event_ref(),
        disagreement_record(
            disagreement_id="sod_existing_successor",
            status="active",
            supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
            created_at=T1,
            updated_at=T1,
            statement_text="Existing declared replacement.",
        ),
    )
    successor = disagreement_record(
        disagreement_id="sod_competing_successor",
        status="active",
        supersedes=_supersedes("sod_alpha", reason="statement_corrected"),
        created_at=T2,
        updated_at=T2,
        statement_text="Competing replacement.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="declared direct successor"):
        service.correct(
            disagreement_reference(event_ref(), "sod_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_disagreement_competing",
        )
