from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repair_pip_residue.py"
SPEC = importlib.util.spec_from_file_location("repair_pip_residue", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def test_remove_residue_removes_only_interrupted_pip_paths(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    site_packages.mkdir()
    stale_package = site_packages / "~ip"
    stale_package.mkdir()
    (stale_package / "__init__.py").write_text("", encoding="utf-8")
    stale_metadata = site_packages / "~ip-26.2.1.dist-info"
    stale_metadata.mkdir()
    healthy_pip = site_packages / "pip"
    healthy_pip.mkdir()
    unrelated = site_packages / "~important"
    unrelated.mkdir()

    removed = repair.remove_residue(site_packages)

    assert removed == (stale_package, stale_metadata)
    assert not stale_package.exists()
    assert not stale_metadata.exists()
    assert healthy_pip.is_dir()
    assert unrelated.is_dir()


def test_residue_paths_returns_empty_for_missing_site_packages(tmp_path: Path) -> None:
    assert repair.residue_paths(tmp_path / "missing") == ()
