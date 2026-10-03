"""Core-facing projection over Portia's native Issue #49 attention service."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Final

from pds_core.module_operations import (
    MAX_MODULE_OPERATION_COUNT,
    ModuleAttentionReport,
    ModuleAttentionSummary,
    ModuleOperationsNotice,
    ModuleOperationsRequest,
    ModuleOwnerActionRef,
)
from pds_core.routing_models import ModuleWorkRef

from portia.attention import (
    PORTIA_ATTENTION_ACTION_ID_BY_CODE,
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    AttentionQueryService,
    PortiaAttentionItem,
    PortiaAttentionNotice,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionScope,
    require_portia_attention_action_id,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.pds_operations import PORTIA_MODULE_ID

AttentionClock = Callable[[], datetime]

_KNOWN_NATIVE_ATTENTION_CODES: Final[frozenset[str]] = frozenset(
    PORTIA_ATTENTION_ACTION_ID_BY_CODE
)

_NOTICE_SUMMARIES: Final[dict[str, str]] = {
    PORTIA_ATTENTION_PARTIAL_NOTICE: (
        "Some Portia attention sources could not be evaluated safely."
    ),
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE: (
        "Portia attention could not be evaluated for the supplied context."
    ),
}


def _system_clock() -> datetime:
    """Return one timezone-aware current instant for a shared invocation."""

    return datetime.now(timezone.utc)


def _capture_as_of(clock: AttentionClock) -> ExplicitOffsetTimestamp:
    captured = clock()
    if not isinstance(captured, datetime):
        raise TypeError("attention clock must return a datetime")
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError("attention clock must return a timezone-aware datetime")
    return ExplicitOffsetTimestamp(captured.isoformat())


def _unavailable_report() -> ModuleAttentionReport:
    return ModuleAttentionReport(
        evaluation="unavailable",
        summaries=(),
        notices=(
            ModuleOperationsNotice(
                code=PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
                summary=_NOTICE_SUMMARIES[PORTIA_ATTENTION_UNAVAILABLE_NOTICE],
            ),
        ),
    )


def _shared_native_notice(
    notice: PortiaAttentionNotice,
) -> ModuleOperationsNotice:
    try:
        summary = _NOTICE_SUMMARIES[notice.code]
    except KeyError as exc:
        raise RuntimeError(
            "native Portia attention returned an unsupported notice code"
        ) from exc
    return ModuleOperationsNotice(code=notice.code, summary=summary)


def _project_notices(
    notices: tuple[PortiaAttentionNotice, ...],
    *,
    projection_partial: bool,
) -> tuple[ModuleOperationsNotice, ...]:
    projected = [_shared_native_notice(notice) for notice in notices]
    if projection_partial and not any(
        notice.code == PORTIA_ATTENTION_PARTIAL_NOTICE for notice in projected
    ):
        projected.append(
            ModuleOperationsNotice(
                code=PORTIA_ATTENTION_PARTIAL_NOTICE,
                summary=_NOTICE_SUMMARIES[PORTIA_ATTENTION_PARTIAL_NOTICE],
            )
        )
    return tuple(projected)


def _exact_shared_class(
    items: tuple[PortiaAttentionItem, ...],
) -> str | None:
    if not items:
        return None
    first = items[0].context.class_id
    if first is None:
        return None
    if any(item.context.class_id != first for item in items[1:]):
        return None
    return first


def _exact_shared_work(
    items: tuple[PortiaAttentionItem, ...],
) -> ExactPortiaWorkRef | None:
    if not items:
        return None
    first = items[0].context.work_ref
    if first is None:
        return None
    if any(item.context.work_ref != first for item in items[1:]):
        return None
    return first


def _shared_context(
    report: PortiaAttentionReport,
    code: str,
    request: ModuleOperationsRequest,
) -> tuple[str | None, ModuleWorkRef | None]:
    contributors = tuple(item for item in report.items if item.code == code)
    exact_work = _exact_shared_work(contributors)

    work_ref: ModuleWorkRef | None = None
    if exact_work is not None:
        if request.class_id is not None and exact_work.class_id != request.class_id:
            raise RuntimeError(
                "native Portia attention escaped the requested class scope"
            )
        work_ref = ModuleWorkRef(
            module_id=PORTIA_MODULE_ID,
            class_id=exact_work.class_id,
            work_id=exact_work.work_id,
        )

    class_id: str | None
    if request.class_id is not None:
        class_id = request.class_id
    elif exact_work is not None:
        class_id = exact_work.class_id
    else:
        class_id = _exact_shared_class(contributors)

    return class_id, work_ref


def _owner_action(code: str) -> ModuleOwnerActionRef:
    return ModuleOwnerActionRef(
        module_id=PORTIA_MODULE_ID,
        action_id=require_portia_attention_action_id(code),
    )


def _project_native_report(
    native: PortiaAttentionReport,
    request: ModuleOperationsRequest,
) -> ModuleAttentionReport:
    if not isinstance(native, PortiaAttentionReport):
        raise TypeError("native attention service must return PortiaAttentionReport")

    if native.evaluation == "unavailable":
        return ModuleAttentionReport(
            evaluation="unavailable",
            summaries=(),
            notices=_project_notices(
                native.notices,
                projection_partial=False,
            ),
        )

    summaries: list[ModuleAttentionSummary] = []
    projection_partial = False
    for summary in native.summaries:
        if summary.code not in _KNOWN_NATIVE_ATTENTION_CODES:
            raise RuntimeError(
                "native Portia attention returned an unsupported attention code"
            )
        if summary.count > MAX_MODULE_OPERATION_COUNT:
            projection_partial = True
            continue

        class_id, work_ref = _shared_context(native, summary.code, request)
        summaries.append(
            ModuleAttentionSummary(
                code=summary.code,
                label=summary.label,
                count=summary.count,
                class_id=class_id,
                work_ref=work_ref,
                action=_owner_action(summary.code),
            )
        )

    return ModuleAttentionReport(
        evaluation="evaluated",
        summaries=tuple(summaries),
        notices=_project_notices(
            native.notices,
            projection_partial=projection_partial,
        ),
    )


def _evaluate_portia_attention(
    request: ModuleOperationsRequest,
    *,
    clock: AttentionClock,
) -> ModuleAttentionReport:
    if not isinstance(request, ModuleOperationsRequest):
        raise TypeError("request must be a ModuleOperationsRequest")

    as_of = _capture_as_of(clock)
    if request.workspace_root is None:
        return _unavailable_report()

    scope = (
        PortiaAttentionScope.workspace_scope()
        if request.class_id is None
        else PortiaAttentionScope.class_scope(request.class_id)
    )
    query = PortiaAttentionQuery(
        scope=scope,
        as_of=as_of,
        active_school_year=request.active_school_year,
    )
    native = AttentionQueryService(request.workspace_root).query(query)
    return _project_native_report(native, request)


def evaluate_portia_attention(
    request: ModuleOperationsRequest,
    /,
) -> ModuleAttentionReport:
    """Evaluate current Portia attention through the native #49 authority."""

    return _evaluate_portia_attention(request, clock=_system_clock)


__all__ = ["evaluate_portia_attention"]
