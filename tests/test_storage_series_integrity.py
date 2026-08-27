from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage.errors import PortiaAmbiguousRecoveryError
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, guarded_replace
from portia.storage.paths import operation_current_path, operation_revision_path
from portia.storage.series import OperationJournalStore

ROOT = Path(__file__).resolve().parents[1]


def _fixture() -> dict[str, object]:
    path = (
        ROOT
        / "tests/schema_validation/fixtures/issue-14/actor-aware-operations/"
        "operation-journal/valid/create-actor.json"
    )
    if not path.exists():
        pytest.skip("repository fixtures are unavailable in the reconstructed test tree")
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _journal(value: dict[str, object], revision: int, previous: int | None):
    candidate = dict(value)
    candidate["journal_revision"] = revision
    candidate["previous_journal_revision"] = previous
    return parse_portia_record("operation_journal", "2", candidate)


def _pointer(operation_id: str, revision: int):
    return parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": operation_id,
            "journal_revision": revision,
        },
    )


def test_selected_revision_chain_rejects_branching_history(tmp_path: Path) -> None:
    value = _fixture()
    operation_id = str(value["operation_id"])
    store = OperationJournalStore(tmp_path)
    revision1 = _journal(value, 1, None)
    pointer1 = _pointer(operation_id, 1)
    initial = store.create(revision1, pointer1)

    revision2 = _journal(value, 2, 1)
    pointer2 = _pointer(operation_id, 2)
    second = store.append(
        revision2,
        pointer2,
        expected_pointer=initial.pointer_fingerprint,
    )

    revision3 = _journal(value, 3, 1)
    exclusive_create(
        operation_revision_path(tmp_path, operation_id, 3),
        canonical_json_bytes(revision3.to_dict()),
    )
    pointer3 = _pointer(operation_id, 3)
    guarded_replace(
        operation_current_path(tmp_path, operation_id),
        canonical_json_bytes(pointer3.to_dict()),
        expected=second.pointer_fingerprint,
    )

    with pytest.raises(PortiaAmbiguousRecoveryError, match="branch"):
        store.load_current(operation_id)
