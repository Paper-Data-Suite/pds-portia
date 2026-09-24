"""Task-oriented teacher-menu entry point for Portia."""

from __future__ import annotations

from dataclasses import dataclass

from portia.menu.context import MenuSessionContext
from portia.menu.event import launch_record_event_menu
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    QuitPDS,
    ReturnToMainMenu,
    navigation_hint_with_help,
    navigation_labels_with_help,
    parse_menu_navigation,
)
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)


@dataclass(frozen=True, slots=True)
class MenuTask:
    """One teacher-facing task label and its bounded purpose statement."""

    key: str
    label: str
    purpose: str


PRIMARY_TASKS: tuple[MenuTask, ...] = (
    MenuTask("1", "Record Event", "Record what happened and who was involved."),
    MenuTask(
        "2",
        "Add Information",
        "Add reported information, direct observations, or explicit human judgment.",
    ),
    MenuTask(
        "3",
        "Record Response / Communication",
        "Record a bounded response or communication without inferring its effect.",
    ),
    MenuTask(
        "4",
        "Manage Support",
        "Plan, provide, and review teacher-local support while preserving distinctions.",
    ),
    MenuTask(
        "5",
        "Complete Follow-Up",
        "Review due follow-up work and record only the exact follow-up completed.",
    ),
    MenuTask(
        "6",
        "View Timeline",
        "View the privacy-minimized current history for an exact roster student.",
    ),
    MenuTask(
        "7",
        "Correct / Retract",
        "Route corrections through the record family's existing lifecycle authority.",
    ),
    MenuTask(
        "8",
        "Attention Needed",
        "View native Portia attention without adding ranking or risk scoring.",
    ),
)
ADVANCED_TASK = MenuTask(
    "9",
    "Advanced Portia tools",
    "Reach exact record-family administration, integrity, recovery, and expert tools.",
)
ALL_TASKS: tuple[MenuTask, ...] = (*PRIMARY_TASKS, ADVANCED_TASK)


def render_main_menu() -> str:
    """Render the zero-read task-oriented main menu."""

    lines = ["Portia", ""]
    lines.extend(f"{task.key}. {task.label}" for task in ALL_TASKS)
    lines.append("")
    lines.extend(
        navigation_labels_with_help(
            back=False,
            main_menu=False,
        )
    )
    return "\n".join(lines)


def _main_help() -> None:
    clear_screen()
    print_menu_header("Help")
    print("Choose the task that matches what you are trying to do.")
    print("Portia keeps exact record, identity, evidence, and lifecycle distinctions")
    print("underneath this teacher-facing task organization.")
    print("Viewing or navigating the menu does not create canonical Portia records.")
    print()
    pause_for_user()


def _task_help(task: MenuTask) -> None:
    clear_screen()
    print_menu_header(f"{task.label} Help")
    print(task.purpose)
    print("Task navigation is presentation only; existing Portia services remain authoritative.")
    print()
    pause_for_user()


def _launch_foundation_task(task: MenuTask, state: MenuSessionContext) -> None:
    """Expose one safe task surface while task-specific workflows are added."""

    del state
    while True:
        clear_screen()
        print_menu_header(task.label)
        print(task.purpose)
        print()
        print("Task-specific actions are not wired on this surface yet.")
        print_navigation()
        print()
        choice = input("Select an option: ").strip()
        navigation = parse_menu_navigation(choice)
        if navigation is PortiaMenuChoice.HELP:
            _task_help(task)
        elif navigation is NavigationChoice.BACK:
            return
        else:
            print(navigation_hint_with_help())
            pause_for_user()


def _main_menu_once(state: MenuSessionContext) -> None:
    clear_screen()
    print(render_main_menu())
    print()
    choice = input("Select an option: ").strip()
    navigation = parse_menu_navigation(
        choice,
        allow_back=False,
        allow_main_menu=False,
    )
    if navigation is PortiaMenuChoice.HELP:
        _main_help()
        return
    if choice == "1":
        launch_record_event_menu(state)
        return
    for task in ALL_TASKS:
        if choice == task.key:
            _launch_foundation_task(task, state)
            return
    print(
        navigation_hint_with_help(
            back=False,
            main_menu=False,
        )
    )
    pause_for_user()


def launch_menu(state: MenuSessionContext | None = None) -> int:
    """Launch Portia and unwind B/M/Q/Ctrl+C/EOF cleanly."""

    session = state or MenuSessionContext()
    while True:
        try:
            _main_menu_once(session)
        except ReturnToMainMenu:
            continue
        except (QuitPDS, KeyboardInterrupt, EOFError):
            clear_screen()
            return 0
