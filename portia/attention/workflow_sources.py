"""Work-local Follow-Up schedule and workflow-attention sources for Issue #49.

This slice deliberately remains exact-work-local. Broader workspace/class/work
orchestration and partial/unavailable aggregation belong to Issue #49 Slice 5.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from portia.attention.models import (
    FollowUpScheduleItem,
    FollowUpScheduleQuery,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    build_attention_report,
)
from portia.attention.taxonomy import require_attention_definition
from portia.attention.timing import classify_follow_up_timing
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaCorruptionError
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.downstream_common import follow_up_reference
from portia.workflows.follow_ups import FollowUpWorkflowService
from portia.workflows.judgment_evidence import ModuleJudgmentEvidenceAuthority
from portia.workflows.reviews import ReviewWorkflowService, review_reference

_OPERATIONAL_FOLLOW_UP_STATES: Final[frozenset[str]] = frozenset(
    {"scheduled", "in_progress"}
)
_TERMINAL_FOLLOW_UP_STATES: Final[frozenset[str]] = frozenset(
    {"completed", "cancelled", "unable_to_complete"}
)
_INCOMPLETE_REVIEW_STATES: Final[frozenset[str]] = frozenset(
    {"open", "in_review", "awaiting_information"}
)
_TERMINAL_REVIEW_STATES: Final[frozenset[str]] = frozenset(
    {"completed", "cancelled"}
)


@dataclass(frozen=True, slots=True)
class _CurrentFollowUpEntry:
    item: FollowUpScheduleItem
    workflow_state: str


def _require_exact_work_scope(
    query: FollowUpScheduleQuery | PortiaAttentionQuery,
) -> ExactPortiaWorkRef:
    scope = query.scope
    if scope.kind != "work" or scope.work_ref is None:
        raise PortiaLocalValidationError(
            "work-local attention source requires exact work scope"
        )
    return scope.work_ref


def _record_id(stored: StoredRecord, *, contract: str) -> str:
    identifier = stored.record.logical_id
    if stored.record.contract != contract or not isinstance(identifier, str):
        raise PortiaCorruptionError(
            f"canonical {contract} record has incomplete exact identity"
        )
    return identifier


def _work_matches_school_year(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    active_school_year: str | None,
) -> bool:
    root = repository.load_work(work)
    if active_school_year is None:
        return True
    return root.record.field("school_year") == active_school_year


def _schedule_sort_key(
    entry: _CurrentFollowUpEntry,
) -> tuple[object, ...]:
    reference = entry.item.source_ref
    return (
        entry.item.timing.deterministic_key(),
        reference.work_ref.class_id,
        reference.work_ref.work_kind,
        reference.work_ref.work_id,
        reference.work_ref.contract_version,
        reference.record_ref.record_id,
        reference.record_ref.contract_version,
    )


def _query_wants_code(query: PortiaAttentionQuery, code: str) -> bool:
    definition = require_attention_definition(code)
    if query.attention_codes and code not in query.attention_codes:
        return False
    if (
        query.attention_classes
        and definition.attention_class not in query.attention_classes
    ):
        return False
    return True


class FollowUpScheduleQueryService:
    """Evaluate current operational Follow-Ups in one exact work scope."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.quarantine = quarantine
        self.contexts = context_assembler

    def _entries(
        self,
        query: FollowUpScheduleQuery,
    ) -> tuple[_CurrentFollowUpEntry, ...]:
        if not isinstance(query, FollowUpScheduleQuery):
            raise TypeError("query must be a FollowUpScheduleQuery")
        work = _require_exact_work_scope(query)
        if not _work_matches_school_year(
            self.repository,
            work,
            query.active_school_year,
        ):
            return ()

        service = FollowUpWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        entries: list[_CurrentFollowUpEntry] = []
        for stored in service.list_follow_ups(work):
            if stored.record.status != "active":
                continue

            identifier = _record_id(stored, contract="follow_up")
            reference = follow_up_reference(work, identifier)
            current = service.require_current_use(reference)
            workflow_state = current.record.field("workflow_state")
            if not isinstance(workflow_state, str):
                raise PortiaCorruptionError(
                    "current Follow-Up workflow_state is malformed"
                )
            if workflow_state in _TERMINAL_FOLLOW_UP_STATES:
                continue
            if workflow_state not in _OPERATIONAL_FOLLOW_UP_STATES:
                raise PortiaCorruptionError(
                    "current Follow-Up has unsupported workflow_state"
                )

            raw_timing = current.record.field("planned_timing")
            if not isinstance(raw_timing, Mapping):
                raise PortiaCorruptionError(
                    "current Follow-Up planned_timing is malformed"
                )
            if not all(isinstance(key, str) for key in raw_timing):
                raise PortiaCorruptionError(
                    "current Follow-Up planned_timing keys are malformed"
                )
            planned_timing = {
                key: value
                for key, value in raw_timing.items()
                if isinstance(key, str)
            }
            timing = classify_follow_up_timing(
                planned_timing,
                as_of=query.as_of,
            )
            entries.append(
                _CurrentFollowUpEntry(
                    item=FollowUpScheduleItem(
                        source_ref=reference,
                        timing=timing,
                    ),
                    workflow_state=workflow_state,
                )
            )

        return tuple(sorted(entries, key=_schedule_sort_key))

    def query(
        self,
        query: FollowUpScheduleQuery,
    ) -> tuple[FollowUpScheduleItem, ...]:
        """Return scheduled/due/overdue current Follow-Ups without mutation."""
        return tuple(entry.item for entry in self._entries(query))


