"""Smoke Issue #45 Implementation/Fidelity workflows from an installed wheel."""

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
            "Issue #45 installed-wheel smoke requires the Core 0.6.3 wheel"
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

    code = r"""
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    FidelityWorkflowService,
    ImplementationWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    fidelity_reference,
    implementation_reference,
    support_process_participant_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-issue45"))
agent = {"type": "local_operator", "display_label": "Synthetic Teacher"}
work = ExactPortiaWorkRef(
    class_id="class_issue45_smoke",
    work_id="sup_issue45_smoke",
    work_kind="support_process",
    contract_version="1",
)

root_wire = {
    "schema_version": "1",
    "record_type": "portia_work",
    "work_kind": "support_process",
    "module_id": "portia",
    "class_id": "class_issue45_smoke",
    "work_id": "sup_issue45_smoke",
    "school_year": "2026-2027",
    "status": "proposed",
    "workflow_state": "planning",
    "summary": "Synthetic installed-wheel Issue #45 root.",
    "initiation": {
        "kind": "teacher_identified_need",
        "detail": "Synthetic bounded implementation need.",
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-03T08:00:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-03T08:00:00-04:00",
    "updated_by": agent,
}
roots = SupportProcessWorkflowService(workspace)
stored_root = roots.create(parse_portia_record("support_process", "1", root_wire))
participants = SupportProcessParticipantWorkflowService(workspace)


def participant_wire(participant_id, context, description_type, label):
    return {
        "schema_version": "1",
        "record_type": "support_process_participant",
        "module_id": "portia",
        "class_id": "class_issue45_smoke",
        "work_id": "sup_issue45_smoke",
        "participant_id": participant_id,
        "status": "proposed",
        "person": {
            "kind": "descriptive_person",
            "description_type": description_type,
            "display_label": label,
        },
        "contexts": [{"kind": context}],
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-09-03T08:01:00-04:00",
        "created_by": agent,
        "updated_at": "2026-09-03T08:01:00-04:00",
        "updated_by": agent,
    }


def activate_participant(participant_id, context, description_type, label, suffix):
    wire = participant_wire(participant_id, context, description_type, label)
    created = participants.create(
        work,
        parse_portia_record("support_process_participant", "1", wire),
    )
    active = dict(wire)
    active["status"] = "active"
    active["updated_at"] = "2026-09-03T08:03:00-04:00"
    participants.transition_lifecycle(
        support_process_participant_reference(work, participant_id),
        parse_portia_record("support_process_participant", "1", active),
        expected=created.fingerprint,
        transition_id=f"lct_issue45_{suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_issue45_{suffix}",
    )


activate_participant(
    "spp_issue45_student",
    "supported_person",
    "outside_student",
    "Synthetic Learner",
    "student_active",
)
root_active = dict(root_wire)
root_active["status"] = "active"
root_active["updated_at"] = "2026-09-03T08:04:00-04:00"
roots.transition_lifecycle(
    work,
    parse_portia_record("support_process", "1", root_active),
    expected=stored_root.fingerprint,
    transition_id="lct_issue45_root_active",
    reason_code="planning_confirmed",
    operation_id="op_issue45_root_active",
)
activate_participant(
    "spp_issue45_evaluator",
    "observer",
    "school_staff",
    "Synthetic Evaluator",
    "evaluator_active",
)

target = {
    "kind": "support_process_participant",
    "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_issue45_student",
        "contract_version": "1",
    },
}
need = parse_portia_record("support_need", "1", {
    "schema_version": "1",
    "record_type": "support_need",
    "module_id": "portia",
    "class_id": "class_issue45_smoke",
    "work_id": "sup_issue45_smoke",
    "need_id": "spn_issue45_access",
    "status": "active",
    "target": target,
    "need_kind": "access",
    "description": "Synthetic installed-wheel access need.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-03T08:05:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-03T08:05:00-04:00",
    "updated_by": agent,
})
SupportNeedWorkflowService(workspace).create(work, need)

support = parse_portia_record("support", "1", {
    "schema_version": "1",
    "record_type": "support",
    "module_id": "portia",
    "class_id": "class_issue45_smoke",
    "work_id": "sup_issue45_smoke",
    "support_id": "spt_issue45_access",
    "status": "active",
    "target": target,
    "need_refs": [{
        "record_kind": "support_need",
        "record_id": "spn_issue45_access",
        "contract_version": "1",
    }],
    "strategy": {
        "kind": "access",
        "procedure": "Provide the synthetic installed-wheel access condition.",
    },
    "provider_plan": {
        "kind": "no_assigned_provider",
        "reason": "access_condition",
    },
    "schedule": {
        "kind": "as_needed",
        "planned_duration": {"kind": "minutes", "minutes": 5},
    },
    "plan_state": "active",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-03T08:06:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-03T08:06:00-04:00",
    "updated_by": agent,
})
SupportWorkflowService(workspace).create(work, support)

implementation = parse_portia_record("implementation", "1", {
    "schema_version": "1",
    "record_type": "implementation",
    "module_id": "portia",
    "class_id": "class_issue45_smoke",
    "work_id": "sup_issue45_smoke",
    "implementation_id": "imp_issue45_smoke",
    "status": "active",
    "plan_ref": {
        "record_kind": "support",
        "record_id": "spt_issue45_access",
        "contract_version": "1",
    },
    "actual_target": target,
    "implementation_provider": {
        "kind": "no_human_provider",
        "reason": "environmental_condition",
    },
    "execution_state": "completed",
    "started_at": "2026-09-03T08:10:00-04:00",
    "ended_at": "2026-09-03T08:15:00-04:00",
    "summary": "Synthetic installed-wheel implementation occurrence.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-03T08:16:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-03T08:16:00-04:00",
    "updated_by": agent,
})
implementations = ImplementationWorkflowService(workspace)
stored_implementation = implementations.create(work, implementation)
implementation_exact = implementation_reference(work, "imp_issue45_smoke")
assert implementations.require_current_use(implementation_exact).fingerprint == (
    stored_implementation.fingerprint
)

fidelity = parse_portia_record("fidelity", "1", {
    "schema_version": "1",
    "record_type": "fidelity",
    "module_id": "portia",
    "class_id": "class_issue45_smoke",
    "work_id": "sup_issue45_smoke",
    "fidelity_id": "fid_issue45_smoke",
    "status": "active",
    "plan_ref": {
        "record_kind": "support",
        "record_id": "spt_issue45_access",
        "contract_version": "1",
    },
    "evaluator_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_issue45_evaluator",
        "contract_version": "1",
    },
    "scope": {
        "kind": "one_implementation",
        "implementation_ref": {
            "record_kind": "implementation",
            "record_id": "imp_issue45_smoke",
            "contract_version": "1",
        },
    },
    "result": "as_planned",
    "basis": {"kind": "direct_observation"},
    "evaluated_at": "2026-09-03T08:20:00-04:00",
    "summary": "Synthetic installed-wheel Fidelity evaluation.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-03T08:21:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-03T08:21:00-04:00",
    "updated_by": agent,
})
fidelities = FidelityWorkflowService(workspace)
stored_fidelity = fidelities.create(work, fidelity)
fidelity_exact = fidelity_reference(work, "fid_issue45_smoke")
assert fidelities.require_current_use(fidelity_exact).fingerprint == (
    stored_fidelity.fingerprint
)

records_root = (
    workspace
    / "classes/class_issue45_smoke/modules/portia/work/sup_issue45_smoke/records"
)
for relative in (
    "implementation/imp_issue45_smoke.json",
    "fidelity/fid_issue45_smoke.json",
):
    assert (records_root / relative).is_file(), relative
for forbidden in ("follow_up", "outcome", "reentry", "repair"):
    assert not (records_root / forbidden).exists(), forbidden

implementation_wire = stored_implementation.record.to_dict()
fidelity_wire = stored_fidelity.record.to_dict()
assert "effective" not in implementation_wire
assert "successful" not in implementation_wire
assert "effective" not in fidelity_wire
assert "successful" not in fidelity_wire

print(json.dumps({
    "implementation_id": stored_implementation.record.logical_id,
    "execution_state": stored_implementation.record.field("execution_state"),
    "fidelity_id": stored_fidelity.record.logical_id,
    "fidelity_result": stored_fidelity.record.field("result"),
    "outcome_fabricated": (records_root / "outcome").exists(),
    "follow_up_fabricated": (records_root / "follow_up").exists(),
}))
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue45-wheel-smoke-") as temp:
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
            raise RuntimeError(
                f"smoke import resolved into source checkout: {installed}"
            )

        required_installed = (
            "workflows/action_consolidation.py",
            "workflows/action_reownership.py",
            "workflows/fidelity.py",
            "workflows/fidelity_lifecycle.py",
            "workflows/fidelity_supersession.py",
            "workflows/implementation_lifecycle.py",
            "workflows/implementation_supersession.py",
            "workflows/implementations.py",
        )
        for relative in required_installed:
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #45 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected = {
            "implementation_id": "imp_issue45_smoke",
            "execution_state": "completed",
            "fidelity_id": "fid_issue45_smoke",
            "fidelity_result": "as_planned",
            "outcome_fabricated": False,
            "follow_up_fabricated": False,
        }
        if payload != expected:
            raise RuntimeError(
                f"unexpected Issue #45 Implementation/Fidelity result: {payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Issue #45 wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #45 Implementation/Fidelity smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
