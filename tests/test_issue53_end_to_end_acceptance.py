from __future__ import annotations

import importlib.util
import os
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"


def _load_script():
    path = ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    spec = importlib.util.spec_from_file_location("issue53_end_to_end_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue53_foundation_pins_exact_current_artifact_boundary() -> None:
    smoke = _load_script()
    assert smoke.CORE_064_FILENAME == "pds_core-0.6.4-py3-none-any.whl"
    assert smoke.CORE_064_SHA256 == CORE_064_SHA256
    assert smoke.EXPECTED_CORE_VERSION == "0.6.4"
    assert smoke.EXPECTED_PORTIA_VERSION == "0.2.0"
    assert smoke.TARGET_DEEP_WORKSPACE_LENGTH == 119
    assert len(CORE_064_SHA256) == 64
    int(CORE_064_SHA256, 16)


def test_issue53_isolated_environment_removes_inherited_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke = _load_script()
    monkeypatch.setenv("PYTHONPATH", "source-shadow")
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", "implicit-workspace")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))

    scripts = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir(parents=True)
    profile = tmp_path / "profile"
    env = smoke._isolated_environment(
        user_home=profile,
        scripts_directory=scripts,
    )

    assert "PYTHONPATH" not in {key.upper() for key in env}
    assert "PDS_WORKSPACE_ROOT" not in {key.upper() for key in env}
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PIP_NO_INDEX"] == "1"
    assert Path(env["HOME"]) == profile
    assert Path(env["USERPROFILE"]) == profile
    assert Path(env["LOCALAPPDATA"]).is_dir()
    assert Path(env["APPDATA"]).is_dir()
    assert Path(env["XDG_CONFIG_HOME"]).is_dir()
    assert env["PATH"].split(os.pathsep)[0] == str(scripts)


def test_issue53_deep_workspace_helper_consumes_issue92_geometry(
    tmp_path: Path,
) -> None:
    smoke = _load_script()
    parent = tmp_path / "workspace-parent"
    parent.mkdir()
    workspace = smoke._deep_workspace_path(parent)

    assert workspace.parent == parent.resolve()
    assert workspace.name.startswith("pds-portia-i53-")
    assert len(str(workspace)) >= smoke.TARGET_DEEP_WORKSPACE_LENGTH


def test_issue53_foundation_probe_uses_public_core_workspace_service() -> None:
    smoke = _load_script()
    probe = smoke._FOUNDATION_PROBE
    assert "from pds_core.workspace import ensure_workspace_root" in probe
    assert "ensure_workspace_root(workspace, create=True)" in probe
    assert '"pds-core": metadata.version("pds-core")' in probe
    assert '"pds-portia": metadata.version("pds-portia")' in probe
    assert 'expected_pds = {"pds-core", "pds-portia"}' in probe


def test_issue53_foundation_reports_candidate_digest_without_rebuild() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert "candidate = _require_wheel(portia_wheel" in source
    assert "portia_digest = _sha256(candidate)" in source
    assert '"candidate_portia_sha256": portia_digest' in source
    assert '"--no-deps"' in source
    assert "str(candidate)" in source
    assert "python -m build" not in source


def test_issue53_smoke_script_is_in_strict_mypy_qualification() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    files = set(data["tool"]["mypy"]["files"])
    assert "scripts/smoke_test_issue53_end_to_end_wheel.py" in files


def test_issue53_core_setup_identifiers_match_representative_story() -> None:
    smoke = _load_script()
    assert smoke.SYNTHETIC_SCHOOL_YEAR == "2026-2027"
    assert smoke.PRIMARY_CLASS_ID == "eng10_p2_2026"
    assert smoke.SECONDARY_CLASS_ID == "journalism_p6_2026"
    assert smoke.COLLISION_STUDENT_ID == "student_shared_001"


def test_issue53_core_setup_probe_uses_public_core_authorities() -> None:
    smoke = _load_script()
    probe = smoke._CORE_SETUP_PROBE
    for marker in (
        "from pds_core.class_metadata import (",
        "create_class_metadata,",
        "write_class_metadata_for_class,",
        "from pds_core.classes import load_class_roster, write_class_roster",
        "from pds_core.rosters import create_roster, student_display_name",
        "from pds_core.school_years import get_active_school_year, open_school_year",
        "open_school_year(",
        "write_class_metadata_for_class(workspace, metadata_record)",
        "write_class_roster(workspace, primary_roster)",
        "write_class_roster(workspace, secondary_roster)",
    ):
        assert marker in probe


def test_issue53_core_setup_uses_portia_exact_class_qualified_identity() -> None:
    smoke = _load_script()
    probe = smoke._CORE_SETUP_PROBE
    for marker in (
        "from portia.identity.roster import CoreRosterResolver",
        "from portia.models.references import RosterStudentRef",
        "primary_ref = RosterStudentRef(",
        "secondary_ref = RosterStudentRef(",
        "resolver.resolve_reference(primary_ref)",
        "resolver.resolve_reference(secondary_ref)",
        "if primary_ref == secondary_ref:",
        "if primary_resolution.reference == secondary_resolution.reference:",
        "student_display_name(primary_student) != student_display_name(secondary_student)",
    ):
        assert marker in probe


def test_issue53_core_setup_extends_same_deep_workspace_after_foundation() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    foundation_index = source.index("foundation = _foundation_probe(")
    core_setup_index = source.index("core_setup = _core_setup_probe(")
    assert foundation_index < core_setup_index
    assert 'print("PASS Core setup")' in source
    assert '"active_school_year": core_setup["active_school_year"]' in source
    assert '"collision_reference_distinct": core_setup[' in source