class AttentionQueryService:
    """Slice-2 attention over exact-work Follow-Up and Review sources."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        module_authority: ModuleJudgmentEvidenceAuthority | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.quarantine = quarantine
        self.contexts = context_assembler
        self.module_authority = module_authority
        self.follow_ups = FollowUpScheduleQueryService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _follow_up_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        wants_due = _query_wants_code(query, "portia_follow_up_due")
        wants_overdue = _query_wants_code(query, "portia_follow_up_overdue")
        if not wants_due and not wants_overdue:
            return ()

        schedule_query = FollowUpScheduleQuery(
            scope=query.scope,
            as_of=query.as_of,
            active_school_year=query.active_school_year,
        )
        work = _require_exact_work_scope(query)
        context = PortiaAttentionContext(
            class_id=work.class_id,
            work_ref=work,
        )
        items: list[PortiaAttentionItem] = []
        for entry in self.follow_ups._entries(schedule_query):
            classification = entry.item.timing.classification
            if classification == "scheduled":
                continue
            if classification == "due":
                code = "portia_follow_up_due"
                if not wants_due:
                    continue
            else:
                code = "portia_follow_up_overdue"
                if not wants_overdue:
                    continue
            items.append(
                PortiaAttentionItem(
                    code=code,
                    source_ref=entry.item.source_ref,
                    context=context,
                    reason_codes=(entry.workflow_state,),
                    timing=entry.item.timing,
                )
            )
        return tuple(items)

    def _review_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        if not _query_wants_code(query, "portia_review_incomplete"):
            return ()

        work = _require_exact_work_scope(query)
        if work.work_kind != "event":
            return ()

        service = ReviewWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
            module_authority=self.module_authority,
        )
        context = PortiaAttentionContext(
            class_id=work.class_id,
            work_ref=work,
        )
        items: list[PortiaAttentionItem] = []
        for stored in service.list_reviews(work):
            if stored.record.status != "active":
                continue

            identifier = _record_id(stored, contract="review")
            reference = review_reference(work, identifier)
            current = service.require_current_use(reference)
            review_state = current.record.field("review_state")
            if not isinstance(review_state, str):
                raise PortiaCorruptionError(
                    "current Review review_state is malformed"
                )
            if review_state in _TERMINAL_REVIEW_STATES:
                continue
            if review_state not in _INCOMPLETE_REVIEW_STATES:
                raise PortiaCorruptionError(
                    "current Review has unsupported review_state"
                )
            items.append(
                PortiaAttentionItem(
                    code="portia_review_incomplete",
                    source_ref=reference,
                    context=context,
                    reason_codes=(review_state,),
                )
            )
        return tuple(items)

    def query(self, query: PortiaAttentionQuery) -> PortiaAttentionReport:
        """Evaluate Slice-2 workflow attention for one exact work scope."""
        if not isinstance(query, PortiaAttentionQuery):
            raise TypeError("query must be a PortiaAttentionQuery")
        work = _require_exact_work_scope(query)

        if not _work_matches_school_year(
            self.repository,
            work,
            query.active_school_year,
        ):
            return build_attention_report(query)

        items = (
            *self._follow_up_items(query),
            *self._review_items(query),
        )
        return build_attention_report(query, tuple(items))
