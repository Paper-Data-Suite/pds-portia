"""Teacher-facing native Portia attention workflow."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from portia.attention import (
    ATTENTION_DEFINITION_BY_CODE,
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    AttentionQueryService,
    OpaqueAttentionSourceRef,
    PortiaAttentionItem,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionScope,
    TimingDecision,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.follow_up import launch_complete_follow_up_menu
from portia.menu.information import launch_add_information_menu
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import CancelMenuAction, select_one
from portia.menu.selectors import ClassOption, class_options
from portia.menu.support import launch_manage_support_menu
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaCorruptionError, PortiaStorageError
from portia.storage.repository import PortiaRepository

AttentionRoute: TypeAlias = Literal[
    "complete_follow_up",
    "add_information",
    "manage_support",
    "advanced_inspection",
]

ATTENTION_ROUTE_BY_CODE: Final[dict[str, AttentionRoute]] = {
    "portia_follow_up_due": "complete_follow_up",
    "portia_follow_up_overdue": "complete_follow_up",
    "portia_review_incomplete": "add_information",
    "portia_integrity_conflict": "advanced_inspection",
    "portia_integrity_review_required": "advanced_inspection",
    "portia_recovery_required": "advanced_inspection",
    "portia_quarantine_active": "advanced_inspection",
    "portia_derived_state_stale": "advanced_inspection",
    "portia_support_process_review_due": "manage_support",
    "portia_support_process_review_overdue": "manage_support",
    "portia_support_process_dependency_attention": "manage_support",
}

_ROUTE_LABELS: Final[dict[AttentionRoute, str]] = {
    "complete_follow_up": "Open Complete Follow-Up",
    "add_information": "Open Add Information / Review",
    "manage_support": "Open Manage Support",
    "advanced_inspection": "Open bounded Advanced inspection guidance",
}


@dataclass(frozen=True, slots=True)
class AttentionWorkOption:
    """One exact Portia work available for an explicit attention scope."""

    work: ExactPortiaWorkRef
    label: str


@dataclass(frozen=True, slots=True)
class AttentionItemOption:
    """One exact native attention item plus teacher-facing display text."""

    item: PortiaAttentionItem
    label: str


def attention_route(code: str) -> AttentionRoute | None:
    """Return a closed route for one known native code; never infer by substring."""

    return ATTENTION_ROUTE_BY_CODE.get(code)


def attention_query(
    scope: PortiaAttentionScope,
    *,
    clock: MenuClock,
) -> PortiaAttentionQuery:
    """Construct one explicit native attention query at the menu clock instant."""

    return PortiaAttentionQuery(
        scope=scope,
        as_of=clock.now(),
    )


def attention_report(
    root: Path,
    scope: PortiaAttentionScope,
    *,
    clock: MenuClock,
) -> PortiaAttentionReport:
    """Delegate native attention evaluation directly to Issue #49."""

    return AttentionQueryService(root).query(
        attention_query(scope, clock=clock)
    )


def report_evaluation_label(report: PortiaAttentionReport) -> str:
    """Preserve evaluated, partial, and unavailable distinctions."""

    if report.evaluation == "unavailable":
        return "Unavailable"
    if any(
        notice.code == PORTIA_ATTENTION_PARTIAL_NOTICE
        for notice in report.notices
    ):
        return "Partial"
    return "Evaluated"


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _scope_label(scope: PortiaAttentionScope) -> str:
    if scope.kind == "workspace":
        return "Workspace"
    if scope.kind == "class":
        assert scope.class_id is not None
        return f"Class {scope.class_id}"
    assert scope.work_ref is not None
    work = scope.work_ref
    kind = "Event" if work.work_kind == "event" else "Support Process"
    return f"{kind} — {work.class_id} — {work.work_id}"


def _count_unit_label(value: str) -> str:
    return value.replace("_", " ")


