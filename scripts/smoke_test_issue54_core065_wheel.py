"""Run Issue #54 isolated installed-wheel compatibility against Core 0.6.5."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from typing import Final

CORE_065_FILENAME: Final[str] = "pds_core-0.6.5-py3-none-any.whl"
CORE_065_SHA256: Final[str] = (
    "9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18"
)
EXPECTED_CORE_VERSION: Final[str] = "0.6.5"
EXPECTED_PORTIA_VERSION: Final[str] = "0.2.0"


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
    if core_wheel.name != CORE_065_FILENAME:
        raise RuntimeError(
            "Issue #54 Core compatibility smoke requires the released Core 0.6.5 wheel"
        )
    completed = _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    if "Verified official pds-core 0.6.5 wheel" not in completed.stdout:
        raise RuntimeError("Core 0.6.5 wheel verification did not complete")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    _authenticate_core(repository, core_wheel)

    if portia_wheel.name != "pds_portia-0.2.0-py3-none-any.whl":
        raise RuntimeError("Issue #54 requires the exact Portia 0.2.0 wheel filename")

    code = r'''
import json
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.class_metadata import create_class_metadata, write_class_metadata_for_class
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


def normalized(name):
    return name.lower().replace("_", "-")


def snapshot(root):
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


assert metadata.version("pds-core") == "0.6.5"
assert metadata.version("pds-portia") == "0.2.0"

installed_pds = {
    normalized(dist.metadata["Name"])
    for dist in metadata.distributions()
    if dist.metadata.get("Name")
    and normalized(dist.metadata["Name"]).startswith("pds-")
}
assert installed_pds == {"pds-core", "pds-portia"}, installed_pds

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

profile_factory = operations[0].load()
profile = validate_module_operations_profile(profile_factory())
assert profile.module_id == "portia"
assert profile.supported_core_operations_contract_versions == frozenset({"1"})
assert profile.readiness_provider is not None
assert profile.attention_provider is not None

trap = Path("issue54-implicit-workspace-must-not-exist").resolve()
os.environ["PDS_WORKSPACE_ROOT"] = str(trap)
missing = ModuleOperationsRequest()
missing_readiness = invoke_module_readiness(profile, missing)
missing_attention = invoke_module_attention(profile, missing)
assert missing_readiness.code == "module_operations.evaluation_unavailable"
assert missing_attention.code == "module_operations.evaluation_unavailable"
assert not trap.exists()

with TemporaryDirectory(prefix="portia-issue54-core065-") as temp:
    workspace = Path(temp)
    ensure_workspace_root(workspace)
    write_class_roster(
        workspace,
        create_roster(
            "class_issue54_core065",
            [
                {
                    "student_id": "student_synthetic",
                    "last_name": "Synthetic",
                    "first_name": "Student",
                    "period": "1",
                }
            ],
        ),
    )
    write_class_metadata_for_class(
        workspace,
        create_class_metadata(
            "class_issue54_core065",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )
    before = snapshot(workspace)
    request = ModuleOperationsRequest(
        workspace_root=workspace,
        active_school_year="2026-2027",
        class_id="class_issue54_core065",
    )
    readiness, attention = invoke_module_operations(profile, request)
    assert readiness.code == "module_operations.evaluated"
    assert readiness.report is not None
    assert attention.code == "module_operations.evaluated"
    assert attention.report is not None
    after = snapshot(workspace)
    assert before == after, "Core 0.6.5 module-operations invocation mutated workspace"

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
            "core_065_exact": True,
            "portia_020_exact": True,
            "isolated_pds_set_exact": True,
            "module_operations_entry_point_exact": True,
            "console_entry_point_exact": True,
            "missing_context_fail_soft": True,
            "missing_context_zero_create": True,
            "class_context_evaluated": True,
            "provider_zero_write": True,
            "runtime_requirement_still_range_based": True,
            "no_sibling_runtime_dependency": True,
        },
        sort_keys=True,
    )
)
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue54-core065-wheel-") as temp:
        root = Path(temp)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PIP_NO_INDEX"] = "1"

        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                str(core_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-index",
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
                f"Issue #54 import resolved into source checkout: {installed}"
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
        if core_version != EXPECTED_CORE_VERSION:
            raise RuntimeError(
                f"installed Core version is not {EXPECTED_CORE_VERSION}: {core_version}"
            )

        console = _console_path(python)
        status = _run([str(console), "status"], cwd=work, env=env)
        if "Core requirement: pds-core>=0.6.3,<0.7" not in status.stdout:
            raise RuntimeError("Portia status lost the Core compatibility range")
        if "Installed Core: 0.6.5" not in status.stdout:
            raise RuntimeError("Portia status did not report installed Core 0.6.5")

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("Issue #54 Core 0.6.5 smoke produced no result")
        payload = json.loads(lines[-1])
        if not all(value is True for value in payload.values()):
            raise RuntimeError(f"Issue #54 Core 0.6.5 smoke failed: {payload!r}")


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
    print("Portia Issue #54 Core 0.6.5 installed compatibility passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
