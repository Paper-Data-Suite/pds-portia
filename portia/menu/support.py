"""Teacher-facing Support Process foundation workflow."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from portia.menu.authoring import (
    HumanAttributionInput,
    SupportParticipantAuthoringInput,
    SupportParticipantContextInput,
    SupportProcessAuthoringInput,
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
from portia.models import PortiaRecord, SupportProcessParticipantV1, SupportProcessV1
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
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
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
                    "Needs, goals, supports, interventions, implementation, and fidelity are not collapsed here.",
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
                    "This slice wires the Support Process root and Participants only.",
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
