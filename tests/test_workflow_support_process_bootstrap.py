from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaQuarantinedError
from portia.workflows import (
    SupportProcessWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    support_process_reference,
)

TIMESTAMP = "2026-08-31T09:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice1_test"}


class _BlockingQuarantine:
    def require_allowed(self, _target: object, effect: str) -> None:
        if effect == "block_work_writes":
            raise PortiaQuarantinedError("synthetic Support Process write block")


def support_process_wire(
    *,
    class_id: str = "class_a",
    work_id: str = "sup_alpha",
    school_year: str = "2026-2027",
    status: str = "proposed",
    workflow_state: str = "planning",
    initiation: dict[str, object] | None = None,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    updated_at: str = TIMESTAMP,
    planned_start_date: str | None = None,
    planned_end_date: str | None = None,
    review_on: str | None = None,
    continues_from: dict[str, object] | None = None,
    supersedes: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": work_id,
        "school_year": school_year,
        "status": status,
        "workflow_state": workflow_state,
        "summary": "Synthetic bounded teacher-local support planning.",
        "initiation": initiation
        or {
            "kind": "teacher_identified_need",
            "detail": "Synthetic need identified for planning.",
        },
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if planned_start_date is not None:
        value["planned_start_date"] = planned_start_date
    if planned_end_date is not None:
        value["planned_end_date"] = planned_end_date
    if review_on is not None:
        value["review_on"] = review_on
    if continues_from is not None:
        value["continues_from"] = continues_from
    if supersedes is not None:
        value["supersedes"] = supersedes
    return value


def support_process_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        support_process_wire(**kwargs),
    )


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


def test_reference_is_exact_support_process_v1() -> None:
    reference = support_process_reference(support_process_record())
    assert reference == support_process_ref()
    assert reference.to_dict()["module_id"] == "portia"


def test_proposed_digital_bootstrap_create_load_resolve_and_list(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    created = service.create(support_process_record())

    assert created.record.status == "proposed"
    assert created.record.field("workflow_state") == "planning"
    assert service.load_exact(support_process_ref()).path == created.path
    assert service.resolve_exact(support_process_ref()).record.logical_id == "sup_alpha"
    assert [item.record.logical_id for item in service.list("class_a")] == [
        "sup_alpha"
    ]
    assert not (created.path.parent / "records").exists()


def test_exact_load_rejects_wrong_work_kind_or_contract_version(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(tmp_path)
    with pytest.raises(WorkflowOwnershipError):
        service.load_exact(
            ExactPortiaWorkRef(
                class_id="class_a",
                work_id="evt_alpha",
                work_kind="event",
                contract_version="2",
            )
        )
    with pytest.raises(WorkflowOwnershipError):
        service.load_exact(support_process_ref(version="2"))


def test_standalone_active_creation_is_rejected_for_participant_bootstrap(
    tmp_path: Path,
) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="must begin proposed"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(status="active")
        )
    assert not (tmp_path / "classes").exists()


def test_new_proposed_process_must_begin_in_planning(tmp_path: Path) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="begin in planning"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(workflow_state="active")
        )
    assert not (tmp_path / "classes").exists()


def test_bootstrap_is_digital_entry_only(tmp_path: Path) -> None:
    paper_source = {
        "type": "paper_capture",
        "stage": "ingested",
        "route_id": "route_alpha",
        "page_record_id": "page_alpha",
    }
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(creation_source=paper_source)
        )
    assert not (tmp_path / "classes").exists()


def test_school_year_must_be_consecutive(tmp_path: Path) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="consecutive"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(school_year="2026-2028")
        )
    assert not (tmp_path / "classes").exists()


def test_update_timestamp_cannot_precede_creation(tmp_path: Path) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(updated_at="2026-08-31T08:59:00-04:00")
        )
    assert not (tmp_path / "classes").exists()


@pytest.mark.parametrize(
    ("dates", "message"),
    [
        (
            {
                "planned_start_date": "2026-09-10",
                "planned_end_date": "2026-09-09",
            },
            "planned_end_date cannot precede planned_start_date",
        ),
        (
            {
                "planned_start_date": "2026-09-10",
                "review_on": "2026-09-09",
            },
            "review_on cannot precede planned_start_date",
        ),
    ],
)
def test_planned_date_chronology_is_validated(
    tmp_path: Path,
    dates: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match=message):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(**dates)
        )
    assert not (tmp_path / "classes").exists()


def test_reference_initiation_fails_closed_until_context_authority_slice(
    tmp_path: Path,
) -> None:
    event = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    initiation = {"kind": "event_context", "event_ref": event.to_dict()}
    with pytest.raises(WorkflowPrerequisiteError, match="exact context authority"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(initiation=initiation)
        )
    assert not (tmp_path / "classes").exists()


def test_imported_history_cannot_be_fabricated_by_digital_bootstrap(
    tmp_path: Path,
) -> None:
    initiation = {
        "kind": "imported_history",
        "detail": "Synthetic historical context.",
    }
    with pytest.raises(WorkflowPrerequisiteError, match="import provenance"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(initiation=initiation)
        )
    assert not (tmp_path / "classes").exists()


def test_cross_year_continuation_is_deferred_from_fresh_bootstrap(
    tmp_path: Path,
) -> None:
    predecessor = ExactPortiaWorkRef(
        class_id="class_previous",
        work_id="sup_previous",
        work_kind="support_process",
        contract_version="1",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="continues_from authority"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(continues_from=predecessor.to_dict())
        )
    assert not (tmp_path / "classes").exists()


def test_fresh_bootstrap_rejects_supersession_history(tmp_path: Path) -> None:
    predecessor = support_process_ref().to_dict()
    supersedes = [{"work_ref": predecessor, "reason": "summary_corrected"}]
    with pytest.raises(WorkflowPrerequisiteError, match="cannot create correction"):
        SupportProcessWorkflowService(tmp_path).create(
            support_process_record(supersedes=supersedes)
        )
    assert not (tmp_path / "classes").exists()


def test_quarantine_blocks_write_without_blocking_exact_service_design(
    tmp_path: Path,
) -> None:
    service = SupportProcessWorkflowService(
        tmp_path,
        quarantine=_BlockingQuarantine(),  # type: ignore[arg-type]
    )
    with pytest.raises(PortiaQuarantinedError):
        service.create(support_process_record())
    assert not (tmp_path / "classes").exists()