def _report_lines(report: PortiaAttentionReport) -> tuple[str, ...]:
    lines = [
        f"Scope: {_scope_label(report.scope)}",
        f"As of: {report.as_of.text}",
        f"Evaluation: {report_evaluation_label(report)}",
    ]
    for notice in report.notices:
        lines.append(f"Notice: {notice.message}")

    if report.evaluation == "unavailable":
        return tuple(lines)

    if report.summaries:
        lines.append("")
        lines.append("Native attention summary:")
        for summary in report.summaries:
            lines.append(
                f"- {summary.label}: {summary.count} "
                f"{_count_unit_label(summary.count_unit)}"
            )
    elif not report.notices:
        lines.append("")
        lines.append("No native Portia attention items are present in this scope.")

    return tuple(lines)


def _timing_label(timing: TimingDecision | None) -> str | None:
    if timing is None:
        return None
    start = timing.start.isoformat()
    end = timing.end.isoformat()
    if start == end:
        interval = start
    else:
        interval = f"{start} to {end}"
    return f"{_humanize(timing.classification)} — {interval}"


def _source_label(item: PortiaAttentionItem) -> str:
    source = item.source_ref
    if isinstance(source, ExactPortiaWorkRecordRef):
        work = source.work_ref
        return (
            f"{_humanize(source.record_ref.record_kind)} — "
            f"{work.class_id} — {work.work_kind} — {work.work_id}"
        )
    if isinstance(source, ExactPortiaWorkRef):
        return (
            f"{_humanize(source.work_kind)} — "
            f"{source.class_id} — {source.work_id}"
        )
    assert isinstance(source, OpaqueAttentionSourceRef)
    return f"Operational source — {_humanize(source.kind)}"


def _item_label(item: PortiaAttentionItem) -> str:
    definition = ATTENTION_DEFINITION_BY_CODE[item.code]
    return f"{definition.label} — {_source_label(item)}"


def _item_options(
    report: PortiaAttentionReport,
) -> tuple[AttentionItemOption, ...]:
    preliminary = tuple(
        AttentionItemOption(item=item, label=_item_label(item))
        for item in report.items
    )
    counts = Counter(option.label.casefold() for option in preliminary)
    options: list[AttentionItemOption] = []
    for option in preliminary:
        label = option.label
        if counts[label.casefold()] > 1:
            source = option.item.source_ref
            if isinstance(source, ExactPortiaWorkRecordRef):
                label += f" — exact {source.record_ref.record_id}"
            elif isinstance(source, ExactPortiaWorkRef):
                label += f" — exact {source.work_id}"
            else:
                label += " — exact opaque source"
        options.append(AttentionItemOption(option.item, label))
    return tuple(options)


def _work_options(root: Path, class_id: str) -> tuple[AttentionWorkOption, ...]:
    repository = PortiaRepository(root)
    values: list[AttentionWorkOption] = []
    for work_kind, version, label in (
        ("event", "2", "Event"),
        ("support_process", "1", "Support Process"),
    ):
        for stored in repository.list_works(
            class_id,
            work_kind=work_kind,
            version=version,
        ):
            work_id = stored.record.work_id
            if work_id is None:
                raise PortiaCorruptionError(
                    "Portia work root has no exact work identity"
                )
            work = ExactPortiaWorkRef(
                class_id=class_id,
                work_id=work_id,
                work_kind=work_kind,
                contract_version=version,
            )
            status = stored.record.status or "unknown"
            values.append(
                AttentionWorkOption(
                    work,
                    f"{label} — {_humanize(status)} — exact {work_id}",
                )
            )
    return tuple(values)


def _choose_class_scope(
    state: MenuSessionContext,
    root: Path,
) -> PortiaAttentionScope:
    classes = class_options(root)
    if not classes:
        raise ValueError(
            "No Core classes with both metadata and rosters are available."
        )
    selected: ClassOption = select_one(
        "Attention Needed — Class",
        classes,
        tuple(item.label for item in classes),
        help_text=(
            "Choose one exact Core class. Attention remains workflow state, "
            "not a student ranking or risk assessment."
        ),
    )
    state.remember_class(selected.class_id)
    return PortiaAttentionScope.class_scope(selected.class_id)


