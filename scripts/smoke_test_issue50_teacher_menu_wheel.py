"""Run an isolated installed-wheel smoke for the Issue #50 teacher menu."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    code = r"""
import json
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.cli import main, render_menu, render_status
from portia.menu import MenuSessionContext
from portia.menu.clock import MenuClock
from portia.menu.event import launch_record_event_menu
from portia.menu.identifiers import PortiaIdGenerator
import portia.menu.attention as attention_menu
import portia.menu.follow_up as follow_up_menu
import portia.menu.timeline as timeline_menu
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository

FIXED_NOW = datetime(2026, 9, 24, 20, 0, tzinfo=timezone.utc)


def snapshot(root: Path):
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def add_class(root: Path):
    ensure_workspace_root(root)
    write_class_roster(
        root,
        create_roster(
            "class_smoke",
            [
                {
                    "student_id": "student_smoke",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            "class_smoke",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )


def ids(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


with TemporaryDirectory(prefix="portia-issue50-menu-") as temp:
    workspace = Path(temp)
    add_class(workspace)
    os.environ["PDS_WORKSPACE_ROOT"] = str(workspace)

    menu_text = render_menu()
    assert "[planned]" not in menu_text
    for label in (
        "Record Event",
        "Add Information",
        "Record Response / Communication",
        "Manage Support",
        "Complete Follow-Up",
        "View Timeline",
        "Correct / Retract",
        "Attention Needed",
        "Advanced Portia tools",
    ):
        assert label in menu_text

    status = render_status()
    assert "Teacher data access: none" in status

    before_navigation = snapshot(workspace)
    for choice in tuple(str(value) for value in range(1, 10)):
        with patch("builtins.input", side_effect=(choice, "b", "q")):
            assert main([]) == 0
    assert snapshot(workspace) == before_navigation

    answers = (
        "1",
        "1",
        "Synthetic Teacher",
        "",
        "Installed-wheel synthetic classroom context.",
        "1",
        "1",
        "1",
        "3",
        "CREATE",
        "",
        "b",
    )
    with patch("builtins.input", side_effect=answers):
        launch_record_event_menu(
            MenuSessionContext(),
            clock=MenuClock(lambda: FIXED_NOW),
            ids=ids("smoke", "participant", "operation"),
        )

    work = ExactPortiaWorkRef(
        class_id="class_smoke",
        work_id="evt_smoke",
        work_kind="event",
        contract_version="2",
    )
    repository = PortiaRepository(workspace)
    event = repository.load_work(work).record
    participants = repository.list_event_participants(work)

    assert event.status == "draft"
    assert len(participants) == 1
    assert repository.list_accounts(work) == ()
    assert repository.list_observations(work) == ()
    assert repository.list_work_records(
        work, "determination", version="1"
    ) == ()
    assert repository.list_work_records(work, "response", version="1") == ()
    assert repository.list_work_records(work, "follow_up", version="1") == ()

    assert timeline_menu.StudentTimelineService.__module__.startswith("portia.views")
    assert attention_menu.AttentionQueryService.__module__.startswith(
        "portia.attention"
    )
    assert follow_up_menu.FollowUpScheduleQueryService.__module__.startswith(
        "portia.attention"
    )
    assert follow_up_menu.FollowUpWorkflowService.__module__.startswith(
        "portia.workflows"
    )

    requirements = metadata.requires("pds-portia") or []
    runtime_requirements = [
        value.lower()
        for value in requirements
        if "extra ==" not in value.lower()
    ]
    assert not any(
        sibling in requirement
        for sibling in ("concord", "meridian", "quillan", "scoreform", "vitrine")
        for requirement in runtime_requirements
    )

    print(
        json.dumps(
            {
                "all_surfaces_reachable": True,
                "navigation_zero_write": True,
                "event_created": True,
                "no_inferred_downstream_writes": True,
                "timeline_service": True,
                "attention_service": True,
                "follow_up_services": True,
                "no_sibling_runtime_dependency": True,
            },
            sort_keys=True,
        )
    )
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue50-wheel-smoke-") as temp:
        root = Path(temp)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(portia_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        installed_check = _run(
            [
                str(python),
                "-c",
                "import json,portia; print(json.dumps({'path': portia.__path__[0]}))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(installed_check.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(
                f"smoke import resolved into source checkout: {installed}"
            )

        for relative in (
            "menu/__init__.py",
            "menu/main.py",
            "menu/event.py",
            "menu/information.py",
            "menu/response_communication.py",
            "menu/support.py",
            "menu/follow_up.py",
            "menu/timeline.py",
            "menu/correction.py",
            "menu/attention.py",
            "menu/advanced.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #50 file: {relative}"
                )

        core_version = _run(
            [
                str(python),
                "-c",
                "from importlib import metadata; print(metadata.version('pds-core'))",
            ],
            cwd=work,
            env=env,
        ).stdout.strip()
        if core_version != "0.6.3":
            raise RuntimeError(
                f"installed Core version is not 0.6.3: {core_version}"
            )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("installed teacher-menu smoke produced no result")
        payload = json.loads(lines[-1])
        for key, value in payload.items():
            if value is not True:
                raise RuntimeError(
                    f"installed Issue #50 smoke failed {key}: {payload!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()

    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError, AssertionError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1

    print("Portia installed-wheel Issue #50 teacher-menu smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
