from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.response_lifecycle import require_response_lifecycle_reconciled
from portia.workflows.responses import ResponseWorkflowService, response_reference

FIXTURES = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "response"
)


def _response(filename: str, *, section: str = "valid") -> PortiaRecord:
    value = json.loads((FIXTURES / section / filename).read_text(encoding="utf-8"))
    return parse_portia_record("response", "1", value)


def _work(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _event(work: ExactPortiaWorkRef, *, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        contract="event",
        contract_version="2",
        class_id=work.class_id,
        work_id=work.work_id,
        logical_id=work.work_id,
        status=status,
    )


def _stored(record: PortiaRecord) -> SimpleNamespace:
    return SimpleNamespace(record=record)


def _service(
    tmp_path: Path,
    response: PortiaRecord,
    *,
    event_status: str = "active",
) -> tuple[ResponseWorkflowService, Mock, Mock, Mock]:
    repository = Mock()
    repository.load_work.side_effect = lambda selected: SimpleNamespace(
        record=_event(selected, status=event_status)
    )
    repository.load_work_record.return_value = _stored(response)
    repository.list_work_records.return_value = ()
    quarantine = Mock()
    contexts = Mock()
    service = ResponseWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=quarantine,
        context_assembler=contexts,
    )
    return service, repository, quarantine, contexts


def test_active_digital_response_qualifies_for_current_use(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    service, repository, quarantine, contexts = _service(tmp_path, response)

    stored = service.require_current_use(
        response_reference(work, response.logical_id or "missing")
    )

    assert stored.record is response
    contexts.rosters.resolve_reference.assert_not_called()
    quarantine.require_allowed.assert_any_call(
        {"kind": "work", "work_ref": work.to_dict()},
        "block_current_use",
    )
    repository.list_work_records.assert_called_with(
        work,
        "lifecycle_transition",
        version="1",
    )


def test_resolve_current_is_current_use_alias(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    service, _repository, _quarantine, _contexts = _service(tmp_path, response)

    assert service.resolve_current(
        response_reference(work, response.logical_id or "missing")
    ).record is response


def test_proposed_response_is_not_current(tmp_path: Path) -> None:
    wire = _response("event-classroom-management.json").to_dict()
    wire["status"] = "proposed"
    response = parse_portia_record("response", "1", wire)
    work = _work(response)
    service, _repository, _quarantine, _contexts = _service(tmp_path, response)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="active canonical Response",
    ):
        service.require_current_use(
            response_reference(work, response.logical_id or "missing")
        )


def test_active_import_fails_current_materialization(tmp_path: Path) -> None:
    response = _response("active-import.json", section="application-invalid")
    work = _work(response)
    service, _repository, _quarantine, _contexts = _service(tmp_path, response)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="reviewed materialization",
    ):
        service.require_current_use(
            response_reference(work, response.logical_id or "missing")
        )


def test_current_response_requires_current_event(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        response,
        event_status="draft",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="Event status"):
        service.require_current_use(
            response_reference(work, response.logical_id or "missing")
        )


def test_current_participant_target_must_remain_active(tmp_path: Path) -> None:
    response = _response("participant-redirection.json")
    work = _work(response)
    service, repository, _quarantine, _contexts = _service(tmp_path, response)
    participant = SimpleNamespace(
        contract="event_participant",
        contract_version="3",
        logical_id="ep_student_a",
        status="inactive",
    )

    def load_record(
        selected_work: object,
        kind: str,
        version: str,
        identifier: str,
    ) -> SimpleNamespace:
        if kind == "response":
            return _stored(response)
        assert selected_work == work
        assert (kind, version, identifier) == (
            "event_participant",
            "3",
            "ep_student_a",
        )
        return SimpleNamespace(record=participant)

    repository.load_work_record.side_effect = load_record

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="target Participant must be active",
    ):
        service.require_current_use(
            response_reference(work, response.logical_id or "missing")
        )


