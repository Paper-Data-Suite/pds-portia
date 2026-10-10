"""Validate the Portia v0.2.0 Issue #54 release-candidate artifacts.

This is a pre-freeze package gate. The hashes printed here are diagnostic
candidate hashes only, not final release hashes.
"""

from __future__ import annotations

import configparser
import email
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Final, cast

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

EXPECTED_WHEEL: Final[str] = "pds_portia-0.2.0-py3-none-any.whl"
EXPECTED_SDIST: Final[str] = "pds_portia-0.2.0.tar.gz"
EXPECTED_SDIST_ROOT: Final[str] = "pds_portia-0.2.0"
EXPECTED_VERSION: Final[str] = "0.2.0"
EXPECTED_CONSOLE_TARGET: Final[str] = "portia.cli:main"
EXPECTED_OPERATIONS_TARGET: Final[str] = (
    "portia.pds_operations:get_module_operations_profile"
)

REQUIRED_SDIST_EVIDENCE: Final[frozenset[str]] = frozenset(
    {
        "CHANGELOG.md",
        "LICENSE",
        "MANIFEST.in",
        "README.md",
        "RELEASE_NOTES_v0.2.0.md",
        "SECURITY.md",
        "pyproject.toml",
        "setup.py",
        "docs/README.md",
        "docs/audits/portia-v0.2.0-release-audit.json",
        "docs/audits/portia-v0.2.0-release-audit.md",
        "docs/audits/portia-v0.2.0-release-findings.md",
        "docs/validation/issue-54-v0.2.0-release-audit-validation.md",
        "scripts/check_package.py",
        "scripts/check_issue53_package.py",
        "scripts/check_issue54_release_package.py",
        "scripts/validate_issue54_release_audit.py",
        "scripts/validate_issue54_documentation_audit.py",
        "scripts/validate_issue54_release_mechanics.py",
        "tests/test_issue54_release_audit.py",
        "tests/test_issue54_documentation_audit.py",
        "tests/test_issue54_release_package.py",
        "tests/test_issue54_release_mechanics.py",
    }
)

FORBIDDEN_WHEEL_PREFIXES: Final[tuple[str, ...]] = (
    "docs/",
    "schemas/",
    "scripts/",
    "tests/",
    ".github/",
)
SIBLING_RUNTIME_NAMES: Final[frozenset[str]] = frozenset(
    {
        "pds-scoreform",
        "pds-quillan",
        "pds-concord",
        "pds-meridian",
        "pds-vitrine",
        "pds-paper-data-suite",
    }
)


def _unsafe_path(name: str) -> bool:
    path = PurePosixPath(name)
    return path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_findings(content: bytes) -> list[str]:
    findings: list[str] = []
    message = email.message_from_bytes(content)
    if message.get("Name") != "pds-portia":
        findings.append(f"unexpected distribution name: {message.get('Name')!r}")
    if message.get("Version") != EXPECTED_VERSION:
        findings.append(f"unexpected distribution version: {message.get('Version')!r}")
    if message.get("Requires-Python") != ">=3.11":
        findings.append(
            f"unexpected Requires-Python: {message.get('Requires-Python')!r}"
        )
    if message.get("License-Expression") not in {None, "MIT"}:
        findings.append(
            f"unexpected license expression: {message.get('License-Expression')!r}"
        )

    runtime: list[Requirement] = []
    for raw in message.get_all("Requires-Dist", []):
        try:
            requirement = Requirement(raw)
        except ValueError as exc:
            findings.append(f"invalid Requires-Dist {raw!r}: {exc}")
            continue
        marker_text = str(requirement.marker) if requirement.marker is not None else ""
        if "extra" not in marker_text:
            runtime.append(requirement)

    if len(runtime) != 1:
        findings.append(
            "runtime dependency closure must contain exactly one requirement: "
            f"{[str(item) for item in runtime]}"
        )
    else:
        requirement = runtime[0]
        if canonicalize_name(requirement.name) != "pds-core":
            findings.append(f"unexpected runtime dependency: {requirement}")
        if str(requirement.specifier) != "<0.7,>=0.6.3":
            findings.append(f"unexpected Core specifier: {requirement.specifier}")
        if requirement.url is not None or requirement.extras:
            findings.append("Core runtime dependency must be ordinary and unconditional")

    runtime_names = {canonicalize_name(item.name) for item in runtime}
    if runtime_names & SIBLING_RUNTIME_NAMES:
        findings.append(
            f"unexpected sibling PDS runtime dependency: {sorted(runtime_names)}"
        )
    return findings


