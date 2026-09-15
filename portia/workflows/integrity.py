"""Bounded workflow integrity evaluation over accepted storage evidence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.derived import DerivedGeneration, DerivedStore
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.integrity import (
    PersistenceFinding,
    source_snapshot_digest,
    validate_operation_durable_state,
)
from portia.storage.paths import (
    derived_data_path,
    operation_current_path,
    operation_revision_path,
    operation_root,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.workflows.errors import WorkflowPrerequisiteError

_PROJECTION_KIND = "active_integrity_finding_index"
_PROJECTION_CONTRACT_VERSION = "2"
_BUILDER_ID = "operation_persistence_integrity"
_BUILDER_VERSION = "1"
_AUTHORIZATION_SCOPE = {
    "authorization_scope_id": "operation_persistence_complete",
    "coverage": "complete",
    "limitation_codes": [],
}


@dataclass(frozen=True, slots=True)
class _PublicDiagnostic:
    category: str
    code: str
    check: str


_PUBLIC_DIAGNOSTICS = {
    "PORTIA.STORAGE.OPERATION_WRITE_SET_INVALID": _PublicDiagnostic(
        "persistence_recovery", "recovery_required", "journal_write_set"
    ),
    "PORTIA.STORAGE.UNSAFE_OPERATION_PATH": _PublicDiagnostic(
        "structure", "canonical_path_mismatch", "workspace_containment"
    ),
    "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH": _PublicDiagnostic(
        "structure", "canonical_path_mismatch", "target_path_ownership"
    ),
    "PORTIA.STORAGE.DURABLE_RESULT_MISSING": _PublicDiagnostic(
        "persistence_recovery", "recovery_required", "durable_destination"
    ),
    "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH": _PublicDiagnostic(
        "persistence_recovery", "content_digest_mismatch", "intended_fingerprint"
    ),
    "PORTIA.STORAGE.READBACK_RESULT_MISMATCH": _PublicDiagnostic(
        "persistence_recovery", "content_digest_mismatch", "observed_fingerprint"
    ),
}


def _deterministic_id(prefix: str, value: object) -> str:
    return prefix + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class OperationIntegrityEvaluation:
    """Persistence-integrity evidence for one exact selected journal revision."""

    operation_id: str
    journal_revision: int
    journal_fingerprint: ContentFingerprint
    pointer_fingerprint: ContentFingerprint
    findings: tuple[PersistenceFinding, ...]


@dataclass(frozen=True, slots=True)
class OperationIntegrityProjection:
    """Installed current findings for one exact operation-journal revision."""

    evaluation: OperationIntegrityEvaluation
    findings: tuple[PortiaRecord, ...]
    generation: DerivedGeneration


class IntegrityWorkflowService:
    """Application boundary for deterministic Portia integrity evaluation."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self._operations = OperationJournalStore(self.root)
        self._derived = DerivedStore(self.root)

    def evaluate_operation_persistence(
        self,
        operation_id: str,
    ) -> OperationIntegrityEvaluation:
        """Evaluate the exact current operation revision without mutating state.

        Recovery topology is deliberately checked before and after evaluation.
        A missing pointer, orphan successor, or other non-current series must be
        handled through recovery rather than silently evaluating a stale head.
        """
        before = self._operations.inspect_recovery(operation_id)
        if before.disposition != "current":
            raise WorkflowPrerequisiteError(
                "integrity evaluation requires an unambiguous current operation "
                "journal; resolve recovery state first"
            )

        current = self._operations.load_current(operation_id)
        revision_value = current.revision.to_dict().get("journal_revision")
        if not isinstance(revision_value, int) or isinstance(revision_value, bool):
            raise WorkflowPrerequisiteError(
                "selected operation journal has no valid journal revision"
            )

        findings = validate_operation_durable_state(self.root, current.revision)

        after = self._operations.inspect_recovery(operation_id)
        if (
            after.disposition != "current"
            or after.selected_revision != revision_value
        ):
            raise WorkflowPrerequisiteError(
                "operation recovery state changed during integrity evaluation"
            )
        readback = self._operations.load_current(operation_id)
        if (
            readback.revision_fingerprint != current.revision_fingerprint
            or readback.pointer_fingerprint != current.pointer_fingerprint
        ):
            raise WorkflowPrerequisiteError(
                "operation current selection changed during integrity evaluation"
            )

        return OperationIntegrityEvaluation(
            operation_id=operation_id,
            journal_revision=revision_value,
            journal_fingerprint=current.revision_fingerprint,
            pointer_fingerprint=current.pointer_fingerprint,
            findings=findings,
        )

    def project_operation_persistence_findings(
        self,
        operation_id: str,
    ) -> OperationIntegrityProjection:
        """Install deterministic public findings for one exact current journal."""
        evaluation = self.evaluate_operation_persistence(operation_id)
        current = self._operations.load_current(operation_id)
        revision_value = current.revision.to_dict().get("journal_revision")
        if (
            revision_value != evaluation.journal_revision
            or current.revision_fingerprint != evaluation.journal_fingerprint
            or current.pointer_fingerprint != evaluation.pointer_fingerprint
        ):
            raise WorkflowPrerequisiteError(
                "operation current selection changed before finding projection"
            )

        journal_data = current.revision.to_dict()
        observed_at = journal_data.get("updated_at")
        if not isinstance(observed_at, str):
            raise WorkflowPrerequisiteError(
                "selected operation journal has no stable observation timestamp"
            )

        mapped: list[tuple[PersistenceFinding, _PublicDiagnostic]] = []
        for finding in evaluation.findings:
            public = _PUBLIC_DIAGNOSTICS.get(finding.code)
            if public is None:
                raise WorkflowPrerequisiteError(
                    "persistence diagnostic has no public integrity-finding mapping: "
                    f"{finding.code}"
                )
            mapped.append((finding, public))
        mapped.sort(
            key=lambda item: (
                item[1].category,
                item[1].code,
                item[0].relative_path,
                item[1].check,
            )
        )

        evaluation_identity = {
            "operation_id": operation_id,
            "journal_revision": evaluation.journal_revision,
            "journal_fingerprint": evaluation.journal_fingerprint.to_dict(),
            "diagnostics": [
                {
                    "category": public.category,
                    "code": public.code,
                    "check": public.check,
                    "relative_path": finding.relative_path,
                }
                for finding, public in mapped
            ],
        }
        evaluation_key = _deterministic_id("evl_", evaluation_identity)
        public_findings: list[PortiaRecord] = []
        for finding, public in mapped:
            rule_id = f"portia.{public.category}.{public.code}"
            finding_identity = {
                "builder_id": _BUILDER_ID,
                "builder_version": _BUILDER_VERSION,
                "rule_id": rule_id,
                "rule_version": "1",
                "primary_target": {
                    "kind": "operation",
                    "operation_id": operation_id,
                },
                "category": public.category,
                "code": public.code,
                "check": public.check,
                "relative_path": finding.relative_path,
            }
            evidence: list[dict[str, Any]] = [
                {
                    "name": "journal_contract_version",
                    "kind": "identifier",
                    "value": "2",
                },
                {
                    "name": "journal_revision",
                    "kind": "integer",
                    "value": evaluation.journal_revision,
                },
                {
                    "name": "persistence_check",
                    "kind": "token",
                    "value": public.check,
                },
            ]
            if len(finding.relative_path) <= 512:
                evidence.append(
                    {
                        "name": "destination_path",
                        "kind": "path",
                        "value": finding.relative_path,
                    }
                )
            else:
                evidence.append(
                    {
                        "name": "destination_path_sha256",
                        "kind": "identifier",
                        "value": hashlib.sha256(
                            finding.relative_path.encode("utf-8")
                        ).hexdigest(),
                    }
                )
            value = {
                "finding_key": _deterministic_id("fnd_", finding_identity),
                "evaluation_key": evaluation_key,
                "rule_id": rule_id,
                "rule_version": "1",
                "category": public.category,
                "code": public.code,
                "severity": "error",
                "assessment": {"result": "confirmed"},
                "effects": ["review_required", "block_operation_completion"],
                "scope": "operation",
                "primary_target": {
                    "kind": "operation",
                    "operation_id": operation_id,
                },
                "related_targets": [],
                "evidence": evidence,
                "observed_at": observed_at,
            }
            public_findings.append(parse_portia_record("integrity_finding", "2", value))

        data = {"findings": [finding.to_dict() for finding in public_findings]}
        scope = {"scope": "operation", "operation_ref": {"operation_id": operation_id}}
        snapshot_data: dict[str, Any] = {
            "schema_version": "1",
            "record_type": "source_snapshot",
            "module_id": "portia",
            "snapshot_algorithm": "portia_source_snapshot_v1",
            "projection_kind": _PROJECTION_KIND,
            "projection_scope": scope,
            "authorization_scope": _AUTHORIZATION_SCOPE,
            "discovery_roots": [workspace_relative(self.root, operation_root(self.root, operation_id))],
            "source_contracts": [
                {"contract_name": "operation_current_pointer", "contract_version": "1"},
                {"contract_name": "operation_journal", "contract_version": "2"},
            ],
            "entries": [
                {
                    "workspace_relative_path": workspace_relative(
                        self.root, operation_current_path(self.root, operation_id)
                    ),
                    "byte_length": evaluation.pointer_fingerprint.byte_length,
                    "sha256_digest": evaluation.pointer_fingerprint.digest,
                    "source_role": "operational_pointer",
                    "contract_or_artifact_kind": "operation_current_pointer",
                },
                {
                    "workspace_relative_path": workspace_relative(
                        self.root,
                        operation_revision_path(
                            self.root, operation_id, evaluation.journal_revision
                        ),
                    ),
                    "byte_length": evaluation.journal_fingerprint.byte_length,
                    "sha256_digest": evaluation.journal_fingerprint.digest,
                    "source_role": "operational_revision",
                    "contract_or_artifact_kind": "operation_journal",
                },
            ],
            "source_snapshot_digest": "",
            "observed_at": observed_at,
        }
        snapshot_data["source_snapshot_digest"] = source_snapshot_digest(snapshot_data)
        snapshot = parse_portia_record("source_snapshot", "1", snapshot_data)

        data_fingerprint = fingerprint_bytes(canonical_json_bytes(data))
        generation_id = _deterministic_id(
            "dgen_",
            {
                "builder_id": _BUILDER_ID,
                "builder_version": _BUILDER_VERSION,
                "source_snapshot_digest": snapshot_data["source_snapshot_digest"],
                "data_fingerprint": data_fingerprint.to_dict(),
            },
        )
        metadata = parse_portia_record(
            "derived_index_metadata",
            "1",
            {
                "schema_version": "1",
                "record_type": "derived_index_metadata",
                "module_id": "portia",
                "generation_id": generation_id,
                "generation_state": "complete",
                "projection_kind": _PROJECTION_KIND,
                "projection_scope": scope,
                "projection_contract_version": _PROJECTION_CONTRACT_VERSION,
                "builder": {
                    "builder_id": _BUILDER_ID,
                    "builder_version": _BUILDER_VERSION,
                },
                "authorization_scope": _AUTHORIZATION_SCOPE,
                "source_snapshot": snapshot.to_dict(),
                "data_artifact": {
                    "workspace_relative_path": workspace_relative(
                        self.root,
                        derived_data_path(
                            self.root, _PROJECTION_KIND, scope, generation_id
                        ),
                    ),
                    "contract_version": _PROJECTION_CONTRACT_VERSION,
                    "fingerprint": data_fingerprint.to_dict(),
                },
                "validation": {
                    "schema_validation": "passed",
                    "identity_validation": "passed",
                    "reference_validation": "passed",
                    "privacy_validation": "passed",
                    "invariant_validation": "passed",
                },
                "generating_operation": {
                    "operation_id": operation_id,
                    "journal_revision": evaluation.journal_revision,
                    "contract_version": "2",
                },
                "generated_at": observed_at,
            },
        )
        pointer = parse_portia_record(
            "derived_current_pointer",
            "1",
            {
                "schema_version": "1",
                "record_type": "derived_current_pointer",
                "module_id": "portia",
                "projection_kind": _PROJECTION_KIND,
                "projection_scope": scope,
                "generation_ref": {
                    "generation_id": generation_id,
                    "contract_version": "1",
                },
            },
        )

        prior = self._derived.load_current_or_none(
            _PROJECTION_KIND, scope, require_fresh=False
        )
        if prior is not None and prior.metadata.to_dict().get("generation_id") == generation_id:
            fresh = self._derived.load_current(_PROJECTION_KIND, scope, require_fresh=True)
            if fresh.metadata.to_dict() != metadata.to_dict() or fresh.data != data:
                raise WorkflowPrerequisiteError(
                    "deterministic integrity generation identity has conflicting content"
                )
            generation = DerivedGeneration(
                fresh.metadata,
                fresh.data_fingerprint,
                fresh.metadata_fingerprint,
                fresh.pointer_fingerprint,
            )
        else:
            generation = self._derived.install(
                metadata,
                pointer,
                data,
                expected_current=(None if prior is None else prior.pointer_fingerprint),
            )
        return OperationIntegrityProjection(
            evaluation=evaluation,
            findings=tuple(public_findings),
            generation=generation,
        )
