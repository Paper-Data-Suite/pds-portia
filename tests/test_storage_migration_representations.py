from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaNotFoundError,
    PortiaOwnershipError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import guarded_replace
from portia.storage.migration_representations import (
    MigrationRepresentationStore,
    version_qualified_representation_path,
)
from portia.storage.paths import work_manifest_path, work_record_path
from portia.storage.repository import PortiaRepository
from tests.workflow_helpers import (
    event_record,
    event_ref,
    event_wire,
    participant_record,
    participant_wire,
)


def _event_v1() -> PortiaRecord:
    value = event_wire()
    value["schema_version"] = "1"
    return parse_portia_record("event", "1", value)


def _participant_v2() -> PortiaRecord:
    value = participant_wire()
    value["schema_version"] = "2"
    return parse_portia_record("event_participant", "2", value)


def _participant_ref(
    work: ExactPortiaWorkRef,
    version: str,
    participant_id: str = "ep_alpha",
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id=participant_id,
            contract_version=version,
        ),
    )


def test_version_qualified_path_is_not_technical_storage_history(tmp_path: Path) -> None:
    work = event_ref()
    first = version_qualified_representation_path(
        tmp_path, work, "event_participant", "ep_alpha", "2"
    )
    second = version_qualified_representation_path(
        tmp_path, work, "event_participant", "ep_alpha", "3"
    )

    assert first != second
    assert first.as_posix().endswith(
        "/representations/event_participant/ep_alpha/2.json"
    )
    assert "storage_revisions" not in first.as_posix()


def test_work_source_must_be_preserved_before_destination_creation(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    source = event_ref(version="1")
    repository.create_work(source, _event_v1())
    store = MigrationRepresentationStore(tmp_path, repository=repository)

    with pytest.raises(PortiaNotFoundError):
        store.create_destination_work_representation(source, event_record())


def test_preserve_current_work_is_exact_and_does_not_change_current(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    source = event_ref(version="1")
    current = repository.create_work(source, _event_v1())
    store = MigrationRepresentationStore(tmp_path, repository=repository)

    preserved = store.preserve_current_work_representation(
        source, expected=current.fingerprint
    )

    assert preserved.fingerprint == current.fingerprint
    assert preserved.path != current.path
    assert repository.load_work(source).fingerprint == current.fingerprint


def test_work_destination_can_coexist_before_current_selection(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    source = event_ref(version="1")
    current = repository.create_work(source, _event_v1())
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    store.preserve_current_work_representation(source, expected=current.fingerprint)

    destination = event_record()
    created = store.create_destination_work_representation(source, destination)

    assert created.record.contract_version == "2"
    assert repository.load_work(source).record.contract_version == "1"
    assert store.load_work_representation(event_ref(version="2")).record.to_dict() == (
        destination.to_dict()
    )


def test_work_exact_old_version_resolves_after_explicit_external_switch(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    source = event_ref(version="1")
    current = repository.create_work(source, _event_v1())
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    preserved = store.preserve_current_work_representation(
        source, expected=current.fingerprint
    )
    destination = event_record()
    created = store.create_destination_work_representation(source, destination)

    guarded_replace(
        work_manifest_path(tmp_path, source),
        canonical_json_bytes(destination.to_dict()),
        expected=current.fingerprint,
    )

    old = store.load_work_representation(source)
    new = store.load_work_representation(event_ref(version="2"))
    assert old.path == preserved.path
    assert old.record.contract_version == "1"
    assert new.record.contract_version == "2"
    assert new.fingerprint == created.fingerprint


def test_missing_work_version_never_falls_back_to_another_version(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    current = repository.create_work(event_ref(), event_record())
    assert current.record.contract_version == "2"
    store = MigrationRepresentationStore(tmp_path, repository=repository)

    with pytest.raises(PortiaNotFoundError):
        store.load_work_representation(event_ref(version="1"))


def test_record_source_and_destination_coexist_without_current_selection(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    source_record = _participant_v2()
    current = repository.create_work_record(work, source_record)
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)

    preserved = store.preserve_current_work_record_representation(
        source, expected=current.fingerprint
    )
    destination = participant_record()
    created = store.create_destination_work_record_representation(
        source, destination
    )

    still_current = repository.load_work_record(
        work, "event_participant", "2", "ep_alpha"
    )
    assert still_current.fingerprint == current.fingerprint
    assert preserved.record.contract_version == "2"
    assert created.record.contract_version == "3"


def test_record_exact_old_version_resolves_after_explicit_external_switch(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    source_record = _participant_v2()
    current = repository.create_work_record(work, source_record)
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    preserved = store.preserve_current_work_record_representation(
        source, expected=current.fingerprint
    )
    destination = participant_record()
    destination_preserved = store.create_destination_work_record_representation(
        source, destination
    )

    guarded_replace(
        work_record_path(tmp_path, work, "event_participant", "ep_alpha"),
        canonical_json_bytes(destination.to_dict()),
        expected=current.fingerprint,
    )

    old = store.load_work_record_representation(source)
    new = store.load_work_record_representation(_participant_ref(work, "3"))
    assert old.path == preserved.path
    assert old.record.contract_version == "2"
    assert new.record.contract_version == "3"
    assert new.fingerprint == destination_preserved.fingerprint


def test_missing_record_version_never_selects_current_version(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    repository.create_work_record(work, participant_record())
    store = MigrationRepresentationStore(tmp_path, repository=repository)

    with pytest.raises(PortiaNotFoundError):
        store.load_work_record_representation(_participant_ref(work, "2"))


def test_destination_must_preserve_stable_record_identity(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    source_record = _participant_v2()
    current = repository.create_work_record(work, source_record)
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    store.preserve_current_work_record_representation(
        source, expected=current.fingerprint
    )

    with pytest.raises(PortiaOwnershipError, match="stable record identifier"):
        store.create_destination_work_record_representation(
            source,
            participant_record(participant_id="ep_beta"),
        )


def test_destination_same_version_is_not_a_migration(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    source_record = _participant_v2()
    current = repository.create_work_record(work, source_record)
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    store.preserve_current_work_record_representation(
        source, expected=current.fingerprint
    )

    with pytest.raises(PortiaConflictError, match="must differ"):
        store.create_destination_work_record_representation(
            source,
            _participant_v2(),
        )


def test_preserve_requires_exact_expected_fingerprint(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    repository.create_work_record(work, _participant_v2())
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    wrong = ContentFingerprint(digest="0" * 64, byte_length=0)

    with pytest.raises(PortiaConflictError, match="fingerprint"):
        store.preserve_current_work_record_representation(source, expected=wrong)


def test_version_destination_identity_is_exclusive(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record())
    current = repository.create_work_record(work, _participant_v2())
    source = _participant_ref(work, "2")
    store = MigrationRepresentationStore(tmp_path, repository=repository)
    store.preserve_current_work_record_representation(
        source, expected=current.fingerprint
    )
    store.create_destination_work_record_representation(source, participant_record())

    with pytest.raises(PortiaConflictError, match="already exists"):
        store.create_destination_work_record_representation(
            source, participant_record()
        )
