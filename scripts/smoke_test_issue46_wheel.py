"""Smoke Issue #46 downstream workflows from an installed Portia wheel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


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
        text=True,
        capture_output=True,
        check=True,
    )


def _venv_python(environment: Path) -> Path:
    return environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _authenticate_core(repository: Path, core_wheel: Path) -> None:
    if core_wheel.name != "pds_core-0.6.3-py3-none-any.whl":
        raise RuntimeError(
            "Issue #46 installed-wheel smoke requires the Core 0.6.3 wheel"
        )
    _run(
        [
            sys.executable,
            str(repository / "scripts/verify_core_wheel.py"),
            str(core_wheel.resolve()),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    _authenticate_core(repository, core_wheel)
    scenario_root = repository / "tests" / "fixtures" / "issue_22" / "positive"
    if not scenario_root.is_dir():
        raise RuntimeError(f"missing Issue #22 representative corpus: {scenario_root}")

    code = r"""
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from portia.identity.roster import ResolvedRosterStudent
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.validation import KnownValidationContext
from portia.workflows import (
    FidelityWorkflowService,
    FollowUpWorkflowService,
    ImplementationWorkflowService,
    OutcomeWorkflowService,
    ReentryWorkflowService,
    RepairWorkflowService,
    SupportProcessWorkflowService,
    follow_up_reference,
    outcome_reference,
    reentry_reference,
    repair_reference,
)
from portia.workflows.context import AuthoritativeWorkflowContext, roster_references

SCENARIO_ROOT = Path(sys.argv[1])


class RepresentativeRosters:
    def resolve_reference(self, reference):
        del reference
        return cast(ResolvedRosterStudent, object())


class RepresentativeActors:
    def load_actor(self, reference, *, require_current_use=False):
        del reference, require_current_use
        return cast(StoredRecord, object())


class RepresentativeContext:
    def __init__(self):
        self.rosters = RepresentativeRosters()
        self.actors = RepresentativeActors()

    def assemble(self, records, *, require_actor_current_use=False):
        del require_actor_current_use
        references = roster_references(records)
        return AuthoritativeWorkflowContext(
            validation=KnownValidationContext.from_values(
                roster_students=references,
                core_works=None,
            ),
            roster_students=(),
            actors=(),
        )


def load_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(path)
    return value


def entries(scenario):
    records = scenario["records"]
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise AssertionError("scenario records")
    return tuple(records)


def entry(scenario, *, filename=None, contract=None):
    matches = tuple(
        item
        for item in entries(scenario)
        if (filename is None or item["fixture_path"] == filename)
        and (contract is None or item["contract"] == contract)
    )
    if len(matches) != 1:
        raise AssertionError((filename, contract, len(matches)))
    return matches[0]


def contract_entries(scenario, contract):
    return tuple(item for item in entries(scenario) if item["contract"] == contract)


def owner_work(item):
    owner = item["owner"]
    if not isinstance(owner, Mapping):
        raise AssertionError("owner")
    work_kind = str(owner["work_kind"])
    return ExactPortiaWorkRef(
        class_id=str(owner["class_id"]),
        work_id=str(owner["work_id"]),
        work_kind=work_kind,
        contract_version="2" if work_kind == "event" else "1",
    )


def record_ref(item, record):
    logical_id = record.logical_id
    if logical_id is None:
        raise AssertionError("logical id")
    return ExactPortiaWorkRecordRef(
        work_ref=owner_work(item),
        record_ref=ExactLocalRecordRef(
            record_kind=str(item["contract"]),
            record_id=logical_id,
            contract_version=str(item["version"]),
        ),
    )


def seed(name, workspace):
    fixture_root = SCENARIO_ROOT / name
    scenario = load_json(fixture_root / "scenario.json")
    repository = PortiaRepository(workspace)
    records = {}
    for item in entries(scenario):
        if item.get("authority") != "portia":
            continue
        filename = str(item["fixture_path"])
        wire = load_json(fixture_root / filename)
        contract = str(item["contract"])
        version = str(item["version"])
        record = parse_portia_record(contract, version, wire)
        work = owner_work(item)
        if wire.get("record_type") == "portia_work":
            repository.create_work(work, record)
        else:
            repository.create_work_record(work, record)
        records[filename] = record
    return repository, RepresentativeContext(), scenario, records


def kwargs(repository, context):
    return {"repository": repository, "context_assembler": context}


