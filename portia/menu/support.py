"""Teacher-facing Support Process foundation workflow."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, cast

from portia.menu.authoring import (
    HumanAttributionInput,
    SupportAuthoringInput,
    SupportGoalAuthoringInput,
    SupportNeedAuthoringInput,
    SupportParticipantAuthoringInput,
    SupportParticipantContextInput,
    SupportPlanTargetInput,
    SupportProcessAuthoringInput,
    SupportScheduleInput,
    prepare_support,
    prepare_support_goal,
    prepare_support_need,
    prepare_support_participant,
    prepare_support_participant_activation,
    prepare_support_process,
    prepare_support_process_activation,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    QuitPDS,
    ReturnToMainMenu,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import CancelMenuAction, confirm_write, prompt_text, select_one
from portia.menu.selectors import (
    ClassOption,
    StudentOption,
    class_options,
    student_options,
)
from portia.menu.ui import (
    PAGE_SIZE,
    clear_screen,
    page_count,
    page_items,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models import (
    PortiaRecord,
    SupportProcessParticipantV1,
    SupportProcessV1,
)
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaOperationPartialCommitError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.repository import StoredRecord
from portia.workflows import (
    PortiaWorkflowError,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    support_process_participant_reference,
)

_SUPPORT_CONTEXTS: tuple[tuple[str, str], ...] = (
    ("supported_person", "Person receiving/supporting the focus of support"),
    ("provider_or_collaborator", "Provider or collaborator"),
    ("family_or_support_person", "Family or support person"),
    ("coordinator", "Coordinator"),
    ("observer", "Observer"),
    ("other", "Other bounded context"),
)
_DESCRIPTION_TYPES: tuple[tuple[str, str], ...] = (
    ("outside_student", "Student outside the available roster"),
    ("family_member", "Family member"),
    ("school_staff", "School staff"),
    ("visitor", "Visitor"),
    ("community_member", "Community member"),
    ("other", "Other described person"),
)

_NEED_KINDS: tuple[tuple[str, str], ...] = (
    ("access", "Access"),
    ("environmental_or_instructional", "Environmental or instructional"),
    ("organizational_or_routine", "Organizational or routine"),
    ("skill_or_strategy", "Skill or strategy"),
    ("relationship_or_connection", "Relationship or connection"),
    ("resource_or_coordination", "Resource or coordination"),
    ("other", "Other bounded need"),
)
_SUPPORT_STRATEGIES: tuple[tuple[str, str], ...] = (
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
    ("access_condition", "Access condition — no individual provider assigned"),
    ("self_directed", "Self-directed"),
    ("resource_availability", "Resource availability"),
    ("other", "Other explicit reason"),
)


@dataclass(frozen=True, slots=True)
class SupportProcessOption:
    """One exact routine Support Process selection."""

    work: ExactPortiaWorkRef
    stored: StoredRecord
    summary: str
    status: str
    workflow_state: str
    label: str


@dataclass(frozen=True, slots=True)
class SupportParticipantOption:
    """One exact current/proposed Support Process Participant selection."""

    stored: StoredRecord
    participant_id: str
    person_label: str
    context_label: str
    status: str
    label: str


@dataclass(frozen=True, slots=True)
class SupportNeedOption:
    """One exact Support Need selection."""

    stored: StoredRecord
    need_id: str
    description: str
    status: str
    label: str


@dataclass(frozen=True, slots=True)
class SupportGoalOption:
    """One exact Support Goal selection."""

    stored: StoredRecord
    goal_id: str
    description: str
    status: str
    label: str


@dataclass(frozen=True, slots=True)
class SupportPlanOption:
    """One exact Support planning record for display."""

    stored: StoredRecord
    support_id: str
    procedure: str
    status: str
    plan_state: str
    label: str


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


def _choose_class(root: Path, *, title: str) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError("No Core classes with both metadata and rosters are available.")
    return select_one(
        title,
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact Core class that owns this teacher-local Support Process. "
            "Participant identity does not change the owner."
        ),
    )


def _support_process_options(root: Path, class_id: str) -> tuple[SupportProcessOption, ...]:
    service = SupportProcessWorkflowService(root)
    preliminary: list[tuple[ExactPortiaWorkRef, StoredRecord, str, str, str, str]] = []
    for stored in service.list(class_id):
        record = stored.record
        status_value = record.status
        work_id = record.work_id
        if status_value not in {"proposed", "active"} or work_id is None:
            continue
        summary_value = record.field("summary")
        summary = summary_value if isinstance(summary_value, str) else "Support Process"
        workflow_value = record.field("workflow_state")
        workflow_state = workflow_value if isinstance(workflow_value, str) else "unknown"
        status = status_value
        label = f"{summary} — {status.title()} / {workflow_state.replace('_', ' ').title()}"
        work = ExactPortiaWorkRef(
            class_id=class_id,
            work_id=work_id,
            work_kind="support_process",
            contract_version="1",
        )
        preliminary.append((work, stored, summary, status, workflow_state, label))
    counts = Counter(item[5].casefold() for item in preliminary)
    options: list[SupportProcessOption] = []
    for work, stored, summary, status, workflow_state, label in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact Support Process {work.work_id}"
        options.append(
            SupportProcessOption(
                work=work,
                stored=stored,
                summary=summary,
                status=status,
                workflow_state=workflow_state,
                label=label,
            )
        )
    return tuple(options)


def _choose_support_process(root: Path, state: MenuSessionContext) -> SupportProcessOption:
    owner = _choose_class(root, title="Manage Support — Class")
    options = _support_process_options(root, owner.class_id)
    if not options:
        raise ValueError(f"No proposed or active Support Processes are available in {owner.class_id!r}.")
    selected = select_one(
        "Manage Support — Open Process",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact Support Process. Summary text is presentation only; "
            "the numbered choice carries canonical identity."
        ),
    )
    state.remember_work(
        class_id=selected.work.class_id,
        work_kind="support_process",
        work_id=selected.work.work_id,
    )
    return selected


def _prompt_date(title: str, label: str) -> str | None:
    while True:
        value = prompt_text(
            title,
            label,
            help_text="Optional. Leave blank or enter a calendar date as YYYY-MM-DD.",
            optional=True,
        )
        if value is None:
            return None
        try:
            date.fromisoformat(value)
        except ValueError:
            _show_result(title, ("That date is invalid. Use YYYY-MM-DD.",))
            continue
        return value


def create_support_process_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Create one proposed/planning Support Process root and nothing downstream."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    owner = _choose_class(root, title="Create Support Process — Owning Class")
    operator = _require_operator(state, title="Create Support Process — Your Name")
    summary = prompt_text(
        "Create Support Process — Summary",
        "Neutral summary",
        help_text=(
            "Describe the bounded teacher-local support focus. Do not present this as an IEP, "
            "504 plan, clinical plan, diagnosis, eligibility decision, risk label, or Outcome."
        ),
    )
    assert summary is not None
    initiation_detail = prompt_text(
        "Create Support Process — Why Start",
        "Teacher-identified need",
        help_text=(
            "Record the teacher-local reason for opening planning. This creates context only; "
            "it does not create a canonical Support Need record."
        ),
    )
    assert initiation_detail is not None
    planned_start = _prompt_date("Create Support Process — Dates", "Planned start date")
    planned_end = _prompt_date("Create Support Process — Dates", "Planned end date")
    review_on = _prompt_date("Create Support Process — Dates", "Review date")
    candidate = prepare_support_process(
        SupportProcessAuthoringInput(
            owner_class_id=owner.class_id,
            school_year=owner.school_year,
            summary=summary,
            initiation_detail=initiation_detail,
            local_operator_label=operator,
            planned_start_date=planned_start,
            planned_end_date=planned_end,
            review_on=review_on,
        ),
        clock=menu_clock,
        ids=id_generator,
    )
    lines: list[str] = [
        f"Owning class: {owner.class_id}",
        f"School year: {owner.school_year}",
        f"Summary: {summary}",
        f"Why planning starts: {initiation_detail}",
    ]
    if planned_start is not None:
        lines.append(f"Planned start: {planned_start}")
    if planned_end is not None:
        lines.append(f"Planned end: {planned_end}")
    if review_on is not None:
        lines.append(f"Review on: {review_on}")
    lines.extend(
        (
            "",
            "This creates one proposed Support Process in planning state.",
            "It does not create participants, needs, goals, supports, interventions, implementation, fidelity, Follow-Up, or Outcome.",
        )
    )
    if not confirm_write(
        "Create Support Process — Review",
        "CREATE",
        tuple(lines),
        help_text=(
            "CREATE commits only the proposed Support Process root. Later confirmed steps are "
            "separate canonical writes and remain committed if setup is paused."
        ),
    ):
        return
    created = SupportProcessWorkflowService(root).create(candidate)
    if created.record.work_id is None:
        raise ValueError("created Support Process has no exact work identity")
    state.remember_work(
        class_id=owner.class_id,
        work_kind="support_process",
        work_id=created.record.work_id,
    )
    _show_result(
        "Support Process Created",
        (
            "Proposed Support Process created in planning state.",
            "No participant or planning child record was created automatically.",
            "Open the process to add participants and continue setup explicitly.",
        ),
    )


def _choose_roster_person(root: Path) -> tuple[HumanAttributionInput, str]:
    source_class = _choose_class(root, title="Support Participant — Roster Class")
    students = student_options(root, source_class.class_id)
    if not students:
        raise ValueError(f"The selected Core class {source_class.class_id!r} has no students.")
    student: StudentOption = select_one(
        "Support Participant — Roster Student",
        students,
        tuple(item.label for item in students),
        help_text=(
            "Choose exact class_id + student_id identity. A cross-class participant does not "
            "change Support Process ownership."
        ),
    )
    return (
        HumanAttributionInput(
            kind="roster_student",
            class_id=student.class_id,
            student_id=student.student_id,
            display_name=student.display_name,
        ),
        student.display_name,
    )


def _choose_descriptive_person() -> tuple[HumanAttributionInput, str]:
    description_type = select_one(
        "Support Participant — Person Type",
        tuple(item[0] for item in _DESCRIPTION_TYPES),
        tuple(item[1] for item in _DESCRIPTION_TYPES),
        help_text=(
            "Use descriptive identity only when no exact roster or Actor identity is available. "
            "The label is presentation, not a new directory identity."
        ),
    )
    label = prompt_text(
        "Support Participant — Person",
        "Display label",
        help_text="Enter a concise human-readable label.",
    )
    assert label is not None
    detail: str | None = None
    if description_type == "other":
        detail = prompt_text(
            "Support Participant — Person",
            "Detail",
            help_text="Briefly clarify the represented person type.",
        )
        assert detail is not None
    return (
        HumanAttributionInput(
            kind="descriptive_person",
            description_type=description_type,
            display_label=label,
            detail=detail,
        ),
        label,
    )


def _choose_support_person(
    root: Path,
    state: MenuSessionContext,
) -> tuple[HumanAttributionInput, str]:
    kind = select_one(
        "Support Participant — Person",
        ("roster", "operator", "descriptive"),
        ("Roster student", "This local operator", "Another described person"),
        help_text=(
            "Select the represented human explicitly. This does not create an Event relationship, "
            "Actor, need, goal, or institutional role."
        ),
    )
    if kind == "roster":
        return _choose_roster_person(root)
    if kind == "operator":
        label = _require_operator(state, title="Support Participant — Your Name")
        return HumanAttributionInput(kind="local_operator", display_label=label), label
    return _choose_descriptive_person()


def _choose_context() -> SupportParticipantContextInput:
    kind = select_one(
        "Support Participant — Context",
        tuple(item[0] for item in _SUPPORT_CONTEXTS),
        tuple(item[1] for item in _SUPPORT_CONTEXTS),
        help_text=(
            "Choose this person's explicit context in the Support Process. Context does not prove "
            "need, service delivery, authority, participation in an external plan, or effectiveness."
        ),
    )
    detail: str | None = None
    if kind == "other":
        detail = prompt_text(
            "Support Participant — Context",
            "Context detail",
            help_text="Briefly describe the bounded participation context.",
        )
        assert detail is not None
    return SupportParticipantContextInput(kind=kind, detail=detail)


def _collect_contexts() -> tuple[SupportParticipantContextInput, ...]:
    selected: list[SupportParticipantContextInput] = []
    while True:
        context = _choose_context()
        if context not in selected:
            selected.append(context)
        again = select_one(
            "Support Participant — Contexts",
            (False, True),
            ("Continue", "Add another context"),
            help_text="Add only contexts that are explicitly applicable to this person.",
        )
        if not again:
            return tuple(selected)


def add_support_participant_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Create one proposed Support Process Participant as a separate confirmed write."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    operator = _require_operator(state, title="Add Support Participant — Your Name")
    person, person_label = _choose_support_person(root, state)
    contexts = _collect_contexts()
    candidate = prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=process.work,
            person=person,
            contexts=contexts,
            local_operator_label=operator,
        ),
        clock=menu_clock,
        ids=id_generator,
    )
    context_text = ", ".join(item.kind.replace("_", " ") for item in contexts)
    if not confirm_write(
        "Add Support Participant — Review",
        "ADD",
        (
            f"Support Process: {process.summary}",
            f"Person: {person_label}",
            f"Contexts: {context_text}",
            "",
            "This creates one proposed Participant. It does not activate the person or the Support Process.",
        ),
        help_text=(
            "ADD commits only this Participant. Existing confirmed Support Process state remains "
            "committed if setup stops afterward."
        ),
    ):
        return
    SupportProcessParticipantWorkflowService(root).create(process.work, candidate)
    _show_result(
        "Support Participant Added",
        (
            "Proposed Support Process Participant added.",
            "Activation remains a separate explicit lifecycle action.",
        ),
    )


def _person_label(record: PortiaRecord) -> str:
    person = record.field("person")
    if not isinstance(person, Mapping):
        return "Participant"
    kind = person.get("kind")
    if kind == "roster_student":
        snapshot = person.get("display_snapshot")
        display = snapshot.get("display_name") if isinstance(snapshot, Mapping) else None
        return display if isinstance(display, str) else "Roster student"
    if kind == "local_operator":
        label = person.get("display_label")
        return label if isinstance(label, str) else "Local operator"
    if kind == "descriptive_person":
        label = person.get("display_label")
        return label if isinstance(label, str) else "Described person"
    if kind == "actor":
        snapshot = person.get("display_snapshot")
        display = snapshot.get("display_name") if isinstance(snapshot, Mapping) else None
        return display if isinstance(display, str) else "Actor"
    if kind == "unidentified_person":
        label = person.get("display_label")
        return label if isinstance(label, str) else "Unidentified person"
    return "Participant"


def _context_label(record: PortiaRecord) -> str:
    contexts = record.field("contexts")
    if not isinstance(contexts, tuple):
        return "context unavailable"
    values: list[str] = []
    for item in contexts:
        if not isinstance(item, Mapping):
            continue
        kind = item.get("kind")
        if isinstance(kind, str):
            values.append(kind.replace("_", " "))
    return ", ".join(values) if values else "context unavailable"


def _participant_options(
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    statuses: frozenset[str] = frozenset({"proposed", "active"}),
) -> tuple[SupportParticipantOption, ...]:
    service = SupportProcessParticipantWorkflowService(root)
    preliminary: list[SupportParticipantOption] = []
    for stored in service.list(work):
        record = stored.record
        status_value = record.status
        participant_id = record.logical_id
        if status_value not in statuses or participant_id is None:
            continue
        person = _person_label(record)
        context = _context_label(record)
        preliminary.append(
            SupportParticipantOption(
                stored=stored,
                participant_id=participant_id,
                person_label=person,
                context_label=context,
                status=status_value,
                label=f"{person} — {context} — {status_value.title()}",
            )
        )
    counts = Counter(item.label.casefold() for item in preliminary)
    return tuple(
        SupportParticipantOption(
            stored=item.stored,
            participant_id=item.participant_id,
            person_label=item.person_label,
            context_label=item.context_label,
            status=item.status,
            label=(
                item.label
                if counts[item.label.casefold()] == 1
                else f"{item.label} — exact participant {item.participant_id}"
            ),
        )
        for item in preliminary
    )


def view_support_participants_once(state: MenuSessionContext, process: SupportProcessOption) -> None:
    """Render bounded Participant state without mutation."""

    root = state.resolve_workspace()
    options = _participant_options(root, process.work)
    if not options:
        _show_result("Support Participants", ("No current/proposed participants are recorded.",))
        return
    pages = page_count(len(options), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header("Support Participants")
        print(f"Support Process: {process.summary}")
        print()
        for item in page_items(options, page_index, page_size=PAGE_SIZE):
            print(f"- {item.person_label} — {item.context_label} — {item.status}")
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
                "Support Participants Help",
                (
                    "This is a read-only view of exact Participant records.",
                    "Participant context does not establish need, implementation, fidelity, or Outcome.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def activate_support_participant_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Activate one exact proposed Participant through coordinated lifecycle authority."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    operator = _require_operator(state, title="Activate Support Participant — Your Name")
    options = _participant_options(root, process.work, statuses=frozenset({"proposed"}))
    if not options:
        raise ValueError("No proposed Support Process Participants are available to activate.")
    selected = select_one(
        "Activate Support Participant",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Activation makes this exact Participant eligible for current Support Process use. "
            "It does not activate the Support Process root."
        ),
    )
    record = selected.stored.record
    if not isinstance(record, SupportProcessParticipantV1):
        raise ValueError("selected Participant is not support_process_participant@1")
    prepared = prepare_support_participant_activation(
        record,
        local_operator_label=operator,
        clock=menu_clock,
        ids=id_generator,
    )
    if not confirm_write(
        "Activate Support Participant — Review",
        "ACTIVATE",
        (
            f"Support Process: {process.summary}",
            f"Person: {selected.person_label}",
            f"Contexts: {selected.context_label}",
            "",
            "Activation does not establish a need, goal, service delivery, fidelity, or Outcome.",
        ),
        help_text="ACTIVATE performs one coordinated Participant lifecycle write.",
    ):
        return
    SupportProcessParticipantWorkflowService(root).transition_lifecycle(
        support_process_participant_reference(process.work, selected.participant_id),
        prepared.candidate,
        expected=selected.stored.fingerprint,
        transition_id=prepared.transition_id,
        reason_code="planning_confirmed",
        operation_id=prepared.operation_id,
    )
    _show_result("Support Participant Activated", ("Participant activated for current use.",))


def activate_support_process_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Activate one exact proposed root after existing service preflight succeeds."""

    if process.status != "proposed":
        raise ValueError("The selected Support Process is not proposed and cannot be activated here.")
    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    operator = _require_operator(state, title="Activate Support Process — Your Name")
    current = SupportProcessWorkflowService(root).load_exact(process.work)
    if not isinstance(current.record, SupportProcessV1):
        raise ValueError("selected Support Process is not support_process@1")
    prepared = prepare_support_process_activation(
        current.record,
        local_operator_label=operator,
        clock=menu_clock,
        ids=id_generator,
    )
    if not confirm_write(
        "Activate Support Process — Review",
        "ACTIVATE",
        (
            f"Support Process: {process.summary}",
            "",
            "Activation requires at least one eligible active supported-person Participant.",
            "Canonical activation does not prove implementation, fidelity, effectiveness, or Outcome.",
            "The Support Process workflow remains in its explicit planning state until separately progressed.",
        ),
        help_text="ACTIVATE delegates all eligibility and Dependency gates to SupportProcessWorkflowService.",
    ):
        return
    SupportProcessWorkflowService(root).transition_lifecycle(
        process.work,
        prepared.candidate,
        expected=current.fingerprint,
        transition_id=prepared.transition_id,
        reason_code="planning_confirmed",
        operation_id=prepared.operation_id,
    )
    _show_result(
        "Support Process Activated",
        (
            "Support Process canonical lifecycle activated.",
            "No Need, Goal, Support, Intervention, Implementation, Fidelity, Follow-Up, or Outcome was created automatically.",
        ),
    )


