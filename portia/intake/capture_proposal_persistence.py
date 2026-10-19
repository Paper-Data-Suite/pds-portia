"""#60 Slice 5B: immutable, review-gated Capture Proposals from exact staging.

Only a fully authorized, historically selected Slice 5A proposal plan may
create records. Source literals stay in Paper Interpretation; this store holds
only references and field binding metadata. No canonical or review writes.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

from pds_core.routes import safe_module_work_descendant

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import resolve_capture_page_spec
from portia.intake.capture_proposal_planning import (
    FileCaptureProposalPlanningService,
    plan_historical_capture_mappings,
)
from portia.models import CaptureProposalV1
from portia.models.errors import PortiaModelError
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaPathError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes

_PROPOSAL_ID = re.compile(r"cprp_[a-f0-9]{40}\Z")
_MAX_RECORDS = 4096
_MAX_BYTES = 200_000


class CaptureProposalPersistenceError(ValueError):
    """Non-sensitive failure code; never contain source literals or local paths."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CaptureProposalStagingResult:
    """One selected interpretation's noncanonical proposal write outcome."""

    page_record_id: str
    interpretation_id: str
    generation: int
    created: int
    reused: int
    attention_entries: int
    records: tuple[CaptureProposalV1, ...] = field(repr=False)

    def summary(self) -> dict[str, object]:
        return {
            "page_record_id": self.page_record_id,
            "interpretation_id": self.interpretation_id,
            "generation": self.generation,
            "proposals_created": self.created,
            "proposals_reused": self.reused,
            "needs_attention_entries": self.attention_entries,
            "requires_human_review": True,
        }


def _proposal_id(
    page_record_id: str,
    interpretation_id: str,
    generation: int,
    entry_key: str,
    target: Mapping[str, object],
    bindings: list[dict[str, object]],
    flags: tuple[str, ...],
) -> str:
    """Stable identity for one exact interpretation entry and pinned mapping."""
    digest = hashlib.sha256(
        canonical_json_bytes(
            [
                page_record_id,
                interpretation_id,
                generation,
                entry_key,
                dict(target),
                bindings,
                list(flags),
            ]
        )
    ).hexdigest()
    return "cprp_" + digest[:40]


def _parse(path: Path) -> CaptureProposalV1:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate proposal JSON key")
            result[key] = value
        return result

    def refuse_constant(value: str) -> None:
        raise ValueError("nonfinite proposal JSON")

    payload = read_bytes(path)
    if len(payload) > _MAX_BYTES:
        raise PortiaCorruptionError("capture_proposal_saved_size_limit")
    try:
        data = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=refuse_constant,
        )
        if not isinstance(data, dict):
            raise ValueError("saved proposal is not an object")
        return CaptureProposalV1(data)
    except (ValueError, TypeError, UnicodeError, PortiaModelError) as exc:
        raise PortiaCorruptionError("capture_proposal_invalid_saved_record") from exc


def _id_for_saved(saved: CaptureProposalV1) -> str:
    data = saved.to_dict()
    interpretation = data["interpretation_ref"]
    if not isinstance(interpretation, dict):
        raise PortiaCorruptionError("capture_proposal_interpretation_ref_invalid")
    if interpretation.get("contract_version") != "1":
        raise PortiaCorruptionError("capture_proposal_version_conflict")
    target = data["target"]
    bindings = data["field_bindings"]
    flags = data["review_flags"]
    if (
        not isinstance(target, dict)
        or not isinstance(bindings, list)
        or not isinstance(flags, list)
    ):
        raise PortiaCorruptionError("capture_proposal_saved_shape_invalid")
    if any(not isinstance(item, dict) for item in bindings) or any(
        not isinstance(item, str) for item in flags
    ):
        raise PortiaCorruptionError("capture_proposal_saved_binding_invalid")
    return _proposal_id(
        cast(str, data["page_record_id"]),
        cast(str, interpretation["interpretation_id"]),
        cast(int, interpretation["generation"]),
        cast(str, data["entry_key"]),
        cast(dict[str, object], target),
        cast(list[dict[str, object]], bindings),
        tuple(cast(list[str], flags)),
    )


