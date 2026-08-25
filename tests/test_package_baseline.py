from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    return data["project"]


def test_package_metadata_baseline() -> None:
    project = _project()
    assert project["name"] == "pds-portia"
    assert project["requires-python"] == ">=3.11"
    assert project["dependencies"] == ["pds-core>=0.6,<0.7"]


def test_console_entry_point_is_bounded_to_portia_cli() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    assert data["project"]["scripts"] == {"portia": "portia.cli:main"}
    assert "entry-points" not in data["project"]


def test_py_typed_marker_exists() -> None:
    assert (ROOT / "portia" / "py.typed").is_file()


def test_ruff_scope_preserves_accepted_foundation_corpus() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    excluded = set(data["tool"]["ruff"]["extend-exclude"])
    assert "scripts/validate_portia_foundation.py" in excluded
    assert "tests/schema_validation" in excluded


def test_gitignore_excludes_local_and_build_state() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for expected in (".venv/", "dist/", "build/", "*.egg-info/"):
        assert expected in ignore


def test_help_and_status_do_not_mutate_working_directory(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    before = list(tmp_path.iterdir())
    for arguments in (["-m", "portia", "--help"], ["-m", "portia", "status"]):
        result = subprocess.run(
            [sys.executable, *arguments],
            cwd=tmp_path,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == before


def test_synthetic_data_policy_states_real_records_are_prohibited() -> None:
    policy = (ROOT / "docs" / "synthetic-data-policy.md").read_text(encoding="utf-8")
    assert "synthetic data only" in policy
    assert "Do not commit real or anonymized-from-real school records" in policy