def _planning_status(process: SupportProcessOption) -> Literal["proposed", "active"]:
    if process.status == "proposed":
        return "proposed"
    if process.status == "active":
        return "active"
    raise ValueError("Support planning requires a proposed or active Support Process")


def _choose_planning_target(
    root: Path,
    process: SupportProcessOption,
    *,
    title: str,
) -> tuple[SupportPlanTargetInput, str]:
    statuses = (
        frozenset({"active"})
        if process.status == "active"
        else frozenset({"proposed", "active"})
    )
    participants = _participant_options(root, process.work, statuses=statuses)
    values: list[tuple[SupportPlanTargetInput, str]] = [
        (SupportPlanTargetInput(kind="support_process"), "Whole Support Process")
    ]
    values.extend(
        (
            SupportPlanTargetInput(
                kind="support_process_participant",
                participant_id=item.participant_id,
            ),
            item.person_label,
        )
        for item in participants
    )
    return select_one(
        title,
        tuple(values),
        tuple(label for _value, label in values),
        help_text=(
            "Choose the exact planning target. A target identifies scope only; it does not "
            "assign a role, establish delivery, or assert an Outcome."
        ),
    )


def _need_options(
    root: Path,
    process: SupportProcessOption,
    *,
    statuses: frozenset[str],
) -> tuple[SupportNeedOption, ...]:
    values: list[SupportNeedOption] = []
    for stored in SupportNeedWorkflowService(root).list(process.work):
        record = stored.record
        identifier = record.logical_id
        status = record.status
        description = record.field("description")
        if (
            identifier is None
            or not isinstance(status, str)
            or status not in statuses
            or not isinstance(description, str)
        ):
            continue
        values.append(
            SupportNeedOption(
                stored=stored,
                need_id=identifier,
                description=description,
                status=status,
                label=f"{description} — {status.title()}",
            )
        )
    return tuple(values)


