"""Run Issue #56 installed Page Target runtime acceptance."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

CORE_NAME = "pds_core-0.6.5-py3-none-any.whl"
PORTIA_NAME = "pds_portia-0.2.0-py3-none-any.whl"


def _run(
    command: list[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _python(root: Path) -> Path:
    return (
        root / "Scripts/python.exe"
        if os.name == "nt"
        else root / "bin/python"
    )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    if core_wheel.name != CORE_NAME:
        raise RuntimeError("expected authenticated Core 0.6.5 wheel")
    if portia_wheel.name != PORTIA_NAME:
        raise RuntimeError(f"expected candidate wheel {PORTIA_NAME}")

    verified = _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    if "Verified official pds-core 0.6.5 wheel" not in verified.stdout:
        raise RuntimeError("Core authentication did not complete")

    code = r"""
from portia.models import (
    MODEL_REGISTRY,
    PageTargetV1,
    PageTargetV2,
    PortiaLocalValidationError,
    parse_portia_record,
    runtime_coverage,
)

agent = {"type": "system_process", "process_id": "issue56_smoke"}
v1 = {
    "schema_version": "1",
    "record_type": "capture_page_target",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "work_id": "cbat_synthetic_01",
    "page_target_id": "ptgt_synthetic_v1",
    "page_index": 1,
    "page_purpose": "new_event_capture",
    "template_identity": {
        "template_id": "portia_event_intake",
        "template_version": "1",
        "layout_version": "layout_1",
        "capture_spec_version": "capture_1",
        "layout_fingerprint": "b" * 64,
        "page_role": "event_capture",
        "page_ordinal": 1
    },
    "capture_mode": "mixed_recognition",
    "entry_layout": {"mode": "single_entry", "entry_keys": ["entry"]},
    "status": "active",
    "created_at": "2026-10-11T12:00:00-04:00",
    "created_by": agent,
    "updated_at": "2026-10-11T12:00:00-04:00",
    "updated_by": agent
}
v2 = dict(v1)
v2.update({
    "schema_version": "2",
    "work_id": "cbat_synthetic_02",
    "page_target_id": "ptgt_synthetic_v2",
    "page_purpose": "classroom_observation_capture",
    "template_identity": {
        "template_id": "portia_classroom_observation",
        "template_version": "1",
        "layout_version": "layout_1",
        "capture_spec_version": "capture_1",
        "layout_fingerprint": "c" * 64,
        "page_role": "classroom_observation",
        "page_ordinal": 1
    },
    "entry_layout": {
        "mode": "multi_entry",
        "entry_keys": ["session_context", "observation_01"],
        "context_entry_key": "session_context"
    }
})

assert isinstance(parse_portia_record("page_target", "1", v1), PageTargetV1)
parsed = parse_portia_record("page_target", "2", v2)
assert isinstance(parsed, PageTargetV2)
assert parsed.to_dict() == v2
assert MODEL_REGISTRY[("page_target", "1")] is PageTargetV1
assert MODEL_REGISTRY[("page_target", "2")] is PageTargetV2

coverage = {
    (e.contract, e.version): (e.disposition, e.modelled)
    for e in runtime_coverage()
}
assert coverage[("page_target", "1")] == ("historical_read", True)
assert coverage[("page_target", "2")] == ("current_v0_3", True)

invalid = dict(v2)
invalid["entry_layout"] = dict(v2["entry_layout"])
invalid["entry_layout"]["context_entry_key"] = "missing_entry"
try:
    parse_portia_record("page_target", "2", invalid)
except PortiaLocalValidationError:
    pass
else:
    raise AssertionError("undeclared context_entry_key was accepted")

print("installed Page Target runtime OK")
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue56-") as temp:
        root = Path(temp)
        venv_root = root / "venv"
        work = root / "work"
        work.mkdir()
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
        python = _python(venv_root)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PIP_NO_INDEX"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        for wheel in (core_wheel, portia_wheel):
            _run(
                [
                    str(python),
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    str(wheel.resolve()),
                ],
                cwd=work,
                env=env,
            )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        result = _run([str(python), "-c", code], cwd=work, env=env)
        if "installed Page Target runtime OK" not in result.stdout:
            raise RuntimeError("installed runtime smoke did not complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        AssertionError,
    ) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print(
        "Portia Issue #56 Slice 3 installed Page Target runtime acceptance passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
