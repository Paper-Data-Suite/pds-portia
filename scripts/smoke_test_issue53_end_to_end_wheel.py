"""Establish isolated installed-wheel acceptance foundations for Issue #53.

Slice 1 owns the exact-artifact, environment-isolation, and deep-workspace
boundary. Later Issue #53 slices extend the installed probe with the continuous
production-service story while preserving this single environment and workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

CORE_064_FILENAME: Final[str] = "pds_core-0.6.4-py3-none-any.whl"
CORE_064_SHA256: Final[str] = (
    "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
)
EXPECTED_CORE_VERSION: Final[str] = "0.6.4"
EXPECTED_PORTIA_VERSION: Final[str] = "0.2.0"
TARGET_DEEP_WORKSPACE_LENGTH: Final[int] = 119
SYNTHETIC_SCHOOL_YEAR: Final[str] = "2026-2027"
PRIMARY_CLASS_ID: Final[str] = "eng10_p2_2026"
SECONDARY_CLASS_ID: Final[str] = "journalism_p6_2026"
COLLISION_STUDENT_ID: Final[str] = "student_shared_001"

_AUTHORITY_ENVIRONMENT_KEYS: Final[frozenset[str]] = frozenset(
    {"PYTHONPATH", "PDS_WORKSPACE_ROOT"}
)
_PDS_RUNTIME_DISTRIBUTIONS: Final[frozenset[str]] = frozenset(
    {
        "pds-core",
        "pds-portia",
        "pds-scoreform",
        "pds-quillan",
        "pds-concord",
        "pds-meridian",
        "pds-vitrine",
        "pds-paper-data-suite",
    }
)

_FOUNDATION_PROBE = r"""
import importlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path

from pds_core.workspace import ensure_workspace_root


def _inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


workspace = Path(sys.argv[1]).resolve()
environment = Path(sys.argv[2]).resolve()
repository = Path(sys.argv[3]).resolve()

if "PYTHONPATH" in {key.upper() for key in os.environ}:
    raise RuntimeError("PYTHONPATH leaked into Issue #53 installed acceptance")
if "PDS_WORKSPACE_ROOT" in {key.upper() for key in os.environ}:
    raise RuntimeError(
        "PDS_WORKSPACE_ROOT leaked into Issue #53 installed acceptance"
    )
if os.environ.get("PYTHONNOUSERSITE") != "1":
    raise RuntimeError("Issue #53 installed acceptance requires PYTHONNOUSERSITE=1")
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise RuntimeError(
        "Issue #53 installed acceptance requires PYTHONDONTWRITEBYTECODE=1"
    )

versions = {
    "pds-core": metadata.version("pds-core"),
    "pds-portia": metadata.version("pds-portia"),
}
if versions["pds-core"] != "0.6.4":
    raise RuntimeError("installed Core version does not match Issue #53 authority")
if versions["pds-portia"] != "0.2.0":
    raise RuntimeError("installed Portia version does not match Issue #53 candidate")

for import_name in ("pds_core", "portia"):
    module = importlib.import_module(import_name)
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        raise RuntimeError(f"{import_name} has no installed module file")
    resolved = Path(module_file).resolve()
    if not _inside(resolved, environment):
        raise RuntimeError(f"{import_name} import resolved outside the temporary venv")
    if _inside(resolved, repository):
        raise RuntimeError(f"{import_name} import resolved into the source checkout")

installed_pds = {
    (distribution.metadata.get("Name") or "").strip().lower()
    for distribution in metadata.distributions()
    if (distribution.metadata.get("Name") or "").strip().lower().startswith("pds-")
}
expected_pds = {"pds-core", "pds-portia"}
if installed_pds != expected_pds:
    raise RuntimeError(
        "Issue #53 isolated runtime contains unexpected PDS distributions"
    )

created = ensure_workspace_root(workspace, create=True).resolve()
if created != workspace:
    raise RuntimeError("Core normalized the Issue #53 workspace unexpectedly")
if len(str(created)) < 119:
    raise RuntimeError("Issue #53 workspace did not meet deep-path geometry")
if not (created / ".pds" / "workspace.json").is_file():
    raise RuntimeError("Core workspace marker was not created")

