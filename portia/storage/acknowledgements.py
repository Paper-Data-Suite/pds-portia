"""Append-only persistence for Portia Finding Acknowledgements."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import exclusive_create, read_json
from portia.storage.paths import finding_acknowledgement_path


@dataclass(frozen=True, slots=True)
class StoredAcknowledgement:
    record: PortiaRecord
    path: Path
    fingerprint: ContentFingerprint


class FindingAcknowledgementStore:
    """Persist acknowledgement as append-only operational evidence."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def create(self, record: PortiaRecord) -> StoredAcknowledgement:
        if (
            record.contract != "finding_acknowledgement"
            or record.contract_version != "1"
        ):
            raise PortiaConflictError(
                "acknowledgement must be finding_acknowledgement@1"
            )
        data = record.to_dict()
        acknowledgement_id = data.get("acknowledgement_id")
        if not isinstance(acknowledgement_id, str):
            raise PortiaCorruptionError("acknowledgement is missing its identity")
        path = finding_acknowledgement_path(self.root, acknowledgement_id)
        fingerprint = exclusive_create(path, canonical_json_bytes(data))
        return StoredAcknowledgement(record, path, fingerprint)

    def load(self, acknowledgement_id: str) -> StoredAcknowledgement:
        path = finding_acknowledgement_path(self.root, acknowledgement_id)
        value, _bytes, fingerprint = read_json(path)
        try:
            record = parse_portia_record("finding_acknowledgement", "1", value)
        except Exception as exc:
            raise PortiaCorruptionError(
                f"invalid persisted Finding Acknowledgement: {path}"
            ) from exc
        if record.to_dict().get("acknowledgement_id") != acknowledgement_id:
            raise PortiaCorruptionError(
                "Finding Acknowledgement identity disagrees with its path"
            )
        return StoredAcknowledgement(record, path, fingerprint)
