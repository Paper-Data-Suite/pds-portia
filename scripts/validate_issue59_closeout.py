"""Final Issue #59 source/packaging/ownership audit (non-mutating)."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from scripts.check_package import REQUIRED_RUNTIME_FILES, REQUIRED_SDIST_FILES

ROOT = Path(__file__).resolve().parents[1]

INTAKE_FILES = frozenset(
    {
        "portia/intake/__init__.py",
        "portia/intake/contracts.py",
        "portia/intake/retention.py",
        "portia/intake/recognition.py",
        "portia/intake/dispatch.py",
        "portia/intake/page_records.py",
        "portia/intake/teacher.py",
        "portia/intake/recovery.py",
        "portia/menu/returned_paper.py",
    }
)
VALIDATION_FILES = frozenset(
    {
        "scripts/validate_issue59_closeout.py",
        "scripts/smoke_test_issue59_scan_wheel.py",
        "tests/test_issue59_slice8_closeout.py",
        "docs/validation/issue-59-slice-8-final-matrix.md",
        *(
            f"docs/validation/issue-59-slice-{n}-{name}.md"
            for n, name in (
                (1, "intake-contract-boundaries"),
                (2, "retain-first-source"),
                (3, "page-qr-discovery"),
                (4, "core-dispatch"),
                (5, "page-record-receipts"),
                (6, "teacher-intake-workflow"),
                (7, "restart-recovery"),
            )
        ),
        *(
            f"tests/test_issue59_slice{n}_{name}.py"
            for n, name in (
                (1, "intake_contracts"),
                (2, "retention"),
                (3, "page_qr_discovery"),
                (4, "route_dispatch"),
                (5, "page_records"),
                (6, "teacher_workflow"),
                (7, "restart_recovery"),
            )
        ),
    }
)


def validate(root: Path = ROOT) -> tuple[str, ...]:
    """Assert public install, frozen historical contracts and release wiring."""
    findings: list[str] = []
    for relative in sorted(INTAKE_FILES | VALIDATION_FILES):
        if not (root / relative).is_file():
            findings.append(f"Issue #59 source missing: {relative}")
    if not INTAKE_FILES <= REQUIRED_RUNTIME_FILES:
        findings.append("Issue #59 runtime sources are missing from wheel manifest")
    if not (INTAKE_FILES | VALIDATION_FILES) <= REQUIRED_SDIST_FILES:
        findings.append("Issue #59 sources are missing from sdist manifest")
    try:
        with (root / "pyproject.toml").open("rb") as stream:
            project = tomllib.load(stream)
        dependencies = project["project"]["dependencies"]
        if dependencies != [
            "pds-core>=0.6.3,<0.7",
            "reportlab>=4.2,<5",
            "qrcode>=7.4,<9",
            "pypdf>=5,<7",
        ]:
            findings.append("historical Core/runtime dependency authority changed")
        optional = project["project"]["optional-dependencies"]
        scan = optional["scan"]
        if scan != [
            "PyMuPDF>=1.26,<2",
            "opencv-python-headless>=4.10,<6",
            "numpy>=2,<3",
        ]:
            findings.append("Issue #59 installed QR/raster scan extra changed")
        if (
            project["tool"]["mypy"]["files"].count(
                "scripts/validate_issue59_closeout.py"
            )
            != 1
        ):
            findings.append("Issue #59 validator is not in strict mypy gate")
        if (
            project["tool"]["mypy"]["files"].count(
                "scripts/smoke_test_issue59_scan_wheel.py"
            )
            != 1
        ):
            findings.append("Issue #59 installed smoke is not in strict mypy gate")
    except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError):
        findings.append("cannot verify frozen runtime and scan-extra metadata")
    try:
        root_menu = (root / "portia/menu/main.py").read_text(encoding="utf-8")
        teacher = (root / "portia/intake/teacher.py").read_text(encoding="utf-8")
        receipts = (root / "portia/intake/page_records.py").read_text(encoding="utf-8")
        ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        qualification = (root / "scripts/validate_repository.py").read_text(
            encoding="utf-8"
        )
        if '"11",' not in root_menu or "launch_returned_paper_menu" not in root_menu:
            findings.append("teacher intake menu is not exposed")
        if "resume_recovered" not in teacher or "admit_and_retain" not in teacher:
            findings.append("retention/restart flow is not exposed")
        if "PageRecordV1" not in receipts or "exclusive_create" not in receipts:
            findings.append("exact retained Page Record storage is missing")
        if "smoke_test_issue59_scan_wheel.py" not in ci:
            findings.append("official Core 0.6.6 installed wheel smoke is missing")
        if "validate_issue59_closeout" not in qualification:
            findings.append("final repository qualification omits #59 audit")
        if "smoke_test_issue59_scan_wheel" not in qualification:
            findings.append("historical Core installed smoke is missing")
    except OSError:
        findings.append("cannot inspect Issue #59 teacher/CI qualification wiring")
    return tuple(findings)


def main() -> int:
    findings = validate()
    for finding in findings:
        print(f"FAIL: {finding}", file=sys.stderr)
    if findings:
        return 1
    print("Issue #59 source, wheel/sdist and CI closeout audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
