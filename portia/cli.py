"""Command-line entry point for Portia's teacher-local application."""

from __future__ import annotations

import argparse
from importlib import metadata
from typing import Sequence

from portia._version import __version__
from portia.menu import launch_menu, render_main_menu

CORE_DISTRIBUTION = "pds-core"
CORE_REQUIREMENT = "pds-core>=0.6.3,<0.7"


def installed_core_version() -> str | None:
    """Return the installed Core distribution version, if available."""

    try:
        return metadata.version(CORE_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return None


def render_status() -> str:
    """Render non-mutating package/Core status information."""

    core_version = installed_core_version()
    installed = core_version if core_version is not None else "not installed"
    return "\n".join(
        (
            f"Portia {__version__}",
            "Runtime stage: v0.2 task-oriented teacher menu",
            f"Core requirement: {CORE_REQUIREMENT}",
            f"Installed Core: {installed}",
            "Teacher data access: none in this status command",
        )
    )


def render_menu() -> str:
    """Render the zero-read production main-menu taxonomy."""

    return render_main_menu()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portia",
        description="Portia teacher-local behavior-support and response tooling.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Portia {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "status",
        help="show package/Core status without reading teacher data",
    )
    subparsers.add_parser(
        "menu",
        help="launch the task-oriented Portia teacher menu",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print(render_status())
        return 0

    if args.command in {None, "menu"}:
        return launch_menu()

    parser.error(f"unsupported command: {args.command}")
    return 2
