from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ModuleWorkRecordRef
from portia.storage.errors import PortiaQuarantinedError
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.repository import PortiaRepository
from portia.storage.series import QuarantineStore
from portia.workflows import (
    AccountWorkflowService,
    DeterminationWorkflowService,
    ReviewWorkflowService,
    account_reference,
    determination_reference,
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


def _review_ref(review_id: str = "rvw_det") -> dict[str, object]:
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
    review_id: str = "rvw_det",
    review_state: str = "completed",
    target: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "review_id": review_id,
        "status": "active",
        "review_state": review_state,
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "determination_review",
            "text": "What bounded decision should be recorded?",
        },
        "target": target or {"kind": "event"},
        "reviewer": {
            "kind": "local_operator",
            "display_label": "Synthetic Reviewer",
        },
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


def _basis(relation: str, evidence_ref: dict[str, object]) -> dict[str, object]:
    return {"relation": relation, "evidence_ref": evidence_ref}


def _workspace_artifact(
    root: Path,
    *,
    relative_path: str = "authority/synthetic-authority.txt",
    content: bytes = b"Synthetic authority material.\n",
) -> dict[str, object]:
    path = root.joinpath(*relative_path.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "kind": "workspace_file",
        "path": relative_path,
        "fingerprint": fingerprint_bytes(content).to_dict(),
    }


def _external_artifact() -> dict[str, object]:
    return {
        "kind": "external_record",
        "system_label": "Synthetic Archive",
        "external_reference": "authority-alpha",
        "record_label": "Authority memo",
    }


