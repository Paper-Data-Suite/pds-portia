from __future__ import annotations

import shutil
from copy import deepcopy
from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.storage import FindingSuppressionStore, OperationJournalStore
from portia.storage.derived import DerivedStore
from portia.storage.errors import PortiaConflictError
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.integrity import source_snapshot_digest
from portia.storage.io import exclusive_create, read_bytes
from portia.storage.paths import (
    derived_data_path,
    derived_projection_root,
    workspace_relative,
)
from portia.workflows import (
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
    TEACHER_LOCAL_OPERATOR_ROLE,
    TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
    EventBundle,
    EventBundleWorkflowService,
    EventWorkflowService,
    IntegrityGuard,
    IntegrityOperatorAuthority,
    IntegrityWorkflowService,
    SuppressionAuthorizationReference,
    SuppressionPolicyDefinition,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import event_record, event_ref, participant_record

NOW = "2026-09-16T12:00:00-04:00"
LATER = "2026-09-17T12:00:00-04:00"
OPERATOR = {"type": "local_operator", "display_label": "Local Teacher"}
POLICY = {
    "policy_id": TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
    "policy_version": "1",
}
AUTHORIZATION = {
    "authorized_by": OPERATOR,
    "asserted_role": TEACHER_LOCAL_OPERATOR_ROLE,
    "authorization_reference": {
        "kind": TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
        "reference_id": TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
        "contract_version": TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
    },
}


def _roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )


def _completed_operation(root: Path) -> dict[str, object]:
    _roster(root)
    result = EventBundleWorkflowService(root).commit(
        EventBundle(
            event=event_record(),  # type: ignore[arg-type]
            participants=(participant_record(),),  # type: ignore[arg-type]
        ),
        operation_id="op_integrity_authority",
    )
    current = OperationJournalStore(root).load_current(result.operation_id)
    revision = current.revision.to_dict()["journal_revision"]
    assert isinstance(revision, int)
    source = root / "integrity-authority-source.json"
    exclusive_create(source, b'{"authority":"synthetic"}\n')
    return {
        "operation_id": result.operation_id,
        "journal_revision": revision,
        "contract_version": "2",
    }


def _finding(
    *,
    finding_key: str = "fnd_warning",
    evaluation_key: str = "evl_one",
    target: dict[str, object] | None = None,
    severity: str = "warning",
    effects: list[str] | None = None,
    rule_version: str = "1",
    target_revision: int = 1,
) -> PortiaRecord:
    selected_target = target or {
        "kind": "operation",
        "operation_id": "op_integrity_authority",
    }
    scope = "operation"
    if selected_target.get("kind") in {"portia_work", "portia_work_record"}:
        scope = "work"
    return parse_portia_record(
        "integrity_finding",
        "2",
        {
            "finding_key": finding_key,
            "evaluation_key": evaluation_key,
            "rule_id": "portia.derived_state.projection_stale",
            "rule_version": rule_version,
            "category": "derived_state",
            "code": "projection_stale",
            "severity": severity,
            "assessment": {"result": "confirmed"},
            "effects": effects or ["attention"],
            "scope": scope,
            "primary_target": selected_target,
            "related_targets": [],
            "evidence": [
                {
                    "name": "target_revision",
                    "kind": "integer",
                    "value": target_revision,
                }
            ],
            "observed_at": NOW,
        },
    )


