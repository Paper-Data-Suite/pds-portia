"""Focused Slice 9 tests for Communication current-use qualification."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import fingerprint_bytes
from portia.workflows import (
    CommunicationWorkflowService,
    communication_reference,
)
from portia.workflows.errors import WorkflowPrerequisiteError

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "communication"
)


def _wire(path: str, *, section: str = "valid") -> dict[str, object]:
    return json.loads(
        (_FIXTURE_ROOT / section / path).read_text(encoding="utf-8")
    )


def _communication(path: str, *, section: str = "valid") -> PortiaRecord:
    return parse_portia_record("communication", "1", _wire(path, section=section))


def _work(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    assert record.work_kind in {"event", "support_process"}
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind=record.work_kind,
        contract_version="2" if record.work_kind == "event" else "1",
    )


def _dependency(
    kind: str,
    identifier: str,
    *,
    status: str = "superseded",
    version: str = "1",
) -> SimpleNamespace:
    return SimpleNamespace(
        contract=kind,
        contract_version=version,
        logical_id=identifier,
        status=status,
    )


def _event(*, status: str = "active") -> SimpleNamespace:
    return SimpleNamespace(
        contract="event",
        contract_version="2",
        status=status,
    )


def _service(
    tmp_path: Path,
    communication: PortiaRecord,
    *,
    event_status: str = "active",
    module_authority: object | None = None,
    predecessors: dict[str, PortiaRecord] | None = None,
) -> tuple[CommunicationWorkflowService, Mock, Mock, Mock]:
    repository = Mock()
    work = _work(communication)
    repository.load_work.return_value = SimpleNamespace(
        record=_event(status=event_status)
    )

    def load_record(
        selected_work: ExactPortiaWorkRef,
        kind: str,
        version: str,
        identifier: str,
    ) -> SimpleNamespace:
        if selected_work == work and kind == "communication":
            if identifier == communication.logical_id:
                return SimpleNamespace(record=communication)
            if predecessors is not None and identifier in predecessors:
                return SimpleNamespace(record=predecessors[identifier])
        return SimpleNamespace(record=_dependency(kind, identifier, version=version))

    repository.load_work_record.side_effect = load_record
    repository.list_work_records.return_value = ()
    quarantine = Mock()
    contexts = Mock()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=quarantine,
        context_assembler=contexts,
        module_attachment_authority=module_authority,
    )
    return service, repository, quarantine, contexts


def _reference(record: PortiaRecord):
    return communication_reference(_work(record), record.logical_id or "missing")


def test_active_digital_event_communication_qualifies(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, repository, quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    stored = service.require_current_use(_reference(communication))

    assert stored.record is communication
    repository.list_work_records.assert_called_once_with(
        _work(communication),
        "lifecycle_transition",
        version="1",
    )
    assert any(
        call.args[0].get("kind") == "work_record"
        and call.args[1] == "block_current_use"
        for call in quarantine.require_allowed.call_args_list
    )


def test_resolve_current_is_current_use_alias(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    assert service.resolve_current(_reference(communication)).record is communication


def test_proposed_communication_is_not_current(tmp_path: Path) -> None:
    value = _wire("student-in-person.json")
    value["status"] = "proposed"
    communication = parse_portia_record("communication", "1", value)
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(_reference(communication))


def test_active_import_fails_current_materialization(tmp_path: Path) -> None:
    communication = _communication("active-import.json", section="application-invalid")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="reviewed materialization"):
        service.require_current_use(_reference(communication))


def test_support_process_current_use_uses_issue44_owner_authority(
    tmp_path: Path,
) -> None:
    communication = _communication(
        "support-process-owner-before-issue18.json",
        section="application-invalid",
    )
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="support_process",
            contract_version="1",
            status="active",
        )
    )

    with patch(
        "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use"
    ) as require_support_process_current:
        stored = service.require_current_use(_reference(communication))

    assert stored.record is communication
    require_support_process_current.assert_called_once_with(_work(communication))
    assert repository.load_work_record.call_count >= 1


def test_current_communication_requires_current_event(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
        event_status="draft",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="Event status"):
        service.require_current_use(_reference(communication))


def test_current_actor_and_contact_point_use_current_authority(tmp_path: Path) -> None:
    communication = _communication("completed-family-phone.json")
    service, _repository, _quarantine, contexts = _service(
        tmp_path,
        communication,
    )

    service.require_current_use(_reference(communication))

    contexts.actors.load_actor.assert_called_once_with(
        ExactActorRef(actor_id="actr_family_001", contract_version="1"),
        require_current_use=True,
    )
    contexts.actors.load_contact_point.assert_called_once_with(
        ExactActorContactPointRef(
            actor_id="actr_family_001",
            contact_point_id="acp_family_phone_001",
            contract_version="1",
        ),
        require_current_use=True,
    )


def test_restricted_privacy_scope_is_handling_metadata_not_authorization(
    tmp_path: Path,
) -> None:
    value = _wire("student-in-person.json")
    value["privacy_scope"] = "restricted"
    communication = parse_portia_record("communication", "1", value)
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    stored = service.require_current_use(_reference(communication))
    assert stored.record is communication


def test_superseded_relation_target_remains_exact_but_is_quarantined(
    tmp_path: Path,
) -> None:
    communication = _communication("response-relation.json")
    service, repository, quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    service.require_current_use(_reference(communication))

    assert any(
        call.args[0].get("kind") == "work_record"
        and call.args[0]["work_record_ref"]["record_ref"]["record_kind"]
        == "response"
        for call in quarantine.require_allowed.call_args_list
    )
    assert any(
        call.args[1] == "block_current_use"
        for call in quarantine.require_allowed.call_args_list
    )
    assert repository.load_work_record.call_count == 2


def test_superseded_portia_attachment_remains_exact_but_is_quarantined(
    tmp_path: Path,
) -> None:
    communication = _communication("portia-record-attachment.json")
    service, _repository, quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    service.require_current_use(_reference(communication))

    assert any(
        call.args[0].get("kind") == "work_record"
        and call.args[0]["work_record_ref"]["record_ref"]["record_kind"]
        == "review"
        for call in quarantine.require_allowed.call_args_list
    )


def test_workspace_attachment_is_reverified_for_current_use(tmp_path: Path) -> None:
    value = _wire("workspace-file-attachment.json")
    attachment = value["attachments"][0]  # type: ignore[index]
    assert isinstance(attachment, dict)
    path = tmp_path / str(attachment["path"])
    path.parent.mkdir(parents=True)
    original = b"original synthetic attachment\n"
    path.write_bytes(original)
    attachment["fingerprint"] = fingerprint_bytes(original).to_dict()
    communication = parse_portia_record("communication", "1", value)
    path.write_bytes(b"changed after recording\n")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="fingerprint"):
        service.require_current_use(_reference(communication))


def test_current_module_attachment_reuses_explicit_public_authority(
    tmp_path: Path,
) -> None:
    authority = Mock()
    authority.resolve_exact.return_value = object()
    communication = _communication("module-record-attachment.json")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
        module_authority=authority,
    )

    service.require_current_use(_reference(communication))

    authority.resolve_exact.assert_called_once()


def test_current_module_attachment_fails_closed_without_authority(
    tmp_path: Path,
) -> None:
    communication = _communication("module-record-attachment.json")
    service, _repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        service.require_current_use(_reference(communication))


def test_external_attachment_remains_inert_during_current_use(tmp_path: Path) -> None:
    communication = _communication("external-record-attachment.json")
    authority = Mock()
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
        module_authority=authority,
    )

    service.require_current_use(_reference(communication))

    authority.resolve_exact.assert_not_called()
    assert repository.load_work_record.call_count == 1


def test_current_corrected_successor_uses_exact_superseded_predecessor(
    tmp_path: Path,
) -> None:
    communication = _communication("successor-correction.json")
    values = communication.to_dict()["supersedes"]
    assert isinstance(values, list) and len(values) == 1
    reference = ExactPortiaWorkRecordRef.from_dict(values[0]["work_record_ref"])
    prior_wire = communication.to_dict()
    prior_wire["communication_id"] = reference.record_ref.record_id
    prior_wire["status"] = "superseded"
    prior_wire.pop("supersedes", None)
    prior_wire["started_at"] = "2026-08-10T09:20:00-04:00"
    prior_wire["ended_at"] = "2026-08-10T09:25:00-04:00"
    prior = parse_portia_record("communication", "1", prior_wire)
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
        predecessors={reference.record_ref.record_id: prior},
    )

    stored = service.require_current_use(_reference(communication))

    assert stored.record is communication
    assert any(
        call.args == (
            reference.work_ref,
            "communication",
            "1",
            reference.record_ref.record_id,
        )
        for call in repository.load_work_record.call_args_list
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


def _transition_target(communication: PortiaRecord) -> dict[str, object]:
    assert communication.logical_id is not None
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "communication",
            "record_id": communication.logical_id,
            "contract_version": "1",
        },
    }


def _previous(transition_id: str) -> dict[str, object]:
    return {
        "record_kind": "lifecycle_transition",
        "record_id": transition_id,
        "contract_version": "1",
    }


def test_lifecycle_head_must_match_canonical_status(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )
    repository.list_work_records.return_value = (
        SimpleNamespace(
            record=_Transition(
                "lct_comm_invalidated",
                _transition_target(communication),
                from_status="active",
                to_status="invalidated",
            )
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_current_use(_reference(communication))


def test_lifecycle_missing_predecessor_fails_closed(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )
    repository.list_work_records.return_value = (
        SimpleNamespace(
            record=_Transition(
                "lct_comm_active",
                _transition_target(communication),
                from_status="proposed",
                to_status="active",
                previous_transition=_previous("lct_missing"),
            )
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing predecessor"):
        service.require_current_use(_reference(communication))


def test_lifecycle_fork_fails_closed(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, repository, _quarantine, _contexts = _service(
        tmp_path,
        communication,
    )
    target = _transition_target(communication)
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
    repository.list_work_records.return_value = tuple(
        SimpleNamespace(record=value) for value in (root, left, right)
    )

    with pytest.raises(WorkflowPrerequisiteError, match="fork"):
        service.require_current_use(_reference(communication))


def test_current_use_propagates_communication_quarantine(tmp_path: Path) -> None:
    communication = _communication("student-in-person.json")
    service, _repository, quarantine, _contexts = _service(
        tmp_path,
        communication,
    )

    def require_allowed(target: dict[str, object], mode: str) -> None:
        if target.get("kind") == "work_record" and mode == "block_current_use":
            raise RuntimeError("synthetic quarantine block")

    quarantine.require_allowed.side_effect = require_allowed

    with pytest.raises(RuntimeError, match="synthetic quarantine block"):
        service.require_current_use(_reference(communication))
