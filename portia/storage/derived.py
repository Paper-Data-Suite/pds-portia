"""Complete immutable derived-generation installation and exact current loading."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.integrity import validate_source_snapshot
from portia.storage.io import exclusive_create, guarded_replace, read_json
from portia.storage.paths import (
    derived_current_path,
    derived_data_path,
    derived_metadata_path,
    workspace_relative,
)


@dataclass(frozen=True, slots=True)
class DerivedGeneration:
    """One newly installed complete immutable generation."""

    metadata: PortiaRecord
    data_fingerprint: ContentFingerprint
    metadata_fingerprint: ContentFingerprint
    current_pointer_fingerprint: ContentFingerprint


@dataclass(frozen=True, slots=True)
class DerivedCurrentState:
    """One explicitly selected, verified current derived generation."""

    metadata: PortiaRecord
    pointer: PortiaRecord
    data: object
    data_fingerprint: ContentFingerprint
    metadata_fingerprint: ContentFingerprint
    pointer_fingerprint: ContentFingerprint


def _mapping(value: object, *, description: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PortiaCorruptionError(f"{description} must be a JSON object")
    return value


def _parse_timestamp(value: object, *, description: str) -> datetime:
    if not isinstance(value, str):
        raise PortiaCorruptionError(f"{description} must be an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PortiaCorruptionError(f"{description} is not a valid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PortiaCorruptionError(f"{description} must include an explicit offset")
    return parsed


class DerivedStore:
    """Install and load derived state without treating it as canonical authority."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _validate_metadata(
        self,
        metadata: PortiaRecord,
        data_bytes: bytes,
    ) -> tuple[str, str, dict[str, Any], ContentFingerprint, Path]:
        if (
            metadata.contract != "derived_index_metadata"
            or metadata.contract_version != "1"
        ):
            raise PortiaConflictError("metadata must be derived_index_metadata@1")
        data = metadata.to_dict()
        generation_id = data.get("generation_id")
        projection_kind = data.get("projection_kind")
        scope = data.get("projection_scope")
        if not isinstance(generation_id, str) or not isinstance(projection_kind, str):
            raise PortiaCorruptionError("derived metadata is missing generation identity")
        if not isinstance(scope, dict):
            raise PortiaCorruptionError("derived metadata is missing projection scope")

        snapshot_value = data.get("source_snapshot")
        try:
            snapshot = parse_portia_record("source_snapshot", "1", snapshot_value)
        except Exception as exc:
            raise PortiaCorruptionError(
                "derived metadata embeds an invalid Source Snapshot"
            ) from exc
        snapshot_data = snapshot.to_dict()
        if snapshot_data.get("projection_kind") != projection_kind:
            raise PortiaConflictError("metadata projection kind disagrees with Source Snapshot")
        if snapshot_data.get("projection_scope") != scope:
            raise PortiaConflictError("metadata projection scope disagrees with Source Snapshot")
        if snapshot_data.get("authorization_scope") != data.get("authorization_scope"):
            raise PortiaConflictError(
                "metadata authorization scope disagrees with Source Snapshot"
            )
        if _parse_timestamp(data.get("generated_at"), description="generated_at") < _parse_timestamp(
            snapshot_data.get("observed_at"), description="source observed_at"
        ):
            raise PortiaConflictError("derived generation predates its Source Snapshot")

        snapshot_findings = validate_source_snapshot(self.root, snapshot)
        if snapshot_findings:
            raise PortiaConflictError(
                "derived generation Source Snapshot is stale or internally inconsistent"
            )

        data_fp = fingerprint_bytes(data_bytes)
        artifact = _mapping(data.get("data_artifact"), description="data_artifact")
        try:
            recorded_fp = ContentFingerprint.from_dict(artifact.get("fingerprint"))
        except ValueError as exc:
            raise PortiaCorruptionError("derived metadata has an invalid data fingerprint") from exc
        if recorded_fp != data_fp:
            raise PortiaConflictError("metadata data fingerprint does not match candidate data")

        data_path = derived_data_path(
            self.root,
            projection_kind,
            scope,
            generation_id,
        )
        expected_relative = workspace_relative(self.root, data_path)
        if artifact.get("workspace_relative_path") != expected_relative:
            raise PortiaConflictError(
                "metadata data-artifact path does not match the identity-derived generation path"
            )
        return generation_id, projection_kind, scope, data_fp, data_path

    def install(
        self,
        metadata: PortiaRecord,
        current_pointer: PortiaRecord,
        data: Any,
        *,
        expected_current: ContentFingerprint | None = None,
    ) -> DerivedGeneration:
        """Install a complete generation and select it only after exact verification."""
        if (
            current_pointer.contract != "derived_current_pointer"
            or current_pointer.contract_version != "1"
        ):
            raise PortiaConflictError("current pointer must be derived_current_pointer@1")

        data_bytes = canonical_json_bytes(data)
        generation_id, projection_kind, scope, data_fp, data_path = self._validate_metadata(
            metadata,
            data_bytes,
        )
        metadata_data = metadata.to_dict()
        pointer_data = current_pointer.to_dict()
        if (
            pointer_data.get("projection_kind") != projection_kind
            or pointer_data.get("projection_scope") != scope
        ):
            raise PortiaConflictError("derived pointer scope does not match metadata")
        generation_ref = _mapping(
            pointer_data.get("generation_ref"),
            description="generation_ref",
        )
        if generation_ref.get("generation_id") != generation_id:
            raise PortiaConflictError("derived pointer does not select metadata generation")
        if generation_ref.get("contract_version") != metadata.contract_version:
            raise PortiaConflictError(
                "derived pointer expects a different generation-metadata contract"
            )

        metadata_path = derived_metadata_path(
            self.root,
            projection_kind,
            scope,
            generation_id,
        )
        current_path = derived_current_path(self.root, projection_kind, scope)

        exclusive_create(data_path, data_bytes)
        try:
            metadata_fp = exclusive_create(
                metadata_path,
                canonical_json_bytes(metadata_data),
            )
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "derived data is durable but generation metadata was not accepted"
            ) from exc

        observed_meta, _meta_bytes, observed_meta_fp = read_json(metadata_path)
        try:
            parsed_meta = parse_portia_record("derived_index_metadata", "1", observed_meta)
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "derived metadata failed post-install validation"
            ) from exc
        if observed_meta_fp != metadata_fp or parsed_meta.to_dict() != metadata_data:
            raise PortiaRecoveryRequiredError("derived metadata readback changed after acceptance")

        # Source state is rechecked immediately before current selection.
        self._validate_metadata(metadata, data_bytes)
        pointer_bytes = canonical_json_bytes(pointer_data)
        try:
            if expected_current is None:
                pointer_fp = exclusive_create(current_path, pointer_bytes)
            else:
                pointer_fp = guarded_replace(
                    current_path,
                    pointer_bytes,
                    expected=expected_current,
                )
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "complete derived generation is durable but did not become current"
            ) from exc

        loaded = self.load_current(projection_kind, scope, require_fresh=True)
        if loaded.pointer_fingerprint != pointer_fp:
            raise PortiaRecoveryRequiredError("derived current-pointer readback changed")
        return DerivedGeneration(metadata, data_fp, metadata_fp, pointer_fp)

    def load_current(
        self,
        projection_kind: str,
        scope: object,
        *,
        require_fresh: bool = True,
    ) -> DerivedCurrentState:
        """Load only the generation explicitly selected by ``current.json``."""
        current_path = derived_current_path(self.root, projection_kind, scope)
        pointer_value, _pointer_bytes, pointer_fp = read_json(current_path)
        try:
            pointer = parse_portia_record("derived_current_pointer", "1", pointer_value)
        except Exception as exc:
            raise PortiaCorruptionError("invalid derived current pointer") from exc
        pointer_data = pointer.to_dict()
        if (
            pointer_data.get("projection_kind") != projection_kind
            or pointer_data.get("projection_scope") != scope
        ):
            raise PortiaCorruptionError("derived current pointer disagrees with its storage scope")
        generation_ref = _mapping(pointer_data.get("generation_ref"), description="generation_ref")
        generation_id = generation_ref.get("generation_id")
        contract_version = generation_ref.get("contract_version")
        if not isinstance(generation_id, str) or contract_version != "1":
            raise PortiaCorruptionError("derived current pointer has invalid generation reference")

        metadata_path = derived_metadata_path(
            self.root,
            projection_kind,
            scope,
            generation_id,
        )
        metadata_value, _metadata_bytes, metadata_fp = read_json(metadata_path)
        try:
            metadata = parse_portia_record("derived_index_metadata", "1", metadata_value)
        except Exception as exc:
            raise PortiaCorruptionError("selected derived metadata is invalid") from exc
        metadata_data = metadata.to_dict()
        if (
            metadata_data.get("generation_id") != generation_id
            or metadata_data.get("projection_kind") != projection_kind
            or metadata_data.get("projection_scope") != scope
        ):
            raise PortiaCorruptionError("selected generation metadata disagrees with current pointer")

        data_path = derived_data_path(self.root, projection_kind, scope, generation_id)
        data_value, data_bytes, data_fp = read_json(data_path)
        artifact = _mapping(metadata_data.get("data_artifact"), description="data_artifact")
        try:
            expected_fp = ContentFingerprint.from_dict(artifact.get("fingerprint"))
        except ValueError as exc:
            raise PortiaCorruptionError("selected metadata data fingerprint is invalid") from exc
        if data_fp != expected_fp:
            raise PortiaCorruptionError("selected derived data fingerprint does not match metadata")
        if artifact.get("workspace_relative_path") != workspace_relative(self.root, data_path):
            raise PortiaCorruptionError("selected derived data path does not match metadata")

        snapshot_value = metadata_data.get("source_snapshot")
        try:
            snapshot = parse_portia_record("source_snapshot", "1", snapshot_value)
        except Exception as exc:
            raise PortiaCorruptionError("selected metadata embeds an invalid Source Snapshot") from exc
        if require_fresh and validate_source_snapshot(self.root, snapshot):
            raise PortiaRecoveryRequiredError(
                "selected derived generation is stale; canonical state must be evaluated directly or rebuilt"
            )
        return DerivedCurrentState(
            metadata,
            pointer,
            data_value,
            data_fp,
            metadata_fp,
            pointer_fp,
        )

    def load_current_or_none(
        self,
        projection_kind: str,
        scope: object,
        *,
        require_fresh: bool = True,
    ) -> DerivedCurrentState | None:
        """Return ``None`` for unavailable derived state, never for an empty graph."""
        try:
            return self.load_current(
                projection_kind,
                scope,
                require_fresh=require_fresh,
            )
        except PortiaNotFoundError:
            return None
