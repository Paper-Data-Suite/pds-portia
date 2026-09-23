\
"""Smoke Issue #49 native attention from an installed Portia wheel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _authenticate_core(repository: Path, core_wheel: Path) -> None:
    if core_wheel.name != "pds_core-0.6.3-py3-none-any.whl":
        raise RuntimeError(
            "Issue #49 installed-wheel smoke requires the Core 0.6.3 wheel"
        )
    _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    _authenticate_core(repository, core_wheel)

    code = r"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.attention import (
    AttentionQueryService,
    FollowUpScheduleQuery,
    FollowUpScheduleQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage import OperationJournalStore, PortiaRepository
from portia.storage.derived import DerivedStore
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.integrity import source_snapshot_digest
from portia.storage.io import exclusive_create, read_bytes
from portia.storage.paths import derived_data_path, workspace_relative
from portia.storage.series import QuarantineStore
from portia.workflows import (
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
    TEACHER_LOCAL_OPERATOR_ROLE,
    TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
    DependencyWorkflowService,
    EventBundle,
    EventBundleWorkflowService,
    FollowUpWorkflowService,
    IntegrityWorkflowService,
    ReviewWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    support_process_participant_reference,
)

WORKSPACE = Path("synthetic-issue49-workspace")
CLASS_ID = "class_a"
STUDENT_ID = "student_1"
AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")
T0 = "2026-09-20T09:00:00-04:00"
T1 = "2026-09-20T09:05:00-04:00"
T2 = "2026-09-20T09:10:00-04:00"
T3 = "2026-09-20T09:15:00-04:00"
NOW = "2026-09-16T12:00:00-04:00"
LATER = "2026-09-22T12:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue49_installed_smoke"}
OPERATOR = {"type": "local_operator", "display_label": "Synthetic Teacher"}
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


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def event_ref(event_id):
    return ExactPortiaWorkRef(
        class_id=CLASS_ID,
        work_id=event_id,
        work_kind="event",
        contract_version="2",
    )


def event_record(event_id):
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": event_id,
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {
                "precision": "exact",
                "started_at": T0,
            },
            "summary": "Synthetic installed-wheel event.",
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": OPERATOR,
            "updated_at": T0,
            "updated_by": OPERATOR,
        },
    )


def participant_record(event_id, participant_id):
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": event_id,
            "participant_id": participant_id,
            "status": "active",
            "subject": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": CLASS_ID,
                    "student_id": STUDENT_ID,
                },
                "display_snapshot": {"display_name": "Private Synthetic Student"},
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": OPERATOR,
            "updated_at": T0,
            "updated_by": OPERATOR,
        },
    )


def commit_event(event_id, participant_id, operation_id):
    result = EventBundleWorkflowService(WORKSPACE).commit(
        EventBundle(
            event=event_record(event_id),
            participants=(participant_record(event_id, participant_id),),
        ),
        operation_id=operation_id,
    )
    current = OperationJournalStore(WORKSPACE).load_current(result.operation_id)
    revision = current.revision.to_dict()["journal_revision"]
    return {
        "operation_id": result.operation_id,
        "journal_revision": revision,
        "contract_version": current.revision.contract_version,
    }


def follow_up(event_id, participant_id, follow_up_id, date, state="scheduled"):
    value = {
        "schema_version": "1",
        "record_type": "follow_up",
        "module_id": "portia",
        "class_id": CLASS_ID,
        "work_kind": "event",
        "work_id": event_id,
        "follow_up_id": follow_up_id,
        "status": "active",
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": participant_id,
                "contract_version": "3",
            },
        },
        "owner": {
            "kind": "represented_human",
            "person": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
        },
        "purpose": {"kind": "student_check_in"},
        "planned_timing": {"kind": "date_only", "date": date},
        "workflow_state": state,
        "creation_source": {"type": "digital_entry"},
        "created_at": T0,
        "created_by": AGENT,
        "updated_at": T0,
        "updated_by": AGENT,
    }
    if state == "completed":
        value["completed_at"] = T1
    return parse_portia_record("follow_up", "1", value)


def review_record(event_id):
    return parse_portia_record(
        "review",
        "1",
        {
            "schema_version": "1",
            "record_type": "review",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": event_id,
            "review_id": "rvw_smoke_incomplete",
            "status": "active",
            "review_state": "open",
            "trigger": {"kind": "routine_review"},
            "question": {
                "kind": "evidence_review",
                "text": "What exact information is available?",
            },
            "target": {"kind": "event"},
            "reviewer": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "evidence_considered": [],
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": OPERATOR,
            "updated_at": T0,
            "updated_by": OPERATOR,
        },
    )


def support_ref():
    return ExactPortiaWorkRef(
        class_id=CLASS_ID,
        work_id="sup_attention_smoke",
        work_kind="support_process",
        contract_version="1",
    )


def support_root(*, status="proposed", updated_at=T0):
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": "sup_attention_smoke",
            "school_year": "2026-2027",
            "status": status,
            "workflow_state": "planning",
            "review_on": "2026-09-21",
            "summary": "Synthetic installed-wheel support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": OPERATOR,
            "updated_at": updated_at,
            "updated_by": OPERATOR,
        },
    )


def support_participant(participant_id, *, status="proposed", updated_at=T0):
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": "sup_attention_smoke",
            "participant_id": participant_id,
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic learner {participant_id}",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": OPERATOR,
            "updated_at": updated_at,
            "updated_by": OPERATOR,
        },
    )


def dependency_record():
    return parse_portia_record(
        "dependency",
        "1",
        {
            "schema_version": "1",
            "record_type": "dependency",
            "module_id": "portia",
            "class_id": CLASS_ID,
            "work_id": "sup_attention_smoke",
            "dependency_id": "dep_smoke_review",
            "status": "active",
            "dependent": {
                "kind": "work",
                "work_kind": "support_process",
                "contract_version": "1",
            },
            "dependency": {
                "kind": "portia_record",
                "work_record_ref": {
                    "work_ref": support_ref().to_dict(),
                    "record_ref": {
                        "record_kind": "support_process_participant",
                        "record_id": "spp_smoke_pending",
                        "contract_version": "1",
                    },
                },
            },
            "strength": "required",
            "applies_to": "current_use",
            "purpose": "workflow_prerequisite",
            "creation_source": {"type": "digital_entry"},
            "created_at": T1,
            "created_by": OPERATOR,
            "updated_at": T1,
            "updated_by": OPERATOR,
        },
    )


def prepared_recovery_operation():
    data = {
        "schema_version": "2",
        "record_type": "operation_journal",
        "module_id": "portia",
        "operation_id": "op_smoke_recovery",
        "operation_kind": "create_record",
        "intent_digest": "1" * 64,
        "scope": "workspace",
        "primary_target": {
            "kind": "actor_directory_record",
            "actor_directory_record_ref": {
                "kind": "actor",
                "actor_ref": {
                    "actor_id": "actr_smoke_recovery",
                    "contract_version": "1",
                },
            },
        },
        "affected_targets": [],
        "intent_facts": [
            {
                "name": "requested_record_kind",
                "kind": "token",
                "value": "actor",
            }
        ],
        "initiated_at": T0,
        "initiated_by": OPERATOR,
        "authorization_references": [],
        "journal_revision": 1,
        "previous_journal_revision": None,
        "state": "prepared",
        "preflight_snapshot_digest": "2" * 64,
        "preflight_snapshot": [
            {
                "target": {
                    "kind": "actor_directory_record",
                    "actor_directory_record_ref": {
                        "kind": "actor",
                        "actor_ref": {
                            "actor_id": "actr_smoke_recovery",
                            "contract_version": "1",
                        },
                    },
                },
                "representation_role": "canonical_domain",
                "expected_state": {"presence": "must_be_absent"},
                "workspace_relative_path": (
                    "portia/actors/actr_smoke_recovery/actor.json"
                ),
                "contract_version": "1",
                "source_basis": "canonical",
                "source_projection": None,
                "selected_state": [],
                "observed_at": T1,
            }
        ],
        "lock_set": [
            {
                "lock_id": "lock_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "sequence": 1,
                "lock_scope": "actor_directory_record",
                "protected_target": {
                    "kind": "actor_directory_record",
                    "actor_directory_record_ref": {
                        "kind": "actor",
                        "actor_ref": {
                            "actor_id": "actr_smoke_recovery",
                            "contract_version": "1",
                        },
                    },
                },
                "lock_path": (
                    "portia/locks/"
                    "lock_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json"
                ),
                "disposition": "planned",
                "fingerprint": None,
                "acquired_at": None,
                "released_at": None,
            }
        ],
        "write_set": [
            {
                "step_id": "step_smoke_recovery",
                "sequence": 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": {
                    "kind": "actor_directory_record",
                    "actor_directory_record_ref": {
                        "kind": "actor",
                        "actor_ref": {
                            "actor_id": "actr_smoke_recovery",
                            "contract_version": "1",
                        },
                    },
                },
                "representation_role": "canonical_domain",
                "destination_path": (
                    "portia/actors/actr_smoke_recovery/actor.json"
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": "1",
                    "fingerprint": {
                        "algorithm": "sha256",
                        "digest": "3" * 64,
                        "byte_length": 512,
                    },
                    "selected_state": [],
                },
                "disposition": "pending",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": None,
            }
        ],
        "staged_artifacts": [],
        "commit_point": {"reached": False, "reached_at": None},
        "compensation_plan": [],
        "recovery_plan": [
            "resume",
            "abandon_preacceptance_artifacts",
            "require_manual_review",
        ],
        "partial_state": {
            "durability_assessment": "none",
            "accepted_steps": [],
            "verified_steps": [],
            "durable_unverified_steps": [],
            "indeterminate_steps": [],
            "remaining_canonical_steps": ["step_smoke_recovery"],
            "remaining_post_commit_steps": [],
            "current_pointer_changes": [],
            "held_or_possible_locks": [],
            "quarantined_targets": [],
            "active_finding_keys": [],
            "recommended_disposition": "resume",
        },
        "created_at": T2,
        "updated_at": T2,
    }
    journal = parse_portia_record("operation_journal", "2", data)
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": "op_smoke_recovery",
            "journal_revision": 1,
        },
    )
    OperationJournalStore(WORKSPACE).create(journal, pointer)


def finding(code, finding_key, evaluation_key, *, severity="warning", effects=None):
    category = (
        "lifecycle"
        if code == "selected_history_ambiguous"
        else "persistence_recovery"
    )
    return parse_portia_record(
        "integrity_finding",
        "2",
        {
            "finding_key": finding_key,
            "evaluation_key": evaluation_key,
            "rule_id": f"portia.synthetic.{code}",
            "rule_version": "1",
            "category": category,
            "code": code,
            "severity": severity,
            "assessment": {"result": "confirmed"},
            "effects": effects or ["attention"],
            "scope": "operation",
            "primary_target": {
                "kind": "operation",
                "operation_id": "op_smoke_alpha",
            },
            "related_targets": [],
            "evidence": [
                {"name": "target_revision", "kind": "integer", "value": 1}
            ],
            "observed_at": NOW,
        },
    )


def install_generation(operation_ref, findings, generation_id, source_name):
    source = WORKSPACE / source_name
    if not source.exists():
        exclusive_create(source, b'{"authority":"synthetic"}\n')
    source_fp = fingerprint_bytes(read_bytes(source))
    data = {"findings": [value.to_dict() for value in findings]}
    data_fp = fingerprint_bytes(canonical_json_bytes(data))
    scope = IntegrityWorkflowService.operation_scope(
        str(operation_ref["operation_id"])
    )
    snapshot_value = {
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
        "discovery_roots": [source_name],
        "source_contracts": [
            {"contract_name": "operation_journal", "contract_version": "2"}
        ],
        "entries": [
            {
                "workspace_relative_path": workspace_relative(WORKSPACE, source),
                "byte_length": source_fp.byte_length,
                "sha256_digest": source_fp.digest,
                "source_role": "operational_revision",
                "contract_or_artifact_kind": "operation_journal",
            }
        ],
        "source_snapshot_digest": "",
        "observed_at": NOW,
    }
    snapshot_value["source_snapshot_digest"] = source_snapshot_digest(
        snapshot_value
    )
    snapshot_record = parse_portia_record(
        "source_snapshot",
        "1",
        snapshot_value,
    )
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
                "builder_id": "issue49_installed_smoke",
                "builder_version": "1",
            },
            "authorization_scope": snapshot_value["authorization_scope"],
            "source_snapshot": snapshot_record.to_dict(),
            "data_artifact": {
                "workspace_relative_path": workspace_relative(
                    WORKSPACE,
                    derived_data_path(
                        WORKSPACE,
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
    DerivedStore(WORKSPACE).install(metadata, pointer, data)
    return scope, source


def binding(value):
    data = value.to_dict()
    return {
        key: deepcopy(data[key])
        for key in (
            "finding_key",
            "evaluation_key",
            "rule_id",
            "rule_version",
            "severity",
            "effects",
        )
    }


write_class_roster(
    WORKSPACE,
    create_roster(
        CLASS_ID,
        [
            {
                "student_id": STUDENT_ID,
                "last_name": "Private",
                "first_name": "Synthetic",
                "period": "2",
            }
        ],
    ),
)

op_alpha = commit_event("evt_smoke_alpha", "ep_smoke_alpha", "op_smoke_alpha")
op_beta = commit_event("evt_smoke_beta", "ep_smoke_beta", "op_smoke_beta")
op_gamma = commit_event("evt_smoke_gamma", "ep_smoke_gamma", "op_smoke_gamma")

repository = PortiaRepository(WORKSPACE)
alpha = event_ref("evt_smoke_alpha")
followups = FollowUpWorkflowService(WORKSPACE, repository=repository)
for identifier, date, state in (
    ("fup_smoke_future", "2026-09-22", "scheduled"),
    ("fup_smoke_due", "2026-09-21", "scheduled"),
    ("fup_smoke_overdue", "2026-09-20", "scheduled"),
    ("fup_smoke_completed", "2026-09-20", "completed"),
):
    followups.create(
        alpha,
        follow_up(
            "evt_smoke_alpha",
            "ep_smoke_alpha",
            identifier,
            date,
            state,
        ),
    )
ReviewWorkflowService(WORKSPACE, repository=repository).create(
    alpha,
    review_record("evt_smoke_alpha"),
)

support = SupportProcessWorkflowService(WORKSPACE, repository=repository)
root = support.create(support_root())
participants = SupportProcessParticipantWorkflowService(
    WORKSPACE,
    repository=repository,
)
participants.create(
    support_ref(),
    support_participant("spp_smoke_active"),
)
active_ref = support_process_participant_reference(
    support_ref(),
    "spp_smoke_active",
)
prior_active = participants.load_exact(active_ref)
participants.transition_lifecycle(
    active_ref,
    support_participant(
        "spp_smoke_active",
        status="active",
        updated_at=T1,
    ),
    expected=prior_active.fingerprint,
    transition_id="lct_smoke_participant_active",
    reason_code="planning_confirmed",
    operation_id="op_smoke_participant_active",
)
participants.create(
    support_ref(),
    support_participant("spp_smoke_pending"),
)
DependencyWorkflowService(
    WORKSPACE,
    repository=repository,
).create(
    support_ref(),
    dependency_record(),
)
support.transition_lifecycle(
    support_ref(),
    support_root(status="active", updated_at=T2),
    expected=root.fingerprint,
    transition_id="lct_smoke_support_active",
    reason_code="planning_confirmed",
    operation_id="op_smoke_support_active",
)

prepared_recovery_operation()

q_record = parse_portia_record(
    "quarantine_record",
    "2",
    {
        "schema_version": "2",
        "record_type": "quarantine_record",
        "module_id": "portia",
        "quarantine_id": "qnt_0123456789abcdef0123456789abcdef",
        "quarantine_revision": 1,
        "previous_quarantine_revision": None,
        "state": "active",
        "target": {
            "kind": "work",
            "work_ref": event_ref("evt_smoke_gamma").to_dict(),
        },
        "reason": "partial_commit",
        "reason_detail": "Synthetic installed-wheel containment.",
        "effects": [
            "block_current_use",
            "block_work_writes",
            "review_required",
        ],
        "origin": {
            "applying_operation": op_gamma,
            "supporting_finding_keys": [],
            "applied_at": T3,
            "applied_by": OPERATOR,
            "release_requirements": ["canonical_state_reconciled"],
            "review_deadline": None,
        },
        "resolution": None,
        "created_at": T3,
    },
)
q_pointer = parse_portia_record(
    "quarantine_current_pointer",
    "1",
    {
        "schema_version": "1",
        "record_type": "quarantine_current_pointer",
        "module_id": "portia",
        "quarantine_id": "qnt_0123456789abcdef0123456789abcdef",
        "quarantine_revision": 1,
    },
)
QuarantineStore(WORKSPACE).create(q_record, q_pointer)

conflict = finding(
    "selected_history_ambiguous",
    "fnd_smoke_conflict",
    "evl_smoke_conflict",
    severity="error",
    effects=["review_required", "block_operation_completion"],
)
routine = finding(
    "content_digest_mismatch",
    "fnd_smoke_routine",
    "evl_smoke_routine",
)
alpha_scope, _alpha_source = install_generation(
    op_alpha,
    [conflict, routine],
    "dgen_smoke_fresh",
    "integrity-fresh-source.json",
)
integrity = IntegrityWorkflowService(WORKSPACE)
integrity.acknowledge_finding(
    alpha_scope,
    acknowledgement_id="fack_smoke_conflict",
    finding_key="fnd_smoke_conflict",
    evaluation_key="evl_smoke_conflict",
    acknowledged_at=NOW,
    acknowledged_by=OPERATOR,
    acknowledgement_category="reviewed",
    creating_operation=op_alpha,
)
integrity.suppress_finding(
    alpha_scope,
    suppression_id="fsup_smoke_routine",
    finding_key="fnd_smoke_routine",
    evaluation_key="evl_smoke_routine",
    finding_binding=binding(routine),
    presentation_scope={
        "surfaces": ["teacher_dashboard"],
        "audiences": ["local_teacher"],
    },
    policy=POLICY,
    authorization=AUTHORIZATION,
    rationale="Synthetic duplicate-presentation suppression.",
    starts_at=NOW,
    expiry_conditions=[
        {"kind": "fixed_timestamp", "expires_at": LATER}
    ],
    created_by_operation=op_alpha,
    created_at=NOW,
)

_beta_scope, beta_source = install_generation(
    op_beta,
    [],
    "dgen_smoke_stale",
    "integrity-stale-source.json",
)
beta_source.write_bytes(b'{"authority":"changed"}\n')

before = snapshot(WORKSPACE)

schedule = FollowUpScheduleQueryService(
    WORKSPACE,
    repository=repository,
).query(
    FollowUpScheduleQuery(
        scope=PortiaAttentionScope.work_scope(alpha),
        as_of=AS_OF,
    )
)
schedule_state = {
    item.source_ref.record_ref.record_id: item.timing.classification
    for item in schedule
}

service = AttentionQueryService(WORKSPACE, repository=repository)
alpha_query = PortiaAttentionQuery(
    scope=PortiaAttentionScope.work_scope(alpha),
    as_of=AS_OF,
)
alpha_report = service.query(alpha_query)
support_report = service.query(
    PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(support_ref()),
        as_of=AS_OF,
    )
)
beta_report = service.query(
    PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref("evt_smoke_beta")),
        as_of=AS_OF,
    )
)
gamma_report = service.query(
    PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref("evt_smoke_gamma")),
        as_of=AS_OF,
    )
)
class_report = service.query(
    PortiaAttentionQuery(
        scope=PortiaAttentionScope.class_scope(CLASS_ID),
        as_of=AS_OF,
    )
)
workspace_query = PortiaAttentionQuery(
    scope=PortiaAttentionScope.workspace_scope(),
    as_of=AS_OF,
)
workspace_first = service.query(workspace_query)
workspace_second = service.query(workspace_query)

after = snapshot(WORKSPACE)

def codes(report):
    return [item.code for item in report.items]

def key(report):
    return [
        (
            item.code,
            item.attention_class,
            item.reason_codes,
            repr(item.source_ref),
            repr(item.context),
        )
        for item in report.items
    ]

privacy_text = repr(
    (
        alpha_report,
        support_report,
        beta_report,
        gamma_report,
        class_report,
        workspace_first,
    )
)

payload = {
    "schedule": schedule_state,
    "alpha_codes": codes(alpha_report),
    "support_codes": codes(support_report),
    "beta_codes": codes(beta_report),
    "gamma_codes": codes(gamma_report),
    "class_has_due": "portia_follow_up_due" in codes(class_report),
    "workspace_has_recovery": (
        "portia_recovery_required" in codes(workspace_first)
    ),
    "workspace_partial": any(
        notice.code == "portia_attention_partial"
        for notice in workspace_first.notices
    ),
    "deterministic": key(workspace_first) == key(workspace_second),
    "privacy_minimal": (
        "Private Synthetic Student" not in privacy_text
        and "student_1" not in privacy_text
    ),
    "workspace_unchanged": before == after,
}
print(json.dumps(payload, sort_keys=True))
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue49-wheel-smoke-") as temp:
        root = Path(temp)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(portia_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        package = _run(
            [
                str(python),
                "-c",
                "import json,portia; "
                "print(json.dumps({'path': portia.__path__[0]}))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(
                "smoke import resolved into source checkout: "
                f"{installed}"
            )

        for relative in (
            "attention/__init__.py",
            "attention/models.py",
            "attention/taxonomy.py",
            "attention/timing.py",
            "attention/workflow_sources.py",
            "attention/operational_sources.py",
            "attention/derived_sources.py",
            "attention/scope.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #49 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected_schedule = {
            "fup_smoke_due": "due",
            "fup_smoke_future": "scheduled",
            "fup_smoke_overdue": "overdue",
        }
        if payload["schedule"] != expected_schedule:
            raise RuntimeError(
                f"unexpected Follow-Up schedule result: {payload!r}"
            )
        alpha_codes = set(payload["alpha_codes"])
        if not {
            "portia_follow_up_due",
            "portia_follow_up_overdue",
            "portia_review_incomplete",
            "portia_integrity_conflict",
        }.issubset(alpha_codes):
            raise RuntimeError(
                f"installed alpha attention is incomplete: {payload!r}"
            )
        if "portia_integrity_review_required" in alpha_codes:
            raise RuntimeError(
                f"effective presentation suppression was ignored: {payload!r}"
            )
        if not {
            "portia_support_process_review_due",
            "portia_support_process_dependency_attention",
        }.issubset(set(payload["support_codes"])):
            raise RuntimeError(
                f"Support Process attention is incomplete: {payload!r}"
            )
        if "portia_derived_state_stale" not in payload["beta_codes"]:
            raise RuntimeError(f"stale derived state was not surfaced: {payload!r}")
        if "portia_quarantine_active" not in payload["gamma_codes"]:
            raise RuntimeError(f"active Quarantine was not surfaced: {payload!r}")
        for truthy in (
            "class_has_due",
            "workspace_has_recovery",
            "workspace_partial",
            "deterministic",
            "privacy_minimal",
            "workspace_unchanged",
        ):
            if payload[truthy] is not True:
                raise RuntimeError(
                    f"installed Issue #49 smoke failed {truthy}: {payload!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print("Portia installed-wheel Issue #49 attention smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
