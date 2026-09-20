"""Public ownership-correction workflow acceptance and boundary tests."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from portia.models import OwnershipCorrectionV2
from portia.storage.errors import PortiaNotFoundError, PortiaOperationPartialCommitError
from portia.storage.io import read_bytes
from portia.storage.quarantine import QuarantineGuard
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    OwnershipCorrectionWorkflowService,
    RecoveryWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    follow_up_reference,
    supported_ownership_correction_families,
)
from portia.workflows import __all__ as workflow_exports
from tests import test_workflow_dependencies as dependency_cases
from tests import test_workflow_fidelity as fidelity_cases
from tests import test_workflow_implementations as implementation_cases
from tests import test_workflow_outcomes as outcome_cases
from tests import test_workflow_reentries as reentry_cases
from tests import test_workflow_repairs as repair_cases
from tests.test_workflow_follow_ups import (
    AGENT,
    WORK_ROOT_UPDATED,
    FollowUpWorkflowService,
    event_ref,
    follow_up_record,
    follow_up_work_root_successor,
    seed_event,
    seed_support,
    support_ref,
)

_SENSITIVE_SENTINEL = "SENSITIVE-STUDENT-NOTE-OWNERSHIP-47"


class _ClearIntegrityGuard:
    """Focused fixture: production defaults are tested separately as fail-closed."""

    def __init__(self, root: Path) -> None:
        self.quarantine = QuarantineGuard(root)

    def require_allowed(self, requested_target: object, effect: str) -> None:
        self.quarantine.require_allowed(requested_target, effect)


class _FailAfterCertificate(OwnershipCorrectionWorkflowService):
    def _fault_hook(self, phase: str, step_id: str | None) -> None:
        if phase == "after_publish" and step_id == "step_ownership_certificate":
            raise RuntimeError("deterministic post-certificate interruption")


class _FailAfterSourceLifecycle(OwnershipCorrectionWorkflowService):
    def _fault_hook(self, phase: str, step_id: str | None) -> None:
        if phase == "after_publish" and step_id == "step_predecessor":
            raise RuntimeError("deterministic post-lifecycle interruption")


def _prepared(tmp_path: Path) -> tuple[object, object, object]:
    seed_event(tmp_path)
    seed_support(tmp_path)
    created = FollowUpWorkflowService(tmp_path).create(
        event_ref(),
        follow_up_record(
            purpose={"kind": "other", "detail": _SENSITIVE_SENTINEL}
        ),
    )
    predecessor = follow_up_reference(event_ref(), "fup_alpha")
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=support_ref(),
    )
    return created, predecessor, successor


def test_public_boundary_and_closed_six_family_registry() -> None:
    assert "OwnershipCorrectionWorkflowService" in workflow_exports
    assert "ActionOwnershipCorrectionCoordinator" not in workflow_exports
    assert set(supported_ownership_correction_families()) == {
        "fidelity",
        "implementation",
        "follow_up",
        "outcome",
        "reentry",
        "repair",
    }
    methods = {
        name
        for name, value in inspect.getmembers(
            OwnershipCorrectionWorkflowService, inspect.isfunction
        )
        if not name.startswith("_")
    }
    assert methods == {"assess_correction", "correct_work_root", "resolve_correction"}
    signature = inspect.signature(OwnershipCorrectionWorkflowService.correct_work_root)
    assert not {
        "move",
        "copy_tree",
        "relocate",
        "callbacks",
        "fault_hook",
    }.intersection(signature.parameters)


def test_public_follow_up_event_to_support_writes_v2_certificate_and_journal(
    tmp_path: Path,
) -> None:
    created, predecessor, successor = _prepared(tmp_path)
    service = OwnershipCorrectionWorkflowService(
        tmp_path,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    assessment = service.assess_correction(
        predecessor,  # type: ignore[arg-type]
        support_ref(),
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        effective_at=WORK_ROOT_UPDATED,
    )
    assert assessment.incoming_references == ()
    assert assessment.dependencies == ()

    result = service.correct_work_root(
        predecessor,  # type: ignore[arg-type]
        support_ref(),
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        transition_id="lct_public_fup_move",
        correction_id="owc_public_fup_move",
        reason={"code": "wrong_work_root"},
        effective_at=WORK_ROOT_UPDATED,
        created_by=AGENT,
        reference_dispositions={},
        dependency_dispositions={},
        operation_id="op_public_fup_move",
    )

    assert result.status == "completed"
    assert result.recovery_required is False
    certificate = service.resolve_correction(result.ownership_correction)
    assert isinstance(certificate.record, OwnershipCorrectionV2)
    certificate_data = certificate.record.to_dict()
    assert certificate_data["source"]["work_record_ref"] == predecessor.to_dict()  # type: ignore[union-attr]
    assert (
        certificate_data["destination"]["work_record_ref"]
        == result.destination.to_dict()
    )
    assert certificate_data["work_kind"] == "support_process"

    historical = FollowUpWorkflowService(tmp_path).resolve_exact(predecessor)  # type: ignore[arg-type]
    assert historical.record.status == "superseded"
    assert historical.record.work_kind == "event"
    journal = OperationJournalStore(tmp_path).load_current(result.operation_id)
    assert journal.revision.contract_version == "2"
    assert journal.revision.to_dict()["operation_kind"] == "correct_ownership"
    assert journal.revision.to_dict()["state"] == "completed"
    assert str(tmp_path) not in json.dumps(journal.revision.to_dict())
    assert _SENSITIVE_SENTINEL in json.dumps(successor.to_dict())  # type: ignore[union-attr]
    assert _SENSITIVE_SENTINEL not in json.dumps(certificate_data)
    assert _SENSITIVE_SENTINEL not in json.dumps(journal.revision.to_dict())
    assert _SENSITIVE_SENTINEL not in repr(result)
    assert not (tmp_path / "portia" / "actors").exists()
    assert not (tmp_path / "portia" / "quarantines").exists()
    assert not (tmp_path / "portia" / "integrity").exists()

    replay = service.correct_work_root(
        predecessor,  # type: ignore[arg-type]
        support_ref(),
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        transition_id="lct_public_fup_move",
        correction_id="owc_public_fup_move",
        reason={"code": "wrong_work_root"},
        effective_at=WORK_ROOT_UPDATED,
        created_by=AGENT,
        reference_dispositions={},
        dependency_dispositions={},
        operation_id="op_public_fup_move",
    )
    assert replay == result


def test_default_integrity_preflight_fails_closed_without_current_generation(
    tmp_path: Path,
) -> None:
    created, predecessor, successor = _prepared(tmp_path)
    service = OwnershipCorrectionWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="Integrity Finding state"):
        service.assess_correction(
            predecessor,  # type: ignore[arg-type]
            support_ref(),
            successor,  # type: ignore[arg-type]
            expected=created.fingerprint,  # type: ignore[union-attr]
            effective_at=WORK_ROOT_UPDATED,
        )
    with pytest.raises(PortiaNotFoundError):
        service.repository.load_work_record(
            support_ref(), "follow_up", "1", "fup_alpha"
        )


def test_unsupported_family_and_pair_fail_before_mutation(tmp_path: Path) -> None:
    created, predecessor, successor = _prepared(tmp_path)
    service = OwnershipCorrectionWorkflowService(
        tmp_path,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    wrong_family = type(predecessor)(
        work_ref=predecessor.work_ref,  # type: ignore[union-attr]
        record_ref=type(predecessor.record_ref)(  # type: ignore[union-attr]
            record_kind="response",
            record_id="rsp_alpha",
            contract_version="1",
        ),
    )
    with pytest.raises(WorkflowOwnershipError, match="unsupported.*family"):
        service.assess_correction(
            wrong_family,
            support_ref(),
            successor,  # type: ignore[arg-type]
            expected=created.fingerprint,  # type: ignore[union-attr]
            effective_at=WORK_ROOT_UPDATED,
        )


def _fidelity_case(tmp_path: Path) -> tuple[object, object, object, object, str]:
    fidelity_cases.setup_authority(tmp_path)
    fidelity_cases.seed_implementation(tmp_path)
    destination = fidelity_cases.corrected_work_ref()
    fidelity_cases._setup_authority_for_work(  # noqa: SLF001
        tmp_path, destination, suffix="public_fidelity"
    )
    created = fidelity_cases.FidelityWorkflowService(tmp_path).create(
        fidelity_cases.work_ref(), fidelity_cases.fidelity_record()
    )
    predecessor = fidelity_cases.fidelity_reference(
        fidelity_cases.work_ref(), "fid_alpha"
    )
    successor = fidelity_cases._fidelity_work_root_successor(  # noqa: SLF001
        created.record, predecessor, destination
    )
    return (
        created,
        predecessor,
        destination,
        successor,
        fidelity_cases.FIDELITY_WORK_ROOT_UPDATED,
    )


def _implementation_case(tmp_path: Path) -> tuple[object, object, object, object, str]:
    implementation_cases._setup_active_plans(tmp_path)  # noqa: SLF001
    destination = implementation_cases.corrected_work_ref()
    implementation_cases._setup_active_plans_for_work(  # noqa: SLF001
        tmp_path, destination, suffix="public_implementation"
    )
    created = implementation_cases.ImplementationWorkflowService(tmp_path).create(
        implementation_cases.work_ref(), implementation_cases.implementation_record()
    )
    predecessor = implementation_cases.implementation_reference(
        implementation_cases.work_ref(), "imp_alpha"
    )
    successor = implementation_cases._work_root_successor(  # noqa: SLF001
        created.record, predecessor, destination
    )
    return (
        created,
        predecessor,
        destination,
        successor,
        implementation_cases.WORK_ROOT_UPDATED,
    )


def _outcome_case(tmp_path: Path) -> tuple[object, object, object, object, str]:
    outcome_cases.seed_event(tmp_path)
    outcome_cases.seed_support(tmp_path)
    created = outcome_cases.OutcomeWorkflowService(tmp_path).create(
        outcome_cases.event_ref(), outcome_cases.outcome_record(outcome_id="out_public")
    )
    predecessor = outcome_cases.outcome_reference(
        outcome_cases.event_ref(), "out_public"
    )
    successor = outcome_cases.outcome_work_root_successor(
        created.record,
        outcome_cases.support_ref(),
        target=outcome_cases.support_target(),
        evaluator=outcome_cases.support_evaluator(),
    )
    return (
        created,
        predecessor,
        outcome_cases.support_ref(),
        successor,
        outcome_cases.REOWNERSHIP_UPDATED,
    )


def _reentry_case(tmp_path: Path) -> tuple[object, object, object, object, str]:
    reentry_cases.seed_event(tmp_path)
    reentry_cases.seed_support(tmp_path)
    created = reentry_cases.ReentryWorkflowService(tmp_path).create(
        reentry_cases.event_ref(), reentry_cases.reentry_record(reentry_id="ren_public")
    )
    predecessor = reentry_cases.reentry_reference(
        reentry_cases.event_ref(), "ren_public"
    )
    successor = reentry_cases.reentry_work_root_successor(
        created.record,
        reentry_cases.support_ref(),
        target=reentry_cases.support_target(),
        coordinator=reentry_cases.support_coordinator(),
    )
    return (
        created,
        predecessor,
        reentry_cases.support_ref(),
        successor,
        str(successor.field("updated_at")),
    )


def _repair_case(tmp_path: Path) -> tuple[object, object, object, object, str]:
    repair_cases.seed_event(tmp_path)
    repair_cases.seed_support(tmp_path)
    created = repair_cases.RepairWorkflowService(tmp_path).create(
        repair_cases.event_ref(),
        repair_cases.repair_work_record(repair_id="rpr_public"),
    )
    predecessor = repair_cases.repair_reference(repair_cases.event_ref(), "rpr_public")
    successor = repair_cases.repair_work_root_successor(
        created.record,
        repair_cases.support_ref(),
        target=repair_cases.support_target(),
        facilitator=repair_cases.support_facilitator(),
        participants=[repair_cases.support_repair_participant()],
    )
    return (
        created,
        predecessor,
        repair_cases.support_ref(),
        successor,
        str(successor.field("updated_at")),
    )


@pytest.mark.parametrize(
    ("family", "factory"),
    [
        ("fidelity", _fidelity_case),
        ("implementation", _implementation_case),
        ("outcome", _outcome_case),
        ("reentry", _reentry_case),
        ("repair", _repair_case),
    ],
)
def test_public_service_uses_each_remaining_registered_family(
    tmp_path: Path,
    family: str,
    factory: object,
) -> None:
    created, predecessor, destination, successor, effective_at = factory(tmp_path)  # type: ignore[operator]
    service = OwnershipCorrectionWorkflowService(
        tmp_path,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    assessment = service.assess_correction(
        predecessor,  # type: ignore[arg-type]
        destination,  # type: ignore[arg-type]
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        effective_at=effective_at,
    )
    result = service.correct_work_root(
        predecessor,  # type: ignore[arg-type]
        destination,  # type: ignore[arg-type]
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        transition_id=f"lct_public_{family}",
        correction_id=f"owc_public_{family}",
        reason={"code": "wrong_work_root"},
        effective_at=effective_at,
        created_by=successor.field("updated_by"),  # type: ignore[union-attr,arg-type]
        reference_dispositions={
            item.reference_key: "remain_exact_historical"
            for item in assessment.incoming_references
        },
        dependency_dispositions={
            item.dependency_key: "satisfied_by_destination"
            for item in assessment.dependencies
        },
        operation_id=f"op_public_{family}",
    )
    assert result.status == "completed"
    assert (
        service.resolve_correction(result.ownership_correction).record.contract_version
        == "2"
    )


@pytest.mark.parametrize("pair", ["support_to_event", "event_to_event"])
def test_public_follow_up_additional_work_kind_pairs(
    tmp_path: Path,
    pair: str,
) -> None:
    seed_event(tmp_path)
    seed_support(tmp_path)
    if pair == "support_to_event":
        source_work = support_ref()
        destination_work = event_ref()
        follow_up_id = "fup_support_event"
    else:
        seed_event(tmp_path, event_id="evt_beta")
        source_work = event_ref()
        destination_work = event_ref(event_id="evt_beta")
        follow_up_id = "fup_event_event"
    family = FollowUpWorkflowService(tmp_path)
    created = family.create(
        source_work,
        follow_up_record(
            work=source_work,
            follow_up_id=follow_up_id,
            purpose={"kind": "coordination"},
        ),
    )
    predecessor = follow_up_reference(source_work, follow_up_id)
    successor = follow_up_work_root_successor(
        created.record,
        destination_work=destination_work,
    )
    service = OwnershipCorrectionWorkflowService(
        tmp_path,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    assessment = service.assess_correction(
        predecessor,
        destination_work,
        successor,
        expected=created.fingerprint,
        effective_at=WORK_ROOT_UPDATED,
    )
    result = service.correct_work_root(
        predecessor,
        destination_work,
        successor,
        expected=created.fingerprint,
        transition_id=f"lct_public_{pair}",
        correction_id=f"owc_public_{pair}",
        reason={"code": "wrong_work_root"},
        effective_at=WORK_ROOT_UPDATED,
        created_by=AGENT,
        reference_dispositions={
            item.reference_key: "remain_exact_historical"
            for item in assessment.incoming_references
        },
        dependency_dispositions={
            item.dependency_key: "satisfied_by_destination"
            for item in assessment.dependencies
        },
        operation_id=f"op_public_{pair}",
    )
    assert result.destination.work_ref.work_kind == destination_work.work_kind


def test_incoming_reference_and_dependency_dispositions_preserve_exact_bytes(
    tmp_path: Path,
) -> None:
    created, predecessor, successor = _prepared(tmp_path)
    dependency = dependency_cases.dependency_record(
        support_ref(),
        dependency_id="dep_historical_source",
        dependency=dependency_cases._portia_record_dependency(  # noqa: SLF001
            event_ref(), "follow_up", "fup_alpha", "1"
        ),
        strength="advisory",
    )
    service_repository = FollowUpWorkflowService(tmp_path).repository
    stored_dependency = service_repository.create_work_record(support_ref(), dependency)
    before = read_bytes(stored_dependency.path)
    service = OwnershipCorrectionWorkflowService(
        tmp_path,
        repository=service_repository,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    assessment = service.assess_correction(
        predecessor,  # type: ignore[arg-type]
        support_ref(),
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        effective_at=WORK_ROOT_UPDATED,
    )
    assert len(assessment.incoming_references) == 1
    assert len(assessment.dependencies) == 1
    result = service.correct_work_root(
        predecessor,  # type: ignore[arg-type]
        support_ref(),
        successor,  # type: ignore[arg-type]
        expected=created.fingerprint,  # type: ignore[union-attr]
        transition_id="lct_public_reference_proof",
        correction_id="owc_public_reference_proof",
        reason={"code": "wrong_work_root"},
        effective_at=WORK_ROOT_UPDATED,
        created_by=AGENT,
        reference_dispositions={
            assessment.incoming_references[0].reference_key: "remain_exact_historical"
        },
        dependency_dispositions={
            assessment.dependencies[0].dependency_key: "remains_historical_to_source"
        },
        operation_id="op_public_reference_proof",
    )
    assert result.incoming_reference_count == 1
    assert result.dependency_count == 1
    assert read_bytes(stored_dependency.path) == before


@pytest.mark.parametrize(
    ("service_type", "source_superseded_before_recovery"),
    [
        (_FailAfterCertificate, False),
        (_FailAfterSourceLifecycle, True),
    ],
)
def test_public_interruption_preserves_evidence_and_generic_recovery_finishes(
    tmp_path: Path,
    service_type: type[OwnershipCorrectionWorkflowService],
    source_superseded_before_recovery: bool,
) -> None:
    created, predecessor, successor = _prepared(tmp_path)
    service = service_type(
        tmp_path,
        integrity_guard=_ClearIntegrityGuard(tmp_path),  # type: ignore[arg-type]
    )
    with pytest.raises(PortiaOperationPartialCommitError):
        service.correct_work_root(
            predecessor,  # type: ignore[arg-type]
            support_ref(),
            successor,  # type: ignore[arg-type]
            expected=created.fingerprint,  # type: ignore[union-attr]
            transition_id="lct_public_recovery",
            correction_id="owc_public_recovery",
            reason={"code": "wrong_work_root"},
            effective_at=WORK_ROOT_UPDATED,
            created_by=AGENT,
            reference_dispositions={},
            dependency_dispositions={},
            operation_id="op_public_recovery",
        )

    certificate_ref = follow_up_reference(support_ref(), "fup_alpha")
    assert (
        service.repository.load_work_record(
            support_ref(), "ownership_correction", "2", "owc_public_recovery"
        ).record.contract_version
        == "2"
    )
    assert (
        service.repository.load_work_record(
            support_ref(), "follow_up", "1", certificate_ref.record_ref.record_id
        ).record.status
        == "active"
    )
    current = OperationJournalStore(tmp_path).load_current("op_public_recovery")
    assert current.revision.to_dict()["state"] == "recovering"
    assert (
        FollowUpWorkflowService(tmp_path)
        .resolve_exact(predecessor)  # type: ignore[arg-type]
        .record.status
        == ("superseded" if source_superseded_before_recovery else "active")
    )

    recovered = RecoveryWorkflowService(tmp_path).resume_incomplete(
        "op_public_recovery",
        expected_pointer=current.pointer_fingerprint,
    )
    assert recovered.state == "completed"
    assert (
        FollowUpWorkflowService(tmp_path)
        .resolve_exact(predecessor)  # type: ignore[arg-type]
        .record.status
        == "superseded"
    )
