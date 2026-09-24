"""Teacher-facing Intervention, Implementation, and Fidelity workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast

from portia.menu.authoring import (
    FidelityAuthoringInput,
    ImplementationAuthoringInput,
    InterventionAuthoringInput,
    SupportPlanTargetInput,
    SupportScheduleInput,
    prepare_fidelity,
    prepare_implementation,
    prepare_intervention,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import confirm_write, prompt_text, select_one
from portia.menu.ui import (
    PAGE_SIZE,
    clear_screen,
    page_count,
    page_items,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import StoredRecord
from portia.workflows import (
    FidelityWorkflowService,
    ImplementationWorkflowService,
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportWorkflowService,
)


class SupportProcessSelection(Protocol):
    """Minimum selected-process presentation needed by delivery workflows."""

    @property
    def work(self) -> ExactPortiaWorkRef:
        ...

    @property
    def summary(self) -> str:
        ...

    @property
    def status(self) -> str:
        ...

    @property
    def workflow_state(self) -> str:
        ...


class LabeledOption(Protocol):
    """Read-only label contract shared by bounded menu option records."""

    @property
    def label(self) -> str:
        ...


LabeledOptionT = TypeVar("LabeledOptionT", bound=LabeledOption)


@dataclass(frozen=True, slots=True)
class ParticipantOption:
    stored: StoredRecord
    participant_id: str
    label: str
    status: str


@dataclass(frozen=True, slots=True)
class NeedOption:
    stored: StoredRecord
    need_id: str
    label: str


@dataclass(frozen=True, slots=True)
class GoalOption:
    stored: StoredRecord
    goal_id: str
    label: str


@dataclass(frozen=True, slots=True)
class PlanOption:
    stored: StoredRecord
    kind: Literal["support", "intervention"]
    plan_id: str
    label: str


@dataclass(frozen=True, slots=True)
class ImplementationOption:
    stored: StoredRecord
    implementation_id: str
    plan_kind: Literal["support", "intervention"]
    plan_id: str
    label: str


_STRATEGIES: tuple[tuple[str, str], ...] = (
    ("access", "Access"),
    ("environmental_or_instructional", "Environmental or instructional"),
    ("organizational", "Organizational"),
    ("relationship_or_connection", "Relationship or connection"),
    ("routine_or_structure", "Routine or structure"),
    ("skill_building", "Skill building"),
    ("self_management", "Self-management"),
    ("resource_or_coordination", "Resource or coordination"),
    ("other", "Other bounded strategy"),
)
_NO_PROVIDER_REASONS: tuple[tuple[str, str], ...] = (
    ("access_condition", "Access condition"),
    ("self_directed", "Self-directed"),
    ("resource_availability", "Resource availability"),
    ("other", "Other explicit reason"),
)
_NO_HUMAN_PROVIDER_REASONS: tuple[tuple[str, str], ...] = (
    ("self_directed", "Self-directed"),
    ("environmental_condition", "Environmental condition"),
    ("resource_access", "Resource access"),
    ("other", "Other explicit reason"),
)
_EXECUTION_STATES: tuple[tuple[str, str], ...] = (
    ("attempted", "Attempted"),
    ("in_progress", "In progress"),
    ("completed", "Completed"),
    ("partially_completed", "Partially completed"),
    ("unable_to_complete", "Unable to complete"),
)
_FIDELITY_RESULTS: tuple[tuple[str, str], ...] = (
    ("as_planned", "As planned"),
    ("partially_as_planned", "Partially as planned"),
    ("not_as_planned", "Not as planned"),
    ("unable_to_determine", "Unable to determine"),
    ("not_applicable", "Not applicable"),
)
_FIDELITY_BASES: tuple[tuple[str, str], ...] = (
    ("direct_observation", "Direct observation"),
    ("implementation_records", "Implementation record(s)"),
    ("record_review", "Record review"),
    ("combined", "Combined basis"),
    ("other", "Other bounded basis"),
)


def _show_result(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _require_operator(state: MenuSessionContext, *, title: str) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        title,
        "Display label",
        help_text=(
            "Enter the teacher-facing name or label for the local operator. "
            "This records provenance only; it is not authentication or institutional authority."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _person_label(record: object) -> str:
    field = getattr(record, "field")
    person = field("person")
    if not isinstance(person, Mapping):
        return "Participant"
    display = person.get("display_snapshot")
    if isinstance(display, Mapping):
        name = display.get("display_name")
        if isinstance(name, str) and name.strip():
            return name
    label = person.get("display_label")
    if isinstance(label, str) and label.strip():
        return label
    kind = person.get("kind")
    return str(kind).replace("_", " ").title() if isinstance(kind, str) else "Participant"


def _participants(
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    statuses: frozenset[str],
) -> tuple[ParticipantOption, ...]:
    values: list[ParticipantOption] = []
    for stored in SupportProcessParticipantWorkflowService(root).list(work):
        identifier = stored.record.logical_id
        status = stored.record.status
        if identifier is None or status not in statuses:
            continue
        label = _person_label(stored.record)
        values.append(
            ParticipantOption(
                stored=stored,
                participant_id=identifier,
                label=f"{label} — {status.title()}",
                status=status,
            )
        )
    return tuple(values)


def _choose_target(
    root: Path,
    process: SupportProcessSelection,
    *,
    statuses: frozenset[str],
    title: str,
) -> tuple[SupportPlanTargetInput, str]:
    participants = _participants(root, process.work, statuses=statuses)
    values: list[tuple[SupportPlanTargetInput, str]] = [
        (SupportPlanTargetInput(kind="support_process"), "Whole Support Process")
    ]
    values.extend(
        (
            SupportPlanTargetInput(
                kind="support_process_participant",
                participant_id=item.participant_id,
            ),
            item.label,
        )
        for item in participants
    )
    return select_one(
        title,
        tuple(values),
        tuple(label for _value, label in values),
        help_text=(
            "Choose the exact scope. This selection does not itself establish delivery, "
            "fidelity, effectiveness, or Outcome."
        ),
    )


def _need_options(
    root: Path,
    process: SupportProcessSelection,
    *,
    statuses: frozenset[str],
) -> tuple[NeedOption, ...]:
    values: list[NeedOption] = []
    for stored in SupportNeedWorkflowService(root).list(process.work):
        identifier = stored.record.logical_id
        status = stored.record.status
        description = stored.record.field("description")
        if identifier is None or status not in statuses or not isinstance(description, str):
            continue
        values.append(
            NeedOption(
                stored=stored,
                need_id=identifier,
                label=f"{description} — {status.title()}",
            )
        )
    return tuple(values)


def _goal_options(
    root: Path,
    process: SupportProcessSelection,
    *,
    statuses: frozenset[str],
) -> tuple[GoalOption, ...]:
    values: list[GoalOption] = []
    for stored in SupportGoalWorkflowService(root).list(process.work):
        identifier = stored.record.logical_id
        status = stored.record.status
        description = stored.record.field("description")
        if identifier is None or status not in statuses or not isinstance(description, str):
            continue
        values.append(
            GoalOption(
                stored=stored,
                goal_id=identifier,
                label=f"{description} — {status.title()}",
            )
        )
    return tuple(values)


def _select_many(
    title: str,
    options: tuple[LabeledOptionT, ...],
    *,
    required: bool,
    help_text: str,
) -> tuple[LabeledOptionT, ...]:
    available = list(options)
    if not available:
        if required:
            raise ValueError(f"No eligible records are available for {title}.")
        return ()
    if not required:
        use = select_one(
            title,
            (False, True),
            ("Do not link any", "Link one or more"),
            help_text=help_text,
        )
        if not use:
            return ()
    selected: list[LabeledOptionT] = []
    while available:
        choice = select_one(
            title,
            tuple(available),
            tuple(item.label for item in available),
            help_text=help_text,
        )
        selected.append(choice)
        available = [item for item in available if item is not choice]
        if not available:
            break
        more = select_one(
            title,
            (False, True),
            ("Continue with selected records", "Add another"),
            help_text=help_text,
        )
        if not more:
            break
    return tuple(selected)


def _prompt_positive_int(title: str, label: str, help_text: str) -> int:
    while True:
        value = prompt_text(title, label, help_text=help_text)
        assert value is not None
        if value.isdigit() and int(value) > 0:
            return int(value)
        _show_result(title, (f"{label} must be a positive whole number.",))


def _prompt_optional_minutes(title: str) -> int | None:
    while True:
        value = prompt_text(
            title,
            "Planned duration in minutes",
            help_text="Optional planned duration; this is not actual delivered time.",
            optional=True,
        )
        if value is None:
            return None
        if value.isdigit() and 1 <= int(value) <= 10080:
            return int(value)
        _show_result(title, ("Duration must be a whole number from 1 through 10080.",))


def _choose_schedule(
    *,
    active: bool,
) -> tuple[SupportScheduleInput, str]:
    kinds = (
        ("recurring", "condition_triggered", "custom")
        if active
        else ("as_needed", "recurring", "condition_triggered", "custom")
    )
    labels = {
        "as_needed": "As needed",
        "recurring": "Recurring",
        "condition_triggered": "Condition triggered",
        "custom": "Custom description",
    }
    kind = cast(
        Literal["as_needed", "recurring", "condition_triggered", "custom"],
        select_one(
            "Plan Intervention — Schedule",
            kinds,
            tuple(labels[value] for value in kinds),
            help_text=(
                "This is a planned schedule. An active Intervention requires a non-as-needed "
                "schedule. A schedule never creates an Implementation occurrence."
            ),
        ),
    )
    minutes = _prompt_optional_minutes("Plan Intervention — Schedule")
    if kind == "as_needed":
        return SupportScheduleInput(kind=kind, planned_minutes=minutes), labels[kind]
    if kind == "recurring":
        occurrences = _prompt_positive_int(
            "Plan Intervention — Schedule",
            "Occurrences",
            "Planned number of occurrences, not an implementation count.",
        )
        interval_count = _prompt_positive_int(
            "Plan Intervention — Schedule",
            "Every how many units",
            "Enter the planned recurrence interval.",
        )
        unit = select_one(
            "Plan Intervention — Schedule",
            ("day", "week", "month"),
            ("Day(s)", "Week(s)", "Month(s)"),
            help_text="Choose the planned recurrence unit.",
        )
        return (
            SupportScheduleInput(
                kind=kind,
                planned_minutes=minutes,
                occurrences=occurrences,
                interval_count=interval_count,
                interval_unit=unit,
            ),
            f"{occurrences} occurrence(s), every {interval_count} {unit}(s)",
        )
    if kind == "condition_triggered":
        trigger = prompt_text(
            "Plan Intervention — Schedule",
            "Trigger condition",
            help_text="Describe the bounded planned trigger.",
        )
        assert trigger is not None
        return (
            SupportScheduleInput(kind=kind, planned_minutes=minutes, trigger=trigger),
            f"Condition triggered — {trigger}",
        )
    description = prompt_text(
        "Plan Intervention — Schedule",
        "Custom schedule description",
        help_text="Describe the planned schedule without claiming delivery occurred.",
    )
    assert description is not None
    return (
        SupportScheduleInput(
            kind=kind,
            planned_minutes=minutes,
            description=description,
        ),
        f"Custom — {description}",
    )


def _select_provider_ids(
    root: Path,
    process: SupportProcessSelection,
    *,
    statuses: frozenset[str],
    required: bool,
    title: str,
) -> tuple[tuple[str, ...], str]:
    available = list(_participants(root, process.work, statuses=statuses))
    if required and not available:
        raise ValueError("No eligible Support Process Participants are available as providers.")
    if not required:
        assign = select_one(
            title,
            (False, True),
            ("No provider assigned yet", "Assign participant provider(s)"),
            help_text=(
                "Provider planning is explicit. It does not establish actual delivery or Fidelity."
            ),
        )
        if not assign:
            return (), "No provider assigned"
    selected: list[ParticipantOption] = []
    while available:
        choice = select_one(
            title,
            tuple(available),
            tuple(item.label for item in available),
            help_text="Select exact Support Process Participant provider(s).",
        )
        selected.append(choice)
        available = [
            item for item in available if item.participant_id != choice.participant_id
        ]
        if not available:
            break
        more = select_one(
            title,
            (False, True),
            ("Continue with selected providers", "Add another provider"),
            help_text="Add only providers explicitly part of this plan or occurrence.",
        )
        if not more:
            break
    return (
        tuple(item.participant_id for item in selected),
        ", ".join(item.label for item in selected),
    )


def record_intervention_once(
    state: MenuSessionContext,
    process: SupportProcessSelection,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one Intervention plan, distinct from actual Implementation."""

    root = state.resolve_workspace()
    operator = _require_operator(state, title="Plan Intervention — Your Name")
    statuses = (
        frozenset({"active"})
        if process.status == "active"
        else frozenset({"proposed", "active"})
    )
    target, target_label = _choose_target(
        root,
        process,
        statuses=statuses,
        title="Plan Intervention — Target",
    )
    needs = _select_many(
        "Plan Intervention — Needs",
        _need_options(root, process, statuses=statuses),
        required=True,
        help_text="Select exact Need(s) this Intervention is intended to address.",
    )
    goals = _select_many(
        "Plan Intervention — Goals",
        _goal_options(root, process, statuses=statuses),
        required=True,
        help_text="Select exact future-facing Goal(s) this Intervention is intended to serve.",
    )
    strategy_kind = select_one(
        "Plan Intervention — Strategy",
        tuple(item[0] for item in _STRATEGIES),
        tuple(item[1] for item in _STRATEGIES),
        help_text="Choose the bounded type of structured Intervention plan.",
    )
    strategy_detail: str | None = None
    if strategy_kind == "other":
        strategy_detail = prompt_text(
            "Plan Intervention — Strategy",
            "Strategy detail",
            help_text="Describe the bounded strategy category.",
        )
    procedure = prompt_text(
        "Plan Intervention — Procedure",
        "Planned procedure",
        help_text="Describe the structured action that is planned, not what actually occurred.",
    )
    assert procedure is not None

    active = process.status == "active"
    provider_ids, provider_label = _select_provider_ids(
        root,
        process,
        statuses=statuses,
        required=active,
        title="Plan Intervention — Provider",
    )
    no_provider_reason: str | None = None
    no_provider_detail: str | None = None
    if not provider_ids:
        no_provider_reason = select_one(
            "Plan Intervention — No Assigned Provider",
            tuple(item[0] for item in _NO_PROVIDER_REASONS),
            tuple(item[1] for item in _NO_PROVIDER_REASONS),
            help_text="Record why this proposed plan does not yet have an assigned provider.",
        )
        provider_label = f"No assigned provider — {no_provider_reason.replace('_', ' ')}"
        if no_provider_reason == "other":
            no_provider_detail = prompt_text(
                "Plan Intervention — No Assigned Provider",
                "Reason detail",
                help_text="Briefly state the bounded reason.",
            )

    schedule, schedule_label = _choose_schedule(active=active)
    monitoring = prompt_text(
        "Plan Intervention — Monitoring",
        "Planned monitoring approach",
        help_text=(
            "Describe how this Intervention is planned to be reviewed. This does not record "
            "progress, Fidelity, effectiveness, or Outcome."
        ),
    )
    assert monitoring is not None
    status: Literal["proposed", "active"] = "active" if active else "proposed"
    candidate = prepare_intervention(
        InterventionAuthoringInput(
            work=process.work,
            status=status,
            target=target,
            need_ids=tuple(item.need_id for item in needs),
            goal_ids=tuple(item.goal_id for item in goals),
            strategy_kind=strategy_kind,
            procedure=procedure,
            strategy_detail=strategy_detail,
            provider_participant_ids=provider_ids,
            no_provider_reason=no_provider_reason,
            no_provider_detail=no_provider_detail,
            schedule=schedule,
            monitoring_approach=monitoring,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    if not confirm_write(
        "Plan Intervention — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Target: {target_label}",
            f"Need(s): {', '.join(item.label for item in needs)}",
            f"Goal(s): {', '.join(item.label for item in goals)}",
            f"Strategy: {strategy_kind.replace('_', ' ')}",
            f"Procedure: {procedure}",
            f"Provider plan: {provider_label}",
            f"Schedule: {schedule_label}",
            f"Monitoring: {monitoring}",
            f"Canonical status: {status}",
            "",
            "This creates an Intervention plan only. It does not create an Implementation, "
            "Fidelity evaluation, or Outcome.",
        ),
        help_text="RECORD creates only this exact Intervention planning record.",
    ):
        return
    InterventionWorkflowService(root).create(process.work, candidate)
    _show_result("Intervention Planned", ("Intervention planning record created.",))


def _active_plan_options(
    root: Path,
    process: SupportProcessSelection,
) -> tuple[PlanOption, ...]:
    values: list[PlanOption] = []
    for stored in SupportWorkflowService(root).list(process.work):
        identifier = stored.record.logical_id
        status = stored.record.status
        plan_state = stored.record.field("plan_state")
        strategy = stored.record.field("strategy")
        procedure = strategy.get("procedure") if isinstance(strategy, Mapping) else None
        if (
            identifier is None
            or status != "active"
            or plan_state != "active"
            or not isinstance(procedure, str)
        ):
            continue
        values.append(
            PlanOption(
                stored=stored,
                kind="support",
                plan_id=identifier,
                label=f"Support — {procedure}",
            )
        )
    for stored in InterventionWorkflowService(root).list(process.work):
        identifier = stored.record.logical_id
        status = stored.record.status
        plan_state = stored.record.field("plan_state")
        strategy = stored.record.field("strategy")
        procedure = strategy.get("procedure") if isinstance(strategy, Mapping) else None
        if (
            identifier is None
            or status != "active"
            or plan_state != "active"
            or not isinstance(procedure, str)
        ):
            continue
        values.append(
            PlanOption(
                stored=stored,
                kind="intervention",
                plan_id=identifier,
                label=f"Intervention — {procedure}",
            )
        )
    return tuple(values)


def _prompt_time(
    title: str,
    clock: MenuClock,
    label: str,
    *,
    optional: bool = False,
) -> ExplicitOffsetTimestamp | None:
    default = None if optional else clock.now().text
    while True:
        value = prompt_text(
            title,
            label,
            help_text=(
                "Enter an RFC 3339 date/time with an explicit UTC offset."
                + (" Leave blank if not applicable." if optional else " Press Enter for the current time.")
            ),
            optional=optional,
            default=default,
        )
        if value is None:
            return None
        try:
            return ExplicitOffsetTimestamp(value)
        except Exception:
            _show_result(title, ("That date/time is invalid. Include an explicit UTC offset.",))


def _target_signature_from_record(record: object) -> tuple[object, ...]:
    target = getattr(record, "field")("target")
    if not isinstance(target, Mapping):
        return ("unknown",)
    kind = target.get("kind")
    if kind == "support_process":
        return ("support_process",)
    if kind == "support_process_participant":
        ref = target.get("record_ref")
        if isinstance(ref, Mapping):
            return ("participants", frozenset({ref.get("record_id")}))
    if kind == "support_process_participants":
        raw = target.get("targets")
        if isinstance(raw, tuple):
            ids = []
            for item in raw:
                if isinstance(item, Mapping):
                    ref = item.get("record_ref")
                    if isinstance(ref, Mapping):
                        ids.append(ref.get("record_id"))
            return ("participants", frozenset(ids))
    return ("unknown",)


def _target_signature_from_input(value: SupportPlanTargetInput) -> tuple[object, ...]:
    if value.kind == "support_process":
        return ("support_process",)
    return ("participants", frozenset({value.participant_id}))


def _plan_provider_signature(record: object) -> tuple[object, ...]:
    plan = getattr(record, "field")("provider_plan")
    if not isinstance(plan, Mapping):
        return ("unknown",)
    if plan.get("kind") == "no_assigned_provider":
        return ("no_human_provider",)
    raw = plan.get("participant_refs")
    if isinstance(raw, tuple):
        return (
            "participants",
            frozenset(
                item.get("record_id")
                for item in raw
                if isinstance(item, Mapping)
            ),
        )
    return ("unknown",)


def _actual_provider_signature(ids: tuple[str, ...]) -> tuple[object, ...]:
    if not ids:
        return ("no_human_provider",)
    return ("participants", frozenset(ids))


def _select_actual_provider(
    root: Path,
    process: SupportProcessSelection,
) -> tuple[tuple[str, ...], str | None, str | None, str]:
    mode = select_one(
        "Record Implementation — Actual Provider",
        ("participants", "none"),
        ("One or more Support Process participants", "No human provider"),
        help_text="Record who actually provided the occurrence. This is not copied from the plan.",
    )
    if mode == "participants":
        ids, label = _select_provider_ids(
            root,
            process,
            statuses=frozenset({"active"}),
            required=True,
            title="Record Implementation — Actual Provider",
        )
        return ids, None, None, label
    reason = select_one(
        "Record Implementation — No Human Provider",
        tuple(item[0] for item in _NO_HUMAN_PROVIDER_REASONS),
        tuple(item[1] for item in _NO_HUMAN_PROVIDER_REASONS),
        help_text="Record why this occurrence had no human provider.",
    )
    detail: str | None = None
    if reason == "other":
        detail = prompt_text(
            "Record Implementation — No Human Provider",
            "Reason detail",
            help_text="Briefly state the bounded reason.",
        )
    return (), reason, detail, f"No human provider — {reason.replace('_', ' ')}"


def _select_extra_variations() -> tuple[str, ...]:
    selected: list[str] = []
    choices = (
        ("timing_or_duration", "Timing or duration differed"),
        ("procedure", "Procedure differed"),
        ("context", "Context differed"),
        ("other", "Other difference"),
    )
    while True:
        remaining = tuple(item for item in choices if item[0] not in selected)
        if not remaining:
            return tuple(selected)
        choice = select_one(
            "Record Implementation — Other Variation",
            ("done",) + tuple(item[0] for item in remaining),
            ("No more variation categories",) + tuple(item[1] for item in remaining),
            help_text=(
                "Select only differences from the exact plan. Variation records difference; "
                "it does not evaluate Fidelity or effectiveness."
            ),
        )
        if choice == "done":
            return tuple(selected)
        selected.append(choice)


def record_implementation_once(
    state: MenuSessionContext,
    process: SupportProcessSelection,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one actual occurrence against an exact active Support/Intervention plan."""

    if process.status != "active":
        raise ValueError("Implementation recording requires an active Support Process.")
    root = state.resolve_workspace()
    operator = _require_operator(state, title="Record Implementation — Your Name")
    plans = _active_plan_options(root, process)
    if not plans:
        raise ValueError("No active Support or Intervention plans are available.")
    plan = select_one(
        "Record Implementation — Plan",
        plans,
        tuple(item.label for item in plans),
        help_text="Choose the exact plan this actual occurrence implements.",
    )
    actual_target, actual_target_label = _choose_target(
        root,
        process,
        statuses=frozenset({"active"}),
        title="Record Implementation — Actual Target",
    )
    provider_ids, no_provider_reason, no_provider_detail, provider_label = (
        _select_actual_provider(root, process)
    )
    execution_state = select_one(
        "Record Implementation — Execution",
        tuple(item[0] for item in _EXECUTION_STATES),
        tuple(item[1] for item in _EXECUTION_STATES),
        help_text="Record what actually occurred; this does not establish effectiveness.",
    )
    menu_clock = clock or MenuClock()
    started = _prompt_time(
        "Record Implementation — When",
        menu_clock,
        "Started at",
    )
    assert started is not None
    ended: ExplicitOffsetTimestamp | None = None
    if execution_state != "in_progress":
        ended = _prompt_time(
            "Record Implementation — When",
            menu_clock,
            "Ended at",
            optional=True,
        )
    summary = prompt_text(
        "Record Implementation — Summary",
        "Bounded occurrence summary",
        help_text="Describe the actual occurrence without evaluating success or Outcome.",
    )
    assert summary is not None

    variations: list[str] = []
    if _target_signature_from_input(actual_target) != _target_signature_from_record(
        plan.stored.record
    ):
        variations.append("target")
    if _actual_provider_signature(provider_ids) != _plan_provider_signature(
        plan.stored.record
    ):
        variations.append("provider")
    variations.extend(_select_extra_variations())
    variation_detail: str | None = None
    if variations:
        variation_detail = prompt_text(
            "Record Implementation — Variation",
            "Variation detail",
            help_text=(
                "Describe how the actual occurrence differed from the exact plan. "
                "This is not a Fidelity rating."
            ),
        )

    candidate = prepare_implementation(
        ImplementationAuthoringInput(
            work=process.work,
            plan_kind=plan.kind,
            plan_id=plan.plan_id,
            actual_target=actual_target,
            provider_participant_ids=provider_ids,
            no_human_provider_reason=no_provider_reason,
            no_human_provider_detail=no_provider_detail,
            execution_state=execution_state,
            started_at=started,
            ended_at=ended,
            variation_kinds=tuple(variations),
            variation_detail=variation_detail,
            summary=summary,
            local_operator_label=operator,
        ),
        clock=menu_clock,
        ids=ids or PortiaIdGenerator(),
    )
    variation_label = ", ".join(variations) if variations else "None recorded"
    if not confirm_write(
        "Record Implementation — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Exact plan: {plan.label}",
            f"Actual target: {actual_target_label}",
            f"Actual provider: {provider_label}",
            f"Execution: {execution_state.replace('_', ' ')}",
            f"Started: {started.text}",
            f"Ended: {ended.text if ended is not None else 'Not recorded'}",
            f"Variation: {variation_label}",
            f"Summary: {summary}",
            "",
            "Implementation records an actual occurrence. It does not prove Fidelity, "
            "effectiveness, progress, or Outcome.",
        ),
        help_text="RECORD creates only this exact Implementation occurrence.",
    ):
        return
    ImplementationWorkflowService(root).create(process.work, candidate)
    _show_result("Implementation Recorded", ("Implementation occurrence recorded.",))


def _implementation_options(
    root: Path,
    process: SupportProcessSelection,
) -> tuple[ImplementationOption, ...]:
    values: list[ImplementationOption] = []
    for stored in ImplementationWorkflowService(root).list(process.work):
        record = stored.record
        identifier = record.logical_id
        if identifier is None or record.status != "active":
            continue
        plan_ref = record.field("plan_ref")
        if not isinstance(plan_ref, Mapping):
            continue
        kind = plan_ref.get("record_kind")
        plan_id = plan_ref.get("record_id")
        if kind not in {"support", "intervention"} or not isinstance(plan_id, str):
            continue
        state = record.field("execution_state")
        summary = record.field("summary")
        label = (
            summary
            if isinstance(summary, str)
            else f"{str(state).replace('_', ' ').title()} implementation"
        )
        values.append(
            ImplementationOption(
                stored=stored,
                implementation_id=identifier,
                plan_kind=cast(Literal["support", "intervention"], kind),
                plan_id=plan_id,
                label=f"{label} — {str(state).replace('_', ' ').title()}",
            )
        )
    return tuple(values)


def record_fidelity_once(
    state: MenuSessionContext,
    process: SupportProcessSelection,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one Fidelity evaluation without inferring effectiveness or Outcome."""

    if process.status != "active":
        raise ValueError("Fidelity recording requires an active Support Process.")
    root = state.resolve_workspace()
    operator = _require_operator(state, title="Record Fidelity — Your Name")
    implementations = _implementation_options(root, process)
    if not implementations:
        raise ValueError("No active Implementation occurrences are available for Fidelity review.")
    implementation = select_one(
        "Record Fidelity — Implementation",
        implementations,
        tuple(item.label for item in implementations),
        help_text=(
            "Choose the exact Implementation occurrence being evaluated against its exact plan."
        ),
    )
    evaluators = _participants(root, process.work, statuses=frozenset({"active"}))
    if not evaluators:
        raise ValueError("No active Support Process Participant is available as evaluator.")
    evaluator = select_one(
        "Record Fidelity — Evaluator",
        evaluators,
        tuple(item.label for item in evaluators),
        help_text="Select the exact active Support Process Participant who performed this evaluation.",
    )
    result = select_one(
        "Record Fidelity — Result",
        tuple(item[0] for item in _FIDELITY_RESULTS),
        tuple(item[1] for item in _FIDELITY_RESULTS),
        help_text=(
            "Fidelity asks whether implementation matched the plan. It does not rate "
            "effectiveness, success, student progress, or Outcome."
        ),
    )
    basis_kind = select_one(
        "Record Fidelity — Basis",
        tuple(item[0] for item in _FIDELITY_BASES),
        tuple(item[1] for item in _FIDELITY_BASES),
        help_text="Choose the bounded basis used for this Fidelity evaluation.",
    )
    basis_detail: str | None = None
    if basis_kind in {"combined", "other"}:
        basis_detail = prompt_text(
            "Record Fidelity — Basis",
            "Basis detail",
            help_text="Briefly describe the bounded evaluation basis.",
        )
    include_basis = basis_kind in {
        "implementation_records",
        "record_review",
        "combined",
    }
    menu_clock = clock or MenuClock()
    evaluated = _prompt_time(
        "Record Fidelity — When",
        menu_clock,
        "Evaluated at",
    )
    assert evaluated is not None
    summary = prompt_text(
        "Record Fidelity — Summary",
        "Evaluation summary",
        help_text=(
            "Summarize the Fidelity evaluation without making an effectiveness or Outcome claim."
        ),
    )
    assert summary is not None
    candidate = prepare_fidelity(
        FidelityAuthoringInput(
            work=process.work,
            plan_kind=implementation.plan_kind,
            plan_id=implementation.plan_id,
            evaluator_participant_id=evaluator.participant_id,
            implementation_id=implementation.implementation_id,
            result=result,
            basis_kind=basis_kind,
            basis_detail=basis_detail,
            include_implementation_basis=include_basis,
            evaluated_at=evaluated,
            summary=summary,
            local_operator_label=operator,
        ),
        clock=menu_clock,
        ids=ids or PortiaIdGenerator(),
    )
    if not confirm_write(
        "Record Fidelity — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Implementation: {implementation.label}",
            f"Evaluator: {evaluator.label}",
            f"Result: {result.replace('_', ' ')}",
            f"Basis: {basis_kind.replace('_', ' ')}",
            f"Evaluated: {evaluated.text}",
            f"Summary: {summary}",
            "",
            "Fidelity records plan adherence only. It does not establish effectiveness, "
            "success, progress, causation, or Outcome.",
        ),
        help_text="RECORD creates only this exact Fidelity evaluation.",
    ):
        return
    FidelityWorkflowService(root).create(process.work, candidate)
    _show_result("Fidelity Recorded", ("Fidelity evaluation recorded.",))


def view_delivery_records_once(
    state: MenuSessionContext,
    process: SupportProcessSelection,
) -> None:
    """Read Intervention, Implementation, and Fidelity records without writing."""

    root = state.resolve_workspace()
    entries: list[str] = []
    for stored in InterventionWorkflowService(root).list(process.work):
        if stored.record.status not in {"proposed", "active"}:
            continue
        strategy = stored.record.field("strategy")
        procedure = strategy.get("procedure") if isinstance(strategy, Mapping) else "Intervention"
        entries.append(
            f"Intervention — {procedure} — {stored.record.status} / "
            f"{stored.record.field('plan_state')}"
        )
    for stored in ImplementationWorkflowService(root).list(process.work):
        if stored.record.status != "active":
            continue
        summary = stored.record.field("summary")
        entries.append(
            f"Implementation — {summary if isinstance(summary, str) else stored.record.logical_id} "
            f"— {stored.record.field('execution_state')}"
        )
    for stored in FidelityWorkflowService(root).list(process.work):
        if stored.record.status != "active":
            continue
        summary = stored.record.field("summary")
        entries.append(
            f"Fidelity — {summary if isinstance(summary, str) else stored.record.logical_id} "
            f"— {stored.record.field('result')}"
        )
    if not entries:
        _show_result(
            "Support Delivery / Fidelity",
            (
                "No current/proposed Intervention, Implementation, or Fidelity "
                "records are available.",
            ),
        )
        return

    pages = page_count(len(entries), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header("Support Delivery / Fidelity")
        print(f"Support Process: {process.summary}")
        print()
        for entry in page_items(entries, page_index, page_size=PAGE_SIZE):
            print(f"- {entry}")
        if pages > 1:
            print()
            print(f"Page {page_index + 1} of {pages}")
            if page_index + 1 < pages:
                print("N. Next page")
            if page_index > 0:
                print("P. Previous page")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        normalized = raw.casefold()
        if normalized == "n" and page_index + 1 < pages:
            page_index += 1
            continue
        if normalized == "p" and page_index > 0:
            page_index -= 1
            continue
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show_result(
                "Support Delivery / Fidelity Help",
                (
                    "This is a read-only view of exact canonical records.",
                    "Intervention is a plan; Implementation is an occurrence; "
                    "Fidelity evaluates plan adherence; none is an Outcome.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()
