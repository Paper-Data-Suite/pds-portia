"""Exact material-correction supersession rules for Account/Observation evidence."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    ACCOUNT_READ_VERSIONS,
    OBSERVATION_READ_VERSIONS,
    require_evidence_record_owner,
    require_supported_evidence_version,
)

_CORRECTION_REASON_TO_LIFECYCLE = {
    "duplicate_consolidated": "duplicate_consolidated",
    "work_root_corrected": "work_root_corrected",
    "contract_migrated": "contract_migrated",
}


_ACCOUNT_CORRECTION_FIELDS = {
    "source_corrected": ("source",),
    "source_attribution_corrected": ("source",),
    "target_corrected": ("target",),
    "statement_corrected": ("content", "elicitation_context", "source_certainty"),
    "representation_corrected": ("content",),
    "information_origin_corrected": ("information_origin",),
    "timing_corrected": ("provided_time",),
    "provenance_corrected": ("source_artifacts",),
}
_OBSERVATION_CORRECTION_FIELDS = {
    "observer_corrected": ("observer",),
    "instrument_corrected": ("observer",),
    "target_corrected": ("target",),
    "observation_content_corrected": ("content",),
    "measurement_corrected": ("content",),
    "timing_corrected": ("observation_time",),
    "method_corrected": ("method", "method_detail"),
    "provenance_corrected": ("source_artifacts",),
}
_ACCOUNT_MATERIAL_FIELDS = (
    "source",
    "target",
    "content",
    "elicitation_context",
    "information_origin",
    "source_certainty",
    "provided_time",
    "source_artifacts",
)
_OBSERVATION_MATERIAL_FIELDS = (
    "observer",
    "target",
    "method",
    "method_detail",
    "content",
    "observation_time",
    "source_artifacts",
)


def _supported_versions(contract: str) -> frozenset[str]:
    if contract == "account":
        return ACCOUNT_READ_VERSIONS
    if contract == "observation":
        return OBSERVATION_READ_VERSIONS
    raise WorkflowOwnershipError(
        "evidence supersession requires Account or Observation"
    )


def supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Resolve exact same-work predecessors without following any successor."""
    require_evidence_record_owner(work, successor, contract=successor.contract)
    entries = successor.to_dict().get("supersedes")
    if entries is None:
        return ()
    if not isinstance(entries, list):
        raise WorkflowOwnershipError("evidence supersedes collection is malformed")

    resolved: list[StoredRecord] = []
    seen_ids: set[str] = set()
    reasons: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise WorkflowOwnershipError("supersession entry is malformed")
        composite = entry.get("work_record_ref")
        if not isinstance(composite, dict):
            raise WorkflowOwnershipError("supersession predecessor reference is malformed")
        if composite.get("work_ref") != work.to_dict():
            raise WorkflowOwnershipError(
                "supersession predecessor must remain in the same exact owning work"
            )
        reference = composite.get("record_ref")
        if not isinstance(reference, dict):
            raise WorkflowOwnershipError("supersession predecessor is not an exact record")
        if reference.get("record_kind") != successor.contract:
            raise WorkflowOwnershipError(
                "supersession predecessor must use the same evidence family"
            )
        record_id = reference.get("record_id")
        version = reference.get("contract_version")
        if not isinstance(record_id, str) or not isinstance(version, str):
            raise WorkflowOwnershipError("supersession predecessor reference is incomplete")
        require_supported_evidence_version(
            work,
            contract=successor.contract,
            version=version,
            supported_versions=_supported_versions(successor.contract),
        )
        if record_id == successor.logical_id:
            raise WorkflowPrerequisiteError("evidence cannot supersede itself")
        if record_id in seen_ids:
            raise WorkflowPrerequisiteError(
                "supersession cannot repeat one logical predecessor identity"
            )
        seen_ids.add(record_id)
        reason = entry.get("reason")
        if not isinstance(reason, str):
            raise WorkflowOwnershipError("supersession reason is malformed")
        reasons.add(reason)
        if reason == "other":
            detail = entry.get("detail")
            if not isinstance(detail, str) or not detail.strip():
                raise WorkflowPrerequisiteError(
                    "supersession reason 'other' requires bounded detail"
                )
        resolved.append(
            repository.load_work_record(
                work,
                successor.contract,
                version,
                record_id,
            )
        )
    if len(reasons) > 1:
        raise WorkflowPrerequisiteError(
            "one successor must use one uniform supersession reason"
        )
    return tuple(resolved)


def supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    evidence: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Return bounded transitive exact supersession ancestry for complete graphs."""
    values: list[StoredRecord] = []
    visited: set[tuple[str, str, str]] = set()
    visiting: set[tuple[str, str, str]] = set()

    def visit(record: PortiaRecord) -> None:
        for stored in supersession_records(repository, work, record):
            identifier = stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "supersession predecessor has no canonical identity"
                )
            key = (
                stored.record.contract,
                stored.record.contract_version,
                identifier,
            )
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(stored)
            visit(stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(evidence)
    return tuple(values)


def require_exact_supersession_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact selected predecessor and return its supersession reason."""
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "supersession predecessor does not belong to the selected Portia work"
        )
    require_evidence_record_owner(work, successor, contract=successor.contract)
    supersedes = successor.to_dict().get("supersedes")
    if not isinstance(supersedes, list) or len(supersedes) != 1:
        raise WorkflowPrerequisiteError(
            "material correction requires exactly one supersedes predecessor"
        )
    entry = supersedes[0]
    if not isinstance(entry, dict):
        raise WorkflowOwnershipError("supersession entry is malformed")
    reference = entry.get("work_record_ref")
    if not isinstance(reference, dict) or reference != predecessor.to_dict():
        raise WorkflowOwnershipError(
            "successor supersedes entry must name the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "material correction must use a new canonical evidence identity"
        )
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "supersession reason 'other' requires bounded detail"
            )
    return reason


def require_supersession_effective(predecessors: tuple[StoredRecord, ...]) -> None:
    """Require a current successor's exact predecessors to be superseded."""
    for predecessor in predecessors:
        if predecessor.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current corrected evidence requires its exact predecessor to be superseded"
            )


def require_material_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require a correction reason to correspond to changed primary evidence."""
    if prior.contract != successor.contract:
        raise WorkflowOwnershipError(
            "material correction requires the same evidence family"
        )
    if supersession_reason in {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }:
        raise WorkflowPrerequisiteError(
            f"{supersession_reason} is not a material-correction operation"
        )
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    material_fields = (
        _ACCOUNT_MATERIAL_FIELDS
        if prior.contract == "account"
        else _OBSERVATION_MATERIAL_FIELDS
    )
    changed = {
        field
        for field in material_fields
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material correction requires an actual primary-evidence change"
        )
    if supersession_reason == "other":
        return
    by_reason = (
        _ACCOUNT_CORRECTION_FIELDS
        if prior.contract == "account"
        else _OBSERVATION_CORRECTION_FIELDS
    )
    expected_fields = by_reason.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported material correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"supersession reason {supersession_reason!r} does not match the evidence change"
        )


def correction_lifecycle_reason(supersession_reason: str) -> str:
    """Map successor correction provenance onto predecessor lifecycle provenance."""
    return _CORRECTION_REASON_TO_LIFECYCLE.get(
        supersession_reason, "corrected_by_successor"
    )


def superseded_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the exact predecessor representation with only lifecycle metadata changed."""
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "corrected successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record(prior.contract, prior.contract_version, data)
