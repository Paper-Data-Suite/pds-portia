from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ModuleWorkRecordRef
from portia.storage.errors import PortiaNotFoundError, PortiaQuarantinedError
from portia.storage.repository import PortiaRepository
from portia.storage.series import QuarantineStore
from portia.workflows import (
    AccountWorkflowService,
    ReviewWorkflowService,
    account_reference,
    review_reference,
)
from portia.workflows.common import record_target, work_target
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    account_wire,
    event_record,
    event_ref,
    participant_record,
)


def _review_wire(
    *,
    review_id: str = "rvw_alpha",
    status: str = "proposed",
    review_state: str = "open",
    target: dict[str, object] | None = None,
    reviewer: dict[str, object] | None = None,
    evidence: list[dict[str, object]] | None = None,
    creation_source: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "review_id": review_id,
        "status": status,
        "review_state": review_state,
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "evidence_review",
            "text": "What exact information is available for this Event?",
        },
        "target": target or {"kind": "event"},
        "reviewer": reviewer
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "evidence_considered": evidence or [],
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def _review_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("review", "1", _review_wire(**kwargs))


def _descriptive_participant(*, status: str = "active") -> PortiaRecord:
    return participant_record(
        status=status,
        subject={
            "kind": "descriptive_person",
            "description_type": "school_staff",
            "display_label": "Synthetic Staff Member",
        },
    )


def _participant_target() -> dict[str, object]:
    return {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_alpha",
            "contract_version": "3",
        },
    }


def _account_evidence() -> dict[str, object]:
    return {
        "kind": "portia_record",
        "work_record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "account",
                "record_id": "acct_alpha",
                "contract_version": "1",
            },
        },
    }


def _module_evidence() -> dict[str, object]:
    return {
        "kind": "module_record",
        "module_work_record_ref": {
            "work_ref": {
                "module_id": "quillan",
                "class_id": "class_a",
                "work_id": "asg_alpha",
            },
            "record_ref": {
                "module_id": "quillan",
                "record_kind": "response",
                "record_id": "resp_alpha",
                "contract_version": "1",
            },
        },
    }


def _repository_with_event(tmp_path: Path, *, status: str = "active") -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status=status))
    return repository, work


def _activate_quarantine(
    tmp_path: Path,
    *,
    target: dict[str, object],
    effect: str,
    quarantine_id: str,
) -> None:
    record = parse_portia_record(
        "quarantine_record",
        "2",
        {
            "schema_version": "2",
            "record_type": "quarantine_record",
            "module_id": "portia",
            "quarantine_id": quarantine_id,
            "quarantine_revision": 1,
            "previous_quarantine_revision": None,
            "state": "active",
            "target": target,
            "reason": "authorization_limitation",
            "reason_detail": "Synthetic current-use protection.",
            "effects": [effect],
            "origin": {
                "applying_operation": {
                    "operation_id": "op_judgment_quarantine_test",
                    "journal_revision": 1,
                    "contract_version": "2",
                },
                "supporting_finding_keys": [],
                "applied_at": TIMESTAMP,
                "applied_by": AGENT,
                "release_requirements": ["manual_review"],
                "review_deadline": None,
            },
            "resolution": None,
            "created_at": TIMESTAMP,
        },
    )
    pointer = parse_portia_record(
        "quarantine_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "quarantine_current_pointer",
            "module_id": "portia",
            "quarantine_id": quarantine_id,
            "quarantine_revision": 1,
        },
    )
    QuarantineStore(tmp_path).create(record, pointer)


def test_create_proposed_review_uses_guarded_digital_path(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)

    stored = service.create(work, _review_record())

    assert stored.record.logical_id == "rvw_alpha"
    assert stored.record.status == "proposed"
    assert service.load_exact(review_reference(work, "rvw_alpha")).record.to_dict() == stored.record.to_dict()


def test_create_rejects_non_digital_review(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    review = _review_record(creation_source={"type": "import", "source_label": "Synthetic import"})

    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry"):
        ReviewWorkflowService(tmp_path, repository=repository).create(work, review)


def test_active_review_requires_current_event(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path, status="draft")

    with pytest.raises(WorkflowPrerequisiteError, match="current judgment use"):
        ReviewWorkflowService(tmp_path, repository=repository).create(
            work,
            _review_record(status="active"),
        )


def test_active_review_requires_active_participant_target(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, _descriptive_participant(status="proposed"))

    with pytest.raises(WorkflowPrerequisiteError, match="Participant must be active"):
        ReviewWorkflowService(tmp_path, repository=repository).create(
            work,
            _review_record(status="active", target=_participant_target()),
        )


def test_issue16_active_review_accepts_explicit_participant_set_target(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, _descriptive_participant())
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_beta",
            subject={
                "kind": "descriptive_person",
                "description_type": "school_staff",
                "display_label": "Second Synthetic Staff Member",
            },
        ),
    )
    target = {
        "kind": "event_participants",
        "targets": [
            _participant_target(),
            {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_beta",
                    "contract_version": "3",
                },
            },
        ],
    }
    service = ReviewWorkflowService(tmp_path, repository=repository)

    stored = service.create(
        work,
        _review_record(status="active", target=target),
    )
    current = service.require_current_use(review_reference(work, "rvw_alpha"))

    assert stored.record.to_dict()["target"] == target
    assert current.record.to_dict()["target"] == target


