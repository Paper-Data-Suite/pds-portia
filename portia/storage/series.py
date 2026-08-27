"""Immutable operational revision-series persistence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import (
    PortiaAmbiguousRecoveryError,
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import exclusive_create, guarded_replace, read_json
from portia.storage.paths import (
    finding_suppression_current_path,
    finding_suppression_revision_path,
    operation_current_path,
    operation_revision_path,
    quarantine_current_path,
    quarantine_revision_path,
)


@dataclass(frozen=True, slots=True)
class SeriesState:
    revision: PortiaRecord
    pointer: PortiaRecord
    revision_fingerprint: ContentFingerprint
    pointer_fingerprint: ContentFingerprint


@dataclass(frozen=True, slots=True)
class RecoveryObservation:
    series_id: str
    selected_revision: int | None
    valid_revisions: tuple[int, ...]
    orphan_successors: tuple[int, ...]
    disposition: str


class _RevisionSeries:
    def __init__(
        self,
        root: str | Path,
        *,
        revision_contract: str,
        revision_version: str,
        pointer_contract: str,
        id_field: str,
        revision_field: str,
        previous_field: str,
        revision_path: Callable[[Path, str, int], Path],
        pointer_path: Callable[[Path, str], Path],
    ) -> None:
        self.root = Path(root)
        self.revision_contract = revision_contract
        self.revision_version = revision_version
        self.pointer_contract = pointer_contract
        self.id_field = id_field
        self.revision_field = revision_field
        self.previous_field = previous_field
        self._revision_path = revision_path
        self._pointer_path = pointer_path

    def _paths(self, series_id: str, revision: int) -> tuple[Path, Path]:
        return (
            self._revision_path(self.root, series_id, revision),
            self._pointer_path(self.root, series_id),
        )

    def _parse_revision(self, value: object, path: Path) -> PortiaRecord:
        try:
            return parse_portia_record(
                self.revision_contract,
                self.revision_version,
                value,
            )
        except Exception as exc:
            raise PortiaCorruptionError(f"invalid immutable revision: {path}") from exc

    def _parse_pointer(self, value: object, path: Path) -> PortiaRecord:
        try:
            return parse_portia_record(self.pointer_contract, "1", value)
        except Exception as exc:
            raise PortiaCorruptionError(f"invalid current pointer: {path}") from exc

    def _identity(self, record: PortiaRecord) -> tuple[str, int]:
        data = record.to_dict()
        series_id = data.get(self.id_field)
        revision = data.get(self.revision_field)
        if (
            not isinstance(series_id, str)
            or not isinstance(revision, int)
            or isinstance(revision, bool)
        ):
            raise PortiaCorruptionError("revision is missing its series identity")
        return series_id, revision

    def _load_revisions(self, series_id: str) -> dict[int, PortiaRecord]:
        revisions_root = self._revision_path(self.root, series_id, 1).parent
        if not revisions_root.exists():
            return {}
        records: dict[int, PortiaRecord] = {}
        for path in sorted(revisions_root.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            if path.suffix != ".json" or not path.stem.isascii() or not path.stem.isdigit():
                raise PortiaCorruptionError(
                    f"unexpected artifact in immutable revision namespace: {path}"
                )
            number = int(path.stem)
            if number < 1 or str(number) != path.stem:
                raise PortiaCorruptionError(
                    f"revision filename is not canonical positive decimal: {path}"
                )
            value, _bytes, _fp = read_json(path)
            record = self._parse_revision(value, path)
            record_id, record_number = self._identity(record)
            if record_id != series_id or record_number != number:
                raise PortiaCorruptionError(
                    "revision identity disagrees with its filename"
                )
            records[number] = record
        return records

    def _validate_linear_history(
        self,
        records: dict[int, PortiaRecord],
        *,
        through: int | None = None,
    ) -> None:
        if not records:
            return
        limit = max(records) if through is None else through
        expected_numbers = tuple(range(1, limit + 1))
        present = tuple(number for number in sorted(records) if number <= limit)
        if present != expected_numbers:
            raise PortiaAmbiguousRecoveryError(
                "immutable revision history is noncontiguous"
            )
        for number in expected_numbers:
            predecessor = records[number].to_dict().get(self.previous_field)
            expected_predecessor = None if number == 1 else number - 1
            if predecessor != expected_predecessor:
                raise PortiaAmbiguousRecoveryError(
                    "immutable revision history contains a branch or broken predecessor chain"
                )

    def load_current(self, series_id: str) -> SeriesState:
        pointer_path = self._pointer_path(self.root, series_id)
        pointer_value, _pointer_bytes, pointer_fp = read_json(pointer_path)
        pointer = self._parse_pointer(pointer_value, pointer_path)
        pointer_data = pointer.to_dict()
        if pointer_data.get(self.id_field) != series_id:
            raise PortiaCorruptionError("current pointer identifies another series")
        revision = pointer_data.get(self.revision_field)
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
        ):
            raise PortiaCorruptionError("current pointer has invalid selected revision")

        records = self._load_revisions(series_id)
        if revision not in records:
            raise PortiaCorruptionError(
                "selected revision is absent from immutable history"
            )
        self._validate_linear_history(records, through=revision)
        record = records[revision]
        revision_path = self._revision_path(self.root, series_id, revision)
        _revision_value, _revision_bytes, revision_fp = read_json(revision_path)
        return SeriesState(record, pointer, revision_fp, pointer_fp)

    def create(self, revision: PortiaRecord, pointer: PortiaRecord) -> SeriesState:
        series_id, number = self._identity(revision)
        if number != 1 or revision.to_dict().get(self.previous_field) is not None:
            raise PortiaConflictError(
                "first immutable revision must be revision 1 with null predecessor"
            )
        pointer_data = pointer.to_dict()
        if (
            pointer.contract != self.pointer_contract
            or pointer_data.get(self.id_field) != series_id
            or pointer_data.get(self.revision_field) != 1
        ):
            raise PortiaConflictError(
                "initial current pointer does not select revision 1"
            )
        revision_path, pointer_path = self._paths(series_id, 1)
        revision_fp = exclusive_create(
            revision_path,
            canonical_json_bytes(revision.to_dict()),
        )
        try:
            pointer_fp = exclusive_create(
                pointer_path,
                canonical_json_bytes(pointer.to_dict()),
            )
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "immutable revision is durable but current pointer was not accepted"
            ) from exc
        return SeriesState(revision, pointer, revision_fp, pointer_fp)

    def append(
        self,
        revision: PortiaRecord,
        pointer: PortiaRecord,
        *,
        expected_pointer: ContentFingerprint,
    ) -> SeriesState:
        series_id, number = self._identity(revision)
        current = self.load_current(series_id)
        current_number = current.revision.to_dict()[self.revision_field]
        if not isinstance(current_number, int) or isinstance(current_number, bool):
            raise PortiaCorruptionError("selected revision number is invalid")
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError(
                "current pointer changed since caller observation"
            )
        if (
            number != current_number + 1
            or revision.to_dict().get(self.previous_field) != current_number
        ):
            raise PortiaConflictError(
                "immutable revision must be the exact linear successor"
            )
        pointer_data = pointer.to_dict()
        if (
            pointer.contract != self.pointer_contract
            or pointer_data.get(self.id_field) != series_id
            or pointer_data.get(self.revision_field) != number
        ):
            raise PortiaConflictError(
                "replacement pointer does not select the new revision"
            )
        revision_path, pointer_path = self._paths(series_id, number)
        revision_fp = exclusive_create(
            revision_path,
            canonical_json_bytes(revision.to_dict()),
        )
        try:
            pointer_fp = guarded_replace(
                pointer_path,
                canonical_json_bytes(pointer.to_dict()),
                expected=expected_pointer,
            )
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "successor revision is durable but current pointer did not advance"
            ) from exc
        return SeriesState(revision, pointer, revision_fp, pointer_fp)

    def inspect_recovery(self, series_id: str) -> RecoveryObservation:
        records = self._load_revisions(series_id)
        valid = tuple(sorted(records))
        try:
            current = self.load_current(series_id)
            selected_value = current.revision.to_dict()[self.revision_field]
            if not isinstance(selected_value, int) or isinstance(selected_value, bool):
                raise PortiaCorruptionError("selected revision number is invalid")
            selected: int | None = selected_value
        except PortiaNotFoundError:
            selected = None

        if selected is None:
            if not valid:
                return RecoveryObservation(series_id, None, (), (), "absent")
            self._validate_linear_history(records)
            return RecoveryObservation(
                series_id,
                None,
                valid,
                valid,
                "pointer_missing_manual_recovery",
            )

        orphan = tuple(number for number in valid if number > selected)
        if not orphan:
            return RecoveryObservation(series_id, selected, valid, (), "current")
        if len(orphan) != 1:
            raise PortiaAmbiguousRecoveryError(
                "multiple unselected successors require explicit manual review"
            )
        successor_number = orphan[0]
        if successor_number != selected + 1:
            raise PortiaAmbiguousRecoveryError(
                "unselected successor is not the exact next revision"
            )
        successor = records[successor_number]
        if successor.to_dict().get(self.previous_field) != selected:
            raise PortiaAmbiguousRecoveryError(
                "unselected successor does not extend the selected history"
            )
        return RecoveryObservation(
            series_id,
            selected,
            valid,
            orphan,
            "orphan_linear_successor",
        )


class OperationJournalStore(_RevisionSeries):
    def __init__(self, root: str | Path) -> None:
        super().__init__(
            root,
            revision_contract="operation_journal",
            revision_version="2",
            pointer_contract="operation_current_pointer",
            id_field="operation_id",
            revision_field="journal_revision",
            previous_field="previous_journal_revision",
            revision_path=operation_revision_path,
            pointer_path=operation_current_path,
        )

    def create(self, revision: PortiaRecord, pointer: PortiaRecord) -> SeriesState:
        if (
            revision.contract != "operation_journal"
            or revision.contract_version != "2"
        ):
            raise PortiaConflictError(
                "current operations must use operation_journal@2"
            )
        return super().create(revision, pointer)

    def append(
        self,
        revision: PortiaRecord,
        pointer: PortiaRecord,
        *,
        expected_pointer: ContentFingerprint,
    ) -> SeriesState:
        operation_id = revision.to_dict().get("operation_id")
        if not isinstance(operation_id, str):
            raise PortiaCorruptionError("operation journal is missing operation_id")
        current = self.load_current(operation_id)
        if current.revision.to_dict().get("intent_digest") != revision.to_dict().get(
            "intent_digest"
        ):
            raise PortiaConflictError(
                "operation identity cannot be reused for different intent"
            )
        return super().append(
            revision,
            pointer,
            expected_pointer=expected_pointer,
        )


class QuarantineStore(_RevisionSeries):
    def __init__(self, root: str | Path) -> None:
        super().__init__(
            root,
            revision_contract="quarantine_record",
            revision_version="2",
            pointer_contract="quarantine_current_pointer",
            id_field="quarantine_id",
            revision_field="quarantine_revision",
            previous_field="previous_quarantine_revision",
            revision_path=quarantine_revision_path,
            pointer_path=quarantine_current_path,
        )


class FindingSuppressionStore(_RevisionSeries):
    def __init__(self, root: str | Path) -> None:
        super().__init__(
            root,
            revision_contract="finding_suppression",
            revision_version="1",
            pointer_contract="finding_suppression_current_pointer",
            id_field="suppression_id",
            revision_field="suppression_revision",
            previous_field="previous_suppression_revision",
            revision_path=finding_suppression_revision_path,
            pointer_path=finding_suppression_current_path,
        )
