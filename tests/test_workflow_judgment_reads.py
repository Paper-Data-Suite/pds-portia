from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef, ModuleWorkRecordRef
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ReviewWorkflowService,
    account_reference,
    classification_reference,
    determination_reference,
    hypothesis_reference,
    resolve_judgment_evidence,
    review_reference,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from tests.workflow_helpers import account_wire, event_record, event_ref

FIXTURES = Path("tests/schema_validation/fixtures")


def _fixture(path: str) -> dict[str, object]:
    value = json.loads((FIXTURES / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _store_judgment_fixture(
    tmp_path: Path,
    *,
    contract: str,
    fixture_path: str,
):
    value = _fixture(fixture_path)
    class_id = value["class_id"]
    work_id = value["work_id"]
    assert isinstance(class_id, str)
    assert isinstance(work_id, str)
    work = event_ref(class_id=class_id, event_id=work_id)
    repository = PortiaRepository(tmp_path)
    repository.create_work(
        work,
        event_record(class_id=class_id, event_id=work_id, status="active"),
    )
    record = parse_portia_record(contract, "1", value)
    repository.create_work_record(work, record)
    return repository, work, record


@pytest.mark.parametrize(
    ("contract", "fixture_path", "service_type", "reference_factory"),
    [
        (
            "review",
            "issue-16/review/valid/completed-without-finding-or-evidence.json",
            ReviewWorkflowService,
            review_reference,
        ),
        (
            "classification",
            "issue-16/classification/valid/event-target.json",
            ClassificationWorkflowService,
            classification_reference,
        ),
        (
            "hypothesis",
            "issue-16/hypothesis/valid/event-under-consideration-empty-evidence.json",
            HypothesisWorkflowService,
            hypothesis_reference,
        ),
        (
            "determination",
            "issue-16/determination/valid/insufficient-information.json",
            DeterminationWorkflowService,
            determination_reference,
        ),
    ],
)
def test_judgment_services_preserve_exact_v1_history(
    tmp_path: Path,
    contract: str,
    fixture_path: str,
    service_type: type,
    reference_factory: object,
) -> None:
    repository, work, record = _store_judgment_fixture(
        tmp_path,
        contract=contract,
        fixture_path=fixture_path,
    )
    service = service_type(tmp_path, repository=repository)
    identifier = record.logical_id
    assert identifier is not None
    reference = reference_factory(work, identifier)

    assert service.load_exact(reference).record.to_dict() == record.to_dict()
    assert [item.record.logical_id for item in service.list(work)] == [identifier]


def test_judgment_references_require_exact_event_v2_owner() -> None:
    support = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )
    old_event = event_ref(version="1")

    with pytest.raises(WorkflowOwnershipError):
        review_reference(support, "rvw_alpha")
    with pytest.raises(WorkflowOwnershipError):
        classification_reference(old_event, "cls_alpha")


def test_judgment_service_rejects_wrong_family_reference(tmp_path: Path) -> None:
    repository, work, record = _store_judgment_fixture(
        tmp_path,
        contract="review",
        fixture_path="issue-16/review/valid/completed-without-finding-or-evidence.json",
    )
    identifier = record.logical_id
    assert identifier is not None

    with pytest.raises(WorkflowOwnershipError):
        ClassificationWorkflowService(tmp_path, repository=repository).load_exact(
            review_reference(work, identifier)
        )


def test_judgment_evidence_resolves_exact_portia_work_and_record(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    account = parse_portia_record("account", "1", account_wire())
    repository.create_work_record(work, account)

    work_result = resolve_judgment_evidence(
        repository,
        {"kind": "portia_work", "work_ref": work.to_dict()},
    )
    record_result = resolve_judgment_evidence(
        repository,
        {
            "kind": "portia_record",
            "work_record_ref": account_reference(
                work, "acct_alpha", version="1"
            ).to_dict(),
        },
    )

    assert work_result.kind == "portia_work"
    assert work_result.stored is not None
    assert work_result.stored.record.logical_id == "evt_alpha"
    assert record_result.kind == "portia_record"
    assert record_result.stored is not None
    assert record_result.stored.record.logical_id == "acct_alpha"
    assert record_result.stored.record.contract_version == "1"


class _ModuleAuthority:
    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        return {
            "module_id": reference.work_ref.module_id,
            "record_id": reference.record_ref.record_id,
        }


def _module_evidence() -> dict[str, object]:
    return {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "quillan",
                "class_id": "eng10_p2_2026",
                "work_id": "asg_issue16_cls",
            },
            "record_ref": {
                "module_id": "quillan",
                "record_kind": "response",
                "record_id": "resp_issue16_cls",
                "contract_version": "1",
            },
        },
    }


def test_module_judgment_evidence_fails_closed_without_public_authority(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError):
        resolve_judgment_evidence(repository, _module_evidence())


def test_module_judgment_evidence_uses_explicit_authority(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)

    result = resolve_judgment_evidence(
        repository,
        _module_evidence(),
        module_authority=_ModuleAuthority(),
    )

    assert result.kind == "module_record"
    assert result.module_reference is not None
    assert result.module_reference.work_ref.module_id == "quillan"
    assert result.module_value == {
        "module_id": "quillan",
        "record_id": "resp_issue16_cls",
    }


def test_module_judgment_evidence_rejects_nested_module_mismatch(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    value = _module_evidence()
    nested = value["module_work_record_ref"]
    assert isinstance(nested, dict)
    record_ref = nested["record_ref"]
    assert isinstance(record_ref, dict)
    record_ref["module_id"] = "scoreform"

    with pytest.raises(WorkflowOwnershipError):
        resolve_judgment_evidence(
            repository,
            value,
            module_authority=_ModuleAuthority(),
        )