def _goal_options(
    root: Path,
    process: SupportProcessOption,
    *,
    statuses: frozenset[str],
) -> tuple[SupportGoalOption, ...]:
    values: list[SupportGoalOption] = []
    for stored in SupportGoalWorkflowService(root).list(process.work):
        record = stored.record
        identifier = record.logical_id
        status = record.status
        description = record.field("description")
        if (
            identifier is None
            or not isinstance(status, str)
            or status not in statuses
            or not isinstance(description, str)
        ):
            continue
        values.append(
            SupportGoalOption(
                stored=stored,
                goal_id=identifier,
                description=description,
                status=status,
                label=f"{description} — {status.title()}",
            )
        )
    return tuple(values)


def _support_options(root: Path, process: SupportProcessOption) -> tuple[SupportPlanOption, ...]:
    values: list[SupportPlanOption] = []
    for stored in SupportWorkflowService(root).list(process.work):
        record = stored.record
        identifier = record.logical_id
        status = record.status
        strategy = record.field("strategy")
        plan_state = record.field("plan_state")
        procedure = strategy.get("procedure") if isinstance(strategy, Mapping) else None
        if (
            identifier is None
            or not isinstance(status, str)
            or status not in {"proposed", "active"}
            or not isinstance(plan_state, str)
            or not isinstance(procedure, str)
        ):
            continue
        values.append(
            SupportPlanOption(
                stored=stored,
                support_id=identifier,
                procedure=procedure,
                status=status,
                plan_state=plan_state,
                label=(
                    f"{procedure} — {status.title()} / "
                    f"{plan_state.replace('_', ' ').title()}"
                ),
            )
        )
    return tuple(values)


