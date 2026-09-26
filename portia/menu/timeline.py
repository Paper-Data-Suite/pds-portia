"""Teacher-facing privacy-minimized student timeline workflow."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from portia.menu.context import MenuSessionContext
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import CancelMenuAction, select_one
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
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import RosterStudentRef
from portia.storage.errors import PortiaCorruptionError, PortiaStorageError
from portia.views import (
    ProjectedField,
    SemanticTimelineMarker,
    StudentTimelineQuery,
    StudentTimelineService,
    StudentTimelineViewResult,
    StudentViewEntry,
    StudentViewScope,
    StudentWorkTimelineView,
    ViewMode,
)


@dataclass(frozen=True, slots=True)
class TimelineWorkOption:
    """One exact discovered work with bounded teacher-facing presentation."""

    work: StudentWorkTimelineView
    label: str


_DISPOSITION_LABELS = {
    "included": "Details available",
    "withheld": "Details withheld by privacy policy",
    "unavailable": "Details unavailable in this view",
    "requires_manual_review": "Details require manual review",
}


def _bounded(value: str, *, limit: int = 72) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _student_label(student: StudentOption) -> str:
    return f"{student.display_name} — {student.class_id} — Period {student.period}"


def _marker_label(marker: SemanticTimelineMarker) -> str:
    if marker.precision == "unknown" or marker.start is None:
        return "Time not available"

    if marker.precision == "timestamp_range" and marker.end is not None:
        value = f"{marker.start} to {marker.end}"
    elif marker.precision == "date_range" and marker.end is not None:
        value = f"{marker.start} to {marker.end}"
    elif marker.precision == "approximate_timestamp":
        qualifier = marker.approximation or "about"
        value = f"{qualifier.replace('_', ' ')} {marker.start}"
    else:
        value = marker.start

    if marker.planned:
        return f"Planned: {value}"
    return value


def _field_line(field: ProjectedField) -> str | None:
    if field.disposition != "included" or field.value is None:
        return None
    value = _bounded(str(field.value), limit=88)
    return f"   {_humanize(field.name)}: {value}"


def _entry_lines(entry: StudentViewEntry) -> tuple[str, ...]:
    history = (
        "Current"
        if entry.history_kind == "current_representation"
        else "Historical"
    )
    status = f" — {_humanize(entry.status)}" if entry.status else ""
    lines = [
        (
            f"{history} — {_humanize(entry.semantic_type)} — "
            f"{_humanize(entry.category)}{status}"
        ),
        f"   {_marker_label(entry.marker)}",
    ]
    disposition = _DISPOSITION_LABELS.get(
        entry.disposition,
        _humanize(entry.disposition),
    )
    lines.append(f"   {disposition}")
    for field in entry.fields:
        line = _field_line(field)
        if line is not None:
            lines.append(line)
    return tuple(lines)


def _show_result(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def student_timeline_query(
    student: StudentOption,
    *,
    history: bool,
) -> StudentTimelineQuery:
    """Build one exact, class-bounded student-view query."""

    roster_ref = RosterStudentRef(
        class_id=student.class_id,
        student_id=student.student_id,
    )
    scope = StudentViewScope(
        focal_students=(roster_ref,),
        allowed_class_ids=(student.class_id,),
        history_allowed=history,
        purpose="teacher_current",
    )
    mode: ViewMode = "history" if history else "current"
    return StudentTimelineQuery(
        scope=scope,
        mode=mode,
    )


def student_timeline_result(
    root: Path,
    student: StudentOption,
    *,
    history: bool,
) -> StudentTimelineViewResult:
    """Delegate one bounded read directly to the production student-view service."""

    return StudentTimelineService(root).generate(
        student_timeline_query(student, history=history)
    )


def _browse_entries(
    student: StudentOption,
    entries: tuple[StudentViewEntry, ...],
    *,
    title: str,
    help_text: str,
) -> None:
    if not entries:
        _show_result(
            title,
            (
                _student_label(student),
                "No privacy-safe entries are available for this view.",
            ),
        )
        return

    pages = page_count(len(entries), page_size=PAGE_SIZE)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header(title)
        print(_student_label(student))
        print()
        current = page_items(entries, page_index, page_size=PAGE_SIZE)
        start = page_index * PAGE_SIZE
        for offset, entry in enumerate(current, start=1):
            print(f"{start + offset}. {_entry_lines(entry)[0]}")
            for line in _entry_lines(entry)[1:]:
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
            clear_screen()
            print_menu_header(f"{title} Help")
            print(help_text)
            print(
                "Only privacy-projected scalar fields are displayed. "
                "Withheld, unavailable, and manual-review states remain distinct."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        print(navigation_hint_with_help())
        pause_for_user()


def _work_options(
    works: tuple[StudentWorkTimelineView, ...],
) -> tuple[TimelineWorkOption, ...]:
    preliminary: list[tuple[StudentWorkTimelineView, str]] = []
    for work in works:
        kind = "Event" if work.work_ref.work_kind == "event" else "Support Process"
        status = _humanize(work.current_status) if work.current_status else "Status unavailable"
        year = work.school_year or "School year unavailable"
        timing = _marker_label(work.semantic_work_timing)
        label = f"{kind} — {year} — {status} — {timing}"
        preliminary.append((work, label))

    counts = Counter(label.casefold() for _work, label in preliminary)
    options: list[TimelineWorkOption] = []
    for work, label in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact {work.work_ref.work_id}"
        options.append(TimelineWorkOption(work, label))
    return tuple(options)


def _view_current_timeline(root: Path, student: StudentOption) -> None:
    result = student_timeline_result(root, student, history=False)
    _browse_entries(
        student,
        result.entries,
        title="View Timeline — Current",
        help_text=(
            "Current mode is the privacy-minimized production student view. "
            "It uses canonical current-use authority and does not include superseded "
            "or invalidated representations as independent current facts."
        ),
    )


def _open_current_work(root: Path, student: StudentOption) -> None:
    result = student_timeline_result(root, student, history=False)
    options = _work_options(result.works)
    if not options:
        _show_result(
            "View Timeline — Open Work",
            (
                _student_label(student),
                "No current Event or Support Process grouping is available.",
            ),
        )
        return

    selected = select_one(
        "View Timeline — Open Work",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Each choice is one exact Event or Support Process discovered by the "
            "production student-view service. Display labels are not lookup authority."
        ),
    )
    _browse_entries(
        student,
        selected.work.current_items,
        title="View Timeline — Current Work",
        help_text=(
            "This screen contains only the current privacy-projected entries for the "
            "selected exact work. Related work is not merged into this work item."
        ),
    )


def _view_history(root: Path, student: StudentOption) -> None:
    result = student_timeline_result(root, student, history=True)
    history_entries = tuple(
        entry
        for entry in result.entries
        if entry.history_kind != "current_representation"
    )
    _browse_entries(
        student,
        history_entries,
        title="View Timeline — Deliberate History",
        help_text=(
            "History mode is explicit and separate from the current timeline. "
            "Historical representations remain pinned to their exact identities and "
            "do not silently follow successors, corrections, migrations, or removals."
        ),
    )


def _student_view_menu(
    state: MenuSessionContext,
    root: Path,
    student: StudentOption,
) -> None:
    while True:
        clear_screen()
        print_menu_header("View Timeline")
        print(_student_label(student))
        print()
        print("1. Current timeline")
        print("2. Open a current work item")
        print("3. View deliberate history")
        print("4. Choose another student")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("View Timeline Help")
            print(
                "Current view is privacy-minimized and read-only. History is shown "
                "only after an explicit history action."
            )
            print(
                "The focal student is the exact Core roster identity "
                "(class_id, student_id); names are display aids only."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        if raw == "1":
            _view_current_timeline(root, student)
            continue
        if raw == "2":
            _open_current_work(root, student)
            continue
        if raw == "3":
            _view_history(root, student)
            continue
        if raw == "4":
            return
        print(navigation_hint_with_help())
        pause_for_user()


def _select_student(
    state: MenuSessionContext,
    root: Path,
) -> StudentOption | None:
    classes = class_options(root)
    if not classes:
        _show_result(
            "View Timeline",
            ("No Core classes with both metadata and a roster are available.",),
        )
        return None

    selected_class: ClassOption = select_one(
        "View Timeline — Class",
        classes,
        tuple(item.label for item in classes),
        help_text=(
            "Choose the authoritative Core roster class containing the focal student. "
            "Class ownership for Portia work remains separate from student identity."
        ),
    )
    state.remember_class(selected_class.class_id)

    students = student_options(root, selected_class.class_id)
    if not students:
        _show_result(
            "View Timeline",
            (f"No roster students are available in {selected_class.class_id}.",),
        )
        return None

    return select_one(
        "View Timeline — Student",
        students,
        tuple(item.label for item in students),
        help_text=(
            "Select by the exact class-qualified Core roster row. Matching names or "
            "bare student IDs in another class are not identity authority."
        ),
    )


def launch_view_timeline_menu(state: MenuSessionContext) -> None:
    """Launch the read-only Issue #48 student timeline/work-view surface."""

    while True:
        clear_screen()
        print_menu_header("View Timeline")
        print(
            "View Portia information through the privacy-minimized production "
            "student timeline/work view."
        )
        print()
        print("1. Select a student")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("View Timeline Help")
            print(
                "The menu delegates to StudentTimelineService and never assembles a "
                "parallel student dossier or behavior narrative."
            )
            print(
                "Viewing, grouping, sorting, or opening a work item is read-only and "
                "does not mutate Portia or Core."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        if raw != "1":
            print(navigation_hint_with_help())
            pause_for_user()
            continue

        try:
            root = state.resolve_workspace()
            student = _select_student(state, root)
            if student is not None:
                _student_view_menu(state, root, student)
        except CancelMenuAction:
            continue
        except (
            PortiaCorruptionError,
            PortiaLocalValidationError,
            PortiaStorageError,
            ValueError,
        ) as exc:
            _show_result(
                "View Timeline — Unable to Display",
                (
                    "The requested privacy-minimized view could not be displayed.",
                    _bounded(str(exc), limit=120),
                ),
            )
