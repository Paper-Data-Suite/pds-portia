from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.paths import (
    legacy_work_storage_history_path,
    work_storage_history_path,
)
from portia.storage.repository import PortiaRepository


def _event_wire(*, status: str, updated_at: str) -> dict[str, object]:
    return {
        "schema_version": "2",
        "record_type": "portia_work",
        "work_kind": "event",
        "module_id": "portia",
        "class_id": "class_storage",
        "work_id": "evt_storage",
        "school_year": "2026-2027",
        "status": status,
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-08-26T12:00:00-04:00",
        "created_by": {"type": "system_process", "process_id": "storage_test"},
        "updated_at": updated_at,
        "updated_by": {"type": "system_process", "process_id": "storage_test"},
    }


def _work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_storage",
        work_id="evt_storage",
        work_kind="event",
        contract_version="2",
    )


def test_work_root_replacement_is_expected_state_guarded_and_preserves_prior_bytes(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = _work_ref()
    initial = parse_portia_record(
        "event", "2", _event_wire(status="draft", updated_at="2026-08-26T12:00:00-04:00")
    )
    created = repository.create_work(work, initial)

    replacement = parse_portia_record(
        "event", "2", _event_wire(status="draft", updated_at="2026-08-26T12:05:00-04:00")
    )
    stored = repository.replace_work(work, replacement, expected=created.fingerprint)
    assert repository.load_work(work).record.to_dict() == replacement.to_dict()
    assert stored.fingerprint != created.fingerprint

    history = work_storage_history_path(
        tmp_path,
        work,
        "event",
        "evt_storage",
        created.fingerprint.digest,
    )
    assert history.is_file()

    with pytest.raises(PortiaConflictError):
        repository.replace_work(work, replacement, expected=created.fingerprint)


def test_work_replacement_reuses_exact_legacy_history_without_migration(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = _work_ref()
    initial = parse_portia_record(
        "event",
        "2",
        _event_wire(
            status="draft",
            updated_at="2026-08-26T12:00:00-04:00",
        ),
    )
    created = repository.create_work(work, initial)
    legacy = legacy_work_storage_history_path(
        tmp_path,
        work,
        "event",
        "evt_storage",
        created.fingerprint.digest,
    )
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(canonical_json_bytes(initial.to_dict()))

    replacement = parse_portia_record(
        "event",
        "2",
        _event_wire(
            status="draft",
            updated_at="2026-08-26T12:05:00-04:00",
        ),
    )
    repository.replace_work(work, replacement, expected=created.fingerprint)

    current = work_storage_history_path(
        tmp_path,
        work,
        "event",
        "evt_storage",
        created.fingerprint.digest,
    )
    assert legacy.is_file()
    assert not current.exists()
    assert repository.load_work(work).record.to_dict() == replacement.to_dict()


def test_work_replacement_fails_closed_when_current_and_legacy_history_both_exist(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = _work_ref()
    initial = parse_portia_record(
        "event",
        "2",
        _event_wire(
            status="draft",
            updated_at="2026-08-26T12:00:00-04:00",
        ),
    )
    created = repository.create_work(work, initial)
    prior = canonical_json_bytes(initial.to_dict())
    current = work_storage_history_path(
        tmp_path,
        work,
        "event",
        "evt_storage",
        created.fingerprint.digest,
    )
    legacy = legacy_work_storage_history_path(
        tmp_path,
        work,
        "event",
        "evt_storage",
        created.fingerprint.digest,
    )
    current.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    current.write_bytes(prior)
    legacy.write_bytes(prior)

    replacement = parse_portia_record(
        "event",
        "2",
        _event_wire(
            status="draft",
            updated_at="2026-08-26T12:05:00-04:00",
        ),
    )
    with pytest.raises(PortiaCorruptionError, match="current and legacy"):
        repository.replace_work(
            work,
            replacement,
            expected=created.fingerprint,
        )


def test_bounded_work_and_child_enumeration_is_sorted_and_strict(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    first = _work_ref()
    second = ExactPortiaWorkRef(
        class_id="class_storage",
        work_id="evt_storage_b",
        work_kind="event",
        contract_version="2",
    )
    repository.create_work(first, parse_portia_record("event", "2", _event_wire(status="draft", updated_at="2026-08-26T12:00:00-04:00")))
    second_wire = _event_wire(status="draft", updated_at="2026-08-26T12:00:00-04:00")
    second_wire["work_id"] = "evt_storage_b"
    repository.create_work(second, parse_portia_record("event", "2", second_wire))
    assert [item.record.logical_id for item in repository.list_events("class_storage")] == [
        "evt_storage",
        "evt_storage_b",
    ]

    collection = (
        tmp_path
        / "classes/class_storage/modules/portia/work/evt_storage/records/event_participant"
    )
    collection.mkdir(parents=True)
    (collection / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(PortiaCorruptionError):
        repository.list_event_participants(first)