def _remember_work(
    state: MenuSessionContext,
    work: ExactPortiaWorkRef,
) -> None:
    if work.work_kind == "event":
        state.remember_work(
            class_id=work.class_id,
            work_kind="event",
            work_id=work.work_id,
        )
    elif work.work_kind == "support_process":
        state.remember_work(
            class_id=work.class_id,
            work_kind="support_process",
            work_id=work.work_id,
        )
    else:
        raise ValueError("attention work must be Event or Support Process")


def _choose_work_scope(
    state: MenuSessionContext,
    root: Path,
) -> PortiaAttentionScope:
    class_scope = _choose_class_scope(state, root)
    assert class_scope.class_id is not None
    works = _work_options(root, class_scope.class_id)
    if not works:
        raise ValueError(
            "No Event or Support Process work is available in that class."
        )
    selected = select_one(
        "Attention Needed — Exact Work",
        works,
        tuple(item.label for item in works),
        help_text=(
            "Choose an exact work reference. This only narrows Issue #49's "
            "read-only attention query."
        ),
    )
    _remember_work(state, selected.work)
    return PortiaAttentionScope.work_scope(selected.work)


def _work_from_item(
    item: PortiaAttentionItem,
) -> ExactPortiaWorkRef | None:
    source = item.source_ref
    if isinstance(source, ExactPortiaWorkRecordRef):
        return source.work_ref
    if isinstance(source, ExactPortiaWorkRef):
        return source
    return item.context.work_ref


def _advanced_guidance(item: PortiaAttentionItem) -> None:
    definition = ATTENTION_DEFINITION_BY_CODE[item.code]
    clear_screen()
    print_menu_header("Attention Needed — Advanced Inspection")
    print(definition.label)
    print()
    print(
        "This item belongs to Portia's integrity/recovery operational surface."
    )
    print(
        "Viewing Attention Needed did not acknowledge, suppress, release, "
        "recover, repair, or rebuild anything."
    )
    print(
        "Use Advanced Portia tools for bounded technical inspection when that "
        "surface is available."
    )
    print()
    pause_for_user()


def route_attention_item(
    state: MenuSessionContext,
    item: PortiaAttentionItem,
) -> None:
    """Route one already-classified native item through the closed table."""

    route = attention_route(item.code)
    if route is None:
        clear_screen()
        print_menu_header("Attention Needed — No Routine Route")
        print(
            "This native attention code has no registered Issue #50 action route."
        )
        print("No action was inferred from its text or code name.")
        print()
        pause_for_user()
        return

    work = _work_from_item(item)
    if work is not None:
        _remember_work(state, work)

    if route == "complete_follow_up":
        launch_complete_follow_up_menu(state)
    elif route == "add_information":
        launch_add_information_menu(state)
    elif route == "manage_support":
        launch_manage_support_menu(state)
    else:
        _advanced_guidance(item)


def _item_details(
    option: AttentionItemOption,
) -> tuple[str, ...]:
    item = option.item
    definition = ATTENTION_DEFINITION_BY_CODE[item.code]
    lines = [
        definition.label,
        f"Attention class: {_humanize(definition.attention_class)}",
        f"Source: {_source_label(item)}",
    ]
    timing = _timing_label(item.timing)
    if timing is not None:
        lines.append(f"Timing: {timing}")
    if item.reason_codes:
        reasons = ", ".join(_humanize(code) for code in item.reason_codes)
        lines.append(f"Native reason state: {reasons}")
    route = attention_route(item.code)
    if route is None:
        lines.append("Route: No registered routine action")
    else:
        lines.append(f"Route: {_ROUTE_LABELS[route]}")
    return tuple(lines)


