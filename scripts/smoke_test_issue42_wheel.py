"""Smoke Issue #42 judgment workflows from an isolated installed Portia wheel."""

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
        raise RuntimeError("Issue #42 installed-wheel smoke requires Core 0.6.3")

    code = r'''
import json
from pathlib import Path

from pds_core.workspace import ensure_workspace_root
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    EventWorkflowService,
    HypothesisWorkflowService,
    ParticipantWorkflowService,
    ReviewWorkflowService,
    classification_reference,
    determination_reference,
    hypothesis_reference,
    review_reference,
)

workspace = ensure_workspace_root(Path("synthetic-workspace-judgment"))
agent = {"type": "system_process", "process_id": "wheel_judgment_smoke"}
timestamp = "2026-08-29T20:00:00-04:00"
work = ExactPortiaWorkRef(
    class_id="class_judgment_smoke",
    work_id="evt_judgment_smoke",
    work_kind="event",
    contract_version="2",
)

event_data = {
    "schema_version": "2",
    "record_type": "portia_work",
    "work_kind": "event",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "school_year": "2026-2027",
    "status": "draft",
    "occurrence": {"precision": "exact", "started_at": timestamp},
    "summary": "Synthetic judgment smoke context.",
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
}
event = parse_portia_record("event", "2", event_data)
events = EventWorkflowService(workspace)
stored_event = events.create(event)

participant = parse_portia_record("event_participant", "3", {
    "schema_version": "3",
    "record_type": "event_participant",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "participant_id": "ep_judgment_smoke",
    "status": "active",
    "subject": {"kind": "unknown_person", "reason": "identity_not_known"},
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
ParticipantWorkflowService(workspace).create(work, participant)

activation_timestamp = "2026-08-29T20:01:00-04:00"
active_event_data = dict(event_data)
active_event_data["status"] = "active"
active_event_data["updated_at"] = activation_timestamp
active_event = parse_portia_record("event", "2", active_event_data)
events.replace(active_event, expected=stored_event.fingerprint)

timestamp = "2026-08-29T20:02:00-04:00"

review = parse_portia_record("review", "1", {
    "schema_version": "1",
    "record_type": "review",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "review_id": "rvw_judgment_smoke",
    "status": "active",
    "review_state": "completed",
    "trigger": {"kind": "routine_review"},
    "question": {
        "kind": "determination_review",
        "text": "What bounded decision should be recorded?",
    },
    "target": {"kind": "event"},
    "reviewer": {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    },
    "evidence_considered": [],
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
reviews = ReviewWorkflowService(workspace)
reviews.create(work, review)
review_ref = review_reference(work, "rvw_judgment_smoke")
assert reviews.require_current_use(review_ref).record.logical_id == "rvw_judgment_smoke"

classification = parse_portia_record("classification", "1", {
    "schema_version": "1",
    "record_type": "classification",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "classification_id": "cls_judgment_smoke",
    "status": "active",
    "target": {"kind": "event"},
    "selector": {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    },
    "stage": "reporter_selected",
    "result": {
        "kind": "category_selected",
        "definition": {
            "scheme_id": "local_behavior",
            "scheme_version": "2026_1",
            "category_code": "contextual_concern",
            "category_label": "Contextual concern",
            "definition_text": "Synthetic local category for wheel smoke.",
        },
    },
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
classifications = ClassificationWorkflowService(workspace)
classifications.create(work, classification)
classification_ref = classification_reference(work, "cls_judgment_smoke")
assert (
    classifications.require_current_use(classification_ref).record.logical_id
    == "cls_judgment_smoke"
)

hypothesis = parse_portia_record("hypothesis", "1", {
    "schema_version": "1",
    "record_type": "hypothesis",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "hypothesis_id": "hyp_judgment_smoke",
    "status": "active",
    "target": {"kind": "event"},
    "author": {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    },
    "proposition": "A contextual change may have contributed to the Event.",
    "consideration_state": "under_consideration",
    "evidence": [],
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
hypotheses = HypothesisWorkflowService(workspace)
hypotheses.create(work, hypothesis)
hypothesis_ref = hypothesis_reference(work, "hyp_judgment_smoke")
assert hypotheses.require_current_use(hypothesis_ref).record.logical_id == (
    "hyp_judgment_smoke"
)

determination = parse_portia_record("determination", "1", {
    "schema_version": "1",
    "record_type": "determination",
    "module_id": "portia",
    "class_id": "class_judgment_smoke",
    "work_id": "evt_judgment_smoke",
    "determination_id": "det_judgment_smoke",
    "status": "active",
    "target": {"kind": "event"},
    "question": "What bounded conclusion is supported for this Event?",
    "decision_maker": {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    },
    "authority_context": {
        "kind": "teacher_local",
        "scope": "teacher_review",
    },
    "process_basis": {
        "kind": "teacher_local",
        "process_label": "Local teacher review",
    },
    "outcome": {"kind": "insufficient_information"},
    "review_ref": review_ref.to_dict(),
    "creation_source": {"type": "digital_entry"},
    "created_at": timestamp,
    "created_by": agent,
    "updated_at": timestamp,
    "updated_by": agent,
})
determinations = DeterminationWorkflowService(workspace)
determinations.create(work, determination)
determination_ref = determination_reference(work, "det_judgment_smoke")
assert determinations.require_current_use(determination_ref).record.logical_id == (
    "det_judgment_smoke"
)

records_root = (
    workspace
    / "classes/class_judgment_smoke/modules/portia/work/evt_judgment_smoke/records"
)
for kind, record_id in (
    ("review", "rvw_judgment_smoke"),
    ("classification", "cls_judgment_smoke"),
    ("hypothesis", "hyp_judgment_smoke"),
    ("determination", "det_judgment_smoke"),
):
    assert (records_root / kind / f"{record_id}.json").is_file()

print(json.dumps({
    "review": reviews.load_exact(review_ref).record.logical_id,
    "classification": classifications.load_exact(classification_ref).record.logical_id,
    "hypothesis": hypotheses.load_exact(hypothesis_ref).record.logical_id,
    "determination": determinations.load_exact(determination_ref).record.logical_id,
    "determination_outcome": {
        "kind": determination.field("outcome")["kind"],
    },
}))
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue42-wheel-smoke-") as temporary:
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
                (
                    "import json,portia; "
                    "print(json.dumps({'path': portia.__path__[0]}))"
                ),
            ],
            cwd=work,
            env=env,
        )
        installed = Path(json.loads(package.stdout)["path"]).resolve()
        if repository.resolve() in installed.parents:
            raise RuntimeError(f"smoke import resolved into source checkout: {installed}")
        for relative in (
            "workflows/reviews.py",
            "workflows/classifications.py",
            "workflows/hypotheses.py",
            "workflows/determinations.py",
            "workflows/judgment_evidence.py",
            "workflows/judgment_transition.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #42 file: {relative}"
                )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        payload = json.loads(result.stdout)
        expected = {
            "review": "rvw_judgment_smoke",
            "classification": "cls_judgment_smoke",
            "hypothesis": "hyp_judgment_smoke",
            "determination": "det_judgment_smoke",
            "determination_outcome": {"kind": "insufficient_information"},
        }
        if payload != expected:
            raise RuntimeError(
                f"unexpected Issue #42 judgment smoke result: {payload!r}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Issue #42 wheel smoke test failed: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout, file=sys.stderr)
            if exc.stderr:
                print(exc.stderr, file=sys.stderr)
        return 1
    print("Portia installed-wheel Issue #42 judgment smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
