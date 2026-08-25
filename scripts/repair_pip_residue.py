"""Remove pip's interrupted-upgrade residue from the active virtual environment."""

from __future__ import annotations

import shutil
import sys
import sysconfig
from pathlib import Path


def residue_paths(site_packages: Path) -> tuple[Path, ...]:
    """Return pip temporary rename artifacts created by interrupted upgrades."""

    if not site_packages.is_dir():
        return ()
    return tuple(sorted(site_packages.glob("~ip*")))


def remove_residue(site_packages: Path) -> tuple[Path, ...]:
    """Remove only pip's ``~ip*`` temporary artifacts from site-packages."""

    removed: list[Path] = []
    for path in residue_paths(site_packages):
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            raise RuntimeError(f"unsupported pip residue path type: {path}")
        removed.append(path)
    return tuple(removed)


def active_site_packages() -> Path:
    """Locate site-packages for the interpreter executing this helper."""

    if sys.prefix == sys.base_prefix:
        raise RuntimeError("pip residue repair must run inside a virtual environment")
    purelib = sysconfig.get_path("purelib")
    if not purelib:
        raise RuntimeError("could not resolve virtual-environment site-packages")
    return Path(purelib).resolve()


def main() -> int:
    site_packages = active_site_packages()
    removed = remove_residue(site_packages)
    for path in removed:
        print(f"Removed interrupted pip-upgrade residue: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
