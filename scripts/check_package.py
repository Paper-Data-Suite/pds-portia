"""Validate built Portia wheel and source-distribution boundaries."""

from __future__ import annotations

import argparse
import email
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_VERSION = "0.2.0"
REQUIRED_RUNTIME_FILES = {
    "portia/__init__.py",
    "portia/__main__.py",
    "portia/_version.py",
    "portia/_bundle_builder.py",
    "portia/_runtime_contract_bundle.json",
    "portia/cli.py",
    "portia/py.typed",
    "portia/runtime-coverage.json",
    "portia/identity/__init__.py",
    "portia/identity/actors.py",
    "portia/identity/context.py",
    "portia/identity/errors.py",
    "portia/identity/issue22_parity.py",
    "portia/identity/roster.py",
    "portia/models/__init__.py",
    "portia/models/base.py",
    "portia/models/common.py",
    "portia/models/coverage.py",
    "portia/models/errors.py",
    "portia/models/identifiers.py",
    "portia/models/json_values.py",
    "portia/models/records.py",
    "portia/models/references.py",
    "portia/models/schema_runtime.py",
    "portia/storage/__init__.py",
    "portia/storage/acknowledgements.py",
    "portia/storage/actor_directory.py",
    "portia/storage/derived.py",
    "portia/storage/errors.py",
    "portia/storage/fingerprint.py",
    "portia/storage/integrity.py",
    "portia/storage/io.py",
    "portia/storage/issue22_parity.py",
    "portia/storage/locks.py",
    "portia/storage/orchestration.py",
    "portia/storage/paths.py",
    "portia/storage/quarantine.py",
    "portia/storage/recovery.py",
    "portia/storage/repository.py",
    "portia/storage/series.py",
    "portia/storage/staging.py",
    "portia/validation/__init__.py",
    "portia/validation/context.py",
    "portia/validation/findings.py",
    "portia/validation/graph.py",
    "portia/validation/issue22_parity.py",
    "portia/workflows/__init__.py",
    "portia/workflows/common.py",
    "portia/workflows/context.py",
    "portia/workflows/coordinated.py",
    "portia/workflows/errors.py",
    "portia/workflows/events.py",
    "portia/workflows/issue22_parity.py",
    "portia/workflows/participants.py",
    "portia/workflows/relationships.py",
    "portia/workflows/roles.py",
}
REQUIRED_SDIST_FILES = {
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "SECURITY.md",
    "pyproject.toml",
    "setup.py",
    "docs/development.md",
    "docs/identity-and-actor-directory.md",
    "docs/runtime-models.md",
    "docs/storage.md",
    "docs/synthetic-data-policy.md",
    "docs/validation/issue-38-canonical-storage-and-guarded-persistence-validation.md",
    "docs/validation/issue-39-actor-directory-and-core-roster-linking-validation.md",
    "docs/event-participant-role-and-relationship-workflows.md",
    "docs/validation/issue-40-event-participant-role-and-relationship-workflows-validation.md",
    "portia/__init__.py",
    "portia/__main__.py",
    "portia/_version.py",
    "portia/_bundle_builder.py",
    "portia/cli.py",
    "portia/identity/__init__.py",
    "portia/identity/actors.py",
    "portia/identity/context.py",
    "portia/identity/errors.py",
    "portia/identity/issue22_parity.py",
    "portia/identity/roster.py",
    "portia/models/__init__.py",
    "portia/models/records.py",
    "portia/models/schema_runtime.py",
    "portia/storage/__init__.py",
    "portia/storage/actor_directory.py",
    "portia/storage/issue22_parity.py",
    "portia/storage/orchestration.py",
    "portia/storage/repository.py",
    "portia/validation/__init__.py",
    "portia/validation/graph.py",
    "portia/workflows/__init__.py",
    "portia/workflows/common.py",
    "portia/workflows/context.py",
    "portia/workflows/coordinated.py",
    "portia/workflows/errors.py",
    "portia/workflows/events.py",
    "portia/workflows/issue22_parity.py",
    "portia/workflows/participants.py",
    "portia/workflows/relationships.py",
    "portia/workflows/roles.py",
    "scripts/bootstrap_dev.ps1",
    "scripts/bootstrap_dev.sh",
    "scripts/check_package.py",
    "scripts/repair_pip_residue.py",
    "scripts/smoke_test_wheel.py",
    "scripts/validate_identity.py",
    "scripts/validate_portia_foundation.py",
    "scripts/validate_repository.py",
    "scripts/validate_runtime_models.py",
    "scripts/validate_storage.py",
    "scripts/validate_workflows.py",
    "scripts/verify_core_wheel.py",
}


def _unsafe_path(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)


