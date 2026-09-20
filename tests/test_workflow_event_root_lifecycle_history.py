from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef
from portia.storage.repository import PortiaRepository
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.event_lifecycle import build_event_lifecycle_transition
from portia.workflows.event_lifecycle_history import (
    EventLifecycleHistoryResolution,
    load_event_lifecycle_history_corrections,
    require_event_lifecycle_history_reconciled,
    resolve_event_lifecycle_history,
)
from tests.workflow_helpers import AGENT, event_record, event_ref

T0 = "2026-08-26T12:00:00-04:00"
T1 = "2026-08-26T12:05:00-04:00"
T2 = "2026-08-26T12:10:00-04:00"


def _local_ref(kind: str, identifier: str) -> dict[str, object]:
    return ExactLocalRecordRef(
        record_kind=kind,
        record_id=identifier,
        contract_version="1",
    ).to_dict()


def _root_target(*, version: str = "2") -> dict[str, object]:
    return {
        "kind": "work",
        "work_kind": "event",
        "contract_version": version,
    }


def _correction(
    correction_id: str,
    *,
    replaced: str,
    replacement: str | None,
    previous: str | None = None,
    version: str = "2",
) -> PortiaRecord:
    return parse_portia_record(
        "lifecycle_history_correction",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_history_correction",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "correction_id": correction_id,
            "target": _root_target(version=version),
            "previous_correction": (
                None
                if previous is None
                else _local_ref("lifecycle_history_correction", previous)
            ),
            "replaced_head": _local_ref("lifecycle_transition", replaced),
            "replacement_head": (
                None
                if replacement is None
                else _local_ref("lifecycle_transition", replacement)
            ),
            "reason": {"code": "wrong_to_status"},
            "creation_source": {"type": "digital_entry"},
            "created_at": T2,
            "created_by": AGENT,
        },
    )


def _seed_root(tmp_path: Path, *, status: str) -> tuple[PortiaRepository, PortiaRecord]:
    repository = PortiaRepository(tmp_path)
    root = event_record(status=status, updated_at=T2)
    repository.create_work(event_ref(), root)
    return repository, root


def _branch(
    repository: PortiaRepository,
    *,
    transition_id: str,
    to_status: str,
) -> PortiaRecord:
    reason = "event_confirmed" if to_status == "active" else "event_cancelled"
    candidate = event_record(status=to_status, updated_at=T1)
    return build_event_lifecycle_transition(
        repository,
        event_ref(),
        event_record(status="draft", updated_at=T0),
        candidate,
        transition_id=transition_id,
        reason_code=reason,
        effective_at=T1,
    )


def _store_root_branches(
    repository: PortiaRepository,
    *branches: tuple[str, str],
) -> None:
    # Build every alternative against the same empty-history baseline before
    # persisting any branch.  The ordinary Event builder remains linear and
    # must not be weakened merely to construct correction fixtures.
    built = tuple(
        _branch(
            repository,
            transition_id=transition_id,
            to_status=status,
        )
        for transition_id, status in branches
    )
    for transition in built:
        repository.create_work_record(event_ref(), transition)


def test_no_correction_evidence_delegates_to_raw_event_lifecycle_reader(
    tmp_path: Path,
) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(repository, ("lct_evt_active", "active"))

    resolution = require_event_lifecycle_history_reconciled(
        repository,
        event_ref(),
        root,
    )

    assert isinstance(resolution, EventLifecycleHistoryResolution)
    assert resolution.corrections == ()
    assert resolution.selected_correction is None
    assert resolution.baseline_status == "draft"
    assert resolution.selected_status == "active"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_evt_active"
    assert resolution.excluded_transition_ids == frozenset()


def test_corrected_event_history_selects_replacement_branch_from_raw_fork(
    tmp_path: Path,
) -> None:
    repository, root = _seed_root(tmp_path, status="cancelled")
    _store_root_branches(
        repository,
        ("lct_evt_old_active", "active"),
        ("lct_evt_corrected_cancelled", "cancelled"),
    )
    repository.create_work_record(
        event_ref(),
        _correction(
            "lhc_evt_select_cancelled",
            replaced="lct_evt_old_active",
            replacement="lct_evt_corrected_cancelled",
        ),
    )

    resolution = require_event_lifecycle_history_reconciled(
        repository,
        event_ref(),
        root,
    )

    assert resolution.baseline_status == "draft"
    assert resolution.selected_status == "cancelled"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_evt_corrected_cancelled"
    assert resolution.selected_correction is not None
    assert (
        resolution.selected_correction.record.logical_id
        == "lhc_evt_select_cancelled"
    )
    assert resolution.excluded_transition_ids == frozenset({"lct_evt_old_active"})
    assert resolution.reconciled is True


