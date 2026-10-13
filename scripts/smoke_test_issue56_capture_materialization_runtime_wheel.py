'''Run Issue #56 installed Capture Materialization runtime acceptance.'''

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
import zipfile
from pathlib import Path

CORE_NAME = "pds_core-0.6.5-py3-none-any.whl"
PORTIA_NAME = "pds_portia-0.2.0-py3-none-any.whl"


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _verify_candidate_payload(portia_wheel: Path) -> None:
    with zipfile.ZipFile(portia_wheel) as archive:
        init_text = archive.read("portia/models/__init__.py").decode("utf-8")
        records_text = archive.read("portia/models/records.py").decode("utf-8")
        coverage = json.loads(
            archive.read("portia/runtime-coverage.json").decode("utf-8")
        )

    if "CaptureMaterializationV1" not in init_text:
        raise RuntimeError(
            "candidate wheel is stale: CaptureMaterializationV1 is not exported"
        )
    if "class CaptureMaterializationV1" not in records_text:
        raise RuntimeError(
            "candidate wheel is stale: CaptureMaterializationV1 is not defined"
        )

    entries = coverage.get("contracts")
    if not isinstance(entries, list):
        raise RuntimeError("candidate wheel runtime coverage is malformed")
    entry = next(
        (
            item
            for item in entries
            if isinstance(item, dict)
            and item.get("contract") == "capture_materialization"
            and item.get("version") == "1"
        ),
        None,
    )
    if not isinstance(entry, dict) or (
        entry.get("disposition"),
        entry.get("modelled"),
    ) != ("current_v0_3", True):
        raise RuntimeError(
            "candidate wheel is stale: capture_materialization@1 is not promoted"
        )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    if core_wheel.name != CORE_NAME:
        raise RuntimeError("expected authenticated Core 0.6.5 wheel")
    if portia_wheel.name != PORTIA_NAME:
        raise RuntimeError(f"expected candidate wheel {PORTIA_NAME}")

    _verify_candidate_payload(portia_wheel)

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

    code = r'''
from portia.models import (
    MODEL_REGISTRY,
    CaptureMaterializationV1,
    parse_portia_record,
    runtime_coverage,
)

agent = {"type": "system_process", "process_id": "issue56_smoke"}
receipt = {
    "schema_version": "1",
    "record_type": "capture_materialization",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "work_id": "cbat_synthetic_01",
    "page_target_id": "ptgt_synthetic_01",
    "page_record_id": "prec_synthetic_01",
    "proposal_ref": {
        "contract_version": "1",
        "proposal_id": "cprp_synthetic_01",
    },
    "review_ref": {
        "contract_version": "1",
        "review_id": "crev_synthetic_01",
        "review_sequence": 1,
    },
    "operation_journal_ref": {
        "operation_id": "op_synthetic_01",
        "journal_revision": 4,
        "contract_version": "1",
    },
    "canonical_results": [
        {
            "result_relation": "produced",
            "target": {
                "kind": "work",
                "work_ref": {
                    "module_id": "portia",
                    "class_id": "class_synthetic",
                    "work_id": "evt_synthetic_01",
                    "work_kind": "event",
                    "contract_version": "2",
                },
            },
        }
    ],
    "materialized_at": "2026-10-12T12:00:00-04:00",
    "recorded_at": "2026-10-12T12:00:00-04:00",
    "recorded_by": agent,
}

parsed = parse_portia_record("capture_materialization", "1", receipt)
assert isinstance(parsed, CaptureMaterializationV1)
assert parsed.to_dict() == receipt
assert parsed.logical_id is None
assert parsed.work_id == "cbat_synthetic_01"
assert MODEL_REGISTRY[("capture_materialization", "1")] is CaptureMaterializationV1
coverage = {
    (entry.contract, entry.version): (entry.disposition, entry.modelled)
    for entry in runtime_coverage()
}
assert coverage[("capture_materialization", "1")] == ("current_v0_3", True)
print("installed Capture Materialization runtime OK")
'''

    with tempfile.TemporaryDirectory(
        prefix="portia-issue56-capture-materialization-"
    ) as temp:
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
        if "installed Capture Materialization runtime OK" not in result.stdout:
            raise RuntimeError(
                "installed Capture Materialization runtime smoke did not complete"
            )


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
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print(
        "Portia Issue #56 Slice 9 installed "
        "Capture Materialization runtime acceptance passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
