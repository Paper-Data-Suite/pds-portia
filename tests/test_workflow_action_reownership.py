"""Regression coverage for deterministic cross-work reownership lock order."""

from __future__ import annotations

from portia.models.references import ExactPortiaWorkRef
from portia.storage.orchestration import validate_lock_plan
from portia.workflows.action_reownership import _cross_work_lock_plan


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _support_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def test_cross_work_reownership_lock_plan_matches_storage_total_order() -> None:
    for source, destination in (
        (_event_ref(), _support_ref()),
        (_support_ref(), _event_ref()),
    ):
        entries, _records = _cross_work_lock_plan(
            "op_cross_work_lock_order",
            source,
            destination,
            "2026-09-05T19:00:00-04:00",
        )
        assert validate_lock_plan({"lock_set": entries}) == tuple(entries)
