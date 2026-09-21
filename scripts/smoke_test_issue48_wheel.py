"""Smoke Issue #48 student views from an installed Portia wheel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


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
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _authenticate_core(repository: Path, core_wheel: Path) -> None:
    if core_wheel.name != "pds_core-0.6.3-py3-none-any.whl":
        raise RuntimeError(
            "Issue #48 installed-wheel smoke requires the Core 0.6.3 wheel"
        )
    _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    _authenticate_core(repository, core_wheel)
    fixture_root = (
        repository
        / "tests"
        / "fixtures"
        / "issue_22"
        / "positive"
        / "p22_04_correction_supersession_disagreement"
        / "records"
    )
    if not fixture_root.is_dir():
        raise RuntimeError(f"missing Issue #48 history fixture: {fixture_root}")

    code = r"""
import hashlib
import json
import sys
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef, RosterStudentRef
from portia.storage import PortiaRepository
from portia.views import (
    StudentTimelineFilter,
    StudentTimelineQuery,
    StudentTimelineService,
    StudentViewScope,
)

FIXTURE = Path(sys.argv[1])
WORKSPACE = Path("synthetic-issue48-workspace")
CLASS_ID = "eng10_p2_2026"
STUDENT_ID = "stu_p22_001"
EVENT_ID = "evt_p22_correction_001"


def load_record(name):
    value = json.loads((FIXTURE / name).read_text(encoding="utf-8"))
    version = str(value["schema_version"])
    contract = (
        str(value["work_kind"])
        if value["record_type"] == "portia_work"
        else str(value["record_type"])
    )
    return parse_portia_record(contract, version, value)


