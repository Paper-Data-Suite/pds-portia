from __future__ import annotations

import hashlib
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from portia.exports.execution import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionSuccess,
)
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.derived import DerivedStore
from portia.storage.paths import (
    derived_metadata_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.repository import PortiaRepository
from portia.storage.staging import cleanup_staged, publish_staged, stage_bytes
from portia.workflows import IntegrityWorkflowService
from tests.test_teacher_reference_export_execution import (
    CONFIRMED,
    _execution_service,
    _prepare,
    _seed,
)
from tests.test_workflow_integrity_operators import (
    _completed_operation,
    _install_generation,
)

TARGET_DEEP_WORKSPACE_LENGTH = 119
PROJECTION = "active_integrity_finding_index"


@pytest.fixture
def deep_workspace(tmp_path: Path) -> Iterator[Path]:
    """Create a real workspace rooted at ~119 absolute characters.

    The system temporary root is used directly so pytest's own nested temporary
    directory does not dominate the requested geometry. ``tmp_path`` supplies
    only a collision-resistant seed.
    """
    base = Path(tempfile.gettempdir()).resolve()
    token = hashlib.sha256(str(tmp_path.resolve()).encode("utf-8")).hexdigest()[:16]
    prefix = f"pds-portia-issue92-{token}-"
    desired_leaf = TARGET_DEEP_WORKSPACE_LENGTH - len(str(base)) - 1
    if desired_leaf >= len(prefix):
        leaf = prefix + ("d" * (desired_leaf - len(prefix)))
    else:
        # An unusually long host temp root is already at least as stressful.
        leaf = prefix.rstrip("-")
    root = base / leaf

    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    resolved = root.resolve()
    assert len(str(resolved)) >= TARGET_DEEP_WORKSPACE_LENGTH

    try:
        yield resolved
    finally:
        shutil.rmtree(resolved, ignore_errors=True)


def _deep_event_wire(*, updated_at: str) -> dict[str, object]:
    return {
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
        "created_by": {"type": "system_process", "process_id": "issue92_deep"},
        "updated_at": updated_at,
        "updated_by": {"type": "system_process", "process_id": "issue92_deep"},
    }


def _deep_work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_deep",
        work_id="evt_deep",
        work_kind="event",
        contract_version="2",
    )


def test_deep_workspace_storage_staging_and_history(
    deep_workspace: Path,
) -> None:
    root = deep_workspace

    staged = stage_bytes(
        root,
        "op_issue92_deep",
        "step_issue92_deep",
        "portia/deep-qualification/artifact.json",
        b'{"qualified":true}\n',
    )
    accepted = publish_staged(root, staged, action="exclusive_create")
    assert staged.destination_path.read_bytes() == b'{"qualified":true}\n'
    assert accepted == staged.fingerprint
    cleanup_staged(root, staged)
    assert not staged.staging_path.exists()

    repository = PortiaRepository(root)
    work = _deep_work_ref()
    initial = parse_portia_record(
        "event",
        "2",
        _deep_event_wire(updated_at="2026-10-03T12:00:00-04:00"),
    )
    created = repository.create_work(work, initial)
    replacement = parse_portia_record(
        "event",
        "2",
        _deep_event_wire(updated_at="2026-10-03T12:05:00-04:00"),
    )
    stored = repository.replace_work(
        work,
        replacement,
        expected=created.fingerprint,
    )

    assert stored.fingerprint != created.fingerprint
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
    assert history.read_bytes()


def test_deep_workspace_derived_install_and_reload(
    deep_workspace: Path,
) -> None:
    root = deep_workspace
    operation_ref = _completed_operation(root)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    generation_id = "dgen_issue92_deep"

    _install_generation(
        root,
        scope,
        [],
        operation_ref,
        generation_id=generation_id,
    )

    loaded = DerivedStore(root).load_current(
        PROJECTION,
        scope,
        require_fresh=True,
    )
    assert loaded.metadata.to_dict()["generation_id"] == generation_id

    metadata = derived_metadata_path(
        root,
        PROJECTION,
        scope,
        generation_id,
    )
    relative = workspace_relative(root, metadata)
    assert len(relative) == 115
    assert metadata.is_file()
    assert len(str(metadata)) >= 235


def test_deep_workspace_teacher_reference_export_transaction(
    deep_workspace: Path,
) -> None:
    root = deep_workspace
    repository = _seed(root)
    preparation = _prepare(root, repository)
    service = _execution_service(root, repository)

    result = service.execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    artifact = root / preparation.artifact_relative_path
    provenance = root / preparation.provenance_relative_path
    assert artifact.read_bytes() == preparation.artifact_bytes
    assert provenance.read_bytes() == preparation.provenance_bytes
    assert len(workspace_relative(root, artifact)) == 45
