"""Run isolated installed-wheel acceptance for Issue #52 module operations."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

CORE_064_FILENAME = "pds_core-0.6.4-py3-none-any.whl"
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"


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


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _console_path(python: Path) -> Path:
    code = "import json,sysconfig; print(json.dumps(sysconfig.get_path('scripts')))"
    completed = subprocess.run(
        [str(python), "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    scripts = Path(json.loads(completed.stdout))
    return scripts / ("portia.exe" if os.name == "nt" else "portia")


def _authenticate_core(repository: Path, core_wheel: Path) -> None:
    if core_wheel.name != CORE_064_FILENAME:
        raise RuntimeError(
            "Issue #52 installed-wheel smoke requires the released Core 0.6.4 wheel"
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

    code = r'''
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.module_operations import (
    MODULE_OPERATIONS_ENTRY_POINT_GROUP,
    ModuleOperationsRequest,
    invoke_module_attention,
    invoke_module_operations,
    invoke_module_readiness,
    validate_module_operations_profile,
)
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository


def snapshot(root):
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


dist = metadata.distribution("pds-portia")
operations = [
    ep
    for ep in dist.entry_points
    if ep.group == MODULE_OPERATIONS_ENTRY_POINT_GROUP
]
assert len(operations) == 1
assert operations[0].name == "portia"
assert operations[0].value == "portia.pds_operations:get_module_operations_profile"
console = [
    ep
    for ep in dist.entry_points
    if ep.group == "console_scripts" and ep.name == "portia"
]
assert len(console) == 1
assert console[0].value == "portia.cli:main"

trap = Path("implicit-workspace-must-not-exist").resolve()
os.environ["PDS_WORKSPACE_ROOT"] = str(trap)
profile_factory = operations[0].load()
profile = validate_module_operations_profile(profile_factory())
assert profile.module_id == "portia"
assert profile.supported_core_operations_contract_versions == frozenset({"1"})
assert profile.readiness_provider is not None
assert profile.attention_provider is not None

missing_request = ModuleOperationsRequest()
missing_ready = invoke_module_readiness(profile, missing_request)
missing_attention = invoke_module_attention(profile, missing_request)
assert missing_ready.code == "module_operations.evaluation_unavailable"
assert missing_ready.report is not None
assert missing_ready.report.ready is None
assert missing_ready.report.notices[0].code == "portia_readiness_unavailable"
assert missing_attention.code == "module_operations.evaluation_unavailable"
assert missing_attention.report is not None
assert missing_attention.report.summaries == ()
assert missing_attention.report.notices[0].code == "portia_attention_unavailable"
assert not trap.exists(), "missing-context invocation resolved or created implicit workspace"

with TemporaryDirectory(prefix="portia-issue52-installed-") as temp:
    workspace = Path(temp)
    ensure_workspace_root(workspace)
    write_class_roster(
        workspace,
        create_roster(
            "class_smoke",
            [
                {
                    "student_id": "student_private",
                    "last_name": "Private",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    write_class_metadata_for_class(
        workspace,
        create_class_metadata(
            "class_smoke",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )

    work = ExactPortiaWorkRef(
        class_id="class_smoke",
        work_id="evt_issue52",
        work_kind="event",
        contract_version="2",
    )
    agent = {"type": "system_process", "process_id": "issue52_installed_smoke"}
    operator = {"type": "local_operator", "display_label": "Synthetic Teacher"}
    reviewer = {"kind": "local_operator", "display_label": "Synthetic Teacher"}
    timestamp = "2026-09-30T18:00:00-04:00"
    repository = PortiaRepository(workspace)
    repository.create_work(
        work,
        parse_portia_record(
            "event",
            "2",
            {
                "schema_version": "2",
                "record_type": "portia_work",
                "work_kind": "event",
                "module_id": "portia",
                "class_id": "class_smoke",
                "work_id": "evt_issue52",
                "school_year": "2026-2027",
                "status": "active",
                "occurrence": {"precision": "exact", "started_at": timestamp},
                "summary": "Private synthetic event narrative.",
                "creation_source": {"type": "digital_entry"},
                "created_at": timestamp,
                "created_by": agent,
                "updated_at": timestamp,
                "updated_by": agent,
            },
        ),
    )
    repository.create_work_record(
        work,
        parse_portia_record(
            "review",
            "1",
            {
                "schema_version": "1",
                "record_type": "review",
                "module_id": "portia",
                "class_id": "class_smoke",
                "work_id": "evt_issue52",
                "review_id": "rvw_issue52",
                "status": "active",
                "review_state": "open",
                "trigger": {"kind": "routine_review"},
                "question": {
                    "kind": "evidence_review",
                    "text": "Private synthetic review narrative.",
                },
                "target": {"kind": "event"},
                "reviewer": reviewer,
                "evidence_considered": [],
                "creation_source": {"type": "digital_entry"},
                "created_at": timestamp,
                "created_by": operator,
                "updated_at": timestamp,
                "updated_by": operator,
            },
        ),
    )

    before = snapshot(workspace)
    request = ModuleOperationsRequest(
        workspace_root=workspace,
        active_school_year="2026-2027",
        class_id="class_smoke",
    )
    readiness, attention = invoke_module_operations(profile, request)
    assert readiness.code == "module_operations.evaluated"
    assert readiness.report is not None
    assert readiness.report.ready is True
    assert attention.code == "module_operations.evaluated"
    assert attention.report is not None
    assert attention.report.summaries

    summaries = {summary.code: summary for summary in attention.report.summaries}
    review = summaries["portia_review_incomplete"]
    assert review.label == "Reviews incomplete"
    assert review.count == 1
    assert review.class_id == "class_smoke"
    assert review.work_ref is not None
    assert review.work_ref.module_id == "portia"
    assert review.work_ref.class_id == "class_smoke"
    assert review.work_ref.work_id == "evt_issue52"
    assert review.action is not None
    assert review.action.module_id == "portia"
    assert review.action.action_id == "open_add_information"

    missing_class = invoke_module_readiness(
        profile,
        ModuleOperationsRequest(
            workspace_root=workspace,
            class_id="class_missing",
        ),
    )
    assert missing_class.code == "module_operations.evaluated"
    assert missing_class.report is not None
    assert missing_class.report.ready is False
    assert missing_class.report.notices[0].code == "portia_class_not_ready"

    after = snapshot(workspace)
    assert before == after, "Issue #52 providers mutated workspace state"

    shared = json.dumps(
        {
            "readiness": asdict(readiness.report),
            "attention": asdict(attention.report),
        },
        sort_keys=True,
        default=str,
    )
    for prohibited in (
        "student_private",
        "Private Synthetic",
        "Private synthetic event narrative.",
        "Private synthetic review narrative.",
        str(workspace),
        "rvw_issue52",
    ):
        assert prohibited not in shared

requirements = metadata.requires("pds-portia") or []
runtime_requirements = [
    value.lower() for value in requirements if "extra ==" not in value.lower()
]
assert any(
    "pds-core" in value and ">=0.6.3" in value and "<0.7" in value
    for value in runtime_requirements
)
assert not any(
    sibling in requirement
    for sibling in ("concord", "meridian", "quillan", "scoreform", "vitrine")
    for requirement in runtime_requirements
)

print(
    json.dumps(
        {
            "entry_point_exact": True,
            "console_entry_point_preserved": True,
            "metadata_safe_missing_context": True,
            "missing_context_unavailable": True,
            "valid_class_ready": True,
            "missing_class_not_ready": True,
            "attention_projected": True,
            "owner_action_projected": True,
            "readiness_and_attention_coexist": True,
            "privacy_bounded": True,
            "provider_zero_write": True,
            "no_sibling_runtime_dependency": True,
        },
        sort_keys=True,
    )
)
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue52-wheel-smoke-") as temp:
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
            "pds_operations.py",
            "attention_provider.py",
            "readiness_provider.py",
            "attention/actions.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #52 file: {relative}"
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
        if core_version != "0.6.4":
            raise RuntimeError(
                f"installed Core version is not released 0.6.4: {core_version}"
            )

        console = _console_path(python)
        status = _run([str(console), "status"], cwd=work, env=env)
        if "Core requirement: pds-core>=0.6.3,<0.7" not in status.stdout:
            raise RuntimeError("installed portia status lost the Core compatibility floor")
        if "Installed Core: 0.6.4" not in status.stdout:
            raise RuntimeError("installed portia status did not report Core 0.6.4")

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("installed Issue #52 smoke produced no result")
        payload = json.loads(lines[-1])
        if not all(value is True for value in payload.values()):
            raise RuntimeError(f"installed Issue #52 smoke failed: {payload!r}")


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
    print("Portia installed-wheel Issue #52 module-operations smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