def record_support_need_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one bounded Support Need without diagnostic or eligibility inference."""

    root = state.resolve_workspace()
    operator = _require_operator(state, title="Record Support Need — Your Name")
    target, target_label = _choose_planning_target(
        root, process, title="Record Support Need — Target"
    )
    need_kind = select_one(
        "Record Support Need — Kind",
        tuple(item[0] for item in _NEED_KINDS),
        tuple(item[1] for item in _NEED_KINDS),
        help_text=(
            "Choose a bounded teacher-local planning category. This is not a diagnosis, "
            "eligibility code, risk level, or institutional determination."
        ),
    )
    kind_detail: str | None = None
    if need_kind == "other":
        kind_detail = prompt_text(
            "Record Support Need — Kind",
            "Need kind detail",
            help_text=(
                "Describe the bounded category without converting it into a diagnosis "
                "or eligibility claim."
            ),
        )
    description = prompt_text(
        "Record Support Need — Description",
        "Need description",
        help_text=(
            "Describe what access, condition, resource, routine, skill, strategy, or "
            "coordination need is being planned for. Record only the human-entered need statement."
        ),
    )
    assert description is not None
    status = _planning_status(process)
    candidate = prepare_support_need(
        SupportNeedAuthoringInput(
            work=process.work,
            status=status,
            target=target,
            need_kind=need_kind,
            description=description,
            kind_detail=kind_detail,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    if not confirm_write(
        "Record Support Need — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Target: {target_label}",
            f"Need kind: {need_kind.replace('_', ' ')}",
            f"Description: {description}",
            f"Canonical status: {status}",
            "",
            "A Need is a planning record. It does not establish diagnosis, eligibility, "
            "severity, service delivery, or Outcome.",
        ),
        help_text="RECORD creates only this exact Support Need.",
    ):
        return
    SupportNeedWorkflowService(root).create(process.work, candidate)
    _show_result("Support Need Recorded", ("Support Need recorded.",))


def record_support_goal_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one future-facing Support Goal without progress or attainment inference."""

    root = state.resolve_workspace()
    operator = _require_operator(state, title="Record Support Goal — Your Name")
    target, target_label = _choose_planning_target(
        root, process, title="Record Support Goal — Target"
    )
    description = prompt_text(
        "Record Support Goal — Description",
        "Future objective",
        help_text=(
            "State the future support objective. This field is a plan; it does not say the goal "
            "has been met or that progress has occurred."
        ),
    )
    assert description is not None
    criteria = prompt_text(
        "Record Support Goal — Criteria",
        "Planned criteria",
        help_text="Optional planned criteria for later review; this is not a current result.",
        optional=True,
    )
    measurement = prompt_text(
        "Record Support Goal — Measurement",
        "Planned measurement approach",
        help_text=(
            "Optional plan for later observation or review; this does not create an Outcome."
        ),
        optional=True,
    )
    status = _planning_status(process)
    candidate = prepare_support_goal(
        SupportGoalAuthoringInput(
            work=process.work,
            status=status,
            target=target,
            description=description,
            planned_criteria=criteria,
            measurement_approach=measurement,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    if not confirm_write(
        "Record Support Goal — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Target: {target_label}",
            f"Future objective: {description}",
            f"Canonical status: {status}",
            "",
            "A Goal describes planned future direction. It does not record progress, attainment, "
            "effectiveness, or Outcome.",
        ),
        help_text="RECORD creates only this exact Support Goal.",
    ):
        return
    SupportGoalWorkflowService(root).create(process.work, candidate)
    _show_result("Support Goal Recorded", ("Support Goal recorded.",))


def _select_needs_for_support(
    root: Path, process: SupportProcessOption
) -> tuple[SupportNeedOption, ...]:
    statuses = (
        frozenset({"active"})
        if process.status == "active"
        else frozenset({"proposed", "active"})
    )
    available = list(_need_options(root, process, statuses=statuses))
    if not available:
        raise ValueError("Record at least one eligible Support Need before planning a Support.")
    selected: list[SupportNeedOption] = []
    while available:
        choice = select_one(
            "Plan Support — Need",
            tuple(available),
            tuple(item.label for item in available),
            help_text="Select an exact Need this Support is intended to address.",
        )
        selected.append(choice)
        available = [item for item in available if item.need_id != choice.need_id]
        if not available:
            break
        more = select_one(
            "Plan Support — Needs",
            (False, True),
            ("Continue with selected Needs", "Add another Need"),
            help_text="Link only Needs this planned Support explicitly addresses.",
        )
        if not more:
            break
    return tuple(selected)


def _select_goals_for_support(
    root: Path, process: SupportProcessOption
) -> tuple[SupportGoalOption, ...]:
    statuses = (
        frozenset({"active"})
        if process.status == "active"
        else frozenset({"proposed", "active"})
    )
    available = list(_goal_options(root, process, statuses=statuses))
    if not available:
        return ()
    link = select_one(
        "Plan Support — Goals",
        (False, True),
        ("Do not link a Goal", "Link one or more Goals"),
        help_text="Goal linkage is optional and does not assert progress or attainment.",
    )
    if not link:
        return ()
    selected: list[SupportGoalOption] = []
    while available:
        choice = select_one(
            "Plan Support — Goal",
            tuple(available),
            tuple(item.label for item in available),
            help_text="Select an exact future-facing Goal this Support is intended to serve.",
        )
        selected.append(choice)
        available = [item for item in available if item.goal_id != choice.goal_id]
        if not available:
            break
        more = select_one(
            "Plan Support — Goals",
            (False, True),
            ("Continue with selected Goals", "Add another Goal"),
            help_text="Link only Goals explicitly served by this plan.",
        )
        if not more:
            break
    return tuple(selected)


def _select_provider_plan(
    root: Path, process: SupportProcessOption
) -> tuple[tuple[str, ...], str | None, str | None, str]:
    statuses = (
        frozenset({"active"})
        if process.status == "active"
        else frozenset({"proposed", "active"})
    )
    participants = list(_participant_options(root, process.work, statuses=statuses))
    assigned = select_one(
        "Plan Support — Provider",
        (False, True),
        ("No individual provider assigned", "Assign Support Process participant(s)"),
        help_text=(
            "Provider planning is explicit. Assignment does not establish actual implementation, "
            "attendance, fidelity, or effectiveness."
        ),
    )
    if assigned:
        if not participants:
            raise ValueError(
                "No eligible Support Process Participants are available for provider assignment."
            )
        selected: list[SupportParticipantOption] = []
        available = participants
        while available:
            choice = select_one(
                "Plan Support — Provider",
                tuple(available),
                tuple(item.label for item in available),
                help_text=(
                    "Select an exact Support Process Participant as a planned provider/collaborator."
                ),
            )
            selected.append(choice)
            available = [
                item for item in available if item.participant_id != choice.participant_id
            ]
            if not available:
                break
            more = select_one(
                "Plan Support — Providers",
                (False, True),
                ("Continue with selected providers", "Add another provider"),
                help_text="Add only participants explicitly assigned in this plan.",
            )
            if not more:
                break
        return (
            tuple(item.participant_id for item in selected),
            None,
            None,
            ", ".join(item.person_label for item in selected),
        )
    reason = select_one(
        "Plan Support — No Assigned Provider",
        tuple(item[0] for item in _NO_PROVIDER_REASONS),
        tuple(item[1] for item in _NO_PROVIDER_REASONS),
        help_text="Record why this plan has no individually assigned provider.",
    )
    detail: str | None = None
    if reason == "other":
        detail = prompt_text(
            "Plan Support — No Assigned Provider",
            "Reason detail",
            help_text="Briefly state the bounded reason no provider is assigned.",
        )
    return (), reason, detail, f"No assigned provider — {reason.replace('_', ' ')}"


def _prompt_positive_int(title: str, label: str, *, help_text: str) -> int:
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
            help_text="Optional planning duration. This does not record actual time delivered.",
            optional=True,
        )
        if value is None:
            return None
        if value.isdigit() and 1 <= int(value) <= 10080:
            return int(value)
        _show_result(title, ("Duration must be a whole number from 1 through 10080.",))