class FileCaptureProposalPersistenceService:
    """Append-only, receipt-scoped proposals using the Capture Batch lock."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.planner = FileCaptureProposalPlanningService(workspace_root)
        self.generations = self.planner.history.generations
        self.batches = self.generations.batches
        self.root = self.batches.root

    def _collection(self, class_id: str, work_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                "records/capture_proposal",
            )
        )

    def _inventory(self, class_id: str, work_id: str) -> tuple[CaptureProposalV1, ...]:
        folder = self._collection(class_id, work_id)
        if not folder.exists():
            if folder.is_symlink():
                raise PortiaPathError("unsafe_capture_proposal_collection")
            return ()
        if not folder.is_dir():
            raise PortiaCorruptionError("capture_proposal_collection_not_directory")
        children = tuple(folder.iterdir())
        if len(children) > _MAX_RECORDS:
            raise PortiaCorruptionError("capture_proposal_inventory_limit")
        records: list[CaptureProposalV1] = []
        names: set[str] = set()
        for path in sorted(children, key=lambda item: item.name):
            self.batches._safe(path)
            if (
                not path.is_file()
                or path.suffix != ".json"
                or _PROPOSAL_ID.fullmatch(path.stem) is None
                or path.name.casefold() in names
            ):
                raise PortiaCorruptionError("capture_proposal_inventory_invalid")
            names.add(path.name.casefold())
            saved = _parse(path)
            if (
                saved.class_id != class_id
                or saved.work_id != work_id
                or saved.module_id != "portia"
                or saved.record_type != "capture_proposal"
                or saved.logical_id != path.stem
                or _id_for_saved(saved) != path.stem
            ):
                raise PortiaCorruptionError("capture_proposal_identity_conflict")
            # No confidence, transcript, image or copied literal is permitted in
            # the schema-backed proposal shape.
            records.append(saved)
        return tuple(records)

    def stage(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        interpretation_id: str,
        generation: int,
        *,
        authorization: CaptureAuthorization,
    ) -> CaptureProposalStagingResult:
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization required")
        authorization.require_access(class_id, "capture_proposal.persist")
        actor = self.batches._actor(authorization)
        first = self.planner.plan(
            class_id,
            work_id,
            page_record_id,
            interpretation_id,
            generation,
            authorization=authorization,
        )
        with self.batches._lifecycle_lock(class_id, work_id):
            current = self.planner.plan(
                class_id,
                work_id,
                page_record_id,
                interpretation_id,
                generation,
                authorization=authorization,
            )
            if current != first:
                raise CaptureProposalPersistenceError("capture_proposal_plan_changed")
            history = self.planner.history.history(
                class_id,
                work_id,
                page_record_id,
                authorization=authorization,
            )
            selected = [
                r
                for r in history.records
                if r.logical_id == interpretation_id
                and r.field("generation") == generation
            ]
            if len(selected) != 1:
                raise CaptureProposalPersistenceError("capture_proposal_source_changed")
            source = selected[0]
            source_wire = source.to_dict()
            layout = source_wire.get("layout_snapshot")
            entries = source_wire.get("entries")
            if not isinstance(layout, dict) or not isinstance(entries, dict):
                raise PortiaCorruptionError("capture_proposal_source_shape_invalid")
            spec = resolve_capture_page_spec(layout)
            if (
                source_wire.get("page_record_id") != page_record_id
                or source_wire.get("class_id") != class_id
                or source_wire.get("work_id") != work_id
                or plan_historical_capture_mappings(spec, entries) != current.entries
            ):
                raise CaptureProposalPersistenceError("capture_proposal_source_changed")
            existing = self._inventory(class_id, work_id)
            by_id = {r.logical_id: r for r in existing}
            ready: list[tuple[CaptureProposalV1, CaptureProposalV1 | None]] = []
            for entry in current.entries:
                if entry.disposition != "proposable":
                    continue
                mapping = entry.mapping
                if mapping is None:
                    raise CaptureProposalPersistenceError("proposal_mapping_missing")
                now = datetime.now(timezone.utc).isoformat()
                target = mapping.target_wire()
                bindings = mapping.binding_wire()
                identifier = _proposal_id(
                    current.page_record_id,
                    current.interpretation_id,
                    current.generation,
                    entry.entry_key,
                    target,
                    bindings,
                    mapping.review_flags,
                )
                payload: dict[str, object] = {
                    "schema_version": "1",
                    "record_type": "capture_proposal",
                    "module_id": "portia",
                    "class_id": class_id,
                    "work_id": work_id,
                    "page_target_id": source.field("page_target_id"),
                    "page_record_id": page_record_id,
                    "proposal_id": identifier,
                    "interpretation_ref": {
                        "contract_version": "1",
                        "interpretation_id": interpretation_id,
                        "generation": generation,
                    },
                    "entry_key": entry.entry_key,
                    "target": target,
                    "field_bindings": bindings,
                    "review_flags": list(mapping.review_flags),
                    "proposed_at": now,
                    "proposed_by": dict(actor),
                    "created_at": now,
                    "created_by": dict(actor),
                }
                if "human_review_required" not in mapping.review_flags:
                    raise CaptureProposalPersistenceError(
                        "proposal_review_gate_missing"
                    )
                if len({b.target_path for b in mapping.bindings}) != len(
                    mapping.bindings
                ):
                    raise CaptureProposalPersistenceError(
                        "proposal_target_path_conflict"
                    )
                proposed = CaptureProposalV1(payload)
                old = by_id.get(identifier)
                if old is not None:
                    prior = old.to_dict()
                    # Provenance timestamps are immutable and excluded only from
                    # the replay comparison, not from saved storage.
                    for key in (
                        "created_at",
                        "created_by",
                        "proposed_at",
                        "proposed_by",
                    ):
                        prior.pop(key)
                        payload.pop(key)
                    if prior != payload:
                        raise PortiaConflictError("capture_proposal_replay_conflict")
                ready.append((proposed, old))
            if len(existing) + sum(old is None for _, old in ready) > _MAX_RECORDS:
                raise PortiaCorruptionError("capture_proposal_inventory_limit")
            created = 0
            reused = 0
            returned: list[CaptureProposalV1] = []
            for proposed, old in ready:
                if old is not None:
                    reused += 1
                    returned.append(old)
                    continue
                dest = self.batches._safe(
                    self._collection(class_id, work_id)
                    / (cast(str, proposed.logical_id) + ".json")
                )
                payload_bytes = canonical_json_bytes(proposed.to_dict())
                if len(payload_bytes) > _MAX_BYTES:
                    raise CaptureProposalPersistenceError("capture_proposal_size_limit")
                exclusive_create(dest, payload_bytes)
                persisted = _parse(self.batches._safe(dest))
                if persisted != proposed:
                    raise PortiaCorruptionError("capture_proposal_readback_conflict")
                created += 1
                returned.append(persisted)
            return CaptureProposalStagingResult(
                page_record_id,
                interpretation_id,
                generation,
                created,
                reused,
                sum(e.disposition == "needs_attention" for e in current.entries),
                tuple(returned),
            )
