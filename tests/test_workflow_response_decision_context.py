"""Focused Slice 3 tests for Response Review/Determination context."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import ResponseWorkflowService
from portia.workflows import responses as responses_module
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "response"
)


def _response(path: str, *, section: str = "valid") -> PortiaRecord:
    value = json.loads((_FIXTURE_ROOT / section / path).read_text(encoding="utf-8"))
    return parse_portia_record("response", "1", value)


def _event_for(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _service(
    tmp_path: Path,
    *,
    module_authority: object | None = None,
) -> tuple[ResponseWorkflowService, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="event",
            contract_version="2",
            status="active",
        )
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    service = ResponseWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
        module_authority=module_authority,
    )
    return service, repository


class _FakeReviewService:
    instances: list[_FakeReviewService] = []
    error: Exception | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.loaded: list[object] = []
        type(self).instances.append(self)

    def load_exact(self, reference: object) -> SimpleNamespace:
        self.loaded.append(reference)
        if type(self).error is not None:
            raise type(self).error
        return SimpleNamespace(record=SimpleNamespace(status="superseded"))


class _FakeDeterminationService:
    instances: list[_FakeDeterminationService] = []
    exact_error: Exception | None = None
    current_error: Exception | None = None

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.exact: list[object] = []
        self.current: list[object] = []
        type(self).instances.append(self)

    def load_exact(self, reference: object) -> SimpleNamespace:
        self.exact.append(reference)
        if type(self).exact_error is not None:
            raise type(self).exact_error
        return SimpleNamespace(record=SimpleNamespace(status="superseded"))

    def require_current_use(self, reference: object) -> SimpleNamespace:
        self.current.append(reference)
        if type(self).current_error is not None:
            raise type(self).current_error
        return SimpleNamespace(record=SimpleNamespace(status="active"))


@pytest.fixture(autouse=True)
def _reset_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeReviewService.instances.clear()
    _FakeReviewService.error = None
    _FakeDeterminationService.instances.clear()
    _FakeDeterminationService.exact_error = None
    _FakeDeterminationService.current_error = None
    monkeypatch.setattr(
        responses_module,
        "ReviewWorkflowService",
        _FakeReviewService,
    )
    monkeypatch.setattr(
        responses_module,
        "DeterminationWorkflowService",
        _FakeDeterminationService,
    )


def test_review_context_uses_public_exact_review_authority(tmp_path: Path) -> None:
    candidate = _response("review-context.json")
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    review_service = _FakeReviewService.instances[-1]
    assert len(review_service.loaded) == 1
    reference = review_service.loaded[0]
    assert reference.record_ref.record_id == "rvw_response_context"
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_superseded_review_context_remains_exact_historical_context(
    tmp_path: Path,
) -> None:
    candidate = _response("review-context.json")
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    assert len(_FakeReviewService.instances[-1].loaded) == 1
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_recorded_institutional_active_requires_current_determination(
    tmp_path: Path,
) -> None:
    candidate = _response("recorded-institutional-consequence.json")
    work = _event_for(candidate)
    authority = object()
    service, repository = _service(tmp_path, module_authority=authority)

    service.create(work, candidate)

    determination_service = _FakeDeterminationService.instances[-1]
    assert determination_service.exact == []
    assert len(determination_service.current) == 1
    reference = determination_service.current[0]
    assert reference.record_ref.record_id == "det_institutional_001"
    assert determination_service.kwargs["module_authority"] is authority
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_recorded_institutional_current_authority_failure_blocks_write(
    tmp_path: Path,
) -> None:
    candidate = _response("recorded-institutional-consequence.json")
    work = _event_for(candidate)
    service, repository = _service(tmp_path)
    _FakeDeterminationService.current_error = WorkflowPrerequisiteError(
        "not current"
    )

    with pytest.raises(WorkflowPrerequisiteError, match="not current"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_proposed_institutional_response_only_resolves_exact_determination(
    tmp_path: Path,
) -> None:
    wire = _response("recorded-institutional-consequence.json").to_dict()
    wire["status"] = "proposed"
    candidate = parse_portia_record("response", "1", wire)
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    determination_service = _FakeDeterminationService.instances[-1]
    assert len(determination_service.exact) == 1
    assert determination_service.current == []
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_ordinary_determination_context_is_historical_not_current_gate(
    tmp_path: Path,
) -> None:
    wire = _response("event-classroom-management.json").to_dict()
    source = _response("recorded-institutional-consequence.json").to_dict()
    wire["determination_ref"] = source["determination_ref"]
    candidate = parse_portia_record("response", "1", wire)
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    determination_service = _FakeDeterminationService.instances[-1]
    assert len(determination_service.exact) == 1
    assert determination_service.current == []
    repository.create_work_record.assert_called_once_with(work, candidate)


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("review-ref-other-event.json", "review_ref must belong to the same Event"),
        (
            "determination-ref-other-event.json",
            "determination_ref must belong to the same Event",
        ),
    ],
)
def test_cross_event_context_is_rejected_before_public_resolution(
    tmp_path: Path,
    filename: str,
    expected: str,
) -> None:
    candidate = _response(filename, section="application-invalid")
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(WorkflowOwnershipError, match=expected):
        service.create(work, candidate)

    assert _FakeReviewService.instances == []
    assert _FakeDeterminationService.instances == []
    repository.create_work_record.assert_not_called()


def test_review_authority_resolution_failure_blocks_write(tmp_path: Path) -> None:
    candidate = _response("review-context.json")
    work = _event_for(candidate)
    service, repository = _service(tmp_path)
    _FakeReviewService.error = WorkflowOwnershipError("missing exact Review")

    with pytest.raises(WorkflowOwnershipError, match="missing exact Review"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


@pytest.mark.parametrize("provider_kind", ["roster_student", "descriptive_person"])
def test_institutional_consequence_rejects_unqualified_provider_forms(
    tmp_path: Path,
    provider_kind: str,
) -> None:
    wire = _response("recorded-institutional-consequence.json").to_dict()
    if provider_kind == "roster_student":
        wire["provider"] = {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": wire["class_id"],
                "student_id": "student_provider_001",
            },
            "display_snapshot": {
                "display_name": "Synthetic student provider",
            },
        }
    else:
        wire["provider"] = {
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic staff description",
        }
    candidate = parse_portia_record("response", "1", wire)
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="identified provider resolved through current local or Actor authority",
    ):
        service.create(work, candidate)

    assert _FakeDeterminationService.instances == []
    repository.create_work_record.assert_not_called()


def test_actor_form_can_reach_public_determination_gate(tmp_path: Path) -> None:
    wire = _response("recorded-institutional-consequence.json").to_dict()
    wire["provider"] = {
        "kind": "actor",
        "actor_ref": {
            "actor_id": "actr_school_staff_001",
        },
        "display_snapshot": {
            "display_name": "Synthetic exact staff Actor",
        },
    }
    candidate = parse_portia_record("response", "1", wire)
    work = _event_for(candidate)
    service, repository = _service(tmp_path)
    service.contexts.actors.load_actor.return_value = SimpleNamespace(record="actor")

    service.create(work, candidate)

    assert len(_FakeDeterminationService.instances[-1].current) == 1
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_review_and_determination_context_can_coexist_without_target_rewrite(
    tmp_path: Path,
) -> None:
    wire = _response("review-context.json").to_dict()
    source = _response("recorded-institutional-consequence.json").to_dict()
    wire["determination_ref"] = source["determination_ref"]
    candidate = parse_portia_record("response", "1", wire)
    work = _event_for(candidate)
    service, repository = _service(tmp_path)

    service.create(work, candidate)

    assert len(_FakeReviewService.instances[-1].loaded) == 1
    assert len(_FakeDeterminationService.instances[-1].exact) == 1
    repository.create_work_record.assert_called_once_with(work, candidate)
