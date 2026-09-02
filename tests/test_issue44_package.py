"""Focused distribution tests for Issue #44."""

from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

from scripts.check_issue44_package import (
    _REQUIRED_RUNTIME,
    _REQUIRED_SDIST,
    _sdist_findings,
    _wheel_findings,
)

ROOT = Path(__file__).resolve().parents[1]


def _write_wheel(path: Path, names: set[str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            archive.writestr(name, "# synthetic\n")


def _write_sdist(path: Path, names: set[str]) -> None:
    root = "pds_portia-0.2.0"
    with tarfile.open(path, "w:gz") as archive:
        for relative in sorted(names):
            payload = b"# synthetic\n"
            info = tarfile.TarInfo(f"{root}/{relative}")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))


def test_issue44_wheel_inventory_accepts_complete_runtime(tmp_path: Path) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    _write_wheel(wheel, set(_REQUIRED_RUNTIME))
    assert _wheel_findings(wheel) == []


def test_issue44_wheel_inventory_detects_missing_runtime(tmp_path: Path) -> None:
    wheel = tmp_path / "pds_portia-0.2.0-py3-none-any.whl"
    names = set(_REQUIRED_RUNTIME)
    names.remove("portia/workflows/interventions.py")
    _write_wheel(wheel, names)
    findings = _wheel_findings(wheel)
    assert any("interventions.py" in finding for finding in findings)


def test_issue44_sdist_inventory_accepts_docs_and_tools(tmp_path: Path) -> None:
    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    _write_sdist(sdist, set(_REQUIRED_SDIST))
    assert _sdist_findings(sdist) == []


def test_issue44_sdist_inventory_detects_missing_smoke(tmp_path: Path) -> None:
    sdist = tmp_path / "pds_portia-0.2.0.tar.gz"
    names = set(_REQUIRED_SDIST)
    names.remove("scripts/smoke_test_issue44_wheel.py")
    _write_sdist(sdist, names)
    findings = _sdist_findings(sdist)
    assert any("smoke_test_issue44_wheel.py" in finding for finding in findings)


def test_issue44_wheel_smoke_retains_core_and_boundary_guards() -> None:
    text = (ROOT / "scripts/smoke_test_issue44_wheel.py").read_text(encoding="utf-8")
    for phrase in (
        "Core 0.6.3",
        "smoke import resolved into source checkout",
        '"implementation_fabricated": False',
        '"fidelity_fabricated": False',
        "SupportProcessWorkflowService",
        "InterventionWorkflowService",
    ):
        assert phrase in text
