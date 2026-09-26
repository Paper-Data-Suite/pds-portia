"""Controlled teacher-facing prompts for Portia menu workflows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    parse_menu_navigation,
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

T = TypeVar("T")


class CancelMenuAction(Exception):
    """Cancel the current uncommitted menu action and return to its parent."""


def prompt_text(
    title: str,
    label: str,
    *,
    help_text: str,
    default: str | None = None,
    optional: bool = False,
) -> str | None:
    """Prompt for one bounded text value while preserving H/B/M/Q semantics."""

    while True:
        clear_screen()
        print_menu_header(title)
        print(help_text)
        if default is not None:
            print(f"Press Enter to use: {default}")
        elif optional:
            print("Press Enter to leave this blank.")
        print()
        print_navigation()
        print()
        raw = input(f"{label}: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header(f"{title} Help")
            print(help_text)
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            raise CancelMenuAction
        if not raw:
            if default is not None:
                return default
            if optional:
                return None
            print(f"{label} is required.")
            pause_for_user()
            continue
        return raw


def _selection_hint(page_index: int, pages: int) -> str:
    commands: list[str] = []
    if page_index + 1 < pages:
        commands.append("N")
    if page_index > 0:
        commands.append("P")
    commands.extend(("H", "B", "M", "Q"))
    if len(commands) == 1:
        suffix = commands[0]
    elif len(commands) == 2:
        suffix = f"{commands[0]} or {commands[1]}"
    else:
        suffix = ", ".join(commands[:-1]) + f", or {commands[-1]}"
    return f"Please choose a listed option, {suffix}."


def select_one(
    title: str,
    values: Sequence[T],
    labels: Sequence[str],
    *,
    help_text: str,
    page_size: int = PAGE_SIZE,
) -> T:
    """Select one exact value by position with deterministic pagination."""

    if len(values) != len(labels):
        raise ValueError("values and labels must have the same length")
    if not values:
        raise ValueError("at least one selectable value is required")

    pages = page_count(len(values), page_size=page_size)
    page_index = 0
    while True:
        clear_screen()
        print_menu_header(title)
        page_values = page_items(values, page_index, page_size=page_size)
        start = page_index * page_size
        for offset, _value in enumerate(page_values, start=1):
            print(f"{offset}. {labels[start + offset - 1]}")
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
            clear_screen()
            print_menu_header(f"{title} Help")
            print(help_text)
            print("Selection is by exact listed position; names are display aids only.")
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            raise CancelMenuAction
        if raw.isdigit():
            local_index = int(raw) - 1
            if 0 <= local_index < len(page_values):
                return page_values[local_index]
        print(_selection_hint(page_index, pages))
        pause_for_user()


def confirm_write(
    title: str,
    verb: str,
    lines: Sequence[str],
    *,
    help_text: str,
) -> bool:
    """Require an action-specific uppercase confirmation before a write."""

    normalized_verb = verb.strip().upper()
    if not normalized_verb or not normalized_verb.isalpha():
        raise ValueError("confirmation verb must contain letters only")

    while True:
        clear_screen()
        print_menu_header(title)
        for line in lines:
            print(line)
        print()
        print(f"Type {normalized_verb} exactly to continue, or press Enter to cancel.")
        print_navigation()
        print()
        raw = input("Confirmation: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header(f"{title} Help")
            print(help_text)
            print("No canonical Portia record is written until confirmation succeeds.")
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK or not raw:
            return False
        if raw == normalized_verb:
            return True
        print(f"Type uppercase {normalized_verb} exactly, or use H, B, M, or Q.")
        pause_for_user()
