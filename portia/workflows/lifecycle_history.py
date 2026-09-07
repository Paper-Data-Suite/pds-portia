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

from collections.abc import Mapping
from dataclasses import dataclass

from portia.models import PortiaRecord
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRecordRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

_LIFECYCLE_VERSION = "1"
_CORRECTION_VERSION = "1"


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
