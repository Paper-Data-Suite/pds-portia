"""Issue #57 official Core 0.6.6 wheel authority and compatibility tests."""

from __future__ import annotations

import os
import tomllib
import zipfile
from pathlib import Path

import pytest

from scripts.verify_core_wheel import verify_wheel

ROOT = Path(__file__).resolve().parents[1]
CORE_066 = "pds_core-0.6.6-py3-none-any.whl"
SHA_066 = "d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301"


def _core_wheel() -> Path:
    provided = os.environ.get("PDS_CORE_066_WHEEL", "")
    if not provided:
        pytest.skip("PDS_CORE_066_WHEEL not supplied; Core 0.6.6 gate supplies it")
    return Path(provided)


def test_exact_authenticated_released_core_066_wheel() -> None:
    wheel = _core_wheel()
    assert wheel.name == CORE_066
    assert verify_wheel(wheel) == "0.6.6"
    import hashlib

    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == SHA_066
    with zipfile.ZipFile(wheel) as archive:
        assert "pds_core/local_open.py" in archive.namelist()
        assert "pds_core/route_registrations.py" in archive.namelist()
        assert "pds_core/pds2.py" in archive.namelist()


def test_tampered_wheel_must_fail_authentication(tmp_path: Path) -> None:
    wheel = _core_wheel()
    destination = tmp_path / CORE_066
    raw = wheel.read_bytes()
    destination.write_bytes(raw[:-1] + bytes([raw[-1] ^ 0x01]))
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        verify_wheel(destination)


def test_core_minimum_retained_for_older_compatible_releases() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    assert "pds-core>=0.6.3,<0.7" in dependencies
