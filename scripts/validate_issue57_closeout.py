"""Issue #57 preparation service and qualification closeout audit.

Static architectural/package checks complement (not replace) the behavior tests
and independently hosted Core 0.6.6 installed-wheel qualification. Historical
release evidence, source blobs and prior-version CI jobs remain unchanged.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

from portia.capture import (
    FileCaptureBatchService,
    FileCapturePreparationService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.models import CaptureBatchV1, PageTargetV1, PageTargetV2
from scripts.check_package import REQUIRED_RUNTIME_FILES, REQUIRED_SDIST_FILES
from scripts.verify_core_wheel import KNOWN_WHEELS, verify_wheel

ROOT = Path(__file__).resolve().parents[1]
CORE_066 = "pds_core-0.6.6-py3-none-any.whl"
CORE_066_SHA256 = "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301"

RUNTIME_FILES = frozenset(
    {
        "portia/capture/__init__.py",
        "portia/capture/contracts.py",
        "portia/capture/batches.py",
        "portia/capture/page_targets.py",
        "portia/capture/purposes.py",
        "portia/capture/routes.py",
        "portia/capture/preparation.py",
        "portia/capture/recovery.py",
    }
)
SDIST_FILES = frozenset(
    {
        "scripts/validate_issue57_closeout.py",
        "scripts/smoke_test_issue57_core066_wheel.py",
        "tests/test_issue57_closeout.py",
        "tests/test_issue57_slice8_core066.py",
        "docs/validation/issue-57-acceptance-matrix.md",
        "docs/validation/issue-57-final-qualification.md",
    }
    | {
        f"tests/test_issue57_slice{n}_{name}.py"
        for n, name in (
            (1, "contracts"),
            (2, "batches"),
            (3, "page_targets"),
            (4, "purposes"),
            (5, "routes"),
            (6, "preparation"),
            (7, "recovery"),
        )
    }
)


def validate(root: Path = ROOT) -> tuple[str, ...]:
    """Check Issue #57 source/package/qualification wiring without mutation."""
    findings: list[str] = []
    root = root.resolve()
    for path in sorted(RUNTIME_FILES | SDIST_FILES):
        if not (root / path).is_file():
            findings.append(f"required Issue #57 source missing: {path}")
    missing_runtime = RUNTIME_FILES - REQUIRED_RUNTIME_FILES
    if missing_runtime:
        findings.append(
            f"capture services missing from wheel inventory: {sorted(missing_runtime)}"
        )
    missing_sdist = (RUNTIME_FILES | SDIST_FILES) - REQUIRED_SDIST_FILES
    if missing_sdist:
        findings.append(
            f"Issue #57 sources missing from sdist inventory: {sorted(missing_sdist)}"
        )

    service_methods: tuple[tuple[type[object], tuple[str, ...]], ...] = (
        (
            FileCaptureBatchService,
            ("create_or_load", "load", "list_batches", "transition"),
        ),
        (FilePageTargetService, ("create_or_load", "load", "list_targets")),
        (FilePageRouteService, ("register_or_load", "inspect")),
        (FileCapturePreparationService, ("prepare", "inspect", "recover")),
    )
    for cls, methods in service_methods:
        for method in methods:
            if not callable(getattr(cls, method, None)):
                findings.append(
                    f"missing capture service method: {cls.__name__}.{method}"
                )

    for model, version in (
        (CaptureBatchV1, "1"),
        (PageTargetV1, "1"),
        (PageTargetV2, "2"),
    ):
        if model.VERSION != version:
            findings.append(f"unexpected frozen {model.CONTRACT} model version")

    try:
        with (root / "pyproject.toml").open("rb") as stream:
            pyproject = tomllib.load(stream)
        project = pyproject["project"]
        requirements = project["dependencies"]
        if requirements != [
            "pds-core>=0.6.3,<0.7",
            "reportlab>=4.2,<5",
            "qrcode>=7.4,<9",
            "pypdf>=5,<7",
        ]:
            findings.append("Portia Core runtime compatibility range changed")
        if project.get("requires-python") != ">=3.11":
            findings.append("Portia Python support changed")
        mypy_files = pyproject["tool"]["mypy"]["files"]
        if "scripts/validate_issue57_closeout.py" not in mypy_files:
            findings.append("Issue #57 closeout validator missing from strict mypy")
    except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        findings.append(f"could not inspect project metadata: {exc}")

    if KNOWN_WHEELS.get(CORE_066) != ("0.6.6", CORE_066_SHA256):
        findings.append("official Core 0.6.6 wheel identity not authenticated")

    try:
        ci = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        repository_validator = (root / "scripts/validate_repository.py").read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as exc:
        findings.append(f"missing qualification wiring: {exc}")
    else:
        for marker in (
            "issue57-core066:",
            "os: [ubuntu-latest, windows-latest]",
            'current_core: "0.6.5"',
            'prior_core: "0.6.4"',
            'core: "0.6.3"',
            "PDS_CORE_066_WHEEL=$wheel",
            "scripts/smoke_test_issue57_core066_wheel.py",
        ):
            if marker not in ci:
                findings.append(f"missing Core platform/historical CI marker: {marker}")
        old = '"scripts/validate_issue56_closeout.py"'
        current = '"scripts.validate_issue57_closeout"'
        tests = '[sys.executable, "-m", "pytest"]'
        if not (
            0
            <= repository_validator.find(old)
            < repository_validator.find(current)
            < repository_validator.find(tests)
        ):
            findings.append(
                "Issue #57 closeout audit must follow Issue #56 and precede pytest"
            )

    try:
        tests_source = (root / "tests/test_issue57_slice8_core066.py").read_text(
            encoding="utf-8"
        )
        if 'os.environ.get("PDS_CORE_066_WHEEL", "")' not in tests_source:
            findings.append("Core 0.6.6 test isolation variable is missing")
    except (OSError, UnicodeError) as exc:
        findings.append(f"cannot audit version-specific test isolation: {exc}")

    return tuple(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--core-wheel", type=Path, help="optionally authenticate exact Core 0.6.6 wheel"
    )
    args = parser.parse_args()
    failures = list(validate())
    if args.core_wheel is not None:
        try:
            if verify_wheel(args.core_wheel) != "0.6.6":
                failures.append("wrong Core release supplied to Issue #57 closeout")
        except (OSError, ValueError) as exc:
            failures.append(f"Core 0.6.6 authentication failed: {exc}")
    if failures:
        for finding in failures:
            print(f"Issue #57 closeout: {finding}", file=sys.stderr)
        return 1
    print("Portia Issue #57 closeout source and qualification wiring passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
