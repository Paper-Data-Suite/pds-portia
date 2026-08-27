"""Bounded Actor Directory inventory reads layered on the #38 repository."""

from __future__ import annotations

from portia.models import parse_portia_record
from portia.models.identifiers import validate_external_id, validate_portia_id
from portia.storage.errors import PortiaCorruptionError, PortiaOwnershipError
from portia.storage.io import read_json
from portia.storage.paths import actor_directory_removal_path, actor_root, portia_root
from portia.storage.repository import PortiaRepository, StoredRecord


class ActorDirectoryRepository(PortiaRepository):
    """Extend guarded #38 persistence with strict bounded Actor inventory reads."""

    def list_actor_children(
        self,
        actor_id: str,
        contract: str,
        *,
        version: str = "1",
    ) -> tuple[StoredRecord, ...]:
        self.load_actor(actor_id)
        kind = validate_external_id(contract, "record_kind")
        collection = actor_root(self.workspace_root, actor_id) / "records" / kind
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError(
                f"Actor child collection is not a directory: {collection}"
            )

        records: list[StoredRecord] = []
        for path in sorted(collection.iterdir(), key=lambda item: item.name):
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError(
                    f"unexpected artifact in Actor child collection: {path}"
                )
            try:
                record_id = validate_external_id(path.stem, "record_id")
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"Actor child filename has invalid identity: {path}"
                ) from exc
            records.append(
                self.load_actor_child(actor_id, kind, version, record_id)
            )
        return tuple(records)

    def load_actor_directory_removal(
        self,
        removal_id: str,
        *,
        version: str = "1",
    ) -> StoredRecord:
        identifier = validate_portia_id(removal_id, "rmv_", "removal_id")
        path = actor_directory_removal_path(self.workspace_root, identifier)
        value, _bytes, fingerprint = read_json(path)
        try:
            record = parse_portia_record(
                "actor_directory_exceptional_removal",
                version,
                value,
            )
        except Exception as exc:
            raise PortiaCorruptionError(
                "persisted Actor exceptional-removal certificate is invalid: "
                f"{path}"
            ) from exc
        if record.module_id != "portia" or record.logical_id != identifier:
            raise PortiaOwnershipError(
                "Actor exceptional-removal identity disagrees with canonical filename"
            )
        return StoredRecord(record, path, fingerprint)

    def list_actor_directory_removals(
        self,
        *,
        version: str = "1",
    ) -> tuple[StoredRecord, ...]:
        collection = portia_root(self.workspace_root) / "actor-directory-removals"
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError(
                "Actor exceptional-removal collection is not a directory"
            )

        records: list[StoredRecord] = []
        for path in sorted(collection.iterdir(), key=lambda item: item.name):
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError(
                    f"unexpected artifact in Actor removal collection: {path}"
                )
            try:
                removal_id = validate_portia_id(path.stem, "rmv_", "removal_id")
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"Actor removal filename has invalid identity: {path}"
                ) from exc
            records.append(
                self.load_actor_directory_removal(removal_id, version=version)
            )
        return tuple(records)
