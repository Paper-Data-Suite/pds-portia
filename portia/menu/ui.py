"""Small presentation helpers for Portia teacher-facing terminal menus."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import TypeVar

from portia.menu.navigation import navigation_labels_with_help

T = TypeVar("T")
PAGE_SIZE = 10


def clear_screen() -> None:
    """Clear an interactive terminal, but never captured/noninteractive output."""

    try:
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, OSError):
        interactive = False
    if interactive:
        os.system("cls" if os.name == "nt" else "clear")


def pause_for_user(message: str = "Press Enter to continue...") -> None:
    """Pause inside the teacher-facing interactive surface."""

    input(message)


def print_menu_header(title: str | None = None) -> None:
    """Print the Portia identity plus an optional compact section title."""

    print("Portia")
    if title:
        print(title)
    print()


def print_navigation(
    *,
    help: bool = True,
    back: bool = True,
    main_menu: bool = True,
    quit: bool = True,
) -> None:
    """Print enabled teacher-menu navigation commands."""

    for label in navigation_labels_with_help(
        help=help,
        back=back,
        main_menu=main_menu,
        quit=quit,
    ):
        print(label)


def page_count(item_count: int, *, page_size: int = PAGE_SIZE) -> int:
    """Return at least one page for deterministic menu pagination."""

    if page_size < 1:
        raise ValueError("page_size must be positive.")
    return max(1, (item_count + page_size - 1) // page_size)


def page_items(
    items: Sequence[T],
    page_index: int,
    *,
    page_size: int = PAGE_SIZE,
) -> tuple[T, ...]:
    """Return one deterministic page of items."""

    pages = page_count(len(items), page_size=page_size)
    if page_index < 0 or page_index >= pages:
        raise ValueError("page_index is outside the available range.")
    start = page_index * page_size
    return tuple(items[start : start + page_size])
