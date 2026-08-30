from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ModuleWorkRecordRef
from portia.storage.errors import PortiaNotFoundError, PortiaQuarantinedError
from portia.storage.repository import PortiaRepository
from portia.storage.series import QuarantineStore
from portia.workflows import (
    ClassificationWorkflowService,
    ReviewWorkflowService,
    classification_reference,
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


def _category_result(code: str = "disruption") -> dict[str, object]:
    return {
        "kind": "category_selected",
        "definition": {
            "scheme_id": "local_behavior",
            "scheme_version": "2026_1",
            "category_code": code,
            "category_label": code.replace("_", " ").title(),
            "definition_text": f"Synthetic definition for {code}.",
        },
    }


def _unable_result() -> dict[str, object]:
    return {"kind": "unable_to_determine", "rationale": "More context is needed."}


def _review_ref(review_id: str = "rvw_alpha") -> dict[str, object]:
    return {
        "work_ref": event_ref().to_dict(),
        "record_ref": {
            "record_kind": "review",
            "record_id": review_id,
            "contract_version": "1",
        },
    }


def _classification_ref(classification_id: str) -> dict[str, object]:
    return {
        "work_ref": event_ref().to_dict(),
        "record_ref": {
            "record_kind": "classification",
            "record_id": classification_id,
            "contract_version": "1",
        },
    }


def _account_basis() -> dict[str, object]:
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


def _module_basis() -> dict[str, object]:
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


def _review_wire(
    *,
    review_state: str = "completed",
    reviewer: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "review_id": "rvw_alpha",
        "status": "active",
        "review_state": review_state,
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "classification_review",
            "text": "Which classification, if any, is supported?",
        },
        "target": {"kind": "event"},
        "reviewer": reviewer
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "evidence_considered": [],
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def _classification_wire(
    *,
    classification_id: str = "cls_alpha",
    status: str = "active",
    stage: str = "reporter_selected",
    selector: dict[str, object] | None = None,
    result: dict[str, object] | None = None,
    review_ref: dict[str, object] | None = None,
    reviewed_classification: dict[str, object] | None = None,
    basis: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "classification",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "classification_id": classification_id,
        "status": status,
        "target": {"kind": "event"},
        "selector": selector
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "stage": stage,
        "result": result or _category_result(),
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if review_ref is not None:
        value["review_ref"] = review_ref
    if reviewed_classification is not None:
        value["reviewed_classification"] = reviewed_classification
    if basis is not None:
        value["basis"] = basis
    return value


def _classification_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("classification", "1", _classification_wire(**kwargs))


def _repository_with_event(tmp_path: Path) -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    return repository, work


def _create_completed_review(repository: PortiaRepository, work: object, tmp_path: Path) -> None:
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        parse_portia_record("review", "1", _review_wire()),
    )


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
                    "operation_id": "op_classification_quarantine_test",
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


def test_create_active_reporter_classification(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)

    stored = service.create(work, _classification_record())  # type: ignore[arg-type]

    assert stored.record.logical_id == "cls_alpha"
    assert service.require_current_use(
        classification_reference(work, "cls_alpha")  # type: ignore[arg-type]
    ).record.logical_id == "cls_alpha"


def test_digital_creation_rejects_unknown_historical_stage(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="historical unknown stage"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(status="proposed", stage="unknown"),
        )


def test_reviewer_stage_requires_exact_review(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="governing Review"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(stage="reviewer_selected"),
        )


def test_active_reviewer_stage_requires_completed_review(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        parse_portia_record(
            "review", "1", _review_wire(review_state="in_review")
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="completed Review"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(
                stage="reviewer_selected",
                review_ref=_review_ref(),
            ),
        )


def test_reviewer_selector_must_match_review_reviewer(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    _create_completed_review(repository, work, tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="selector must match"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(
                stage="reviewer_selected",
                selector={"kind": "local_operator", "display_label": "Other Teacher"},
                review_ref=_review_ref(),
            ),
        )


def test_reviewer_confirmed_requires_matching_prior_result(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    _create_completed_review(repository, work, tmp_path)
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        _classification_record(classification_id="cls_reporter"),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="result must match"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(
                classification_id="cls_confirm",
                stage="reviewer_confirmed",
                result=_category_result("other_category"),
                review_ref=_review_ref(),
                reviewed_classification=_classification_ref("cls_reporter"),
            ),
        )


def test_reviewer_confirmed_compares_category_identity_not_snapshot_text(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    _create_completed_review(repository, work, tmp_path)
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        _classification_record(classification_id="cls_reporter"),
    )
    same_identity = _category_result()
    definition = same_identity["definition"]
    assert isinstance(definition, dict)
    definition["category_label"] = "Updated display wording"
    definition["definition_text"] = "Updated local explanatory snapshot."

    stored = ClassificationWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _classification_record(
            classification_id="cls_confirm",
            stage="reviewer_confirmed",
            result=same_identity,
            review_ref=_review_ref(),
            reviewed_classification=_classification_ref("cls_reporter"),
        ),
    )

    assert stored.record.logical_id == "cls_confirm"


def test_reviewer_selected_disagreement_does_not_supersede_reporter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    _create_completed_review(repository, work, tmp_path)
    reporter = _classification_record(classification_id="cls_reporter")
    repository.create_work_record(work, reporter)  # type: ignore[arg-type]

    reviewer = ClassificationWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _classification_record(
            classification_id="cls_reviewer",
            stage="reviewer_selected",
            result=_unable_result(),
            review_ref=_review_ref(),
            reviewed_classification=_classification_ref("cls_reporter"),
        ),
    )

    assert reviewer.record.status == "active"
    assert repository.load_work_record(
        work, "classification", "1", "cls_reporter"  # type: ignore[arg-type]
    ).record.status == "active"


def test_active_classification_checks_current_account_basis_at_acceptance(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        participant_record(
            subject={
                "kind": "descriptive_person",
                "description_type": "school_staff",
                "display_label": "Synthetic Staff",
            }
        ),
    )
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        parse_portia_record("account", "1", account_wire(status="invalidated")),
    )

    with pytest.raises(WorkflowPrerequisiteError):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(basis=[_account_basis()]),
        )