def _determination_wire(
    *,
    determination_id: str = "det_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    decision_maker: dict[str, object] | None = None,
    authority_context: dict[str, object] | None = None,
    process_basis: dict[str, object] | None = None,
    outcome: dict[str, object] | None = None,
    review_ref: dict[str, object] | None = None,
    basis: list[dict[str, object]] | None = None,
    creation_source: dict[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "determination",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "determination_id": determination_id,
        "status": status,
        "target": target or {"kind": "event"},
        "question": "What bounded conclusion is supported for this Event?",
        "decision_maker": decision_maker
        or {"kind": "local_operator", "display_label": "Synthetic Teacher"},
        "authority_context": authority_context
        or {"kind": "teacher_local", "scope": "teacher_review"},
        "process_basis": process_basis
        or {"kind": "teacher_local", "process_label": "Local teacher review"},
        "outcome": outcome or {"kind": "insufficient_information"},
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if review_ref is not None:
        value["review_ref"] = review_ref
    if basis is not None:
        value["basis"] = basis
    return value


def _determination_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("determination", "1", _determination_wire(**kwargs))


def _repository_with_event(tmp_path: Path) -> tuple[PortiaRepository, object]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    return repository, work


def test_teacher_local_determination_requires_local_operator(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    with pytest.raises(WorkflowPrerequisiteError, match="local-operator"):
        service.create(
            work,  # type: ignore[arg-type]
            _determination_record(
                decision_maker={
                    "kind": "descriptive_person",
                    "description_type": "school_staff",
                    "display_label": "Synthetic Staff",
                }
            ),
        )

    assert service.list_determinations(work) == ()  # type: ignore[arg-type]


def test_teacher_local_current_use_preserves_insufficient_information(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    created = service.create(work, _determination_record())  # type: ignore[arg-type]

    current = service.require_current_use(
        determination_reference(work, "det_alpha")  # type: ignore[arg-type]
    )

    assert created.record.field("outcome") == {"kind": "insufficient_information"}
    assert current.record.logical_id == "det_alpha"


@pytest.mark.parametrize(
    "outcome",
    [
        {"kind": "conclusion", "text": "A bounded local conclusion."},
        {
            "kind": "coded_conclusion",
            "scheme_id": "local_decision",
            "scheme_version": "2026_1",
            "code": "bounded_result",
            "label": "Bounded result",
            "definition_text": "Synthetic bounded decision code.",
        },
        {"kind": "insufficient_information"},
        {"kind": "unable_to_determine"},
        {"kind": "not_applicable"},
    ],
)
def test_closed_outcome_branches_are_human_recordable(
    tmp_path: Path,
    outcome: dict[str, object],
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(
        work,  # type: ignore[arg-type]
        _determination_record(outcome=outcome),
    )

    assert stored.record.field("outcome") == outcome


def test_recorded_institutional_school_staff_maker_is_allowed(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            decision_maker={
                "kind": "descriptive_person",
                "description_type": "school_staff",
                "display_label": "Synthetic Administrator",
            },
            authority_context={
                "kind": "recorded_institutional",
                "authority_label": "Synthetic administrative decision",
                "authority_status": "asserted",
            },
            process_basis={"kind": "unknown"},
        ),
    )

    assert stored.record.field("authority_context")["authority_status"] == "asserted"


def test_recorded_institutional_nonstaff_descriptive_maker_is_rejected(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    with pytest.raises(WorkflowPrerequisiteError, match="school-staff"):
        service.create(
            work,  # type: ignore[arg-type]
            _determination_record(
                decision_maker={
                    "kind": "descriptive_person",
                    "description_type": "family_member",
                    "display_label": "Synthetic Family Member",
                },
                authority_context={
                    "kind": "recorded_institutional",
                    "authority_label": "Synthetic institutional representation",
                    "authority_status": "asserted",
                },
            ),
        )


def test_recorded_institutional_unidentified_maker_preserves_historical_uncertainty(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            decision_maker={
                "kind": "unidentified_person",
                "identity_status": "not_recorded",
                "detail": "Decision-maker identity was not retained.",
            },
            authority_context={
                "kind": "recorded_institutional",
                "authority_label": "Historical institutional decision",
                "authority_status": "unknown",
            },
            process_basis={"kind": "unknown"},
        ),
    )

    assert stored.record.field("decision_maker")["kind"] == "unidentified_person"


def test_active_linked_determination_requires_completed_review(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    ReviewWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        parse_portia_record("review", "1", _review_wire(review_state="in_review")),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="completed Review"):
        DeterminationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _determination_record(review_ref=_review_ref()),
        )


def test_review_link_requires_same_target_but_not_same_human(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        participant_record(
            subject={"kind": "unknown_person", "reason": "identity_not_known"}
        ),
    )
    review_service = ReviewWorkflowService(tmp_path, repository=repository)
    review_service.create(
        work,  # type: ignore[arg-type]
        parse_portia_record(
            "review", "1", _review_wire(target=_participant_target())
        ),
    )
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    with pytest.raises(WorkflowPrerequisiteError, match="target must match"):
        service.create(
            work,  # type: ignore[arg-type]
            _determination_record(review_ref=_review_ref()),
        )

    stored = service.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            determination_id="det_participant",
            target=_participant_target(),
            review_ref=_review_ref(),
            decision_maker={
                "kind": "local_operator",
                "display_label": "Different Decision Maker",
            },
        ),
    )
    assert stored.record.logical_id == "det_participant"


def test_duplicate_logical_basis_across_roles_is_rejected(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    evidence = {"kind": "portia_work", "work_ref": event_ref().to_dict()}

    with pytest.raises(WorkflowOwnershipError, match="repeats"):
        DeterminationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _determination_record(
                basis=[_basis("supporting", evidence), _basis("contrary", evidence)]
            ),
        )


def test_active_account_basis_uses_current_evidence_authority(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    repository.create_work_record(work, participant_record())  # type: ignore[arg-type]
    repository.create_work_record(
        work,  # type: ignore[arg-type]
        parse_portia_record("account", "1", account_wire(status="invalidated")),
    )

    with pytest.raises(WorkflowPrerequisiteError):
        DeterminationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _determination_record(
                basis=[_basis("supporting", _portia_account_evidence())]
            ),
        )


def test_existing_determination_keeps_exact_account_after_later_invalidation(
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
    determinations = DeterminationWorkflowService(tmp_path, repository=repository)
    stored_determination = determinations.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            basis=[_basis("supporting", _portia_account_evidence())]
        ),
    )
    determination_ref = determination_reference(
        work, "det_alpha"  # type: ignore[arg-type]
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
        transition_id="lct_account_after_determination",
        reason_code="recording_error",
        operation_id="op_account_after_determination",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="active evidence"):
        accounts.require_current_use(account_ref)

    current_determination = determinations.require_current_use(determination_ref)
    exact_determination = determinations.load_exact(determination_ref)

    assert current_determination.fingerprint == stored_determination.fingerprint
    assert exact_determination.fingerprint == stored_determination.fingerprint
    assert (
        exact_determination.record.to_dict()
        == stored_determination.record.to_dict()
    )
    assert exact_determination.record.to_dict()["basis"] == [
        _basis("supporting", _portia_account_evidence())
    ]


