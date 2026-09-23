"""Follow-Up schedule and native attention orchestration for Issue #49."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from portia.attention.derived_sources import DerivedAttentionSourceService
from portia.attention.models import (
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    FollowUpScheduleItem,
    FollowUpScheduleQuery,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionNotice,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionScope,
    build_attention_report,
)
from portia.attention.operational_sources import (
    OperationalAttentionSourceService,
    UnknownIntegrityAttentionCodeError,
)
from portia.attention.scope import (
    class_exists,
    class_work_refs,
    discover_workspace_classes,
)
from portia.attention.taxonomy import require_attention_definition
from portia.attention.timing import classify_follow_up_timing
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaStorageError,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.dependencies import (
    DependencyConditionEvaluation,
    DependencyWorkflowService,
)
from portia.workflows.downstream_common import follow_up_reference
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.follow_ups import FollowUpWorkflowService
from portia.workflows.judgment_evidence import ModuleJudgmentEvidenceAuthority
from portia.workflows.reviews import ReviewWorkflowService, review_reference
from portia.workflows.support_processes import SupportProcessWorkflowService

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
_OPERATIONAL_SUPPORT_PROCESS_STATES: Final[frozenset[str]] = frozenset(
    {"planning", "active", "paused"}
)
_TERMINAL_SUPPORT_PROCESS_STATES: Final[frozenset[str]] = frozenset(
    {"completed", "discontinued", "cancelled"}
)
_DEPENDENCY_ATTENTION_CONDITIONS: Final[frozenset[str]] = frozenset(
    {"review_required", "unsatisfied", "indeterminate"}
)
_DEPENDENCY_ATTENTION_REASON_ORDER: Final[tuple[str, ...]] = (
    "required_review_required",
    "required_unsatisfied",
    "required_indeterminate",
    "advisory_review_required",
    "advisory_unsatisfied",
    "advisory_indeterminate",
)
_PARTIAL_NOTICE_MESSAGE: Final[str] = (
    "One or more independent Portia attention sources could not be evaluated safely."
)
_UNAVAILABLE_NOTICE_MESSAGE: Final[str] = (
    "The requested Portia attention scope could not be evaluated safely."
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


def _dependency_attention_reason_codes(
    evaluations: Sequence[DependencyConditionEvaluation],
) -> tuple[str, ...]:
    """Collapse Dependency conditions to bounded process-level reason codes."""
    observed: set[str] = set()
    for evaluation in evaluations:
        if evaluation.condition not in _DEPENDENCY_ATTENTION_CONDITIONS:
            continue
        if evaluation.strength not in {"required", "advisory"}:
            raise PortiaCorruptionError(
                "Dependency attention encountered unsupported strength"
            )
        observed.add(f"{evaluation.strength}_{evaluation.condition}")
    return tuple(
        reason
        for reason in _DEPENDENCY_ATTENTION_REASON_ORDER
        if reason in observed
    )


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
        """Return current Follow-Ups in explicit work/class/workspace scope."""
        if not isinstance(query, FollowUpScheduleQuery):
            raise TypeError("query must be a FollowUpScheduleQuery")

        if query.scope.kind == "work":
            entries = list(self._entries(query))
        elif query.scope.kind == "class":
            class_id = query.scope.class_id
            assert class_id is not None
            if not class_exists(self.workspace_root, class_id):
                raise PortiaNotFoundError(
                    "requested Follow-Up schedule class scope does not exist"
                )
            entries = []
            for work in class_work_refs(self.repository, class_id):
                entries.extend(
                    self._entries(
                        FollowUpScheduleQuery(
                            scope=PortiaAttentionScope.work_scope(work),
                            as_of=query.as_of,
                            active_school_year=query.active_school_year,
                        )
                    )
                )
        else:
            discovery = discover_workspace_classes(self.workspace_root)
            if discovery.incomplete:
                raise PortiaCorruptionError(
                    "workspace class discovery is incomplete"
                )
            entries = []
            for class_id in discovery.class_ids:
                for work in class_work_refs(self.repository, class_id):
                    entries.extend(
                        self._entries(
                            FollowUpScheduleQuery(
                                scope=PortiaAttentionScope.work_scope(work),
                                as_of=query.as_of,
                                active_school_year=query.active_school_year,
                            )
                        )
                    )

        return tuple(
            entry.item
            for entry in sorted(entries, key=_schedule_sort_key)
        )


class AttentionQueryService:
    """Native read-only attention over explicit work/class/workspace scope."""

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
        self.operational = OperationalAttentionSourceService(
            self.workspace_root,
            quarantine=self.quarantine,
        )
        self.derived = DerivedAttentionSourceService(
            self.workspace_root,
            operational=self.operational,
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

    def _support_process_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        work = _require_exact_work_scope(query)
        if work.work_kind != "support_process":
            return ()

        wants_due = _query_wants_code(
            query,
            "portia_support_process_review_due",
        )
        wants_overdue = _query_wants_code(
            query,
            "portia_support_process_review_overdue",
        )
        wants_dependency = _query_wants_code(
            query,
            "portia_support_process_dependency_attention",
        )
        if not wants_due and not wants_overdue and not wants_dependency:
            return ()

        support = SupportProcessWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        exact = support.load_exact(work)
        if exact.record.status != "active":
            return ()
        current = support.require_current_use_authority(work)
        workflow_state = current.record.field("workflow_state")
        if not isinstance(workflow_state, str):
            raise PortiaCorruptionError(
                "current Support Process workflow_state is malformed"
            )
        if workflow_state in _TERMINAL_SUPPORT_PROCESS_STATES:
            return ()
        if workflow_state not in _OPERATIONAL_SUPPORT_PROCESS_STATES:
            raise PortiaCorruptionError(
                "current Support Process has unsupported workflow_state"
            )

        context = PortiaAttentionContext(
            class_id=work.class_id,
            work_ref=work,
        )
        items: list[PortiaAttentionItem] = []

        if wants_due or wants_overdue:
            review_on = current.record.field("review_on")
            if review_on is not None:
                if not isinstance(review_on, str):
                    raise PortiaCorruptionError(
                        "current Support Process review_on is malformed"
                    )
                timing = classify_follow_up_timing(
                    {"kind": "date_only", "date": review_on},
                    as_of=query.as_of,
                )
                if timing.classification == "due" and wants_due:
                    items.append(
                        PortiaAttentionItem(
                            code="portia_support_process_review_due",
                            source_ref=work,
                            context=context,
                            reason_codes=(workflow_state,),
                            timing=timing,
                        )
                    )
                elif timing.classification == "overdue" and wants_overdue:
                    items.append(
                        PortiaAttentionItem(
                            code="portia_support_process_review_overdue",
                            source_ref=work,
                            context=context,
                            reason_codes=(workflow_state,),
                            timing=timing,
                        )
                    )

        if wants_dependency:
            gate = DependencyWorkflowService(
                self.workspace_root,
                repository=self.repository,
                quarantine=self.quarantine,
                context_assembler=self.contexts,
            ).evaluate_gate(
                work,
                gate="current_use",
                evaluated_at=query.as_of.text,
            )
            reasons = _dependency_attention_reason_codes(gate.conditions)
            if reasons:
                items.append(
                    PortiaAttentionItem(
                        code="portia_support_process_dependency_attention",
                        source_ref=work,
                        context=context,
                        reason_codes=reasons,
                    )
                )

        return tuple(items)

    @staticmethod
    def _partial_notice() -> PortiaAttentionNotice:
        return PortiaAttentionNotice(
            code=PORTIA_ATTENTION_PARTIAL_NOTICE,
            message=_PARTIAL_NOTICE_MESSAGE,
        )

    @staticmethod
    def _unavailable_report(
        query: PortiaAttentionQuery,
    ) -> PortiaAttentionReport:
        return build_attention_report(
            query,
            notices=(
                PortiaAttentionNotice(
                    code=PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
                    message=_UNAVAILABLE_NOTICE_MESSAGE,
                ),
            ),
            evaluation="unavailable",
        )

    @staticmethod
    def _work_query(
        query: PortiaAttentionQuery,
        work: ExactPortiaWorkRef,
    ) -> PortiaAttentionQuery:
        return PortiaAttentionQuery(
            scope=PortiaAttentionScope.work_scope(work),
            as_of=query.as_of,
            active_school_year=query.active_school_year,
            attention_codes=query.attention_codes,
            attention_classes=query.attention_classes,
        )

    def _technical_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[list[PortiaAttentionItem], bool]:
        items: list[PortiaAttentionItem] = []
        partial = False
        for source in (
            self.operational.recovery_items,
            self.operational.quarantine_items,
            self.operational.integrity_items,
            self.derived.items,
        ):
            try:
                items.extend(source(query))
            except UnknownIntegrityAttentionCodeError:
                # Unknown accepted finding vocabulary is a contract failure,
                # not an isolatable availability problem.
                raise
            except (PortiaStorageError, WorkflowPrerequisiteError):
                partial = True
        return items, partial

    def _domain_items_for_work(
        self,
        query: PortiaAttentionQuery,
        work: ExactPortiaWorkRef,
    ) -> tuple[list[PortiaAttentionItem], bool]:
        local_query = self._work_query(query, work)
        try:
            if not _work_matches_school_year(
                self.repository,
                work,
                query.active_school_year,
            ):
                return [], False
        except PortiaStorageError:
            return [], True

        items: list[PortiaAttentionItem] = []
        partial = False
        for source in (
            self._follow_up_items,
            self._review_items,
            self._support_process_items,
        ):
            try:
                items.extend(source(local_query))
            except (PortiaStorageError, WorkflowPrerequisiteError):
                partial = True
        return items, partial

    def _evaluated_report(
        self,
        query: PortiaAttentionQuery,
        items: list[PortiaAttentionItem],
        *,
        partial: bool,
    ) -> PortiaAttentionReport:
        notices = (self._partial_notice(),) if partial else ()
        return build_attention_report(
            query,
            tuple(items),
            notices=notices,
        )

    def _query_work(
        self,
        query: PortiaAttentionQuery,
    ) -> PortiaAttentionReport:
        work = _require_exact_work_scope(query)
        try:
            root = self.repository.load_work(work)
        except PortiaStorageError:
            return self._unavailable_report(query)

        if (
            query.active_school_year is not None
            and root.record.field("school_year") != query.active_school_year
        ):
            return build_attention_report(query)

        technical, technical_partial = self._technical_items(query)
        domain, domain_partial = self._domain_items_for_work(query, work)
        return self._evaluated_report(
            query,
            [*technical, *domain],
            partial=technical_partial or domain_partial,
        )

    def _query_class(
        self,
        query: PortiaAttentionQuery,
    ) -> PortiaAttentionReport:
        class_id = query.scope.class_id
        assert class_id is not None
        if not class_exists(self.workspace_root, class_id):
            return self._unavailable_report(query)

        try:
            works = class_work_refs(self.repository, class_id)
        except PortiaStorageError:
            return self._unavailable_report(query)

        items, partial = self._technical_items(query)
        for work in works:
            domain, work_partial = self._domain_items_for_work(query, work)
            items.extend(domain)
            partial = partial or work_partial
        return self._evaluated_report(query, items, partial=partial)

    def _query_workspace(
        self,
        query: PortiaAttentionQuery,
    ) -> PortiaAttentionReport:
        try:
            discovery = discover_workspace_classes(self.workspace_root)
        except PortiaStorageError:
            return self._unavailable_report(query)

        items, partial = self._technical_items(query)
        partial = partial or discovery.incomplete
        for class_id in discovery.class_ids:
            try:
                works = class_work_refs(self.repository, class_id)
            except PortiaStorageError:
                partial = True
                continue
            for work in works:
                domain, work_partial = self._domain_items_for_work(
                    query,
                    work,
                )
                items.extend(domain)
                partial = partial or work_partial
        return self._evaluated_report(query, items, partial=partial)

    def query(self, query: PortiaAttentionQuery) -> PortiaAttentionReport:
        """Evaluate native attention in one explicit work/class/workspace scope."""
        if not isinstance(query, PortiaAttentionQuery):
            raise TypeError("query must be a PortiaAttentionQuery")
        if query.scope.kind == "work":
            return self._query_work(query)
        if query.scope.kind == "class":
            return self._query_class(query)
        return self._query_workspace(query)
