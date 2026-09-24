from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from portia.menu.authoring import (
    AccountCorrectionInput,
    AccountRetractionInput,
    EvidenceInvalidationInput,
    ObservationCorrectionInput,
    event_summary_amendment_change,
    prepare_account_retraction,
    prepare_account_statement_correction,
    prepare_evidence_invalidation,
    prepare_observation_content_correction,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.correction import launch_correct_retract_menu
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.main import launch_menu
from portia.models import PortiaRecord, parse_portia_record
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    account_reference,
    observation_reference,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

LATER = "2026-08-26T12:05:00-04:00"


def _clock() -> MenuClock:
    return MenuClock(
        now_source=lambda: datetime.fromisoformat(LATER)
    )


def _ids(*tokens: str) -> PortiaIdGenerator:
    values = iter(tokens)
    return PortiaIdGenerator(lambda: next(values))


def _account() -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": "acct_alpha",
            "status": "active",
            "target": {"kind": "event"},
            "source": {"kind": "local_operator", "display_label": "Synthetic Source"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [{"representation": "recorded_summary", "text": "Original report."}],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _observation() -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "observation_id": "obs_alpha",
            "status": "active",
            "target": {"kind": "event"},
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Observer",
                },
            },
            "method": "live_direct",
            "content": {"narrative": "Original direct observation."},
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_event_summary_amendment_change_declares_exact_before_after() -> None:
    change = event_summary_amendment_change(
        event_record(status="draft"),
        "Corrected neutral classroom context.",
    )
    assert change == {
        "path": "/summary",
        "operation": "replace",
        "before": {"present": True, "value": "Synthetic neutral classroom context."},
        "after": {"present": True, "value": "Corrected neutral classroom context."},
    }


def test_account_material_correction_builds_exact_successor() -> None:
    successor = prepare_account_statement_correction(
        AccountCorrectionInput(
            event_ref(),
            _account(),
            "Corrected report.",
            "Synthetic Teacher",
        ),
        clock=_clock(),
        ids=_ids("corrected"),
    )
    assert successor.logical_id == "acct_corrected"
    assert successor.field("content")[0]["text"] == "Corrected report."
    predecessor = successor.field("supersedes")[0]["work_record_ref"]["record_ref"]
    assert predecessor == {
        "record_kind": "account",
        "record_id": "acct_alpha",
        "contract_version": "2",
    }


def test_account_retraction_preserves_source_and_uses_retract_relation() -> None:
    prior = _account()
    retraction = prepare_account_retraction(
        AccountRetractionInput(
            event_ref(),
            prior,
            "The source withdrew the earlier statement.",
            "Synthetic Teacher",
        ),
        clock=_clock(),
        ids=_ids("retraction"),
    )
    assert retraction.logical_id == "acct_retraction"
    assert retraction.field("source") == prior.field("source")
    relation = retraction.field("related_accounts")[0]
    assert relation["relation"] == "retracts"
    assert relation["account_ref"]["record_id"] == "acct_alpha"


def test_observation_material_correction_builds_exact_successor() -> None:
    successor = prepare_observation_content_correction(
        ObservationCorrectionInput(
            event_ref(),
            _observation(),
            "Corrected direct observation.",
            "Synthetic Teacher",
        ),
        clock=_clock(),
        ids=_ids("corrected"),
    )
    assert successor.logical_id == "obs_corrected"
    assert successor.field("content")["narrative"] == "Corrected direct observation."
    assert successor.field("supersedes")[0]["reason"] == "observation_content_corrected"


def test_invalidation_preserves_identity_and_substance() -> None:
    prior = _observation()
    invalidated = prepare_evidence_invalidation(
        EvidenceInvalidationInput(prior, "Synthetic Teacher"),
        clock=_clock(),
    )
    assert invalidated.logical_id == prior.logical_id
    assert invalidated.status == "invalidated"
    assert invalidated.field("content") == prior.field("content")
    assert invalidated.field("created_at") == prior.field("created_at")


def test_prepared_account_correction_executes_through_canonical_service(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    prior = service.create(event_ref(), _account())
    successor = prepare_account_statement_correction(
        AccountCorrectionInput(
            event_ref(),
            prior.record,
            "Corrected report.",
            "Synthetic Teacher",
        ),
        clock=_clock(),
        ids=_ids("corrected"),
    )
    service.correct(
        account_reference(event_ref(), "acct_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_correct_menu",
        operation_id="op_correct_menu",
    )
    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "superseded"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_corrected")
    ).record.field("content")[0]["text"] == "Corrected report."


def test_prepared_account_retraction_executes_through_canonical_service(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = AccountWorkflowService(tmp_path)
    prior = service.create(event_ref(), _account())
    retraction = prepare_account_retraction(
        AccountRetractionInput(
            event_ref(),
            prior.record,
            "The source withdrew the earlier statement.",
            "Synthetic Teacher",
        ),
        clock=_clock(),
        ids=_ids("retraction"),
    )
    service.retract(
        account_reference(event_ref(), "acct_alpha"),
        retraction,
        expected=prior.fingerprint,
        transition_id="lct_retract_menu",
        operation_id="op_retract_menu",
    )
    assert service.load_exact(
        account_reference(event_ref(), "acct_alpha")
    ).record.status == "retracted"
    assert service.require_current_use(
        account_reference(event_ref(), "acct_retraction")
    ).record.status == "active"


def test_prepared_observation_invalidation_executes_through_lifecycle(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ObservationWorkflowService(tmp_path)
    prior = service.create(event_ref(), _observation())
    candidate = prepare_evidence_invalidation(
        EvidenceInvalidationInput(prior.record, "Synthetic Teacher"),
        clock=_clock(),
    )
    service.transition_lifecycle(
        observation_reference(event_ref(), "obs_alpha"),
        candidate,
        expected=prior.fingerprint,
        transition_id="lct_invalidate_menu",
        reason_code="recording_error",
        operation_id="op_invalidate_menu",
    )
    assert service.load_exact(
        observation_reference(event_ref(), "obs_alpha")
    ).record.status == "invalidated"


def test_correct_retract_menu_entry_is_zero_read_until_work_selection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("b",))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    launch_correct_retract_menu(MenuSessionContext())
    output = capsys.readouterr().out
    assert "Correct / Retract" in output
    assert "Choose an Event or Support Process" in output


def test_main_menu_routes_to_correct_retract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("7", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Correct / Retract" in output
    assert "Choose an Event or Support Process" in output
