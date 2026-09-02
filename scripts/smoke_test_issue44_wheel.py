"""Smoke Issue #44 Support planning workflows from an installed wheel."""

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


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    if "0.6.3" not in core_wheel.name:
        raise RuntimeError("Issue #44 installed-wheel smoke requires Core 0.6.3")

    code = r"""
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    intervention_reference,
    support_goal_reference,
    support_need_reference,
    support_process_participant_reference,
    support_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-support-planning"))
agent = {"type": "local_operator", "display_label": "Synthetic Teacher"}
work = ExactPortiaWorkRef(
    class_id="class_issue44_smoke",
    work_id="sup_issue44_smoke",
    work_kind="support_process",
    contract_version="1",
)

root_base = {
    "schema_version": "1",
    "record_type": "portia_work",
    "work_kind": "support_process",
    "module_id": "portia",
    "class_id": "class_issue44_smoke",
    "work_id": "sup_issue44_smoke",
    "school_year": "2026-2027",
    "status": "proposed",
    "workflow_state": "planning",
    "summary": "Synthetic installed-wheel Support planning root.",
    "initiation": {
        "kind": "teacher_identified_need",
        "detail": "Synthetic bounded planning need.",
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-02T07:50:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-02T07:50:00-04:00",
    "updated_by": agent,
}
roots = SupportProcessWorkflowService(workspace)
stored_root = roots.create(parse_portia_record("support_process", "1", root_base))

participants = SupportProcessParticipantWorkflowService(workspace)

def participant_wire(participant_id, person, contexts, created_at):
    return {
        "schema_version": "1",
        "record_type": "support_process_participant",
        "module_id": "portia",
        "class_id": "class_issue44_smoke",
        "work_id": "sup_issue44_smoke",
        "participant_id": participant_id,
        "status": "proposed",
        "person": person,
        "contexts": contexts,
        "creation_source": {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": agent,
        "updated_at": created_at,
        "updated_by": agent,
    }

student_wire = participant_wire(
    "spp_issue44_student",
    {
        "kind": "descriptive_person",
        "description_type": "outside_student",
        "display_label": "Synthetic Learner",
    },
    [{"kind": "supported_person"}],
    "2026-09-02T07:51:00-04:00",
)
student = participants.create(
    work,
    parse_portia_record("support_process_participant", "1", student_wire),
)
student_active = dict(student_wire)
student_active["status"] = "active"
student_active["updated_at"] = "2026-09-02T07:53:00-04:00"
participants.transition_lifecycle(
    support_process_participant_reference(work, "spp_issue44_student"),
    parse_portia_record("support_process_participant", "1", student_active),
    expected=student.fingerprint,
    transition_id="lct_issue44_student_active",
    reason_code="planning_confirmed",
    operation_id="op_issue44_student_active",
)

provider_wire = participant_wire(
    "spp_issue44_provider",
    {"kind": "local_operator", "display_label": "Synthetic Teacher"},
    [{"kind": "provider_or_collaborator"}],
    "2026-09-02T07:52:00-04:00",
)
provider = participants.create(
    work,
    parse_portia_record("support_process_participant", "1", provider_wire),
)
provider_active = dict(provider_wire)
provider_active["status"] = "active"
provider_active["updated_at"] = "2026-09-02T07:54:00-04:00"
participants.transition_lifecycle(
    support_process_participant_reference(work, "spp_issue44_provider"),
    parse_portia_record("support_process_participant", "1", provider_active),
    expected=provider.fingerprint,
    transition_id="lct_issue44_provider_active",
    reason_code="planning_confirmed",
    operation_id="op_issue44_provider_active",
)

root_active = dict(root_base)
root_active["status"] = "active"
root_active["updated_at"] = "2026-09-02T07:55:00-04:00"
roots.transition_lifecycle(
    work,
    parse_portia_record("support_process", "1", root_active),
    expected=stored_root.fingerprint,
    transition_id="lct_issue44_root_active",
    reason_code="planning_confirmed",
    operation_id="op_issue44_root_active",
)
assert roots.require_current_use(work).record.status == "active"

target = {
    "kind": "support_process_participant",
    "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_issue44_student",
        "contract_version": "1",
    },
}
need = parse_portia_record("support_need", "1", {
    "schema_version": "1",
    "record_type": "support_need",
    "module_id": "portia",
    "class_id": "class_issue44_smoke",
    "work_id": "sup_issue44_smoke",
    "need_id": "spn_issue44_access",
    "status": "active",
    "target": target,
    "need_kind": "access",
    "description": "Synthetic bounded access need.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-02T07:56:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-02T07:56:00-04:00",
    "updated_by": agent,
})
needs = SupportNeedWorkflowService(workspace)
needs.create(work, need)
assert needs.require_current_use(
    support_need_reference(work, "spn_issue44_access")
).record.logical_id == "spn_issue44_access"

goal = parse_portia_record("support_goal", "1", {
    "schema_version": "1",
    "record_type": "support_goal",
    "module_id": "portia",
    "class_id": "class_issue44_smoke",
    "work_id": "sup_issue44_smoke",
    "goal_id": "spg_issue44_routine",
    "status": "active",
    "target": target,
    "description": "Synthetic bounded future routine objective.",
    "planned_criteria": "Review the planned routine at the review point.",
    "measurement_approach": "Teacher review of later implementation records.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-02T07:57:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-02T07:57:00-04:00",
    "updated_by": agent,
})
goals = SupportGoalWorkflowService(workspace)
goals.create(work, goal)
assert goals.require_current_use(
    support_goal_reference(work, "spg_issue44_routine")
).record.logical_id == "spg_issue44_routine"

provider_plan = {
    "kind": "assigned",
    "participant_refs": [{
        "record_kind": "support_process_participant",
        "record_id": "spp_issue44_provider",
        "contract_version": "1",
    }],
}
schedule = {
    "kind": "recurring",
    "frequency": {
        "occurrences": 1,
        "interval_count": 1,
        "interval_unit": "week",
    },
    "selected_days": ["monday", "thursday"],
    "planned_duration": {"kind": "minutes", "minutes": 10},
}
support = parse_portia_record("support", "1", {
    "schema_version": "1",
    "record_type": "support",
    "module_id": "portia",
    "class_id": "class_issue44_smoke",
    "work_id": "sup_issue44_smoke",
    "support_id": "spt_issue44_routine",
    "status": "active",
    "target": target,
    "need_refs": [{
        "record_kind": "support_need",
        "record_id": "spn_issue44_access",
        "contract_version": "1",
    }],
    "strategy": {
        "kind": "routine_or_structure",
        "procedure": "Provide a predictable synthetic weekly check-in routine.",
    },
    "provider_plan": provider_plan,
    "schedule": schedule,
    "plan_state": "active",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-02T07:58:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-02T07:58:00-04:00",
    "updated_by": agent,
})
supports = SupportWorkflowService(workspace)
supports.create(work, support)
assert supports.require_current_use(
    support_reference(work, "spt_issue44_routine")
).record.field("plan_state") == "active"

intervention = parse_portia_record("intervention", "1", {
    "schema_version": "1",
    "record_type": "intervention",
    "module_id": "portia",
    "class_id": "class_issue44_smoke",
    "work_id": "sup_issue44_smoke",
    "intervention_id": "int_issue44_routine",
    "status": "active",
    "target": target,
    "need_refs": [{
        "record_kind": "support_need",
        "record_id": "spn_issue44_access",
        "contract_version": "1",
    }],
    "goal_refs": [{
        "record_kind": "support_goal",
        "record_id": "spg_issue44_routine",
        "contract_version": "1",
    }],
    "strategy": {
        "kind": "routine_or_structure",
        "procedure": "Use the explicitly planned synthetic check-in and reset routine.",
    },
    "provider_plan": provider_plan,
    "schedule": schedule,
    "monitoring_approach": "Review later implementation records at the review point.",
    "plan_state": "active",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-09-02T07:59:00-04:00",
    "created_by": agent,
    "updated_at": "2026-09-02T07:59:00-04:00",
    "updated_by": agent,
})
interventions = InterventionWorkflowService(workspace)
interventions.create(work, intervention)
assert interventions.require_current_use(
    intervention_reference(work, "int_issue44_routine")
).record.field("plan_state") == "active"

records_root = (
    workspace
    / "classes/class_issue44_smoke/modules/portia/work/sup_issue44_smoke/records"
)
expected_files = {
    "support_process_participant/spp_issue44_student.json",
    "support_process_participant/spp_issue44_provider.json",
    "support_need/spn_issue44_access.json",
    "support_goal/spg_issue44_routine.json",
    "support/spt_issue44_routine.json",
    "intervention/int_issue44_routine.json",
}
for relative in expected_files:
    assert (records_root / relative).is_file(), relative

for forbidden in ("implementation", "fidelity", "follow_up", "outcome", "reentry", "repair"):
    assert not (records_root / forbidden).exists(), forbidden

print(json.dumps({
    "root_status": roots.require_current_use(work).record.status,
    "supported_person": participants.require_current_use(
        support_process_participant_reference(work, "spp_issue44_student")
    ).participant.record.logical_id,
    "need": need.logical_id,
    "goal": goal.logical_id,
    "support_plan_state": support.field("plan_state"),
    "intervention_plan_state": intervention.field("plan_state"),
    "implementation_fabricated": (records_root / "implementation").exists(),
    "fidelity_fabricated": (records_root / "fidelity").exists(),
}))
"""

    with tempfile.TemporaryDirectory(prefix="portia-issue44-wheel-smoke-") as temporary:
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
            "workflows/support_processes.py",
            "workflows/support_process_participants.py",
            "workflows/support_needs.py",
            "workflows/support_goals.py",
            "workflows/supports.py",
            "workflows/interventions.py",
            "workflows/support_process_continuation.py",
            "workflows/support_process_initiation.py",
        )
        for relative in required_installed:
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #44 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected = {
            "root_status": "active",
            "supported_person": "spp_issue44_student",
            "need": "spn_issue44_access",
            "goal": "spg_issue44_routine",
            "support_plan_state": "active",
            "intervention_plan_state": "active",
            "implementation_fabricated": False,
            "fidelity_fabricated": False,
        }
        if payload != expected:
            raise RuntimeError(
                f"unexpected Issue #44 Support-planning smoke result: {payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Issue #44 wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #44 Support-planning smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
