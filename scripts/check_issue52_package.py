"""Validate Issue #52 module-operations distribution inventory and metadata."""

from __future__ import annotations

import argparse
import configparser
import email
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_VERSION = "0.2.0"
_EXPECTED_OPERATIONS_TARGET = "portia.pds_operations:get_module_operations_profile"
_EXPECTED_CONSOLE_TARGET = "portia.cli:main"
_REQUIRED_RUNTIME = {
    "portia/pds_operations.py",
    "portia/attention_provider.py",
    "portia/readiness_provider.py",
    "portia/attention/actions.py",
}
_REQUIRED_SDIST = _REQUIRED_RUNTIME | {
    "docs/module-operations.md",
    "scripts/check_issue52_package.py",
    "scripts/smoke_test_issue52_module_operations_wheel.py",
    "tests/test_issue52_operations_profile.py",
    "tests/test_issue52_attention_provider.py",
    "tests/test_issue52_attention_actions.py",
    "tests/test_issue52_readiness_provider.py",
    "tests/test_issue52_packaging.py",
}


def _entry_point_findings(content: str) -> list[str]:
    findings: list[str] = []
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content)
    except configparser.Error as exc:
        return [f"could not parse entry_points.txt: {exc}"]

    console = dict(parser.items("console_scripts")) if parser.has_section("console_scripts") else {}
    if console.get("portia") != _EXPECTED_CONSOLE_TARGET:
        findings.append(f"unexpected portia console entry point: {console.get('portia')!r}")

    operations = (
        dict(parser.items("paper_data_suite.module_operations"))
        if parser.has_section("paper_data_suite.module_operations")
        else {}
    )
    if operations != {"portia": _EXPECTED_OPERATIONS_TARGET}:
        findings.append(f"unexpected module-operations entry points: {operations!r}")

    for forbidden in (
        "paper_data_suite.modules",
        "paper_data_suite.publication_producers",
    ):
        if parser.has_section(forbidden):
            findings.append(f"premature entry-point group present: {forbidden}")
    return findings


def _metadata_findings(content: bytes) -> list[str]:
    findings: list[str] = []
    message = email.message_from_bytes(content)
    if message.get("Name") != "pds-portia":
        findings.append(f"unexpected distribution name: {message.get('Name')!r}")
    if message.get("Version") != EXPECTED_VERSION:
        findings.append(f"unexpected distribution version: {message.get('Version')!r}")
    requirements = [
        item.replace(" ", "") for item in message.get_all("Requires-Dist", [])
    ]
    if not any("pds-core<0.7,>=0.6.3" in item for item in requirements):
        findings.append(f"missing preserved Core compatibility floor: {requirements}")
    runtime = [item.lower() for item in requirements if "extra==" not in item.lower()]
    if any(
        sibling in requirement
        for sibling in ("scoreform", "quillan", "concord", "meridian", "vitrine")
        for requirement in runtime
    ):
        findings.append(f"unexpected sibling runtime dependency: {runtime}")
    return findings


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
            findings.append(f"missing Issue #52 runtime files: {missing}")
        if any(name.startswith("portia/schemas/") for name in names):
            findings.append("repository schema tree leaked into runtime wheel")

        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            findings.append("expected exactly one wheel METADATA file")
        else:
            findings.extend(_metadata_findings(archive.read(metadata_names[0])))

        entry_names = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        if len(entry_names) != 1:
            findings.append("expected exactly one wheel entry_points.txt")
        else:
            findings.extend(
                _entry_point_findings(
                    archive.read(entry_names[0]).decode("utf-8")
                )
            )
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
            findings.append(f"missing Issue #52 sdist files: {missing}")
        pkg_info = f"{root}/PKG-INFO"
        try:
            handle = archive.extractfile(pkg_info)
        except KeyError:
            findings.append("sdist PKG-INFO is missing")
        else:
            if handle is None:
                findings.append("sdist PKG-INFO is unreadable")
            else:
                findings.extend(_metadata_findings(handle.read()))
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
    print("Portia Issue #52 package inventory validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