def _install_generation(
    root: Path,
    scope: dict[str, object],
    findings: list[PortiaRecord],
    operation_ref: dict[str, object],
    *,
    generation_id: str,
) -> None:
    source = root / "integrity-authority-source.json"
    source_fp = fingerprint_bytes(read_bytes(source))
    data = {"findings": [finding.to_dict() for finding in findings]}
    data_fp = fingerprint_bytes(canonical_json_bytes(data))
    snapshot_value: dict[str, object] = {
        "schema_version": "1",
        "record_type": "source_snapshot",
        "module_id": "portia",
        "snapshot_algorithm": "portia_source_snapshot_v1",
        "projection_kind": "active_integrity_finding_index",
        "projection_scope": scope,
        "authorization_scope": {
            "authorization_scope_id": "synthetic_complete",
            "coverage": "complete",
            "limitation_codes": [],
        },
        "discovery_roots": ["integrity-authority-source.json"],
        "source_contracts": [
            {"contract_name": "operation_journal", "contract_version": "2"}
        ],
        "entries": [
            {
                "workspace_relative_path": workspace_relative(root, source),
                "byte_length": source_fp.byte_length,
                "sha256_digest": source_fp.digest,
                "source_role": "operational_revision",
                "contract_or_artifact_kind": "operation_journal",
            }
        ],
        "source_snapshot_digest": "",
        "observed_at": NOW,
    }
    snapshot_value["source_snapshot_digest"] = source_snapshot_digest(snapshot_value)
    snapshot = parse_portia_record("source_snapshot", "1", snapshot_value)
    metadata = parse_portia_record(
        "derived_index_metadata",
        "1",
        {
            "schema_version": "1",
            "record_type": "derived_index_metadata",
            "module_id": "portia",
            "generation_id": generation_id,
            "generation_state": "complete",
            "projection_kind": "active_integrity_finding_index",
            "projection_scope": scope,
            "projection_contract_version": "2",
            "builder": {
                "builder_id": "synthetic_integrity_test",
                "builder_version": "1",
            },
            "authorization_scope": snapshot_value["authorization_scope"],
            "source_snapshot": snapshot.to_dict(),
            "data_artifact": {
                "workspace_relative_path": workspace_relative(
                    root,
                    derived_data_path(
                        root,
                        "active_integrity_finding_index",
                        scope,
                        generation_id,
                    ),
                ),
                "contract_version": "2",
                "fingerprint": data_fp.to_dict(),
            },
            "validation": {
                "schema_validation": "passed",
                "identity_validation": "passed",
                "reference_validation": "passed",
                "privacy_validation": "passed",
                "invariant_validation": "passed",
            },
            "generating_operation": operation_ref,
            "generated_at": NOW,
        },
    )
    pointer = parse_portia_record(
        "derived_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "derived_current_pointer",
            "module_id": "portia",
            "projection_kind": "active_integrity_finding_index",
            "projection_scope": scope,
            "generation_ref": {
                "generation_id": generation_id,
                "contract_version": "1",
            },
        },
    )
    store = DerivedStore(root)
    prior = store.load_current_or_none(
        "active_integrity_finding_index", scope, require_fresh=False
    )
    store.install(
        metadata,
        pointer,
        data,
        expected_current=None if prior is None else prior.pointer_fingerprint,
    )


def _binding(finding: PortiaRecord) -> dict[str, object]:
    value = finding.to_dict()
    return {
        key: deepcopy(value[key])
        for key in (
            "finding_key",
            "evaluation_key",
            "rule_id",
            "rule_version",
            "severity",
            "effects",
        )
    }


def _create_suppression(
    service: IntegrityWorkflowService,
    scope: dict[str, object],
    finding: PortiaRecord,
    operation_ref: dict[str, object],
    *,
    suppression_id: str,
    conditions: list[dict[str, object]] | None = None,
) -> object:
    value = finding.to_dict()
    return service.suppress_finding(
        scope,
        suppression_id=suppression_id,
        finding_key=str(value["finding_key"]),
        evaluation_key=str(value["evaluation_key"]),
        finding_binding=_binding(finding),
        presentation_scope={
            "surfaces": ["teacher_dashboard"],
            "audiences": ["local_teacher"],
        },
        policy=POLICY,
        authorization=AUTHORIZATION,
        rationale="Temporarily reduce duplicate presentation noise.",
        starts_at=NOW,
        expiry_conditions=conditions or [{"kind": "target_evaluation_change"}],
        created_by_operation=operation_ref,
        created_at=NOW,
    )