def test_active_module_basis_fails_closed_without_public_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="resolution authority"):
        DeterminationWorkflowService(tmp_path, repository=repository).create(
            work,  # type: ignore[arg-type]
            _determination_record(basis=[_basis("contextual", _module_evidence())]),
        )


class _ModuleAuthority:
    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        return {"record_id": reference.record_ref.record_id}


def test_active_module_basis_accepts_explicit_public_authority(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    stored = DeterminationWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    ).create(
        work,  # type: ignore[arg-type]
        _determination_record(basis=[_basis("contextual", _module_evidence())]),
    )

    assert stored.record.logical_id == "det_alpha"


def test_current_determination_revalidates_module_authority_without_rewriting_history(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    authority_service = DeterminationWorkflowService(
        tmp_path,
        repository=repository,
        module_authority=_ModuleAuthority(),
    )
    stored = authority_service.create(
        work,  # type: ignore[arg-type]
        _determination_record(basis=[_basis("contextual", _module_evidence())]),
    )
    reference = determination_reference(
        work, "det_alpha"  # type: ignore[arg-type]
    )

    unprivileged_service = DeterminationWorkflowService(
        tmp_path, repository=repository
    )
    exact = unprivileged_service.load_exact(reference)

    assert exact.fingerprint == stored.fingerprint
    assert exact.record.to_dict() == stored.record.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="resolution authority"):
        unprivileged_service.require_current_use(reference)

    current = authority_service.require_current_use(reference)
    assert current.fingerprint == stored.fingerprint
    assert current.record.to_dict() == stored.record.to_dict()


def test_documented_authority_workspace_artifact_is_verified_and_drift_blocks_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    artifact = _workspace_artifact(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    service.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            decision_maker={
                "kind": "descriptive_person",
                "description_type": "school_staff",
                "display_label": "Synthetic Administrator",
            },
            authority_context={
                "kind": "recorded_institutional",
                "authority_label": "Synthetic administrative decision",
                "authority_status": "documented_basis",
                "authority_basis": [artifact],
            },
            process_basis={"kind": "unknown"},
        ),
    )
    reference = determination_reference(work, "det_alpha")  # type: ignore[arg-type]
    assert service.require_current_use(reference).record.logical_id == "det_alpha"

    (tmp_path / "authority/synthetic-authority.txt").write_bytes(b"Changed.\n")

    assert service.load_exact(reference).record.logical_id == "det_alpha"
    with pytest.raises(WorkflowPrerequisiteError, match="fingerprint"):
        service.require_current_use(reference)


