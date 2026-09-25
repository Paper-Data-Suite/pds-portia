"""Validate Issue #50 teacher-menu distribution inventory."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

_REQUIRED_RUNTIME = {
    "portia/menu/__init__.py",
    "portia/menu/advanced.py",
    "portia/menu/attention.py",
    "portia/menu/authoring.py",
    "portia/menu/clock.py",
    "portia/menu/context.py",
    "portia/menu/correction.py",
    "portia/menu/event.py",
    "portia/menu/follow_up.py",
    "portia/menu/identifiers.py",
    "portia/menu/information.py",
    "portia/menu/judgment.py",
    "portia/menu/main.py",
    "portia/menu/navigation.py",
    "portia/menu/prompts.py",
    "portia/menu/response_communication.py",
    "portia/menu/selectors.py",
    "portia/menu/support.py",
    "portia/menu/support_delivery.py",
    "portia/menu/timeline.py",
    "portia/menu/ui.py",
}
_REQUIRED_SDIST = _REQUIRED_RUNTIME | {
    "docs/task-oriented-teacher-menu.md",
    "docs/validation/issue-50-task-oriented-teacher-menu-validation.md",
    "scripts/check_issue50_package.py",
    "scripts/smoke_test_issue50_teacher_menu_wheel.py",
    "scripts/validate_teacher_menu.py",
    "tests/test_issue50_teacher_menu_validation.py",
    "tests/test_teacher_menu_advanced.py",
    "tests/test_teacher_menu_attention.py",
    "tests/test_teacher_menu_correction.py",
    "tests/test_teacher_menu_event.py",
    "tests/test_teacher_menu_follow_up.py",
    "tests/test_teacher_menu_foundation.py",
    "tests/test_teacher_menu_information.py",
    "tests/test_teacher_menu_judgment.py",
    "tests/test_teacher_menu_response_communication.py",
    "tests/test_teacher_menu_support.py",
    "tests/test_teacher_menu_support_delivery.py",
    "tests/test_teacher_menu_support_planning.py",
    "tests/test_teacher_menu_timeline.py",
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
            findings.append(f"missing Issue #50 runtime files: {missing}")
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
            findings.append(f"missing Issue #50 sdist files: {missing}")
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
    print("Portia Issue #50 package inventory validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
