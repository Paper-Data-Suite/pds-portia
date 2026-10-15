"""Run Issue #56 installed Import Source Record runtime acceptance."""

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
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _verify_candidate_payload(portia_wheel: Path) -> None:
    with zipfile.ZipFile(portia_wheel) as archive:
        init_text = archive.read("portia/models/__init__.py").decode("utf-8")
        records_text = archive.read("portia/models/records.py").decode("utf-8")
        coverage = json.loads(
            archive.read("portia/runtime-coverage.json").decode("utf-8")
        )

    if "ImportSourceRecordV1" not in init_text:
        raise RuntimeError(
            "candidate wheel is stale: ImportSourceRecordV1 is not exported"
        )
    if "class ImportSourceRecordV1" not in records_text:
        raise RuntimeError(
            "candidate wheel is stale: ImportSourceRecordV1 is not defined"
        )

    entries = coverage.get("contracts")
    if not isinstance(entries, list):
        raise RuntimeError("candidate wheel runtime coverage is malformed")
    item = next(
        (
            entry
            for entry in entries
            if isinstance(entry, dict)
            and entry.get("contract") == "import_source_record"
            and entry.get("version") == "1"
        ),
        None,
    )
    if not isinstance(item, dict) or (
        item.get("disposition"),
        item.get("modelled"),
    ) != ("current_v0_3", True):
        raise RuntimeError(
            "candidate wheel is stale: import_source_record@1 is not promoted"
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
    ImportSourceRecordV1,
    parse_portia_record,
    runtime_coverage,
)

record = {
    "schema_version": "1",
    "record_type": "import_source_record",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "import_batch_id": "ibat_synthetic_01",
    "source_record_id": "isrc_synthetic_01",
    "source_record_key_origin": "source_provided",
    "source_record_key": "SRC-0001",
    "source_record_digest": "a" * 64,
    "source_record_identity_digest": "b" * 64,
    "source_fields": [
        {"field_key": "student_external_id", "value": "S-1"},
        {"field_key": "optional_note", "value": None},
        {"field_key": "tags", "value": ["one", "two"]},
    ],
    "observed_at": "2026-10-12T12:00:00-04:00",
    "created_at": "2026-10-12T12:00:00-04:00",
    "created_by": {
        "type": "system_process",
        "process_id": "issue56_smoke",
    },
}
parsed = parse_portia_record("import_source_record", "1", record)
assert isinstance(parsed, ImportSourceRecordV1)
assert parsed.to_dict() == record
assert parsed.logical_id == "isrc_synthetic_01"
assert parsed.class_id == "class_synthetic"
assert parsed.work_id is None
assert MODEL_REGISTRY[("import_source_record", "1")] is ImportSourceRecordV1
coverage = {
    (entry.contract, entry.version): (entry.disposition, entry.modelled)
    for entry in runtime_coverage()
}
assert coverage[("import_source_record", "1")] == ("current_v0_3", True)
print("installed Import Source Record runtime OK")
'''

    with tempfile.TemporaryDirectory(
        prefix="portia-issue56-import-source-record-"
    ) as temp:
        temp_root = Path(temp)
        venv_root = temp_root / "venv"
        work = temp_root / "work"
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
        if "installed Import Source Record runtime OK" not in result.stdout:
            raise RuntimeError(
                "installed Import Source Record runtime smoke did not complete"
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
        "Portia Issue #56 Slice 11 installed Import Source Record runtime "
        "acceptance passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