def snapshot(root):
    values = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        values[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


write_class_roster(
    WORKSPACE,
    create_roster(
        CLASS_ID,
        [
            {
                "student_id": STUDENT_ID,
                "last_name": "Synthetic",
                "first_name": "Focal",
                "period": "2",
            },
            {
                "student_id": "stu_p22_other",
                "last_name": "Synthetic",
                "first_name": "Other",
                "period": "2",
            },
        ],
    ),
)
repository = PortiaRepository(WORKSPACE)
event_work = ExactPortiaWorkRef(
    class_id=CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
repository.create_work(event_work, load_record("event.json"))
for name in (
    "participant.json",
    "account-predecessor.json",
    "account-successor.json",
    "disagreement.json",
    "transition-predecessor-active.json",
    "transition-predecessor-superseded.json",
    "transition-successor-active.json",
):
    repository.create_work_record(event_work, load_record(name))

other = parse_portia_record(
    "event_participant",
    "3",
    {
        "schema_version": "3",
        "record_type": "event_participant",
        "module_id": "portia",
        "class_id": CLASS_ID,
        "work_id": EVENT_ID,
        "participant_id": "ep_smoke_other",
        "status": "active",
        "subject": {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": CLASS_ID,
                "student_id": "stu_p22_other",
            },
            "display_snapshot": {"display_name": "Synthetic Other"},
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-09-20T10:00:00-04:00",
        "created_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
        "updated_at": "2026-09-20T10:00:00-04:00",
        "updated_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
    },
)
repository.create_work_record(event_work, other)

support_work = ExactPortiaWorkRef(
    class_id=CLASS_ID,
    work_id="sup_smoke_student_view",
    work_kind="support_process",
    contract_version="1",
)
support_root = parse_portia_record(
    "support_process",
    "1",
    {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": CLASS_ID,
        "work_id": support_work.work_id,
        "school_year": "2026-2027",
        "status": "active",
        "workflow_state": "active",
        "summary": "Synthetic support process for installed-wheel smoke.",
        "initiation": {
            "kind": "teacher_identified_need",
            "detail": "Synthetic bounded need.",
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-09-20T11:00:00-04:00",
        "created_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
        "updated_at": "2026-09-20T11:00:00-04:00",
        "updated_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
    },
)
support_participant = parse_portia_record(
    "support_process_participant",
    "1",
    {
        "schema_version": "1",
        "record_type": "support_process_participant",
        "module_id": "portia",
        "class_id": CLASS_ID,
        "work_id": support_work.work_id,
        "participant_id": "spp_smoke_student_view",
        "status": "active",
        "person": {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": CLASS_ID,
                "student_id": STUDENT_ID,
            },
            "display_snapshot": {"display_name": "Synthetic Focal"},
        },
        "contexts": [{"kind": "supported_person"}],
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-09-20T11:01:00-04:00",
        "created_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
        "updated_at": "2026-09-20T11:01:00-04:00",
        "updated_by": {
            "type": "local_operator",
            "display_label": "Synthetic Teacher",
        },
    },
)
repository.create_work(support_work, support_root)
repository.create_work_record(support_work, support_participant)

student = RosterStudentRef(class_id=CLASS_ID, student_id=STUDENT_ID)
allowed = (event_work, support_work)
current_query = StudentTimelineQuery(
    StudentViewScope(
        focal_students=(student,),
        allowed_works=allowed,
    )
)
history_query = StudentTimelineQuery(
    StudentViewScope(
        focal_students=(student,),
        allowed_works=allowed,
        history_allowed=True,
    ),
    mode="history",
)
service = StudentTimelineService(WORKSPACE, repository=repository)
before = snapshot(WORKSPACE)
current = service.generate(current_query)
history = service.generate(history_query)
account_filter = StudentTimelineFilter(
    record_families=("account",),
    sort_direction="ascending",
)
filtered_a = service.generate(history_query, filters=account_filter)
filtered_b = service.generate(history_query, filters=account_filter)
after = snapshot(WORKSPACE)

current_kinds = sorted(work.work_ref.work_kind for work in current.works)
history_ids = {
    entry.navigation.record_id
    for entry in history.entries
    if entry.semantic_type == "account"
}
manual_review_present = any(
    entry.semantic_type == "account"
    and entry.disposition == "requires_manual_review"
    for entry in current.entries
)
filtered_keys_a = [
    (
        entry.navigation.scope,
        entry.navigation.record_kind,
        entry.navigation.record_id,
        entry.history_kind,
    )
    for entry in filtered_a.entries
]
filtered_keys_b = [
    (
        entry.navigation.scope,
        entry.navigation.record_kind,
        entry.navigation.record_id,
        entry.history_kind,
    )
    for entry in filtered_b.entries
]
unrelated_hidden = all(
    entry.navigation.record_id != "ep_smoke_other"
    for entry in (*current.entries, *history.entries)
)

print(
    json.dumps(
        {
            "current_work_kinds": current_kinds,
            "history_has_predecessor": "acct_p22_original_red" in history_ids,
            "history_has_successor": "acct_p22_corrected_blue" in history_ids,
            "manual_review_present": manual_review_present,
            "deterministic_filtering": filtered_keys_a == filtered_keys_b,
            "workspace_unchanged": before == after,
            "unrelated_hidden": unrelated_hidden,
        }
    )
)
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue48-wheel-smoke-") as temp:
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

        package = _run(
            [
                str(python),
                "-c",
                "import json,portia; "
                "print(json.dumps({'path': portia.__path__[0]}))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(
                "smoke import resolved into source checkout: "
                f"{installed}"
            )

        required_installed = (
            "views/chronology.py",
            "views/currentness.py",
            "views/discovery.py",
            "views/filters.py",
            "views/history.py",
            "views/models.py",
            "views/policy.py",
            "views/projection.py",
            "views/student.py",
        )
        for relative in required_installed:
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #48 file: {relative}"
                )

        result = _run(
            [str(python), "-c", code, str(fixture_root.resolve())],
            cwd=work,
            env=env,
        )
        payload = json.loads(result.stdout)
        expected = {
            "current_work_kinds": ["event", "support_process"],
            "history_has_predecessor": True,
            "history_has_successor": True,
            "manual_review_present": True,
            "deterministic_filtering": True,
            "workspace_unchanged": True,
            "unrelated_hidden": True,
        }
        if payload != expected:
            raise RuntimeError(
                "unexpected Issue #48 student-view result: "
                f"{payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print("Portia installed-wheel Issue #48 student-view smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
