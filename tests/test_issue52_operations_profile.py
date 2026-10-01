from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    ModuleAttentionReport,
    ModuleOperationsRequest,
    ModuleReadinessReport,
    validate_module_operations_profile,
)

import portia.pds_operations as operations
from portia.pds_operations import (
    PORTIA_MODULE_ID,
    evaluate_portia_attention,
    evaluate_portia_readiness,
    get_module_operations_profile,
)

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)


def test_issue52_profile_is_valid_core_v1_profile() -> None:
    profile = get_module_operations_profile()

    assert validate_module_operations_profile(profile) == profile
    assert PORTIA_MODULE_ID == "portia"
    assert profile.module_id == PORTIA_MODULE_ID
    assert profile.supported_core_operations_contract_versions == frozenset(
        {MODULE_OPERATIONS_CONTRACT_VERSION}
    )
    assert profile.attention_provider is evaluate_portia_attention
    assert profile.readiness_provider is evaluate_portia_readiness


def test_issue52_pyproject_registers_exactly_one_portia_operations_provider() -> None:
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    entry_points = project["entry-points"]
    assert isinstance(entry_points, dict)

    operations_group = entry_points["paper_data_suite.module_operations"]
    assert operations_group == {
        "portia": "portia.pds_operations:get_module_operations_profile"
    }

    for forbidden_group in (
        "paper_data_suite.portia_operations",
        "paper_data_suite.portia_attention",
        "paper_data_suite.portia_readiness",
    ):
        assert forbidden_group not in entry_points


def test_issue52_foundation_preserves_launcher_and_core_dependency_floor() -> None:
    project = _pyproject()["project"]
    assert isinstance(project, dict)

    scripts = project["scripts"]
    assert scripts == {"portia": "portia.cli:main"}

    dependencies = project["dependencies"]
    assert isinstance(dependencies, list)
    assert "pds-core>=0.6.3,<0.7" in dependencies
    for sibling in (
        "pds-concord",
        "pds-meridian",
        "pds-quillan",
        "pds-scoreform",
        "pds-vitrine",
        "paper-data-suite",
    ):
        assert not any(sibling in item.casefold() for item in dependencies)


def test_issue52_profile_loading_is_metadata_safe(tmp_path: Path) -> None:
    workspace = tmp_path / "must-not-be-created"
    script = r"""
import json
import sys
from portia.pds_operations import get_module_operations_profile

profile = get_module_operations_profile()
print(json.dumps({
    "module_id": profile.module_id,
    "attention_callable": callable(profile.attention_provider),
    "readiness_callable": callable(profile.readiness_provider),
    "attention_impl_imported": "portia.attention_provider" in sys.modules,
    "readiness_impl_imported": "portia.readiness_provider" in sys.modules,
    "menu_imported": any(name.startswith("portia.menu") for name in sys.modules),
    "storage_imported": any(name.startswith("portia.storage") for name in sys.modules),
    "exports_imported": any(name.startswith("portia.exports") for name in sys.modules),
}))
"""
    environment = os.environ.copy()
    environment["PDS_WORKSPACE_ROOT"] = str(workspace)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "module_id": "portia",
        "attention_callable": True,
        "readiness_callable": True,
        "attention_impl_imported": False,
        "readiness_impl_imported": False,
        "menu_imported": False,
        "storage_imported": False,
        "exports_imported": False,
    }
    assert not workspace.exists()


def test_issue52_attention_seam_imports_only_on_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ModuleOperationsRequest()
    expected = ModuleAttentionReport(evaluation="evaluated")
    imported: list[str] = []

    def fake_import(name: str) -> object:
        imported.append(name)
        return SimpleNamespace(evaluate_portia_attention=lambda received: expected)

    monkeypatch.setattr(operations, "import_module", fake_import)

    assert evaluate_portia_attention(request) is expected
    assert imported == ["portia.attention_provider"]


def test_issue52_readiness_seam_imports_only_on_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ModuleOperationsRequest()
    expected = ModuleReadinessReport(evaluation="evaluated", ready=True)
    imported: list[str] = []

    def fake_import(name: str) -> object:
        imported.append(name)
        return SimpleNamespace(evaluate_portia_readiness=lambda received: expected)

    monkeypatch.setattr(operations, "import_module", fake_import)

    assert evaluate_portia_readiness(request) is expected
    assert imported == ["portia.readiness_provider"]
