"""Amendment policy, exact history reconciliation, and journaled mutation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TypeAlias, cast

from portia.models import PortiaRecord, parse_portia_record
from portia.models.json_values import JsonValue
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.io import read_bytes
from portia.storage.locks import derive_lock_id
from portia.storage.orchestration import (
    FaultHook,
    OperationCommitResult,
    commit_journaled_candidates,
    stage_journaled_candidates,
)
from portia.storage.paths import (
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.storage.staging import cleanup_staged
from portia.workflows.common import (
    WorkflowServiceBase,
    record_target,
    work_target,
)
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.coordinated import EventBundleWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_AMENDMENT_VERSION = "1"
AmendmentTargetReference: TypeAlias = ExactPortiaWorkRef | ExactPortiaWorkRecordRef


@dataclass(frozen=True, slots=True)
class AmendmentPathPolicy:
    """One record-family path permitted to enter Amendment materiality review."""

    path: str
    validator: str


@dataclass(frozen=True, slots=True)
class AmendmentResolution:
    """Exact selected Amendment chain and its current-target reconciliation."""

    reference: AmendmentTargetReference
    target: StoredRecord
    amendments: tuple[StoredRecord, ...]
    selected_amendment: StoredRecord | None
    policies: tuple[AmendmentPathPolicy, ...]
    reconciliation_error: str | None

    @property
    def reconciled(self) -> bool:
        return self.reconciliation_error is None

    @property
    def selected_amendment_id(self) -> str | None:
        if self.selected_amendment is None:
            return None
        return self.selected_amendment.record.logical_id


_AMENDMENT_POLICIES: dict[
    tuple[str, str], tuple[AmendmentPathPolicy, ...]
] = {
    ("event", "2"): (
        AmendmentPathPolicy("/summary", "event_summary_semantic_equivalence"),
        AmendmentPathPolicy(
            "/location/detail",
            "event_location_detail_semantic_equivalence",
        ),
        AmendmentPathPolicy(
            "/instructional_context/detail",
            "event_instructional_context_detail_semantic_equivalence",
        ),
    ),
    ("event_participant", "3"): (
        AmendmentPathPolicy(
            "/subject/display_snapshot/display_name",
            "participant_display_snapshot_semantic_equivalence",
        ),
    ),
    ("event_participant_role", "3"): (
        AmendmentPathPolicy(
            "/detail",
            "contextual_role_detail_semantic_equivalence",
        ),
    ),
    ("statement_of_disagreement", "1"): (
        AmendmentPathPolicy(
            "/statement/text",
            "disagreement_recorded_summary_semantic_equivalence",
        ),
    ),
    ("work_relationship", "2"): (
        AmendmentPathPolicy(
            "/detail",
            "work_relationship_detail_semantic_equivalence",
        ),
    ),
}


def supported_amendment_contracts() -> tuple[tuple[str, str], ...]:
    """Return the closed exact contract registry with Amendment authority."""
    return tuple(sorted(_AMENDMENT_POLICIES))


def amendment_path_policies(
    contract: str,
    version: str,
) -> tuple[AmendmentPathPolicy, ...]:
    """Return accepted path policies; unregistered contracts fail closed to empty."""
    return _AMENDMENT_POLICIES.get((contract, version), ())


def amendable_paths(contract: str, version: str) -> tuple[str, ...]:
    """Return JSON Pointers eligible for family-specific nonmateriality review."""
    return tuple(
        policy.path for policy in amendment_path_policies(contract, version)
    )


def _parsed_timestamp(value: object, description: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} is not an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} is not an explicit timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(f"{description} lacks an explicit offset")
    return parsed


def _decode_pointer(path: object) -> tuple[str, ...]:
    if not isinstance(path, str) or not path.startswith("/"):
        raise WorkflowPrerequisiteError(
            "Amendment change path must be a non-root JSON Pointer"
        )
    raw_tokens = path[1:].split("/")
    tokens: list[str] = []
    for raw in raw_tokens:
        token = ""
        index = 0
        while index < len(raw):
            char = raw[index]
            if char != "~":
                token += char
                index += 1
                continue
            if index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}:
                raise WorkflowPrerequisiteError(
                    "Amendment change path contains an invalid JSON Pointer escape"
                )
            token += "~" if raw[index + 1] == "0" else "/"
            index += 2
        tokens.append(token)
    return tuple(tokens)


def _target_parts(
    reference: AmendmentTargetReference,
) -> tuple[ExactPortiaWorkRef, str, str, dict[str, object]]:
    if isinstance(reference, ExactPortiaWorkRef):
        work_target: dict[str, object] = {
            "kind": "work",
            "work_kind": reference.work_kind,
            "contract_version": reference.contract_version,
        }
        return (
            reference,
            reference.work_kind,
            reference.contract_version,
            work_target,
        )
    record_target: dict[str, object] = {
        "kind": "local_record",
        "record_ref": reference.record_ref.to_dict(),
    }
    return (
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        record_target,
    )


def _load_target(
    service: WorkflowServiceBase,
    reference: AmendmentTargetReference,
) -> StoredRecord:
    if isinstance(reference, ExactPortiaWorkRef):
        return service.repository.load_work(reference)
    return service.repository.load_work_record(
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )


def _previous_amendment_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_amendment")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError("Amendment previous_amendment is malformed")
    if (
        previous.get("record_kind") != "amendment"
        or previous.get("contract_version") != _AMENDMENT_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "Amendment previous_amendment is not an exact amendment@1 reference"
        )
    return cast(str, previous["record_id"])


def _ordered_chain(
    selected: tuple[StoredRecord, ...],
) -> tuple[StoredRecord, ...]:
    if not selected:
        return ()
    by_id: dict[str, StoredRecord] = {}
    children: dict[str, list[str]] = {}
    roots: list[str] = []
    for stored in selected:
        amendment_id = stored.record.logical_id
        if amendment_id is None:
            raise WorkflowOwnershipError("Amendment has no exact identity")
        if amendment_id in by_id:
            raise WorkflowPrerequisiteError("Amendment history repeats an identity")
        by_id[amendment_id] = stored
        previous_id = _previous_amendment_id(stored.record)
        if previous_id is None:
            roots.append(amendment_id)
        else:
            if previous_id == amendment_id:
                raise WorkflowPrerequisiteError(
                    "Amendment cannot reference itself as previous_amendment"
                )
            children.setdefault(previous_id, []).append(amendment_id)

    missing = sorted(identifier for identifier in children if identifier not in by_id)
    if missing:
        raise WorkflowPrerequisiteError(
            "Amendment history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "Amendment history must contain exactly one root Amendment"
        )
    if any(len(values) != 1 for values in children.values()):
        raise WorkflowPrerequisiteError("Amendment history contains a fork")

    ordered: list[StoredRecord] = []
    visited: set[str] = set()
    current_id = roots[0]
    while True:
        if current_id in visited:
            raise WorkflowPrerequisiteError("Amendment history contains a cycle")
        visited.add(current_id)
        ordered.append(by_id[current_id])
        next_ids = children.get(current_id, [])
        if not next_ids:
            break
        current_id = next_ids[0]
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "Amendment history contains a disconnected Amendment"
        )
    return tuple(ordered)


def _property_state(
    document: Mapping[str, object],
    path: str,
) -> dict[str, object]:
    tokens = _decode_pointer(path)
    current: object = document
    for token in tokens[:-1]:
        if isinstance(current, list):
            raise WorkflowPrerequisiteError(
                "Amendment change path must not traverse an array"
            )
        if not isinstance(current, Mapping):
            raise WorkflowPrerequisiteError(
                "Amendment change path traverses a non-object value"
            )
        if token not in current:
            raise WorkflowPrerequisiteError(
                "Amendment change path has a missing parent object"
            )
        current = current[token]
    if isinstance(current, list):
        raise WorkflowPrerequisiteError(
            "Amendment change path must not traverse an array"
        )
    if not isinstance(current, Mapping):
        raise WorkflowPrerequisiteError(
            "Amendment change path parent is not an object"
        )
    leaf = tokens[-1]
    if leaf not in current:
        return {"present": False}
    return {"present": True, "value": deepcopy(current[leaf])}


def _declared_state(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or not isinstance(value.get("present"), bool):
        raise WorkflowPrerequisiteError(f"{description} is malformed")
    present = cast(bool, value["present"])
    if present:
        if "value" not in value:
            raise WorkflowPrerequisiteError(f"{description} lacks its present value")
        return {"present": True, "value": deepcopy(value["value"])}
    if "value" in value:
        raise WorkflowPrerequisiteError(f"{description} has a value while absent")
    return {"present": False}


def _restore_property_state(
    document: dict[str, object],
    path: str,
    state: Mapping[str, object],
) -> None:
    tokens = _decode_pointer(path)
    current: object = document
    for token in tokens[:-1]:
        if isinstance(current, list):
            raise WorkflowPrerequisiteError(
                "Amendment change path must not traverse an array"
            )
        if not isinstance(current, dict) or token not in current:
            raise WorkflowPrerequisiteError(
                "Amendment change path cannot restore through a missing parent"
            )
        current = current[token]
    if isinstance(current, list):
        raise WorkflowPrerequisiteError(
            "Amendment change path must not traverse an array"
        )
    if not isinstance(current, dict):
        raise WorkflowPrerequisiteError(
            "Amendment change path parent is not a mutable object"
        )
    leaf = tokens[-1]
    if state.get("present") is True:
        if "value" not in state:
            raise WorkflowPrerequisiteError("present Amendment state lacks a value")
        current[leaf] = deepcopy(state["value"])
    else:
        current.pop(leaf, None)


def _paths_overlap(first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    shorter, longer = (first, second) if len(first) <= len(second) else (second, first)
    return shorter == longer[: len(shorter)]


def _policy_for(
    contract: str,
    version: str,
    path: str,
) -> AmendmentPathPolicy | None:
    return next(
        (
            policy
            for policy in amendment_path_policies(contract, version)
            if policy.path == path
        ),
        None,
    )


def _require_policy_context(
    target: PortiaRecord,
    policy: AmendmentPathPolicy,
) -> None:
    data = target.to_dict()
    if policy.validator == "participant_display_snapshot_semantic_equivalence":
        subject = data.get("subject")
        if not isinstance(subject, Mapping) or subject.get("kind") not in {
            "roster_student",
            "actor",
        }:
            raise WorkflowPrerequisiteError(
                "Event Participant Amendment display path requires a stable "
                "roster-student or Actor subject reference"
            )
    elif policy.validator == "contextual_role_detail_semantic_equivalence":
        if data.get("role_type") != "contextual":
            raise WorkflowPrerequisiteError(
                "Event Participant Role Amendment detail is permitted only for "
                "a contextual Role"
            )
    elif policy.validator == "disagreement_recorded_summary_semantic_equivalence":
        statement = data.get("statement")
        if (
            not isinstance(statement, Mapping)
            or statement.get("representation") != "recorded_summary"
        ):
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement Amendment text is permitted only for "
                "a recorded_summary representation"
            )


def _changes(record: PortiaRecord) -> tuple[Mapping[str, object], ...]:
    raw = record.field("changes")
    if not isinstance(raw, tuple):
        raise WorkflowPrerequisiteError("Amendment changes are malformed")
    changes: list[Mapping[str, object]] = []
    for value in raw:
        if not isinstance(value, Mapping):
            raise WorkflowPrerequisiteError("Amendment change entry is malformed")
        changes.append(value)
    if not changes:
        raise WorkflowPrerequisiteError("Amendment must contain at least one change")
    return tuple(changes)


def _validate_change_set(
    target: PortiaRecord,
    amendment: PortiaRecord,
    working: dict[str, object],
) -> tuple[tuple[Mapping[str, object], str], ...]:
    changes = _changes(amendment)
    paths: list[str] = []
    decoded: list[tuple[str, ...]] = []
    for change in changes:
        path = change.get("path")
        if not isinstance(path, str):
            raise WorkflowPrerequisiteError("Amendment change path is malformed")
        paths.append(path)
        decoded.append(_decode_pointer(path))
    if len(set(paths)) != len(paths):
        raise WorkflowPrerequisiteError("Amendment change paths must be unique")
    for index, first in enumerate(decoded):
        for second in decoded[index + 1 :]:
            if _paths_overlap(first, second):
                raise WorkflowPrerequisiteError(
                    "Amendment change paths must not overlap as ancestor and descendant"
                )

    validated: list[tuple[Mapping[str, object], str]] = []
    for change, path in zip(changes, paths, strict=True):
        actual_after = _property_state(working, path)
        policy = _policy_for(target.contract, target.contract_version, path)
        if policy is None:
            raise WorkflowPrerequisiteError(
                f"{target.contract}@{target.contract_version} does not permit "
                f"Amendment path {path!r}"
            )
        _require_policy_context(target, policy)
        before = _declared_state(change.get("before"), "Amendment before state")
        after = _declared_state(change.get("after"), "Amendment after state")
        operation = change.get("operation")
        if operation == "add":
            if before != {"present": False} or after.get("present") is not True:
                raise WorkflowPrerequisiteError(
                    "Amendment add must change absent state to present state"
                )
        elif operation == "replace":
            if before.get("present") is not True or after.get("present") is not True:
                raise WorkflowPrerequisiteError(
                    "Amendment replace must preserve property presence"
                )
            if before == after:
                raise WorkflowPrerequisiteError(
                    "Amendment replace before and after values must differ"
                )
        elif operation == "remove":
            if before.get("present") is not True or after != {"present": False}:
                raise WorkflowPrerequisiteError(
                    "Amendment remove must change present state to absent state"
                )
        else:
            raise WorkflowPrerequisiteError("Amendment operation is unsupported")
        if actual_after != after:
            raise WorkflowPrerequisiteError(
                f"Amendment after state does not match target history at {path!r}"
            )
        validated.append((change, path))
    return tuple(validated)


def _history_reconciliation_error(
    target: PortiaRecord,
    ordered: tuple[StoredRecord, ...],
) -> str | None:
    if not ordered:
        return None
    target_data = target.to_dict()
    current_updated = target_data.get("updated_at")
    head_created = ordered[-1].record.field("created_at")
    if _parsed_timestamp(current_updated, "target updated_at") < _parsed_timestamp(
        head_created, "selected Amendment created_at"
    ):
        return "canonical target revision predates the selected Amendment head"

    working = cast(dict[str, object], deepcopy(target_data))
    for stored in reversed(ordered):
        amendment = stored.record
        try:
            validated = _validate_change_set(target, amendment, working)
        except WorkflowPrerequisiteError as exc:
            message = str(exc)
            if "after state does not match target history" in message:
                return message
            raise
        for change, path in validated:
            before = _declared_state(
                change.get("before"), "Amendment before state"
            )
            _restore_property_state(working, path, before)
    return None


_AMENDMENT_REASON_CODES = frozenset(
    {
        "spelling_corrected",
        "punctuation_corrected",
        "formatting_corrected",
        "transcription_corrected",
        "display_value_corrected",
        "nonsemantic_metadata_corrected",
        "other",
    }
)
_TEXTUAL_REASON_CODES = frozenset(
    {
        "spelling_corrected",
        "punctuation_corrected",
        "formatting_corrected",
        "transcription_corrected",
        "other",
    }
)
_DISPLAY_REASON_CODES = _TEXTUAL_REASON_CODES | {"display_value_corrected"}


def _amendment_reason(code: str, detail: str | None) -> dict[str, object]:
    if code not in _AMENDMENT_REASON_CODES:
        raise WorkflowPrerequisiteError(f"unsupported Amendment reason code: {code!r}")
    if code == "other" and (detail is None or not detail.strip()):
        raise WorkflowPrerequisiteError("Amendment reason 'other' requires detail")
    reason: dict[str, object] = {"code": code}
    if detail is not None:
        reason["detail"] = detail
    return reason


def _reason_allowed(policy: AmendmentPathPolicy, code: str) -> bool:
    if policy.validator == "participant_display_snapshot_semantic_equivalence":
        return code in _DISPLAY_REASON_CODES
    return code in _TEXTUAL_REASON_CODES


def _mutation_change_set(
    target: PortiaRecord,
    changes: Sequence[Mapping[str, object]],
    *,
    reason_code: str,
    semantic_equivalence_confirmed: bool,
) -> tuple[dict[str, object], ...]:
    if not semantic_equivalence_confirmed:
        raise WorkflowPrerequisiteError(
            "requested Amendment lacks explicit semantic-equivalence confirmation; "
            "successor correction is required when materiality is uncertain"
        )
    if not changes:
        raise WorkflowPrerequisiteError("Amendment must contain at least one change")

    normalized: list[dict[str, object]] = []
    paths: list[str] = []
    decoded: list[tuple[str, ...]] = []
    for raw in changes:
        path = raw.get("path")
        if not isinstance(path, str):
            raise WorkflowPrerequisiteError("Amendment change path is malformed")
        policy = _policy_for(target.contract, target.contract_version, path)
        if policy is None:
            raise WorkflowPrerequisiteError(
                f"{target.contract}@{target.contract_version} does not permit "
                f"Amendment path {path!r}; successor correction is required"
            )
        _require_policy_context(target, policy)
        if not _reason_allowed(policy, reason_code):
            raise WorkflowPrerequisiteError(
                f"Amendment reason {reason_code!r} is incompatible with path {path!r}"
            )
        operation = raw.get("operation")
        if operation != "replace":
            raise WorkflowPrerequisiteError(
                "current Amendment-authorized paths are conditionally amendable text; "
                "add/remove presence changes require successor correction"
            )
        before = _declared_state(raw.get("before"), "Amendment before state")
        after = _declared_state(raw.get("after"), "Amendment after state")
        if before.get("present") is not True or after.get("present") is not True:
            raise WorkflowPrerequisiteError(
                "current Amendment-authorized paths require present-to-present replacement"
            )
        before_value = before.get("value")
        after_value = after.get("value")
        if not isinstance(before_value, str) or not isinstance(after_value, str):
            raise WorkflowPrerequisiteError(
                "current Amendment-authorized paths require textual before/after values"
            )
        if before_value == after_value:
            raise WorkflowPrerequisiteError(
                "Amendment replace before and after values must differ"
            )
        paths.append(path)
        decoded.append(_decode_pointer(path))
        normalized.append(
            {
                "path": path,
                "operation": "replace",
                "before": before,
                "after": after,
            }
        )

    if len(set(paths)) != len(paths):
        raise WorkflowPrerequisiteError("Amendment change paths must be unique")
    for index, first in enumerate(decoded):
        for second in decoded[index + 1 :]:
            if _paths_overlap(first, second):
                raise WorkflowPrerequisiteError(
                    "Amendment change paths must not overlap as ancestor and descendant"
                )
    return tuple(normalized)


def _apply_state(
    document: dict[str, object],
    path: str,
    state: Mapping[str, object],
) -> None:
    tokens = _decode_pointer(path)
    current: object = document
    for token in tokens[:-1]:
        if isinstance(current, list):
            raise WorkflowPrerequisiteError(
                "Amendment change path must not traverse an array"
            )
        if not isinstance(current, dict) or token not in current:
            raise WorkflowPrerequisiteError(
                "Amendment change path has a missing parent object"
            )
        current = current[token]
    if isinstance(current, list):
        raise WorkflowPrerequisiteError(
            "Amendment change path must not traverse an array"
        )
    if not isinstance(current, dict):
        raise WorkflowPrerequisiteError(
            "Amendment change path parent is not a mutable object"
        )
    leaf = tokens[-1]
    if state.get("present") is True:
        if "value" not in state:
            raise WorkflowPrerequisiteError("present Amendment state lacks a value")
        current[leaf] = deepcopy(state["value"])
    else:
        current.pop(leaf, None)


def _amended_candidate(
    prior: PortiaRecord,
    changes: tuple[dict[str, object], ...],
    *,
    amended_at: str,
    amended_by: Mapping[str, object],
) -> PortiaRecord:
    data = cast(dict[str, object], deepcopy(prior.to_dict()))
    for change in changes:
        path = cast(str, change["path"])
        before = cast(Mapping[str, object], change["before"])
        actual = _property_state(data, path)
        if actual != before:
            raise PortiaConflictError(
                f"Amendment before state does not match selected target at {path!r}"
            )
        _apply_state(data, path, cast(Mapping[str, object], change["after"]))
    data["updated_at"] = amended_at
    data["updated_by"] = cast(JsonValue, dict(amended_by))
    candidate = parse_portia_record(prior.contract, prior.contract_version, data)
    for protected in (
        "module_id",
        "class_id",
        "work_id",
        "work_kind",
        "status",
        "creation_source",
        "created_at",
        "created_by",
        "supersedes",
    ):
        if candidate.field(protected) != prior.field(protected):
            raise WorkflowPrerequisiteError(
                f"Amendment changed protected target field {protected!r}"
            )
    if candidate.logical_id != prior.logical_id:
        raise WorkflowPrerequisiteError("Amendment changed canonical target identity")
    return candidate


def _previous_amendment_ref(amendment_id: str | None) -> dict[str, object] | None:
    if amendment_id is None:
        return None
    return {
        "record_kind": "amendment",
        "record_id": amendment_id,
        "contract_version": _AMENDMENT_VERSION,
    }


def _build_amendment(
    reference: AmendmentTargetReference,
    *,
    amendment_id: str,
    previous_amendment_id: str | None,
    target_updated_at_before: str,
    changes: tuple[dict[str, object], ...],
    reason_code: str,
    reason_detail: str | None,
    created_at: str,
    created_by: Mapping[str, object],
) -> PortiaRecord:
    work, _contract, _version, target = _target_parts(reference)
    return parse_portia_record(
        "amendment",
        _AMENDMENT_VERSION,
        {
            "schema_version": _AMENDMENT_VERSION,
            "record_type": "amendment",
            "module_id": "portia",
            "class_id": work.class_id,
            "work_id": work.work_id,
            "amendment_id": amendment_id,
            "target": target,
            "previous_amendment": _previous_amendment_ref(previous_amendment_id),
            "target_updated_at_before": target_updated_at_before,
            "changes": [deepcopy(change) for change in changes],
            "reason": _amendment_reason(reason_code, reason_detail),
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )


def _target_journal_ref(
    reference: AmendmentTargetReference,
    target: PortiaRecord,
) -> dict[str, object]:
    work, _contract, _version, _shape = _target_parts(reference)
    if isinstance(reference, ExactPortiaWorkRef):
        return work_target(work)
    return record_target(work, target)


def _amendment_journal_ref(
    work: ExactPortiaWorkRef,
    amendment: PortiaRecord,
) -> dict[str, object]:
    return record_target(work, amendment)


def _history_snapshot(
    records: tuple[StoredRecord, ...],
) -> tuple[tuple[str, ContentFingerprint], ...]:
    values: list[tuple[str, ContentFingerprint]] = []
    for stored in records:
        identifier = stored.record.logical_id
        if identifier is None:
            raise WorkflowOwnershipError("Amendment history artifact has no identity")
        values.append((identifier, stored.fingerprint))
    return tuple(sorted(values, key=lambda item: item[0]))


def _intent_digest(
    reference: AmendmentTargetReference,
    *,
    expected: ContentFingerprint,
    amendment_id: str,
    changes: tuple[dict[str, object], ...],
    reason_code: str,
    reason_detail: str | None,
    created_at: str,
    created_by: Mapping[str, object],
) -> str:
    payload = {
        "reference": reference.to_dict(),
        "expected": expected.to_dict(),
        "amendment_id": amendment_id,
        "changes": [deepcopy(change) for change in changes],
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "created_at": created_at,
        "created_by": dict(created_by),
        "semantic_equivalence_confirmed": True,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _state_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "token", "value": value}


def _identifier_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "identifier", "value": value}


def _expected_state(step: Mapping[str, object]) -> dict[str, object]:
    precondition = step.get("precondition")
    if not isinstance(precondition, Mapping):
        raise PortiaConflictError("Amendment write step has no precondition")
    presence = precondition.get("presence")
    if presence == "must_be_absent":
        return {"presence": "must_be_absent"}
    if presence != "must_match":
        raise PortiaConflictError("Amendment write precondition is unsupported")
    fingerprint = precondition.get("fingerprint")
    semantic_checks = precondition.get("semantic_checks")
    if not isinstance(fingerprint, Mapping) or not isinstance(semantic_checks, list):
        raise PortiaConflictError("Amendment must-match precondition is incomplete")
    return {
        "presence": "must_match",
        "fingerprint": dict(fingerprint),
        "semantic_checks": semantic_checks,
    }


def _journal_plan(
    *,
    operation_id: str,
    digest: str,
    timestamp: str,
    initiated_by: Mapping[str, object],
    primary_target: dict[str, object],
    amendment_target: dict[str, object],
    lock_entries: list[dict[str, object]],
    steps: list[dict[str, object]],
    contract: str,
    amendment_id: str,
) -> dict[str, object]:
    preflight: list[dict[str, object]] = []
    for step in steps:
        intended = step.get("intended_result")
        destination = step.get("destination_path")
        role = step.get("representation_role")
        target = step.get("target")
        if (
            not isinstance(intended, Mapping)
            or not isinstance(destination, str)
            or not isinstance(role, str)
            or not isinstance(target, dict)
        ):
            raise PortiaConflictError("Amendment write step is incomplete")
        contract_version = intended.get("contract_version")
        selected_state = intended.get("selected_state")
        if not isinstance(contract_version, str) or not isinstance(selected_state, list):
            raise PortiaConflictError("Amendment intended result is incomplete")
        preflight.append(
            {
                "target": target,
                "representation_role": role,
                "expected_state": _expected_state(step),
                "workspace_relative_path": destination,
                "contract_version": contract_version,
                "source_basis": "canonical",
                "source_projection": None,
                "selected_state": selected_state,
                "observed_at": timestamp,
            }
        )
    preflight_digest = fingerprint_bytes(
        canonical_json_bytes({"entries": preflight})
    ).digest
    step_ids = [str(step["step_id"]) for step in steps]
    return {
        "schema_version": "2",
        "record_type": "operation_journal",
        "module_id": "portia",
        "operation_id": operation_id,
        "operation_kind": "apply_amendment",
        "intent_digest": digest,
        "scope": "work",
        "primary_target": primary_target,
        "affected_targets": [amendment_target],
        "intent_facts": [
            _state_fact("record_kind", contract),
            _identifier_fact("amendment_id", amendment_id),
            _state_fact("semantic_equivalence", "confirmed"),
        ],
        "initiated_at": timestamp,
        "initiated_by": dict(initiated_by),
        "authorization_references": [],
        "journal_revision": 1,
        "previous_journal_revision": None,
        "state": "staged",
        "preflight_snapshot_digest": preflight_digest,
        "preflight_snapshot": preflight,
        "lock_set": lock_entries,
        "write_set": steps,
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
            "remaining_canonical_steps": step_ids,
            "remaining_post_commit_steps": [],
            "current_pointer_changes": [],
            "held_or_possible_locks": [],
            "quarantined_targets": [],
            "active_finding_keys": [],
            "recommended_disposition": "resume",
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _lock_plan(
    operation_id: str,
    work: ExactPortiaWorkRef,
    timestamp: str,
) -> tuple[list[dict[str, object]], dict[str, PortiaRecord]]:
    operation_target: dict[str, object] = {
        "kind": "operation",
        "operation_ref": {"operation_id": operation_id},
    }
    targets = (("operation", operation_target), ("work", work_target(work)))
    entries: list[dict[str, object]] = []
    records: dict[str, PortiaRecord] = {}
    for sequence, (scope, target) in enumerate(targets, start=1):
        lock_id = derive_lock_id(scope, target)
        entries.append(
            {
                "lock_id": lock_id,
                "sequence": sequence,
                "lock_scope": scope,
                "protected_target": target,
                "lock_path": f"portia/locks/{lock_id}.json",
                "disposition": "planned",
                "fingerprint": None,
                "acquired_at": None,
                "released_at": None,
            }
        )
        records[lock_id] = parse_portia_record(
            "operation_lock",
            "2",
            {
                "schema_version": "2",
                "record_type": "operation_lock",
                "module_id": "portia",
                "lock_id": lock_id,
                "lock_scope": scope,
                "protected_target": target,
                "owning_operation": {"operation_id": operation_id},
                "acquired_at": timestamp,
                "deployment_instance_id": "amendment_workflow",
                "process_instance_id": "amendment_workflow",
            },
        )
    return entries, records


def _target_history_path(
    workspace_root: Path,
    work: ExactPortiaWorkRef,
    target: PortiaRecord,
    digest: str,
) -> Path:
    identifier = target.logical_id
    if identifier is None:
        raise WorkflowOwnershipError("Amendment target has no canonical identity")
    return work_storage_history_path(
        workspace_root,
        work,
        target.contract,
        identifier,
        digest,
    )


def _all_target_amendments(
    repository: PortiaRepository,
    reference: AmendmentTargetReference,
) -> tuple[StoredRecord, ...]:
    work, _contract, _version, expected_target = _target_parts(reference)
    return tuple(
        stored
        for stored in repository.list_work_records(
            work, "amendment", version=_AMENDMENT_VERSION
        )
        if stored.record.field("target") == expected_target
    )


def _require_locked_preflight_state(
    repository: PortiaRepository,
    reference: AmendmentTargetReference,
    *,
    expected_target: ContentFingerprint,
    expected_amendments: tuple[tuple[str, ContentFingerprint], ...],
    amendment_id: str,
) -> None:
    if isinstance(reference, ExactPortiaWorkRef):
        current = repository.load_work(reference)
        work = reference
    else:
        work = reference.work_ref
        current = repository.load_work_record(
            work,
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
    if current.fingerprint != expected_target:
        raise PortiaConflictError("Amendment target changed after preflight")
    if _history_snapshot(_all_target_amendments(repository, reference)) != expected_amendments:
        raise PortiaConflictError("Amendment history changed after preflight")
    all_amendments = repository.list_work_records(
        work, "amendment", version=_AMENDMENT_VERSION
    )
    if any(item.record.logical_id == amendment_id for item in all_amendments):
        raise PortiaConflictError("Amendment identity appeared after preflight")


class AmendmentWorkflowService(WorkflowServiceBase):
    """Read and journal strictly nonmaterial exact work-local Amendments."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )

    def _operation_support(self) -> EventBundleWorkflowService:
        return EventBundleWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    @staticmethod
    def supported_contracts() -> tuple[tuple[str, str], ...]:
        return supported_amendment_contracts()

    def load_history(
        self,
        reference: AmendmentTargetReference,
    ) -> AmendmentResolution:
        work, contract, version, expected_target = _target_parts(reference)
        policies = amendment_path_policies(contract, version)
        if not policies:
            raise WorkflowOwnershipError(
                f"no registered Amendment policy for {contract}@{version}"
            )
        target = _load_target(self, reference)
        if (
            target.record.contract != contract
            or target.record.contract_version != version
        ):
            raise WorkflowOwnershipError(
                "resolved Amendment target does not match the exact target contract"
            )

        selected = tuple(
            stored
            for stored in self.repository.list_work_records(
                work, "amendment", version=_AMENDMENT_VERSION
            )
            if stored.record.field("target") == expected_target
        )
        for stored in selected:
            if (
                stored.record.class_id != work.class_id
                or stored.record.work_id != work.work_id
            ):
                raise WorkflowOwnershipError(
                    "Amendment history does not belong to the exact containing work"
                )
        ordered = _ordered_chain(selected)

        previous: StoredRecord | None = None
        for stored in ordered:
            amendment = stored.record
            before = amendment.field("target_updated_at_before")
            created = amendment.field("created_at")
            before_time = _parsed_timestamp(
                before, "Amendment target_updated_at_before"
            )
            created_time = _parsed_timestamp(created, "Amendment created_at")
            if created_time <= before_time:
                raise WorkflowPrerequisiteError(
                    "Amendment created_at must follow target_updated_at_before"
                )
            if previous is not None:
                previous_created = _parsed_timestamp(
                    previous.record.field("created_at"),
                    "previous Amendment created_at",
                )
                if before_time < previous_created:
                    raise WorkflowPrerequisiteError(
                        "Amendment target revision predates its predecessor Amendment"
                    )
            previous = stored

        reconciliation_error = _history_reconciliation_error(target.record, ordered)
        return AmendmentResolution(
            reference=reference,
            target=target,
            amendments=ordered,
            selected_amendment=ordered[-1] if ordered else None,
            policies=policies,
            reconciliation_error=reconciliation_error,
        )

    def resolve_selected_head(
        self,
        reference: AmendmentTargetReference,
    ) -> StoredRecord | None:
        return self.load_history(reference).selected_amendment

    def require_reconciled(
        self,
        reference: AmendmentTargetReference,
    ) -> AmendmentResolution:
        resolution = self.load_history(reference)
        if not resolution.reconciled:
            raise WorkflowPrerequisiteError(
                "canonical target does not reconcile with selected Amendment history: "
                f"{resolution.reconciliation_error}"
            )
        return resolution

    def _completed_replay(
        self,
        operation_id: str | None,
        reference: AmendmentTargetReference,
        *,
        digest: str,
        amendment_id: str,
    ) -> OperationCommitResult | None:
        if operation_id is None:
            return None
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            return None
        data = current.revision.to_dict()
        if data.get("intent_digest") != digest or data.get("operation_kind") != "apply_amendment":
            raise PortiaConflictError(
                "operation identity is already bound to different Amendment intent"
            )
        state = data.get("state")
        if state == "completed":
            resolution = self.require_reconciled(reference)
            if resolution.selected_amendment_id != amendment_id:
                raise PortiaRecoveryRequiredError(
                    "completed Amendment operation no longer selects its Amendment head"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing Amendment operation requires explicit #38 recovery"
            )
        return None

    def apply_amendment(
        self,
        reference: AmendmentTargetReference,
        *,
        expected: ContentFingerprint,
        amendment_id: str,
        changes: Sequence[Mapping[str, object]],
        reason_code: str,
        created_at: str,
        created_by: Mapping[str, object],
        semantic_equivalence_confirmed: bool,
        reason_detail: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Persist immutable Amendment evidence before guarded target replacement."""
        work, contract, version, _target_shape = _target_parts(reference)
        policies = amendment_path_policies(contract, version)
        if not policies:
            raise WorkflowOwnershipError(
                f"no registered Amendment policy for {contract}@{version}"
            )
        normalized = _mutation_change_set(
            _load_target(self, reference).record,
            changes,
            reason_code=reason_code,
            semantic_equivalence_confirmed=semantic_equivalence_confirmed,
        )
        _amendment_reason(reason_code, reason_detail)
        digest = _intent_digest(
            reference,
            expected=expected,
            amendment_id=amendment_id,
            changes=normalized,
            reason_code=reason_code,
            reason_detail=reason_detail,
            created_at=created_at,
            created_by=created_by,
        )
        op_id = operation_id or f"op_{digest}"
        replay = self._completed_replay(
            op_id,
            reference,
            digest=digest,
            amendment_id=amendment_id,
        )
        if replay is not None:
            return replay

        resolution = self.require_reconciled(reference)
        prior = resolution.target
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Amendment target state does not match selected canonical bytes"
            )
        prior_data = prior.record.to_dict()
        target_updated_at = prior_data.get("updated_at")
        if not isinstance(target_updated_at, str):
            raise WorkflowPrerequisiteError(
                "Amendment target update provenance is incomplete"
            )
        amendment_time = _parsed_timestamp(created_at, "Amendment created_at")
        target_time = _parsed_timestamp(target_updated_at, "target updated_at")
        if amendment_time <= target_time:
            raise WorkflowPrerequisiteError(
                "Amendment created_at must follow target_updated_at_before"
            )
        previous_id = resolution.selected_amendment_id
        if resolution.selected_amendment is not None:
            previous_time = _parsed_timestamp(
                resolution.selected_amendment.record.field("created_at"),
                "selected Amendment created_at",
            )
            if amendment_time < previous_time:
                raise WorkflowPrerequisiteError(
                    "Amendment cannot precede the selected Amendment head"
                )

        all_amendments = self.repository.list_work_records(
            work, "amendment", version=_AMENDMENT_VERSION
        )
        if any(item.record.logical_id == amendment_id for item in all_amendments):
            raise PortiaConflictError("Amendment identity already exists in this work")
        amendment_snapshot = _history_snapshot(resolution.amendments)

        amendment = _build_amendment(
            reference,
            amendment_id=amendment_id,
            previous_amendment_id=previous_id,
            target_updated_at_before=target_updated_at,
            changes=normalized,
            reason_code=reason_code,
            reason_detail=reason_detail,
            created_at=created_at,
            created_by=created_by,
        )
        candidate = _amended_candidate(
            prior.record,
            normalized,
            amended_at=created_at,
            amended_by=created_by,
        )

        primary_target = _target_journal_ref(reference, prior.record)
        amendment_target = _amendment_journal_ref(work, amendment)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(primary_target, "block_work_writes")
        self.quarantine.require_allowed(amendment_target, "block_work_writes")

        lock_entries, lock_records = _lock_plan(op_id, work, created_at)
        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError("selected Amendment target changed during preflight")
        if prior.record.logical_id is None:
            raise WorkflowOwnershipError("selected Amendment target has no identity")

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        history_path = _target_history_path(
            self.workspace_root,
            work,
            prior.record,
            prior.fingerprint.digest,
        )
        if history_path.exists():
            existing = read_bytes(history_path)
            if existing != prior_bytes or fingerprint_bytes(existing) != prior.fingerprint:
                raise PortiaCorruptionError("Amendment storage-history collision")
        else:
            history_step = "step_history"
            candidates[history_step] = prior_bytes
            steps.append(
                {
                    "step_id": history_step,
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": {"kind": "workspace"},
                    "representation_role": "operational_revision",
                    "destination_path": workspace_relative(
                        self.workspace_root, history_path
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": prior.record.contract_version,
                        "fingerprint": prior.fingerprint.to_dict(),
                        "selected_state": [
                            _state_fact("record_kind", prior.record.contract)
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": "preserve_prior_revision",
                }
            )

        amendment_step = "step_amendment"
        amendment_bytes = canonical_json_bytes(amendment.to_dict())
        candidates[amendment_step] = amendment_bytes
        steps.append(
            {
                "step_id": amendment_step,
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": amendment_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_record_path(
                        self.workspace_root, work, "amendment", amendment_id
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": _AMENDMENT_VERSION,
                    "fingerprint": fingerprint_bytes(amendment_bytes).to_dict(),
                    "selected_state": [_state_fact("record_kind", "amendment")],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": reason_code,
            }
        )

        target_step = "step_target"
        candidate_bytes = canonical_json_bytes(candidate.to_dict())
        candidates[target_step] = candidate_bytes
        steps.append(
            {
                "step_id": target_step,
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": primary_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root, prior.path
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": prior.record.contract_version,
                    "semantic_checks": [
                        _state_fact("record_kind", prior.record.contract)
                    ],
                },
                "intended_result": {
                    "contract_version": candidate.contract_version,
                    "fingerprint": fingerprint_bytes(candidate_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("record_kind", candidate.contract)
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": "amendment_applied",
            }
        )

        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=created_at,
            initiated_by=created_by,
            primary_target=primary_target,
            amendment_target=amendment_target,
            lock_entries=lock_entries,
            steps=steps,
            contract=prior.record.contract,
            amendment_id=amendment_id,
        )
        journal = parse_portia_record("operation_journal", "2", plan)
        store = OperationJournalStore(self.workspace_root)
        support = self._operation_support()
        try:
            current = store.load_current(op_id)
        except PortiaNotFoundError:
            current = store.create(journal, support._pointer(op_id, 1))
        else:
            current_data = current.revision.to_dict()
            if current_data.get("intent_digest") != digest:
                raise PortiaConflictError(
                    "operation identity is already bound to different Amendment intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing Amendment operation requires explicit #38 recovery"
                )

        staged = stage_journaled_candidates(
            self.workspace_root,
            plan,
            candidates,
            fault_hook=fault_hook,
        )
        work_lock_id = derive_lock_id("work", work_target(work))

        def commit_fault_hook(event: str, identifier: str | None) -> None:
            if event == "after_lock_acquire" and identifier == work_lock_id:
                _require_locked_preflight_state(
                    self.repository,
                    reference,
                    expected_target=expected,
                    expected_amendments=amendment_snapshot,
                    amendment_id=amendment_id,
                )
            if fault_hook is not None:
                fault_hook(event, identifier)

        try:
            result = commit_journaled_candidates(
                self.workspace_root,
                plan,
                staged,
                lock_records,
                fault_hook=commit_fault_hook,
            )
        except PortiaOperationPartialCommitError as exc:
            support._record_partial_commit(
                plan, current, exc, lock_records, staged
            )
            raise
        except Exception:
            for artifact in staged:
                cleanup_staged(self.workspace_root, artifact)
            raise

        try:
            accepted_amendment = self.repository.load_work_record(
                work, "amendment", _AMENDMENT_VERSION, amendment_id
            )
            if accepted_amendment.record.to_dict() != amendment.to_dict():
                raise PortiaCorruptionError("accepted Amendment readback changed")
            accepted_target = _load_target(self, reference)
            if accepted_target.record.to_dict() != candidate.to_dict():
                raise PortiaCorruptionError("accepted Amendment target readback changed")
            reconciled = self.require_reconciled(reference)
            if reconciled.selected_amendment_id != amendment_id:
                raise PortiaCorruptionError(
                    "accepted Amendment does not select the expected history head"
                )
        except Exception as exc:
            partial = PortiaOperationPartialCommitError(
                operation_id=op_id,
                accepted_steps=result.accepted_steps,
                held_lock_ids=(),
            )
            support._record_partial_commit(
                plan, current, partial, lock_records, staged
            )
            raise partial from exc

        support._complete_journal(plan, current, result, lock_records)
        for artifact in staged:
            cleanup_staged(self.workspace_root, artifact)
        return result

