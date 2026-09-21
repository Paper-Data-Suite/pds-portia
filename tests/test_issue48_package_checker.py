"""Focused tests for the Issue #48 distribution inventory checker."""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_issue48_package.py"

RUNTIME = {
    "portia/views/__init__.py",
    "portia/views/chronology.py",
    "portia/views/currentness.py",
    "portia/views/discovery.py",
    "portia/views/filters.py",
    "portia/views/history.py",
    "portia/views/models.py",
    "portia/views/policy.py",
    "portia/views/projection.py",
    "portia/views/student.py",
}
SDIST_EXTRA = {
    "docs/student-timeline-and-work-view.md",
    "docs/validation/issue-48-student-timeline-work-view-validation.md",
    "scripts/check_issue48_package.py",
    "scripts/smoke_test_issue48_wheel.py",
    "scripts/validate_student_views.py",
}


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue48_package_checker_accepts_complete_wheel_and_sdist(
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
    assert "Issue #48 package inventory validation passed" in wheel_result.stdout
    assert "Issue #48 package inventory validation passed" in sdist_result.stdout


def test_issue48_package_checker_rejects_missing_runtime_file(
    tmp_path: Path,
) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    missing = "portia/views/student.py"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(RUNTIME - {missing}):
            archive.writestr(name, "# synthetic\n")

    result = _run(wheel)

    assert result.returncode == 1
    assert "missing Issue #48 runtime files" in result.stdout
    assert missing in result.stdout


def test_issue48_package_checker_rejects_missing_sdist_closeout_file(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    missing = "docs/student-timeline-and-work-view.md"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in sorted((RUNTIME | SDIST_EXTRA) - {missing}):
            payload = b"# synthetic\n"
            info = tarfile.TarInfo(f"pds_portia-0.2.0/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    result = _run(sdist)

    assert result.returncode == 1
    assert "missing Issue #48 sdist files" in result.stdout
    assert missing in result.stdout
