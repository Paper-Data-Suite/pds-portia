"""Bootstrap command-line surface for Portia v0.2 development."""

from __future__ import annotations

import argparse
from importlib import metadata
from typing import Sequence

from portia._version import __version__

CORE_DISTRIBUTION = "pds-core"
CORE_REQUIREMENT = "pds-core>=0.6.3,<0.7"

_BOOTSTRAP_MENU = (
    "Record Event",
    "Add Information",
    "Record Response / Communication",
    "Manage Support",
    "Complete Follow-Up",
    "View Timeline",
    "Correct / Retract",
    "Attention Needed",
)


def installed_core_version() -> str | None:
    """Return the installed Core distribution version, if available."""

    try:
        return metadata.version(CORE_DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return None


def render_status() -> str:
    """Render non-mutating bootstrap status information."""

    core_version = installed_core_version()
    installed = core_version if core_version is not None else "not installed"
    return "\n".join(
        (
            f"Portia {__version__}",
            "Runtime stage: v0.2 bootstrap chassis",
            f"Core requirement: {CORE_REQUIREMENT}",
            f"Installed Core: {installed}",
            "Teacher data access: none in this bootstrap command",
        )
    )


def render_menu() -> str:
    """Render the bounded #36 menu scaffold without reading teacher data."""

    lines = [
        "Portia — teacher-local behavior-support and response",
        "",
        "Executable workflow status: bootstrap only.",
        "The following v0.2 teacher tasks are planned but are not implemented by #36:",
    ]
    lines.extend(f"  - {label} [planned]" for label in _BOOTSTRAP_MENU)
    lines.extend(
        (
            "",
            "No Event, Response, Support, Follow-Up, timeline, or correction data was read or written.",
        )
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portia",
        description=(
            "Portia bootstrap CLI for the teacher-local behavior-support and response module."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Portia {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "status",
        help="show package/Core bootstrap status without reading teacher data",
    )
    subparsers.add_parser(
        "menu",
        help="show the bounded v0.2 teacher-task menu scaffold",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bootstrap CLI and return a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        print(render_status())
        return 0

    if args.command in {None, "menu"}:
        print(render_menu())
        return 0

    parser.error(f"unsupported command: {args.command}")
    return 2
