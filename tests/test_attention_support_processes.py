
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.attention.workflow_sources import _dependency_attention_reason_codes
from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import StoredRecord
from portia.workflows import (
    DependencyWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    support_process_participant_reference,
)
from portia.workflows.dependencies import (
    DependencyConditionEvaluation,
    dependency_reference,
)

T0 = "2026-08-31T10:00:00-04:00"
T5 = "2026-08-31T10:05:00-04:00"
T6 = "2026-08-31T10:06:00-04:00"
T10 = "2026-08-31T10:10:00-04:00"
T15 = "2026-08-31T10:15:00-04:00"
T20 = "2026-08-31T10:20:00-04:00"
T25 = "2026-08-31T10:25:00-04:00"
AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")
AGENT = {"type": "system_process", "process_id": "issue49_slice3_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record(
    *,
    status: str = "proposed",
    workflow_state: str = "planning",
    review_on: str | None = None,
    updated_at: str = T0,
) -> PortiaRecord:
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "school_year": "2026-2027",
        "status": status,
        "workflow_state": workflow_state,
        "summary": "Synthetic bounded Support Process.",
        "initiation": {"kind": "teacher_identified_need", "detail": "Synthetic planning need."},
        "creation_source": {"type": "digital_entry"},
        "created_at": T0,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if review_on is not None:
        data["review_on"] = review_on
    return parse_portia_record("support_process", "1", data)


def participant_record(
    participant_id: str,
    *,
    status: str = "proposed",
    updated_at: str = T0,
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
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic learner {participant_id}",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def dependency_record(
    *,
    dependency_id: str,
    target_id: str,
    strength: str = "required",
) -> PortiaRecord:
    return parse_portia_record(
        "dependency",
        "1",
        {
            "schema_version": "1",
            "record_type": "dependency",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "dependency_id": dependency_id,
            "status": "active",
            "dependent": {
                "kind": "work",
                "work_kind": "support_process",
                "contract_version": "1",
            },
            "dependency": {
                "kind": "portia_record",
                "work_record_ref": {
                    "work_ref": work_ref().to_dict(),
                    "record_ref": {
                        "record_kind": "support_process_participant",
                        "record_id": target_id,
                        "contract_version": "1",
                    },
                },
            },
            "strength": strength,
            "applies_to": "current_use",
            "purpose": "workflow_prerequisite",
            "creation_source": {"type": "digital_entry"},
            "created_at": T6,
            "created_by": AGENT,
            "updated_at": T6,
            "updated_by": AGENT,
        },
    )


def _activate_participant(
    service: SupportProcessParticipantWorkflowService,
    participant_id: str,
    *,
    updated_at: str = T5,
) -> None:
    reference = support_process_participant_reference(work_ref(), participant_id)
    prior = service.load_exact(reference)
    service.transition_lifecycle(
        reference,
        participant_record(participant_id, status="active", updated_at=updated_at),
        expected=prior.fingerprint,
        transition_id=f"lct_{participant_id}_active",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_active",
    )


def _invalidate_participant(
    service: SupportProcessParticipantWorkflowService,
    participant_id: str,
) -> None:
    reference = support_process_participant_reference(work_ref(), participant_id)
    prior = service.load_exact(reference)
    service.transition_lifecycle(
        reference,
        participant_record(participant_id, status="invalidated", updated_at=T15),
        expected=prior.fingerprint,
        transition_id=f"lct_{participant_id}_invalidated",
        reason_code="recording_error",
        operation_id=f"op_{participant_id}_invalidated",
    )


def _ready_root(
    tmp_path: Path,
    *,
    review_on: str | None = None,
    beta_active: bool = False,
    gamma_active: bool = False,
) -> tuple[SupportProcessWorkflowService, SupportProcessParticipantWorkflowService, StoredRecord]:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record(review_on=review_on))

    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    for participant_id, active in (
        ("spp_alpha", True),
        ("spp_beta", beta_active),
        ("spp_gamma", gamma_active),
    ):
        participant_service.create(work_ref(), participant_record(participant_id))
        if active:
            _activate_participant(participant_service, participant_id)

    return root_service, participant_service, root


def _activate_root(
    service: SupportProcessWorkflowService,
    root: StoredRecord,
    *,
    review_on: str | None = None,
) -> None:
    service.transition_lifecycle(
        work_ref(),
        root_record(status="active", review_on=review_on, updated_at=T10),
        expected=root.fingerprint,
        transition_id="lct_root_active",
        reason_code="planning_confirmed",
        operation_id="op_root_active",
    )


def _declare(tmp_path: Path, record: PortiaRecord) -> None:
    DependencyWorkflowService(tmp_path).create(work_ref(), record)


def _query() -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(work_ref()),
        as_of=AS_OF,
    )


