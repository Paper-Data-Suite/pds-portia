"""Authenticate supported pds-core wheels and installed Core metadata."""

from __future__ import annotations

import argparse
import email
import hashlib
import sys
import zipfile
from importlib import metadata
from pathlib import Path

KNOWN_WHEELS = {
    "pds_core-0.6.0-py3-none-any.whl": (
        "0.6.0",
        "be28c061b38463ef59ebc328ed1aa443767fe7f2c626babb769c2d8e5932f308",
    ),
    "pds_core-0.6.3-py3-none-any.whl": (
        "0.6.3",
        "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_wheel(path: Path) -> str:
    """Verify an allowlisted official Core wheel and return its version."""

    expected = KNOWN_WHEELS.get(path.name)
    if expected is None:
        supported = ", ".join(sorted(KNOWN_WHEELS))
        raise ValueError(f"unsupported Core wheel {path.name!r}; expected one of: {supported}")

    expected_version, expected_digest = expected
    actual_digest = _sha256(path)
    if actual_digest != expected_digest:
        raise ValueError(
            f"Core wheel SHA-256 mismatch for {path.name}: "
            f"expected {expected_digest}, found {actual_digest}"
        )

    with zipfile.ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError(f"corrupt Core wheel member: {corrupt}")
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError("Core wheel must contain exactly one METADATA file")
        message = email.message_from_bytes(archive.read(metadata_names[0]))

    if message.get("Name") != "pds-core":
        raise ValueError(f"unexpected Core distribution name: {message.get('Name')!r}")
    if message.get("Version") != expected_version:
        raise ValueError(
            f"unexpected Core version: expected {expected_version}, "
            f"found {message.get('Version')!r}"
        )
    if message.get("Requires-Python") != ">=3.11":
        raise ValueError(
            f"unexpected Core Requires-Python: {message.get('Requires-Python')!r}"
        )
    return expected_version


def verify_installed(expected_version: str | None) -> str:
    """Verify installed Core distribution metadata."""

    try:
        installed = metadata.version("pds-core")
    except metadata.PackageNotFoundError as exc:
        raise ValueError("pds-core is not installed") from exc
    if expected_version is not None and installed != expected_version:
        raise ValueError(
            f"installed Core version mismatch: expected {expected_version}, found {installed}"
        )
    return installed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", nargs="?", type=Path)
    parser.add_argument(
        "--installed",
        nargs="?",
        const="",
        metavar="VERSION",
        help="verify installed pds-core, optionally requiring VERSION",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.installed is not None:
            if args.wheel is not None:
                raise ValueError("provide either a wheel path or --installed, not both")
            expected = args.installed or None
            version = verify_installed(expected)
            print(f"Verified installed pds-core {version}")
            return 0
        if args.wheel is None:
            raise ValueError("a Core wheel path or --installed is required")
        version = verify_wheel(args.wheel)
        print(f"Verified official pds-core {version} wheel: {args.wheel}")
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"Core verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
