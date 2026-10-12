"""Run Issue #56 installed Capture Review runtime acceptance."""

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

    if "CaptureReviewV1" not in init_text:
        raise RuntimeError(
            "candidate wheel is stale: CaptureReviewV1 is not exported"
        )
    if "class CaptureReviewV1" not in records_text:
        raise RuntimeError(
            "candidate wheel is stale: CaptureReviewV1 is not defined"
        )

    entries = coverage.get("contracts")
    if not isinstance(entries, list):
        raise RuntimeError("candidate wheel runtime coverage is malformed")

    review = next(
        (
            item
            for item in entries
            if isinstance(item, dict)
            and item.get("contract") == "capture_review"
            and item.get("version") == "1"
        ),
        None,
    )
    if not isinstance(review, dict) or (
        review.get("disposition"),
        review.get("modelled"),
    ) != ("current_v0_3", True):
        raise RuntimeError(
            "candidate wheel is stale: capture_review@1 is not promoted"
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

    code = r"""
from portia.models import (
    MODEL_REGISTRY,
    CaptureReviewV1,
    parse_portia_record,
    runtime_coverage,
)

agent = {"type": "system_process", "process_id": "issue56_smoke"}
review = {
    "schema_version": "1",
    "record_type": "capture_review",
    "module_id": "portia",
    "class_id": "class_synthetic",
    "work_id": "cbat_synthetic_01",
    "page_target_id": "ptgt_synthetic_01",
    "page_record_id": "prec_synthetic_01",
    "review_id": "crev_synthetic_01",
    "review_sequence": 1,
    "proposal_ref": {
        "contract_version": "1",
        "proposal_id": "cprp_synthetic_01",
    },
    "interpretation_ref": {
        "contract_version": "1",
        "interpretation_id": "pint_synthetic_01",
        "generation": 1,
    },
    "entry_key": "entry",
    "reviewer": {
        "kind": "local_operator",
        "display_label": "Synthetic Reviewer",
    },
    "disposition": "accepted",
    "field_reviews": [],
    "reason_codes": [],
    "reviewed_at": "2026-10-12T12:00:00-04:00",
    "created_at": "2026-10-12T12:00:00-04:00",
    "created_by": agent,
}

parsed = parse_portia_record("capture_review", "1", review)
assert isinstance(parsed, CaptureReviewV1)
assert parsed.to_dict() == review
assert parsed.logical_id == "crev_synthetic_01"
assert parsed.work_id == "cbat_synthetic_01"
assert MODEL_REGISTRY[("capture_review", "1")] is CaptureReviewV1

coverage = {
    (entry.contract, entry.version): (entry.disposition, entry.modelled)
    for entry in runtime_coverage()
}
assert coverage[("capture_review", "1")] == ("current_v0_3", True)

print("installed Capture Review runtime OK")
"""

    with tempfile.TemporaryDirectory(
        prefix="portia-issue56-capture-review-"
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
        if "installed Capture Review runtime OK" not in result.stdout:
            raise RuntimeError(
                "installed Capture Review runtime smoke did not complete"
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
        "Portia Issue #56 Slice 8 installed "
        "Capture Review runtime acceptance passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
