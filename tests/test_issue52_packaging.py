from __future__ import annotations

import configparser
import hashlib
import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"


def _load_script(relative: str, name: str) -> ModuleType:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue52_package_checker_requires_runtime_and_exact_entry_points() -> None:
    module = _load_script(
        "scripts/check_issue52_package.py",
        "issue52_package_checker",
    )
    assert module._REQUIRED_RUNTIME == {
        "portia/pds_operations.py",
        "portia/attention_provider.py",
        "portia/readiness_provider.py",
        "portia/attention/actions.py",
    }
    content = """\
[console_scripts]
portia = portia.cli:main

[paper_data_suite.module_operations]
portia = portia.pds_operations:get_module_operations_profile
"""
    assert module._entry_point_findings(content) == []

    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(content)
    assert dict(parser.items("paper_data_suite.module_operations")) == {
        "portia": "portia.pds_operations:get_module_operations_profile"
    }


def test_issue52_checker_rejects_parallel_operations_entry_point() -> None:
    module = _load_script(
        "scripts/check_issue52_package.py",
        "issue52_package_checker_parallel",
    )
    content = """\
[console_scripts]
portia = portia.cli:main

[paper_data_suite.module_operations]
portia = portia.pds_operations:get_module_operations_profile
portia_attention = portia.attention_provider:evaluate_portia_attention
"""
    findings = module._entry_point_findings(content)
    assert findings
    assert "unexpected module-operations entry points" in findings[0]


def test_core_064_release_wheel_is_allowlisted_exactly() -> None:
    verifier = _load_script("scripts/verify_core_wheel.py", "issue52_core_verifier")
    assert verifier.KNOWN_WHEELS["pds_core-0.6.4-py3-none-any.whl"] == (
        "0.6.4",
        CORE_064_SHA256,
    )


def test_issue52_scripts_are_in_mypy_qualification() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    files = set(data["tool"]["mypy"]["files"])
    assert "scripts/check_issue52_package.py" in files
    assert "scripts/smoke_test_issue52_module_operations_wheel.py" in files


def test_release_digest_literal_has_expected_sha256_shape() -> None:
    assert len(CORE_064_SHA256) == 64
    int(CORE_064_SHA256, 16)
    assert hashlib.sha256(b"not-the-release-wheel").hexdigest() != CORE_064_SHA256
