"""Teacher-facing Record Event workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pds_core.class_metadata import load_class_metadata_for_class

from portia.menu.authoring import (
    EventAuthoringInput,
    PreparedEventBundle,
    RosterParticipantInput,
    prepare_event_bundle,
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
from portia.menu.prompts import (
    CancelMenuAction,
    confirm_write,
    prompt_text,
    select_one,
)
from portia.menu.selectors import (
    ClassOption,
    StudentOption,
    class_options,
    student_options,
)
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaOperationPartialCommitError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.workflows import EventBundleWorkflowService, PortiaWorkflowError

_LOCATION_TYPES: tuple[tuple[str, str], ...] = (
    ("classroom", "Classroom"),
    ("hallway", "Hallway"),
    ("cafeteria", "Cafeteria"),
    ("transportation", "Transportation"),
    ("online", "Online"),
    ("field_trip", "Field trip"),
    ("assembly", "Assembly"),
    ("extracurricular", "Extracurricular"),
    ("before_school", "Before school"),
    ("after_school", "After school"),
    ("other", "Other"),
    ("unknown", "Unknown"),
    ("withheld", "Withheld"),
)


@dataclass(frozen=True, slots=True)
class SelectedParticipant:
    """Presentation-preserving exact roster selection for one Event."""

    option: StudentOption


def _show_result(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _choose_class(root: Path, *, title: str) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError(
            "No Core classes with both metadata and rosters are available."
        )
    return select_one(
        title,
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact Core class. Event ownership is never inferred "
            "from a participant."
        ),
    )


def _choose_location() -> tuple[str, str | None]:
    location_type = select_one(
        "Record Event — Location",
        tuple(item[0] for item in _LOCATION_TYPES),
        tuple(item[1] for item in _LOCATION_TYPES),
        help_text=(
            "Choose the closest bounded location description without adding "
            "a finding or judgment."
        ),
    )
    detail: str | None = None
    if location_type == "other":
        detail = prompt_text(
            "Record Event — Location",
            "Location detail",
            help_text="Enter a short neutral location description.",
        )
        assert detail is not None
    return location_type, detail


def _choose_student(root: Path, class_id: str) -> StudentOption:
    options = student_options(root, class_id)
    if not options:
        raise ValueError(
            f"The selected Core class {class_id!r} has no roster students."
        )
    return select_one(
        "Record Event — Person Involved",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact roster student. Display names are never used "
            "as identity."
        ),
    )


def _collect_participants(
    root: Path,
    owner: ClassOption,
) -> tuple[SelectedParticipant, ...]:
    selected: list[SelectedParticipant] = []
    exact_seen: set[tuple[str, str]] = set()
    while True:
        clear_screen()
        print_menu_header("Record Event — People Involved")
        if selected:
            print("Selected:")
            for index, participant in enumerate(selected, start=1):
                option = participant.option
                source = (
                    "owning class"
                    if option.class_id == owner.class_id
                    else option.class_id
                )
                print(f"{index}. {option.display_name} — {source}")
            print()
        else:
            print("Add at least one person involved before continuing.")
            print()
        print("1. Add a student from the owning class")
        print("2. Add a student from another class")
        if selected:
            print("3. Continue to review")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("People Involved Help")
            print("Roster identity is always the exact class_id + student_id pair.")
            print("A student from another class does not change Event ownership.")
            print(
                "This step records participation only; it does not assign "
                "culpability or a finding."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            raise CancelMenuAction
        if raw == "1":
            student = _choose_student(root, owner.class_id)
        elif raw == "2":
            source_class = _choose_class(root, title="Record Event — Participant Class")
            student = _choose_student(root, source_class.class_id)
        elif raw == "3" and selected:
            return tuple(selected)
        else:
            print(navigation_hint_with_help())
            pause_for_user()
            continue
        key = (student.class_id, student.student_id)
        if key in exact_seen:
            _show_result(
                "Record Event — People Involved",
                ("That exact roster student is already included.",),
            )
            continue
        exact_seen.add(key)
        selected.append(SelectedParticipant(option=student))


def _require_operator(state: MenuSessionContext) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        "Record Event — Your Name",
        "Display label",
        help_text=(
            "Enter the teacher-facing name or label to record who made this local entry. "
            "This is provenance only; it is not authentication or institutional authority."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _occurrence(clock: MenuClock) -> ExplicitOffsetTimestamp:
    default = clock.now().text
    while True:
        value = prompt_text(
            "Record Event — When",
            "Date/time",
            help_text=(
                "Press Enter for the current time, or enter an RFC 3339 date/time "
                "with an explicit UTC offset, such as 2026-09-23T14:30:00-04:00."
            ),
            default=default,
        )
        assert value is not None
        try:
            return ExplicitOffsetTimestamp(value)
        except Exception:
            _show_result(
                "Record Event — When",
                ("That date/time is not valid. Include an explicit UTC offset.",),
            )


def _review_lines(
    owner: ClassOption,
    request: EventAuthoringInput,
    selected: tuple[SelectedParticipant, ...],
) -> tuple[str, ...]:
    location = request.location_type.replace("_", " ").title()
    if request.location_detail:
        location = f"{location}: {request.location_detail}"
    lines: list[str] = [
        f"Owning class: {owner.class_id}",
        f"School year: {request.school_year}",
        f"When: {request.occurrence.text}",
        f"Where: {location}",
        f"Summary: {request.summary}",
        "People involved:",
    ]
    for participant in selected:
        option = participant.option
        context = (
            "owning class" if option.class_id == owner.class_id else option.class_id
        )
        lines.append(f"  - {option.display_name} — {context}")
    lines.extend(
        (
            "",
            "This records Event context and participation only.",
            (
                "It does not create an Account, Observation, Determination, "
                "Response, or Support record."
            ),
        )
    )
    return tuple(lines)


def commit_prepared_event(
    workspace_root: str | Path,
    prepared: PreparedEventBundle,
) -> str:
    """Commit one prepared Event through the existing coordinated workflow service."""

    result = EventBundleWorkflowService(workspace_root).commit(
        prepared.bundle,
        operation_id=prepared.operation_id,
    )
    work_id = prepared.bundle.event.work_id
    if work_id is None:
        raise RuntimeError("committed Event has no work identity")
    if not result.accepted_steps:
        raise RuntimeError("Event commit accepted no canonical steps")
    return work_id


def record_event_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Collect, preview, and deliberately commit one teacher-entered Event."""

    menu_clock = clock or MenuClock()
    id_generator = ids or PortiaIdGenerator()
    root = state.resolve_workspace()
    owner = _choose_class(root, title="Record Event — Owning Class")
    state.remember_class(owner.class_id)
    operator = _require_operator(state)
    occurrence = _occurrence(menu_clock)
    summary = prompt_text(
        "Record Event — Summary",
        "Summary",
        help_text=(
            "Enter a concise neutral description of what happened. "
            "Do not turn the Event summary into a finding or determination."
        ),
    )
    assert summary is not None
    location_type, location_detail = _choose_location()
    selected = _collect_participants(root, owner)
    request = EventAuthoringInput(
        owner_class_id=owner.class_id,
        school_year=owner.school_year,
        occurrence=occurrence,
        summary=summary,
        location_type=location_type,
        location_detail=location_detail,
        local_operator_label=operator,
        participants=tuple(
            RosterParticipantInput(
                class_id=item.option.class_id,
                student_id=item.option.student_id,
                display_name=item.option.display_name,
            )
            for item in selected
        ),
    )
    prepared = prepare_event_bundle(request, clock=menu_clock, ids=id_generator)
    if not confirm_write(
        "Record Event — Review",
        "CREATE",
        _review_lines(owner, request, selected),
        help_text=(
            "CREATE writes this Event and its selected Participants together through "
            "Portia's existing coordinated persistence service."
        ),
    ):
        return

    current_metadata = load_class_metadata_for_class(root, owner.class_id)
    if current_metadata.school_year != owner.school_year:
        raise ValueError(
            "The selected class changed while this Event was being prepared. "
            "Return and review the current class state before trying again."
        )
    work_id = commit_prepared_event(root, prepared)
    state.remember_work(
        class_id=owner.class_id,
        work_kind="event",
        work_id=work_id,
    )
    _show_result(
        "Event Saved",
        (
            "Event saved with the selected people involved.",
            (
                "No Account, Observation, Determination, Response, Support, "
                "Follow-Up, or Outcome was created automatically."
            ),
        ),
    )


