"""Exact cross-year authority for ``support_process@1.continues_from``."""

from __future__ import annotations

from typing import cast

from portia.models import PortiaRecord, SupportProcessV1
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

SUPPORT_PROCESS_VERSION = "1"


def support_process_continuation_predecessor(
    repository: PortiaRepository,
    record: PortiaRecord,
) -> StoredRecord | None:
    """Resolve exactly one continuation predecessor without successor following."""
    if not isinstance(record, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process continuation authority requires support_process@1"
        )
    value = record.field("continues_from")
    if value is None:
        return None

    reference = ExactPortiaWorkRef.from_dict(value)
    if (
        reference.work_kind != "support_process"
        or reference.contract_version != SUPPORT_PROCESS_VERSION
    ):
        raise WorkflowOwnershipError(
            "Support Process continues_from must name exact support_process@1"
        )
    if record.work_id == reference.work_id:
        raise WorkflowPrerequisiteError(
            "cross-year Support Process continuation requires a distinct work_id"
        )

    predecessor = repository.load_work(reference)
    if not isinstance(predecessor.record, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process continues_from resolved a non-support_process@1 root"
        )
    if (
        predecessor.record.class_id != reference.class_id
        or predecessor.record.work_id != reference.work_id
    ):
        raise WorkflowOwnershipError(
            "Support Process continues_from exact predecessor identity mismatches "
            "canonical storage"
        )
    return predecessor


def support_process_continuation_ancestry(
    repository: PortiaRepository,
    record: PortiaRecord,
    *,
    max_depth: int = 128,
) -> tuple[StoredRecord, ...]:
    """Resolve the exact continuation chain, newest predecessor first."""
    if not isinstance(record, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process continuation ancestry requires support_process@1"
        )
    if max_depth < 1:
        raise ValueError("max_depth must be positive")

    current = record
    seen: set[tuple[str, str]] = set()
    if current.class_id is not None and current.work_id is not None:
        seen.add((current.class_id, current.work_id))
    resolved: list[StoredRecord] = []

    for _ in range(max_depth):
        predecessor = support_process_continuation_predecessor(repository, current)
        if predecessor is None:
            return tuple(resolved)
        class_id = predecessor.record.class_id
        work_id = predecessor.record.work_id
        if class_id is None or work_id is None:
            raise WorkflowOwnershipError(
                "Support Process continuation predecessor lacks exact identity"
            )
        exact_key = (class_id, work_id)
        if exact_key in seen:
            raise WorkflowPrerequisiteError(
                "Support Process continues_from chain contains a cycle"
            )
        seen.add(exact_key)
        resolved.append(predecessor)
        current = cast(SupportProcessV1, predecessor.record)

    if support_process_continuation_predecessor(repository, current) is not None:
        raise WorkflowPrerequisiteError(
            "Support Process continues_from ancestry exceeds the 128-record bound"
        )
    return tuple(resolved)
