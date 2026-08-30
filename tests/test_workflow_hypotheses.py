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
    AccountWorkflowService,
    HypothesisWorkflowService,
    ReviewWorkflowService,
    account_reference,
    hypothesis_reference,
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


def _review_ref(review_id: str = "rvw_alpha") -> dict[str, object]:
    return {
        "work_ref": event_ref().to_dict(),
        "record_ref": {
            "record_kind": "review",
            "record_id": review_id,
            "contract_version": "1",
        },
    }


def _review_wire(
    *,
    review_id: str = "rvw_alpha",
    target: dict[str, object] | None = None,
    reviewer: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "review_id": review_id,
        "status": "active",
        "review_state": "in_review",
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "hypothesis_review",
            "text": "What tentative explanation should be considered?",
        },
        "target": target or {"kind": "event"},
        "reviewer": reviewer
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "evidence_considered": [],
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def _participant_target() -> dict[str, object]:
    return {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_alpha",
            "contract_version": "3",
        },
    }


def _portia_account_evidence() -> dict[str, object]:
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


def _evidence(
    relation: str,
    evidence_ref: dict[str, object],
) -> dict[str, object]:
    return {"relation": relation, "evidence_ref": evidence_ref}


def _hypothesis_wire(
    *,
    hypothesis_id: str = "hyp_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    author: dict[str, object] | None = None,
    proposition: str = "A contextual change may have contributed to the Event.",
    consideration_state: str = "under_consideration",
    review_ref: dict[str, object] | None = None,
    evidence: list[dict[str, object]] | None = None,
    creation_source: dict[str, object] | None = None,
    updated_at: str = TIMESTAMP,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "hypothesis",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "hypothesis_id": hypothesis_id,
        "status": status,
        "target": target or {"kind": "event"},
        "author": author
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "proposition": proposition,
        "consideration_state": consideration_state,
        "evidence": evidence or [],
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if review_ref is not None:
        value["review_ref"] = review_ref
    return value


def _hypothesis_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("hypothesis", "1", _hypothesis_wire(**kwargs))


def _repository_with_event(tmp_path: Path) -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
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
                    "operation_id": "op_hypothesis_quarantine_test",
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


def test_create_active_under_consideration_hypothesis_without_evidence(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)

    stored = service.create(work, _hypothesis_record())  # type: ignore[arg-type]

    assert stored.record.logical_id == "hyp_alpha"
    assert stored.record.field("evidence") == ()
    assert service.require_current_use(
        hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]
    ).record.logical_id == "hyp_alpha"


def test_guarded_set_aside_preserves_active_history_but_ends_current_consideration(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    created = service.create(work, _hypothesis_record())  # type: ignore[arg-type]

    stored = service.set_aside(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            consideration_state="set_aside",
            updated_at="2026-08-26T12:05:00-04:00",
        ),
        expected=created.fingerprint,
    )
    reference = hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]

    assert stored.record.status == "active"
    assert stored.record.field("consideration_state") == "set_aside"
    with pytest.raises(WorkflowPrerequisiteError, match="under-consideration"):
        service.require_current_use(reference)


def test_set_aside_cannot_rewrite_proposition(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    created = service.create(work, _hypothesis_record())  # type: ignore[arg-type]

    with pytest.raises(WorkflowPrerequisiteError, match="substantive fields"):
        service.set_aside(
            work,  # type: ignore[arg-type]
            _hypothesis_record(
                consideration_state="set_aside",
                proposition="A materially different proposition.",
                updated_at="2026-08-26T12:05:00-04:00",
            ),
            expected=created.fingerprint,
        )


def test_competing_hypotheses_coexist_without_supersession(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)

    first = service.create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            hypothesis_id="hyp_first",
            proposition="One contextual explanation is being considered.",
        ),
    )
    second = service.create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            hypothesis_id="hyp_second",
            proposition="A competing contextual explanation is being considered.",
        ),
    )

    assert first.record.status == "active"
    assert second.record.status == "active"
    assert first.record.field("supersedes") is None
    assert second.record.field("supersedes") is None


def test_review_link_requires_same_target(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, participant_record())  # type: ignore[arg-type]
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        parse_portia_record("review", "1", _review_wire()),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="target must match"):
        HypothesisWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _hypothesis_record(
                target=_participant_target(),
                review_ref=_review_ref(),
            ),
        )