def test_active_review_accepts_current_account_evidence(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, _descriptive_participant())
    repository.create_work_record(
        work,
        parse_portia_record("account", "1", account_wire()),
    )
    service = ReviewWorkflowService(tmp_path, repository=repository)

    stored = service.create(
        work,
        _review_record(
            status="active",
            target=_participant_target(),
            evidence=[_account_evidence()],
        ),
    )

    assert stored.record.status == "active"
    assert service.require_current_use(review_reference(work, "rvw_alpha")).record.logical_id == "rvw_alpha"


def test_active_review_rejects_noncurrent_account_at_acceptance(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, _descriptive_participant())
    stale = account_wire(status="invalidated")
    repository.create_work_record(work, parse_portia_record("account", "1", stale))

    with pytest.raises(
        WorkflowPrerequisiteError, match="current Account use requires active evidence"
    ):
        ReviewWorkflowService(tmp_path, repository=repository).create(
            work,
            _review_record(
                status="active",
                target=_participant_target(),
                evidence=[_account_evidence()],
            ),
        )


def test_existing_review_keeps_exact_account_after_later_invalidation(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, _descriptive_participant())
    account = repository.create_work_record(
        work,
        parse_portia_record("account", "1", account_wire()),
    )
    reviews = ReviewWorkflowService(tmp_path, repository=repository)
    stored_review = reviews.create(
        work,
        _review_record(
            status="active",
            target=_participant_target(),
            evidence=[_account_evidence()],
        ),
    )
    review_ref = review_reference(work, "rvw_alpha")
    account_ref = account_reference(work, "acct_alpha", version="1")

    invalidated_data = deepcopy(account.record.to_dict())
    invalidated_data["status"] = "invalidated"
    invalidated_data["updated_at"] = "2026-08-26T12:05:00-04:00"
    invalidated = parse_portia_record("account", "1", invalidated_data)
    accounts = AccountWorkflowService(tmp_path, repository=repository)
    accounts.transition_lifecycle(
        account_ref,
        invalidated,
        expected=account.fingerprint,
        transition_id="lct_account_after_review",
        reason_code="recording_error",
        operation_id="op_account_after_review",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        accounts.require_current_use(account_ref)

    current_review = reviews.require_current_use(review_ref)
    exact_review = reviews.load_exact(review_ref)

    assert current_review.fingerprint == stored_review.fingerprint
    assert exact_review.fingerprint == stored_review.fingerprint
    assert exact_review.record.to_dict() == stored_review.record.to_dict()
    assert exact_review.record.to_dict()["evidence_considered"] == [_account_evidence()]
    assert reviews.load_exact(review_ref).record.status == "active"


def test_proposed_review_preserves_module_evidence_without_adapter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = ReviewWorkflowService(tmp_path, repository=repository).create(
        work,
        _review_record(evidence=[_module_evidence()]),
    )

    assert stored.record.status == "proposed"


def test_active_review_fails_closed_on_module_evidence_without_adapter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        ReviewWorkflowService(tmp_path, repository=repository).create(
            work,
            _review_record(status="active", evidence=[_module_evidence()]),
        )


class _ModuleAuthority:
    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        return {"record_id": reference.record_ref.record_id}


def test_active_review_accepts_module_evidence_through_explicit_adapter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = ReviewWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    ).create(
        work,
        _review_record(status="active", evidence=[_module_evidence()]),
    )

    assert stored.record.status == "active"


def test_current_review_revalidates_module_authority_without_rewriting_history(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    authority_service = ReviewWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    )
    stored = authority_service.create(
        work,
        _review_record(status="active", evidence=[_module_evidence()]),
    )
    reference = review_reference(work, "rvw_alpha")

    unprivileged_service = ReviewWorkflowService(tmp_path, repository=repository)
    exact = unprivileged_service.load_exact(reference)

    assert exact.fingerprint == stored.fingerprint
    assert exact.record.to_dict() == stored.record.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        unprivileged_service.require_current_use(reference)

    current = authority_service.require_current_use(reference)
    assert current.fingerprint == stored.fingerprint
    assert current.record.to_dict() == stored.record.to_dict()