def _choose_support_schedule() -> tuple[SupportScheduleInput, str]:
    kind = cast(
        Literal["as_needed", "recurring", "condition_triggered", "custom"],
        select_one(
            "Plan Support — Schedule",
            ("as_needed", "recurring", "condition_triggered", "custom"),
            ("As needed", "Recurring", "Condition triggered", "Custom description"),
            help_text=(
                "This is a planned schedule only. Calendar recurrence or a trigger does not create "
                "an Implementation record."
            ),
        ),
    )
    minutes = _prompt_optional_minutes("Plan Support — Schedule")
    if kind == "as_needed":
        return SupportScheduleInput(kind="as_needed", planned_minutes=minutes), "As needed"
    if kind == "recurring":
        occurrences = _prompt_positive_int(
            "Plan Support — Recurrence",
            "Occurrences",
            help_text="Planned number of occurrences; this is not an implementation count.",
        )
        interval_count = _prompt_positive_int(
            "Plan Support — Recurrence",
            "Every how many units",
            help_text="Enter the planned interval count.",
        )
        unit = select_one(
            "Plan Support — Recurrence",
            ("day", "week", "month"),
            ("Day(s)", "Week(s)", "Month(s)"),
            help_text="Choose the planned recurrence unit.",
        )
        return (
            SupportScheduleInput(
                kind="recurring",
                planned_minutes=minutes,
                occurrences=occurrences,
                interval_count=interval_count,
                interval_unit=unit,
            ),
            f"{occurrences} occurrence(s), every {interval_count} {unit}(s)",
        )
    if kind == "condition_triggered":
        trigger = prompt_text(
            "Plan Support — Trigger",
            "Trigger condition",
            help_text="Describe the bounded condition that calls for the planned Support.",
        )
        assert trigger is not None
        return (
            SupportScheduleInput(
                kind="condition_triggered", planned_minutes=minutes, trigger=trigger
            ),
            f"Condition triggered — {trigger}",
        )
    description = prompt_text(
        "Plan Support — Schedule",
        "Custom schedule description",
        help_text="Describe the planned schedule without claiming implementation occurred.",
    )
    assert description is not None
    return (
        SupportScheduleInput(
            kind="custom", planned_minutes=minutes, description=description
        ),
        f"Custom — {description}",
    )


