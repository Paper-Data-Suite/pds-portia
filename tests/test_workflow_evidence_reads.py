from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaCorruptionError
from portia.storage.paths import work_record_path
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    AccountWorkflowService,
    ObservationWorkflowService,
    account_reference,
    observation_reference,
)
from portia.workflows.errors import WorkflowOwnershipError
from tests.workflow_helpers import event_record, event_ref

FIXTURES = Path("tests/schema_validation/fixtures")


def _fixture(path: str) -> dict[str, object]:
    value = json.loads((FIXTURES / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _event_repository(tmp_path: Path) -> tuple[PortiaRepository, ExactPortiaWorkRef]:
    repository = PortiaRepository(tmp_path)
    work = event_ref(class_id="eng10_p2_2026", event_id="evt_alpha")
    repository.create_work(
        work,
        event_record(
            class_id="eng10_p2_2026",
            event_id="evt_alpha",
            status="draft",
        ),
    )
    return repository, work


def test_account_collection_preserves_exact_v1_and_v2(tmp_path: Path) -> None:
    repository, work = _event_repository(tmp_path)
    v1 = parse_portia_record(
        "account",
        "1",
        _fixture("issue-15/account/valid/minimum-active.json"),
    )
    v2 = parse_portia_record(
        "account",
        "2",
        _fixture("issue-19/account-v2/valid/event-active.json"),
    )
    repository.create_work_record(work, v1)
    repository.create_work_record(work, v2)

    listed = repository.list_accounts(work)

    assert {(item.record.contract_version, item.record.logical_id) for item in listed} == {
        ("1", "acct_student_report_1"),
        ("2", "acct_v2_alpha"),
    }
    service = AccountWorkflowService(tmp_path, repository=repository)
    assert service.load_exact(
        account_reference(work, "acct_student_report_1", version="1")
    ).record.to_dict() == v1.to_dict()
    assert service.load_exact(
        account_reference(work, "acct_v2_alpha")
    ).record.to_dict() == v2.to_dict()


def test_observation_collection_preserves_exact_v1_and_v2(tmp_path: Path) -> None:
    repository, work = _event_repository(tmp_path)
    v1 = parse_portia_record(
        "observation",
        "1",
        _fixture("issue-15/observation/valid/minimum-active.json"),
    )
    v2 = parse_portia_record(
        "observation",
        "2",
        _fixture("issue-19/observation-v2/valid/event-manual-count.json"),
    )
    repository.create_work_record(work, v1)
    repository.create_work_record(work, v2)

    service = ObservationWorkflowService(tmp_path, repository=repository)
    listed = service.list_observations(work)

    assert {item.record.contract_version for item in listed} == {"1", "2"}
    for item in listed:
        identifier = item.record.logical_id
        assert identifier is not None
        loaded = service.load_exact(
            observation_reference(
                work,
                identifier,
                version=item.record.contract_version,
            )
        )
        assert loaded.record.to_dict() == item.record.to_dict()


def test_v1_evidence_cannot_use_support_process_owner() -> None:
    support = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )

    with pytest.raises(WorkflowOwnershipError):
        account_reference(support, "acct_alpha", version="1")
    with pytest.raises(WorkflowOwnershipError):
        observation_reference(support, "obs_alpha", version="1")


def test_mixed_version_enumeration_surfaces_unknown_version_as_corruption(
    tmp_path: Path,
) -> None:
    repository, work = _event_repository(tmp_path)
    record = parse_portia_record(
        "account",
        "2",
        _fixture("issue-19/account-v2/valid/event-active.json"),
    )
    stored = repository.create_work_record(work, record)
    value = record.to_dict()
    value["schema_version"] = "99"
    stored.path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(PortiaCorruptionError):
        repository.list_accounts(work)


def test_reserved_staging_directory_is_ignored_by_uniform_enumeration(
    tmp_path: Path,
) -> None:
    repository, work = _event_repository(tmp_path)
    collection = work_record_path(
        tmp_path, work, "lifecycle_transition", "bounded_collection_probe"
    ).parent
    staging = collection / ".portia-staging" / "op_partial"
    staging.mkdir(parents=True)
    (staging / "step_pending.candidate").write_bytes(b"pending")

    assert repository.list_work_records(
        work, "lifecycle_transition", version="1"
    ) == ()


def test_reserved_staging_directory_is_not_canonical_collection_content(
    tmp_path: Path,
) -> None:
    repository, work = _event_repository(tmp_path)
    record = parse_portia_record(
        "account",
        "2",
        _fixture("issue-19/account-v2/valid/event-active.json"),
    )
    stored = repository.create_work_record(work, record)
    staging = stored.path.parent / ".portia-staging" / "op_partial"
    staging.mkdir(parents=True)
    (staging / "step_pending.candidate").write_bytes(b"pending")

    listed = repository.list_accounts(work)

    assert [item.record.logical_id for item in listed] == [record.logical_id]


def test_nonreserved_directory_remains_collection_corruption(tmp_path: Path) -> None:
    repository, work = _event_repository(tmp_path)
    record = parse_portia_record(
        "account",
        "2",
        _fixture("issue-19/account-v2/valid/event-active.json"),
    )
    stored = repository.create_work_record(work, record)
    (stored.path.parent / "unexpected-directory").mkdir()

    with pytest.raises(PortiaCorruptionError):
        repository.list_accounts(work)