def _open_item(
    state: MenuSessionContext,
    option: AttentionItemOption,
) -> None:
    while True:
        clear_screen()
        print_menu_header("Attention Needed — Item")
        for line in _item_details(option):
            print(line)
        print()
        print("1. Open related task")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Attention Needed — Item Help")
            print(
                "The item was classified by Issue #49. This screen does not "
                "reclassify, rank, score, or recommend an intervention."
            )
            print(
                "Opening a related task does not itself complete or alter the "
                "attention source."
            )
            print()
            pause_for_user()
        elif navigation is NavigationChoice.BACK:
            return
        elif raw == "1":
            route_attention_item(state, option.item)
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _review_items(
    state: MenuSessionContext,
    report: PortiaAttentionReport,
) -> None:
    options = _item_options(report)
    if not options:
        clear_screen()
        print_menu_header("Attention Needed — Items")
        print("No native attention items are available in this evaluation.")
        print()
        pause_for_user()
        return
    while True:
        try:
            selected = select_one(
                "Attention Needed — Items",
                options,
                tuple(option.label for option in options),
                help_text=(
                    "Items are ordered by Issue #49's deterministic definition "
                    "and source ordering. That order is not urgency, severity, "
                    "priority, or student ranking."
                ),
            )
            _open_item(state, selected)
        except CancelMenuAction:
            return


def _report_menu(
    state: MenuSessionContext,
    root: Path,
    scope: PortiaAttentionScope,
    *,
    clock: MenuClock,
) -> None:
    while True:
        report = attention_report(root, scope, clock=clock)
        clear_screen()
        print_menu_header("Attention Needed")
        for line in _report_lines(report):
            print(line)
        print()
        if report.items:
            print("1. Review attention items")
        print("2. Refresh this evaluation")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Attention Needed Help")
            print(
                "Attention reports native workflow, integrity, and recovery "
                "state. It is not student risk, severity, or priority."
            )
            print(
                "A partial notice means some independent sources could not be "
                "evaluated safely; unavailable is not the same as no attention."
            )
            print()
            pause_for_user()
        elif navigation is NavigationChoice.BACK:
            return
        elif raw == "1" and report.items:
            _review_items(state, report)
        elif raw == "2":
            continue
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def launch_attention_needed_menu(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
) -> None:
    """Launch the read-only Issue #49 native attention surface."""

    selected_clock = clock or MenuClock()
    while True:
        clear_screen()
        print_menu_header("Attention Needed")
        print(
            "Review native Portia workflow, integrity, and recovery attention."
        )
        print()
        print("1. Workspace attention")
        print("2. Class attention")
        print("3. Exact work attention")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Attention Needed Help")
            print(
                "Workspace is the broad teacher view. Class and exact-work "
                "scopes explicitly narrow the same Issue #49 query service."
            )
            print(
                "Attention is workflow state, not a behavior score, risk score, "
                "urgency ranking, or recommendation."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        if raw not in {"1", "2", "3"}:
            print(navigation_hint_with_help())
            pause_for_user()
            continue

        try:
            root = state.resolve_workspace()
            if raw == "1":
                scope = PortiaAttentionScope.workspace_scope()
            elif raw == "2":
                scope = _choose_class_scope(state, root)
            else:
                scope = _choose_work_scope(state, root)
            _report_menu(
                state,
                root,
                scope,
                clock=selected_clock,
            )
        except CancelMenuAction:
            continue
        except (
            PortiaCorruptionError,
            PortiaLocalValidationError,
            PortiaStorageError,
            ValueError,
        ):
            clear_screen()
            print_menu_header("Attention Needed — Unable to Evaluate")
            print(
                "Portia could not safely evaluate the requested attention scope."
            )
            print(
                "No attention state was changed and no repair was attempted."
            )
            print()
            pause_for_user()
