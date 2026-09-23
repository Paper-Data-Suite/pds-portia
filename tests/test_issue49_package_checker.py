"""Focused tests for the Issue #49 distribution inventory checker."""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_issue49_package.py"

RUNTIME = {
    "portia/attention/__init__.py",
    "portia/attention/models.py",
    "portia/attention/taxonomy.py",
    "portia/attention/timing.py",
    "portia/attention/workflow_sources.py",
    "portia/attention/operational_sources.py",
    "portia/attention/derived_sources.py",
    "portia/attention/scope.py",
}
SDIST_EXTRA = {
    "docs/due-follow-up-and-attention-queries.md",
    "docs/validation/issue-49-attention-query-validation.md",
    "scripts/check_issue49_package.py",
    "scripts/smoke_test_issue49_wheel.py",
    "scripts/validate_attention_queries.py",
    "tests/test_attention_privacy.py",
    "tests/test_attention_acceptance_matrix.py",
}


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue49_package_checker_accepts_complete_wheel_and_sdist(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(RUNTIME):
            archive.writestr(name, "# synthetic\n")

    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in sorted(RUNTIME | SDIST_EXTRA):
            payload = b"# synthetic\n"
            info = tarfile.TarInfo(f"pds_portia-0.2.0/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    wheel_result = _run(wheel)
    sdist_result = _run(sdist)

    assert wheel_result.returncode == 0, wheel_result.stderr + wheel_result.stdout
    assert sdist_result.returncode == 0, sdist_result.stderr + sdist_result.stdout
    assert "Issue #49 package inventory validation passed" in wheel_result.stdout
    assert "Issue #49 package inventory validation passed" in sdist_result.stdout


def test_issue49_package_checker_rejects_missing_runtime_file(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    missing = "portia/attention/workflow_sources.py"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(RUNTIME - {missing}):
            archive.writestr(name, "# synthetic\n")

    result = _run(wheel)

    assert result.returncode == 1
    assert "missing Issue #49 runtime files" in result.stdout
    assert missing in result.stdout


def test_issue49_package_checker_rejects_missing_sdist_closeout_file(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    missing = "docs/due-follow-up-and-attention-queries.md"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in sorted((RUNTIME | SDIST_EXTRA) - {missing}):
            payload = b"# synthetic\n"
            info = tarfile.TarInfo(f"pds_portia-0.2.0/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    result = _run(sdist)

    assert result.returncode == 1
    assert "missing Issue #49 sdist files" in result.stdout
    assert missing in result.stdout