def _entry_point_findings(content: str) -> list[str]:
    findings: list[str] = []
    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read_string(content)
    except configparser.Error as exc:
        return [f"could not parse entry_points.txt: {exc}"]

    console = (
        dict(parser.items("console_scripts"))
        if parser.has_section("console_scripts")
        else {}
    )
    if console != {"portia": EXPECTED_CONSOLE_TARGET}:
        findings.append(f"unexpected console entry-point surface: {console!r}")

    operations = (
        dict(parser.items("paper_data_suite.module_operations"))
        if parser.has_section("paper_data_suite.module_operations")
        else {}
    )
    if operations != {"portia": EXPECTED_OPERATIONS_TARGET}:
        findings.append(f"unexpected module-operations surface: {operations!r}")

    for forbidden in (
        "paper_data_suite.modules",
        "paper_data_suite.publication_producers",
    ):
        if parser.has_section(forbidden):
            findings.append(f"unexpected release entry-point group: {forbidden}")
    return findings


def _single_member(names: set[str], suffix: str) -> str | None:
    matches = sorted(name for name in names if name.endswith(suffix))
    return matches[0] if len(matches) == 1 else None


def _wheel_findings(path: Path) -> list[str]:
    findings: list[str] = []
    if path.name != EXPECTED_WHEEL:
        findings.append(f"wheel filename must be exactly {EXPECTED_WHEEL}")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        return findings + [f"could not open wheel: {exc}"]

    with archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            return findings + [f"corrupt wheel member: {corrupt}"]
        names = set(archive.namelist())

        for name in sorted(names):
            if _unsafe_path(name):
                findings.append(f"unsafe wheel path: {name}")
            if name.startswith(FORBIDDEN_WHEEL_PREFIXES):
                findings.append(f"repository content leaked into runtime wheel: {name}")
            if name == "RELEASE_NOTES_v0.2.0.md":
                findings.append("release notes must not be a runtime-wheel root file")
            if "__pycache__/" in name or name.endswith((".pyc", ".pyo")):
                findings.append(f"cache content leaked into runtime wheel: {name}")

        for required in (
            "portia/_runtime_contract_bundle.json",
            "portia/py.typed",
            "portia/runtime-coverage.json",
        ):
            if required not in names:
                findings.append(f"required runtime package resource is missing: {required}")

        metadata_name = _single_member(names, ".dist-info/METADATA")
        if metadata_name is None:
            findings.append("wheel must contain exactly one METADATA file")
        else:
            findings.extend(_metadata_findings(archive.read(metadata_name)))

        entries_name = _single_member(names, ".dist-info/entry_points.txt")
        if entries_name is None:
            findings.append("wheel must contain exactly one entry_points.txt")
        else:
            findings.extend(
                _entry_point_findings(archive.read(entries_name).decode("utf-8"))
            )

        wheel_name = _single_member(names, ".dist-info/WHEEL")
        if wheel_name is None:
            findings.append("wheel must contain exactly one WHEEL metadata file")
        else:
            wheel_metadata = email.message_from_bytes(archive.read(wheel_name))
            if wheel_metadata.get("Root-Is-Purelib") != "true":
                findings.append("release wheel must be purelib")
            tags = wheel_metadata.get_all("Tag", [])
            if tags != ["py3-none-any"]:
                findings.append(f"release wheel tag must be py3-none-any: {tags!r}")
    return findings


def _sdist_audit_findings(raw: object) -> list[str]:
    findings: list[str] = []
    if not isinstance(raw, dict):
        return ["sdist release-audit state must be one JSON object"]
    audit = cast(dict[str, Any], raw)
    if audit.get("target_distribution") != "pds-portia":
        findings.append("sdist release audit has unexpected target distribution")
    if audit.get("target_version") != "0.2.0":
        findings.append("sdist release audit has unexpected target version")
    if audit.get("final_verdict") != "PENDING":
        findings.append("pre-freeze candidate must retain PENDING final verdict")
    publication = audit.get("release_publication")
    if not isinstance(publication, dict) or publication.get("status") != "not_started":
        findings.append("pre-freeze candidate must retain not_started publication state")

    statuses: dict[str, str] = {}
    domains = audit.get("audit_domains")
    if isinstance(domains, list):
        for item in domains:
            if isinstance(item, dict):
                domain_id = item.get("domain_id")
                status = item.get("status")
                if isinstance(domain_id, str) and isinstance(status, str):
                    statuses[domain_id] = status
    if statuses.get("release_contract_mechanical") != "pass":
        findings.append("sdist must carry release_contract_mechanical == pass")
    if statuses.get("cumulative_repository_qualification") != "pending":
        findings.append("Slice 14 must not pre-pass cumulative repository qualification")
    if statuses.get("python_platform_qualification") != "pending":
        findings.append("Slice 14 must not pre-pass Python/platform qualification")
    return findings


