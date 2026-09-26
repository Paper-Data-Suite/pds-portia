"""Mechanically validate the Issue #50 task-oriented teacher menu."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_RUNTIME = {
    "portia/menu/__init__.py",
    "portia/menu/advanced.py",
    "portia/menu/attention.py",
    "portia/menu/authoring.py",
    "portia/menu/clock.py",
    "portia/menu/context.py",
    "portia/menu/correction.py",
    "portia/menu/event.py",
    "portia/menu/follow_up.py",
    "portia/menu/identifiers.py",
    "portia/menu/information.py",
    "portia/menu/judgment.py",
    "portia/menu/main.py",
    "portia/menu/navigation.py",
    "portia/menu/prompts.py",
    "portia/menu/response_communication.py",
    "portia/menu/selectors.py",
    "portia/menu/support.py",
    "portia/menu/support_delivery.py",
    "portia/menu/timeline.py",
    "portia/menu/ui.py",
}
_REQUIRED_TESTS = {
    "tests/test_cli.py",
    "tests/test_teacher_menu_foundation.py",
    "tests/test_teacher_menu_event.py",
    "tests/test_teacher_menu_information.py",
    "tests/test_teacher_menu_judgment.py",
    "tests/test_teacher_menu_response_communication.py",
    "tests/test_teacher_menu_support.py",
    "tests/test_teacher_menu_support_planning.py",
    "tests/test_teacher_menu_support_delivery.py",
    "tests/test_teacher_menu_follow_up.py",
    "tests/test_teacher_menu_timeline.py",
    "tests/test_teacher_menu_correction.py",
    "tests/test_teacher_menu_attention.py",
    "tests/test_teacher_menu_advanced.py",
    "tests/test_issue50_teacher_menu_validation.py",
}
_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue50_package.py",
    "scripts/smoke_test_issue50_teacher_menu_wheel.py",
}
_REQUIRED_DOCS = {
    "docs/task-oriented-teacher-menu.md",
    "docs/validation/issue-50-task-oriented-teacher-menu-validation.md",
}
_TASK_LABELS = (
    "Record Event",
    "Add Information",
    "Record Response / Communication",
    "Manage Support",
    "Complete Follow-Up",
    "View Timeline",
    "Correct / Retract",
    "Attention Needed",
    "Advanced Portia tools",
)
_REQUIRED_LAUNCHERS = (
    "launch_record_event_menu",
    "launch_add_information_menu",
    "launch_response_communication_menu",
    "launch_manage_support_menu",
    "launch_complete_follow_up_menu",
    "launch_view_timeline_menu",
    "launch_correct_retract_menu",
    "launch_attention_needed_menu",
    "launch_advanced_menu",
)
_FORBIDDEN_IDENTIFIERS = {
    "attention_score",
    "behavior_score",
    "danger_score",
    "priority_score",
    "risk_score",
    "severity_score",
    "student_ranking",
    "urgency_score",
    "fuzzy_match",
    "fuzzy_resolve",
    "name_only_resolver",
    "raw_json_editor",
}
_DIRECT_MUTATION_CALLS = (
    ".write_text(",
    ".write_bytes(",
    ".unlink(",
    ".rename(",
    "os.remove(",
    "shutil.rmtree(",
    ".create_work(",
    ".replace_work(",
    ".create_work_record(",
    ".replace_work_record(",
)
_SIBLING_RUNTIME_NAMES = {
    "concord",
    "meridian",
    "quillan",
    "scoreform",
    "vitrine",
}


def _read(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"required Issue #50 file is unavailable: {relative}"
        ) from exc


def _require_files(root: Path, paths: set[str]) -> None:
    missing = sorted(
        relative for relative in paths if not (root / relative).is_file()
    )
    if missing:
        raise RuntimeError(f"missing Issue #50 files: {missing}")


def _python_names(root: Path) -> set[str]:
    found: set[str] = set()
    for relative in sorted(_REQUIRED_RUNTIME):
        tree = ast.parse(_read(root, relative), filename=relative)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                found.add(node.name)
            elif isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
    return found


def _validate_source(root: Path) -> None:
    _require_files(root, _REQUIRED_RUNTIME | _REQUIRED_TESTS | _REQUIRED_DOCS)

    cli = _read(root, "portia/cli.py")
    for marker in (
        "from portia.menu import launch_menu, render_main_menu",
        'if args.command in {None, "menu"}:',
        "return launch_menu()",
        "Teacher data access: none in this status command",
    ):
        if marker not in cli:
            raise RuntimeError(f"production CLI marker is missing: {marker}")
    if "[planned]" in cli or "bootstrap only" in cli:
        raise RuntimeError("production CLI still contains bootstrap/planned language")

    main = _read(root, "portia/menu/main.py")
    for label in _TASK_LABELS:
        if label not in main:
            raise RuntimeError(f"teacher main menu is missing task label: {label}")
    for launcher in _REQUIRED_LAUNCHERS:
        if launcher not in main:
            raise RuntimeError(f"teacher main menu is missing launcher: {launcher}")
    for forbidden in (
        "_launch_foundation_task",
        "Task-specific actions are not wired",
        "[planned]",
    ):
        if forbidden in main:
            raise RuntimeError(
                f"teacher main menu retains obsolete scaffold marker: {forbidden}"
            )

    navigation = _read(root, "portia/menu/navigation.py")
    for marker in (
        "from pds_core.menu_navigation import",
        "QuitPDS",
        "ReturnToMainMenu",
        "parse_navigation_choice",
        "H. Help",
    ):
        if marker not in navigation:
            raise RuntimeError(f"Core navigation marker is missing: {marker}")

    context = _read(root, "portia/menu/context.py")
    for marker in (
        "resolve_workspace_root",
        "clear_target_context",
        "selected_class_id",
        "selected_work_id",
    ):
        if marker not in context:
            raise RuntimeError(f"menu context marker is missing: {marker}")
    if any(
        token in context
        for token in (
            "write_text(",
            "write_bytes(",
            "json.dump(",
            "pickle.",
        )
    ):
        raise RuntimeError("menu session context became durable state")

    identifiers = _read(root, "portia/menu/identifiers.py")
    if "secrets.token_hex" not in identifiers or "validate_portia_id" not in identifiers:
        raise RuntimeError("opaque production ID generation contract is missing")

    clock = _read(root, "portia/menu/clock.py")
    for marker in (
        "MenuClock",
        "ExplicitOffsetTimestamp",
        "tzinfo",
        "utcoffset",
    ):
        if marker not in clock:
            raise RuntimeError(f"explicit menu clock marker is missing: {marker}")

    timeline = _read(root, "portia/menu/timeline.py")
    if "StudentTimelineService" not in timeline or "StudentTimelineQuery" not in timeline:
        raise RuntimeError("Timeline no longer delegates to Issue #48 student views")

    attention = _read(root, "portia/menu/attention.py")
    for marker in (
        "AttentionQueryService",
        "PortiaAttentionQuery",
        "ATTENTION_ROUTE_BY_CODE",
        "PORTIA_ATTENTION_PARTIAL_NOTICE",
    ):
        if marker not in attention:
            raise RuntimeError(f"Attention delegation marker is missing: {marker}")
    if re.search(r"if .*code.* in .*item\.code", attention):
        raise RuntimeError("Attention routing appears to classify codes by substring")

    combined = "\n".join(
        _read(root, relative) for relative in sorted(_REQUIRED_RUNTIME)
    )
    for call in _DIRECT_MUTATION_CALLS:
        if call in combined:
            raise RuntimeError(
                f"menu application layer contains direct canonical mutation call: {call}"
            )

    names = _python_names(root)
    forbidden_names = sorted(_FORBIDDEN_IDENTIFIERS & names)
    if forbidden_names:
        raise RuntimeError(
            f"forbidden menu/scoring identifiers are present: {forbidden_names}"
        )
    if "fuzzy" in combined.lower():
        raise RuntimeError("menu runtime contains fuzzy-resolution language")

    schema_root = root / "schemas"
    if schema_root.is_dir():
        for path in schema_root.rglob("*.json"):
            lowered = path.name.lower()
            if "teacher_menu" in lowered or "menu_session" in lowered:
                raise RuntimeError(
                    "Issue #50 must not add durable teacher-menu/session schemas"
                )

    pyproject = _read(root, "pyproject.toml").lower()
    runtime_section = pyproject.split("[project]", 1)[1].split(
        "[project.scripts]", 1
    )[0]
    for sibling in _SIBLING_RUNTIME_NAMES:
        if sibling in runtime_section:
            raise RuntimeError(
                f"unexpected sibling runtime dependency in Issue #50: {sibling}"
            )
    if "paper_data_suite.modules" in pyproject:
        raise RuntimeError("#52 module-operations provider is registered early")

    docs = _read(root, "docs/task-oriented-teacher-menu.md")
    for marker in (
        "Eight teacher tasks",
        "Advanced Portia tools",
        "Technical Details / Provenance",
        "zero-write navigation",
        "Issue #49",
        "Issue #51",
        "Issue #52",
        "Issue #53",
        "family-specific correction",
        "No behavior/risk/urgency/priority scoring",
    ):
        if marker not in docs:
            raise RuntimeError(f"Issue #50 documentation is missing: {marker}")

    print("Portia Issue #50 source teacher-menu validation passed")


def _validate_distribution(root: Path) -> None:
    _validate_source(root)
    _require_files(root, _REQUIRED_DISTRIBUTION)
    print("Portia Issue #50 distribution teacher-menu validation passed")


def _validate_repository(root: Path) -> None:
    _validate_distribution(root)
    repository = _read(root, "scripts/validate_repository.py")
    for marker in (
        "scripts/validate_teacher_menu.py",
        "scripts/check_issue50_package.py",
        "scripts/smoke_test_issue50_teacher_menu_wheel.py",
        "Portia Issue #50 repository qualification passed",
    ):
        if marker not in repository:
            raise RuntimeError(
                f"repository qualification is missing Issue #50 marker: {marker}"
            )

    ci = _read(root, ".github/workflows/ci.yml")
    if "ubuntu-latest" not in ci or "windows-latest" not in ci:
        raise RuntimeError("durable CI no longer covers Windows and Ubuntu")
    if 'core: "0.6.3"' not in ci:
        raise RuntimeError("durable CI no longer authenticates Core 0.6.3")

    print("Portia Issue #50 repository teacher-menu validation passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("source", "distribution", "repository"),
        default="source",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.stage == "source":
            _validate_source(root)
        elif args.stage == "distribution":
            _validate_distribution(root)
        else:
            _validate_repository(root)
    except (OSError, RuntimeError, SyntaxError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
