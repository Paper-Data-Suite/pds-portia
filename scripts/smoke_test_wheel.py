"""Install Core and Portia wheels in isolation and smoke the Issue #37 baseline."""

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


def _console_path(python: Path) -> Path:
    code = "import json,sysconfig; print(json.dumps(sysconfig.get_path('scripts')))"
    result = subprocess.run(
        [str(python), "-c", code],
        text=True,
        capture_output=True,
        check=True,
    )
    scripts = Path(json.loads(result.stdout))
    return scripts / ("portia.exe" if os.name == "nt" else "portia")


def _model_smoke(python: Path, *, cwd: Path, env: dict[str, str]) -> None:
    code = r'''
import json
from portia.models import EventV2, parse_portia_record, portia_record_to_dict
from portia.validation import GraphValidationOptions, validate_record_graph

wire = {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_smoke",
    "work_id": "evt_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-25T12:00:00-04:00",
    "created_by": {"type": "system_process", "process_id": "wheel_smoke"},
    "updated_at": "2026-08-25T12:00:00-04:00",
    "updated_by": {"type": "system_process", "process_id": "wheel_smoke"},
}
record = parse_portia_record("event", "2", wire)
assert isinstance(record, EventV2)
assert portia_record_to_dict(record) == wire
assert validate_record_graph(
    [record], options=GraphValidationOptions(require_internal_resolution=True)
) == ()
try:
    record._data["status"] = "closed"
except TypeError:
    pass
else:
    raise AssertionError("runtime record payload is not deeply immutable")
print(json.dumps({"contract": record.contract, "version": record.contract_version}))
'''
    result = _run([str(python), "-c", code], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if payload != {"contract": "event", "version": "2"}:
        raise RuntimeError(f"unexpected runtime-model smoke result: {payload!r}")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="portia-wheel-smoke-") as temporary:
        root = Path(temporary)
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

        package_result = _run(
            [
                str(python),
                "-c",
                (
                    "import json,portia; "
                    "print(json.dumps({'path': portia.__path__[0], 'version': portia.__version__}))"
                ),
            ],
            cwd=work,
            env=env,
        )
        package_info = json.loads(package_result.stdout)
        installed_path = Path(package_info["path"]).resolve()
        if repository.resolve() in installed_path.parents:
            raise RuntimeError(f"smoke import resolved into source checkout: {installed_path}")
        if package_info["version"] != "0.2.0":
            raise RuntimeError(f"unexpected installed Portia version: {package_info['version']}")
        if not (installed_path / "py.typed").is_file():
            raise RuntimeError("installed Portia wheel is missing py.typed")
        if not (installed_path / "_runtime_contract_bundle.json").is_file():
            raise RuntimeError("installed Portia wheel is missing the runtime contract bundle")
        if (installed_path / "schemas").exists():
            raise RuntimeError("installed Portia wheel unexpectedly contains repository schemas")

        _model_smoke(python, cwd=work, env=env)

        before = sorted(path.relative_to(work).as_posix() for path in work.rglob("*"))
        console = _console_path(python)
        _run([str(console), "--help"], cwd=work, env=env)
        version = _run([str(console), "--version"], cwd=work, env=env)
        if "Portia 0.2.0" not in version.stdout:
            raise RuntimeError(f"unexpected --version output: {version.stdout!r}")
        status = _run([str(console), "status"], cwd=work, env=env)
        if "Core requirement: pds-core>=0.6,<0.7" not in status.stdout:
            raise RuntimeError("status output is missing the bounded Core requirement")
        if "Teacher data access: none" not in status.stdout:
            raise RuntimeError("status output does not preserve the non-mutating bootstrap boundary")
        menu = _run([str(console), "menu"], cwd=work, env=env)
        if "bootstrap only" not in menu.stdout:
            raise RuntimeError("menu output does not identify the bootstrap-only state")
        _run([str(python), "-m", "portia", "--version"], cwd=work, env=env)
        after = sorted(path.relative_to(work).as_posix() for path in work.rglob("*"))
        if after != before:
            raise RuntimeError(
                "Portia bootstrap CLI mutated its working directory during smoke test"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
