"""Run the complete Issue #36 Portia repository qualification."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], root: Path) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=root, check=True)


def _clean_build_artifacts(root: Path) -> None:
    for relative in ("build", "dist", "pds_portia.egg-info"):
        target = root / relative
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()


def _core_version_from_wheel(core_wheel: Path) -> str:
    name = core_wheel.name
    prefix = "pds_core-"
    suffix = "-py3-none-any.whl"
    if not name.startswith(prefix) or not name.endswith(suffix):
        raise ValueError(f"unexpected Core wheel filename: {name}")
    version = name[len(prefix) : -len(suffix)]
    if not version:
        raise ValueError(f"Core wheel filename has no version: {name}")
    return version


def qualify(root: Path, core_wheel: Path) -> None:
    _run(
        [sys.executable, "scripts/verify_core_wheel.py", str(core_wheel.resolve())],
        root,
    )
    expected_core_version = _core_version_from_wheel(core_wheel)
    _run(
        [
            sys.executable,
            "scripts/verify_core_wheel.py",
            "--installed",
            expected_core_version,
        ],
        root,
    )

    _run([sys.executable, "scripts/validate_portia_foundation.py"], root)
    _run([sys.executable, "-m", "pytest"], root)
    _run([sys.executable, "-m", "ruff", "check", "."], root)
    _run([sys.executable, "-m", "mypy"], root)
    _run([sys.executable, "-m", "pip", "check"], root)

    _clean_build_artifacts(root)
    _run([sys.executable, "-m", "build"], root)
    artifacts = sorted((root / "dist").iterdir())
    if not artifacts:
        raise RuntimeError("build produced no distribution artifacts")
    _run(
        [sys.executable, "-m", "twine", "check", *[str(path) for path in artifacts]],
        root,
    )
    _run([sys.executable, "scripts/check_package.py", "dist"], root)

    wheels = sorted((root / "dist").glob("pds_portia-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected exactly one Portia wheel, found: {wheels}")
    _run(
        [
            sys.executable,
            "scripts/smoke_test_wheel.py",
            str(wheels[0]),
            str(core_wheel.resolve()),
        ],
        root,
    )
    if (root / ".git").exists():
        _run(["git", "diff", "--check"], root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-wheel", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        qualify(root, args.core_wheel)
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Repository qualification failed: {exc}", file=sys.stderr)
        return 1
    print("Portia Issue #36 repository qualification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
