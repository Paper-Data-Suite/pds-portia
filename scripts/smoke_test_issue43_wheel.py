"""Smoke Issue #43 Response/Communication workflows from an installed wheel."""

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
        raise RuntimeError("Issue #43 installed-wheel smoke requires Core 0.6.3")

    code = r'''
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.identity import ActorDirectoryService
from portia.models import parse_portia_record
from portia.models.references import ExactActorContactPointRef, ExactPortiaWorkRef
from portia.workflows import (
    CommunicationWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    ResponseWorkflowService,
    communication_reference,
    response_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-response-communication"))
agent = {"type": "local_operator", "display_label": "Synthetic Teacher"}
system_agent = {"type": "system_process", "process_id": "wheel_issue43_smoke"}
work = ExactPortiaWorkRef(
    class_id="class_issue43_smoke",
    work_id="evt_issue43_smoke",
    work_kind="event",
    contract_version="2",
)

actors = ActorDirectoryService(workspace)
actor = parse_portia_record("actor", "1", {
    "schema_version": "1",
    "record_type": "actor",
    "module_id": "portia",
    "actor_id": "actr_issue43_family",
    "status": "active",
    "display": {"display_name": "Synthetic Family Contact"},
    "actor_category": {"kind": "family_or_caregiver"},
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:00:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-30T20:00:00-04:00",
    "updated_by": agent,
})
actors.create_actor(actor)
contact = parse_portia_record("actor_contact_point", "1", {
    "schema_version": "1",
    "record_type": "actor_contact_point",
    "module_id": "portia",
    "actor_id": "actr_issue43_family",
    "contact_point_id": "acp_issue43_email",
    "status": "active",
    "contact": {
        "kind": "email",
        "address": "issue43.family@example.invalid",
        "label": "personal",
    },
    "use_preference": "preferred",
    "source": {"kind": "actor_statement"},
    "verification": {
        "kind": "locally_confirmed",
        "verified_at": "2026-08-30T20:01:00-04:00",
        "verified_by": agent,
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:01:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-30T20:01:00-04:00",
    "updated_by": agent,
})
actors.create_actor_child("actr_issue43_family", contact)

base_event = {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_issue43_smoke",
    "work_id": "evt_issue43_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "occurrence": {
        "precision": "exact",
        "started_at": "2026-08-30T20:10:00-04:00",
    },
    "summary": "Synthetic installed-wheel Response/Communication context.",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:30:00-04:00",
    "created_by": system_agent,
    "updated_at": "2026-08-30T20:30:00-04:00",
    "updated_by": system_agent,
}
events = EventWorkflowService(workspace)
stored_event = events.create(parse_portia_record("event", "2", base_event))
participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_issue43_smoke",
    "work_id": "evt_issue43_smoke",
    "participant_id": "ep_issue43_smoke",
    "status": "active",
    "subject": {"kind": "unknown_person", "reason": "identity_not_known"},
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:31:00-04:00",
    "created_by": system_agent,
    "updated_at": "2026-08-30T20:31:00-04:00",
    "updated_by": system_agent,
})
ParticipantWorkflowService(workspace).create(work, participant)
active_event = dict(base_event)
active_event["status"] = "active"
active_event["updated_at"] = "2026-08-30T20:32:00-04:00"
events.replace(
    parse_portia_record("event", "2", active_event),
    expected=stored_event.fingerprint,
)

response = parse_portia_record("response", "1", {
    "schema_version": "1",
    "record_type": "response",
    "module_id": "portia",
    "class_id": "class_issue43_smoke",
    "work_id": "evt_issue43_smoke",
    "response_id": "rsp_issue43_smoke",
    "status": "active",
    "target": {"kind": "event"},
    "provider": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
    "action": {
        "family": "environmental_or_instructional",
        "description": "Teacher offered a quieter location for the bounded Event.",
    },
    "execution_state": "completed",
    "started_at": "2026-08-30T20:20:00-04:00",
    "ended_at": "2026-08-30T20:21:00-04:00",
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:35:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-30T20:35:00-04:00",
    "updated_by": agent,
})
responses = ResponseWorkflowService(workspace)
responses.create(work, response)
response_ref = response_reference(work, "rsp_issue43_smoke")
assert (
    responses.require_current_use(response_ref).record.logical_id
    == "rsp_issue43_smoke"
)

communication = parse_portia_record("communication", "1", {
    "schema_version": "1",
    "record_type": "communication",
    "module_id": "portia",
    "class_id": "class_issue43_smoke",
    "work_kind": "event",
    "work_id": "evt_issue43_smoke",
    "communication_id": "comm_issue43_smoke",
    "status": "active",
    "sender": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
    "recipients": [
        {
            "person": {
                "kind": "actor",
                "actor_ref": {"actor_id": "actr_issue43_family"},
                "display_snapshot": {"display_name": "Synthetic Family Contact"},
            },
            "endpoint_ref": {
                "actor_id": "actr_issue43_family",
                "contact_point_id": "acp_issue43_email",
                "contract_version": "1",
            },
            "participation": "not_established",
        }
    ],
    "method": {"kind": "email"},
    "purpose": {"kind": "response_coordination"},
    "act_state": "completed",
    "privacy_scope": "participant_limited",
    "started_at": "2026-08-30T20:40:00-04:00",
    "ended_at": "2026-08-30T20:41:00-04:00",
    "summary": "Teacher sent a bounded family-contact message about the Response.",
    "relations": [
        {
            "relation": "relates_to_response",
            "record_ref": {
                "work_ref": work.to_dict(),
                "record_ref": {
                    "record_kind": "response",
                    "record_id": "rsp_issue43_smoke",
                    "contract_version": "1",
                },
            },
        }
    ],
    "creation_source": {"type": "digital_entry"},
    "created_at": "2026-08-30T20:45:00-04:00",
    "created_by": agent,
    "updated_at": "2026-08-30T20:45:00-04:00",
    "updated_by": agent,
})
communications = CommunicationWorkflowService(workspace)
communications.create(work, communication)
communication_ref = communication_reference(work, "comm_issue43_smoke")
assert communications.require_current_use(communication_ref).record.logical_id == (
    "comm_issue43_smoke"
)
contact_ref = ExactActorContactPointRef(
    actor_id="actr_issue43_family",
    contact_point_id="acp_issue43_email",
    contract_version="1",
)
assert (
    actors.load_contact_point(contact_ref, require_current_use=True).record.logical_id
    == "acp_issue43_email"
)

records_root = (
    workspace
    / "classes/class_issue43_smoke/modules/portia/work/evt_issue43_smoke/records"
)
assert (records_root / "response/rsp_issue43_smoke.json").is_file()
assert (records_root / "communication/comm_issue43_smoke.json").is_file()
for forbidden in (
    "review",
    "classification",
    "hypothesis",
    "determination",
    "support",
    "intervention",
    "outcome",
):
    assert not (records_root / forbidden).exists()

recipient = communication.field("recipients")[0]
relation = communication.field("relations")[0]
print(json.dumps({
    "response": responses.load_exact(response_ref).record.logical_id,
    "response_execution_state": response.field("execution_state"),
    "communication": communications.load_exact(communication_ref).record.logical_id,
    "communication_act_state": communication.field("act_state"),
    "recipient_participation": recipient["participation"],
    "relation": relation["relation"],
    "contact_point": contact_ref.contact_point_id,
}))
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue43-wheel-smoke-") as temporary:
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
            raise RuntimeError(
                f"smoke import resolved into source checkout: {installed}"
            )
        for relative in (
            "workflows/action_common.py",
            "workflows/action_transition.py",
            "workflows/communication_attachments.py",
            "workflows/communication_common.py",
            "workflows/communication_lifecycle.py",
            "workflows/communication_relations.py",
            "workflows/communication_supersession.py",
            "workflows/communications.py",
            "workflows/response_common.py",
            "workflows/response_lifecycle.py",
            "workflows/response_supersession.py",
            "workflows/responses.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #43 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected = {
            "response": "rsp_issue43_smoke",
            "response_execution_state": "completed",
            "communication": "comm_issue43_smoke",
            "communication_act_state": "completed",
            "recipient_participation": "not_established",
            "relation": "relates_to_response",
            "contact_point": "acp_issue43_email",
        }
        if payload != expected:
            raise RuntimeError(
                f"unexpected Issue #43 Response/Communication smoke result: {payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Issue #43 wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #43 Response/Communication smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