def test_event_correction_chain_uses_predecessors_not_storage_order(
    tmp_path: Path,
) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(
        repository,
        ("lct_evt_old_active", "active"),
        ("lct_evt_cancelled", "cancelled"),
        ("lct_evt_final_active", "active"),
    )
    first = _correction(
        "lhc_evt_first",
        replaced="lct_evt_old_active",
        replacement="lct_evt_cancelled",
    )
    second = _correction(
        "lhc_evt_second",
        replaced="lct_evt_cancelled",
        replacement="lct_evt_final_active",
        previous="lhc_evt_first",
    )
    # Persist reverse lexical/semantic order to prove predecessor authority.
    repository.create_work_record(event_ref(), second)
    repository.create_work_record(event_ref(), first)

    history = load_event_lifecycle_history_corrections(
        repository,
        event_ref(),
        root,
    )
    assert [item.record.logical_id for item in history] == [
        "lhc_evt_first",
        "lhc_evt_second",
    ]

    resolution = require_event_lifecycle_history_reconciled(
        repository,
        event_ref(),
        root,
    )
    assert resolution.selected_status == "active"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_evt_final_active"
    assert resolution.excluded_transition_ids == frozenset(
        {"lct_evt_old_active", "lct_evt_cancelled"}
    )


def test_event_history_correction_can_select_creation_baseline(tmp_path: Path) -> None:
    repository, root = _seed_root(tmp_path, status="draft")
    _store_root_branches(repository, ("lct_evt_old_active", "active"))
    repository.create_work_record(
        event_ref(),
        _correction(
            "lhc_evt_baseline",
            replaced="lct_evt_old_active",
            replacement=None,
        ),
    )

    resolution = require_event_lifecycle_history_reconciled(
        repository,
        event_ref(),
        root,
    )

    assert resolution.baseline_status == "draft"
    assert resolution.selected_head is None
    assert resolution.selected_status == "draft"
    assert resolution.excluded_transition_ids == frozenset({"lct_evt_old_active"})


def test_corrected_event_history_fails_closed_on_canonical_status_mismatch(
    tmp_path: Path,
) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(
        repository,
        ("lct_evt_old_active", "active"),
        ("lct_evt_corrected_cancelled", "cancelled"),
    )
    repository.create_work_record(
        event_ref(),
        _correction(
            "lhc_evt_mismatch",
            replaced="lct_evt_old_active",
            replacement="lct_evt_corrected_cancelled",
        ),
    )

    resolution = resolve_event_lifecycle_history(repository, event_ref(), root)
    assert resolution.reconciled is False
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        require_event_lifecycle_history_reconciled(repository, event_ref(), root)


def test_event_correction_chain_fork_is_rejected(tmp_path: Path) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(repository, ("lct_evt_old_active", "active"))
    correction_root = _correction(
        "lhc_evt_root",
        replaced="lct_evt_old_active",
        replacement=None,
    )
    left = _correction(
        "lhc_evt_left",
        replaced="lct_evt_old_active",
        replacement=None,
        previous="lhc_evt_root",
    )
    right = _correction(
        "lhc_evt_right",
        replaced="lct_evt_old_active",
        replacement=None,
        previous="lhc_evt_root",
    )
    for correction in (left, correction_root, right):
        repository.create_work_record(event_ref(), correction)

    with pytest.raises(WorkflowPrerequisiteError, match="contains a fork"):
        load_event_lifecycle_history_corrections(repository, event_ref(), root)


def test_event_correction_cannot_reselect_excluded_branch(tmp_path: Path) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(
        repository,
        ("lct_evt_old_active", "active"),
        ("lct_evt_cancelled", "cancelled"),
        ("lct_evt_final_active", "active"),
    )
    first = _correction(
        "lhc_evt_first",
        replaced="lct_evt_old_active",
        replacement="lct_evt_cancelled",
    )
    second = _correction(
        "lhc_evt_second",
        replaced="lct_evt_cancelled",
        replacement="lct_evt_old_active",
        previous="lhc_evt_first",
    )
    repository.create_work_record(event_ref(), first)
    repository.create_work_record(event_ref(), second)

    with pytest.raises(WorkflowPrerequisiteError, match="already excluded branch"):
        resolve_event_lifecycle_history(repository, event_ref(), root)


def test_event_correction_missing_transition_head_is_rejected(tmp_path: Path) -> None:
    repository, root = _seed_root(tmp_path, status="active")
    _store_root_branches(repository, ("lct_evt_actual", "active"))
    repository.create_work_record(
        event_ref(),
        _correction(
            "lhc_evt_missing",
            replaced="lct_evt_missing",
            replacement="lct_evt_actual",
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing transition head"):
        resolve_event_lifecycle_history(repository, event_ref(), root)
