"""Smoke Account/Observation workflows from an isolated installed Portia wheel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    if "0.6.3" not in core_wheel.name:
        raise RuntimeError("Issue #41 installed-wheel smoke requires Core 0.6.3")

    code = r'''
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    AccountWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    ParticipantWorkflowService,
    account_reference,
    observation_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-evidence"))
agent = {"type": "system_process", "process_id": "wheel_evidence_smoke"}
timestamp = "2026-08-28T10:00:00-04:00"
work = ExactPortiaWorkRef(
    class_id="class_evidence_smoke",
    work_id="evt_evidence_smoke",
    work_kind="event",
    contract_version="2",
)

event = parse_portia_record("event", "2", {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_evidence_smoke",
    "work_id": "evt_evidence_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "occurrence": {"precision": "exact", "started_at": timestamp},
    "summary": "Synthetic evidence smoke context.",
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
EventWorkflowService(workspace).create(event)

participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_evidence_smoke",
    "work_id": "evt_evidence_smoke",
    "participant_id": "ep_evidence_smoke",
    "status": "active",
    "subject": {"kind": "unknown_person", "reason": "identity_not_known"},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
ParticipantWorkflowService(workspace).create(work, participant)

target = {
    "kind": "event_participant",
    "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_evidence_smoke",
        "contract_version": "3",
    },
}
account = parse_portia_record("account", "2", {
    "schema_version": "2",
    "record_type": "account",
    "module_id": "portia",
    "class_id": "class_evidence_smoke",
    "work_kind": "event",
    "work_id": "evt_evidence_smoke",
    "account_id": "acct_evidence_smoke",
    "status": "active",
    "target": target,
    "source": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
    "information_origin": "firsthand",
    "source_certainty": "stated_certain",
    "content": [{
        "representation": "recorded_summary",
        "text": "Synthetic source contribution for installed-wheel smoke.",
    }],
    "provided_time": {"precision": "exact", "at": timestamp},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
observation = parse_portia_record("observation", "2", {
    "schema_version": "2",
    "record_type": "observation",
    "module_id": "portia",
    "class_id": "class_evidence_smoke",
    "work_kind": "event",
    "work_id": "evt_evidence_smoke",
    "observation_id": "obs_evidence_smoke",
    "status": "active",
    "target": target,
    "observer": {
        "kind": "human",
        "human_attribution": {
            "kind": "local_operator",
            "display_label": "Synthetic Teacher",
        },
    },
    "method": "manual_count",
    "content": {
        "measurements": [{"measure_type": "count", "value": 2, "unit": "count"}]
    },
    "observation_time": {"precision": "exact", "at": timestamp},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})

accounts = AccountWorkflowService(workspace)
observations = ObservationWorkflowService(workspace)
accounts.create(work, account)
observations.create(work, observation)

account_current = accounts.require_current_use(
    account_reference(work, "acct_evidence_smoke")
)
observation_current = observations.require_current_use(
    observation_reference(work, "obs_evidence_smoke")
)
assert account_current.record.contract_version == "2"
assert observation_current.record.contract_version == "2"
assert accounts.load_exact(account_reference(work, "acct_evidence_smoke")).record.logical_id == "acct_evidence_smoke"
assert observations.load_exact(observation_reference(work, "obs_evidence_smoke")).record.logical_id == "obs_evidence_smoke"
assert [item.record.logical_id for item in accounts.list(work)] == ["acct_evidence_smoke"]
assert [item.record.logical_id for item in observations.list(work)] == ["obs_evidence_smoke"]

records_root = workspace / "classes/class_evidence_smoke/modules/portia/work/evt_evidence_smoke/records"
assert (records_root / "account/acct_evidence_smoke.json").is_file()
assert (records_root / "observation/obs_evidence_smoke.json").is_file()
for absent in ("review", "classification", "hypothesis", "determination"):
    assert not (records_root / absent).exists()

print(json.dumps({
    "account": account_current.record.logical_id,
    "observation": observation_current.record.logical_id,
    "account_version": account_current.record.contract_version,
    "observation_version": observation_current.record.contract_version,
}))
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue41-wheel-smoke-") as temporary:
        root = Path(temporary)
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
            [str(python), "-m", "pip", "install", "--no-deps", str(portia_wheel.resolve())],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        package = _run(
            [
                str(python),
                "-c",
                "import json,portia; print(json.dumps({'path': portia.__path__[0]}))",
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(f"smoke import resolved into source checkout: {installed}")
        for relative in (
            "workflows/accounts.py",
            "workflows/observations.py",
            "workflows/evidence_lifecycle.py",
            "workflows/evidence_artifacts.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(f"installed Portia wheel is missing Issue #41 file: {relative}")

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected = {
            "account": "acct_evidence_smoke",
            "observation": "obs_evidence_smoke",
            "account_version": "2",
            "observation_version": "2",
        }
        if payload != expected:
            raise RuntimeError(f"unexpected Issue #41 evidence smoke result: {payload!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Issue #41 wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #41 evidence smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
