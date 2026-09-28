"""Application validation for deliberate-export coordinated operations.

Issue #88 keeps this layer pure: it validates exact journal, lock, candidate,
and committed-reference semantics without acquiring locks or publishing bytes.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any, Final, cast

from portia.models import PortiaRecord
from portia.storage.errors import PortiaCorruptionError
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.locks import derive_lock_id

DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION: Final[str] = (
    "portia_deliberate_export_artifact_v1"
)
_COMMITTED_REVISION_FACT: Final[str] = "committed_journal_revision"
_EXPORT_ROLE_ARTIFACT: Final[str] = "deliberate_export_artifact"
_EXPORT_ROLE_PROVENANCE: Final[str] = "deliberate_export_provenance"
_ARTIFACT_SUFFIX = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
_PROGRESS_RANK: Final[dict[str, int]] = {
    "pending": 0,
    "staged": 1,
    "durable": 2,
    "verified": 3,
    "accepted": 4,
}


def _data(
    value: PortiaRecord | Mapping[str, Any],
    *,
    contract: str | None = None,
    version: str | None = None,
) -> Mapping[str, Any]:
    if isinstance(value, PortiaRecord):
        if contract is not None and value.contract != contract:
            raise PortiaCorruptionError(
                f"expected {contract} record, got {value.contract}"
            )
        if version is not None and value.contract_version != version:
            raise PortiaCorruptionError(
                f"expected {contract}@{version}, got "
                f"{value.contract}@{value.contract_version}"
            )
        return cast(Mapping[str, Any], value.to_dict())
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("application validation requires an object")
    return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError(f"{label} must be an object")
    return cast(Mapping[str, Any], value)


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PortiaCorruptionError(f"{label} must be an array")
    return value


def _fingerprint(value: object, label: str) -> ContentFingerprint:
    try:
        return ContentFingerprint.from_dict(value)
    except ValueError as exc:
        raise PortiaCorruptionError(f"{label} lacks an exact fingerprint") from exc


def _export_identity(target: object, label: str) -> str:
    mapping = _mapping(target, label)
    if mapping.get("kind") != "deliberate_export":
        raise PortiaCorruptionError(f"{label} is not a deliberate-export target")
    ref = _mapping(mapping.get("export_ref"), f"{label}.export_ref")
    export_id = ref.get("export_id")
    if not isinstance(export_id, str) or not export_id.startswith("pexp_"):
        raise PortiaCorruptionError(f"{label} lacks an exact pexp_ identity")
    if ref.get("contract_version") != "1":
        raise PortiaCorruptionError(
            f"{label} must identify deliberate_export@1 exactly"
        )
    if set(mapping) != {"kind", "export_ref"} or set(ref) != {
        "export_id",
        "contract_version",
    }:
        raise PortiaCorruptionError(
            f"{label} contains semantic material beyond exact export identity"
        )
    return export_id


def _export_root(export_id: str) -> PurePosixPath:
    return PurePosixPath("portia", "exports", export_id)


def _artifact_path(value: object, export_id: str) -> str:
    if not isinstance(value, str):
        raise PortiaCorruptionError("export artifact destination must be a path")
    path = PurePosixPath(value)
    expected_root = _export_root(export_id)
    if path.parent != expected_root or not path.name.startswith("artifact."):
        raise PortiaCorruptionError(
            "deliberate-export artifact must be directly beneath its exact "
            "pexp_ root as artifact.<format>"
        )
    suffix = path.name[len("artifact.") :]
    if _ARTIFACT_SUFFIX.fullmatch(suffix) is None or ".." in suffix:
        raise PortiaCorruptionError(
            "deliberate-export artifact filename is not privacy-safe"
        )
    return value


def _provenance_path(export_id: str) -> str:
    return (_export_root(export_id) / "export.json").as_posix()


def _write_step(
    raw: object,
    *,
    index: int,
    primary_target: Mapping[str, Any],
    export_id: str,
    role: str,
) -> tuple[Mapping[str, Any], ContentFingerprint, int | None]:
    step = _mapping(raw, f"export write step {index}")
    if step.get("sequence") != index:
        raise PortiaCorruptionError(
            "deliberate-export writes must be contiguous artifact then provenance"
        )
    if step.get("phase") != "canonical_gate":
        raise PortiaCorruptionError(
            "deliberate-export final representations must be canonical-gate writes"
        )
    if step.get("action") != "exclusive_create":
        raise PortiaCorruptionError(
            "deliberate-export final representations require exclusive_create"
        )
    if step.get("target") != primary_target:
        raise PortiaCorruptionError(
            "deliberate-export write target differs from the exact primary export"
        )
    if step.get("representation_role") != role:
        raise PortiaCorruptionError(
            "deliberate-export write roles must be artifact then provenance"
        )
    if step.get("precondition") != {"presence": "must_be_absent"}:
        raise PortiaCorruptionError(
            "deliberate-export final writes require exact absence preconditions"
        )
    if step.get("compensation_step_id") is not None:
        raise PortiaCorruptionError(
            "accepted deliberate-export bytes must not have a delete/rollback "
            "compensation step"
        )
    if step.get("reason_code") is not None:
        raise PortiaCorruptionError(
            "ordinary deliberate-export final writes must not carry semantic "
            "reason labels"
        )

    intended = _mapping(
        step.get("intended_result"),
        f"deliberate-export {role} intended_result",
    )
    if intended.get("kind") != "present":
        raise PortiaCorruptionError(
            "deliberate-export final writes must plan exact present bytes"
        )
    expected_contract = (
        DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION
        if role == _EXPORT_ROLE_ARTIFACT
        else "1"
    )
    if intended.get("contract_version") != expected_contract:
        raise PortiaCorruptionError(
            f"{role} uses the wrong representation contract version"
        )
    intended_fp = _fingerprint(
        intended.get("fingerprint"),
        f"deliberate-export {role}",
    )

    selected_state = _list(
        intended.get("selected_state"),
        f"deliberate-export {role} selected_state",
    )
    planned_revision: int | None = None
    if role == _EXPORT_ROLE_ARTIFACT:
        if selected_state:
            raise PortiaCorruptionError(
                "export artifact selected_state must not carry semantic payload"
            )
        _artifact_path(step.get("destination_path"), export_id)
    else:
        if len(selected_state) != 1:
            raise PortiaCorruptionError(
                "export provenance must reserve exactly one committed journal revision"
            )
        fact = _mapping(selected_state[0], "committed journal revision fact")
        if (
            fact.get("name") != _COMMITTED_REVISION_FACT
            or fact.get("kind") != "integer"
        ):
            raise PortiaCorruptionError(
                "export provenance must reserve committed_journal_revision"
            )
        value = fact.get("value")
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise PortiaCorruptionError(
                "reserved committed journal revision must be a positive integer"
            )
        planned_revision = value
        if step.get("destination_path") != _provenance_path(export_id):
            raise PortiaCorruptionError(
                "deliberate-export provenance destination must be exact export.json"
            )

    disposition = step.get("disposition")
    if disposition == "compensated":
        raise PortiaCorruptionError(
            "deliberate-export final custody cannot be represented as compensated"
        )

    observed_raw = step.get("observed_result")
    if disposition in {"durable", "verified", "accepted"} and observed_raw is None:
        raise PortiaCorruptionError(
            f"durable deliberate-export step lacks exact readback: {role}"
        )
    if observed_raw is not None:
        observed = _mapping(
            observed_raw,
            f"deliberate-export {role} observed_result",
        )
        if (
            observed.get("kind") != "present"
            or observed.get("workspace_relative_path")
            != step.get("destination_path")
            or _fingerprint(
                observed.get("fingerprint"),
                f"deliberate-export {role} readback",
            )
            != intended_fp
        ):
            raise PortiaCorruptionError(
                f"deliberate-export {role} readback disagrees with intended bytes"
            )
    return step, intended_fp, planned_revision


def _validate_export_preflight(
    data: Mapping[str, Any],
    *,
    primary_target: Mapping[str, Any],
    export_id: str,
    artifact_step: Mapping[str, Any],
    provenance_step: Mapping[str, Any],
) -> None:
    entries = _list(data.get("preflight_snapshot"), "preflight_snapshot")
    export_entries: list[Mapping[str, Any]] = []
    for raw in entries:
        entry = _mapping(raw, "preflight entry")
        target = entry.get("target")
        if isinstance(target, Mapping) and target.get("kind") == "deliberate_export":
            if target != primary_target:
                raise PortiaCorruptionError(
                    "preflight names a contradictory deliberate-export identity"
                )
            export_entries.append(entry)

    if len(export_entries) != 2:
        raise PortiaCorruptionError(
            "deliberate-export preflight must contain exactly artifact and "
            "provenance absence checks"
        )

    expected = {
        _EXPORT_ROLE_ARTIFACT: (
            artifact_step.get("destination_path"),
            DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
        ),
        _EXPORT_ROLE_PROVENANCE: (
            provenance_step.get("destination_path"),
            "1",
        ),
    }
    seen: set[str] = set()
    for entry in export_entries:
        role = entry.get("representation_role")
        if not isinstance(role, str) or role not in expected or role in seen:
            raise PortiaCorruptionError(
                "deliberate-export preflight roles must be exact and unique"
            )
        seen.add(role)
        path, contract_version = expected[role]
        if (
            entry.get("workspace_relative_path") != path
            or entry.get("contract_version") != contract_version
            or entry.get("expected_state") != {"presence": "must_be_absent"}
            or entry.get("selected_state") != []
        ):
            raise PortiaCorruptionError(
                f"deliberate-export preflight disagrees with {role} write intent"
            )
    if seen != set(expected):
        raise PortiaCorruptionError(
            "deliberate-export preflight omits one final representation"
        )

    _artifact_path(artifact_step.get("destination_path"), export_id)


def _validate_export_lock_plan(
    data: Mapping[str, Any],
    *,
    primary_target: Mapping[str, Any],
) -> None:
    raw_locks = _list(data.get("lock_set"), "lock_set")
    if len(raw_locks) != 1:
        raise PortiaCorruptionError(
            "one deliberate-export operation requires exactly one exact export lock"
        )
    entry = _mapping(raw_locks[0], "deliberate-export lock entry")
    if (
        entry.get("sequence") != 1
        or entry.get("lock_scope") != "deliberate_export"
        or entry.get("protected_target") != primary_target
    ):
        raise PortiaCorruptionError(
            "deliberate-export journal lock does not equal its exact export target"
        )
    expected_id = derive_lock_id("deliberate_export", primary_target)
    if entry.get("lock_id") != expected_id:
        raise PortiaCorruptionError(
            "deliberate-export journal lock_id is not canonical"
        )
    if entry.get("lock_path") != f"portia/locks/{expected_id}.json":
        raise PortiaCorruptionError(
            "deliberate-export journal lock path is not canonical"
        )


def planned_deliberate_export_commit_revision(
    journal: PortiaRecord | Mapping[str, Any],
) -> int:
    """Return the exact revision reserved for the first committed snapshot."""
    data = _data(journal, contract="operation_journal", version="4")
    steps = _list(data.get("write_set"), "write_set")
    if len(steps) != 2:
        raise PortiaCorruptionError(
            "deliberate-export write family must contain exactly two steps"
        )
    provenance = _mapping(steps[1], "export provenance write")
    intended = _mapping(provenance.get("intended_result"), "provenance intended_result")
    selected = _list(intended.get("selected_state"), "provenance selected_state")
    if len(selected) != 1:
        raise PortiaCorruptionError(
            "export provenance does not reserve one committed revision"
        )
    fact = _mapping(selected[0], "committed journal revision fact")
    value = fact.get("value")
    if (
        fact.get("name") != _COMMITTED_REVISION_FACT
        or fact.get("kind") != "integer"
        or not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise PortiaCorruptionError(
            "export provenance committed revision reservation is invalid"
        )
    return value


def validate_deliberate_export_journal(
    journal: PortiaRecord | Mapping[str, Any],
) -> None:
    """Validate Issue #88 invariants for one immutable journal v4 revision."""
    data = _data(journal, contract="operation_journal", version="4")
    if data.get("schema_version") != "4":
        raise PortiaCorruptionError(
            "deliberate-export coordinated operation requires operation_journal@4"
        )
    if data.get("operation_kind") != "generate_deliberate_export":
        raise PortiaCorruptionError(
            "operation_journal@4 is reserved for generate_deliberate_export"
        )
    if data.get("scope") != "workspace":
        raise PortiaCorruptionError(
            "deliberate-export operation scope must be workspace"
        )

    primary_target = _mapping(data.get("primary_target"), "primary_target")
    export_id = _export_identity(primary_target, "primary_target")
    if data.get("affected_targets") != []:
        raise PortiaCorruptionError(
            "deliberate-export operation must not substitute source/recipient "
            "targets for its exact primary identity"
        )
    if data.get("intent_facts") != []:
        raise PortiaCorruptionError(
            "deliberate-export intent_facts must stay privacy-minimized; "
            "content and person semantics belong outside operation state"
        )

    raw_steps = _list(data.get("write_set"), "write_set")
    if len(raw_steps) != 2:
        raise PortiaCorruptionError(
            "deliberate-export write family must contain exactly artifact and provenance"
        )
    artifact_step, _artifact_fp, _ = _write_step(
        raw_steps[0],
        index=1,
        primary_target=primary_target,
        export_id=export_id,
        role=_EXPORT_ROLE_ARTIFACT,
    )
    provenance_step, _provenance_fp, planned_revision = _write_step(
        raw_steps[1],
        index=2,
        primary_target=primary_target,
        export_id=export_id,
        role=_EXPORT_ROLE_PROVENANCE,
    )
    assert planned_revision is not None

    artifact_disposition = artifact_step.get("disposition")
    provenance_disposition = provenance_step.get("disposition")
    if (
        isinstance(artifact_disposition, str)
        and isinstance(provenance_disposition, str)
        and artifact_disposition in _PROGRESS_RANK
        and provenance_disposition in _PROGRESS_RANK
        and _PROGRESS_RANK[provenance_disposition]
        > _PROGRESS_RANK[artifact_disposition]
    ):
        raise PortiaCorruptionError(
            "deliberate-export provenance cannot outrun artifact acceptance"
        )

    _validate_export_preflight(
        data,
        primary_target=primary_target,
        export_id=export_id,
        artifact_step=artifact_step,
        provenance_step=provenance_step,
    )
    _validate_export_lock_plan(data, primary_target=primary_target)

    if data.get("compensation_plan") != []:
        raise PortiaCorruptionError(
            "deliberate-export final custody does not use generic compensation"
        )
    recovery = set(
        item
        for item in _list(data.get("recovery_plan"), "recovery_plan")
        if isinstance(item, str)
    )
    required_recovery = {
        "resume",
        "complete_remaining_steps",
        "require_manual_review",
    }
    if not required_recovery <= recovery:
        raise PortiaCorruptionError(
            "deliberate-export recovery plan lacks safe resume/remaining/manual-review paths"
        )

    partial = _mapping(data.get("partial_state"), "partial_state")
    accepted = _list(partial.get("accepted_steps"), "partial accepted_steps")
    artifact_id = artifact_step.get("step_id")
    provenance_id = provenance_step.get("step_id")
    if provenance_id in accepted and artifact_id not in accepted:
        raise PortiaCorruptionError(
            "partial state cannot accept export provenance before artifact"
        )

    revision = data.get("journal_revision")
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise PortiaCorruptionError("journal_revision must be an integer")
    state = data.get("state")
    if state in {"prepared", "staged", "committing"} and planned_revision <= revision:
        raise PortiaCorruptionError(
            "pre-commit export journal must reserve a later committed revision"
        )
    if state == "committed" and planned_revision != revision:
        raise PortiaCorruptionError(
            "committed export journal must equal its reserved committed revision"
        )
    if state == "completed" and planned_revision >= revision:
        raise PortiaCorruptionError(
            "completed export journal must follow the exact committed revision"
        )


