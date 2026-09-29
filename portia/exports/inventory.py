"""Exact contributing-source inventory authoring for Portia Issue #51 Slice 4.

This module converts one *final* teacher-reference projection decision into the
published ``export_source_inventory@1`` contract without writing it.  Only
exact canonical Portia work/work-record representations that materially
contributed projected content are inventoried.  Every entry is reloaded by its
exact reference and its canonical stored fingerprint must still match the
projection observation; no successor selection or reserialization is used as
source-byte authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from portia.exports.discovery import (
    TeacherReferenceSourceObservation,
    TeacherReferenceSourceRef,
    TeacherReferenceSourceRole,
)
from portia.exports.projection import TeacherReferenceProjectionDecision
from portia.models import ExportSourceInventoryV1
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRef
from portia.storage import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaRepository,
    StoredRecord,
)

EXPORT_SOURCE_INVENTORY_ALGORITHM: Final[str] = "portia_export_source_inventory_v1"
_ALLOWED_SOURCE_ROLES: Final[frozenset[str]] = frozenset(
    {
        "projected_domain",
        "projection_context",
        "correction_context",
        "disagreement_context",
    }
)


def _canonical_identity(value: Mapping[str, object]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _source_identity(entry: Mapping[str, object]) -> str:
    for key in ("work_ref", "work_record_ref"):
        value = entry.get(key)
        if isinstance(value, Mapping):
            return _canonical_identity(value)
    raise PortiaLocalValidationError(
        "teacher-reference inventory entry lacks an exact Portia source identity"
    )


def _entry_sort_key(entry: Mapping[str, object]) -> tuple[str, str, str]:
    role = entry.get("source_role")
    kind = entry.get("source_kind")
    if not isinstance(role, str) or not isinstance(kind, str):
        raise PortiaLocalValidationError(
            "teacher-reference inventory entry lacks source role/kind"
        )
    return (role, kind, _source_identity(entry))


def teacher_reference_source_inventory_digest(
    entries: Sequence[Mapping[str, object]],
) -> str:
    """Return the accepted Issue #21 inventory digest for exact ordered entries.

    The published application contract hashes canonical JSON containing only
    ``inventory_algorithm`` and ``entries`` and intentionally does *not* append
    a trailing LF to that digest payload.
    """

    payload = {
        "inventory_algorithm": EXPORT_SOURCE_INVENTORY_ALGORITHM,
        "entries": [dict(entry) for entry in entries],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class TeacherReferenceSourceInventory:
    """Transient exact source inventory paired with its restricted source refs."""

    record: ExportSourceInventoryV1
    source_refs: tuple[TeacherReferenceSourceRef, ...]
    source_roles: tuple[TeacherReferenceSourceRole, ...]

    def __post_init__(self) -> None:
        data = self.record.to_dict()
        entries = data.get("entries")
        if not isinstance(entries, list):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory record lacks entries"
            )
        if len(entries) != len(self.source_refs) or len(entries) != len(
            self.source_roles
        ):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory transient refs drift from entries"
            )
        entry_maps = tuple(_entry_mapping(entry) for entry in entries)
        if entry_maps != tuple(sorted(entry_maps, key=_entry_sort_key)):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory entries are not deterministically ordered"
            )
        identities = tuple(
            (str(entry.get("source_kind")), _source_identity(entry))
            for entry in entry_maps
        )
        if len(identities) != len(set(identities)):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory repeats semantic source identity"
            )
        for entry, source_ref, source_role in zip(
            entry_maps,
            self.source_refs,
            self.source_roles,
            strict=True,
        ):
            if source_role not in _ALLOWED_SOURCE_ROLES:
                raise PortiaLocalValidationError(
                    "ordinary teacher-reference inventory cannot retain this source role"
                )
            if entry.get("source_role") != source_role:
                raise PortiaLocalValidationError(
                    "teacher-reference inventory source role drifted from transient authority"
                )
            if isinstance(source_ref, ExactPortiaWorkRef):
                if entry.get("source_kind") != "portia_work" or entry.get(
                    "work_ref"
                ) != source_ref.to_dict():
                    raise PortiaLocalValidationError(
                        "teacher-reference inventory work source identity mismatch"
                    )
            elif entry.get("source_kind") != "portia_record" or entry.get(
                "work_record_ref"
            ) != source_ref.to_dict():
                raise PortiaLocalValidationError(
                    "teacher-reference inventory record source identity mismatch"
                )
        expected_digest = teacher_reference_source_inventory_digest(entry_maps)
        if data.get("inventory_digest") != expected_digest:
            raise PortiaLocalValidationError(
                "teacher-reference source inventory digest does not match entries"
            )

    @property
    def inventory_algorithm(self) -> str:
        return EXPORT_SOURCE_INVENTORY_ALGORITHM

    @property
    def inventory_digest(self) -> str:
        value = self.record.field("inventory_digest")
        assert isinstance(value, str)
        return value

    @property
    def entries(self) -> tuple[dict[str, object], ...]:
        raw = self.record.to_dict()["entries"]
        assert isinstance(raw, list)
        return tuple(dict(_entry_mapping(entry)) for entry in raw)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in self.record.to_dict().items():
            result[key] = value
        return result


def _entry_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise PortiaLocalValidationError(
            "teacher-reference source inventory entry must be a JSON object"
        )
    return cast(Mapping[str, object], value)


class TeacherReferenceSourceInventoryService:
    """Author exact ``export_source_inventory@1`` values without persistence."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)

    def author(
        self,
        decision: TeacherReferenceProjectionDecision,
    ) -> TeacherReferenceSourceInventory:
        if not isinstance(decision, TeacherReferenceProjectionDecision):
            raise TypeError("decision must be a TeacherReferenceProjectionDecision")
        if not decision.is_final:
            raise PortiaLocalValidationError(
                "teacher-reference source inventory requires a final projection decision"
            )

        contributing = decision.contributing_source_refs
        if not contributing:
            raise PortiaLocalValidationError(
                "teacher-reference source inventory requires projected content"
            )

        observations = {
            observation.source_ref: observation
            for observation in decision.discovery.observations
        }
        contributing_set = frozenset(contributing)
        pairs: list[tuple[dict[str, object], TeacherReferenceSourceRef, TeacherReferenceSourceRole]] = []
        for source_ref in contributing:
            observation = observations.get(source_ref)
            if observation is None:
                raise PortiaLocalValidationError(
                    "contributing projection source was not present in exact discovery"
                )
            self._require_authorized_source(decision, observation, contributing_set)
            stored = self._load_and_verify(observation)
            fingerprint = stored.fingerprint
            if isinstance(source_ref, ExactPortiaWorkRef):
                entry: dict[str, object] = {
                    "source_kind": "portia_work",
                    "source_role": observation.source_role,
                    "work_ref": source_ref.to_dict(),
                    "representation_digest": fingerprint.digest,
                    "byte_length": fingerprint.byte_length,
                }
            else:
                entry = {
                    "source_kind": "portia_record",
                    "source_role": observation.source_role,
                    "work_record_ref": source_ref.to_dict(),
                    "representation_digest": fingerprint.digest,
                    "byte_length": fingerprint.byte_length,
                }
            pairs.append((entry, source_ref, observation.source_role))

        pairs.sort(key=lambda pair: _entry_sort_key(pair[0]))
        entries = [pair[0] for pair in pairs]
        identities = [
            (str(entry["source_kind"]), _source_identity(entry)) for entry in entries
        ]
        if len(identities) != len(set(identities)):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory repeats semantic source identity"
            )
        if entries != sorted(entries, key=_entry_sort_key):
            raise PortiaLocalValidationError(
                "teacher-reference source inventory ordering is nondeterministic"
            )

        inventory_digest = teacher_reference_source_inventory_digest(entries)
        record = ExportSourceInventoryV1(
            {
                "schema_version": "1",
                "record_type": "export_source_inventory",
                "module_id": "portia",
                "inventory_algorithm": EXPORT_SOURCE_INVENTORY_ALGORITHM,
                "entries": entries,
                "inventory_digest": inventory_digest,
            }
        )
        return TeacherReferenceSourceInventory(
            record=record,
            source_refs=tuple(pair[1] for pair in pairs),
            source_roles=tuple(pair[2] for pair in pairs),
        )

    def _require_authorized_source(
        self,
        decision: TeacherReferenceProjectionDecision,
        observation: TeacherReferenceSourceObservation,
        contributing: frozenset[TeacherReferenceSourceRef],
    ) -> None:
        if observation.source_role not in _ALLOWED_SOURCE_ROLES:
            raise PortiaLocalValidationError(
                "ordinary teacher-reference inventory cannot use this source role"
            )
        if observation.work_ref != decision.discovery.scope.work_ref:
            raise PortiaLocalValidationError(
                "teacher-reference source read escaped the exact selected work"
            )
        if observation.source_role in {"correction_context", "disagreement_context"}:
            target = observation.context_target_ref
            if target is None or target not in contributing:
                raise PortiaLocalValidationError(
                    "correction/disagreement source may contribute only with its exact "
                    "projected context target"
                )
        elif observation.context_target_ref is not None:
            raise PortiaLocalValidationError(
                "ordinary teacher-reference source unexpectedly carries a context target"
            )

    def _load_and_verify(
        self,
        observation: TeacherReferenceSourceObservation,
    ) -> StoredRecord:
        source = observation.source_ref
        if isinstance(source, ExactPortiaWorkRef):
            stored = self.repository.load_work(source)
        else:
            stored = self.repository.load_work_record(
                source.work_ref,
                source.record_ref.record_kind,
                source.record_ref.contract_version,
                source.record_ref.record_id,
            )
        if stored.fingerprint != observation.fingerprint:
            raise PortiaConflictError(
                "canonical source changed after teacher-reference projection"
            )
        if stored.record.contract != observation.record_kind:
            raise PortiaCorruptionError(
                "teacher-reference source contract disagrees with exact observation"
            )
        if stored.record.contract_version != observation.contract_version:
            raise PortiaCorruptionError(
                "teacher-reference source version disagrees with exact observation"
            )
        return stored


__all__ = [
    "EXPORT_SOURCE_INVENTORY_ALGORITHM",
    "TeacherReferenceSourceInventory",
    "TeacherReferenceSourceInventoryService",
    "teacher_reference_source_inventory_digest",
]