def launch_record_event_menu(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Launch the bounded Record Event task surface."""

    while True:
        clear_screen()
        print_menu_header("Record Event")
        print("Record what happened and who was involved.")
        print()
        print("1. Record a new Event")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Record Event Help")
            print("An Event records context and participation, not a finding.")
            print("The owning class is selected explicitly from Core authority.")
            print("Cross-class participants keep their original roster identity.")
            print()
            pause_for_user()
        elif navigation is NavigationChoice.BACK:
            return
        elif raw == "1":
            try:
                record_event_once(state, clock=clock, ids=ids)
            except CancelMenuAction:
                continue
            except (ReturnToMainMenu, QuitPDS, EOFError):
                raise
            except PortiaOperationPartialCommitError:
                _show_result(
                    "Record Event Interrupted",
                    (
                        "Part of this Event operation may already be durable.",
                        "Do not retry the same entry blindly.",
                        (
                            "Use Advanced Portia tools to inspect Recovery "
                            "before continuing."
                        ),
                    ),
                )
            except PortiaQuarantinedError:
                _show_result(
                    "Record Event Blocked",
                    (
                        (
                            "Quarantine currently blocks this Event write "
                            "or current use."
                        ),
                        "Inspect the exact Portia state before trying another write.",
                    ),
                )
            except PortiaCorruptionError:
                _show_result(
                    "Record Event Blocked",
                    (
                        "Portia detected canonical storage it cannot safely trust.",
                        "No write or automatic repair was attempted.",
                    ),
                )
            except PortiaConflictError:
                _show_result(
                    "Record Event Conflict",
                    (
                        (
                            "Canonical Portia state changed or conflicted "
                            "with this write."
                        ),
                        "Review the current state before trying again.",
                    ),
                )
            except PortiaRecoveryRequiredError:
                _show_result(
                    "Record Event Blocked",
                    (
                        (
                            "Existing Portia state requires explicit Recovery "
                            "before this write."
                        ),
                        "No automatic recovery action was attempted.",
                    ),
                )
            except PortiaStorageError:
                _show_result(
                    "Record Event Error",
                    (
                        "Portia storage could not safely complete this Event.",
                        "No automatic retry was attempted.",
                    ),
                )
            except (PortiaWorkflowError, ValueError) as error:
                _show_result("Record Event Error", (str(error),))
            except Exception:
                _show_result(
                    "Record Event Error",
                    (
                        "Portia could not complete this Event.",
                        "No automatic retry or recovery action was attempted.",
                    ),
                )
        else:
            print(navigation_hint_with_help())
            pause_for_user()