print(
    json.dumps(
        {
            "core_version": versions["pds-core"],
            "portia_version": versions["pds-portia"],
            "workspace_length": len(str(created)),
            "workspace_marker": True,
            "pds_runtime_distributions": sorted(installed_pds),
        },
        sort_keys=True,
    )
)
"""


_CORE_SETUP_PROBE = r"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pds_core.class_metadata import (
    create_class_metadata,
    load_class_metadata_for_class,
    write_class_metadata_for_class,
)
from pds_core.classes import load_class_roster, write_class_roster
from pds_core.rosters import create_roster, student_display_name
from pds_core.school_years import get_active_school_year, open_school_year

from portia.identity.roster import CoreRosterResolver
from portia.models.references import RosterStudentRef


SCHOOL_YEAR = "2026-2027"
PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
CREATED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

workspace = Path(sys.argv[1]).resolve()

opened = open_school_year(
    workspace,
    SCHOOL_YEAR,
    opened_at=CREATED_AT,
)
if opened.active_school_year != SCHOOL_YEAR or opened.closed_at is not None:
    raise RuntimeError("Core active school-year state did not open as expected")
if get_active_school_year(workspace) != SCHOOL_YEAR:
    raise RuntimeError("Core active school-year lookup disagrees with written state")

for class_id in (PRIMARY_CLASS_ID, SECONDARY_CLASS_ID):
    metadata_record = create_class_metadata(
        class_id,
        SCHOOL_YEAR,
        created_at=CREATED_AT,
    )
    write_class_metadata_for_class(workspace, metadata_record)

primary_roster = create_roster(
    PRIMARY_CLASS_ID,
    (
        {
            "student_id": COLLISION_STUDENT_ID,
            "last_name": "Synthetic",
            "first_name": "Shared",
            "period": "2",
        },
        {
            "student_id": "student_primary_002",
            "last_name": "Synthetic",
            "first_name": "Primary",
            "period": "2",
        },
    ),
)
secondary_roster = create_roster(
    SECONDARY_CLASS_ID,
    (
        {
            "student_id": COLLISION_STUDENT_ID,
            "last_name": "Synthetic",
            "first_name": "Shared",
            "period": "6",
        },
        {
            "student_id": "student_secondary_002",
            "last_name": "Synthetic",
            "first_name": "Secondary",
            "period": "6",
        },
    ),
)

write_class_roster(workspace, primary_roster)
write_class_roster(workspace, secondary_roster)

primary_metadata = load_class_metadata_for_class(workspace, PRIMARY_CLASS_ID)
secondary_metadata = load_class_metadata_for_class(workspace, SECONDARY_CLASS_ID)
if primary_metadata.school_year != SCHOOL_YEAR:
    raise RuntimeError("primary class metadata lost the active school year")
if secondary_metadata.school_year != SCHOOL_YEAR:
    raise RuntimeError("secondary class metadata lost the active school year")

loaded_primary = load_class_roster(workspace, PRIMARY_CLASS_ID)
loaded_secondary = load_class_roster(workspace, SECONDARY_CLASS_ID)
if loaded_primary.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("primary Core roster reloaded under the wrong class")
if loaded_secondary.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("secondary Core roster reloaded under the wrong class")

primary_ref = RosterStudentRef(
    class_id=PRIMARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)
secondary_ref = RosterStudentRef(
    class_id=SECONDARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)
if primary_ref == secondary_ref:
    raise RuntimeError("Portia collapsed distinct class-qualified roster references")

resolver = CoreRosterResolver(workspace)
primary_resolution = resolver.resolve_reference(primary_ref)
secondary_resolution = resolver.resolve_reference(secondary_ref)

if primary_resolution.reference != primary_ref:
    raise RuntimeError("primary Portia roster resolution changed exact identity")
if secondary_resolution.reference != secondary_ref:
    raise RuntimeError("secondary Portia roster resolution changed exact identity")
if primary_resolution.reference == secondary_resolution.reference:
    raise RuntimeError("Portia resolver merged cross-class roster identities")

primary_student = primary_resolution.student
secondary_student = secondary_resolution.student
if primary_student.student_id != secondary_student.student_id:
    raise RuntimeError("synthetic collision no longer shares the local student_id")
if primary_student.class_id == secondary_student.class_id:
    raise RuntimeError("synthetic collision no longer spans distinct Core classes")
if student_display_name(primary_student) != student_display_name(secondary_student):
    raise RuntimeError("synthetic collision no longer shares the display name")
if primary_student == secondary_student:
    raise RuntimeError("class-qualified Core student records were merged")

print(
    json.dumps(
        {
            "active_school_year": get_active_school_year(workspace),
            "class_count": 2,
            "roster_count": 2,
            "primary_roster_count": len(loaded_primary.students),
            "secondary_roster_count": len(loaded_secondary.students),
            "collision_local_student_id_equal": (
                primary_student.student_id == secondary_student.student_id
            ),
            "collision_display_name_equal": (
                student_display_name(primary_student)
                == student_display_name(secondary_student)
            ),
            "collision_reference_distinct": primary_ref != secondary_ref,
            "resolver_reference_distinct": (
                primary_resolution.reference != secondary_resolution.reference
            ),
        },
        sort_keys=True,
    )
)
"""

