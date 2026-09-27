"""Run an isolated installed-wheel smoke for Issue #88 deliberate export."""

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
from importlib import metadata

from portia.models import MODEL_REGISTRY
from portia.storage.deliberate_export_recovery_actions import (
    finalize_deliberate_export,
    recover_deliberate_export_committed_revision,
    recover_deliberate_export_provenance,
)
from portia.storage.errors import PortiaPathError
from portia.storage.paths import validate_workspace_relative_path
from portia.views.policy import contract_rule

assert ("operation_journal", "4") in MODEL_REGISTRY
assert ("operation_lock", "3") in MODEL_REGISTRY
assert ("deliberate_export", "1") in MODEL_REGISTRY
assert contract_rule("operation_journal", "4").surface == "operational_excluded"
assert contract_rule("operation_lock", "3").surface == "operational_excluded"

for value in (
    recover_deliberate_export_provenance,
    recover_deliberate_export_committed_revision,
    finalize_deliberate_export,
):
    assert callable(value)

try:
    validate_workspace_relative_path("../portia/exports/pexp_escape/artifact.csv")
except PortiaPathError:
    traversal_rejected = True
else:
    traversal_rejected = False
assert traversal_rejected

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

print(json.dumps({
    "journal_v4": True,
    "lock_v3": True,
    "student_view_excluded": True,
    "recovery_apis": True,
    "path_traversal_rejected": True,
    "no_sibling_runtime_dependency": True,
}, sort_keys=True))
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue88-wheel-smoke-") as temp:
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
            [str(python), "-m", "pip", "install", "--no-deps", str(portia_wheel.resolve())],
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
            "storage/deliberate_export_operations.py",
            "storage/deliberate_export_persistence.py",
            "storage/deliberate_export_recovery.py",
            "storage/deliberate_export_recovery_actions.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #88 file: {relative}"
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
            raise RuntimeError(f"installed Core version is not 0.6.3: {core_version}")

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("installed Issue #88 smoke produced no result")
        data = json.loads(lines[-1])
        if not all(value is True for value in data.values()):
            raise RuntimeError(f"installed Issue #88 smoke failed: {data!r}")


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

    print("Portia installed-wheel Issue #88 deliberate-export smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