def test_external_documented_authority_is_preserved_proposed_but_fails_active(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    authority = {
        "kind": "recorded_institutional",
        "authority_label": "Synthetic institutional decision",
        "authority_status": "documented_basis",
        "authority_basis": [_external_artifact()],
    }
    maker = {
        "kind": "descriptive_person",
        "description_type": "school_staff",
        "display_label": "Synthetic Administrator",
    }
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    proposed = service.create(
        work,  # type: ignore[arg-type]
        _determination_record(
            determination_id="det_proposed_external",
            status="proposed",
            decision_maker=maker,
            authority_context=authority,
            process_basis={"kind": "unknown"},
        ),
    )
    assert proposed.record.status == "proposed"

    with pytest.raises(WorkflowPrerequisiteError, match="outside Issue #41"):
        service.create(
            work,  # type: ignore[arg-type]
            _determination_record(
                determination_id="det_active_external",
                decision_maker=maker,
                authority_context=authority,
                process_basis={"kind": "unknown"},
            ),
        )


def test_identified_process_workspace_artifact_uses_same_locator_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    artifact = _workspace_artifact(
        tmp_path,
        relative_path="authority/synthetic-policy.txt",
        content=b"Synthetic policy text.\n",
    )
    stored = DeterminationWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _determination_record(
            process_basis={
                "kind": "identified",
                "policy": {
                    "label": "Synthetic policy",
                    "version": "2026_1",
                    "source_artifacts": [artifact],
                },
            }
        ),
    )

    assert stored.record.field("process_basis")["kind"] == "identified"


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
                    "operation_id": "op_determination_quarantine_test",
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


def test_record_quarantine_blocks_determination_current_use_without_exact_read(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _determination_record())  # type: ignore[arg-type]
    reference = determination_reference(work, "det_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=record_target(work, stored.record),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_determination_current_use",
    )

    exact_before = service.load_exact(reference)
    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)
    exact_after = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == stored.record.to_dict()
    assert exact_after.record.status == "active"


def test_work_quarantine_blocks_determination_current_use_without_exact_read(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _determination_record())  # type: ignore[arg-type]
    reference = determination_reference(work, "det_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_current_use",
        quarantine_id="qnt_determination_work_current_use",
    )

    with pytest.raises(PortiaQuarantinedError, match="block_current_use"):
        service.require_current_use(reference)

    assert service.load_exact(reference).record.to_dict() == stored.record.to_dict()


def test_work_write_quarantine_does_not_block_determination_current_use(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _determination_record())  # type: ignore[arg-type]
    reference = determination_reference(work, "det_alpha")  # type: ignore[arg-type]

    _activate_quarantine(
        tmp_path,
        target=work_target(work),  # type: ignore[arg-type]
        effect="block_work_writes",
        quarantine_id="qnt_determination_work_writes",
    )

    current = service.require_current_use(reference)

    assert current.record.to_dict() == stored.record.to_dict()
    assert current.record.status == "active"

def test_determination_creation_does_not_fabricate_response(tmp_path: Path) -> None:
    repository, work = _repository_with_event(tmp_path)
    DeterminationWorkflowService(tmp_path, repository=repository).create(
        work,  # type: ignore[arg-type]
        _determination_record(),
    )

    responses = repository.list_work_records(
        work, "response", version="1"  # type: ignore[arg-type]
    )
    assert responses == ()


LATER = "2026-08-26T12:05:00-04:00"


