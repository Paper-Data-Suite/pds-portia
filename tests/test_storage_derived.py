from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.acknowledgements import FindingAcknowledgementStore
from portia.storage.errors import PortiaConflictError
from portia.storage.integrity import source_snapshot_digest
from portia.storage.paths import (
    derived_current_path,
    derived_data_path,
    derived_metadata_path,
    legacy_derived_data_path,
    legacy_derived_metadata_path,
)

ROOT = Path(__file__).resolve().parents[1]


def _fixture(relative: str) -> dict[str, object]:
    path = ROOT / relative
    if not path.exists():
        pytest.skip("repository fixtures are unavailable in the reconstructed test tree")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_source_snapshot_digest_matches_accepted_issue13_fixture() -> None:
    value = _fixture(
        "tests/schema_validation/fixtures/issue-13/source-snapshot/valid/"
        "complete-current-state-view.json"
    )
    snapshot = parse_portia_record("source_snapshot", "1", value)
    assert source_snapshot_digest(snapshot) == value["source_snapshot_digest"]


def test_derived_paths_use_bounded_writer_layout_and_preserve_legacy_helpers(
    tmp_path: Path,
) -> None:
    work = ExactPortiaWorkRef(
        module_id="portia",
        class_id="class_english10_p2",
        work_id="evt_example",
        work_kind="event",
        contract_version="2",
    )
    work_scope = {"scope": "work", "work_ref": work.to_dict()}
    assert derived_data_path(
        tmp_path,
        "current_state_view",
        work_scope,
        "dgen_example",
    ) == (
        tmp_path
        / "portia"
        / "derived-v2"
        / "pt_751b1943be160f1db511eddae43de8ef"
        / "generations"
        / "pt_a677e8eb837245e8362aa3b29023a008"
        / "data.json"
    )
    assert legacy_derived_data_path(
        tmp_path,
        "current_state_view",
        work_scope,
        "dgen_example",
    ) == (
        tmp_path
        / "classes"
        / "class_english10_p2"
        / "modules"
        / "portia"
        / "work"
        / "evt_example"
        / "derived"
        / "current_state_view"
        / "generations"
        / "dgen_example"
        / "data.json"
    )

    workspace_scope = {"scope": "workspace", "workspace_id": "local_workspace"}
    assert derived_metadata_path(
        tmp_path,
        "incoming_reference_index",
        workspace_scope,
        "dgen_actor_incoming_complete_01",
    ) == (
        tmp_path
        / "portia"
        / "derived-v2"
        / "pt_cdca676a18cc5070e9e0a918b8ff7131"
        / "generations"
        / "pt_060bd4690d29abded082196a9ce8f6d5"
        / "metadata.json"
    )
    assert legacy_derived_metadata_path(
        tmp_path,
        "incoming_reference_index",
        workspace_scope,
        "dgen_actor_incoming_complete_01",
    ) == (
        tmp_path
        / "portia"
        / "derived"
        / "incoming_reference_index"
        / "workspace_local_workspace"
        / "generations"
        / "dgen_actor_incoming_complete_01"
        / "metadata.json"
    )
    assert derived_current_path(
        tmp_path,
        "incoming_reference_index",
        workspace_scope,
    ).name == "current.json"


def test_workspace_derived_path_never_manufactures_workspace_identity(
    tmp_path: Path,
) -> None:
    with pytest.raises(Exception, match="authoritative workspace_id"):
        derived_current_path(
            tmp_path,
            "incoming_reference_index",
            {"scope": "workspace"},
        )


def test_finding_acknowledgement_is_append_only(tmp_path: Path) -> None:
    value = _fixture(
        "tests/schema_validation/fixtures/issue-13/finding-acknowledgement/valid/"
        "reviewed-finding.json"
    )
    record = parse_portia_record("finding_acknowledgement", "1", value)
    store = FindingAcknowledgementStore(tmp_path)
    stored = store.create(record)
    loaded = store.load(str(value["acknowledgement_id"]))
    assert loaded.record == record
    assert loaded.fingerprint == stored.fingerprint
    with pytest.raises(PortiaConflictError):
        store.create(record)