def test_hypothesis_author_need_not_match_review_reviewer(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        parse_portia_record("review", "1", _review_wire()),
    )

    stored = HypothesisWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            author={"kind": "local_operator", "display_label": "Other Teacher"},
            review_ref=_review_ref(),
        ),
    )

    assert stored.record.field("author") != stored.record.field("created_by")
    assert stored.record.status == "active"


def test_duplicate_logical_evidence_is_rejected_across_roles(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    evidence_ref = _portia_account_evidence()

    with pytest.raises(WorkflowOwnershipError, match="same logical evidence identity"):
        HypothesisWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _hypothesis_record(
                status="proposed",
                evidence=[
                    _evidence("supporting", evidence_ref),
                    _evidence("contrary", evidence_ref),
                ],
            ),
        )


def test_active_hypothesis_checks_current_account_evidence_at_acceptance(
    tmp_path: Path,
) -> None:
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
        HypothesisWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _hypothesis_record(
                evidence=[_evidence("supporting", _portia_account_evidence())],
            ),
        )


def test_existing_hypothesis_keeps_exact_account_after_later_invalidation(
    tmp_path: Path,
) -> None:
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
    account = repository.create_work_record(
        work,  # type: ignore[arg-type]
        parse_portia_record("account", "1", account_wire()),
    )
    hypotheses = HypothesisWorkflowService(tmp_path, repository=repository)
    stored_hypothesis = hypotheses.create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            evidence=[_evidence("supporting", _portia_account_evidence())],
        ),
    )
    hypothesis_ref = hypothesis_reference(
        work, "hyp_alpha"  # type: ignore[arg-type]
    )
    account_ref = account_reference(
        work, "acct_alpha", version="1"  # type: ignore[arg-type]
    )

    invalidated_data = deepcopy(account.record.to_dict())
    invalidated_data["status"] = "invalidated"
    invalidated_data["updated_at"] = "2026-08-26T12:05:00-04:00"
    invalidated = parse_portia_record("account", "1", invalidated_data)
    accounts = AccountWorkflowService(tmp_path, repository=repository)
    accounts.transition_lifecycle(
        account_ref,
        invalidated,
        expected=account.fingerprint,
        transition_id="lct_account_after_hypothesis",
        reason_code="recording_error",
        operation_id="op_account_after_hypothesis",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        accounts.require_current_use(account_ref)

    current_hypothesis = hypotheses.require_current_use(hypothesis_ref)
    exact_hypothesis = hypotheses.load_exact(hypothesis_ref)

    assert current_hypothesis.fingerprint == stored_hypothesis.fingerprint
    assert exact_hypothesis.fingerprint == stored_hypothesis.fingerprint
    assert exact_hypothesis.record.to_dict() == stored_hypothesis.record.to_dict()
    assert exact_hypothesis.record.to_dict()["evidence"] == [
        _evidence("supporting", _portia_account_evidence())
    ]


def test_contrary_and_contextual_evidence_are_first_class(tmp_path: Path) -> None:
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
        parse_portia_record("account", "1", account_wire()),
    )

    stored = HypothesisWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            evidence=[
                _evidence("contrary", _portia_account_evidence()),
                _evidence(
                    "contextual",
                    {"kind": "portia_work", "work_ref": event_ref().to_dict()},
                ),
            ],
        ),
    )

    entries = stored.record.field("evidence")
    assert isinstance(entries, tuple)
    assert {entry["relation"] for entry in entries} == {"contrary", "contextual"}


def test_proposed_hypothesis_preserves_module_evidence_without_adapter(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = HypothesisWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            status="proposed",
            evidence=[_evidence("contextual", _module_evidence())],
        ),
    )

    assert stored.record.status == "proposed"


def test_active_hypothesis_fails_closed_on_module_evidence_without_adapter(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        HypothesisWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _hypothesis_record(
                evidence=[_evidence("supporting", _module_evidence())],
            ),
        )


class _ModuleAuthority:
    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        return {"record_id": reference.record_ref.record_id}


def test_active_hypothesis_accepts_explicit_module_evidence_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)

    stored = HypothesisWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    ).create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            evidence=[_evidence("supporting", _module_evidence())],
        ),
    )

    assert stored.record.status == "active"


