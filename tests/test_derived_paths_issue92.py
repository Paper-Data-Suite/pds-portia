from __future__ import annotations

from pathlib import Path

from portia.storage.derived import DerivedStore
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.paths import (
    derived_current_path,
    derived_data_path,
    derived_metadata_path,
    legacy_derived_current_path,
    legacy_derived_data_path,
    legacy_derived_metadata_path,
    workspace_relative,
)
from portia.workflows import IntegrityWorkflowService
from tests.test_workflow_integrity_operators import (
    _binding,
    _completed_operation,
    _finding,
    _install_generation,
)

PROJECTION = "active_integrity_finding_index"


def _operation_scope() -> dict[str, object]:
    return IntegrityWorkflowService.operation_scope("op_integrity_authority")


def _convert_current_generation_to_legacy(
    root: Path,
    scope: dict[str, object],
    generation_id: str,
) -> tuple[bytes, bytes, bytes]:
    store = DerivedStore(root)
    selected = store.load_current(PROJECTION, scope, require_fresh=False)

    current_new = derived_current_path(root, PROJECTION, scope)
    metadata_new = derived_metadata_path(root, PROJECTION, scope, generation_id)
    data_new = derived_data_path(root, PROJECTION, scope, generation_id)

    current_legacy = legacy_derived_current_path(root, PROJECTION, scope)
    metadata_legacy = legacy_derived_metadata_path(
        root,
        PROJECTION,
        scope,
        generation_id,
    )
    data_legacy = legacy_derived_data_path(
        root,
        PROJECTION,
        scope,
        generation_id,
    )

    current_bytes = current_new.read_bytes()
    data_bytes = data_new.read_bytes()
    metadata_value = selected.metadata.to_dict()
    artifact = metadata_value["data_artifact"]
    assert isinstance(artifact, dict)
    artifact["workspace_relative_path"] = workspace_relative(root, data_legacy)
    metadata_bytes = canonical_json_bytes(metadata_value)

    data_legacy.parent.mkdir(parents=True, exist_ok=True)
    data_legacy.write_bytes(data_bytes)
    metadata_legacy.write_bytes(metadata_bytes)
    current_legacy.parent.mkdir(parents=True, exist_ok=True)
    current_legacy.write_bytes(current_bytes)

    generation_root = data_new.parent
    generations_root = generation_root.parent
    projection_root = current_new.parent

    data_new.unlink()
    metadata_new.unlink()
    current_new.unlink()

    generation_root.rmdir()
    generations_root.rmdir()
    projection_root.rmdir()

    return current_bytes, metadata_bytes, data_bytes


def test_bounded_derived_layout_uses_fixed_tokens_and_leaves(tmp_path: Path) -> None:
    _completed_operation(tmp_path)
    scope = _operation_scope()
    generation_id = "dgen_issue92_bounded"
    _install_generation(
        tmp_path,
        scope,
        [],
        {
            "operation_id": "op_integrity_authority",
            "journal_revision": 3,
            "contract_version": "2",
        },
        generation_id=generation_id,
    )

    current = derived_current_path(tmp_path, PROJECTION, scope)
    metadata = derived_metadata_path(tmp_path, PROJECTION, scope, generation_id)
    data = derived_data_path(tmp_path, PROJECTION, scope, generation_id)

    current_relative = workspace_relative(tmp_path, current)
    metadata_relative = workspace_relative(tmp_path, metadata)
    data_relative = workspace_relative(tmp_path, data)

    assert current_relative.startswith("portia/derived-v2/pt_")
    assert metadata_relative.startswith("portia/derived-v2/pt_")
    assert data_relative.startswith("portia/derived-v2/pt_")
    assert current_relative.endswith("/current.json")
    assert metadata_relative.endswith("/metadata.json")
    assert data_relative.endswith("/data.json")
    assert len(current_relative) == 66
    assert len(metadata_relative) == 115
    assert len(data_relative) == 111


def test_legacy_derived_generation_loads_without_migration(tmp_path: Path) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = _operation_scope()
    generation_id = "dgen_issue92_legacy"
    _install_generation(
        tmp_path,
        scope,
        [],
        operation_ref,
        generation_id=generation_id,
    )

    before_current, before_metadata, before_data = _convert_current_generation_to_legacy(
        tmp_path,
        scope,
        generation_id,
    )

    store = DerivedStore(tmp_path)
    loaded = store.load_current(PROJECTION, scope, require_fresh=False)

    assert loaded.metadata.to_dict()["generation_id"] == generation_id
    assert legacy_derived_current_path(tmp_path, PROJECTION, scope).read_bytes() == (
        before_current
    )
    assert legacy_derived_metadata_path(
        tmp_path,
        PROJECTION,
        scope,
        generation_id,
    ).read_bytes() == before_metadata
    assert legacy_derived_data_path(
        tmp_path,
        PROJECTION,
        scope,
        generation_id,
    ).read_bytes() == before_data
    assert not derived_current_path(tmp_path, PROJECTION, scope).exists()


def test_historical_integrity_reader_resolves_exact_legacy_generation(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = _operation_scope()
    generation_id = "dgen_issue92_legacy_history"
    finding = _finding(
        finding_key="fnd_issue92_legacy",
        evaluation_key="evl_issue92_legacy",
    )
    _install_generation(
        tmp_path,
        scope,
        [finding],
        operation_ref,
        generation_id=generation_id,
    )
    _convert_current_generation_to_legacy(
        tmp_path,
        scope,
        generation_id,
    )

    service = IntegrityWorkflowService(tmp_path)
    resolved = service._historical_exact_finding(
        scope,
        _binding(finding),
    )

    assert resolved.to_dict() == finding.to_dict()


def test_new_generation_cuts_over_from_legacy_without_rewriting_legacy(
    tmp_path: Path,
) -> None:
    operation_ref = _completed_operation(tmp_path)
    scope = _operation_scope()
    old_generation = "dgen_issue92_legacy"
    _install_generation(
        tmp_path,
        scope,
        [],
        operation_ref,
        generation_id=old_generation,
    )
    old_current, old_metadata, old_data = _convert_current_generation_to_legacy(
        tmp_path,
        scope,
        old_generation,
    )

    new_generation = "dgen_issue92_bounded_successor"
    _install_generation(
        tmp_path,
        scope,
        [],
        operation_ref,
        generation_id=new_generation,
    )

    bounded_current = derived_current_path(tmp_path, PROJECTION, scope)
    legacy_current = legacy_derived_current_path(tmp_path, PROJECTION, scope)
    assert bounded_current.is_file()
    assert legacy_current.read_bytes() == old_current

    loaded = DerivedStore(tmp_path).load_current(
        PROJECTION,
        scope,
        require_fresh=False,
    )
    assert loaded.metadata.to_dict()["generation_id"] == new_generation
    artifact = loaded.metadata.to_dict()["data_artifact"]
    assert isinstance(artifact, dict)
    assert artifact["workspace_relative_path"] == workspace_relative(
        tmp_path,
        derived_data_path(
            tmp_path,
            PROJECTION,
            scope,
            new_generation,
        ),
    )

    assert legacy_derived_metadata_path(
        tmp_path,
        PROJECTION,
        scope,
        old_generation,
    ).read_bytes() == old_metadata
    assert legacy_derived_data_path(
        tmp_path,
        PROJECTION,
        scope,
        old_generation,
    ).read_bytes() == old_data