def validate_deliberate_export_lock(
    lock: PortiaRecord | Mapping[str, Any],
) -> None:
    """Validate one exact, privacy-minimized operation_lock@3 export lock."""
    data = _data(lock, contract="operation_lock", version="3")
    if data.get("schema_version") != "3":
        raise PortiaCorruptionError(
            "deliberate-export lock requires operation_lock@3"
        )
    if data.get("lock_scope") != "deliberate_export":
        raise PortiaCorruptionError(
            "operation_lock@3 is reserved for deliberate-export locking"
        )
    target = _mapping(data.get("protected_target"), "protected_target")
    _export_identity(target, "protected_target")
    expected_id = derive_lock_id("deliberate_export", target)
    if data.get("lock_id") != expected_id:
        raise PortiaCorruptionError(
            "deliberate-export operation lock has a noncanonical lock_id"
        )


def validate_deliberate_export_lock_agreement(
    journal: PortiaRecord | Mapping[str, Any],
    lock: PortiaRecord | Mapping[str, Any],
) -> None:
    """Require the durable v3 lock to equal the journal's one exact export lock."""
    validate_deliberate_export_journal(journal)
    validate_deliberate_export_lock(lock)
    journal_data = _data(journal, contract="operation_journal", version="4")
    lock_data = _data(lock, contract="operation_lock", version="3")
    journal_lock = _mapping(
        _list(journal_data.get("lock_set"), "lock_set")[0],
        "journal lock",
    )
    if (
        lock_data.get("lock_id") != journal_lock.get("lock_id")
        or lock_data.get("lock_scope") != journal_lock.get("lock_scope")
        or lock_data.get("protected_target") != journal_lock.get("protected_target")
    ):
        raise PortiaCorruptionError(
            "operation_lock@3 does not equal the journaled deliberate-export lock"
        )
    owner = _mapping(lock_data.get("owning_operation"), "owning_operation")
    if owner.get("operation_id") != journal_data.get("operation_id"):
        raise PortiaCorruptionError(
            "deliberate-export lock is owned by another operation"
        )