def record_support_once(
    state: MenuSessionContext,
    process: SupportProcessOption,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Record one Support plan without creating implementation or effectiveness evidence."""

    root = state.resolve_workspace()
    operator = _require_operator(state, title="Plan Support — Your Name")
    target, target_label = _choose_planning_target(
        root, process, title="Plan Support — Target"
    )
    needs = _select_needs_for_support(root, process)
    goals = _select_goals_for_support(root, process)
    strategy_kind = select_one(
        "Plan Support — Strategy",
        tuple(item[0] for item in _SUPPORT_STRATEGIES),
        tuple(item[1] for item in _SUPPORT_STRATEGIES),
        help_text=(
            "Choose the bounded type of planned Support; this is not an Intervention record."
        ),
    )
    strategy_detail: str | None = None
    if strategy_kind == "other":
        strategy_detail = prompt_text(
            "Plan Support — Strategy",
            "Strategy detail",
            help_text="Describe the bounded strategy category.",
        )
    procedure = prompt_text(
        "Plan Support — Procedure",
        "Planned procedure",
        help_text=(
            "Describe what is planned. Do not record implementation, fidelity, or effectiveness here."
        ),
    )
    assert procedure is not None
    provider_ids, no_provider_reason, no_provider_detail, provider_label = (
        _select_provider_plan(root, process)
    )
    schedule, schedule_label = _choose_support_schedule()
    status = _planning_status(process)
    candidate = prepare_support(
        SupportAuthoringInput(
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
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    goal_text = ", ".join(item.description for item in goals) if goals else "None linked"
    if not confirm_write(
        "Plan Support — Review",
        "RECORD",
        (
            f"Support Process: {process.summary}",
            f"Target: {target_label}",
            f"Need(s): {', '.join(item.description for item in needs)}",
            f"Goal(s): {goal_text}",
            f"Strategy: {strategy_kind.replace('_', ' ')}",
            f"Procedure: {procedure}",
            f"Provider plan: {provider_label}",
            f"Schedule: {schedule_label}",
            f"Canonical status: {status}",
            "",
            "This records a Support plan only. It does not create an Intervention, "
            "Implementation, Fidelity, Follow-Up, or Outcome.",
        ),
        help_text="RECORD creates only this exact Support planning record.",
    ):
        return
    SupportWorkflowService(root).create(process.work, candidate)
    _show_result("Support Planned", ("Support planning record created.",))


def view_support_planning_once(state: MenuSessionContext, process: SupportProcessOption) -> None:
    """Read Needs, Goals, and Supports without changing canonical state."""

    root = state.resolve_workspace()
    entries: list[str] = []
    entries.extend(
        f"Need — {item.description} — {item.status}"
        for item in _need_options(
            root, process, statuses=frozenset({"proposed", "active"})
        )
    )
    entries.extend(
        f"Goal — {item.description} — {item.status}"
        for item in _goal_options(
            root, process, statuses=frozenset({"proposed", "active"})
        )
    )
    entries.extend(
        f"Support — {item.procedure} — {item.status} / {item.plan_state}"
        for item in _support_options(root, process)
    )
    if not entries:
        _show_result(
            "Support Planning",
            ("No current/proposed Needs, Goals, or Supports are recorded.",),
        )
        return
    pages = page_count(len(entries), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header("Support Planning")
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
                "Support Planning Help",
                (
                    "This is a read-only view of exact planning records.",
                    "Need is not Goal; Support plan is not Implementation; none of these records "
                    "is an Outcome.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _open_process_menu(state: MenuSessionContext, process: SupportProcessOption) -> None:
    while True:
        clear_screen()
        print_menu_header("Manage Support — Open Process")
        print(f"Support Process: {process.summary}")
        print(f"Canonical status: {process.status}")
        print(f"Workflow state: {process.workflow_state}")
        print()
        print("1. View participants")
        print("2. Add participant")
        print("3. Activate participant")
        if process.status == "proposed":
            print("4. Activate Support Process")
        print("5. Record Support Need")
        print("6. Record Support Goal")
        print("7. Plan Support")
        print("8. View Needs / Goals / Supports")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show_result(
                "Open Support Process Help",
                (
                    "Support setup is incremental. Each confirmed write is canonical on its own.",
                    "Participant activation and Support Process activation are separate lifecycle actions.",
                    "Need, Goal, and Support are separate planning families.",
                    "A Support plan does not create Intervention, Implementation, Fidelity, Follow-Up, or Outcome records.",
                ),
            )
            continue
        if navigation is NavigationChoice.BACK:
            return
        try:
            if raw == "1":
                view_support_participants_once(state, process)
            elif raw == "2":
                add_support_participant_once(state, process)
            elif raw == "3":
                activate_support_participant_once(state, process)
            elif raw == "4" and process.status == "proposed":
                activate_support_process_once(state, process)
                return
            elif raw == "5":
                record_support_need_once(state, process)
            elif raw == "6":
                record_support_goal_once(state, process)
            elif raw == "7":
                record_support_once(state, process)
            elif raw == "8":
                view_support_planning_once(state, process)
            else:
                print(navigation_hint_with_help())
                pause_for_user()
        except CancelMenuAction:
            continue


def open_support_process_once(state: MenuSessionContext) -> None:
    root = state.resolve_workspace()
    process = _choose_support_process(root, state)
    _open_process_menu(state, process)


def _run_action(action: str, state: MenuSessionContext) -> None:
    if action == "create":
        create_support_process_once(state)
    else:
        open_support_process_once(state)


def launch_manage_support_menu(state: MenuSessionContext) -> None:
    """Launch the first production teacher-local Support Process surface."""

    while True:
        clear_screen()
        print_menu_header("Manage Support")
        print("Create or reopen teacher-local support planning without collapsing its record families.")
        print()
        print("1. Create a Support Process")
        print("2. Open a Support Process")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show_result(
                "Manage Support Help",
                (
                    "A Support Process is teacher-local planning, not automatically an IEP, 504 plan, FBA, BIP, clinical plan, or institutional case plan.",
                    "need != goal; support != intervention; plan != implementation; implementation != fidelity; fidelity != Outcome.",
                    "The routine menu keeps Need, Goal, and Support planning separate from Intervention, Implementation, Fidelity, Follow-Up, and Outcome.",
                ),
            )
            continue
        if navigation is NavigationChoice.BACK:
            return
        action = {"1": "create", "2": "open"}.get(raw)
        if action is None:
            print(navigation_hint_with_help())
            pause_for_user()
            continue
        try:
            _run_action(action, state)
        except CancelMenuAction:
            continue
        except (ReturnToMainMenu, QuitPDS, EOFError):
            raise
        except PortiaOperationPartialCommitError:
            _show_result(
                "Manage Support Interrupted",
                (
                    "A coordinated lifecycle operation was interrupted after at least one canonical step.",
                    "Do not blindly retry. Use Advanced Portia Recovery to assess exact state.",
                ),
            )
        except PortiaQuarantinedError:
            _show_result(
                "Manage Support Blocked",
                (
                    "Quarantine currently blocks this write or current use.",
                    "Inspect exact Portia state before trying another write.",
                ),
            )
        except PortiaCorruptionError:
            _show_result(
                "Manage Support Blocked",
                (
                    "Portia detected canonical storage it cannot safely trust.",
                    "No write or automatic repair was attempted.",
                ),
            )
        except PortiaConflictError:
            _show_result(
                "Manage Support Conflict",
                (
                    "Canonical Portia state changed or conflicted with this write.",
                    "Reopen current state before trying again.",
                ),
            )
        except PortiaRecoveryRequiredError:
            _show_result(
                "Manage Support Blocked",
                (
                    "Existing Portia state requires explicit Recovery before this write.",
                    "No automatic recovery action was attempted.",
                ),
            )
        except PortiaStorageError:
            _show_result(
                "Manage Support Error",
                (
                    "Portia storage could not safely complete this action.",
                    "No automatic retry was attempted.",
                ),
            )
        except (PortiaWorkflowError, ValueError) as error:
            _show_result("Manage Support Error", (str(error),))
        except Exception:
            _show_result(
                "Manage Support Error",
                (
                    "Portia could not complete this action.",
                    "No automatic retry or recovery action was attempted.",
                ),
            )
