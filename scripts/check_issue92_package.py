"""Validate Issue #92 path-safety distribution inventory and metadata."""

from __future__ import annotations

import argparse
import email
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_VERSION = "0.2.0"
_REQUIRED_RUNTIME = {
    "portia/storage/generated_paths.py",
    "portia/storage/paths.py",
    "portia/storage/io.py",
    "portia/storage/staging.py",
    "portia/storage/repository.py",
    "portia/storage/derived.py",
    "portia/workflows/integrity.py",
}
_REQUIRED_SDIST = _REQUIRED_RUNTIME | {
    "CHANGELOG.md",
    "docs/path-safety.md",
    "scripts/check_issue92_package.py",
    "scripts/smoke_test_issue92_deep_workspace_wheel.py",
    "tests/test_generated_paths_issue92.py",
    "tests/test_path_geometry_issue92.py",
    "tests/test_derived_paths_issue92.py",
    "tests/test_deep_workspace_issue92.py",
    "tests/test_issue92_qualification.py",
}


def _metadata_findings(content: bytes) -> list[str]:
    findings: list[str] = []
    message = email.message_from_bytes(content)
    if message.get("Name") != "pds-portia":
        findings.append(f"unexpected distribution name: {message.get('Name')!r}")
    if message.get("Version") != EXPECTED_VERSION:
        findings.append(
            f"unexpected distribution version: {message.get('Version')!r}"
        )
    requirements = [
        item.replace(" ", "") for item in message.get_all("Requires-Dist", [])
    ]
    if not any("pds-core<0.7,>=0.6.3" in item for item in requirements):
        findings.append(
            f"missing preserved Core compatibility floor: {requirements}"
        )
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
            findings.append(f"missing Issue #92 runtime files: {missing}")
        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            findings.append("expected exactly one wheel METADATA file")
        else:
            findings.extend(_metadata_findings(archive.read(metadata_names[0])))
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
            findings.append(f"missing Issue #92 sdist files: {missing}")
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
    print("Portia Issue #92 package inventory validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