def _corrected_determination(
    prior: PortiaRecord,
    *,
    determination_id: str = "det_corrected",
    reason: str = "outcome_corrected",
    outcome: dict[str, object] | None = None,
    decision_maker: dict[str, object] | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["determination_id"] = determination_id
    if outcome is not None:
        data["outcome"] = outcome
    if decision_maker is not None:
        data["decision_maker"] = decision_maker
    data["created_at"] = LATER
    data["updated_at"] = LATER
    data["supersedes"] = [
        {
            "work_record_ref": determination_reference(
                event_ref(), prior.logical_id or "missing"
            ).to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("determination", "1", data)


def test_correct_determination_uses_public_coordinated_successor_path(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _determination_record())  # type: ignore[arg-type]
    successor = _corrected_determination(
        prior.record,
        outcome={"kind": "conclusion", "text": "A corrected bounded conclusion."},
    )

    service.correct(
        determination_reference(work, "det_alpha"),  # type: ignore[arg-type]
        successor,
        expected=prior.fingerprint,
        transition_id="lct_determination_public_correction",
        operation_id="op_determination_public_correction",
    )

    predecessor_after = service.load_exact(
        determination_reference(work, "det_alpha")  # type: ignore[arg-type]
    )
    successor_after = service.require_current_use(
        determination_reference(work, "det_corrected")  # type: ignore[arg-type]
    )
    transition = repository.load_work_record(
        work,  # type: ignore[arg-type]
        "lifecycle_transition",
        "1",
        "lct_determination_public_correction",
    ).record

    assert predecessor_after.record.status == "superseded"
    assert successor_after.record.to_dict() == successor.to_dict()
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason")["code"] == "outcome_corrected"


def test_correct_determination_revalidates_successor_human_authority(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _determination_record())  # type: ignore[arg-type]
    successor = _corrected_determination(
        prior.record,
        reason="decision_maker_corrected",
        decision_maker={
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="local-operator"):
        service.correct(
            determination_reference(work, "det_alpha"),  # type: ignore[arg-type]
            successor,
            expected=prior.fingerprint,
            transition_id="lct_determination_bad_authority",
        )

    records = repository.list_work_records(
        work, "determination", version="1"  # type: ignore[arg-type]
    )
    assert len(records) == 1
    assert records[0].record.logical_id == "det_alpha"
    assert records[0].record.status == "active"


def test_correct_determination_rejects_non_determination_predecessor(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _determination_record())  # type: ignore[arg-type]
    successor = _corrected_determination(
        prior.record,
        outcome={"kind": "unable_to_determine"},
    )

    with pytest.raises(WorkflowOwnershipError, match="Determination"):
        service.correct(
            ExactPortiaWorkRecordRef.from_dict(_review_ref()),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_determination_wrong_predecessor",
        )


def test_correct_determination_keeps_reconsideration_out_of_ordinary_path(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    prior = service.create(work, _determination_record())  # type: ignore[arg-type]
    successor = _corrected_determination(
        prior.record,
        reason="reconsidered",
        outcome={"kind": "conclusion", "text": "A reconsidered conclusion."},
    )

    with pytest.raises(WorkflowPrerequisiteError, match="dedicated guarded workflow"):
        service.correct(
            determination_reference(work, "det_alpha"),  # type: ignore[arg-type]
            successor,
            expected=prior.fingerprint,
            transition_id="lct_determination_reconsideration_reserved",
        )

    records = repository.list_work_records(
        work, "determination", version="1"  # type: ignore[arg-type]
    )
    assert len(records) == 1
    assert records[0].record.logical_id == "det_alpha"
    assert records[0].record.status == "active"

def test_active_imported_determination_is_exact_but_not_current(
    tmp_path: Path,
) -> None:
    repository, work = _repository_with_event(tmp_path)
    fixture = Path(
        "tests/schema_validation/fixtures/issue-16/determination/application-invalid/"
        "active-import-without-review-history.json"
    )
    value = json.loads(fixture.read_text(encoding="utf-8"))
    value["class_id"] = "class_a"
    value["work_id"] = "evt_alpha"
    imported = parse_portia_record("determination", "1", value)
    stored = repository.create_work_record(work, imported)  # type: ignore[arg-type]
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    reference = determination_reference(
        work, "det_app_invalid"  # type: ignore[arg-type]
    )

    exact_before = service.load_exact(reference)

    assert exact_before.fingerprint == stored.fingerprint
    assert exact_before.record.to_dict() == imported.to_dict()
    with pytest.raises(WorkflowPrerequisiteError, match="reviewed materialization"):
        service.require_current_use(reference)

    exact_after = service.load_exact(reference)
    assert exact_after.fingerprint == stored.fingerprint
    assert exact_after.record.to_dict() == imported.to_dict()

