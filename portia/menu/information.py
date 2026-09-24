"""Teacher-facing Add Information workflow for Account and Observation evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from portia.menu.authoring import (
    AccountAuthoringInput,
    EventEvidenceTargetInput,
    HumanAttributionInput,
    ObservationAuthoringInput,
    prepare_account,
    prepare_direct_observation,
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
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.workflows import (
    AccountWorkflowService,
    ObservationWorkflowService,
    PortiaWorkflowError,
)

_INFORMATION_ORIGINS: tuple[tuple[str, str], ...] = (
    ("firsthand", "The source is reporting firsthand information"),
    ("secondhand", "The source is relaying information from someone else"),
    ("mixed", "The report mixes firsthand and secondhand information"),
    ("unknown", "The information origin is not known"),
)
_SOURCE_CERTAINTIES: tuple[tuple[str, str], ...] = (
    ("stated_certain", "The source stated this with certainty"),
    ("stated_uncertain", "The source stated uncertainty"),
    ("mixed_or_qualified", "The source was mixed or qualified"),
    ("not_recorded", "Source certainty was not recorded"),
)
_REPRESENTATIONS: tuple[tuple[str, str], ...] = (
    ("recorded_summary", "Recorded summary"),
    ("verbatim_quote", "Verbatim quote"),
)
_DESCRIPTION_TYPES: tuple[tuple[str, str], ...] = (
    ("outside_student", "Student outside the available roster"),
    ("family_member", "Family member"),
    ("school_staff", "School staff"),
    ("visitor", "Visitor"),
    ("community_member", "Community member"),
    ("other", "Other described person"),
)
_IDENTITY_STATUSES: tuple[tuple[str, str], ...] = (
    ("anonymous", "Anonymous source"),
    ("withheld", "Identity intentionally withheld"),
    ("uncertain", "Identity uncertain"),
    ("not_recorded", "Identity not recorded"),
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
            "Enter the teacher-facing name or label for who is making this local entry. "
            "This is provenance only; it is not authentication or institutional authority."
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


def _choose_event(root: Path, state: MenuSessionContext) -> EventOption:
    owner = _choose_class(root, title="Add Information — Event Class")
    options = event_options(root, owner.class_id)
    if not options:
        raise ValueError(
            f"No draft, active, or closed Events are available in {owner.class_id!r}."
        )
    selected = select_one(
        "Add Information — Event",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact existing Event. The summary and time are display aids; "
            "the numbered selection carries exact Portia identity."
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
        "Add Information — Target",
        tuple(values),
        tuple(labels),
        help_text=(
            "Choose what this information concerns. A target identifies scope only; "
            "it does not establish blame, truth, or a finding."
        ),
    )
    index = values.index(selected)
    return selected, labels[index]


def _choose_roster_source(root: Path) -> tuple[HumanAttributionInput, str]:
    source_class = _choose_class(root, title="Add Information — Source Class")
    students = student_options(root, source_class.class_id)
    if not students:
        raise ValueError(f"The selected Core class {source_class.class_id!r} has no students.")
    student: StudentOption = select_one(
        "Add Information — Source Student",
        students,
        tuple(item.label for item in students),
        help_text=(
            "Choose the exact class-qualified roster student who is represented as "
            "the source. Display names are not lookup authority."
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


def _choose_descriptive_source() -> tuple[HumanAttributionInput, str]:
    description_type = select_one(
        "Add Information — Source Type",
        tuple(item[0] for item in _DESCRIPTION_TYPES),
        tuple(item[1] for item in _DESCRIPTION_TYPES),
        help_text=(
            "Use a bounded descriptive person when exact roster or Actor identity "
            "is not available. This does not create a new identity record."
        ),
    )
    display_label = prompt_text(
        "Add Information — Source",
        "Display label",
        help_text="Enter a concise human-readable label for this represented source.",
    )
    assert display_label is not None
    detail: str | None = None
    if description_type == "other":
        detail = prompt_text(
            "Add Information — Source",
            "Detail",
            help_text="Briefly clarify what kind of person is being represented.",
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


def _choose_unidentified_source() -> tuple[HumanAttributionInput, str]:
    identity_status = select_one(
        "Add Information — Unidentified Source",
        tuple(item[0] for item in _IDENTITY_STATUSES),
        tuple(item[1] for item in _IDENTITY_STATUSES),
        help_text=(
            "Record why exact source identity is unavailable without fabricating "
            "a roster student or Actor."
        ),
    )
    display_label = prompt_text(
        "Add Information — Unidentified Source",
        "Optional display label",
        help_text="Optionally record a bounded label such as 'student caller'.",
        optional=True,
    )
    detail = prompt_text(
        "Add Information — Unidentified Source",
        "Optional detail",
        help_text="Optionally record a short identity-related clarification.",
        optional=True,
    )
    label = display_label or identity_status.replace("_", " ").title()
    return (
        HumanAttributionInput(
            kind="unidentified_person",
            identity_status=identity_status,
            display_label=display_label,
            detail=detail,
        ),
        label,
    )


def _choose_account_source(
    root: Path,
    operator: str,
) -> tuple[HumanAttributionInput, str]:
    choice = select_one(
        "Add Information — Who Reported It?",
        ("operator", "roster", "descriptive", "unidentified"),
        (
            f"Me / local operator — {operator}",
            "A roster student",
            "Another described person",
            "An unidentified or withheld source",
        ),
        help_text=(
            "Choose who this Account represents as the source. Source attribution is "
            "different from who is recording the entry."
        ),
    )
    if choice == "operator":
        return HumanAttributionInput(kind="local_operator", display_label=operator), operator
    if choice == "roster":
        return _choose_roster_source(root)
    if choice == "descriptive":
        return _choose_descriptive_source()
    return _choose_unidentified_source()


def _prompt_evidence_time(title: str, clock: MenuClock, label: str) -> ExplicitOffsetTimestamp:
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


def _select_named_value(
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


def record_account_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Collect, preview, and create one attributed Account."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state, title="Add Information — Your Name")
    target, target_label = _choose_target(root, event)
    source, source_label = _choose_account_source(root, operator)
    origin = _select_named_value(
        "Add Information — Information Origin",
        _INFORMATION_ORIGINS,
        help_text=(
            "Record whether this source is speaking from firsthand information, "
            "relaying information, or a mixture. This is not a credibility judgment."
        ),
    )
    certainty = _select_named_value(
        "Add Information — Source Certainty",
        _SOURCE_CERTAINTIES,
        help_text=(
            "Record how the source expressed certainty. Do not convert certainty into truth."
        ),
    )
    representation = _select_named_value(
        "Add Information — Representation",
        _REPRESENTATIONS,
        help_text=(
            "Choose whether the text is your recorded summary or a verbatim quotation."
        ),
    )
    text = prompt_text(
        "Add Information — Report",
        "Text",
        help_text=(
            "Record the bounded information attributed to this source. Keep recorder "
            "interpretation separate from the source's Account."
        ),
    )
    assert text is not None
    provided_time = _prompt_evidence_time(
        "Add Information — Provided Time",
        menu_clock,
        "Date/time provided",
    )
    request = AccountAuthoringInput(
        work=event.work,
        target=target,
        source=source,
        information_origin=origin,
        source_certainty=certainty,
        representation=representation,
        text=text,
        provided_time=provided_time,
        local_operator_label=operator,
    )
    candidate = prepare_account(request, clock=menu_clock, ids=id_generator)
    lines = (
        f"Event: {event.summary}",
        f"Target: {target_label}",
        f"Source: {source_label}",
        f"Information origin: {origin.replace('_', ' ')}",
        f"Source certainty: {certainty.replace('_', ' ')}",
        f"Representation: {representation.replace('_', ' ')}",
        f"Text: {text}",
        f"Provided: {provided_time.text}",
        "",
        "This records attributed information; it does not establish truth or credibility.",
        "It does not create a Classification, Hypothesis, Determination, or Response.",
    )
    if not confirm_write(
        "Add Information — Review Account",
        "RECORD",
        lines,
        help_text=(
            "RECORD creates exactly one Account through Portia's existing Account workflow."
        ),
    ):
        return
    AccountWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Information Saved",
        (
            "The attributed Account was saved.",
            "No credibility judgment, finding, or downstream action was created automatically.",
        ),
    )


def record_observation_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Collect, preview, and create one live-direct teacher Observation."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state, title="Add Information — Your Name")
    target, target_label = _choose_target(root, event)
    narrative = prompt_text(
        "Add Information — Direct Observation",
        "What you directly observed",
        help_text=(
            "Record bounded directly observable information. Keep interpretation, motive, "
            "diagnosis, policy conclusions, and other judgments out of the Observation."
        ),
    )
    assert narrative is not None
    observed_at = _prompt_evidence_time(
        "Add Information — Observation Time",
        menu_clock,
        "Date/time observed",
    )
    request = ObservationAuthoringInput(
        work=event.work,
        target=target,
        narrative=narrative,
        observation_time=observed_at,
        local_operator_label=operator,
    )
    candidate = prepare_direct_observation(request, clock=menu_clock, ids=id_generator)
    lines = (
        f"Event: {event.summary}",
        f"Target: {target_label}",
        f"Observer: {operator}",
        "Method: live direct observation",
        f"Observed: {observed_at.text}",
        f"Observation: {narrative}",
        "",
        "This records observable evidence only; it does not create an interpretation or finding.",
    )
    if not confirm_write(
        "Add Information — Review Observation",
        "RECORD",
        lines,
        help_text=(
            "RECORD creates exactly one Observation through Portia's existing Observation workflow."
        ),
    ):
        return
    ObservationWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Information Saved",
        (
            "The direct Observation was saved.",
            "No Classification, Hypothesis, Determination, Response, or Outcome was created.",
        ),
    )


def _source_label(record: PortiaRecord) -> str:
    source = record.field("source")
    if not isinstance(source, Mapping):
        return "Source not available"
    kind = source.get("kind")
    if kind == "local_operator":
        label = source.get("display_label")
        return label if isinstance(label, str) else "Local operator"
    if kind in {"roster_student", "actor"}:
        snapshot = source.get("display_snapshot")
        label = snapshot.get("display_name") if isinstance(snapshot, Mapping) else None
        return label if isinstance(label, str) else str(kind).replace("_", " ").title()
    if kind in {"descriptive_person", "unidentified_person"}:
        label = source.get("display_label")
        if isinstance(label, str):
            return label
        return str(kind).replace("_", " ").title()
    return "Source not available"


def _observer_label(record: PortiaRecord) -> str:
    observer = record.field("observer")
    if not isinstance(observer, Mapping):
        return "Observer not available"
    if observer.get("kind") == "instrument":
        label = observer.get("instrument_label")
        return label if isinstance(label, str) else "Instrument"
    attribution = observer.get("human_attribution")
    if not isinstance(attribution, Mapping):
        return "Human observer"
    kind = attribution.get("kind")
    if kind == "local_operator":
        label = attribution.get("display_label")
        return label if isinstance(label, str) else "Local operator"
    snapshot = attribution.get("display_snapshot")
    label = snapshot.get("display_name") if isinstance(snapshot, Mapping) else None
    if isinstance(label, str):
        return label
    direct = attribution.get("display_label")
    return direct if isinstance(direct, str) else "Human observer"


def _target_label(record: PortiaRecord, participants: Mapping[str, str]) -> str:
    target = record.field("target")
    if not isinstance(target, Mapping):
        return "Target not available"
    if target.get("kind") == "event":
        return "Event as a whole"
    reference = target.get("record_ref")
    if isinstance(reference, Mapping):
        record_id = reference.get("record_id")
        if isinstance(record_id, str):
            return participants.get(record_id, "Event participant")
    return "Event participant"


def _account_text(record: PortiaRecord) -> str:
    content = record.field("content")
    if not isinstance(content, tuple) or not content:
        return "Account content unavailable"
    first = content[0]
    if isinstance(first, Mapping):
        text = first.get("text")
        if isinstance(text, str):
            return text
    return "Account content unavailable"


def _observation_text(record: PortiaRecord) -> str:
    content = record.field("content")
    if not isinstance(content, Mapping):
        return "Observation content unavailable"
    narrative = content.get("narrative")
    if isinstance(narrative, str):
        return narrative
    measurements = content.get("measurements")
    if isinstance(measurements, tuple):
        return f"{len(measurements)} recorded measurement(s)"
    return "Observation content unavailable"


def _evidence_review_lines(root: Path, work: ExactPortiaWorkRef) -> tuple[str, ...]:
    participants = {
        item.participant_id: item.display_name
        for item in event_participant_options(root, work)
    }
    entries: list[tuple[str, str]] = []
    for stored in AccountWorkflowService(root).list(work):
        record = stored.record
        if record.status not in {"active", "proposed"}:
            continue
        created = record.field("created_at")
        sort_key = created if isinstance(created, str) else ""
        entries.append(
            (
                sort_key,
                (
                    f"Account — {_source_label(record)} — {_target_label(record, participants)}\n"
                    f"  {_account_text(record)}"
                ),
            )
        )
    for stored in ObservationWorkflowService(root).list(work):
        record = stored.record
        if record.status not in {"active", "proposed"}:
            continue
        created = record.field("created_at")
        sort_key = created if isinstance(created, str) else ""
        entries.append(
            (
                sort_key,
                (
                    f"Observation — {_observer_label(record)} — {_target_label(record, participants)}\n"
                    f"  {_observation_text(record)}"
                ),
            )
        )
    entries.sort(key=lambda item: item[0], reverse=True)
    return tuple(item[1] for item in entries)


def review_information_once(state: MenuSessionContext) -> None:
    """Show bounded current Account/Observation evidence without writing state."""

    root = state.resolve_workspace()
    event = _choose_event(root, state)
    lines = _evidence_review_lines(root, event.work)
    if not lines:
        _show_result(
            "Add Information — Review",
            ("No current Account or Observation evidence is recorded for this Event.",),
        )
        return

    pages = page_count(len(lines), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header("Add Information — Review")
        print(f"Event: {event.summary}")
        print()
        for line in page_items(lines, page_index, page_size=PAGE_SIZE):
            print(line)
            print()
        if pages > 1:
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
                "Add Information — Review Help",
                (
                    "This view shows current/proposed Accounts and Observations only.",
                    "Account and Observation remain different evidence families.",
                    "Historical/superseded administration belongs in bounded advanced tools.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _handle_information_error(error: BaseException) -> None:
    lines: tuple[str, ...]
    if isinstance(error, PortiaQuarantinedError):
        lines = (
            "Quarantine currently blocks this information write or current use.",
            "Inspect exact Portia state before trying another write.",
        )
        title = "Add Information Blocked"
    elif isinstance(error, PortiaCorruptionError):
        lines = (
            "Portia detected canonical storage it cannot safely trust.",
            "No write or automatic repair was attempted.",
        )
        title = "Add Information Blocked"
    elif isinstance(error, PortiaConflictError):
        lines = (
            "Canonical Portia state changed or conflicted with this write.",
            "Review the current state before trying again.",
        )
        title = "Add Information Conflict"
    elif isinstance(error, PortiaRecoveryRequiredError):
        lines = (
            "Existing Portia state requires explicit Recovery before this action.",
            "No automatic recovery action was attempted.",
        )
        title = "Add Information Blocked"
    elif isinstance(error, PortiaStorageError):
        lines = (
            "Portia storage could not safely complete this information action.",
            "No automatic retry was attempted.",
        )
        title = "Add Information Error"
    elif isinstance(error, (PortiaWorkflowError, ValueError)):
        lines = (str(error),)
        title = "Add Information Error"
    else:
        lines = (
            "Portia could not complete this information action.",
            "No automatic retry, inference, or recovery action was attempted.",
        )
        title = "Add Information Error"
    _show_result(title, lines)


def launch_add_information_menu(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Launch the evidence-focused portion of the Add Information task."""

    while True:
        clear_screen()
        print_menu_header("Add Information")
        print("Add evidence to an existing Event without collapsing its meaning.")
        print()
        print("1. Record what someone reported")
        print("2. Record what I directly observed")
        print("3. Review recorded Accounts / Observations")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            _show_result(
                "Add Information Help",
                (
                    "An Account records attributable reported information.",
                    "An Observation records bounded direct or measured observation.",
                    "Neither becomes true or a finding merely because it is recorded.",
                    "Human-judgment records are handled separately from this evidence path.",
                ),
            )
        elif navigation is NavigationChoice.BACK:
            return
        elif raw in {"1", "2", "3"}:
            try:
                if raw == "1":
                    record_account_once(state, clock=clock, ids=ids)
                elif raw == "2":
                    record_observation_once(state, clock=clock, ids=ids)
                else:
                    review_information_once(state)
            except CancelMenuAction:
                continue
            except (ReturnToMainMenu, QuitPDS, EOFError):
                raise
            except Exception as error:
                _handle_information_error(error)
        else:
            print(navigation_hint_with_help())
            pause_for_user()
