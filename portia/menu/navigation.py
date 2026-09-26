"""Portia teacher-menu navigation built on Core B/M/Q semantics."""

from __future__ import annotations

from enum import Enum

from pds_core.menu_navigation import (
    NavigationChoice,
    QuitPDS,
    ReturnToMainMenu,
    navigation_labels,
    parse_navigation_choice,
)


class PortiaMenuChoice(Enum):
    """Portia-only controlled-prompt choices."""

    HELP = "h"


def parse_menu_navigation(
    value: str,
    *,
    allow_help: bool = True,
    allow_back: bool = True,
    allow_main_menu: bool = True,
    allow_quit: bool = True,
) -> PortiaMenuChoice | NavigationChoice | None:
    """Parse H plus Core-owned B/M/Q navigation semantics."""

    normalized = value.strip().casefold()
    if normalized == PortiaMenuChoice.HELP.value and allow_help:
        return PortiaMenuChoice.HELP
    return parse_navigation_choice(
        value,
        allow_back=allow_back,
        allow_main_menu=allow_main_menu,
        allow_quit=allow_quit,
    )


def navigation_labels_with_help(
    *,
    help: bool = True,
    back: bool = True,
    main_menu: bool = True,
    quit: bool = True,
) -> tuple[str, ...]:
    """Return enabled H/B/M/Q labels in Portia display order."""

    labels: list[str] = []
    if help:
        labels.append("H. Help")
    labels.extend(
        navigation_labels(
            back=back,
            main_menu=main_menu,
            quit=quit,
        )
    )
    return tuple(labels)


def navigation_hint_with_help(
    *,
    help: bool = True,
    back: bool = True,
    main_menu: bool = True,
    quit: bool = True,
) -> str:
    """Return invalid-selection guidance naming only enabled commands."""

    keys: list[str] = []
    if help:
        keys.append("H")
    if back:
        keys.append("B")
    if main_menu:
        keys.append("M")
    if quit:
        keys.append("Q")
    if not keys:
        return "Please choose a listed option."
    if len(keys) == 1:
        commands = keys[0]
    elif len(keys) == 2:
        commands = f"{keys[0]} or {keys[1]}"
    else:
        commands = ", ".join(keys[:-1]) + f", or {keys[-1]}"
    return f"Please choose a listed option, {commands}."


__all__ = [
    "NavigationChoice",
    "PortiaMenuChoice",
    "QuitPDS",
    "ReturnToMainMenu",
    "navigation_hint_with_help",
    "navigation_labels_with_help",
    "parse_menu_navigation",
]
