"""Issue #57 application semantics for immutable pre-print Page Targets.

An existing Event/Support Process must be resolved exactly, not synthesized or
followed to a successor. Page purpose and entry keys never establish behavior
facts or returned-session values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from portia.capture.contracts import CapturePreparationError
from portia.models import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    PageTargetV2,
)
from portia.models.errors import PortiaModelError
from portia.storage.paths import work_manifest_path, work_record_path
from portia.storage.repository import PortiaRepository

_NO_EXISTING_WORK = frozenset(
    {"new_event_capture", "multi_entry_event_capture", "classroom_observation_capture"}
)
_EXPECTED_WORK_KIND = {
    "event_evidence_capture": "event",
    "support_process_evidence_capture": "support_process",
}


@dataclass(frozen=True, slots=True)
class VerifiedExistingCaptureContext:
    """Exact persisted reference identities, not a new or inferred domain fact."""

    work: ExactPortiaWorkRef
    record: ExactLocalRecordRef | None = None


def validate_page_purpose(target: PageTargetV2) -> None:
    """Check source/layout/purpose rules without reading or changing workspace."""
    if not isinstance(target, PageTargetV2):
        raise CapturePreparationError("current Page Target v2 required")
    data = target.to_dict()
    purpose = data["page_purpose"]
    layout = data["entry_layout"]
    if not isinstance(purpose, str) or not isinstance(layout, dict):
        raise CapturePreparationError("invalid Page Target purpose/layout")
    keys = layout.get("entry_keys")
    if not isinstance(keys, list) or any(not isinstance(k, str) for k in keys):
        raise CapturePreparationError("invalid Page Target entry keys")
    context_key = layout.get("context_entry_key")
    if purpose == "classroom_observation_capture":
        if (
            layout.get("mode") != "multi_entry"
            or not isinstance(context_key, str)
            or context_key not in keys
            or len(keys) < 2
            or not any(key != context_key for key in keys)
        ):
            raise CapturePreparationError(
                "Classroom Observation needs a context entry and observation slots"
            )
    if purpose in _NO_EXISTING_WORK and (
        "existing_work_context" in data or "existing_record_context" in data
    ):
        raise CapturePreparationError(
            "new Event/Classroom Observation capture cannot prebind domain work"
        )
    if purpose in _EXPECTED_WORK_KIND and (
        "existing_work_context" not in data
        and "existing_record_context" not in data
    ):
        raise CapturePreparationError(
            "evidence capture requires exact existing work context"
        )
    # focused_monitoring_capture and communication_capture may be unbound.
    # Positive/general/concern form cues are not stored as judgments here.


def resolve_existing_capture_context(
    target: PageTargetV2,
    *,
    repository: PortiaRepository,
    path_guard: Callable[[Path], Path],
) -> VerifiedExistingCaptureContext | None:
    """Resolve exact domain work/record versions via Portia's strict reader.

    A path guard must reject unsafe workspace links before each read. The
    service passes its existing Capture Batch guard; later security work will
    address directory replacement races beyond this preflight protection.
    """
    validate_page_purpose(target)
    data = target.to_dict()
    work_raw = data.get("existing_work_context")
    record_raw = data.get("existing_record_context")
    if work_raw is None and record_raw is None:
        return None

    try:
        explicit = (
            ExactPortiaWorkRef.from_dict(work_raw)
            if work_raw is not None
            else None
        )
        nested = (
            ExactPortiaWorkRecordRef.from_dict(record_raw)
            if record_raw is not None
            else None
        )
    except (PortiaModelError, TypeError, ValueError) as exc:
        raise CapturePreparationError("invalid exact existing capture context") from exc

    work = nested.work_ref if nested is not None else explicit
    if work is None:
        raise CapturePreparationError("missing exact existing work identity")
    if explicit is not None and explicit != work:
        raise CapturePreparationError("conflicting exact work and record contexts")
    if work.class_id != target.class_id:
        raise CapturePreparationError("existing work belongs to another class")

    purpose = data["page_purpose"]
    if isinstance(purpose, str):
        expected_kind = _EXPECTED_WORK_KIND.get(purpose)
        if expected_kind is not None and work.work_kind != expected_kind:
            raise CapturePreparationError(
                "Page Target purpose contradicts existing work kind"
            )

    # These are exact canonical Portia work/child paths, NEVER a Capture Batch
    # work root or a Core viewer-only presentation alias.
    path_guard(work_manifest_path(repository.workspace_root, work))
    stored = repository.load_work(work)
    if stored.record.work_id != work.work_id or stored.record.class_id != work.class_id:
        raise CapturePreparationError("persisted existing work identity mismatch")
    if nested is not None:
        local = nested.record_ref
        path_guard(
            work_record_path(
                repository.workspace_root,
                work,
                local.record_kind,
                local.record_id,
            )
        )
        existing_record = repository.load_work_record(
            work,
            local.record_kind,
            local.contract_version,
            local.record_id,
        )
        if (
            existing_record.record.contract != local.record_kind
            or existing_record.record.contract_version != local.contract_version
        ):
            raise CapturePreparationError("persisted child representation mismatch")
        return VerifiedExistingCaptureContext(work=work, record=local)
    return VerifiedExistingCaptureContext(work=work)