def test_active_imported_review_is_exact_but_fails_current_materialization(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    imported = _review_record(
        status="active",
        creation_source={
            "type": "import",
            "source_label": "Synthetic import",
            "external_reference": "row-22",
        },
    )
    stored = repository.create_work_record(work, imported)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    reference = review_reference(work, "rvw_alpha")

    assert service.load_exact(reference).fingerprint == stored.fingerprint
    with pytest.raises(
        WorkflowPrerequisiteError, match="reviewed materialization"
    ):
        service.require_current_use(reference)


def test_current_use_rejects_unidentified_reviewer(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    review = _review_record(
        status="active",
        reviewer={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    )
    repository.create_work_record(work, review)

    with pytest.raises(WorkflowPrerequisiteError, match="identified represented human"):
        ReviewWorkflowService(tmp_path, repository=repository).require_current_use(
            review_reference(work, "rvw_alpha")
        )


def test_quarantined_review_remains_exactly_readable_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _review_record(status="active"))
    reference = review_reference(work, "rvw_alpha")

    _activate_quarantine(
        tmp_path,
        target=record_target(work, stored.record),
        effect="block_current_use",
        quarantine_id="qnt_review_current_use",
    )

    exact_before = service.load_exact(reference)
    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)
    exact_after = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == stored.record.to_dict()
    assert exact_after.record.status == "active"


def test_work_quarantine_blocks_review_current_use_without_blocking_exact_read(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _review_record(status="active"))
    reference = review_reference(work, "rvw_alpha")

    _activate_quarantine(
        tmp_path,
        target=work_target(work),
        effect="block_current_use",
        quarantine_id="qnt_review_work_current_use",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)

    assert service.load_exact(reference).record.to_dict() == stored.record.to_dict()


def test_work_write_quarantine_does_not_masquerade_as_current_use_block(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _review_record(status="active"))
    reference = review_reference(work, "rvw_alpha")

    _activate_quarantine(
        tmp_path,
        target=work_target(work),
        effect="block_work_writes",
        quarantine_id="qnt_review_work_writes",
    )

    current = service.require_current_use(reference)

    assert current.record.to_dict() == stored.record.to_dict()
    assert current.record.status == "active"


LATER = "2026-08-26T12:05:00-04:00"


def _corrected_review(
    prior: PortiaRecord,
    *,
    review_id: str = "rvw_corrected",
    reason: str = "review_reframed",
    question: dict[str, object] | None = None,
    reviewer: dict[str, object] | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["review_id"] = review_id
    data["question"] = question or {
        "kind": "other",
        "text": "Corrected bounded Review question.",
    }
    if reviewer is not None:
        data["reviewer"] = reviewer
    data["created_at"] = LATER
    data["updated_at"] = LATER
    data["supersedes"] = [
        {
            "work_record_ref": review_reference(
                event_ref(), prior.logical_id or "missing"
            ).to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("review", "1", data)


def test_correct_review_uses_public_coordinated_successor_path(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    prior = service.create(
        work,
        _review_record(status="active", review_state="completed"),
    )
    successor = _corrected_review(prior.record)

    service.correct(
        review_reference(work, "rvw_alpha"),
        successor,
        expected=prior.fingerprint,
        transition_id="lct_review_public_correction",
        operation_id="op_review_public_correction",
    )

    predecessor_after = service.load_exact(
        review_reference(work, "rvw_alpha")
    )
    successor_after = service.require_current_use(
        review_reference(work, "rvw_corrected")
    )
    transition = repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_review_public_correction",
    ).record

    assert predecessor_after.record.status == "superseded"
    assert successor_after.record.to_dict() == successor.to_dict()
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason")["code"] == "review_reframed"


def test_correct_review_revalidates_successor_human_authority(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    prior = service.create(
        work,
        _review_record(status="active", review_state="completed"),
    )
    successor = _corrected_review(
        prior.record,
        reason="reviewer_corrected",
        reviewer={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="identified represented human"):
        service.correct(
            review_reference(work, "rvw_alpha"),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_review_bad_authority",
        )

    assert service.load_exact(
        review_reference(work, "rvw_alpha")
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(work, "review", "1", "rvw_corrected")


def test_correct_review_rejects_non_review_predecessor(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    prior = service.create(
        work,
        _review_record(status="active", review_state="completed"),
    )
    successor = _corrected_review(prior.record)
    wrong = _account_evidence()["work_record_ref"]
    assert isinstance(wrong, dict)

    with pytest.raises(WorkflowOwnershipError, match="Review"):
        service.correct(
            ExactPortiaWorkRecordRef.from_dict(wrong),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_review_wrong_predecessor",
        )