def test_current_actor_provider_uses_current_actor_authority(tmp_path: Path) -> None:
    wire = _response("event-classroom-management.json").to_dict()
    wire["provider"] = {
        "kind": "actor",
        "actor_ref": {"actor_id": "actr_current_provider"},
        "display_snapshot": {"display_name": "Synthetic current provider"},
    }
    response = parse_portia_record("response", "1", wire)
    work = _work(response)
    service, _repository, _quarantine, contexts = _service(tmp_path, response)
    contexts.actors.load_actor.return_value = SimpleNamespace(record="actor")

    service.require_current_use(
        response_reference(work, response.logical_id or "missing")
    )

    contexts.actors.load_actor.assert_called_once()
    assert contexts.actors.load_actor.call_args.kwargs["require_current_use"] is True


def test_current_response_applies_exact_record_quarantine(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    service, _repository, quarantine, _contexts = _service(tmp_path, response)

    service.require_current_use(
        response_reference(work, response.logical_id or "missing")
    )

    calls = quarantine.require_allowed.call_args_list
    assert any(call.args[1] == "block_current_use" for call in calls)
    assert any(
        call.args[0].get("kind") == "work_record"
        and call.args[1] == "block_current_use"
        for call in calls
    )


class _Transition:
    contract = "lifecycle_transition"
    contract_version = "1"

    def __init__(
        self,
        transition_id: str,
        target: dict[str, object],
        *,
        from_status: str,
        to_status: str,
        previous_transition: dict[str, object] | None = None,
    ) -> None:
        self.logical_id = transition_id
        self._values = {
            "target": target,
            "from_status": from_status,
            "to_status": to_status,
            "previous_transition": previous_transition,
        }

    def field(self, name: str) -> object:
        return self._values.get(name)


def _transition_target(response: PortiaRecord) -> dict[str, object]:
    assert response.logical_id is not None
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "response",
            "record_id": response.logical_id,
            "contract_version": "1",
        },
    }


def _previous(transition_id: str) -> dict[str, object]:
    return {
        "record_kind": "lifecycle_transition",
        "record_id": transition_id,
        "contract_version": "1",
    }


def test_matching_lifecycle_head_reconciles(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    target = _transition_target(response)
    transition = _Transition(
        "lct_response_active",
        target,
        from_status="proposed",
        to_status="active",
    )
    repository = Mock()
    repository.list_work_records.return_value = (
        SimpleNamespace(record=transition),
    )

    state = require_response_lifecycle_reconciled(repository, work, response)

    assert state.head is not None
    assert state.selected_status == "active"


def test_lifecycle_head_must_match_canonical_status(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    target = _transition_target(response)
    transition = _Transition(
        "lct_response_invalidated",
        target,
        from_status="active",
        to_status="invalidated",
    )
    repository = Mock()
    repository.list_work_records.return_value = (
        SimpleNamespace(record=transition),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not reconcile",
    ):
        require_response_lifecycle_reconciled(repository, work, response)


def test_lifecycle_missing_predecessor_fails_closed(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    target = _transition_target(response)
    transition = _Transition(
        "lct_response_active",
        target,
        from_status="proposed",
        to_status="active",
        previous_transition=_previous("lct_missing"),
    )
    repository = Mock()
    repository.list_work_records.return_value = (
        SimpleNamespace(record=transition),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="missing predecessor",
    ):
        require_response_lifecycle_reconciled(repository, work, response)


def test_lifecycle_fork_fails_closed(tmp_path: Path) -> None:
    response = _response("event-classroom-management.json")
    work = _work(response)
    target = _transition_target(response)
    root = _Transition(
        "lct_root",
        target,
        from_status="proposed",
        to_status="active",
    )
    left = _Transition(
        "lct_left",
        target,
        from_status="active",
        to_status="invalidated",
        previous_transition=_previous("lct_root"),
    )
    right = _Transition(
        "lct_right",
        target,
        from_status="active",
        to_status="superseded",
        previous_transition=_previous("lct_root"),
    )
    repository = Mock()
    repository.list_work_records.return_value = tuple(
        SimpleNamespace(record=value) for value in (root, left, right)
    )

    with pytest.raises(WorkflowPrerequisiteError, match="fork"):
        require_response_lifecycle_reconciled(repository, work, response)