def test_current_hypothesis_revalidates_module_authority_without_rewriting_history(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    authority_service = HypothesisWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    )
    stored = authority_service.create(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            evidence=[_evidence("supporting", _module_evidence())],
        ),
    )
    reference = hypothesis_reference(
        work, "hyp_alpha"  # type: ignore[arg-type]
    )

    unprivileged_service = HypothesisWorkflowService(
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


def test_current_hypothesis_requires_identified_author(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        _hypothesis_record(
            author={
                "kind": "unidentified_person",
                "identity_status": "not_recorded",
            }
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="identified represented human"):
        HypothesisWorkflowService(tmp_path, repository=repository).require_current_use(
            hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]
        )


def test_active_imported_hypothesis_is_exact_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    fixture = Path(
        "tests/schema_validation/fixtures/issue-16/hypothesis/application-invalid/"
        "active-import-without-review-history.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    imported = parse_portia_record("hypothesis", "1", value)
    stored = repository.create_work_record(work, imported)  # type: ignore[arg-type]
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    reference = hypothesis_reference(
        work, "hyp_app_invalid"  # type: ignore[arg-type]
    )

    exact_before = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_before.record.to_dict() == imported.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="reviewed materialization"):
        service.require_current_use(reference)

    exact_after = service.load_exact(reference)
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == imported.to_dict()


def test_quarantined_hypothesis_remains_exactly_readable_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    reference = hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=record_target(work, stored.record),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_hypothesis_current_use",
    )

    exact_before = service.load_exact(reference)
    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)
    exact_after = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == stored.record.to_dict()
    assert exact_after.record.status == "active"


def test_work_quarantine_blocks_hypothesis_current_use_without_blocking_exact_read(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    reference = hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_hypothesis_work_current_use",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)

    assert service.load_exact(reference).record.to_dict() == stored.record.to_dict()


def test_work_write_quarantine_does_not_block_hypothesis_current_use(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    reference = hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_work_writes",
        quarantine_id="qnt_hypothesis_work_writes",
    )

    current = service.require_current_use(reference)

    assert current.record.to_dict() == stored.record.to_dict()
    assert current.record.status == "active"


LATER = "2026-08-26T12:05:00-04:00"


def _corrected_hypothesis(
    prior: PortiaRecord,
    *,
    hypothesis_id: str = "hyp_corrected",
    reason: str = "hypothesis_refined",
    proposition: str = (
        "A narrower contextual change may have contributed to the Event."
    ),
    author: dict[str, object] | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["hypothesis_id"] = hypothesis_id
    data["proposition"] = proposition
    if author is not None:
        data["author"] = author
    data["created_at"] = LATER
    data["updated_at"] = LATER
    data["supersedes"] = [
        {
            "work_record_ref": hypothesis_reference(
                event_ref(), prior.logical_id or "missing"
            ).to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("hypothesis", "1", data)


def test_correct_hypothesis_uses_public_coordinated_successor_path(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    successor = _corrected_hypothesis(prior.record)

    service.correct(
        hypothesis_reference(work, "hyp_alpha"),  # type: ignore[arg-type]
        successor,
        expected=prior.fingerprint,
        transition_id="lct_hypothesis_public_correction",
        operation_id="op_hypothesis_public_correction",
    )

    predecessor_after = service.load_exact(
        hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]
    )
    successor_after = service.require_current_use(
        hypothesis_reference(work, "hyp_corrected")  # type: ignore[arg-type]
    )
    transition = repository.load_work_record(
        work,  # type: ignore[arg-type]
        "lifecycle_transition",
        "1",
        "lct_hypothesis_public_correction",
    ).record

    assert predecessor_after.record.status == "superseded"
    assert successor_after.record.to_dict() == successor.to_dict()
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason")["code"] == "hypothesis_refined"


def test_correct_hypothesis_revalidates_successor_human_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    prior_proposition = str(prior.record.field("proposition"))
    successor = _corrected_hypothesis(
        prior.record,
        reason="author_corrected",
        proposition=prior_proposition,
        author={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="identified represented human"):
        service.correct(
            hypothesis_reference(work, "hyp_alpha"),  # type: ignore[arg-type]
            successor,
            expected=prior.fingerprint,
            transition_id="lct_hypothesis_bad_authority",
        )

    assert service.load_exact(
        hypothesis_reference(work, "hyp_alpha")  # type: ignore[arg-type]
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            work,  # type: ignore[arg-type]
            "hypothesis",
            "1",
            "hyp_corrected",
        )


def test_correct_hypothesis_rejects_non_hypothesis_predecessor(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _hypothesis_record())  # type: ignore[arg-type]
    successor = _corrected_hypothesis(prior.record)

    with pytest.raises(WorkflowOwnershipError, match="Hypothesis"):
        service.correct(
            ExactPortiaWorkRecordRef.from_dict(_review_ref()),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_hypothesis_wrong_predecessor",
        )