def test_proposed_classification_preserves_module_basis_without_adapter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = ClassificationWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _classification_record(status="proposed", basis=[_module_basis()]),
    )

    assert stored.record.status == "proposed"


def test_active_classification_fails_closed_on_module_basis_without_adapter(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        ClassificationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _classification_record(basis=[_module_basis()]),
        )


class _ModuleAuthority:
    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        return {"record_id": reference.record_ref.record_id}


def test_active_classification_accepts_explicit_module_basis_authority(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = ClassificationWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    ).create(
        work,  # type: ignore[arg-type]
        _classification_record(basis=[_module_basis()]),
    )

    assert stored.record.status == "active"


def test_current_classification_revalidates_module_authority_without_rewriting_history(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    authority_service = ClassificationWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    )
    stored = authority_service.create(
        work,  # type: ignore[arg-type]
        _classification_record(basis=[_module_basis()]),
    )
    reference = classification_reference(
        work, "cls_alpha"  # type: ignore[arg-type]
    )

    unprivileged_service = ClassificationWorkflowService(
        tmp_path, repository=repository
    )
    exact = unprivileged_service.load_exact(reference)

    assert exact.fingerprint == stored.fingerprint
    assert exact.record.to_dict() == stored.record.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        unprivileged_service.require_current_use(reference)

    current = authority_service.require_current_use(reference)
    assert current.fingerprint == stored.fingerprint
    assert current.record.to_dict() == stored.record.to_dict()


def test_active_imported_classification_is_exact_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    fixture = Path(
        "tests/schema_validation/fixtures/issue-16/classification/application-invalid/"
        "active-import-without-review-history.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    imported = parse_portia_record("classification", "1", value)
    stored = repository.create_work_record(work, imported)  # type: ignore[arg-type]
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    reference = classification_reference(
        work, "cls_active_import"  # type: ignore[arg-type]
    )

    exact_before = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_before.record.to_dict() == imported.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="reviewed materialization"):
        service.require_current_use(reference)

    exact_after = service.load_exact(reference)
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == imported.to_dict()