def _export_steps(
    journal_data: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    steps = _list(journal_data.get("write_set"), "write_set")
    if len(steps) != 2:
        raise PortiaCorruptionError(
            "deliberate-export write family must contain exactly two steps"
        )
    return (
        _mapping(steps[0], "artifact write"),
        _mapping(steps[1], "provenance write"),
    )


def validate_deliberate_export_candidate_reconciliation(
    journal: PortiaRecord | Mapping[str, Any],
    export: PortiaRecord | Mapping[str, Any],
) -> None:
    """Reconcile prepared export bytes/provenance with journal intent."""
    validate_deliberate_export_journal(journal)
    journal_data = _data(journal, contract="operation_journal", version="4")
    export_data = _data(export, contract="deliberate_export", version="1")

    primary_target = _mapping(journal_data.get("primary_target"), "primary_target")
    export_id = _export_identity(primary_target, "primary_target")
    if export_data.get("schema_version") != "1" or export_data.get("export_id") != export_id:
        raise PortiaCorruptionError(
            "deliberate_export@1 identity differs from the coordinated export target"
        )

    artifact_step, provenance_step = _export_steps(journal_data)
    artifact_intended = _mapping(
        artifact_step.get("intended_result"),
        "artifact intended_result",
    )
    artifact_fp = _fingerprint(
        artifact_intended.get("fingerprint"),
        "artifact intended_result",
    )
    output = _mapping(export_data.get("output"), "deliberate export output")
    if (
        output.get("workspace_relative_path")
        != artifact_step.get("destination_path")
        or output.get("sha256_digest") != artifact_fp.digest
        or output.get("byte_length") != artifact_fp.byte_length
    ):
        raise PortiaCorruptionError(
            "deliberate_export@1 output does not equal journaled artifact bytes"
        )

    planned_revision = planned_deliberate_export_commit_revision(journal_data)
    journal_ref = _mapping(
        export_data.get("operation_journal_ref"),
        "operation_journal_ref",
    )
    if (
        journal_ref.get("operation_id") != journal_data.get("operation_id")
        or journal_ref.get("journal_revision") != planned_revision
        or journal_ref.get("contract_version") != "4"
    ):
        raise PortiaCorruptionError(
            "deliberate_export@1 must reference the exact reserved committed v4 revision"
        )

    provenance_intended = _mapping(
        provenance_step.get("intended_result"),
        "provenance intended_result",
    )
    planned_provenance = _fingerprint(
        provenance_intended.get("fingerprint"),
        "provenance intended_result",
    )
    actual_provenance = fingerprint_bytes(canonical_json_bytes(dict(export_data)))
    if planned_provenance != actual_provenance:
        raise PortiaCorruptionError(
            "journaled deliberate-export provenance fingerprint does not equal "
            "the immutable deliberate_export@1 candidate bytes"
        )


def validate_deliberate_export_committed_reference(
    journal: PortiaRecord | Mapping[str, Any],
    export: PortiaRecord | Mapping[str, Any],
) -> None:
    """Prove one exact journal revision is the export's committed authority."""
    validate_deliberate_export_candidate_reconciliation(journal, export)
    journal_data = _data(journal, contract="operation_journal", version="4")
    if journal_data.get("state") != "committed":
        raise PortiaCorruptionError(
            "deliberate export must resolve its operation_journal_ref to committed, "
            "not current/latest/completed"
        )
    planned_revision = planned_deliberate_export_commit_revision(journal_data)
    if journal_data.get("journal_revision") != planned_revision:
        raise PortiaCorruptionError(
            "referenced export journal is not the reserved committed revision"
        )
    commit_point = _mapping(journal_data.get("commit_point"), "commit_point")
    if commit_point.get("reached") is not True:
        raise PortiaCorruptionError(
            "referenced export journal has not reached its commit point"
        )
    artifact_step, provenance_step = _export_steps(journal_data)
    if (
        artifact_step.get("disposition") != "accepted"
        or provenance_step.get("disposition") != "accepted"
    ):
        raise PortiaCorruptionError(
            "committed export journal does not accept both durable representations"
        )
    partial = _mapping(journal_data.get("partial_state"), "partial_state")
    accepted = set(
        item
        for item in _list(partial.get("accepted_steps"), "accepted_steps")
        if isinstance(item, str)
    )
    expected = {
        cast(str, artifact_step.get("step_id")),
        cast(str, provenance_step.get("step_id")),
    }
    if accepted != expected:
        raise PortiaCorruptionError(
            "committed export journal partial state does not reconcile both accepted writes"
        )


def deliberate_export_immutable_plan(
    journal: PortiaRecord | Mapping[str, Any],
) -> bytes:
    """Return the immutable v4 export plan used for revision-series comparison."""
    data = _data(journal, contract="operation_journal", version="4")
    validate_deliberate_export_journal(data)

    raw_locks = _list(data.get("lock_set"), "lock_set")
    raw_steps = _list(data.get("write_set"), "write_set")
    lock_plan = []
    for raw in raw_locks:
        entry = _mapping(raw, "lock entry")
        lock_plan.append(
            {
                "lock_id": entry.get("lock_id"),
                "sequence": entry.get("sequence"),
                "lock_scope": entry.get("lock_scope"),
                "protected_target": entry.get("protected_target"),
                "lock_path": entry.get("lock_path"),
            }
        )

    write_plan = []
    immutable_write_fields = (
        "step_id",
        "sequence",
        "phase",
        "action",
        "target",
        "representation_role",
        "destination_path",
        "precondition",
        "intended_result",
        "compensation_step_id",
        "reason_code",
    )
    for raw in raw_steps:
        step = _mapping(raw, "write step")
        write_plan.append({field: step.get(field) for field in immutable_write_fields})

    immutable = {
        "operation_id": data.get("operation_id"),
        "operation_kind": data.get("operation_kind"),
        "intent_digest": data.get("intent_digest"),
        "scope": data.get("scope"),
        "primary_target": data.get("primary_target"),
        "affected_targets": data.get("affected_targets"),
        "intent_facts": data.get("intent_facts"),
        "initiated_at": data.get("initiated_at"),
        "initiated_by": data.get("initiated_by"),
        "authorization_references": data.get("authorization_references"),
        "preflight_snapshot_digest": data.get("preflight_snapshot_digest"),
        "preflight_snapshot": data.get("preflight_snapshot"),
        "lock_plan": lock_plan,
        "write_plan": write_plan,
        "compensation_plan": data.get("compensation_plan"),
        "recovery_plan": data.get("recovery_plan"),
        "created_at": data.get("created_at"),
    }
    return canonical_json_bytes(immutable)