def _sdist_findings(path: Path) -> list[str]:
    findings: list[str] = []
    if path.name != EXPECTED_SDIST:
        findings.append(f"sdist filename must be exactly {EXPECTED_SDIST}")
    try:
        archive = tarfile.open(path, mode="r:gz")
    except (OSError, tarfile.TarError) as exc:
        return findings + [f"could not open sdist: {exc}"]

    with archive:
        members = archive.getmembers()
        files = [member.name for member in members if member.isfile()]
        roots = {PurePosixPath(name).parts[0] for name in files if name}
        if roots != {EXPECTED_SDIST_ROOT}:
            findings.append(
                f"sdist root must be exactly {EXPECTED_SDIST_ROOT}: {sorted(roots)}"
            )
            return findings

        relative = {
            PurePosixPath(name).relative_to(EXPECTED_SDIST_ROOT).as_posix()
            for name in files
        }
        missing = sorted(REQUIRED_SDIST_EVIDENCE - relative)
        if missing:
            findings.append(f"sdist missing Issue #54 release evidence: {missing}")

        for member in members:
            if _unsafe_path(member.name):
                findings.append(f"unsafe sdist path: {member.name}")
            if member.issym() or member.islnk():
                findings.append(f"sdist link member is not allowed: {member.name}")
            if "__pycache__/" in member.name or member.name.endswith((".pyc", ".pyo")):
                findings.append(f"cache content leaked into sdist: {member.name}")

        pkg_info = f"{EXPECTED_SDIST_ROOT}/PKG-INFO"
        handle = archive.extractfile(pkg_info)
        if handle is None:
            findings.append("sdist PKG-INFO is missing or unreadable")
        else:
            findings.extend(_metadata_findings(handle.read()))

        audit_name = (
            f"{EXPECTED_SDIST_ROOT}/docs/audits/portia-v0.2.0-release-audit.json"
        )
        audit_handle = archive.extractfile(audit_name)
        if audit_handle is None:
            findings.append("sdist release-audit JSON is missing or unreadable")
        else:
            try:
                raw: object = json.loads(audit_handle.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                findings.append(f"sdist release-audit JSON is invalid: {exc}")
            else:
                findings.extend(_sdist_audit_findings(raw))

        notes_name = f"{EXPECTED_SDIST_ROOT}/RELEASE_NOTES_v0.2.0.md"
        notes_handle = archive.extractfile(notes_name)
        if notes_handle is None:
            findings.append("sdist release notes are missing or unreadable")
        else:
            notes = notes_handle.read().decode("utf-8")
            marker = (
                "Status: **release candidate; publication pending Issue #54 "
                "Phase 2 verification**"
            )
            if marker not in notes:
                findings.append("sdist release notes do not preserve candidate status")
    return findings


def validate_target(target: Path) -> list[str]:
    if not target.is_dir():
        return [f"artifact target is not a directory: {target}"]

    files = {path.name: path for path in target.iterdir() if path.is_file()}
    expected = {EXPECTED_WHEEL, EXPECTED_SDIST}
    if set(files) != expected:
        return [
            "dist must contain exactly the two Issue #54 candidate artifacts; "
            f"expected={sorted(expected)}, actual={sorted(files)}"
        ]

    findings: list[str] = []
    findings.extend(_wheel_findings(files[EXPECTED_WHEEL]))
    findings.extend(_sdist_findings(files[EXPECTED_SDIST]))
    return findings


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", nargs="?", type=Path, default=Path("dist"))
    args = parser.parse_args()

    findings = validate_target(args.target)
    if findings:
        print("Portia Issue #54 release/package validation failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    wheel = args.target / EXPECTED_WHEEL
    sdist = args.target / EXPECTED_SDIST
    print("Portia Issue #54 release/package validation passed")
    print(f"candidate wheel SHA-256 (NOT FINAL): {_sha256(wheel)}")
    print(f"candidate sdist SHA-256 (NOT FINAL): {_sha256(sdist)}")
    print("Candidate hashes are diagnostic only; Phase 2 must rebuild from exact qualified main.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
