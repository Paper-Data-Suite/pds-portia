"""Run isolated installed-wheel deep-workspace acceptance for Issue #92."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

CORE_064_FILENAME = "pds_core-0.6.4-py3-none-any.whl"
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
TARGET_DEEP_WORKSPACE_LENGTH = 119


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _authenticate_core(repository: Path, core_wheel: Path) -> None:
    if core_wheel.name != CORE_064_FILENAME:
        raise RuntimeError(
            "Issue #92 installed-wheel smoke requires released Core 0.6.4"
        )
    completed = _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    if "Verified official pds-core 0.6.4 wheel" not in completed.stdout:
        raise RuntimeError("Core 0.6.4 wheel verification did not complete")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    _authenticate_core(repository, core_wheel)

    code = r"""
import hashlib
import json
import shutil
import tempfile
from importlib import metadata
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.derived import DerivedStore
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.integrity import source_snapshot_digest
from portia.storage.io import read_bytes
from portia.storage.paths import (
    derived_data_path,
    derived_metadata_path,
    work_manifest_path,
    work_root,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.repository import PortiaRepository
from portia.storage.staging import cleanup_staged, publish_staged, stage_bytes

TARGET = 119
BASE = Path(tempfile.gettempdir()).resolve()
seed = hashlib.sha256(b"pds-portia-issue92-installed").hexdigest()[:16]
prefix = f"pds-portia-i92-installed-{seed}-"
desired = TARGET - len(str(BASE)) - 1
leaf = prefix + ("d" * max(0, desired - len(prefix)))
root = BASE / leaf
shutil.rmtree(root, ignore_errors=True)
root.mkdir(parents=True)

try:
    assert len(str(root.resolve())) >= TARGET

    assert metadata.version("pds-core") == "0.6.4"
    assert metadata.version("pds-portia") == "0.2.0"

    staged = stage_bytes(
        root,
        "op_issue92_installed",
        "step_issue92_installed",
        "portia/deep-qualification/artifact.json",
        b'{"installed":true}\n',
    )
    accepted = publish_staged(root, staged, action="exclusive_create")
    assert accepted == staged.fingerprint
    assert staged.destination_path.read_bytes() == b'{"installed":true}\n'
    cleanup_staged(root, staged)
    assert not staged.staging_path.exists()

    work = ExactPortiaWorkRef(
        class_id="class_deep",
        work_id="evt_deep",
        work_kind="event",
        contract_version="2",
    )
    agent = {"type": "system_process", "process_id": "issue92_installed"}

    def event(updated_at):
        return parse_portia_record(
            "event",
            "2",
            {
                "schema_version": "2",
                "record_type": "portia_work",
                "work_kind": "event",
                "module_id": "portia",
                "class_id": "class_deep",
                "work_id": "evt_deep",
                "school_year": "2026-2027",
                "status": "draft",
                "creation_source": {"type": "digital_entry"},
                "created_at": "2026-10-03T12:00:00-04:00",
                "created_by": agent,
                "updated_at": updated_at,
                "updated_by": agent,
            },
        )

    repository = PortiaRepository(root)
    created = repository.create_work(
        work,
        event("2026-10-03T12:00:00-04:00"),
    )
    replacement = event("2026-10-03T12:05:00-04:00")
    repository.replace_work(
        work,
        replacement,
        expected=created.fingerprint,
    )
    assert repository.load_work(work).record.to_dict() == replacement.to_dict()

    history = work_storage_history_path(
        root,
        work,
        "event",
        "evt_deep",
        created.fingerprint.digest,
    )
    assert history.is_file()
    assert len(history.name) == 40

    source_path = work_manifest_path(root, work)
    source_bytes = read_bytes(source_path)
    source_fp = fingerprint_bytes(source_bytes)
    scope = {"scope": "work", "work_ref": work.to_dict()}
    projection = "current_state_view"
    generation_id = "dgen_issue92_installed"
    data = {"qualified": True, "source": "installed-wheel"}
    data_fp = fingerprint_bytes(canonical_json_bytes(data))

    authorization = {
        "authorization_scope_id": "issue92_installed_complete",
        "coverage": "complete",
        "limitation_codes": [],
    }
    snapshot_value = {
        "schema_version": "1",
        "record_type": "source_snapshot",
        "module_id": "portia",
        "snapshot_algorithm": "portia_source_snapshot_v1",
        "projection_kind": projection,
        "projection_scope": scope,
        "authorization_scope": authorization,
        "discovery_roots": [workspace_relative(root, work_root(root, work))],
        "source_contracts": [
            {"contract_name": "event", "contract_version": "2"}
        ],
        "entries": [
            {
                "workspace_relative_path": workspace_relative(root, source_path),
                "byte_length": source_fp.byte_length,
                "sha256_digest": source_fp.digest,
                "source_role": "canonical_domain",
                "contract_or_artifact_kind": "event",
            }
        ],
        "source_snapshot_digest": "",
        "observed_at": "2026-10-03T12:06:00-04:00",
    }
    snapshot_value["source_snapshot_digest"] = source_snapshot_digest(snapshot_value)
    snapshot = parse_portia_record("source_snapshot", "1", snapshot_value)

    data_path = derived_data_path(
        root,
        projection,
        scope,
        generation_id,
    )
    metadata_record = parse_portia_record(
        "derived_index_metadata",
        "1",
        {
            "schema_version": "1",
            "record_type": "derived_index_metadata",
            "module_id": "portia",
            "generation_id": generation_id,
            "generation_state": "complete",
            "projection_kind": projection,
            "projection_scope": scope,
            "projection_contract_version": "1",
            "builder": {
                "builder_id": "issue92_installed_builder",
                "builder_version": "1",
            },
            "authorization_scope": authorization,
            "source_snapshot": snapshot.to_dict(),
            "data_artifact": {
                "workspace_relative_path": workspace_relative(root, data_path),
                "contract_version": "1",
                "fingerprint": data_fp.to_dict(),
            },
            "validation": {
                "schema_validation": "passed",
                "identity_validation": "passed",
                "reference_validation": "passed",
                "privacy_validation": "passed",
                "invariant_validation": "passed",
            },
            "generating_operation": {
                "operation_id": "op_issue92_installed",
                "journal_revision": 1,
                "contract_version": "2",
            },
            "generated_at": "2026-10-03T12:07:00-04:00",
        },
    )
    pointer = parse_portia_record(
        "derived_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "derived_current_pointer",
            "module_id": "portia",
            "projection_kind": projection,
            "projection_scope": scope,
            "generation_ref": {
                "generation_id": generation_id,
                "contract_version": "1",
            },
        },
    )

    store = DerivedStore(root)
    store.install(metadata_record, pointer, data)
    loaded = store.load_current(projection, scope, require_fresh=True)
    assert loaded.metadata.to_dict()["generation_id"] == generation_id

    metadata_path = derived_metadata_path(
        root,
        projection,
        scope,
        generation_id,
    )
    metadata_relative = workspace_relative(root, metadata_path)
    assert len(metadata_relative) == 115
    assert metadata_path.is_file()
    assert len(str(metadata_path)) >= 235

    print(
        json.dumps(
            {
                "core_version": metadata.version("pds-core"),
                "portia_version": metadata.version("pds-portia"),
                "workspace_length": len(str(root.resolve())),
                "history_leaf_length": len(history.name),
                "derived_metadata_relative_length": len(metadata_relative),
                "staging_publish_cleanup": True,
                "guarded_replace_history": True,
                "derived_install_reload": True,
            },
            sort_keys=True,
        )
    )