def test_acknowledgement_is_exact_append_only_and_never_clears_blocker(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    blocker = _finding(
        finding_key="fnd_blocker",
        severity="error",
        effects=["review_required", "block_operation_completion"],
    )
    _install_generation(
        tmp_path, scope, [blocker], operation_ref, generation_id="dgen_blocker_one"
    )
    service = IntegrityWorkflowService(tmp_path)

    stored = service.acknowledge_finding(
        scope,
        acknowledgement_id="fack_exact_review",
        finding_key="fnd_blocker",
        evaluation_key="evl_one",
        acknowledged_at=NOW,
        acknowledged_by=OPERATOR,
        acknowledgement_category="reviewed",
        rationale="Reviewed exact persistence diagnostic.",
        creating_operation=operation_ref,
    )

    assert stored.record.to_dict()["finding_key"] == "fnd_blocker"
    with pytest.raises(WorkflowPrerequisiteError, match="blocks"):
        service.require_operation_completion("op_integrity_authority")
    with pytest.raises(PortiaConflictError):
        service.acknowledge_finding(
            scope,
            acknowledgement_id="fack_exact_review",
            finding_key="fnd_blocker",
            evaluation_key="evl_one",
            acknowledged_at=NOW,
            acknowledged_by=OPERATOR,
            acknowledgement_category="reviewed",
        )

    _install_generation(
        tmp_path, scope, [], operation_ref, generation_id="dgen_clean_successor"
    )
    service.require_operation_completion("op_integrity_authority")
    assert stored.path.exists()


def test_acknowledgement_rejects_recombined_or_unavailable_current_identity(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    first = _finding(finding_key="fnd_first", evaluation_key="evl_first")
    second = _finding(finding_key="fnd_second", evaluation_key="evl_second")
    _install_generation(
        tmp_path, scope, [first, second], operation_ref, generation_id="dgen_two_findings"
    )
    service = IntegrityWorkflowService(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="same current finding"):
        service.acknowledge_finding(
            scope,
            acknowledgement_id="fack_recombined",
            finding_key="fnd_first",
            evaluation_key="evl_second",
            acknowledged_at=NOW,
            acknowledged_by=OPERATOR,
            acknowledgement_category="reviewed",
        )
    with pytest.raises(WorkflowPrerequisiteError, match="unavailable"):
        service.acknowledge_finding(
            {"scope": "operation", "operation_ref": {"operation_id": "op_missing"}},
            acknowledgement_id="fack_missing",
            finding_key="fnd_first",
            evaluation_key="evl_first",
            acknowledged_at=NOW,
            acknowledged_by=OPERATOR,
            acknowledgement_category="reviewed",
        )


def test_suppression_creation_binds_exact_finding_authority_and_scope(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _finding()
    _install_generation(
        tmp_path, scope, [finding], operation_ref, generation_id="dgen_warning_one"
    )
    service = IntegrityWorkflowService(tmp_path)
    created = _create_suppression(
        service,
        scope,
        finding,
        operation_ref,
        suppression_id="fsup_exact_warning",
    )
    value = created.revision.to_dict()

    assert value["suppression_revision"] == 1
    assert value["previous_suppression_revision"] is None
    assert value["state"] == "active"
    assert value["finding_binding"] == _binding(finding)
    assert value["policy"] == POLICY
    assert value["authorization"] == AUTHORIZATION
    assert created.pointer.to_dict()["suppression_revision"] == 1

    mismatch = _binding(finding)
    mismatch["rule_version"] = "2"
    with pytest.raises(WorkflowPrerequisiteError, match="exactly match"):
        service.suppress_finding(
            scope,
            suppression_id="fsup_bad_binding",
            finding_key="fnd_warning",
            evaluation_key="evl_one",
            finding_binding=mismatch,
            presentation_scope={"surfaces": ["dashboard"], "audiences": ["teacher"]},
            policy=POLICY,
            authorization=AUTHORIZATION,
            rationale="Bounded rationale.",
            starts_at=NOW,
            expiry_conditions=[{"kind": "target_evaluation_change"}],
            created_by_operation=operation_ref,
            created_at=NOW,
        )


@pytest.mark.parametrize(
    ("severity", "effects"),
    [
        ("error", ["attention"]),
        ("critical", ["review_required"]),
        ("warning", ["block_current_use"]),
        ("warning", ["block_lifecycle_writes"]),
        ("warning", ["block_operation_completion"]),
        ("warning", ["block_work_writes"]),
        ("warning", ["block_class_writes"]),
        ("warning", ["quarantine_target"]),
    ],
)
def test_error_critical_blocking_and_quarantine_findings_cannot_be_suppressed(
    tmp_path: Path,
    severity: str,
    effects: list[str],
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _finding(severity=severity, effects=effects)
    _install_generation(
        tmp_path, scope, [finding], operation_ref, generation_id="dgen_unsuppressible"
    )
    with pytest.raises(WorkflowPrerequisiteError, match="suppress"):
        _create_suppression(
            IntegrityWorkflowService(tmp_path),
            scope,
            finding,
            operation_ref,
            suppression_id="fsup_prohibited",
        )


def test_release_expire_and_supersede_are_immutable_pointer_guarded_revisions(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _finding()
    _install_generation(
        tmp_path, scope, [finding], operation_ref, generation_id="dgen_lifecycle"
    )
    service = IntegrityWorkflowService(tmp_path)

    released_initial = _create_suppression(
        service, scope, finding, operation_ref, suppression_id="fsup_release"
    )
    initial_path = (
        tmp_path
        / "portia"
        / "finding_suppressions"
        / "fsup_release"
        / "revisions"
        / "1.json"
    )
    initial_bytes = read_bytes(initial_path)
    released = service.release_suppression(
        "fsup_release",
        expected_pointer=released_initial.pointer_fingerprint,
        resolving_operation=operation_ref,
        effective_at=LATER,
        resolved_by=OPERATOR,
        rationale="Presentation suppression no longer needed.",
    )
    assert released.revision.to_dict()["state"] == "released"
    assert read_bytes(initial_path) == initial_bytes
    with pytest.raises(PortiaConflictError):
        service.release_suppression(
            "fsup_release",
            expected_pointer=released_initial.pointer_fingerprint,
            resolving_operation=operation_ref,
            effective_at=LATER,
            resolved_by=OPERATOR,
            rationale="Stale pointer must not win.",
        )

    expiring = _create_suppression(
        service,
        scope,
        finding,
        operation_ref,
        suppression_id="fsup_expire",
        conditions=[{"kind": "fixed_timestamp", "expires_at": LATER}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not satisfy"):
        service.expire_suppression(
            "fsup_expire",
            expected_pointer=expiring.pointer_fingerprint,
            matched_expiry_condition={"kind": "fixed_timestamp", "expires_at": LATER},
            evaluated_at=NOW,
            resolved_by=OPERATOR,
        )
    expired = service.expire_suppression(
        "fsup_expire",
        expected_pointer=expiring.pointer_fingerprint,
        matched_expiry_condition={"kind": "fixed_timestamp", "expires_at": LATER},
        evaluated_at=LATER,
        resolved_by=OPERATOR,
    )
    assert expired.revision.to_dict()["state"] == "expired"

    successor = _create_suppression(
        service, scope, finding, operation_ref, suppression_id="fsup_successor"
    )
    superseded_initial = _create_suppression(
        service, scope, finding, operation_ref, suppression_id="fsup_superseded"
    )
    superseded = service.supersede_suppression(
        "fsup_superseded",
        expected_pointer=superseded_initial.pointer_fingerprint,
        resolving_operation=operation_ref,
        successor_suppression={
            "suppression_id": "fsup_successor",
            "suppression_revision": 1,
            "contract_version": "1",
        },
        effective_at=LATER,
        resolved_by=OPERATOR,
        rationale="Use the explicitly named successor series.",
    )
    assert superseded.revision.to_dict()["state"] == "superseded"
    assert successor.revision.to_dict()["state"] == "active"


def test_all_change_based_expiry_conditions_use_authoritative_evidence(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    original = _finding()
    _install_generation(
        tmp_path, scope, [original], operation_ref, generation_id="dgen_expiry_before"
    )
    service = IntegrityWorkflowService(tmp_path)
    kinds = [
        "target_evaluation_change",
        "rule_version_change",
        "target_revision_or_fingerprint_change",
        "severity_or_effects_change",
    ]
    states = {
        kind: _create_suppression(
            service,
            scope,
            original,
            operation_ref,
            suppression_id=f"fsup_{kind}",
            conditions=[{"kind": kind}],
        )
        for kind in kinds
    }
    for kind, state in states.items():
        with pytest.raises(WorkflowPrerequisiteError, match="does not satisfy"):
            service.expire_suppression(
                f"fsup_{kind}",
                expected_pointer=state.pointer_fingerprint,
                matched_expiry_condition={"kind": kind},
                evaluated_at=LATER,
                resolved_by=OPERATOR,
                projection_scope=scope,
            )

    changed = _finding(
        evaluation_key="evl_two",
        severity="advisory",
        rule_version="2",
        target_revision=2,
    )
    _install_generation(
        tmp_path, scope, [changed], operation_ref, generation_id="dgen_expiry_after"
    )
    for kind, state in states.items():
        expired = service.expire_suppression(
            f"fsup_{kind}",
            expected_pointer=state.pointer_fingerprint,
            matched_expiry_condition={"kind": kind},
            evaluated_at=LATER,
            resolved_by=OPERATOR,
            projection_scope=scope,
        )
        assert expired.revision.to_dict()["state"] == "expired"


def test_policy_version_expiry_uses_explicit_authority_selection(
    tmp_path: Path,
) -> None:
    reference = SuppressionAuthorizationReference(
        kind=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
        reference_id=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
        contract_version=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
    )
    policies = tuple(
        SuppressionPolicyDefinition(
            policy_id=TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
            policy_version=version,
            allowed_asserted_roles=frozenset({TEACHER_LOCAL_OPERATOR_ROLE}),
            allowed_attribution_agent_types=frozenset({"local_operator"}),
            authorization_reference=reference,
        )
        for version in ("1", "2")
    )
    current_v1 = IntegrityOperatorAuthority(
        policies=policies,
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "1"},
    )
    current_v2 = IntegrityOperatorAuthority(
        policies=policies,
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "2"},
    )
    assert not current_v1.policy_version_changed(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1"
    )
    assert current_v2.policy_version_changed(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1"
    )

    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    finding = _finding()
    _install_generation(
        tmp_path, scope, [finding], operation_ref, generation_id="dgen_policy_expiry"
    )
    created = _create_suppression(
        IntegrityWorkflowService(tmp_path, authority=current_v1),
        scope,
        finding,
        operation_ref,
        suppression_id="fsup_policy_expiry",
        conditions=[{"kind": "policy_version_change"}],
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not satisfy"):
        IntegrityWorkflowService(tmp_path, authority=current_v1).expire_suppression(
            "fsup_policy_expiry",
            expected_pointer=created.pointer_fingerprint,
            matched_expiry_condition={"kind": "policy_version_change"},
            evaluated_at=LATER,
            resolved_by=OPERATOR,
        )
    expired = IntegrityWorkflowService(
        tmp_path, authority=current_v2
    ).expire_suppression(
        "fsup_policy_expiry",
        expected_pointer=created.pointer_fingerprint,
        matched_expiry_condition={"kind": "policy_version_change"},
        evaluated_at=LATER,
        resolved_by=OPERATOR,
    )
    assert expired.revision.to_dict()["state"] == "expired"


def test_current_use_guard_blocks_exact_target_and_clean_successor_permits(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    work = event_ref()
    scope = {"scope": "work", "work_ref": work.to_dict()}
    target = {"kind": "portia_work", "work_ref": work.to_dict()}
    blocker = _finding(
        finding_key="fnd_current_use",
        target=target,
        severity="error",
        effects=["block_current_use"],
    )
    _install_generation(
        tmp_path, scope, [blocker], operation_ref, generation_id="dgen_current_block"
    )
    with pytest.raises(WorkflowPrerequisiteError, match="block_current_use"):
        EventWorkflowService(
            tmp_path, quarantine=IntegrityGuard(tmp_path)
        ).require_current_use(work)

    IntegrityWorkflowService(tmp_path).require_effect_allowed(
        scope,
        {
            "kind": "work",
            "work_ref": event_ref(event_id="evt_near_miss").to_dict(),
        },
        "block_current_use",
    )
    _install_generation(
        tmp_path, scope, [], operation_ref, generation_id="dgen_current_clean"
    )
    assert (
        EventWorkflowService(
            tmp_path, quarantine=IntegrityGuard(tmp_path)
        ).require_current_use(work).record.status
        == "active"
    )


def test_explicitly_nongoverned_predecessor_current_use_does_not_require_projection(
    tmp_path: Path,
) -> None:
    _completed_operation(tmp_path)

    assert EventWorkflowService(tmp_path).require_current_use(event_ref()).record.status == (
        "active"
    )


def test_governed_scope_with_no_integrity_namespace_fails_closed(
    tmp_path: Path,
) -> None:
    _completed_operation(tmp_path)
    work = event_ref()
    guarded = EventWorkflowService(tmp_path, quarantine=IntegrityGuard(tmp_path))

    with pytest.raises(WorkflowPrerequisiteError, match="unavailable"):
        guarded.require_current_use(work)

    scope = {"scope": "work", "work_ref": work.to_dict()}
    derived_projection_root(
        tmp_path, "active_integrity_finding_index", scope
    ).mkdir(parents=True)
    with pytest.raises(WorkflowPrerequisiteError, match="unavailable"):
        guarded.require_current_use(work)


def test_governed_scope_cannot_downgrade_after_projection_deletion(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    work = event_ref()
    scope = {"scope": "work", "work_ref": work.to_dict()}
    _install_generation(
        tmp_path, scope, [], operation_ref, generation_id="dgen_before_deletion"
    )
    guarded = EventWorkflowService(tmp_path, quarantine=IntegrityGuard(tmp_path))
    assert guarded.require_current_use(work).record.status == "active"

    projection_root = derived_projection_root(
        tmp_path, "active_integrity_finding_index", scope
    )
    shutil.rmtree(projection_root)

    with pytest.raises(WorkflowPrerequisiteError, match="unavailable"):
        guarded.require_current_use(work)


def test_shared_completion_gate_ignores_acknowledgement_and_rejects_suppression(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    operation_id = "op_blocked_bundle"
    work_scope = {
        "scope": "work",
        "work_ref": event_ref(event_id="evt_beta").to_dict(),
    }
    _install_generation(
        tmp_path,
        work_scope,
        [],
        operation_ref,
        generation_id="dgen_completion_work_clean",
    )
    scope = IntegrityWorkflowService.operation_scope(operation_id)
    blocker = _finding(
        finding_key="fnd_completion_block",
        target={"kind": "operation", "operation_id": operation_id},
        severity="error",
        effects=["review_required", "block_operation_completion"],
    )
    _install_generation(
        tmp_path, scope, [blocker], operation_ref, generation_id="dgen_completion_block"
    )
    service = IntegrityWorkflowService(tmp_path)
    service.acknowledge_finding(
        scope,
        acknowledgement_id="fack_completion_block",
        finding_key="fnd_completion_block",
        evaluation_key="evl_one",
        acknowledged_at=NOW,
        acknowledged_by=OPERATOR,
        acknowledgement_category="reviewed",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="suppress"):
        _create_suppression(
            service,
            scope,
            blocker,
            operation_ref,
            suppression_id="fsup_completion_block",
        )

    with pytest.raises(WorkflowPrerequisiteError, match="block_operation_completion"):
        EventBundleWorkflowService(
            tmp_path, quarantine=IntegrityGuard(tmp_path)
        ).commit(
            EventBundle(
                event=event_record(event_id="evt_beta"),  # type: ignore[arg-type]
                participants=(
                    participant_record(
                        event_id="evt_beta", participant_id="ep_beta"
                    ),
                ),  # type: ignore[arg-type]
            ),
            operation_id=operation_id,
        )
    current = OperationJournalStore(tmp_path).load_current(operation_id)
    assert current.revision.to_dict()["state"] == "staged"
    assert FindingSuppressionStore(tmp_path).inspect_recovery(
        "fsup_completion_block"
    ).disposition == "absent"


def test_governed_completion_with_missing_integrity_state_fails_closed(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    operation_id = "op_missing_completion_integrity"
    work_scope = {
        "scope": "work",
        "work_ref": event_ref(event_id="evt_gamma").to_dict(),
    }
    _install_generation(
        tmp_path,
        work_scope,
        [],
        operation_ref,
        generation_id="dgen_missing_completion_work_clean",
    )

    with pytest.raises(WorkflowPrerequisiteError, match="unavailable"):
        EventBundleWorkflowService(
            tmp_path, quarantine=IntegrityGuard(tmp_path)
        ).commit(
            EventBundle(
                event=event_record(event_id="evt_gamma"),  # type: ignore[arg-type]
                participants=(
                    participant_record(
                        event_id="evt_gamma", participant_id="ep_gamma"
                    ),
                ),  # type: ignore[arg-type]
            ),
            operation_id=operation_id,
        )
    current = OperationJournalStore(tmp_path).load_current(operation_id)
    assert current.revision.to_dict()["state"] == "staged"
