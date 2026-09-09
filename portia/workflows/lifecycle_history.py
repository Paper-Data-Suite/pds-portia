"""Read-side lifecycle-history correction selection for exact work records.

``lifecycle_history_correction@1`` is append-only selector evidence.  A correction
never edits an accepted lifecycle transition; instead it names the exact selected
head that is being replaced and either another exact transition head or the
creation baseline.  This module resolves that correction chain without timestamp
winner selection and reduces the surviving lifecycle graph to one exact branch.

Issue #47 intentionally starts this authority with work-record targets.  Work-root
and Actor Directory lifecycle histories have distinct target/persistence shapes
and receive dedicated adapters in later slices rather than being guessed here.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast

from portia.models import PortiaRecord, parse_portia_record
from portia.models.json_values import JsonValue
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
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
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

_LIFECYCLE_VERSION = "1"
_CORRECTION_VERSION = "1"
_CORRECTION_REASON_CODES = frozenset(
    {
        "wrong_target",
        "wrong_predecessor",
        "wrong_from_status",
        "wrong_to_status",
        "wrong_reason",
        "wrong_effective_at",
        "wrong_attribution",
        "duplicate_transition",
        "transition_should_not_exist",
        "multiple_fields_corrected",
        "other",
    }
)


@dataclass(frozen=True, slots=True)
class LifecycleHistoryCorrectionResolution:
    """Selected lifecycle state after applying exact history-correction evidence."""

    reference: ExactPortiaWorkRecordRef
    canonical_status: str
    baseline_status: str | None
    transitions: tuple[StoredRecord, ...]
    corrections: tuple[StoredRecord, ...]
    selected_correction: StoredRecord | None
    selected_head: StoredRecord | None
    selected_status: str | None
    excluded_transition_ids: frozenset[str]

    @property
    def reconciled(self) -> bool:
        """Whether selected corrected history agrees with canonical status."""
        return (
            self.selected_status is None
            or self.selected_status == self.canonical_status
        )


def _target(reference: ExactPortiaWorkRecordRef) -> dict[str, object]:
    return {
        "kind": "local_record",
        "record_ref": reference.record_ref.to_dict(),
    }


def _exact_local_ref(
    value: object,
    *,
    field_name: str,
    record_kind: str,
    nullable: bool = False,
) -> ExactLocalRecordRef | None:
    if value is None:
        if nullable:
            return None
        raise WorkflowOwnershipError(f"{field_name} requires an exact local reference")
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"{field_name} exact reference is malformed")
    try:
        reference = ExactLocalRecordRef.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(
            f"{field_name} exact reference is malformed"
        ) from exc
    if (
        reference.record_kind != record_kind
        or reference.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            f"{field_name} must name exact {record_kind}@1"
        )
    return reference


def _logical_id(stored: StoredRecord, *, description: str) -> str:
    identifier = stored.record.logical_id
    if not isinstance(identifier, str):
        raise WorkflowOwnershipError(f"{description} has no exact identity")
    return identifier


def _correction_previous_id(record: PortiaRecord) -> str | None:
    reference = _exact_local_ref(
        record.field("previous_correction"),
        field_name="lifecycle history previous_correction",
        record_kind="lifecycle_history_correction",
        nullable=True,
    )
    return None if reference is None else reference.record_id


def _transition_previous_id(record: PortiaRecord) -> str | None:
    reference = _exact_local_ref(
        record.field("previous_transition"),
        field_name="lifecycle previous_transition",
        record_kind="lifecycle_transition",
        nullable=True,
    )
    return None if reference is None else reference.record_id


def load_lifecycle_history_corrections(
    repository: PortiaRepository,
    reference: ExactPortiaWorkRecordRef,
) -> tuple[StoredRecord, ...]:
    """Return the exact correction chain in predecessor order, never timestamp order."""
    expected_target = _target(reference)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            reference.work_ref,
            "lifecycle_history_correction",
            version=_CORRECTION_VERSION,
        )
        if stored.record.field("target") == expected_target
    )
    if not selected:
        return ()

    by_id: dict[str, StoredRecord] = {}
    child_by_previous: dict[str, str] = {}
    roots: list[str] = []
    for stored in selected:
        correction_id = _logical_id(stored, description="lifecycle history correction")
        if correction_id in by_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction repeats a correction identity"
            )
        by_id[correction_id] = stored

    for correction_id, stored in by_id.items():
        previous_id = _correction_previous_id(stored.record)
        if previous_id is None:
            roots.append(correction_id)
            continue
        if previous_id == correction_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot name itself as predecessor"
            )
        if previous_id not in by_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction references a missing predecessor"
            )
        if previous_id in child_by_previous:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction chain contains a fork"
            )
        child_by_previous[previous_id] = correction_id

    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "lifecycle history correction chain must contain exactly one root"
        )

    ordered: list[StoredRecord] = []
    visited: set[str] = set()
    current_id = roots[0]
    while True:
        if current_id in visited:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction chain contains a cycle"
            )
        visited.add(current_id)
        ordered.append(by_id[current_id])
        next_id = child_by_previous.get(current_id)
        if next_id is None:
            break
        current_id = next_id

    if len(visited) != len(by_id):
        raise WorkflowPrerequisiteError(
            "lifecycle history correction chain is disconnected"
        )
    return tuple(ordered)


def _transition_records(
    repository: PortiaRepository,
    reference: ExactPortiaWorkRecordRef,
) -> tuple[StoredRecord, ...]:
    expected_target = _target(reference)
    return tuple(
        stored
        for stored in repository.list_work_records(
            reference.work_ref,
            "lifecycle_transition",
            version=_LIFECYCLE_VERSION,
        )
        if stored.record.field("target") == expected_target
    )


@dataclass(frozen=True, slots=True)
class _TransitionGraph:
    by_id: Mapping[str, StoredRecord]
    previous: Mapping[str, str | None]
    children: Mapping[str, tuple[str, ...]]
    baseline_status: str

    def chain_to(self, transition_id: str) -> tuple[str, ...]:
        if transition_id not in self.by_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction references a missing transition head"
            )
        reversed_ids: list[str] = []
        visited: set[str] = set()
        current: str | None = transition_id
        while current is not None:
            if current in visited:
                raise WorkflowPrerequisiteError("lifecycle history contains a cycle")
            visited.add(current)
            reversed_ids.append(current)
            current = self.previous[current]
        return tuple(reversed(reversed_ids))

    def descendants(self, root_id: str) -> frozenset[str]:
        pending = [root_id]
        found: set[str] = set()
        while pending:
            current = pending.pop()
            if current in found:
                continue
            found.add(current)
            pending.extend(self.children.get(current, ()))
        return frozenset(found)


def _transition_graph(transitions: tuple[StoredRecord, ...]) -> _TransitionGraph:
    if not transitions:
        raise WorkflowPrerequisiteError(
            "lifecycle history correction requires persisted lifecycle transitions"
        )

    by_id: dict[str, StoredRecord] = {}
    previous: dict[str, str | None] = {}
    children_lists: dict[str, list[str]] = {}
    for stored in transitions:
        transition_id = _logical_id(stored, description="lifecycle transition")
        if transition_id in by_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history repeats a transition identity"
            )
        by_id[transition_id] = stored

    for transition_id, stored in by_id.items():
        previous_id = _transition_previous_id(stored.record)
        if previous_id == transition_id:
            raise WorkflowPrerequisiteError(
                "lifecycle transition cannot name itself as predecessor"
            )
        if previous_id is not None and previous_id not in by_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history references a missing predecessor"
            )
        previous[transition_id] = previous_id
        if previous_id is not None:
            children_lists.setdefault(previous_id, []).append(transition_id)

        from_status = stored.record.field("from_status")
        to_status = stored.record.field("to_status")
        if not isinstance(from_status, str) or not isinstance(to_status, str):
            raise WorkflowOwnershipError(
                "lifecycle transition has malformed status evidence"
            )
        if from_status == to_status:
            raise WorkflowPrerequisiteError(
                "lifecycle transition cannot preserve the same status"
            )

    root_ids = [identifier for identifier, value in previous.items() if value is None]
    if not root_ids:
        raise WorkflowPrerequisiteError("lifecycle history contains no creation branch")
    baseline_statuses = {
        str(by_id[identifier].record.field("from_status")) for identifier in root_ids
    }
    if len(baseline_statuses) != 1:
        raise WorkflowPrerequisiteError(
            "lifecycle history branches disagree on creation baseline status"
        )
    baseline_status = next(iter(baseline_statuses))

    for transition_id, previous_id in previous.items():
        if previous_id is None:
            continue
        prior_to = by_id[previous_id].record.field("to_status")
        current_from = by_id[transition_id].record.field("from_status")
        if prior_to != current_from:
            raise WorkflowPrerequisiteError(
                "lifecycle predecessor status does not reconcile with successor"
            )

    graph = _TransitionGraph(
        by_id=by_id,
        previous=previous,
        children={
            identifier: tuple(children)
            for identifier, children in children_lists.items()
        },
        baseline_status=baseline_status,
    )
    for transition_id in by_id:
        graph.chain_to(transition_id)
    return graph


def _correction_head_id(
    record: PortiaRecord,
    field_name: str,
    *,
    nullable: bool = False,
) -> str | None:
    reference = _exact_local_ref(
        record.field(field_name),
        field_name=f"lifecycle history {field_name}",
        record_kind="lifecycle_transition",
        nullable=nullable,
    )
    return None if reference is None else reference.record_id


def _common_prefix_length(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    length = 0
    for left_id, right_id in zip(left, right, strict=False):
        if left_id != right_id:
            break
        length += 1
    return length


def _selected_surviving_head(
    graph: _TransitionGraph,
    excluded_ids: frozenset[str],
) -> StoredRecord | None:
    active_ids = set(graph.by_id) - set(excluded_ids)
    if not active_ids:
        return None

    for identifier in active_ids:
        previous_id = graph.previous[identifier]
        if previous_id is not None and previous_id not in active_ids:
            raise WorkflowPrerequisiteError(
                "selected lifecycle branch depends on excluded history"
            )

    roots = [
        identifier for identifier in active_ids if graph.previous[identifier] is None
    ]
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "corrected lifecycle history must select exactly one root branch"
        )

    active_children: dict[str, tuple[str, ...]] = {}
    for identifier in active_ids:
        children = tuple(
            child for child in graph.children.get(identifier, ()) if child in active_ids
        )
        if len(children) > 1:
            raise WorkflowPrerequisiteError(
                "corrected lifecycle history still contains a selected fork"
            )
        active_children[identifier] = children

    heads = [identifier for identifier in active_ids if not active_children[identifier]]
    if len(heads) != 1:
        raise WorkflowPrerequisiteError(
            "corrected lifecycle history must contain exactly one selected head"
        )

    visited: set[str] = set()
    current = roots[0]
    while True:
        if current in visited:
            raise WorkflowPrerequisiteError(
                "corrected lifecycle history contains a cycle"
            )
        visited.add(current)
        children = active_children[current]
        if not children:
            break
        current = children[0]
    if visited != active_ids:
        raise WorkflowPrerequisiteError(
            "corrected lifecycle history contains disconnected selected evidence"
        )
    return graph.by_id[heads[0]]


def resolve_corrected_lifecycle_history(
    repository: PortiaRepository,
    reference: ExactPortiaWorkRecordRef,
    *,
    canonical_status: str,
    corrections: tuple[StoredRecord, ...],
) -> LifecycleHistoryCorrectionResolution:
    """Apply an exact correction chain and select one surviving lifecycle branch."""
    if not corrections:
        raise WorkflowPrerequisiteError(
            "corrected lifecycle resolution requires correction evidence"
        )
    transitions = _transition_records(repository, reference)
    graph = _transition_graph(transitions)

    excluded_roots: set[str] = set()
    excluded_ids: frozenset[str] = frozenset()
    for stored in corrections:
        replaced_id = _correction_head_id(stored.record, "replaced_head")
        replacement_id = _correction_head_id(
            stored.record,
            "replacement_head",
            nullable=True,
        )
        if replaced_id is None:
            raise AssertionError("required replaced_head resolved to None")
        if replacement_id == replaced_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot replace a head with itself"
            )
        if replaced_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot replace an already excluded branch"
            )
        if replacement_id is not None and replacement_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot select an already excluded branch"
            )

        replaced_chain = graph.chain_to(replaced_id)
        if replacement_id is None:
            common_length = 0
        else:
            replacement_chain = graph.chain_to(replacement_id)
            common_length = _common_prefix_length(replaced_chain, replacement_chain)
            replaced_root = graph.by_id[replaced_chain[0]].record.field("from_status")
            replacement_root = graph.by_id[replacement_chain[0]].record.field(
                "from_status"
            )
            if common_length == 0 and replaced_root != replacement_root:
                raise WorkflowPrerequisiteError(
                    "lifecycle correction branches do not share a creation baseline"
                )

        if common_length < len(replaced_chain):
            excluded_roots.add(replaced_chain[common_length])
        excluded: set[str] = set()
        for root_id in excluded_roots:
            excluded.update(graph.descendants(root_id))
        excluded_ids = frozenset(excluded)

        if replacement_id is not None and replacement_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history replacement branch was excluded by correction"
            )

    selected_head = _selected_surviving_head(graph, excluded_ids)
    if selected_head is None:
        selected_status = graph.baseline_status
    else:
        value = selected_head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected corrected lifecycle head has malformed to_status"
            )
        selected_status = value

    final_replacement_id = _correction_head_id(
        corrections[-1].record,
        "replacement_head",
        nullable=True,
    )
    if final_replacement_id is not None:
        if selected_head is None:
            raise WorkflowPrerequisiteError(
                "corrected lifecycle replacement head is not selected"
            )
        selected_head_id = _logical_id(
            selected_head,
            description="selected corrected lifecycle head",
        )
        if final_replacement_id not in graph.chain_to(selected_head_id):
            raise WorkflowPrerequisiteError(
                "selected lifecycle head does not extend the final replacement branch"
            )

    return LifecycleHistoryCorrectionResolution(
        reference=reference,
        canonical_status=canonical_status,
        baseline_status=graph.baseline_status,
        transitions=transitions,
        corrections=corrections,
        selected_correction=corrections[-1],
        selected_head=selected_head,
        selected_status=selected_status,
        excluded_transition_ids=excluded_ids,
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


def _correction_reason(
    reason_code: str,
    reason_detail: str | None,
) -> dict[str, object]:
    if reason_code not in _CORRECTION_REASON_CODES:
        raise WorkflowPrerequisiteError(
            f"unsupported lifecycle-history correction reason: {reason_code!r}"
        )
    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction reason 'other' requires detail"
            )
        return {"code": "other", "detail": reason_detail}
    value: dict[str, object] = {"code": reason_code}
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction reason detail cannot be empty"
            )
        value["detail"] = reason_detail
    return value


def _transition_ref(identifier: str) -> dict[str, object]:
    return ExactLocalRecordRef(
        record_kind="lifecycle_transition",
        record_id=identifier,
        contract_version=_LIFECYCLE_VERSION,
    ).to_dict()


def _correction_ref(identifier: str) -> dict[str, object]:
    return ExactLocalRecordRef(
        record_kind="lifecycle_history_correction",
        record_id=identifier,
        contract_version=_CORRECTION_VERSION,
    ).to_dict()


def _correction_excluded_ids(
    graph: _TransitionGraph,
    corrections: tuple[PortiaRecord, ...],
) -> frozenset[str]:
    """Apply correction selectors without requiring the surviving graph to be linear.

    Slice 4 needs this bounded view because the replacement branch is deliberately
    already durable before its selector is written.  During that interval the raw
    transition graph may contain exactly the old selected branch and the complete
    proposed replacement branch.  Ordinary family readers remain strict about that
    fork and are not weakened merely to plan this maintenance operation.
    """
    excluded_roots: set[str] = set()
    excluded_ids: frozenset[str] = frozenset()
    for record in corrections:
        replaced_id = _correction_head_id(record, "replaced_head")
        replacement_id = _correction_head_id(
            record,
            "replacement_head",
            nullable=True,
        )
        if replaced_id is None:
            raise AssertionError("required replaced_head resolved to None")
        if replacement_id == replaced_id:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot replace a head with itself"
            )
        if replaced_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot replace an already excluded branch"
            )
        if replacement_id is not None and replacement_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history correction cannot select an already excluded branch"
            )

        replaced_chain = graph.chain_to(replaced_id)
        if replacement_id is None:
            common_length = 0
        else:
            replacement_chain = graph.chain_to(replacement_id)
            common_length = _common_prefix_length(replaced_chain, replacement_chain)
            replaced_root = graph.by_id[replaced_chain[0]].record.field("from_status")
            replacement_root = graph.by_id[replacement_chain[0]].record.field(
                "from_status"
            )
            if common_length == 0 and replaced_root != replacement_root:
                raise WorkflowPrerequisiteError(
                    "lifecycle correction branches do not share a creation baseline"
                )

        if common_length < len(replaced_chain):
            excluded_roots.add(replaced_chain[common_length])
        excluded: set[str] = set()
        for root_id in excluded_roots:
            excluded.update(graph.descendants(root_id))
        excluded_ids = frozenset(excluded)
        if replacement_id is not None and replacement_id in excluded_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle history replacement branch was excluded by correction"
            )
    return excluded_ids


def _head_status(graph: _TransitionGraph, transition_id: str) -> str:
    value = graph.by_id[transition_id].record.field("to_status")
    if not isinstance(value, str):
        raise WorkflowOwnershipError(
            "lifecycle transition head has malformed to_status"
        )
    return value


def _preview_correction_selection(
    repository: PortiaRepository,
    reference: ExactPortiaWorkRecordRef,
    *,
    canonical_status: str,
    prior_corrections: tuple[StoredRecord, ...],
    correction: PortiaRecord,
) -> str:
    """Validate one append over an already-complete replacement branch.

    The pre-correction active graph must contain exactly two explicit alternatives
    (or one branch when selecting the creation baseline): the exact currently
    selected head named by ``replaced_head`` and the complete replacement head.
    This makes the temporarily forked state bounded and prevents a correction from
    silently choosing among unrelated or third-party branches.
    """
    transitions = _transition_records(repository, reference)
    graph = _transition_graph(transitions)
    prior_records = tuple(item.record for item in prior_corrections)
    prior_excluded = _correction_excluded_ids(graph, prior_records)
    active_ids = set(graph.by_id) - set(prior_excluded)

    replaced_id = _correction_head_id(correction, "replaced_head")
    replacement_id = _correction_head_id(
        correction,
        "replacement_head",
        nullable=True,
    )
    if replaced_id is None:
        raise AssertionError("required replaced_head resolved to None")
    if replaced_id not in active_ids:
        raise WorkflowPrerequisiteError(
            "lifecycle-history correction replaced head is not active selected history"
        )
    if replacement_id == replaced_id:
        raise WorkflowPrerequisiteError(
            "lifecycle history correction cannot replace a head with itself"
        )

    replaced_chain = graph.chain_to(replaced_id)
    if any(identifier not in active_ids for identifier in replaced_chain):
        raise WorkflowPrerequisiteError(
            "lifecycle-history correction replaced branch depends on excluded history"
        )
    if any(child in active_ids for child in graph.children.get(replaced_id, ())):
        raise WorkflowPrerequisiteError(
            "lifecycle-history correction replaced_head must be an exact current head"
        )
    if _head_status(graph, replaced_id) != canonical_status:
        raise WorkflowPrerequisiteError(
            "lifecycle-history correction replaced head does not reconcile with "
            "the current canonical status"
        )

    correction_time = _parsed_timestamp(
        correction.field("created_at"),
        "lifecycle-history correction created_at",
    )
    branch_ids = set(replaced_chain)

    if replacement_id is None:
        if active_ids != set(replaced_chain):
            raise WorkflowPrerequisiteError(
                "creation-baseline correction requires exactly the selected "
                "replaced branch"
            )
        selected_status = graph.baseline_status
    else:
        if replacement_id not in active_ids:
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction replacement head is excluded or missing"
            )
        replacement_chain = graph.chain_to(replacement_id)
        branch_ids.update(replacement_chain)
        if any(identifier not in active_ids for identifier in replacement_chain):
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction replacement branch depends on "
                "excluded history"
            )
        if any(child in active_ids for child in graph.children.get(replacement_id, ())):
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction replacement_head must be a complete "
                "branch head"
            )
        common_length = _common_prefix_length(replaced_chain, replacement_chain)
        replaced_root = graph.by_id[replaced_chain[0]].record.field("from_status")
        replacement_root = graph.by_id[replacement_chain[0]].record.field(
            "from_status"
        )
        if common_length == 0 and replaced_root != replacement_root:
            raise WorkflowPrerequisiteError(
                "lifecycle correction branches do not share a creation baseline"
            )
        expected_active = set(replaced_chain) | set(replacement_chain)
        if active_ids != expected_active:
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction replacement branch is not the unique "
                "complete alternative to the replaced branch"
            )
        selected_status = _head_status(graph, replacement_id)

    for transition_id in branch_ids:
        transition_created = _parsed_timestamp(
            graph.by_id[transition_id].record.field("created_at"),
            "lifecycle transition created_at",
        )
        if transition_created > correction_time:
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction cannot precede its selected "
                "transition branches"
            )

    combined = (*prior_records, correction)
    excluded_after = _correction_excluded_ids(graph, combined)
    selected_head = _selected_surviving_head(graph, excluded_after)
    if replacement_id is None:
        if selected_head is not None:
            raise WorkflowPrerequisiteError(
                "creation-baseline correction did not select the creation baseline"
            )
    else:
        if selected_head is None or _logical_id(
            selected_head,
            description="selected corrected lifecycle head",
        ) != replacement_id:
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction did not select the exact replacement head"
            )
    return selected_status


def build_lifecycle_history_correction(
    reference: ExactPortiaWorkRecordRef,
    *,
    correction_id: str,
    previous_correction_id: str | None,
    replaced_head_id: str,
    replacement_head_id: str | None,
    reason_code: str,
    reason_detail: str | None,
    created_at: str,
    created_by: Mapping[str, object],
) -> PortiaRecord:
    """Build one immutable lifecycle_history_correction@1 selector."""
    reason = _correction_reason(reason_code, reason_detail)
    return parse_portia_record(
        "lifecycle_history_correction",
        _CORRECTION_VERSION,
        {
            "schema_version": _CORRECTION_VERSION,
            "record_type": "lifecycle_history_correction",
            "module_id": "portia",
            "class_id": reference.work_ref.class_id,
            "work_id": reference.work_ref.work_id,
            "correction_id": correction_id,
            "target": _target(reference),
            "previous_correction": (
                None
                if previous_correction_id is None
                else _correction_ref(previous_correction_id)
            ),
            "replaced_head": _transition_ref(replaced_head_id),
            "replacement_head": (
                None
                if replacement_head_id is None
                else _transition_ref(replacement_head_id)
            ),
            "reason": reason,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )


def _corrected_canonical_candidate(
    prior: PortiaRecord,
    *,
    selected_status: str,
    corrected_at: str,
    corrected_by: Mapping[str, object],
) -> PortiaRecord:
    if prior.status == selected_status:
        return prior
    data = prior.to_dict()
    data["status"] = selected_status
    data["updated_at"] = corrected_at
    data["updated_by"] = cast(JsonValue, dict(corrected_by))
    return parse_portia_record(prior.contract, prior.contract_version, data)


def _intent_digest(
    prior: PortiaRecord,
    correction: PortiaRecord,
    candidate: PortiaRecord,
) -> str:
    payload = b"".join(
        canonical_json_bytes(record.to_dict())
        for record in (prior, correction, candidate)
    )
    return hashlib.sha256(payload).hexdigest()


def _state_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "token", "value": value}


def _expected_state(step: Mapping[str, object]) -> dict[str, object]:
    precondition = step.get("precondition")
    if not isinstance(precondition, Mapping):
        raise PortiaConflictError("history-correction write step has no precondition")
    presence = precondition.get("presence")
    if presence == "must_be_absent":
        return {"presence": "must_be_absent"}
    if presence != "must_match":
        raise PortiaConflictError(
            "history-correction write precondition is unsupported"
        )
    fingerprint = precondition.get("fingerprint")
    semantic_checks = precondition.get("semantic_checks")
    if not isinstance(fingerprint, Mapping) or not isinstance(semantic_checks, list):
        raise PortiaConflictError(
            "history-correction must-match precondition is incomplete"
        )
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
    affected_targets: list[dict[str, object]],
    lock_entries: list[dict[str, object]],
    steps: list[dict[str, object]],
    prior_status: str,
    selected_status: str,
    contract: str,
) -> dict[str, object]:
    preflight: list[dict[str, object]] = []
    for step in steps:
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            raise PortiaConflictError("history-correction intended result is invalid")
        contract_version = intended.get("contract_version")
        selected_state = intended.get("selected_state")
        destination = step.get("destination_path")
        role = step.get("representation_role")
        target = step.get("target")
        if (
            not isinstance(contract_version, str)
            or not isinstance(selected_state, list)
            or not isinstance(destination, str)
            or not isinstance(role, str)
            or not isinstance(target, dict)
        ):
            raise PortiaConflictError("history-correction write step is incomplete")
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
        "operation_kind": "correct_history",
        "intent_digest": digest,
        "scope": "work",
        "primary_target": primary_target,
        "affected_targets": affected_targets,
        "intent_facts": [
            _state_fact("record_kind", contract),
            _state_fact("from_status", prior_status),
            _state_fact("to_status", selected_status),
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
    targets = (
        ("operation", operation_target),
        ("work", work_target(work)),
    )
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
                "deployment_instance_id": "lifecycle_history_correction",
                "process_instance_id": "lifecycle_history_correction",
            },
        )
    return entries, records


def _correction_target(
    reference: ExactPortiaWorkRecordRef,
    correction_id: str,
) -> dict[str, object]:
    return {
        "kind": "work_record",
        "work_record_ref": ExactPortiaWorkRecordRef(
            work_ref=reference.work_ref,
            record_ref=ExactLocalRecordRef(
                record_kind="lifecycle_history_correction",
                record_id=correction_id,
                contract_version=_CORRECTION_VERSION,
            ),
        ).to_dict(),
    }


def _completed_correction_matches(
    repository: PortiaRepository,
    journal_data: Mapping[str, object],
    reference: ExactPortiaWorkRecordRef,
    *,
    expected: ContentFingerprint,
    correction_id: str,
    replaced_head_id: str,
    replacement_head_id: str | None,
    reason_code: str,
    reason_detail: str | None,
    created_at: str,
    created_by: Mapping[str, object],
) -> bool:
    if journal_data.get("operation_kind") != "correct_history":
        return False
    target = _correction_target(reference, correction_id)
    canonical_target = {
        "kind": "work_record",
        "work_record_ref": reference.to_dict(),
    }
    write_set = journal_data.get("write_set")
    if not isinstance(write_set, list):
        return False
    saw_correction = False
    saw_target_replace = False
    for step in write_set:
        if not isinstance(step, Mapping):
            continue
        if step.get("action") == "exclusive_create" and step.get("target") == target:
            saw_correction = True
        if (
            step.get("action") == "revision_aware_replace"
            and step.get("target") == canonical_target
        ):
            precondition = step.get("precondition")
            if not isinstance(precondition, Mapping):
                return False
            try:
                if (
                    ContentFingerprint.from_dict(precondition.get("fingerprint"))
                    != expected
                ):
                    return False
            except ValueError:
                return False
            saw_target_replace = True
    if not saw_correction:
        return False
    try:
        persisted = repository.load_work_record(
            reference.work_ref,
            "lifecycle_history_correction",
            _CORRECTION_VERSION,
            correction_id,
        )
    except Exception:
        return False
    expected_reason = _correction_reason(reason_code, reason_detail)
    expected_previous = persisted.record.field("previous_correction")
    expected_record = parse_portia_record(
        "lifecycle_history_correction",
        _CORRECTION_VERSION,
        {
            "schema_version": _CORRECTION_VERSION,
            "record_type": "lifecycle_history_correction",
            "module_id": "portia",
            "class_id": reference.work_ref.class_id,
            "work_id": reference.work_ref.work_id,
            "correction_id": correction_id,
            "target": _target(reference),
            "previous_correction": expected_previous,
            "replaced_head": _transition_ref(replaced_head_id),
            "replacement_head": (
                None
                if replacement_head_id is None
                else _transition_ref(replacement_head_id)
            ),
            "reason": expected_reason,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )
    if persisted.record.to_dict() != expected_record.to_dict():
        return False
    if not saw_target_replace:
        try:
            current = repository.load_work_record(
                reference.work_ref,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        except Exception:
            return False
        if current.fingerprint != expected:
            return False
    return True


def _history_snapshot(
    records: tuple[StoredRecord, ...],
) -> tuple[tuple[str, ContentFingerprint], ...]:
    values: list[tuple[str, ContentFingerprint]] = []
    for stored in records:
        values.append(
            (
                _logical_id(stored, description="lifecycle history artifact"),
                stored.fingerprint,
            )
        )
    return tuple(sorted(values, key=lambda item: item[0]))


def _require_locked_preflight_state(
    repository: PortiaRepository,
    reference: ExactPortiaWorkRecordRef,
    *,
    expected_target: ContentFingerprint,
    expected_transitions: tuple[tuple[str, ContentFingerprint], ...],
    expected_corrections: tuple[tuple[str, ContentFingerprint], ...],
    correction_id: str,
) -> None:
    """Re-check append-only history after the work lock is held."""
    current = repository.load_work_record(
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )
    if current.fingerprint != expected_target:
        raise PortiaConflictError(
            "lifecycle-history target changed after correction preflight"
        )
    transitions = _history_snapshot(_transition_records(repository, reference))
    if transitions != expected_transitions:
        raise PortiaConflictError(
            "lifecycle transition history changed after correction preflight"
        )
    corrections = _history_snapshot(
        load_lifecycle_history_corrections(repository, reference)
    )
    if corrections != expected_corrections:
        raise PortiaConflictError(
            "lifecycle-history correction chain changed after preflight"
        )
    try:
        repository.load_work_record(
            reference.work_ref,
            "lifecycle_history_correction",
            _CORRECTION_VERSION,
            correction_id,
        )
    except PortiaNotFoundError:
        pass
    else:
        raise PortiaConflictError(
            "lifecycle-history correction identity appeared after preflight"
        )


class LifecycleHistoryCorrectionCoordinator(WorkflowServiceBase):
    """Journal and commit one exact lifecycle-history correction selector."""

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

    def _completed_replay(
        self,
        operation_id: str | None,
        reference: ExactPortiaWorkRecordRef,
        *,
        expected: ContentFingerprint,
        correction_id: str,
        replaced_head_id: str,
        replacement_head_id: str | None,
        reason_code: str,
        reason_detail: str | None,
        created_at: str,
        created_by: Mapping[str, object],
    ) -> OperationCommitResult | None:
        if operation_id is None:
            return None
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            return None
        data = current.revision.to_dict()
        state = data.get("state")
        if state == "completed":
            if not _completed_correction_matches(
                self.repository,
                data,
                reference,
                expected=expected,
                correction_id=correction_id,
                replaced_head_id=replaced_head_id,
                replacement_head_id=replacement_head_id,
                reason_code=reason_code,
                reason_detail=reason_detail,
                created_at=created_at,
                created_by=created_by,
            ):
                raise PortiaConflictError(
                    "completed lifecycle-history correction operation identity is "
                    "bound to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing lifecycle-history correction operation requires "
                "explicit #38 recovery"
            )
        return None

    def commit(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        expected: ContentFingerprint,
        correction_id: str,
        replaced_head_id: str,
        replacement_head_id: str | None,
        reason_code: str,
        created_at: str,
        created_by: Mapping[str, object],
        reason_detail: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Select a complete replacement branch and reconcile canonical status."""
        replay = self._completed_replay(
            operation_id,
            reference,
            expected=expected,
            correction_id=correction_id,
            replaced_head_id=replaced_head_id,
            replacement_head_id=replacement_head_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            created_at=created_at,
            created_by=created_by,
        )
        if replay is not None:
            return replay

        work = reference.work_ref
        prior = self.repository.load_work_record(
            work,
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected lifecycle-history target state does not match selected "
                "canonical bytes"
            )
        canonical_status = prior.record.status
        if not isinstance(canonical_status, str):
            raise WorkflowOwnershipError(
                "lifecycle-history correction target has no canonical status"
            )
        prior_data = prior.record.to_dict()
        prior_updated = prior_data.get("updated_at")
        if not isinstance(prior_updated, str):
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction target update provenance is incomplete"
            )
        correction_time = _parsed_timestamp(
            created_at, "history correction created_at"
        )
        selected_update_time = _parsed_timestamp(
            prior_updated, "selected canonical updated_at"
        )
        if correction_time < selected_update_time:
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction cannot precede the selected "
                "canonical revision"
            )
        if not isinstance(created_by, Mapping):
            raise WorkflowPrerequisiteError(
                "lifecycle-history correction attribution is incomplete"
            )

        prior_corrections = load_lifecycle_history_corrections(
            self.repository,
            reference,
        )
        all_corrections = self.repository.list_work_records(
            work,
            "lifecycle_history_correction",
            version=_CORRECTION_VERSION,
        )
        if any(item.record.logical_id == correction_id for item in all_corrections):
            raise PortiaConflictError(
                "lifecycle-history correction identity already exists in this work"
            )
        previous_correction_id: str | None = None
        if prior_corrections:
            previous = prior_corrections[-1]
            previous_correction_id = _logical_id(
                previous,
                description="selected lifecycle history correction",
            )
            previous_time = _parsed_timestamp(
                previous.record.field("created_at"),
                "selected lifecycle-history correction created_at",
            )
            if correction_time < previous_time:
                raise WorkflowPrerequisiteError(
                    "lifecycle-history correction cannot precede the selected "
                    "correction head"
                )
        transition_snapshot = _history_snapshot(
            _transition_records(self.repository, reference)
        )
        correction_snapshot = _history_snapshot(prior_corrections)

        correction = build_lifecycle_history_correction(
            reference,
            correction_id=correction_id,
            previous_correction_id=previous_correction_id,
            replaced_head_id=replaced_head_id,
            replacement_head_id=replacement_head_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            created_at=created_at,
            created_by=created_by,
        )
        selected_status = _preview_correction_selection(
            self.repository,
            reference,
            canonical_status=canonical_status,
            prior_corrections=prior_corrections,
            correction=correction,
        )
        candidate = _corrected_canonical_candidate(
            prior.record,
            selected_status=selected_status,
            corrected_at=created_at,
            corrected_by=created_by,
        )

        target = record_target(work, prior.record)
        correction_target = record_target(work, correction)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(target, "block_work_writes")
        self.quarantine.require_allowed(correction_target, "block_work_writes")

        digest = _intent_digest(prior.record, correction, candidate)
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, created_at)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected lifecycle-history target changed during preflight"
            )
        if prior.record.logical_id is None:
            raise WorkflowOwnershipError(
                "selected lifecycle-history target has no canonical identity"
            )

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        status_changed = candidate.to_dict() != prior.record.to_dict()
        if status_changed:
            history_path = work_storage_history_path(
                self.workspace_root,
                work,
                prior.record.contract,
                prior.record.logical_id,
                prior.fingerprint.digest,
            )
            if history_path.exists():
                existing = read_bytes(history_path)
                if (
                    existing != prior_bytes
                    or fingerprint_bytes(existing) != prior.fingerprint
                ):
                    raise PortiaCorruptionError(
                        "lifecycle-history correction storage-history collision"
                    )
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
                            self.workspace_root,
                            history_path,
                        ),
                        "precondition": {"presence": "must_be_absent"},
                        "intended_result": {
                            "contract_version": prior.record.contract_version,
                            "fingerprint": prior.fingerprint.to_dict(),
                            "selected_state": [
                                _state_fact("status", canonical_status)
                            ],
                        },
                        "disposition": "staged",
                        "observed_result": None,
                        "compensation_step_id": None,
                        "reason_code": "preserve_prior_revision",
                    }
                )

        correction_step = "step_correction"
        correction_bytes = canonical_json_bytes(correction.to_dict())
        candidates[correction_step] = correction_bytes
        steps.append(
            {
                "step_id": correction_step,
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": correction_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_record_path(
                        self.workspace_root,
                        work,
                        "lifecycle_history_correction",
                        correction_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": _CORRECTION_VERSION,
                    "fingerprint": fingerprint_bytes(correction_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("record_kind", "lifecycle_history_correction")
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": reason_code,
            }
        )

        if status_changed:
            target_step = "step_target"
            candidate_bytes = canonical_json_bytes(candidate.to_dict())
            candidates[target_step] = candidate_bytes
            steps.append(
                {
                    "step_id": target_step,
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "revision_aware_replace",
                    "target": target,
                    "representation_role": "canonical_domain",
                    "destination_path": workspace_relative(
                        self.workspace_root,
                        prior.path,
                    ),
                    "precondition": {
                        "presence": "must_match",
                        "fingerprint": prior.fingerprint.to_dict(),
                        "contract_version": prior.record.contract_version,
                        "semantic_checks": [
                            _state_fact("status", canonical_status)
                        ],
                    },
                    "intended_result": {
                        "contract_version": candidate.contract_version,
                        "fingerprint": fingerprint_bytes(candidate_bytes).to_dict(),
                        "selected_state": [
                            _state_fact("status", selected_status)
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": "history_corrected",
                }
            )

        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=created_at,
            initiated_by=created_by,
            primary_target=target,
            affected_targets=[correction_target],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=canonical_status,
            selected_status=selected_status,
            contract=prior.record.contract,
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
                    "operation identity is already bound to different "
                    "lifecycle-history correction intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing lifecycle-history correction operation requires "
                "explicit #38 recovery"
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
                    expected_transitions=transition_snapshot,
                    expected_corrections=correction_snapshot,
                    correction_id=correction_id,
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
                plan,
                current,
                exc,
                lock_records,
                staged,
            )
            raise
        except Exception:
            for artifact in staged:
                cleanup_staged(self.workspace_root, artifact)
            raise

        try:
            accepted_correction = self.repository.load_work_record(
                work,
                "lifecycle_history_correction",
                _CORRECTION_VERSION,
                correction_id,
            )
            if accepted_correction.record.to_dict() != correction.to_dict():
                raise PortiaCorruptionError(
                    "accepted lifecycle-history correction readback changed"
                )
            accepted_target = self.repository.load_work_record(
                work,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
            if accepted_target.record.to_dict() != candidate.to_dict():
                raise PortiaCorruptionError(
                    "accepted lifecycle-history canonical readback changed"
                )
            accepted_status = accepted_target.record.status
            if not isinstance(accepted_status, str):
                raise PortiaCorruptionError(
                    "accepted lifecycle-history target lost canonical status"
                )
            corrections_after = load_lifecycle_history_corrections(
                self.repository,
                reference,
            )
            resolution = resolve_corrected_lifecycle_history(
                self.repository,
                reference,
                canonical_status=accepted_status,
                corrections=corrections_after,
            )
            selected_correction = resolution.selected_correction
            if (
                selected_correction is None
                or selected_correction.record.logical_id != correction_id
                or resolution.selected_status != selected_status
                or not resolution.reconciled
            ):
                raise PortiaCorruptionError(
                    "accepted lifecycle-history correction does not reconcile "
                    "on readback"
                )
        except Exception as exc:
            partial = PortiaOperationPartialCommitError(
                operation_id=op_id,
                accepted_steps=result.accepted_steps,
                held_lock_ids=(),
            )
            support._record_partial_commit(
                plan,
                current,
                partial,
                lock_records,
                staged,
            )
            raise partial from exc

        support._complete_journal(plan, current, result, lock_records)
        for artifact in staged:
            cleanup_staged(self.workspace_root, artifact)
        return result