finally:
    shutil.rmtree(root, ignore_errors=True)
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue92-wheel-smoke-") as temp:
        root = Path(temp)
        environment = root / "venv"
        work = root / "work"
        work.mkdir()

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        _run(
            [str(python), "-m", "pip", "install", str(core_wheel.resolve())],
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
                str(portia_wheel.resolve()),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)

        installed_check = _run(
            [
                str(python),
                "-c",
                (
                    "import json,portia;"
                    "print(json.dumps({'path': portia.__path__[0]}))"
                ),
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(installed_check.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(
                f"smoke import resolved into source checkout: {installed}"
            )

        for relative in (
            "storage/generated_paths.py",
            "storage/paths.py",
            "storage/io.py",
            "storage/staging.py",
            "storage/repository.py",
            "storage/derived.py",
            "workflows/integrity.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #92 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("installed Issue #92 smoke produced no result")
        payload = json.loads(lines[-1])
        expected = {
            "core_version": "0.6.4",
            "portia_version": "0.2.0",
            "history_leaf_length": 40,
            "derived_metadata_relative_length": 115,
            "staging_publish_cleanup": True,
            "guarded_replace_history": True,
            "derived_install_reload": True,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(
                    f"installed Issue #92 smoke mismatch for {key}: {payload!r}"
                )
        if int(payload.get("workspace_length", 0)) < TARGET_DEEP_WORKSPACE_LENGTH:
            raise RuntimeError(
                f"installed Issue #92 workspace was not deep enough: {payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError, AssertionError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print("Portia installed-wheel Issue #92 deep-workspace smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