def _metadata_findings(content: bytes) -> list[str]:
    findings: list[str] = []
    message = email.message_from_bytes(content)
    if message.get("Name") != "pds-portia":
        findings.append(f"unexpected distribution name: {message.get('Name')!r}")
    if message.get("Version") != EXPECTED_VERSION:
        findings.append(f"unexpected version: {message.get('Version')!r}")
    if message.get("Requires-Python") != ">=3.11":
        findings.append(f"unexpected Requires-Python: {message.get('Requires-Python')!r}")
    requirements = [item.replace(" ", "") for item in message.get_all("Requires-Dist", [])]
    if not any("pds-core<0.7,>=0.6.3" in item for item in requirements):
        findings.append(f"missing Core 0.6.3 dependency floor: {requirements}")
    sibling_names = ("scoreform", "quillan", "concord", "meridian", "vitrine")
    runtime_requirements = [item.lower() for item in requirements if "extra==" not in item.lower()]
    if any(any(name in item for name in sibling_names) for item in runtime_requirements):
        findings.append(f"unexpected sibling runtime dependency: {runtime_requirements}")
    if any("jsonschema" in item.lower() for item in runtime_requirements):
        findings.append("jsonschema must remain a development/test dependency, not runtime")
    return findings


def validate_wheel(path: Path) -> list[str]:
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
        runtime = {name for name in names if name.startswith("portia/")}
        missing = sorted(REQUIRED_RUNTIME_FILES - runtime)
        if missing:
            findings.append(f"missing runtime files: {missing}")
        for name in runtime:
            if name.endswith("/"):
                continue
            if not (
                name.endswith(".py")
                or name.endswith(".json")
                or name == "portia/py.typed"
            ):
                findings.append(f"unexpected runtime file type: {name}")
            if name.startswith("portia/schemas/"):
                findings.append(f"repository schema tree leaked into runtime wheel: {name}")
        for name in names:
            if _unsafe_path(name):
                findings.append(f"unsafe wheel path: {name}")
            if name.startswith(("docs/", "schemas/", "scripts/", "tests/", ".github/")):
                findings.append(f"forbidden wheel repository content: {name}")
            if "__pycache__/" in name or name.endswith((".pyc", ".pyo")):
                findings.append(f"forbidden wheel cache content: {name}")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            findings.append("expected exactly one wheel METADATA file")
        else:
            findings.extend(_metadata_findings(archive.read(metadata_names[0])))
        entry_names = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_names) != 1:
            findings.append("expected exactly one wheel entry_points.txt")
        else:
            entries = archive.read(entry_names[0]).decode("utf-8")
            if "portia = portia.cli:main" not in entries:
                findings.append("missing portia console entry point")
            if "paper_data_suite.modules" in entries:
                findings.append("suite routing entry point is premature in #40")
            if "paper_data_suite.publication_producers" in entries:
                findings.append("publication producer entry point is premature in #40")
        try:
            bundle = archive.read("portia/_runtime_contract_bundle.json")
        except KeyError:
            findings.append("compiled runtime contract bundle is missing")
        else:
            if b'"bundle_contract": "pds-portia.runtime-contract-bundle"' not in bundle:
                findings.append("compiled runtime contract bundle has unexpected identity")
    return findings


def validate_sdist(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        archive = tarfile.open(path, mode="r:gz")
    except (OSError, tarfile.TarError) as exc:
        return [f"could not open sdist {path}: {exc}"]
    with archive:
        members = archive.getmembers()
        files = [member.name for member in members if member.isfile()]
        roots = {PurePosixPath(name).parts[0] for name in files if name}
        if len(roots) != 1:
            return [f"sdist must contain exactly one root directory: {sorted(roots)}"]
        root = next(iter(roots))
        relative = {
            PurePosixPath(name).relative_to(root).as_posix()
            for name in files
            if PurePosixPath(name).parts[0] == root
        }
        missing = sorted(REQUIRED_SDIST_FILES - relative)
        if missing:
            findings.append(f"missing required sdist files: {missing}")
        for member in members:
            if _unsafe_path(member.name):
                findings.append(f"unsafe sdist path: {member.name}")
            if member.issym() or member.islnk():
                findings.append(f"sdist link member is not allowed: {member.name}")
            if "__pycache__/" in member.name or member.name.endswith((".pyc", ".pyo")):
                findings.append(f"forbidden sdist cache content: {member.name}")
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
    wheels = sorted(target.glob("*.whl"))
    sdists = sorted(target.glob("*.tar.gz"))
    return tuple(wheels + sdists)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()
    artifacts = _artifacts(args.target)
    if not artifacts:
        print(f"No distribution artifacts found at {args.target}", file=sys.stderr)
        return 1
    all_findings: list[str] = []
    for artifact in artifacts:
        if artifact.suffix == ".whl":
            findings = validate_wheel(artifact)
        elif artifact.name.endswith(".tar.gz"):
            findings = validate_sdist(artifact)
        else:
            findings = [f"unsupported artifact type: {artifact}"]
        if findings:
            all_findings.extend(f"{artifact.name}: {finding}" for finding in findings)
        else:
            print(f"OK: {artifact}")
    if all_findings:
        for finding in all_findings:
            print(f"ERROR: {finding}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