class Issue53AcceptanceError(RuntimeError):
    """Raised when the representative installed acceptance boundary fails."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise Issue53AcceptanceError(
            f"installed acceptance command failed with exit code {result.returncode}"
        )
    return result


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _require_wheel(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise Issue53AcceptanceError(f"{label} wheel is unavailable")
    if resolved.suffix.lower() != ".whl":
        raise Issue53AcceptanceError(f"{label} artifact must be a wheel")
    return resolved


def _authenticate_core(repository: Path, core_wheel: Path) -> str:
    if core_wheel.name != CORE_064_FILENAME:
        raise Issue53AcceptanceError(
            "Issue #53 requires the exact released Core 0.6.4 wheel filename"
        )
    digest = _sha256(core_wheel)
    if digest != CORE_064_SHA256:
        raise Issue53AcceptanceError(
            "Issue #53 Core 0.6.4 wheel SHA-256 does not match release authority"
        )
    _run(
        [
            sys.executable,
            str(repository / "scripts" / "verify_core_wheel.py"),
            str(core_wheel),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    return digest


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _console_path(python: Path) -> Path:
    return python.parent / ("portia.exe" if os.name == "nt" else "portia")


def _isolated_environment(
    *,
    user_home: Path,
    scripts_directory: Path,
) -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key.upper() in _AUTHORITY_ENVIRONMENT_KEYS:
            env.pop(key, None)

    user_home.mkdir(parents=True, exist_ok=True)
    local_app_data = user_home / "AppData" / "Local"
    roaming_app_data = user_home / "AppData" / "Roaming"
    xdg_config = user_home / ".config"
    for directory in (local_app_data, roaming_app_data, xdg_config):
        directory.mkdir(parents=True, exist_ok=True)

    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["HOME"] = str(user_home)
    env["USERPROFILE"] = str(user_home)
    env["LOCALAPPDATA"] = str(local_app_data)
    env["APPDATA"] = str(roaming_app_data)
    env["XDG_CONFIG_HOME"] = str(xdg_config)

    existing_path = env.get("PATH", "")
    env["PATH"] = (
        f"{scripts_directory}{os.pathsep}{existing_path}"
        if existing_path
        else str(scripts_directory)
    )
    return env


def _deep_workspace_path(parent: Path) -> Path:
    resolved_parent = parent.resolve()
    prefix = "pds-portia-i53-"
    desired_leaf_length = max(
        len(prefix),
        TARGET_DEEP_WORKSPACE_LENGTH - len(str(resolved_parent)) - 1,
    )
    leaf = prefix + ("d" * (desired_leaf_length - len(prefix)))
    workspace = resolved_parent / leaf
    if len(str(workspace)) < TARGET_DEEP_WORKSPACE_LENGTH:
        raise Issue53AcceptanceError(
            "could not construct the Issue #53 deep workspace geometry"
        )
    return workspace


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _assert_isolated_working_directory(
    work: Path,
    *,
    repository: Path,
    workspace: Path,
    artifact_directories: Sequence[Path],
) -> None:
    if tuple(work.iterdir()):
        raise Issue53AcceptanceError(
            "Issue #53 acceptance working directory must start empty"
        )
    forbidden = (repository, workspace, *artifact_directories)
    if any(_is_within(work, root) for root in forbidden):
        raise Issue53AcceptanceError(
            "Issue #53 acceptance working directory is not isolated"
        )


def _assert_launcher_reachable(
    python: Path,
    *,
    env: Mapping[str, str],
) -> None:
    launcher = _console_path(python)
    if not launcher.is_file():
        raise Issue53AcceptanceError(
            "installed Portia console launcher is missing from the temporary venv"
        )
    found = shutil.which("portia", path=env.get("PATH"))
    if found is None:
        raise Issue53AcceptanceError(
            "installed Portia console launcher is not reachable on isolated PATH"
        )
    if Path(found).resolve() != launcher.resolve():
        raise Issue53AcceptanceError(
            "isolated PATH resolved a different Portia console launcher"
        )


def _foundation_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
    environment: Path,
    repository: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _FOUNDATION_PROBE,
            str(workspace),
            str(environment),
            str(repository),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe result was not an object"
        )
    payload = cast(dict[str, object], payload_raw)
    expected = {
        "core_version": EXPECTED_CORE_VERSION,
        "portia_version": EXPECTED_PORTIA_VERSION,
        "workspace_marker": True,
        "pds_runtime_distributions": ["pds-core", "pds-portia"],
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed foundation mismatch for {key}"
            )
    workspace_length = payload.get("workspace_length")
    if (
        not isinstance(workspace_length, int)
        or workspace_length < TARGET_DEEP_WORKSPACE_LENGTH
    ):
        raise Issue53AcceptanceError(
            "Issue #53 installed workspace did not meet deep-path geometry"
        )
    return payload


def _core_setup_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _CORE_SETUP_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "active_school_year": SYNTHETIC_SCHOOL_YEAR,
        "class_count": 2,
        "roster_count": 2,
        "primary_roster_count": 2,
        "secondary_roster_count": 2,
        "collision_local_student_id_equal": True,
        "collision_display_name_equal": True,
        "collision_reference_distinct": True,
        "resolver_reference_distinct": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Core setup mismatch for {key}"
            )
    return payload

def smoke(portia_wheel: Path, core_wheel: Path) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    candidate = _require_wheel(portia_wheel, label="Portia candidate")
    core = _require_wheel(core_wheel, label="Core")
    core_digest = _authenticate_core(repository, core)
    portia_digest = _sha256(candidate)

    with tempfile.TemporaryDirectory(prefix="pds-portia-issue53-") as temp:
        root = Path(temp).resolve()
        environment = root / "venv"
        work = root / "run"
        user_home = root / "profile"
        workspace_parent = root / "workspace-parent"
        work.mkdir()
        workspace_parent.mkdir()
        workspace = _deep_workspace_path(workspace_parent)

        _assert_isolated_working_directory(
            work,
            repository=repository,
            workspace=workspace,
            artifact_directories=(candidate.parent, core.parent),
        )

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = _isolated_environment(
            user_home=user_home,
            scripts_directory=python.parent,
        )

        _run(
            [str(python), "-m", "pip", "install", str(core)],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(candidate),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        _assert_launcher_reachable(python, env=env)

        foundation = _foundation_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
            environment=environment,
            repository=repository,
        )
        core_setup = _core_setup_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        if tuple(work.iterdir()):
            raise Issue53AcceptanceError(
                "Issue #53 acceptance polluted its empty working directory"
            )

        print("PASS install")
        print("PASS deep workspace")
        print("PASS Core setup")

        return {
            "candidate_portia_wheel": candidate.name,
            "candidate_portia_sha256": portia_digest,
            "core_wheel": core.name,
            "core_sha256": core_digest,
            "core_version": foundation["core_version"],
            "portia_version": foundation["portia_version"],
            "workspace_length": foundation["workspace_length"],
            "active_school_year": core_setup["active_school_year"],
            "class_count": core_setup["class_count"],
            "roster_count": core_setup["roster_count"],
            "collision_reference_distinct": core_setup[
                "collision_reference_distinct"
            ],
            "resolver_reference_distinct": core_setup[
                "resolver_reference_distinct"
            ],
            "launcher_reachable": True,
            "pip_check": "clean",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()

    try:
        evidence = smoke(args.portia_wheel, args.core_wheel)
    except (
        Issue53AcceptanceError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"ERROR Issue #53 foundation: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(evidence, sort_keys=True))
    print("Portia Issue #53 installed acceptance foundation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
