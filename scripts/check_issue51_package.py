"""Validate Issue #51 teacher-reference export distribution inventory."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

_REQUIRED_RUNTIME = {
    "portia/exports/__init__.py",
    "portia/exports/policy.py",
    "portia/exports/discovery.py",
    "portia/exports/projection.py",
    "portia/exports/inventory.py",
    "portia/exports/rendering.py",
    "portia/exports/preparation.py",
    "portia/exports/execution.py",
    "portia/exports/recovery.py",
    "portia/exports/history.py",
    "portia/menu/teacher_reference_export.py",
    "portia/menu/timeline.py",
}
_REQUIRED_SDIST = _REQUIRED_RUNTIME | {
    "CHANGELOG.md",
    "docs/README.md",
    "docs/teacher-reference-exports.md",
    "docs/validation/issue-51-acceptance-matrix.md",
    "docs/validation/issue-51-bounded-deliberate-local-exports-validation.md",
    "scripts/check_issue51_package.py",
    "scripts/smoke_test_issue51_teacher_reference_export_wheel.py",
    "scripts/validate_teacher_reference_exports.py",
    "tests/test_issue51_acceptance_matrix.py",
    "tests/test_issue51_qualification.py",
    "tests/test_teacher_reference_export_policy.py",
    "tests/test_teacher_reference_export_discovery.py",
    "tests/test_teacher_reference_export_projection.py",
    "tests/test_teacher_reference_export_rendering.py",
    "tests/test_teacher_reference_export_preparation.py",
    "tests/test_teacher_reference_export_execution.py",
    "tests/test_teacher_reference_export_recovery_history.py",
    "tests/test_teacher_menu_teacher_reference_export.py",
}


def _wheel_findings(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"could not open wheel {path}: {exc}"]
    with archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            return [f"corrupt wheel member: {corrupt}"]
        names = set(archive.namelist())
        missing = sorted(_REQUIRED_RUNTIME - names)
        if missing:
            findings.append(f"missing Issue #51 runtime files: {missing}")
        if any(name.startswith("portia/schemas/") for name in names):
            findings.append("repository schema tree leaked into runtime wheel")
    return findings


def _sdist_findings(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        archive = tarfile.open(path, mode="r:gz")
    except (OSError, tarfile.TarError) as exc:
        return [f"could not open sdist {path}: {exc}"]
    with archive:
        files = [member.name for member in archive.getmembers() if member.isfile()]
        roots = {PurePosixPath(name).parts[0] for name in files if name}
        if len(roots) != 1:
            return [
                "sdist must contain exactly one root directory: "
                f"{sorted(roots)}"
            ]
        root = next(iter(roots))
        relative = {
            PurePosixPath(name).relative_to(root).as_posix()
            for name in files
            if PurePosixPath(name).parts[0] == root
        }
        missing = sorted(_REQUIRED_SDIST - relative)
        if missing:
            findings.append(f"missing Issue #51 sdist files: {missing}")
    return findings


def _artifacts(target: Path) -> tuple[Path, ...]:
    if target.is_file():
        return (target,)
    return tuple(sorted((*target.glob("*.whl"), *target.glob("*.tar.gz"))))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()
    artifacts = _artifacts(args.target)
    if not artifacts:
        print(f"No distribution artifacts found at {args.target}")
        return 1

    findings: list[str] = []
    for artifact in artifacts:
        if artifact.suffix == ".whl":
            current = _wheel_findings(artifact)
        elif artifact.name.endswith(".tar.gz"):
            current = _sdist_findings(artifact)
        else:
            current = [f"unsupported artifact type: {artifact}"]
        findings.extend(f"{artifact.name}: {item}" for item in current)
        if not current:
            print(f"OK: {artifact}")

    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print("Portia Issue #51 package inventory validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