def all_keys(value):
    found = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                found.add(key)
            found.update(all_keys(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            found.update(all_keys(child))
    return found


workspace_08 = Path("synthetic-workspace-issue46-p22-08")
repo_08, context_08, scenario_08, records_08 = seed(
    "p22_08_support_positive_outcome", workspace_08
)
service_kwargs_08 = kwargs(repo_08, context_08)
work_08 = owner_work(entry(scenario_08, filename="support-process.json"))
root_before = repo_08.load_work(work_08).record.to_dict()
SupportProcessWorkflowService(workspace_08, **service_kwargs_08).require_current_use(work_08)

implementations = ImplementationWorkflowService(workspace_08, **service_kwargs_08)
for item in contract_entries(scenario_08, "implementation"):
    record = records_08[str(item["fixture_path"])]
    implementations.require_current_use(record_ref(item, record))

fidelity_item = entry(scenario_08, contract="fidelity")
fidelity_record = records_08[str(fidelity_item["fixture_path"])]
FidelityWorkflowService(workspace_08, **service_kwargs_08).require_current_use(
    record_ref(fidelity_item, fidelity_record)
)

follow_item_08 = entry(scenario_08, contract="follow_up")
follow_record_08 = records_08[str(follow_item_08["fixture_path"])]
follow_ref_08 = follow_up_reference(work_08, follow_record_08.logical_id)
follow_08 = FollowUpWorkflowService(workspace_08, **service_kwargs_08).require_current_use(
    follow_ref_08
).record

outcome_item_08 = entry(scenario_08, contract="outcome")
outcome_record_08 = records_08[str(outcome_item_08["fixture_path"])]
outcome_ref_08 = outcome_reference(work_08, outcome_record_08.logical_id)
outcome_08 = OutcomeWorkflowService(workspace_08, **service_kwargs_08).require_current_use(
    outcome_ref_08
).record

if repo_08.load_work(work_08).record.to_dict() != root_before:
    raise AssertionError("P22-08 current-use resolution mutated the Support Process")

workspace_10 = Path("synthetic-workspace-issue46-p22-10")
repo_10, context_10, scenario_10, records_10 = seed(
    "p22_10_reentry_repair_without_overclaiming", workspace_10
)
service_kwargs_10 = kwargs(repo_10, context_10)
reentry_item = entry(scenario_10, contract="reentry")
repair_item = entry(scenario_10, contract="repair")
follow_item_10 = entry(scenario_10, contract="follow_up")

reentry_record = records_10[str(reentry_item["fixture_path"])]
repair_record = records_10[str(repair_item["fixture_path"])]
follow_record_10 = records_10[str(follow_item_10["fixture_path"])]
reentry_work = owner_work(reentry_item)
repair_work = owner_work(repair_item)
follow_work_10 = owner_work(follow_item_10)

reentry = ReentryWorkflowService(workspace_10, **service_kwargs_10).require_current_use(
    reentry_reference(reentry_work, reentry_record.logical_id)
).record
repair = RepairWorkflowService(workspace_10, **service_kwargs_10).require_current_use(
    repair_reference(repair_work, repair_record.logical_id)
).record
follow_10 = FollowUpWorkflowService(workspace_10, **service_kwargs_10).require_current_use(
    follow_up_reference(follow_work_10, follow_record_10.logical_id)
).record

if contract_entries(scenario_10, "outcome"):
    raise AssertionError("P22-10 must not fabricate an Outcome")
if not all_keys(reentry.to_dict()).isdisjoint(
    {"clearance", "cleared", "readiness_score", "rehabilitated", "compliance_score"}
):
    raise AssertionError("Reentry encoded a forbidden clearance/compliance inference")
if not all_keys(repair.to_dict()).isdisjoint(
    {
        "admission_required",
        "apology_required",
        "remorse_score",
        "forgiveness",
        "relationship_restored",
        "recurrence_prevented",
    }
):
    raise AssertionError("Repair encoded a forbidden restorative inference")

print(json.dumps({
    "p22_08_follow_up_current": follow_08.status == "active",
    "p22_08_outcome_current": outcome_08.status == "active",
    "p22_10_reentry_state": reentry.field("workflow_state"),
    "p22_10_repair_state": repair.field("workflow_state"),
    "p22_10_follow_up_state": follow_10.field("workflow_state"),
    "p22_10_outcome_fabricated": bool(contract_entries(scenario_10, "outcome")),
}))
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue46-wheel-smoke-") as temp:
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

        required_installed = (
            "workflows/action_common.py",
            "workflows/action_reownership.py",
            "workflows/downstream_common.py",
            "workflows/downstream_lifecycle.py",
            "workflows/downstream_supersession.py",
            "workflows/follow_ups.py",
            "workflows/outcomes.py",
            "workflows/reentries.py",
            "workflows/repairs.py",
        )
        for relative in required_installed:
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #46 file: {relative}"
                )

        result = _run(
            [str(python), "-c", code, str(scenario_root.resolve())],
            cwd=work,
            env=env,
        )
        payload = json.loads(result.stdout)
        expected = {
            "p22_08_follow_up_current": True,
            "p22_08_outcome_current": True,
            "p22_10_reentry_state": "completed",
            "p22_10_repair_state": "completed",
            "p22_10_follow_up_state": "completed",
            "p22_10_outcome_fabricated": False,
        }
        if payload != expected:
            raise RuntimeError(f"unexpected Issue #46 downstream result: {payload!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout)
            if exc.stderr:
                print(exc.stderr)
        return 1
    print("Portia installed-wheel Issue #46 downstream workflow smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
