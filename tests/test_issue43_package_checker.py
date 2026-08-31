"""Focused tests for the Issue #43 distribution inventory checker."""

from __future__ import annotations

import io
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_issue43_package.py"

RUNTIME = {
    "portia/workflows/__init__.py",
    "portia/workflows/action_common.py",
    "portia/workflows/action_transition.py",
    "portia/workflows/communication_attachments.py",
    "portia/workflows/communication_common.py",
    "portia/workflows/communication_lifecycle.py",
    "portia/workflows/communication_relations.py",
    "portia/workflows/communication_supersession.py",
    "portia/workflows/communications.py",
    "portia/workflows/response_common.py",
    "portia/workflows/response_lifecycle.py",
    "portia/workflows/response_supersession.py",
    "portia/workflows/responses.py",
}
SDIST_EXTRA = {
    "docs/response-and-communication-workflows.md",
    "docs/validation/issue-43-response-and-communication-workflows-validation.md",
    "scripts/check_issue43_package.py",
    "scripts/smoke_test_issue43_wheel.py",
    "scripts/validate_issue43_workflows.py",
}


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_issue43_package_checker_accepts_complete_wheel_and_sdist(
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
    assert "Issue #43 package inventory validation passed" in wheel_result.stdout
    assert "Issue #43 package inventory validation passed" in sdist_result.stdout


def test_issue43_package_checker_rejects_missing_runtime_file(tmp_path: Path) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(RUNTIME - {"portia/workflows/communications.py"}):
            archive.writestr(name, "# synthetic\n")

    result = _run(wheel)

    assert result.returncode == 1
    assert "missing Issue #43 runtime files" in result.stdout
    assert "portia/workflows/communications.py" in result.stdout


def test_issue43_package_checker_rejects_missing_sdist_closeout_file(
    tmp_path: Path,
) -> None:
    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    missing = "docs/response-and-communication-workflows.md"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in sorted((RUNTIME | SDIST_EXTRA) - {missing}):
            payload = b"# synthetic\n"
            info = tarfile.TarInfo(f"pds_portia-0.2.0/{name}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    result = _run(sdist)

    assert result.returncode == 1
    assert "missing Issue #43 sdist files" in result.stdout
    assert missing in result.stdout
