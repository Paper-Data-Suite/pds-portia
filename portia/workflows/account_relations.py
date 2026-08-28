"""Exact same-work Account lineage and represented-source checks."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    ACCOUNT_READ_VERSIONS,
    require_evidence_record_owner,
    require_supported_evidence_version,
)


def _source_identity(account: PortiaRecord) -> tuple[object, ...]:
    source = account.field("source")
    if not isinstance(source, Mapping):
        raise WorkflowOwnershipError("Account source attribution is malformed")
    kind = source.get("kind")
    if kind == "roster_student":
        reference = source.get("roster_student_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Account roster source reference is malformed")
        class_id = reference.get("class_id")
        student_id = reference.get("student_id")
        if not isinstance(class_id, str) or not isinstance(student_id, str):
            raise WorkflowOwnershipError("Account roster source identity is incomplete")
        return (kind, class_id, student_id)
    if kind == "actor":
        reference = source.get("actor_ref")
        if not isinstance(reference, Mapping) or not isinstance(
            reference.get("actor_id"), str
        ):
            raise WorkflowOwnershipError("Account Actor source identity is incomplete")
        return (kind, reference["actor_id"])
    if kind == "local_operator":
        label = source.get("display_label")
        if not isinstance(label, str):
            raise WorkflowOwnershipError("Account local-operator source is incomplete")
        return (kind, label)
    if kind == "descriptive_person":
        description_type = source.get("description_type")
        label = source.get("display_label")
        detail = source.get("detail")
        if not isinstance(description_type, str) or not isinstance(label, str):
            raise WorkflowOwnershipError("Account descriptive source is incomplete")
        if detail is not None and not isinstance(detail, str):
            raise WorkflowOwnershipError("Account descriptive source detail is malformed")
        return (kind, description_type, label, detail)
    if kind == "unidentified_person":
        raise WorkflowPrerequisiteError(
            "same-source Account lineage cannot establish unidentified-person identity"
        )
    raise WorkflowOwnershipError("Account source uses an unsupported attribution branch")


def require_same_represented_source(
    left: PortiaRecord,
    right: PortiaRecord,
) -> None:
    """Require source identity without using display snapshots as authority."""
    if _source_identity(left) != _source_identity(right):
        raise WorkflowPrerequisiteError(
            "Account lineage requires the same represented source"
        )


def require_account_relation_semantics(
    account: PortiaRecord,
    *,
    allow_retracts: bool,
) -> None:
    """Enforce Account relation semantics that do not require repository reads."""
    relations = account.field("related_accounts")
    if relations is None:
        return
    if not isinstance(relations, tuple):
        raise WorkflowOwnershipError("Account related_accounts is malformed")

    reports_from = False
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise WorkflowOwnershipError("Account relation is malformed")
        relation_kind = relation.get("relation")
        if relation_kind not in {"reports_from", "clarifies", "retracts"}:
            raise WorkflowOwnershipError("Account relation kind is unsupported")
        if relation_kind == "reports_from":
            reports_from = True
        if relation_kind == "retracts" and not allow_retracts:
            raise WorkflowPrerequisiteError(
                "retracts relation requires the source-evidenced retraction workflow"
            )

    if reports_from and account.field("information_origin") not in {
        "secondhand",
        "mixed",
    }:
        raise WorkflowPrerequisiteError(
            "reports_from requires secondhand or mixed information_origin"
        )


def account_relation_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    account: PortiaRecord,
    *,
    allow_retracts: bool = True,
) -> tuple[StoredRecord, ...]:
    """Resolve and validate exact same-work related_accounts references."""
    require_evidence_record_owner(work, account, contract="account")
    require_account_relation_semantics(account, allow_retracts=allow_retracts)
    relations = account.field("related_accounts")
    if relations is None:
        return ()
    if not isinstance(relations, tuple):
        raise WorkflowOwnershipError("Account related_accounts is malformed")

    resolved: list[StoredRecord] = []
    seen_ids: set[str] = set()
    for relation in relations:
        if not isinstance(relation, Mapping):
            raise WorkflowOwnershipError("Account relation is malformed")
        relation_kind = relation.get("relation")
        reference = relation.get("account_ref")
        if relation_kind not in {"reports_from", "clarifies", "retracts"}:
            raise WorkflowOwnershipError("Account relation kind is unsupported")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Account relation reference is malformed")
        if reference.get("record_kind") != "account":
            raise WorkflowOwnershipError("Account relation names the wrong record family")
        record_id = reference.get("record_id")
        version = reference.get("contract_version")
        if not isinstance(record_id, str) or not isinstance(version, str):
            raise WorkflowOwnershipError("Account relation reference is not exact")
        require_supported_evidence_version(
            work,
            contract="account",
            version=version,
            supported_versions=ACCOUNT_READ_VERSIONS,
        )
        if record_id == account.logical_id:
            raise WorkflowPrerequisiteError("Account relation cannot reference itself")
        if record_id in seen_ids:
            raise WorkflowPrerequisiteError(
                "Account relations cannot repeat one logical Account target"
            )
        seen_ids.add(record_id)
        stored = repository.load_work_record(work, "account", version, record_id)
        if relation_kind in {"clarifies", "retracts"}:
            require_same_represented_source(account, stored.record)
        resolved.append(stored)
    return tuple(resolved)


def account_relation_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    account: PortiaRecord,
    *,
    allow_root_retracts: bool = True,
) -> tuple[StoredRecord, ...]:
    """Resolve a bounded transitive Account-relation graph exactly."""
    values: list[StoredRecord] = []
    visited: set[tuple[str, str]] = set()
    root_id = account.logical_id
    visiting: set[tuple[str, str]] = set()
    if root_id is not None:
        visiting.add((account.contract_version, root_id))

    def visit(record: PortiaRecord, *, allow_retracts: bool) -> None:
        for stored in account_relation_records(
            repository,
            work,
            record,
            allow_retracts=allow_retracts,
        ):
            identifier = stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "related Account has no canonical logical identity"
                )
            key = (stored.record.contract_version, identifier)
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Account relation ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Account relation ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(stored)
            visit(stored.record, allow_retracts=True)
            visiting.remove(key)
            visited.add(key)

    visit(account, allow_retracts=allow_root_retracts)
    return tuple(values)