def _attention(tmp_path: Path):
    return AttentionQueryService(tmp_path).query(_query())


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (
                str(path.relative_to(root)),
                path.read_bytes(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def _advance_workflow_state(
    service: SupportProcessWorkflowService,
    *,
    workflow_state: str,
    updated_at: str,
) -> None:
    prior = service.load_exact(work_ref())
    data = prior.record.to_dict()
    data["workflow_state"] = workflow_state
    data["updated_at"] = updated_at
    data["updated_by"] = AGENT
    service.transition_workflow_state(
        work_ref(),
        parse_portia_record("support_process", "1", data),
        expected=prior.fingerprint,
    )


def test_proposed_support_process_is_not_current_attention(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(
        root_record(review_on="2026-09-20")
    )

    report = _attention(tmp_path)

    assert report.evaluation == "evaluated"
    assert report.items == ()


def test_review_on_future_is_not_current_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path, review_on="2026-09-22")
    _activate_root(service, root, review_on="2026-09-22")
    assert _attention(tmp_path).items == ()


def test_review_on_today_is_due_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path, review_on="2026-09-21")
    _activate_root(service, root, review_on="2026-09-21")
    report = _attention(tmp_path)
    assert len(report.items) == 1
    item = report.items[0]
    assert item.code == "portia_support_process_review_due"
    assert item.timing is not None
    assert item.timing.classification == "due"
    assert item.reason_codes == ("planning",)
    assert item.source_ref == work_ref()


def test_review_on_past_is_overdue_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path, review_on="2026-09-20")
    _activate_root(service, root, review_on="2026-09-20")
    report = _attention(tmp_path)
    assert len(report.items) == 1
    assert report.items[0].code == "portia_support_process_review_overdue"
    assert report.items[0].timing is not None
    assert report.items[0].timing.classification == "overdue"


def test_planning_state_alone_is_not_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path)
    _activate_root(service, root)
    assert _attention(tmp_path).items == ()


def test_terminal_workflow_state_drops_historical_review_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path, review_on="2026-09-20")
    _activate_root(service, root, review_on="2026-09-20")
    _advance_workflow_state(service, workflow_state="active", updated_at=T20)
    _advance_workflow_state(service, workflow_state="completed", updated_at=T25)
    assert _attention(tmp_path).items == ()


def test_required_review_required_dependency_is_attention_even_when_gate_blocks(
    tmp_path: Path,
) -> None:
    service, _participants, root = _ready_root(tmp_path, beta_active=False)
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_required_review",
            target_id="spp_beta",
        ),
    )
    _activate_root(service, root)
    report = _attention(tmp_path)
    assert len(report.items) == 1
    assert report.items[0].code == "portia_support_process_dependency_attention"
    assert report.items[0].reason_codes == ("required_review_required",)


def test_advisory_unsatisfied_dependency_is_attention_without_gate_block(
    tmp_path: Path,
) -> None:
    service, participants, root = _ready_root(tmp_path, beta_active=True)
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_advisory_unsatisfied",
            target_id="spp_beta",
            strength="advisory",
        ),
    )
    _activate_root(service, root)
    _invalidate_participant(participants, "spp_beta")
    assert service.require_current_use(work_ref()).record.status == "active"
    report = _attention(tmp_path)
    assert len(report.items) == 1
    assert report.items[0].reason_codes == ("advisory_unsatisfied",)


def test_satisfied_dependency_is_not_attention(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(tmp_path, beta_active=True)
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_satisfied",
            target_id="spp_beta",
        ),
    )
    _activate_root(service, root)
    assert _attention(tmp_path).items == ()


def test_dependency_attention_deduplicates_per_support_process_code(tmp_path: Path) -> None:
    service, participants, root = _ready_root(
        tmp_path,
        beta_active=False,
        gamma_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_required_review",
            target_id="spp_beta",
        ),
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_advisory_unsatisfied",
            target_id="spp_gamma",
            strength="advisory",
        ),
    )
    _activate_root(service, root)
    _invalidate_participant(participants, "spp_gamma")
    report = _attention(tmp_path)
    assert len(report.items) == 1
    assert report.items[0].reason_codes == (
        "required_review_required",
        "advisory_unsatisfied",
    )


def test_support_process_attention_query_is_zero_write(tmp_path: Path) -> None:
    service, _participants, root = _ready_root(
        tmp_path,
        review_on="2026-09-21",
    )
    _activate_root(service, root, review_on="2026-09-21")
    before = _snapshot(tmp_path)

    report = _attention(tmp_path)

    assert len(report.items) == 1
    assert _snapshot(tmp_path) == before


def test_dependency_reason_mapping_preserves_indeterminate_distinction() -> None:
    reference = dependency_reference(work_ref(), "dep_mapping")
    base = DependencyConditionEvaluation(
        reference=reference,
        dependent=work_ref(),
        strength="required",
        applies_to="current_use",
        purpose="workflow_prerequisite",
        condition="review_required",
        reason="target_status_requires_review",
        evaluated_at=AS_OF.text,
    )
    evaluations = (
        base,
        replace(
            base,
            strength="advisory",
            condition="unsatisfied",
            reason="target_status_is_ineligible",
        ),
        replace(
            base,
            condition="indeterminate",
            reason="target_lifecycle_unreconciled",
        ),
    )
    assert _dependency_attention_reason_codes(evaluations) == (
        "required_review_required",
        "required_indeterminate",
        "advisory_unsatisfied",
    )
