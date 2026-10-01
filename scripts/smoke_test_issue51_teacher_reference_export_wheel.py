"""Run isolated installed-wheel acceptance for Issue #51 teacher exports."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


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


def smoke(portia_wheel: Path, core_wheel: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    code = r'''
import json
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory

from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.exports import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionService,
    TeacherReferenceExportExecutionSuccess,
    TeacherReferenceExportHistoryService,
    TeacherReferenceExportPreparationService,
    TeacherReferenceExportRecoveryService,
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
)
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import OperationJournalStore, PortiaOperationPartialCommitError, PortiaRepository
from portia.storage.deliberate_export_persistence import (
    commit_deliberate_export_candidates,
    stage_deliberate_export_candidates,
)
from portia.storage.paths import operation_revision_path
from portia.views import CurrentnessDecision

BASE = "2026-09-30T18:00:00-04:00"
OPERATOR = {"type": "local_operator", "display_label": "Synthetic Teacher"}
AGENT = {"type": "system_process", "process_id": "issue51_installed_smoke"}


class Currentness:
    def evaluate(self, source_ref):
        return CurrentnessDecision(source_ref, "current", "installed_smoke_current")


def ids(*tokens):
    iterator = iter(tokens)
    return PortiaIdGenerator(token_source=iterator.__next__)


def event_ref():
    return ExactPortiaWorkRef(
        class_id="class_smoke",
        work_id="evt_issue51",
        work_kind="event",
        contract_version="2",
    )


def event_participant_ref():
    return ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id="ep_issue51",
            contract_version="3",
        ),
    )


def support_ref():
    return ExactPortiaWorkRef(
        class_id="class_smoke",
        work_id="sup_issue51",
        work_kind="support_process",
        contract_version="1",
    )


def seed(workspace):
    ensure_workspace_root(workspace)
    write_class_roster(
        workspace,
        create_roster(
            "class_smoke",
            [
                {
                    "student_id": "student_issue51",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    write_class_metadata_for_class(
        workspace,
        create_class_metadata(
            "class_smoke",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )
    repo = PortiaRepository(workspace)
    repo.create_work(
        event_ref(),
        parse_portia_record(
            "event",
            "2",
            {
                "schema_version": "2",
                "record_type": "portia_work",
                "work_kind": "event",
                "module_id": "portia",
                "class_id": "class_smoke",
                "work_id": "evt_issue51",
                "school_year": "2026-2027",
                "status": "active",
                "occurrence": {"precision": "exact", "started_at": BASE},
                "summary": "Synthetic installed Event reference content.",
                "creation_source": {"type": "digital_entry"},
                "created_at": BASE,
                "created_by": AGENT,
                "updated_at": BASE,
                "updated_by": AGENT,
            },
        ),
    )
    repo.create_work_record(
        event_ref(),
        parse_portia_record(
            "event_participant",
            "3",
            {
                "schema_version": "3",
                "record_type": "event_participant",
                "module_id": "portia",
                "class_id": "class_smoke",
                "work_id": "evt_issue51",
                "participant_id": "ep_issue51",
                "status": "active",
                "subject": {
                    "kind": "roster_student",
                    "roster_student_ref": {
                        "class_id": "class_smoke",
                        "student_id": "student_issue51",
                    },
                    "display_snapshot": {"display_name": "Synthetic Student"},
                },
                "creation_source": {"type": "digital_entry"},
                "created_at": BASE,
                "created_by": AGENT,
                "updated_at": BASE,
                "updated_by": AGENT,
            },
        ),
    )
    repo.create_work(
        support_ref(),
        parse_portia_record(
            "support_process",
            "1",
            {
                "schema_version": "1",
                "record_type": "portia_work",
                "work_kind": "support_process",
                "module_id": "portia",
                "class_id": "class_smoke",
                "work_id": "sup_issue51",
                "school_year": "2026-2027",
                "status": "active",
                "workflow_state": "active",
                "summary": "Synthetic installed Support Process reference content.",
                "initiation": {
                    "kind": "teacher_identified_need",
                    "detail": "Synthetic bounded need.",
                },
                "creation_source": {"type": "digital_entry"},
                "created_at": BASE,
                "created_by": AGENT,
                "updated_at": BASE,
                "updated_by": AGENT,
            },
        ),
    )
    return repo


def discovery_service(workspace, repo):
    return TeacherReferenceScopeDiscoveryService(
        workspace,
        repository=repo,
        currentness=Currentness(),
    )


def final_decision(workspace, repo, scope, reviewed_at):
    discovery = discovery_service(workspace, repo).discover(scope)
    projection = TeacherReferenceProjectionService(workspace, repository=repo)
    decision = projection.project(discovery)
    if decision.manual_review.status != "pending":
        return decision
    choices = tuple(
        TeacherReferenceManualReviewChoice(
            item.source_ref,
            item.field_name,
            "include_exact",
        )
        for item in decision.unresolved_manual_items
        if item.field_name is not None
    )
    return projection.resolve_manual_review(
        decision,
        choices,
        reviewed_at=reviewed_at,
        reviewed_by=OPERATOR,
    )


def preparation(workspace, repo, scope, prefix, minute):
    reviewed_at = f"2026-09-30T18:{minute:02d}:00-04:00"
    generated_at = f"2026-09-30T18:{minute + 1:02d}:00-04:00"
    decision = final_decision(workspace, repo, scope, reviewed_at)
    service = TeacherReferenceExportPreparationService(
        workspace,
        repository=repo,
        id_generator=ids(
            f"{prefix}_export",
            f"{prefix}_operation",
            f"{prefix}_artifact",
            f"{prefix}_provenance",
        ),
    )
    prepared = service.prepare(
        decision,
        requested_at=reviewed_at,
        requested_by=OPERATOR,
        generated_at=generated_at,
        deployment_instance_id="installed_smoke",
        process_instance_id="installed_smoke_process",
    )
    assert prepared.operation_journal.contract_version == "4"
    assert prepared.operation_lock.contract_version == "3"
    return prepared, f"2026-09-30T18:{minute + 2:02d}:00-04:00"


def execution_service(workspace, repo):
    return TeacherReferenceExportExecutionService(
        workspace,
        repository=repo,
        discovery_service=discovery_service(workspace, repo),
        projection_service=TeacherReferenceProjectionService(
            workspace,
            repository=repo,
        ),
    )


def execute(workspace, repo, scope, prefix, minute):
    prepared, confirmed_at = preparation(workspace, repo, scope, prefix, minute)
    result = execution_service(workspace, repo).execute(
        prepared,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=prepared.preparation_digest,
        confirmed_at=confirmed_at,
    )
    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    assert result.status == "completed"
    assert Path(workspace, prepared.artifact_relative_path).read_bytes() == prepared.artifact_bytes
    assert Path(workspace, prepared.provenance_relative_path).read_bytes() == prepared.provenance_bytes
    assert operation_revision_path(workspace, prepared.operation_id, 2).is_file()
    current = OperationJournalStore(workspace).load_current(prepared.operation_id)
    assert current.revision.field("state") == "completed"
    assert current.revision.field("journal_revision") == 3
    return prepared


def pointer(operation_id):
    return parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": operation_id,
            "journal_revision": 1,
        },
    )


with TemporaryDirectory(prefix="portia-issue51-installed-") as temp:
    workspace = Path(temp)
    repo = seed(workspace)

    event_whole = execute(
        workspace,
        repo,
        TeacherReferenceExportScope("teacher_current", event_ref()),
        "whole",
        5,
    )
    participant = execute(
        workspace,
        repo,
        TeacherReferenceExportScope(
            "participant_specific",
            event_ref(),
            event_participant_ref(),
        ),
        "participant",
        10,
    )
    support = execute(
        workspace,
        repo,
        TeacherReferenceExportScope("teacher_current", support_ref()),
        "support",
        15,
    )

    event_history = TeacherReferenceExportHistoryService(workspace).list_for_work(
        event_ref()
    )
    assert {entry.export_id for entry in event_history} == {
        event_whole.export_id,
        participant.export_id,
    }
    assert all(entry.verification_status == "available_verified" for entry in event_history)
    support_history = TeacherReferenceExportHistoryService(workspace).list_for_work(
        support_ref()
    )
    assert len(support_history) == 1
    assert support_history[0].export_id == support.export_id
    assert support_history[0].verification_status == "available_verified"

    partial, _confirmed_at = preparation(
        workspace,
        repo,
        TeacherReferenceExportScope("teacher_current", event_ref()),
        "recovery",
        20,
    )
    OperationJournalStore(workspace).create(
        partial.operation_journal,
        pointer(partial.operation_id),
    )
    staged = stage_deliberate_export_candidates(
        workspace,
        partial.operation_journal,
        artifact_bytes=partial.artifact_bytes,
        export=partial.deliberate_export,
    )
    artifact_step = partial.operation_journal.to_dict()["write_set"][0]
    assert isinstance(artifact_step, dict)

    def fail_after_artifact(checkpoint, step_id):
        if checkpoint == "after_publish" and step_id == artifact_step["step_id"]:
            raise RuntimeError("synthetic installed artifact-only interruption")

    try:
        commit_deliberate_export_candidates(
            workspace,
            partial.operation_journal,
            staged,
            artifact_bytes=partial.artifact_bytes,
            export=partial.deliberate_export,
            lock=partial.operation_lock,
            fault_hook=fail_after_artifact,
        )
    except PortiaOperationPartialCommitError:
        pass
    else:
        raise AssertionError("partial-commit smoke did not interrupt after artifact")

    recovered = TeacherReferenceExportRecoveryService(workspace).recover(
        partial.operation_id,
        observed_at="2026-09-30T18:23:00-04:00",
        committed_at="2026-09-30T18:23:00-04:00",
    )
    assert recovered.code == "recovered"
    assert recovered.initial_disposition == "artifact_only"
    assert recovered.final_disposition == "completed"
    recovered_history = TeacherReferenceExportHistoryService(workspace).list_for_work(
        event_ref()
    )
    assert any(
        entry.export_id == partial.export_id
        and entry.verification_status == "available_verified"
        for entry in recovered_history
    )

    requirements = metadata.requires("pds-portia") or []
    runtime_requirements = [
        value.lower() for value in requirements if "extra ==" not in value.lower()
    ]
    assert not any(
        sibling in requirement
        for sibling in ("concord", "meridian", "quillan", "scoreform", "vitrine")
        for requirement in runtime_requirements
    )

    print(
        json.dumps(
            {
                "event_export_verified": True,
                "support_process_export_verified": True,
                "participant_specific_verified": True,
                "journal_v4_and_lock_v3": True,
                "artifact_and_provenance_verified": True,
                "history_verified": True,
                "partial_commit_recovered": True,
                "no_sibling_runtime_dependency": True,
            },
            sort_keys=True,
        )
    )
'''

    with tempfile.TemporaryDirectory(prefix="portia-issue51-wheel-smoke-") as temp:
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
                "import json,portia; print(json.dumps({'path': portia.__path__[0]}))",
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
            "exports/policy.py",
            "exports/discovery.py",
            "exports/projection.py",
            "exports/inventory.py",
            "exports/rendering.py",
            "exports/preparation.py",
            "exports/execution.py",
            "exports/recovery.py",
            "exports/history.py",
            "menu/teacher_reference_export.py",
        ):
            if not (installed / relative).is_file():
                raise RuntimeError(
                    f"installed Portia wheel is missing Issue #51 file: {relative}"
                )

        core_version = _run(
            [
                str(python),
                "-c",
                "from importlib import metadata; print(metadata.version('pds-core'))",
            ],
            cwd=work,
            env=env,
        ).stdout.strip()
        if core_version != "0.6.3":
            raise RuntimeError(
                f"installed Core version is not 0.6.3: {core_version}"
            )

        result = _run([str(python), "-c", code], cwd=work, env=env)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            raise RuntimeError("installed Issue #51 smoke produced no result")
        payload = json.loads(lines[-1])
        if not all(value is True for value in payload.values()):
            raise RuntimeError(f"installed Issue #51 smoke failed: {payload!r}")


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
    print("Portia installed-wheel Issue #51 teacher-reference export smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
