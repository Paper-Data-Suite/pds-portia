"""Teacher-facing Response and Communication workflow."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from portia.menu.authoring import (
    CommunicationAuthoringInput,
    CommunicationRecipientInput,
    EventEvidenceTargetInput,
    HumanAttributionInput,
    ResponseAuthoringInput,
    prepare_communication,
    prepare_response,
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
    EventOption,
    StudentOption,
    class_options,
    event_options,
    event_participant_options,
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
from portia.models import PortiaRecord
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.workflows import (
    CommunicationWorkflowService,
    PortiaWorkflowError,
    ResponseWorkflowService,
)

_RESPONSE_FAMILIES: tuple[tuple[str, str], ...] = (
    ("classroom_management", "Classroom management"),
    ("environmental_or_instructional", "Environmental or instructional adjustment"),
    ("support_access", "Support access"),
    ("de_escalation", "De-escalation"),
    ("safety_or_protective", "Safety or protective action"),
    ("referral_or_handoff", "Referral or handoff"),
    ("restorative_or_repair", "Restorative or repair action"),
    ("consequence", "Teacher-local consequence"),
    ("other", "Other bounded response"),
)
_RESPONSE_STATES: tuple[tuple[str, str], ...] = (
    ("attempted", "Attempted"),
    ("in_progress", "In progress"),
    ("completed", "Completed"),
    ("partially_completed", "Partially completed"),
    ("discontinued", "Discontinued"),
    ("unable_to_complete", "Unable to complete"),
)
_COMMUNICATION_METHODS: tuple[tuple[str, str], ...] = (
    ("in_person", "In person"),
    ("phone_call", "Phone call"),
    ("voicemail", "Voicemail"),
    ("text_message", "Text message"),
    ("email", "Email"),
    ("letter", "Letter"),
    ("portal_or_system_message", "Portal or system message"),
    ("video_call", "Video call"),
    ("other", "Other"),
)
_COMMUNICATION_PURPOSES: tuple[tuple[str, str], ...] = (
    ("information_sharing", "Share information"),
    ("request_for_information", "Request information"),
    ("notice", "Provide notice"),
    ("scheduling", "Scheduling"),
    ("review_coordination", "Coordinate a review"),
    ("determination_notice", "Communicate a determination"),
    ("response_coordination", "Coordinate a response"),
    ("support_coordination", "Coordinate support"),
    ("referral_or_handoff", "Referral or handoff"),
    ("follow_up", "Follow-up"),
    ("reentry_or_repair", "Reentry or repair"),
    ("other", "Other"),
)
_COMMUNICATION_STATES: tuple[tuple[str, str], ...] = (
    ("attempted", "Attempted"),
    ("completed", "Completed communication act"),
    ("recipient_unavailable", "Recipient unavailable"),
    ("recipient_declined", "Recipient declined"),
    ("interrupted", "Interrupted"),
)
_PRIVACY_SCOPES: tuple[tuple[str, str], ...] = (
    ("ordinary", "Ordinary"),
    ("participant_limited", "Participant-limited"),
    ("restricted", "Restricted"),
)
_PARTICIPATION_STATES: tuple[tuple[str, str], ...] = (
    ("participated", "Recipient participated in the communication act"),
    ("not_established", "Participation was not established"),
)
_DESCRIPTION_TYPES: tuple[tuple[str, str], ...] = (
    ("family_member", "Family member"),
    ("school_staff", "School staff"),
    ("outside_student", "Student outside the available roster"),
    ("visitor", "Visitor"),
    ("community_member", "Community member"),
    ("other", "Other described person"),
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


def _choose_class(root: Path, *, title: str) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError("No Core classes with both metadata and rosters are available.")
    return select_one(
        title,
        options,
        tuple(item.label for item in options),
        help_text="Choose the exact Core class that owns the Event.",
    )


def _choose_current_event(root: Path, state: MenuSessionContext) -> EventOption:
    owner = _choose_class(root, title="Response / Communication — Event Class")
    options = tuple(
        item for item in event_options(root, owner.class_id) if item.status in {"active", "closed"}
    )
    if not options:
        raise ValueError(
            f"No active or closed Events are available in {owner.class_id!r}."
        )
    selected = select_one(
        "Response / Communication — Event",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact existing Event. The summary and time are display aids; "
            "the numbered choice carries exact Portia identity."
        ),
    )
    state.remember_work(
        class_id=selected.work.class_id,
        work_kind="event",
        work_id=selected.work.work_id,
    )
    return selected


def _choose_target(root: Path, event: EventOption) -> tuple[EventEvidenceTargetInput, str]:
    participants = event_participant_options(root, event.work)
    values: list[EventEvidenceTargetInput] = [EventEvidenceTargetInput(kind="event")]
    labels: list[str] = ["The Event as a whole"]
    for participant in participants:
        values.append(
            EventEvidenceTargetInput(
                kind="event_participant",
                participant_id=participant.participant_id,
            )
        )
        labels.append(f"Person involved: {participant.label}")
    selected = select_one(
        "Record Response — Target",
        tuple(values),
        tuple(labels),
        help_text=(
            "Choose the scope of the Response. Targeting identifies what the action concerns; "
            "it does not establish a finding or outcome."
        ),
    )
    return selected, labels[values.index(selected)]


def _prompt_time(title: str, clock: MenuClock, label: str) -> ExplicitOffsetTimestamp:
    default = clock.now().text
    while True:
        value = prompt_text(
            title,
            label,
            help_text=(
                "Press Enter for the current time, or enter an RFC 3339 date/time "
                "with an explicit UTC offset."
            ),
            default=default,
        )
        assert value is not None
        try:
            return ExplicitOffsetTimestamp(value)
        except Exception:
            _show_result(title, ("That date/time is invalid. Include an explicit UTC offset.",))


def _select_named(
    title: str,
    values: tuple[tuple[str, str], ...],
    *,
    help_text: str,
) -> str:
    return select_one(
        title,
        tuple(item[0] for item in values),
        tuple(item[1] for item in values),
        help_text=help_text,
    )


def record_response_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Collect, preview, and create one bounded Event-local Response."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    event = _choose_current_event(root, state)
    operator = _require_operator(state, title="Record Response — Your Name")
    target, target_label = _choose_target(root, event)
    family = _select_named(
        "Record Response — Action Type",
        _RESPONSE_FAMILIES,
        help_text=(
            "Choose what you did. A Response records the bounded action itself; "
            "it does not establish effectiveness or an Outcome."
        ),
    )
    description = prompt_text(
        "Record Response — Description",
        "What did you do?",
        help_text="Enter a concise factual description of the action taken or attempted.",
    )
    assert description is not None
    execution_state = _select_named(
        "Record Response — Execution",
        _RESPONSE_STATES,
        help_text=(
            "Record only the execution state you can establish. Completion does not mean "
            "the action was effective."
        ),
    )
    started_at = _prompt_time("Record Response — When", menu_clock, "Started at")
    request = ResponseAuthoringInput(
        work=event.work,
        target=target,
        action_family=family,
        description=description,
        execution_state=execution_state,
        started_at=started_at,
        local_operator_label=operator,
        consequence_context="teacher_local" if family == "consequence" else None,
    )
    candidate = prepare_response(request, clock=menu_clock, ids=id_generator)
    lines = (
        f"Event: {event.summary}",
        f"Target: {target_label}",
        f"Provider: {operator}",
        f"Action type: {family.replace('_', ' ')}",
        f"Description: {description}",
        f"Execution: {execution_state.replace('_', ' ')}",
        f"Started: {started_at.text}",
        "",
        "This records what was done or attempted. It does not record effectiveness or Outcome.",
    )
    if not confirm_write(
        "Record Response — Review",
        "RECORD",
        lines,
        help_text="RECORD creates exactly one Response through ResponseWorkflowService.",
    ):
        return
    ResponseWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Response Recorded",
        (
            "Response recorded.",
            "No Communication, Support, Follow-Up, or Outcome was created automatically.",
        ),
    )


def _choose_roster_recipient(root: Path) -> tuple[HumanAttributionInput, str]:
    source_class = _choose_class(root, title="Communication — Recipient Class")
    students = student_options(root, source_class.class_id)
    if not students:
        raise ValueError(f"The selected Core class {source_class.class_id!r} has no students.")
    student: StudentOption = select_one(
        "Communication — Recipient Student",
        students,
        tuple(item.label for item in students),
        help_text=(
            "Choose the exact class-qualified roster student. Display names are presentation only."
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


def _choose_descriptive_recipient() -> tuple[HumanAttributionInput, str]:
    description_type = _select_named(
        "Communication — Recipient Type",
        _DESCRIPTION_TYPES,
        help_text=(
            "Use a bounded descriptive person when an exact roster or Actor identity is not available. "
            "This does not create an Actor or establish institutional authority."
        ),
    )
    display_label = prompt_text(
        "Communication — Recipient",
        "Display label",
        help_text="Enter a concise human-readable label for this recipient.",
    )
    assert display_label is not None
    detail: str | None = None
    if description_type == "other":
        detail = prompt_text(
            "Communication — Recipient",
            "Detail",
            help_text="Briefly clarify what kind of person is represented.",
        )
        assert detail is not None
    return (
        HumanAttributionInput(
            kind="descriptive_person",
            description_type=description_type,
            display_label=display_label,
            detail=detail,
        ),
        display_label,
    )


def _choose_recipient(root: Path) -> tuple[CommunicationRecipientInput, str]:
    kind = select_one(
        "Communication — Recipient",
        ("roster", "descriptive"),
        ("Roster student", "Another described person"),
        help_text=(
            "Choose the represented recipient. Merely listing a recipient does not establish "
            "delivery, reading, understanding, or agreement."
        ),
    )
    if kind == "roster":
        person, label = _choose_roster_recipient(root)
    else:
        person, label = _choose_descriptive_recipient()
    participation = _select_named(
        "Communication — Recipient Participation",
        _PARTICIPATION_STATES,
        help_text=(
            "Record whether this recipient actually participated in the communication act. "
            "Participation still does not establish reading, understanding, or agreement."
        ),
    )
    return CommunicationRecipientInput(person=person, participation=participation), label


def _collect_recipients(root: Path) -> tuple[tuple[CommunicationRecipientInput, str], ...]:
    selected: list[tuple[CommunicationRecipientInput, str]] = []
    while True:
        recipient = _choose_recipient(root)
        selected.append(recipient)
        again = select_one(
            "Communication — Recipients",
            (False, True),
            ("Continue", "Add another recipient"),
            help_text="Add another explicit recipient only when the same communication act involved them.",
        )
        if not again:
            return tuple(selected)


def record_communication_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Collect, preview, and create one Event-owned Communication."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    event = _choose_current_event(root, state)
    operator = _require_operator(state, title="Communication — Your Name")
    selected_recipients = _collect_recipients(root)
    method_kind = _select_named(
        "Communication — Method",
        _COMMUNICATION_METHODS,
        help_text="Record how the communication act was attempted or carried out.",
    )
    method_detail: str | None = None
    if method_kind == "other":
        method_detail = prompt_text(
            "Communication — Method",
            "Method detail",
            help_text="Briefly describe the communication method.",
        )
        assert method_detail is not None
    purpose_kind = _select_named(
        "Communication — Purpose",
        _COMMUNICATION_PURPOSES,
        help_text=(
            "Record the bounded purpose of the communication. Purpose does not establish "
            "delivery, understanding, agreement, or participation in another process."
        ),
    )
    purpose_detail: str | None = None
    if purpose_kind == "other":
        purpose_detail = prompt_text(
            "Communication — Purpose",
            "Purpose detail",
            help_text="Briefly describe the purpose.",
        )
        assert purpose_detail is not None
    act_state = _select_named(
        "Communication — Act State",
        _COMMUNICATION_STATES,
        help_text=(
            "Record the state of the communication act itself. A completed act does not prove "
            "that information was read, understood, accepted, or agreed to."
        ),
    )
    if act_state == "recipient_unavailable" and any(
        item.participation == "participated" for item, _label in selected_recipients
    ):
        raise ValueError(
            "recipient-unavailable communication cannot also record recipient participation"
        )
    privacy_scope = _select_named(
        "Communication — Privacy",
        _PRIVACY_SCOPES,
        help_text="Choose the bounded privacy scope for this communication record.",
    )
    started_at = _prompt_time("Communication — When", menu_clock, "Started at")
    summary = prompt_text(
        "Communication — Summary",
        "Optional summary",
        help_text=(
            "Optionally enter a bounded recorder-authored summary. This is not automatically "
            "a verbatim message archive or an Account."
        ),
        optional=True,
    )
    request = CommunicationAuthoringInput(
        work=event.work,
        recipients=tuple(item for item, _label in selected_recipients),
        method_kind=method_kind,
        method_detail=method_detail,
        purpose_kind=purpose_kind,
        purpose_detail=purpose_detail,
        act_state=act_state,
        privacy_scope=privacy_scope,
        started_at=started_at,
        summary=summary,
        local_operator_label=operator,
    )
    candidate = prepare_communication(request, clock=menu_clock, ids=id_generator)
    lines: list[str] = [
        f"Event: {event.summary}",
        f"Sender: {operator}",
        "Recipients:",
    ]
    for item, label in selected_recipients:
        lines.append(f"  - {label} — {item.participation.replace('_', ' ')}")
    lines.extend(
        (
            f"Method: {method_kind.replace('_', ' ')}",
            f"Purpose: {purpose_kind.replace('_', ' ')}",
            f"Act state: {act_state.replace('_', ' ')}",
            f"Privacy: {privacy_scope.replace('_', ' ')}",
            f"Started: {started_at.text}",
        )
    )
    if summary:
        lines.append(f"Summary: {summary}")
    lines.extend(
        (
            "",
            "This record does not infer delivery, reading, understanding, agreement, or support participation.",
        )
    )
    if not confirm_write(
        "Communication — Review",
        "RECORD",
        tuple(lines),
        help_text="RECORD creates exactly one Communication through CommunicationWorkflowService.",
    ):
        return
    CommunicationWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Communication Recorded",
        (
            "Communication recorded.",
            "No Response, Support, Follow-Up, or Outcome was created automatically.",
        ),
    )


def _response_display(record: PortiaRecord) -> str:
    action = record.field("action")
    family = action.get("family") if isinstance(action, Mapping) else None
    description = action.get("description") if isinstance(action, Mapping) else None
    family_text = str(family).replace("_", " ") if isinstance(family, str) else "response"
    detail = description if isinstance(description, str) else "No description"
    state = record.field("execution_state")
    state_text = str(state).replace("_", " ") if isinstance(state, str) else "state unknown"
    return f"Response — {family_text} — {state_text} — {detail}"


def _communication_display(record: PortiaRecord) -> str:
    method = record.field("method")
    purpose = record.field("purpose")
    method_kind = method.get("kind") if isinstance(method, Mapping) else None
    purpose_kind = purpose.get("kind") if isinstance(purpose, Mapping) else None
    summary = record.field("summary")
    method_text = str(method_kind).replace("_", " ") if isinstance(method_kind, str) else "communication"
    purpose_text = str(purpose_kind).replace("_", " ") if isinstance(purpose_kind, str) else "purpose not recorded"
    detail = summary if isinstance(summary, str) else "No summary"
    return f"Communication — {method_text} — {purpose_text} — {detail}"


def review_recent_once(state: MenuSessionContext) -> None:
    """Render exact Event-local Responses and Communications without rewriting them."""

    root = state.resolve_workspace()
    event = _choose_current_event(root, state)
    responses = ResponseWorkflowService(root).list(event.work)
    communications = CommunicationWorkflowService(root).list(event.work)
    entries: list[tuple[str, str]] = []
    for item in responses:
        created = item.record.field("created_at")
        entries.append((created if isinstance(created, str) else "", _response_display(item.record)))
    for item in communications:
        created = item.record.field("created_at")
        entries.append((created if isinstance(created, str) else "", _communication_display(item.record)))
    entries.sort(key=lambda item: item[0], reverse=True)

    if not entries:
        _show_result(
            "Recent Responses / Communications",
            ("No Responses or Communications are recorded for this Event.",),
        )
        return

    pages = page_count(len(entries), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header("Recent Responses / Communications")
        print(f"Event: {event.summary}")
        print()
        visible = page_items(entries, page_index, page_size=PAGE_SIZE)
        for _created, label in visible:
            print(f"- {label}")
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
                "Recent Responses / Communications Help",
                (
                    "This is a read-only bounded view of the selected Event.",
                    "Response and Communication remain distinct canonical record families.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _run_action(action: str, state: MenuSessionContext) -> None:
    if action == "response":
        record_response_once(state)
    elif action == "communication":
        record_communication_once(state)
    else:
        review_recent_once(state)


def launch_response_communication_menu(state: MenuSessionContext) -> None:
    """Launch the bounded Response / Communication teacher task."""

    while True:
        clear_screen()
        print_menu_header("Record Response / Communication")
        print("Record what was done or what communication occurred or was attempted.")
        print()
        print("1. Record a Response")
        print("2. Record a Communication")
        print("3. View recent Responses / Communications")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show_result(
                "Response / Communication Help",
                (
                    "Response records a bounded action; it does not establish effectiveness.",
                    "Communication records a communication act or attempt; it does not establish reading, understanding, or agreement.",
                ),
            )
            continue
        if navigation is NavigationChoice.BACK:
            return
        action = {"1": "response", "2": "communication", "3": "review"}.get(raw)
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
        except PortiaQuarantinedError:
            _show_result(
                "Response / Communication Blocked",
                (
                    "Quarantine currently blocks this write or current use.",
                    "Inspect the exact Portia state before trying another write.",
                ),
            )
        except PortiaCorruptionError:
            _show_result(
                "Response / Communication Blocked",
                (
                    "Portia detected canonical storage it cannot safely trust.",
                    "No write or automatic repair was attempted.",
                ),
            )
        except PortiaConflictError:
            _show_result(
                "Response / Communication Conflict",
                (
                    "Canonical Portia state changed or conflicted with this write.",
                    "Review current state before trying again.",
                ),
            )
        except PortiaRecoveryRequiredError:
            _show_result(
                "Response / Communication Blocked",
                (
                    "Existing Portia state requires explicit Recovery before this write.",
                    "No automatic recovery action was attempted.",
                ),
            )
        except PortiaStorageError:
            _show_result(
                "Response / Communication Error",
                (
                    "Portia storage could not safely complete this action.",
                    "No automatic retry was attempted.",
                ),
            )
        except (PortiaWorkflowError, ValueError) as error:
            _show_result("Response / Communication Error", (str(error),))
        except Exception:
            _show_result(
                "Response / Communication Error",
                (
                    "Portia could not complete this action.",
                    "No automatic retry or recovery action was attempted.",
                ),
            )
