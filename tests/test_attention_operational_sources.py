from __future__ import annotations

from pathlib import Path

import pytest

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.attention.operational_sources import _integrity_attention_code
from portia.models import parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage import FindingSuppressionStore
from portia.storage.errors import PortiaCorruptionError
from portia.storage.paths import operations_root
from portia.storage.series import OperationJournalStore
from portia.workflows import IntegrityWorkflowService
from portia.workflows.errors import WorkflowPrerequisiteError
from tests.test_workflow_integrity_operators import (
    NOW,
    OPERATOR,
    _completed_operation,
    _create_suppression,
    _finding,
    _install_generation,
)
from tests.test_workflow_quarantine import (
    _apply_work_quarantine,
    _completed_bundle,
    _completed_repair,
)
from tests.test_workflow_recovery import _journal_data
from tests.workflow_helpers import event_ref

AS_OF = ExplicitOffsetTimestamp("2026-09-16T13:00:00-04:00")
LATER = "2026-09-17T12:00:00-04:00"


@pytest.fixture(autouse=True)
def _stable_operation_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep imported synthetic operations before fixed evidence timestamps."""
    monkeypatch.setattr(
        "portia.workflows.coordinated._now",
        lambda: "2026-09-16T11:00:00-04:00",
    )


def _query() -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref()),
        as_of=AS_OF,
    )


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


def _prepared_work_operation(root: Path) -> None:
    data = _journal_data()
    data["primary_target"] = {
        "kind": "work",
        "work_ref": event_ref().to_dict(),
    }
    journal = parse_portia_record("operation_journal", "2", data)
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": "op_create_actor",
            "journal_revision": 1,
        },
    )
    OperationJournalStore(root).create(journal, pointer)


def _mapped_finding(*, code: str, finding_key: str = "fnd_attention"):
    finding = _finding(finding_key=finding_key)
    data = finding.to_dict()
    data["rule_id"] = f"portia.synthetic.{code}"
    data["category"] = "persistence_recovery"
    data["code"] = code
    return parse_portia_record("integrity_finding", "2", data)


def test_operation_series_enumeration_is_storage_owned_and_validated(
    tmp_path: Path,
) -> None:
    _completed_bundle(tmp_path)
    _prepared_work_operation(tmp_path)

    assert OperationJournalStore(tmp_path).series_ids() == (
        "op_create_actor",
        "op_quarantine_apply",
    )

    (operations_root(tmp_path) / "not-an-operation").mkdir()
    with pytest.raises(PortiaCorruptionError, match="operation series identity"):
        OperationJournalStore(tmp_path).series_ids()


def test_prepared_current_operation_is_recovery_attention(tmp_path: Path) -> None:
    _completed_bundle(tmp_path)
    _prepared_work_operation(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    recovery = [
        item for item in report.items if item.code == "portia_recovery_required"
    ]
    assert len(recovery) == 1
    item = recovery[0]
    assert item.source_ref.kind == "recovery_scope"
    assert item.source_ref.identifier == "op_create_actor"
    assert item.reason_codes == ("disposition_resume", "state_prepared")


def test_terminal_consistent_operation_is_not_recovery_history_attention(
    tmp_path: Path,
) -> None:
    _completed_bundle(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    assert all(item.code != "portia_recovery_required" for item in report.items)


def test_active_work_quarantine_is_separate_attention(tmp_path: Path) -> None:
    _service, state, _applying = _apply_work_quarantine(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    quarantine = [
        item for item in report.items if item.code == "portia_quarantine_active"
    ]
    assert len(quarantine) == 1
    item = quarantine[0]
    assert item.source_ref.kind == "quarantine"
    assert item.source_ref.identifier == state.revision.to_dict()["quarantine_id"]
    assert item.reason_codes == (
        "reason_partial_commit",
        "effect_block_current_use",
        "effect_block_work_writes",
        "effect_review_required",
    )


def test_released_quarantine_is_not_current_attention(tmp_path: Path) -> None:
    service, active, applying = _apply_work_quarantine(tmp_path)
    target = active.revision.to_dict()["target"]
    assert isinstance(target, dict)
    repair = _completed_repair(
        tmp_path,
        str(applying["operation_id"]),
        "op_attention_quarantine_release",
        target,
    )
    service.release_quarantine(
        str(active.revision.to_dict()["quarantine_id"]),
        expected_pointer=active.pointer_fingerprint,
        resolving_operation=repair,
        satisfied_release_requirements=["canonical_state_reconciled"],
        effective_at="2026-09-17T23:30:00-04:00",
        resolved_by={"type": "system_process", "process_id": "workflow_bundle"},
    )

    report = AttentionQueryService(tmp_path).query(_query())

    assert all(item.code != "portia_quarantine_active" for item in report.items)


def test_closed_integrity_mapping_distinguishes_conflict_and_review() -> None:
    assert (
        _integrity_attention_code("selected_history_ambiguous")
        == "portia_integrity_conflict"
    )
    assert (
        _integrity_attention_code("content_digest_mismatch")
        == "portia_integrity_review_required"
    )
    with pytest.raises(WorkflowPrerequisiteError, match="no native attention"):
        _integrity_attention_code("future_unknown_integrity_code")


def test_acknowledged_integrity_finding_remains_attention(tmp_path: Path) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _mapped_finding(code="content_digest_mismatch")
    _install_generation(
        tmp_path,
        scope,
        [finding],
        operation_ref,
        generation_id="dgen_attention_acknowledged",
    )
    service = IntegrityWorkflowService(tmp_path)
    value = finding.to_dict()
    service.acknowledge_finding(
        scope,
        acknowledgement_id="fack_attention_reviewed",
        finding_key=str(value["finding_key"]),
        evaluation_key=str(value["evaluation_key"]),
        acknowledged_at=NOW,
        acknowledged_by=OPERATOR,
        acknowledgement_category="reviewed",
        creating_operation=operation_ref,
    )

    report = AttentionQueryService(tmp_path).query(_query())

    items = [
        item
        for item in report.items
        if item.code == "portia_integrity_review_required"
    ]
    assert len(items) == 1
    assert items[0].source_ref.kind == "integrity_finding"
    assert items[0].source_ref.identifier == value["finding_key"]
    assert items[0].reason_codes == ("finding_content_digest_mismatch",)


def test_effective_suppression_hides_routine_integrity_presentation(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _mapped_finding(code="content_digest_mismatch")
    _install_generation(
        tmp_path,
        scope,
        [finding],
        operation_ref,
        generation_id="dgen_attention_suppressed",
    )
    service = IntegrityWorkflowService(tmp_path)
    suppression = _create_suppression(
        service,
        scope,
        finding,
        operation_ref,
        suppression_id="fsup_attention_hidden",
        conditions=[{"kind": "fixed_timestamp", "expires_at": LATER}],
    )
    value = finding.to_dict()

    assert service.is_finding_presentation_suppressed(
        scope,
        finding_key=str(value["finding_key"]),
        evaluation_key=str(value["evaluation_key"]),
        evaluated_at=AS_OF.text,
        surface="teacher_dashboard",
        audience="local_teacher",
    )
    assert not service.is_finding_presentation_suppressed(
        scope,
        finding_key=str(value["finding_key"]),
        evaluation_key=str(value["evaluation_key"]),
        evaluated_at=LATER,
        surface="teacher_dashboard",
        audience="local_teacher",
    )
    assert suppression.revision.to_dict()["state"] == "active"
    assert FindingSuppressionStore(tmp_path).load_current(
        "fsup_attention_hidden"
    ).revision.to_dict()["state"] == "active"

    report = AttentionQueryService(tmp_path).query(_query())
    assert all(
        item.code != "portia_integrity_review_required" for item in report.items
    )


def test_unknown_current_integrity_code_fails_closed(tmp_path: Path) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _finding(finding_key="fnd_unknown_attention")
    _install_generation(
        tmp_path,
        scope,
        [finding],
        operation_ref,
        generation_id="dgen_attention_unknown",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="no native attention"):
        AttentionQueryService(tmp_path).query(_query())


def test_operational_attention_query_is_zero_write(tmp_path: Path) -> None:
    _completed_bundle(tmp_path)
    _prepared_work_operation(tmp_path)
    before = _snapshot(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    assert any(item.code == "portia_recovery_required" for item in report.items)
    assert _snapshot(tmp_path) == before