def test_historical_unknown_classification_is_exact_but_not_current(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    historical = _classification_record(stage="unknown")
    repository.create_work_record(work, historical)  # type: ignore[arg-type]
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    reference = classification_reference(work, "cls_alpha")  # type: ignore[arg-type]

    assert service.load_exact(reference).record.field("stage") == "unknown"
    with pytest.raises(WorkflowPrerequisiteError, match="unknown-stage"):
        service.require_current_use(reference)


def test_quarantined_classification_remains_exactly_readable_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _classification_record())  # type: ignore[arg-type]
    reference = classification_reference(work, "cls_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=record_target(work, stored.record),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_classification_current_use",
    )

    exact_before = service.load_exact(reference)
    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)
    exact_after = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == stored.record.to_dict()
    assert exact_after.record.status == "active"


def test_work_quarantine_blocks_classification_current_use_without_blocking_exact_read(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _classification_record())  # type: ignore[arg-type]
    reference = classification_reference(work, "cls_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_classification_work_current_use",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)

    assert service.load_exact(reference).record.to_dict() == stored.record.to_dict()


def test_work_write_quarantine_does_not_block_classification_current_use(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _classification_record())  # type: ignore[arg-type]
    reference = classification_reference(work, "cls_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_work_writes",
        quarantine_id="qnt_classification_work_writes",
    )

    current = service.require_current_use(reference)

    assert current.record.to_dict() == stored.record.to_dict()
    assert current.record.status == "active"

LATER = "2026-08-26T12:05:00-04:00"


def _corrected_classification(
    prior: PortiaRecord,
    *,
    classification_id: str = "cls_corrected",
    reason: str = "classification_corrected",
    result: dict[str, object] | None = None,
    selector: dict[str, object] | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["classification_id"] = classification_id
    data["result"] = result or _unable_result()
    if selector is not None:
        data["selector"] = selector
    data["created_at"] = LATER
    data["updated_at"] = LATER
    data["supersedes"] = [
        {
            "work_record_ref": classification_reference(
                event_ref(), prior.logical_id or "missing"
            ).to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("classification", "1", data)


def test_correct_classification_uses_public_coordinated_successor_path(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _classification_record())  # type: ignore[arg-type]
    successor = _corrected_classification(prior.record)

    service.correct(
        classification_reference(work, "cls_alpha"),  # type: ignore[arg-type]
        successor,
        expected=prior.fingerprint,
        transition_id="lct_classification_public_correction",
        operation_id="op_classification_public_correction",
    )

    predecessor_after = service.load_exact(
        classification_reference(work, "cls_alpha")  # type: ignore[arg-type]
    )
    successor_after = service.require_current_use(
        classification_reference(work, "cls_corrected")  # type: ignore[arg-type]
    )
    transition = repository.load_work_record(
        work,  # type: ignore[arg-type]
        "lifecycle_transition",
        "1",
        "lct_classification_public_correction",
    ).record

    assert predecessor_after.record.status == "superseded"
    assert successor_after.record.to_dict() == successor.to_dict()
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason")["code"] == "classification_corrected"


def test_correct_classification_revalidates_successor_human_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _classification_record())  # type: ignore[arg-type]
    prior_result = deepcopy(prior.record.to_dict()["result"])
    assert isinstance(prior_result, dict)
    successor = _corrected_classification(
        prior.record,
        reason="selector_corrected",
        result=prior_result,
        selector={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="identified represented human"):
        service.correct(
            classification_reference(work, "cls_alpha"),  # type: ignore[arg-type]
            successor,
            expected=prior.fingerprint,
            transition_id="lct_classification_bad_authority",
        )

    assert service.load_exact(
        classification_reference(work, "cls_alpha")  # type: ignore[arg-type]
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            work,  # type: ignore[arg-type]
            "classification",
            "1",
            "cls_corrected",
        )


def test_correct_classification_rejects_non_classification_predecessor(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _classification_record())  # type: ignore[arg-type]
    successor = _corrected_classification(prior.record)
    wrong = _review_ref()

    with pytest.raises(WorkflowOwnershipError, match="Classification"):
        service.correct(
            ExactPortiaWorkRecordRef.from_dict(wrong),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_classification_wrong_predecessor",
        )

