"""Install Core and Portia wheels in isolation and smoke the Issue #40 baseline."""

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


def _console_path(python: Path) -> Path:
    code = "import json,sysconfig; print(json.dumps(sysconfig.get_path('scripts')))"
    result = subprocess.run(
        [str(python), "-c", code],
        text=True,
        capture_output=True,
        check=True,
    )
    scripts = Path(json.loads(result.stdout))
    return scripts / ("portia.exe" if os.name == "nt" else "portia")


def _model_smoke(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    code = r"""
import json
from portia.models import (
    EventV2,
    OwnershipCorrectionV1,
    OwnershipCorrectionV2,
    parse_portia_record,
    portia_record_to_dict,
)
from portia.models.schema_runtime import load_runtime_contract_bundle
from portia.validation import GraphValidationOptions, validate_record_graph

wire = {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_smoke",
    "work_id": "evt_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-25T12:00:00-04:00",
    "created_by": {"type": "system_process", "process_id": "wheel_smoke"},
    "updated_at": "2026-08-25T12:00:00-04:00",
    "updated_by": {"type": "system_process", "process_id": "wheel_smoke"},
}
record = parse_portia_record("event", "2", wire)
assert isinstance(record, EventV2)
assert portia_record_to_dict(record) == wire
assert validate_record_graph(
    [record], options=GraphValidationOptions(require_internal_resolution=True)
) == ()
try:
    record._data["status"] = "closed"
except TypeError:
    pass
else:
    raise AssertionError("runtime record payload is not deeply immutable")

def endpoint(work_kind, class_id, work_id, record_id):
    return {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": {
                "module_id": "portia",
                "class_id": class_id,
                "work_id": work_id,
                "work_kind": work_kind,
                "contract_version": "2" if work_kind == "event" else "1",
            },
            "record_ref": {
                "record_kind": "follow_up",
                "record_id": record_id,
                "contract_version": "1",
            },
        },
        "observed_updated_at": "2026-09-18T12:00:00-04:00",
    }

common = {
    "record_type": "ownership_correction",
    "module_id": "portia",
    "class_id": "class_smoke",
    "correction_kind": "child_work_root",
    "effective_at": "2026-09-18T12:00:00-04:00",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-18T12:01:00-04:00",
    "created_by": {"type": "system_process", "process_id": "wheel_smoke"},
}
v1_wire = {
    **common,
    "schema_version": "1",
    "work_id": "evt_destination",
    "correction_id": "owc_smoke_v1",
    "source": endpoint("event", "class_smoke", "evt_source", "fup_source"),
    "destination": endpoint(
        "event", "class_smoke", "evt_destination", "fup_destination"
    ),
    "reason": {"code": "wrong_event_root"},
}
v2_wire = {
    **common,
    "schema_version": "2",
    "work_id": "sup_destination",
    "work_kind": "support_process",
    "correction_id": "owc_smoke_v2",
    "source": endpoint("event", "class_smoke", "evt_source", "fup_source"),
    "destination": endpoint(
        "support_process", "class_smoke", "sup_destination", "fup_destination"
    ),
    "reason": {"code": "wrong_work_root"},
}
v1 = parse_portia_record("ownership_correction", "1", v1_wire)
v2 = parse_portia_record("ownership_correction", "2", v2_wire)
assert isinstance(v1, OwnershipCorrectionV1)
assert isinstance(v2, OwnershipCorrectionV2)
bundle = load_runtime_contract_bundle()
assert "2" in bundle.contracts["ownership_correction"]
print(json.dumps({
    "contract": record.contract,
    "version": record.contract_version,
    "ownership_versions": [v1.contract_version, v2.contract_version],
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload != {
        "contract": "event",
        "version": "2",
        "ownership_versions": ["1", "2"],
    }:
        raise RuntimeError(f"unexpected runtime-model smoke result: {payload!r}")


def _operation_journal_v3_smoke(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    repository = Path(__file__).resolve().parents[1]
    fixture = json.loads(
        (
            repository
            / "tests"
            / "schema_validation"
            / "fixtures"
            / "issue-47"
            / "operation-journal-v3"
            / "valid"
            / "v3-removal-pending.json"
        ).read_text(encoding="utf-8")
    )
    code = f"""
import json
from portia.models import OperationJournalV3, parse_portia_record
from portia.storage.operation_journal import absence_steps

wire = json.loads({json.dumps(json.dumps(fixture))})
record = parse_portia_record("operation_journal", "3", wire)
assert isinstance(record, OperationJournalV3)
step = absence_steps(record)[0]
assert step.prior_contract_version == "3"
assert step.removal_ref["removal_id"] == "rmv_issue47_v3"
assert step.observed_absent is False
print(json.dumps({{"contract": record.contract, "version": record.contract_version}}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload != {"contract": "operation_journal", "version": "3"}:
        raise RuntimeError(f"unexpected operation_journal@3 smoke result: {payload!r}")


def _storage_smoke(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    code = r"""
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaConflictError, PortiaRepository

workspace = ensure_workspace_root(Path("synthetic-workspace-storage"))
repository = PortiaRepository(workspace)
work = ExactPortiaWorkRef(
    class_id="class_storage_smoke",
    work_id="evt_storage_smoke",
    work_kind="event",
    contract_version="2",
)
base = {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_storage_smoke",
    "work_id": "evt_storage_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-26T12:00:00-04:00",
    "created_by": {"type": "system_process", "process_id": "wheel_storage_smoke"},
    "updated_at": "2026-08-26T12:00:00-04:00",
    "updated_by": {"type": "system_process", "process_id": "wheel_storage_smoke"},
}
created_record = parse_portia_record("event", "2", base)
created = repository.create_work(work, created_record)
loaded = repository.load_work(work)
assert loaded.record.to_dict() == base
assert loaded.fingerprint == created.fingerprint

updated_wire = dict(base)
updated_wire["updated_at"] = "2026-08-26T12:05:00-04:00"
updated_record = parse_portia_record("event", "2", updated_wire)
replaced = repository.replace_work(work, updated_record, expected=created.fingerprint)
assert repository.load_work(work).record.to_dict() == updated_wire
assert replaced.fingerprint != created.fingerprint

try:
    repository.replace_work(work, updated_record, expected=created.fingerprint)
except PortiaConflictError:
    conflict = "rejected"
else:
    raise AssertionError("stale expected-state replacement was not rejected")

print(json.dumps({
    "created": created.fingerprint.digest,
    "replaced": replaced.fingerprint.digest,
    "stale_conflict": conflict,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload.get("stale_conflict") != "rejected":
        raise RuntimeError(f"unexpected storage smoke result: {payload!r}")
    if payload.get("created") == payload.get("replaced"):
        raise RuntimeError(
            "storage replacement did not change the representation fingerprint"
        )


def _identity_smoke(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    code = r"""
import json
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root
from portia.identity import (
    ActorDirectoryService,
    CoreRosterResolver,
    ResolvedIdentityValidationContext,
)
from portia.models import parse_portia_record
from portia.models.references import ExactActorStudentRelationshipRef

workspace = ensure_workspace_root(Path("synthetic-workspace-identity"))
roster = create_roster(
    "class_identity_smoke",
    [{
        "student_id": "student_17",
        "last_name": "Example",
        "first_name": "Student",
        "period": "2",
        "preferred_name": "Sam",
    }],
)
write_class_roster(workspace, roster)
resolver = CoreRosterResolver(workspace)
resolved = resolver.resolve("class_identity_smoke", "student_17")
assert resolved.reference.class_id == "class_identity_smoke"
assert resolved.reference.student_id == "student_17"
assert not (workspace / "portia").exists(), "roster lookup created Portia canonical state"
context = ResolvedIdentityValidationContext.from_resolutions(resolved)
assert context.roster_student_exists(resolved.reference) is True

agent = {"type": "system_process", "process_id": "wheel_identity_smoke"}
actor_wire = {
    "schema_version": "1",
    "record_type": "actor",
    "module_id": "portia",
    "actor_id": "actr_identity_smoke",
    "status": "active",
    "display": {"display_name": "Synthetic Caregiver"},
    "actor_category": {"kind": "family_or_caregiver"},
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-26T12:00:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-26T12:00:00-04:00",
    "updated_by": agent,
}
relationship_wire = {
    "schema_version": "1",
    "record_type": "actor_student_relationship",
    "module_id": "portia",
    "actor_id": "actr_identity_smoke",
    "relationship_id": "asrel_identity_smoke",
    "status": "active",
    "student_ref": {
        "class_id": "class_identity_smoke",
        "student_id": "student_17",
    },
    "relationship": {"type": "caregiver"},
    "basis": {"kind": "local_operator_knowledge"},
    "review": {
        "kind": "locally_reviewed",
        "reviewed_at": "2026-08-26T12:00:00-04:00",
        "reviewed_by": agent,
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-26T12:00:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-26T12:00:00-04:00",
    "updated_by": agent,
}
service = ActorDirectoryService(workspace)
service.create_actor(parse_portia_record("actor", "1", actor_wire))
service.create_actor_child(
    "actr_identity_smoke",
    parse_portia_record("actor_student_relationship", "1", relationship_wire),
)
relationship_ref = ExactActorStudentRelationshipRef(
    actor_id="actr_identity_smoke",
    relationship_id="asrel_identity_smoke",
    contract_version="1",
)
linked = service.resolve_student_relationship(
    relationship_ref,
    require_current_use=True,
)
assert linked.roster_student.reference == resolved.reference
assert linked.relationship.record.logical_id == "asrel_identity_smoke"
print(json.dumps({
    "class_id": linked.roster_student.reference.class_id,
    "student_id": linked.roster_student.reference.student_id,
    "relationship_id": linked.relationship.record.logical_id,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    expected = {
        "class_id": "class_identity_smoke",
        "student_id": "student_17",
        "relationship_id": "asrel_identity_smoke",
    }
    if payload != expected:
        raise RuntimeError(f"unexpected identity smoke result: {payload!r}")


def _workflow_smoke(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    code = r"""
import json
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root
from portia.identity import ActorDirectoryService
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    RoleWorkflowService,
    WorkRelationshipService,
    participant_reference,
    relationship_reference,
    role_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-workflows"))
write_class_roster(workspace, create_roster("class_workflow_smoke", [{
    "student_id": "student_17",
    "last_name": "Example",
    "first_name": "Student",
    "period": "2",
}]))
agent = {"type": "system_process", "process_id": "wheel_workflow_smoke"}
timestamp = "2026-08-26T12:00:00-04:00"

def event(event_id, *, status="draft", updated_at=timestamp):
    return parse_portia_record("event", "2", {
        "schema_version": "2",
        "record_type": "portia_work",
        "work_kind": "event",
        "module_id": "portia",
        "class_id": "class_workflow_smoke",
        "work_id": event_id,
        "school_year": "2026-2027",
        "status": status,
        "occurrence": {"precision": "exact", "started_at": timestamp},
        "summary": "Synthetic neutral workflow smoke context.",
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": agent,
        "updated_at": updated_at,
        "updated_by": agent,
    })

event_service = EventWorkflowService(workspace)
source_event = event("evt_workflow_smoke")
target_event = event("evt_workflow_context")
source_created = event_service.create(source_event)
target_created = event_service.create(target_event)
source_ref = ExactPortiaWorkRef(
    class_id="class_workflow_smoke",
    work_id="evt_workflow_smoke",
    work_kind="event",
    contract_version="2",
)
target_ref = ExactPortiaWorkRef(
    class_id="class_workflow_smoke",
    work_id="evt_workflow_context",
    work_kind="event",
    contract_version="2",
)

roster_participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_workflow_smoke",
    "work_id": "evt_workflow_smoke",
    "participant_id": "ep_roster_smoke",
    "status": "active",
    "subject": {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": "class_workflow_smoke",
            "student_id": "student_17",
        },
        "display_snapshot": {"display_name": "Synthetic Student"},
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
participants = ParticipantWorkflowService(workspace)
participants.create(source_ref, roster_participant)

target_participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_workflow_smoke",
    "work_id": "evt_workflow_context",
    "participant_id": "ep_context_smoke",
    "status": "active",
    "subject": {"kind": "unknown_person", "reason": "identity_not_known"},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
participants.create(target_ref, target_participant)

actor = parse_portia_record("actor", "1", {
    "schema_version": "1",
    "record_type": "actor",
    "module_id": "portia",
    "actor_id": "actr_workflow_smoke",
    "status": "active",
    "display": {"display_name": "Synthetic Visitor"},
    "actor_category": {"kind": "other", "detail": "Synthetic visitor"},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
ActorDirectoryService(workspace).create_actor(actor)
actor_participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_workflow_smoke",
    "work_id": "evt_workflow_smoke",
    "participant_id": "ep_actor_smoke",
    "status": "active",
    "subject": {
        "kind": "actor",
        "actor_ref": {"actor_id": "actr_workflow_smoke"},
        "display_snapshot": {"display_name": "Synthetic Visitor"},
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
participants.create(source_ref, actor_participant)

event_service.replace(
    event(
        "evt_workflow_smoke",
        status="active",
        updated_at="2026-08-26T12:05:00-04:00",
    ),
    expected=source_created.fingerprint,
)
event_service.replace(
    event(
        "evt_workflow_context",
        status="active",
        updated_at="2026-08-26T12:05:00-04:00",
    ),
    expected=target_created.fingerprint,
)

role = parse_portia_record("event_participant_role", "3", {
    "schema_version": "3",
    "record_type": "event_participant_role",
    "module_id": "portia",
    "class_id": "class_workflow_smoke",
    "work_id": "evt_workflow_smoke",
    "role_id": "epr_present_smoke",
    "target": {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_roster_smoke",
            "contract_version": "3",
        },
    },
    "status": "active",
    "role_type": "present",
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
roles = RoleWorkflowService(workspace)
roles.create(source_ref, role)

relationship = parse_portia_record("work_relationship", "2", {
    "schema_version": "2",
    "record_type": "work_relationship",
    "module_id": "portia",
    "class_id": "class_workflow_smoke",
    "work_id": "evt_workflow_smoke",
    "relationship_id": "rel_workflow_smoke",
    "status": "active",
    "relationship_type": "draws_context_from",
    "source": source_ref.to_dict(),
    "target": target_ref.to_dict(),
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
relationships = WorkRelationshipService(workspace)
relationships.create(relationship)

roster_resolution = participants.require_current_use(
    participant_reference(source_ref, "ep_roster_smoke")
)
actor_resolution = participants.require_current_use(
    participant_reference(source_ref, "ep_actor_smoke")
)
assert roster_resolution.authority.reference.class_id == "class_workflow_smoke"
assert roster_resolution.authority.reference.student_id == "student_17"
assert actor_resolution.authority.record.logical_id == "actr_workflow_smoke"
assert roles.resolve_exact(role_reference(source_ref, "epr_present_smoke")).record.status == "active"
exact_relationship = relationships.resolve_exact(
    relationship_reference(source_ref, "rel_workflow_smoke")
)
assert exact_relationship.target.record.logical_id == "evt_workflow_context"
assert event_service.resolve_exact(source_ref).record.logical_id == "evt_workflow_smoke"

records_root = workspace / "classes/class_workflow_smoke/modules/portia/work/evt_workflow_smoke/records"
for absent in ("account", "observation", "determination"):
    assert not (records_root / absent).exists()
actor_roots = list((workspace / "portia/actors").iterdir())
assert [path.name for path in actor_roots] == ["actr_workflow_smoke"]
print(json.dumps({
    "roster_class": roster_resolution.authority.reference.class_id,
    "actor_id": actor_resolution.authority.record.logical_id,
    "role": roles.load_exact(role_reference(source_ref, "epr_present_smoke")).record.field("role_type"),
    "relationship": exact_relationship.relationship.record.logical_id,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload != {
        "roster_class": "class_workflow_smoke",
        "actor_id": "actr_workflow_smoke",
        "role": "present",
        "relationship": "rel_workflow_smoke",
    }:
        raise RuntimeError(f"unexpected workflow smoke result: {payload!r}")


def _issue47_authority_smoke(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    code = r"""
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    AmendmentWorkflowService,
    DependencyWorkflowService,
    ExceptionalRemovalAuthority,
    ExceptionalRemovalWorkflowService,
    IntegrityWorkflowService,
    LifecycleWorkflowService,
    OwnershipCorrectionWorkflowService,
    RecordMigrationWorkflowService,
    RecoveryWorkflowService,
    StatementOfDisagreementWorkflowService,
    WorkflowPrerequisiteError,
    disagreement_reference,
)

NOW = "2026-09-20T10:00:00-04:00"
UPDATED = "2026-09-20T10:05:00-04:00"
AGENT = {"type": "system_process", "process_id": "wheel_issue47_smoke"}
workspace = ensure_workspace_root(Path("synthetic-workspace-issue47"))
repository = PortiaRepository(workspace)
work = ExactPortiaWorkRef(
    class_id="class_issue47_smoke",
    work_id="evt_issue47_smoke",
    work_kind="event",
    contract_version="2",
)
event = parse_portia_record("event", "2", {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": work.class_id,
    "work_id": work.work_id,
    "school_year": "2026-2027",
    "status": "active",
    "occurrence": {"precision": "exact", "started_at": NOW},
    "summary": "Synthetic student recieveed the handout.",
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
})
prior = repository.create_work(work, event)
amendment = AmendmentWorkflowService(workspace, repository=repository).apply_amendment(
    work,
    expected=prior.fingerprint,
    amendment_id="amd_issue47_smoke",
    changes=[{
        "path": "/summary",
        "operation": "replace",
        "before": {"present": True, "value": "Synthetic student recieveed the handout."},
        "after": {"present": True, "value": "Synthetic student received the handout."},
    }],
    reason_code="spelling_corrected",
    created_at=UPDATED,
    created_by=AGENT,
    semantic_equivalence_confirmed=True,
)

participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": work.class_id,
    "work_id": work.work_id,
    "participant_id": "ep_issue47_smoke",
    "status": "active",
    "subject": {"kind": "unknown_person", "reason": "identity_not_known"},
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
})
repository.create_work_record(work, participant)
participant_ref = ExactPortiaWorkRecordRef(
    work_ref=work,
    record_ref=ExactLocalRecordRef(
        record_kind="event_participant",
        record_id="ep_issue47_smoke",
        contract_version="3",
    ),
)

disagreement = parse_portia_record("statement_of_disagreement", "1", {
    "schema_version": "1",
    "record_type": "statement_of_disagreement",
    "module_id": "portia",
    "class_id": work.class_id,
    "work_id": work.work_id,
    "disagreement_id": "sod_issue47_smoke",
    "status": "proposed",
    "target": {"kind": "local_record", "record_ref": participant_ref.record_ref.to_dict()},
    "source": {"kind": "local_operator", "display_label": "Synthetic teacher"},
    "positions": ["disputes_accuracy"],
    "statement": {"representation": "recorded_summary", "text": "Synthetic bounded disagreement."},
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
})
disagreements = StatementOfDisagreementWorkflowService(workspace, repository=repository)
created_disagreement = disagreements.create(work, disagreement)
active_wire = created_disagreement.record.to_dict()
active_wire.update({"status": "active", "updated_at": UPDATED, "updated_by": AGENT})
active_disagreement = parse_portia_record("statement_of_disagreement", "1", active_wire)
disagreement_ref = disagreement_reference(work, "sod_issue47_smoke")
lifecycle = LifecycleWorkflowService(workspace, repository=repository)
lifecycle.transition(
    disagreement_ref,
    active_disagreement,
    expected=created_disagreement.fingerprint,
    transition_id="lct_issue47_smoke",
    reason_code="review_confirmed",
    operation_id="op_issue47_lifecycle_smoke",
)

dependency = parse_portia_record("dependency", "1", {
    "schema_version": "1",
    "record_type": "dependency",
    "module_id": "portia",
    "class_id": work.class_id,
    "work_id": work.work_id,
    "dependency_id": "dep_issue47_smoke",
    "status": "active",
    "dependent": {"kind": "local_record", "record_ref": participant_ref.record_ref.to_dict()},
    "dependency": {"kind": "portia_work", "work_ref": work.to_dict()},
    "strength": "required",
    "applies_to": "current_use",
    "purpose": "workflow_prerequisite",
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
})
dependencies = DependencyWorkflowService(workspace, repository=repository)
dependencies.create(work, dependency)
gate = dependencies.evaluate_gate(participant_ref, gate="current_use")

integrity = IntegrityWorkflowService(workspace)
try:
    integrity.current_findings(integrity.operation_scope("op_issue47_lifecycle_smoke"))
except WorkflowPrerequisiteError:
    missing_integrity_blocked = True
else:
    raise AssertionError("missing current Integrity projection did not fail closed")

public_instances = (
    lifecycle,
    AmendmentWorkflowService(workspace, repository=repository),
    disagreements,
    dependencies,
    RecordMigrationWorkflowService(workspace, repository=repository),
    OwnershipCorrectionWorkflowService(workspace, repository=repository),
    ExceptionalRemovalWorkflowService(
        workspace,
        authority=ExceptionalRemovalAuthority(
            enabled=False,
            governance_state="unknown",
        ),
    ),
    RecoveryWorkflowService(workspace),
    integrity,
)
print(json.dumps({
    "services": [type(item).__name__ for item in public_instances],
    "amendment_steps": list(amendment.accepted_steps),
    "lifecycle_status": lifecycle.require_corrected_history_reconciled(disagreement_ref).selected_status,
    "dependency_gate": gate.required_gate_satisfied,
    "integrity_missing_blocked": missing_integrity_blocked,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    expected_services = [
        "LifecycleWorkflowService",
        "AmendmentWorkflowService",
        "StatementOfDisagreementWorkflowService",
        "DependencyWorkflowService",
        "RecordMigrationWorkflowService",
        "OwnershipCorrectionWorkflowService",
        "ExceptionalRemovalWorkflowService",
        "RecoveryWorkflowService",
        "IntegrityWorkflowService",
    ]
    if payload.get("services") != expected_services:
        raise RuntimeError(f"unexpected Issue #47 public services: {payload!r}")
    if payload.get("amendment_steps") != [
        "step_history",
        "step_amendment",
        "step_target",
    ]:
        raise RuntimeError(f"unexpected installed Amendment result: {payload!r}")
    if payload.get("lifecycle_status") != "active":
        raise RuntimeError(f"unexpected installed lifecycle result: {payload!r}")
    if payload.get("dependency_gate") is not True:
        raise RuntimeError(f"unexpected installed Dependency gate: {payload!r}")
    if payload.get("integrity_missing_blocked") is not True:
        raise RuntimeError(f"Integrity projection did not fail closed: {payload!r}")


def _exceptional_removal_smoke(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    code = r"""
import json
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaNotFoundError
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.workflows import ExceptionalRemovalAuthority, ExceptionalRemovalWorkflowService

workspace = Path("removal-workspace")
timestamp = "2026-09-18T12:00:00-04:00"
operator = {"type": "local_operator", "display_label": "Synthetic wheel operator"}
work = ExactPortiaWorkRef(
    class_id="class_removal_smoke",
    work_id="evt_removal_smoke",
    work_kind="event",
    contract_version="2",
)
record = parse_portia_record("event", "2", {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_removal_smoke",
    "work_id": "evt_removal_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "summary": "Synthetic installed-wheel removal target.",
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": operator,
    "updated_at": timestamp,
    "updated_by": operator,
})
stored = PortiaRepository(workspace).create_work(work, record)
target = {"kind": "work", "work_ref": work.to_dict()}
reason = {"category": "administrative_test_data", "code": "synthetic_smoke"}
authorization = {
    "decision_reference": "installed-wheel-removal-smoke",
    "authorized_by": operator,
}
service = ExceptionalRemovalWorkflowService(
    workspace,
    authority=ExceptionalRemovalAuthority(enabled=True, governance_state="clear"),
    entropy=lambda count: b"w" * count,
    clock=lambda: timestamp,
)
assessment = service.assess_removal(
    target=target,
    reason=reason,
    authorization=authorization,
    integrity_clearance="clear",
    synthetic_test_data_confirmed=True,
)
result = service.exceptionally_remove(
    assessment,
    reason=reason,
    authorization=authorization,
    child_dispositions={},
    effective_at=timestamp,
    synthetic_test_data_confirmed=True,
)
resolved = service.resolve_removal_state(target)
missing_work = ExactPortiaWorkRef(
    class_id="class_removal_smoke",
    work_id="evt_never_existed",
    work_kind="event",
    contract_version="2",
)
try:
    service.resolve_removal_state({"kind": "work", "work_ref": missing_work.to_dict()})
except PortiaNotFoundError:
    absent_without_certificate = "not_found"
else:
    raise AssertionError("ordinary absence was incorrectly classified as removal")
journal = OperationJournalStore(workspace).load_current(
    result.operation.revision.to_dict()["operation_id"]
)
print(json.dumps({
    "payload_absent": not stored.path.exists(),
    "certificate_present": result.certificate.path.is_file(),
    "resolution": resolved.disposition,
    "ordinary_absence": absent_without_certificate,
    "journal_version": journal.revision.contract_version,
    "operation_kind": journal.revision.to_dict()["operation_kind"],
    "target_unchanged": result.certificate.record.field("target") == target,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload != {
        "payload_absent": True,
        "certificate_present": True,
        "resolution": "exceptionally_removed",
        "ordinary_absence": "not_found",
        "journal_version": "3",
        "operation_kind": "exceptionally_remove",
        "target_unchanged": True,
    }:
        raise RuntimeError(f"unexpected Exceptional Removal smoke result: {payload!r}")


def _ownership_correction_smoke(
    python: Path,
    *,
    cwd: Path,
    env: dict[str, str],
) -> None:
    code = r"""
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaQuarantinedError
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    FollowUpWorkflowService,
    IntegrityWorkflowService,
    OwnershipCorrectionWorkflowService,
    QuarantineWorkflowService,
    RecoveryWorkflowService,
    follow_up_reference,
)

NOW = "2026-09-19T10:00:00-04:00"
UPDATED = "2026-09-19T10:05:00-04:00"
AGENT = {"type": "system_process", "process_id": "wheel_ownership_smoke"}
workspace = ensure_workspace_root(Path("synthetic-workspace-ownership"))
repository = PortiaRepository(workspace)
source = ExactPortiaWorkRef(
    class_id="class_smoke",
    work_id="evt_ownership_smoke",
    work_kind="event",
    contract_version="2",
)
destination = ExactPortiaWorkRef(
    class_id="class_smoke",
    work_id="sup_ownership_smoke",
    work_kind="support_process",
    contract_version="1",
)
repository.create_work(source, parse_portia_record("event", "2", {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": source.class_id,
    "work_id": source.work_id,
    "school_year": "2026-2027",
    "status": "active",
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
    "occurrence": {"precision": "exact", "started_at": NOW},
    "summary": "Synthetic installed ownership source.",
}))
repository.create_work_record(source, parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": source.class_id,
    "work_id": source.work_id,
    "participant_id": "ep_ownership_smoke",
    "status": "active",
    "subject": {
        "kind": "descriptive_person",
        "description_type": "outside_student",
        "display_label": "Synthetic installed student",
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
}))
repository.create_work(destination, parse_portia_record("support_process", "1", {
    "schema_version": "1",
    "record_type": "portia_work",
    "work_kind": "support_process",
    "module_id": "portia",
    "class_id": destination.class_id,
    "work_id": destination.work_id,
    "school_year": "2026-2027",
    "status": "active",
    "workflow_state": "active",
    "summary": "Synthetic installed ownership destination.",
    "initiation": {
        "kind": "teacher_identified_need",
        "detail": "Synthetic installed need.",
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
}))
for participant_id, contexts, person in (
    (
        "spp_ownership_student",
        [{"kind": "supported_person"}],
        {
            "kind": "descriptive_person",
            "description_type": "outside_student",
            "display_label": "Synthetic installed supported student",
        },
    ),
    (
        "spp_ownership_coordinator",
        [{"kind": "coordinator"}],
        {"kind": "local_operator", "display_label": "Synthetic installed teacher"},
    ),
):
    repository.create_work_record(destination, parse_portia_record(
        "support_process_participant", "1", {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": destination.class_id,
            "work_id": destination.work_id,
            "participant_id": participant_id,
            "status": "active",
            "person": person,
            "contexts": contexts,
            "creation_source": {"type": "digital_entry"},
            "created_at": NOW,
            "created_by": AGENT,
            "updated_at": NOW,
            "updated_by": AGENT,
        },
    ))

follow_up = parse_portia_record("follow_up", "1", {
    "schema_version": "1",
    "record_type": "follow_up",
    "module_id": "portia",
    "class_id": source.class_id,
    "work_kind": source.work_kind,
    "work_id": source.work_id,
    "follow_up_id": "fup_ownership_smoke",
    "status": "active",
    "target": {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": "ep_ownership_smoke",
            "contract_version": "3",
        },
    },
    "owner": {
        "kind": "represented_human",
        "person": {"kind": "local_operator", "display_label": "Synthetic installed teacher"},
    },
    "purpose": {"kind": "coordination"},
    "planned_timing": {"kind": "date_only", "date": "2026-09-20"},
    "workflow_state": "scheduled",
    "creation_source": {"type": "digital_entry"},
    "created_at": NOW,
    "created_by": AGENT,
    "updated_at": NOW,
    "updated_by": AGENT,
})
family = FollowUpWorkflowService(workspace, repository=repository)
created = family.create(source, follow_up)
predecessor = follow_up_reference(source, "fup_ownership_smoke")
wire = created.record.to_dict()
wire.update({
    "class_id": destination.class_id,
    "work_kind": destination.work_kind,
    "work_id": destination.work_id,
    "target": {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_ownership_student",
            "contract_version": "1",
        },
    },
    "owner": {
        "kind": "support_process_participant",
        "participant_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_ownership_coordinator",
            "contract_version": "1",
        },
    },
    "supersedes": [{
        "work_record_ref": predecessor.to_dict(),
        "reason": "work_root_corrected",
    }],
    "created_at": UPDATED,
    "created_by": AGENT,
    "updated_at": UPDATED,
    "updated_by": AGENT,
})
successor = parse_portia_record("follow_up", "1", wire)

class ClearIntegrity:
    def __init__(self, root):
        self.quarantine = QuarantineGuard(root)
    def require_allowed(self, target, effect):
        self.quarantine.require_allowed(target, effect)

service = OwnershipCorrectionWorkflowService(
    workspace,
    repository=repository,
    integrity_guard=ClearIntegrity(workspace),
)
assessment = service.assess_correction(
    predecessor,
    destination,
    successor,
    expected=created.fingerprint,
    effective_at=UPDATED,
)
result = service.correct_work_root(
    predecessor,
    destination,
    successor,
    expected=created.fingerprint,
    transition_id="lct_ownership_smoke",
    correction_id="owc_ownership_smoke",
    reason={"code": "wrong_work_root"},
    effective_at=UPDATED,
    created_by=AGENT,
    reference_dispositions={
        item.reference_key: "remain_exact_historical"
        for item in assessment.incoming_references
    },
    dependency_dispositions={
        item.dependency_key: "satisfied_by_destination"
        for item in assessment.dependencies
    },
    operation_id="op_ownership_smoke",
)
certificate = service.resolve_correction(result.ownership_correction)
historical = family.resolve_exact(predecessor)
journal = OperationJournalStore(workspace).load_current(result.operation_id)
recovery = RecoveryWorkflowService(workspace).assess(result.operation_id)
quarantine = QuarantineWorkflowService(workspace).apply_quarantine(
    target={"kind": "work_record", "work_record_ref": predecessor.to_dict()},
    reason="partial_commit",
    reason_detail="Synthetic installed guard proof.",
    effects=["block_current_use", "review_required"],
    applying_operation={
        "operation_id": result.operation_id,
        "journal_revision": journal.revision.to_dict()["journal_revision"],
        "contract_version": "2",
    },
    supporting_finding_keys=[],
    applied_at=UPDATED,
    applied_by=AGENT,
    release_requirements=["canonical_state_reconciled"],
    quarantine_id="qnt_0123456789abcdef0123456789abcdee",
)
try:
    IntegrityWorkflowService(workspace).quarantine.require_allowed(
        {"kind": "work_record", "work_record_ref": predecessor.to_dict()},
        "block_current_use",
    )
except PortiaQuarantinedError:
    quarantine_blocked = True
else:
    raise AssertionError("installed Quarantine did not block current use")
print(json.dumps({
    "service": type(service).__name__,
    "certificate_version": certificate.record.contract_version,
    "destination_status": repository.load_work_record(
        destination, "follow_up", "1", "fup_ownership_smoke"
    ).record.status,
    "historical_status": historical.record.status,
    "journal_version": journal.revision.contract_version,
    "journal_state": journal.revision.to_dict()["state"],
    "recovery_disposition": recovery.disposition,
    "quarantine_state": quarantine.revision.to_dict()["state"],
    "quarantine_blocked": quarantine_blocked,
}))
"""
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    expected = {
        "service": "OwnershipCorrectionWorkflowService",
        "certificate_version": "2",
        "destination_status": "active",
        "historical_status": "superseded",
        "journal_version": "2",
        "journal_state": "completed",
        "recovery_disposition": "terminal_consistent",
        "quarantine_state": "active",
        "quarantine_blocked": True,
    }
    if payload != expected:
        raise RuntimeError(f"unexpected Ownership Correction smoke result: {payload!r}")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    if "0.6.3" not in core_wheel.name:
        raise RuntimeError("Issue #40 installed-wheel smoke requires Core 0.6.3")
    with tempfile.TemporaryDirectory(prefix="portia-wheel-smoke-") as temporary:
        root = Path(temporary)
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

        package_result = _run(
            [
                str(python),
                "-c",
                (
                    "import json,portia; "
                    "print(json.dumps({'path': portia.__path__[0], 'version': portia.__version__}))"
                ),
            ],
            cwd=work,
            env=env,
        )
        package_info = json.loads(package_result.stdout)
        installed_path = Path(package_info["path"]).resolve()
        if repository.resolve() in installed_path.parents:
            raise RuntimeError(
                f"smoke import resolved into source checkout: {installed_path}"
            )
        if package_info["version"] != "0.2.0":
            raise RuntimeError(
                f"unexpected installed Portia version: {package_info['version']}"
            )
        if not (installed_path / "py.typed").is_file():
            raise RuntimeError("installed Portia wheel is missing py.typed")
        if not (installed_path / "_runtime_contract_bundle.json").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing the runtime contract bundle"
            )
        if not (installed_path / "storage" / "repository.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing the Issue #38 storage package"
            )
        if not (installed_path / "storage" / "actor_directory.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing Actor Directory storage inventory"
            )
        if not (installed_path / "identity" / "roster.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing the Issue #39 identity package"
            )
        if not (installed_path / "workflows" / "events.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing the Issue #40 workflow package"
            )
        if not (installed_path / "storage" / "canonical_removal.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing canonical removal storage"
            )
        if not (installed_path / "workflows" / "exceptional_removal.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing Exceptional Removal workflow"
            )
        if not (installed_path / "workflows" / "ownership_correction.py").is_file():
            raise RuntimeError(
                "installed Portia wheel is missing Ownership Correction workflow"
            )
        if (installed_path / "schemas").exists():
            raise RuntimeError(
                "installed Portia wheel unexpectedly contains repository schemas"
            )

        _model_smoke(python, cwd=work, env=env)
        _operation_journal_v3_smoke(python, cwd=work, env=env)
        _storage_smoke(python, cwd=work, env=env)
        _identity_smoke(python, cwd=work, env=env)
        _workflow_smoke(python, cwd=work, env=env)
        _issue47_authority_smoke(python, cwd=work, env=env)
        _exceptional_removal_smoke(python, cwd=work, env=env)
        _ownership_correction_smoke(python, cwd=work, env=env)

        before = sorted(path.relative_to(work).as_posix() for path in work.rglob("*"))
        console = _console_path(python)
        _run([str(console), "--help"], cwd=work, env=env)
        version = _run([str(console), "--version"], cwd=work, env=env)
        if "Portia 0.2.0" not in version.stdout:
            raise RuntimeError(f"unexpected --version output: {version.stdout!r}")
        status = _run([str(console), "status"], cwd=work, env=env)
        if "Core requirement: pds-core>=0.6.3,<0.7" not in status.stdout:
            raise RuntimeError("status output is missing the Core 0.6.3 requirement")
        if "Teacher data access: none" not in status.stdout:
            raise RuntimeError(
                "status output does not preserve the non-mutating bootstrap boundary"
            )
        menu = _run([str(console), "menu"], cwd=work, env=env)
        if "bootstrap only" not in menu.stdout:
            raise RuntimeError("menu output does not identify the bootstrap-only state")
        _run([str(python), "-m", "portia", "--version"], cwd=work, env=env)
        after = sorted(path.relative_to(work).as_posix() for path in work.rglob("*"))
        if after != before:
            raise RuntimeError(
                "Portia bootstrap CLI mutated its working directory during smoke test"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #47 smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
