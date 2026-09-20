"""Bounded workflow integrity evaluation over accepted storage evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.acknowledgements import (
    FindingAcknowledgementStore,
    StoredAcknowledgement,
)
from portia.storage.derived import DerivedGeneration, DerivedStore
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
)
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
from portia.storage.io import read_json
from portia.storage.paths import (
    derived_data_path,
    derived_projection_root,
    operation_current_path,
    operation_revision_path,
    operation_root,
    workspace_relative,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.series import (
    FindingSuppressionStore,
    OperationJournalStore,
    SeriesState,
)
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.integrity_authority import IntegrityOperatorAuthority

_PROJECTION_KIND = "active_integrity_finding_index"
_PROJECTION_CONTRACT_VERSION = "2"
_BUILDER_ID = "operation_persistence_integrity"
_BUILDER_VERSION = "1"
_AUTHORIZATION_SCOPE = {
    "authorization_scope_id": "operation_persistence_complete",
    "coverage": "complete",
    "limitation_codes": [],
}
_RATIONALE_MAX_LENGTH = 512
_SUPPRESSIBLE_SEVERITIES = frozenset({"advisory", "warning"})
_SUPPRESSIBLE_EFFECTS = frozenset({"attention", "review_required"})
_PROHIBITED_SUPPRESSION_CODES = frozenset(
    {
        "authorization_limited_resolution",
        "derived_payload_retained_after_removal",
        "payload_present_after_removal",
    }
)
_TARGET_EVIDENCE_MARKERS = ("revision", "fingerprint", "digest")


def _parse_timestamp(value: object, *, description: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} must be an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} must be a valid explicit-offset timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"{description} must include an explicit UTC offset"
        )
    return parsed


def _bounded_rationale(value: object, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkflowPrerequisiteError("rationale must be bounded non-empty text")
    if len(value) > _RATIONALE_MAX_LENGTH or any(
        character in value for character in ("\r", "\n", "\x00")
    ):
        raise WorkflowPrerequisiteError(
            "rationale must be a single privacy-minimized line of at most "
            f"{_RATIONALE_MAX_LENGTH} characters"
        )
    return value


def _as_mapping(value: object, *, description: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or any(
        not isinstance(key, str) for key in value
    ):
        raise WorkflowPrerequisiteError(f"{description} must be a JSON object")
    return dict(value)


def _exact_finding_binding(finding: PortiaRecord) -> dict[str, object]:
    data = finding.to_dict()
    return {
        name: deepcopy(data[name])
        for name in (
            "finding_key",
            "evaluation_key",
            "rule_id",
            "rule_version",
            "severity",
            "effects",
        )
    }


def _integrity_target(requested_target: object) -> object:
    """Translate accepted workflow guard targets to Integrity Finding v2 targets."""
    if not isinstance(requested_target, Mapping):
        return requested_target
    value = deepcopy(dict(requested_target))
    kind = value.get("kind")
    if kind == "work":
        value["kind"] = "portia_work"
    elif kind == "work_record":
        value["kind"] = "portia_work_record"
    return value


def _projection_scope_for_target(requested_target: object) -> dict[str, object] | None:
    if not isinstance(requested_target, Mapping):
        return None
    kind = requested_target.get("kind")
    if kind == "work":
        work_ref = requested_target.get("work_ref")
        return (
            {"scope": "work", "work_ref": deepcopy(work_ref)}
            if isinstance(work_ref, Mapping)
            else None
        )
    if kind == "work_record":
        record_ref = requested_target.get("work_record_ref")
        work_ref = record_ref.get("work_ref") if isinstance(record_ref, Mapping) else None
        return (
            {"scope": "work", "work_ref": deepcopy(work_ref)}
            if isinstance(work_ref, Mapping)
            else None
        )
    if kind == "class" and isinstance(requested_target.get("class_id"), str):
        return {"scope": "class", "class_id": requested_target["class_id"]}
    if kind == "workspace" and isinstance(
        requested_target.get("workspace_id"), str
    ):
        return {
            "scope": "workspace",
            "workspace_id": requested_target["workspace_id"],
        }
    return None


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
    "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISSING": _PublicDiagnostic(
        "removal", "removal_reconciliation_broken", "removal_certificate_presence"
    ),
    "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH": _PublicDiagnostic(
        "removal", "removal_reconciliation_broken", "removal_certificate_agreement"
    ),
    "PORTIA.STORAGE.REMOVAL_TARGET_RETAINED": _PublicDiagnostic(
        "removal", "payload_present_after_removal", "canonical_absence"
    ),
    "PORTIA.STORAGE.REMOVAL_TARGET_CHANGED": _PublicDiagnostic(
        "persistence_recovery", "content_digest_mismatch", "removal_precondition"
    ),
    "PORTIA.STORAGE.UNEXPLAINED_CANONICAL_ABSENCE": _PublicDiagnostic(
        "removal", "removal_certificate_without_target_history", "canonical_absence_evidence"
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

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        authority: IntegrityOperatorAuthority | None = None,
        quarantine: QuarantineGuard | None = None,
    ) -> None:
        self.root = Path(workspace_root)
        self._operations = OperationJournalStore(self.root)
        self._derived = DerivedStore(self.root)
        self._acknowledgements = FindingAcknowledgementStore(self.root)
        self._suppressions = FindingSuppressionStore(self.root)
        self._authority = authority or IntegrityOperatorAuthority.teacher_local()
        self.quarantine = quarantine or QuarantineGuard(self.root)

    @staticmethod
    def operation_scope(operation_id: str) -> dict[str, object]:
        """Return the accepted exact derived-projection scope for one operation."""
        return {
            "scope": "operation",
            "operation_ref": {"operation_id": operation_id},
        }

    def _load_current_findings(
        self,
        projection_scope: Mapping[str, object],
    ) -> tuple[PortiaRecord, ...]:
        scope = dict(projection_scope)
        self.quarantine.require_allowed(
            {
                "kind": "derived_projection",
                "projection_kind": _PROJECTION_KIND,
                "projection_scope": scope,
            },
            "block_projection_use",
        )
        try:
            current = self._derived.load_current(
                _PROJECTION_KIND,
                scope,
                require_fresh=True,
            )
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                "current fresh Integrity Finding state is unavailable"
            ) from exc
        metadata = current.metadata.to_dict()
        if (
            metadata.get("generation_state") != "complete"
            or metadata.get("projection_contract_version") != _PROJECTION_CONTRACT_VERSION
        ):
            raise PortiaCorruptionError(
                "current Integrity Finding generation has an incompatible contract"
            )
        if not isinstance(current.data, dict) or set(current.data) != {"findings"}:
            raise PortiaCorruptionError(
                "current Integrity Finding generation has an invalid data envelope"
            )
        raw_findings = current.data.get("findings")
        if not isinstance(raw_findings, list):
            raise PortiaCorruptionError(
                "current Integrity Finding generation findings are not an array"
            )
        findings: list[PortiaRecord] = []
        by_key: dict[str, dict[str, Any]] = {}
        for raw in raw_findings:
            try:
                finding = parse_portia_record("integrity_finding", "2", raw)
            except Exception as exc:
                raise PortiaCorruptionError(
                    "current Integrity Finding generation contains a malformed finding"
                ) from exc
            data = finding.to_dict()
            finding_key = data.get("finding_key")
            if not isinstance(finding_key, str):
                raise PortiaCorruptionError("Integrity Finding has no exact finding key")
            prior = by_key.get(finding_key)
            if prior is not None:
                raise PortiaCorruptionError(
                    "current Integrity Finding generation contains an ambiguous finding key"
                )
            by_key[finding_key] = data
            findings.append(finding)
        return tuple(findings)

    def current_findings(
        self,
        projection_scope: Mapping[str, object],
    ) -> tuple[PortiaRecord, ...]:
        """Return exact current fresh findings without mutating projection state."""
        return self._load_current_findings(projection_scope)

    def _require_exact_current_finding(
        self,
        projection_scope: Mapping[str, object],
        *,
        finding_key: str,
        evaluation_key: str,
    ) -> PortiaRecord:
        findings = self._load_current_findings(projection_scope)
        keyed = [
            finding
            for finding in findings
            if finding.to_dict().get("finding_key") == finding_key
        ]
        if len(keyed) != 1:
            raise WorkflowPrerequisiteError(
                "requested finding key does not identify one current Integrity Finding"
            )
        if keyed[0].to_dict().get("evaluation_key") != evaluation_key:
            raise WorkflowPrerequisiteError(
                "finding key and evaluation key do not identify the same current finding"
            )
        return keyed[0]

    def _load_operation_reference(
        self,
        value: object,
        *,
        description: str,
    ) -> PortiaRecord:
        reference = _as_mapping(value, description=description)
        if set(reference) != {
            "operation_id",
            "journal_revision",
            "contract_version",
        }:
            raise WorkflowPrerequisiteError(
                f"{description} does not have the exact operation-reference shape"
            )
        operation_id = reference.get("operation_id")
        revision = reference.get("journal_revision")
        contract_version = reference.get("contract_version")
        if (
            not isinstance(operation_id, str)
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or contract_version not in {"2", "3"}
        ):
            raise WorkflowPrerequisiteError(
                f"{description} is not an exact supported Operation Journal reference"
            )
        try:
            current = self._operations.load_current(operation_id)
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                f"{description} does not resolve through accepted Operation Journal authority"
            ) from exc
        selected_revision = current.revision.to_dict().get("journal_revision")
        if current.revision.contract_version != contract_version:
            raise WorkflowPrerequisiteError(
                f"{description} contract version differs from its selected series"
            )
        if not isinstance(selected_revision, int) or revision > selected_revision:
            raise WorkflowPrerequisiteError(
                f"{description} names an unaccepted Operation Journal revision"
            )
        path = operation_revision_path(self.root, operation_id, revision)
        try:
            raw, _bytes, _fingerprint = read_json(path)
            journal = parse_portia_record("operation_journal", contract_version, raw)
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                f"{description} does not resolve to a valid immutable journal"
            ) from exc
        data = journal.to_dict()
        if (
            data.get("operation_id") != operation_id
            or data.get("journal_revision") != revision
            or data.get("state") != "completed"
        ):
            raise WorkflowPrerequisiteError(
                f"{description} does not name an accepted completed operation"
            )
        return journal

    def acknowledge_finding(
        self,
        projection_scope: Mapping[str, object],
        *,
        acknowledgement_id: str,
        finding_key: str,
        evaluation_key: str,
        acknowledged_at: str,
        acknowledged_by: Mapping[str, object],
        acknowledgement_category: str,
        rationale: str | None = None,
        creating_operation: Mapping[str, object] | None = None,
    ) -> StoredAcknowledgement:
        """Persist review evidence for one exact current fresh finding evaluation."""
        self._require_exact_current_finding(
            projection_scope,
            finding_key=finding_key,
            evaluation_key=evaluation_key,
        )
        _parse_timestamp(acknowledged_at, description="acknowledged_at")
        actor = dict(acknowledged_by)
        self._authority.validate_acknowledgement_actor(
            actor,
            acknowledgement_category,
        )
        rationale_value = _bounded_rationale(rationale, optional=True)
        operation_value: dict[str, object] | None = None
        if creating_operation is not None:
            self._load_operation_reference(
                creating_operation,
                description="creating operation",
            )
            operation_value = dict(creating_operation)
        try:
            record = parse_portia_record(
                "finding_acknowledgement",
                "1",
                {
                    "schema_version": "1",
                    "record_type": "finding_acknowledgement",
                    "module_id": "portia",
                    "acknowledgement_id": acknowledgement_id,
                    "finding_key": finding_key,
                    "evaluation_key": evaluation_key,
                    "acknowledged_at": acknowledged_at,
                    "acknowledged_by": actor,
                    "acknowledgement_category": acknowledgement_category,
                    "rationale": rationale_value,
                    "creating_operation": operation_value,
                },
            )
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "Finding Acknowledgement is not runtime/schema valid"
            ) from exc
        return self._acknowledgements.create(record)

    @staticmethod
    def _require_suppressible(finding: PortiaRecord) -> None:
        data = finding.to_dict()
        severity = data.get("severity")
        effects = data.get("effects")
        assessment = data.get("assessment")
        if severity not in _SUPPRESSIBLE_SEVERITIES:
            raise WorkflowPrerequisiteError(
                "only advisory or warning Integrity Findings are suppressible"
            )
        if (
            not isinstance(effects, list)
            or not effects
            or any(effect not in _SUPPRESSIBLE_EFFECTS for effect in effects)
        ):
            raise WorkflowPrerequisiteError(
                "blocking, quarantine, or otherwise prohibited findings cannot be suppressed"
            )
        if (
            isinstance(assessment, dict)
            and assessment.get("result") == "indeterminate"
            and assessment.get("limitation") == "authorization_limited"
        ):
            raise WorkflowPrerequisiteError(
                "authorization-limited findings cannot be concealed by suppression"
            )
        if data.get("code") in _PROHIBITED_SUPPRESSION_CODES:
            raise WorkflowPrerequisiteError(
                "this Integrity Finding class is not suppressible"
            )

    @staticmethod
    def _validate_expiry_conditions(
        conditions: Sequence[Mapping[str, object]],
        *,
        starts_at: str,
    ) -> list[dict[str, object]]:
        if not conditions:
            raise WorkflowPrerequisiteError(
                "active suppression requires at least one expiry condition"
            )
        result = [dict(condition) for condition in conditions]
        if len(result) != len({repr(sorted(condition.items())) for condition in result}):
            raise WorkflowPrerequisiteError("suppression expiry conditions must be unique")
        start = _parse_timestamp(starts_at, description="starts_at")
        for condition in result:
            kind = condition.get("kind")
            if kind == "fixed_timestamp":
                expires = _parse_timestamp(
                    condition.get("expires_at"),
                    description="fixed suppression expiry",
                )
                if expires <= start:
                    raise WorkflowPrerequisiteError(
                        "fixed suppression expiry must be later than starts_at"
                    )
            elif kind not in {
                "target_evaluation_change",
                "rule_version_change",
                "target_revision_or_fingerprint_change",
                "policy_version_change",
                "severity_or_effects_change",
            }:
                raise WorkflowPrerequisiteError(
                    "suppression expiry condition kind is not supported"
                )
        return result

    def suppress_finding(
        self,
        projection_scope: Mapping[str, object],
        *,
        suppression_id: str,
        finding_key: str,
        evaluation_key: str,
        finding_binding: Mapping[str, object],
        presentation_scope: Mapping[str, object],
        policy: Mapping[str, object],
        authorization: Mapping[str, object],
        rationale: str,
        starts_at: str,
        expiry_conditions: Sequence[Mapping[str, object]],
        created_by_operation: Mapping[str, object],
        created_at: str,
    ) -> SeriesState:
        """Create immutable active suppression revision 1 and its exact pointer."""
        finding = self._require_exact_current_finding(
            projection_scope,
            finding_key=finding_key,
            evaluation_key=evaluation_key,
        )
        expected_binding = _exact_finding_binding(finding)
        if dict(finding_binding) != expected_binding:
            raise WorkflowPrerequisiteError(
                "suppression finding binding does not exactly match the current finding"
            )
        self._require_suppressible(finding)
        decision = self._authority.validate_suppression_authorization(
            policy=policy,
            authorization=authorization,
        )
        rationale_value = _bounded_rationale(rationale)
        assert rationale_value is not None
        start_time = _parse_timestamp(starts_at, description="starts_at")
        created_time = _parse_timestamp(created_at, description="created_at")
        if created_time < start_time:
            raise WorkflowPrerequisiteError("suppression created_at predates starts_at")
        conditions = self._validate_expiry_conditions(
            expiry_conditions,
            starts_at=starts_at,
        )
        if any(
            condition.get("kind") == "target_revision_or_fingerprint_change"
            for condition in conditions
        ) and not self._target_evidence(finding):
            raise WorkflowPrerequisiteError(
                "target revision/fingerprint expiry requires exact finding evidence"
            )
        self._load_operation_reference(
            created_by_operation,
            description="suppression creating operation",
        )
        policy_value = {
            "policy_id": decision.policy.policy_id,
            "policy_version": decision.policy.policy_version,
        }
        authorization_value = {
            "authorized_by": dict(decision.authorized_by),
            "asserted_role": decision.asserted_role,
            "authorization_reference": {
                "kind": decision.authorization_reference.kind,
                "reference_id": decision.authorization_reference.reference_id,
                "contract_version": decision.authorization_reference.contract_version,
            },
        }
        value = {
            "schema_version": "1",
            "record_type": "finding_suppression",
            "module_id": "portia",
            "suppression_id": suppression_id,
            "suppression_revision": 1,
            "previous_suppression_revision": None,
            "state": "active",
            "finding_binding": expected_binding,
            "presentation_scope": deepcopy(dict(presentation_scope)),
            "policy": policy_value,
            "authorization": authorization_value,
            "rationale": rationale_value,
            "starts_at": starts_at,
            "expiry_conditions": conditions,
            "origin": {
                "created_by_operation": dict(created_by_operation),
                "created_at": created_at,
            },
            "resolution": None,
            "created_at": created_at,
        }
        try:
            revision = parse_portia_record("finding_suppression", "1", value)
            pointer = parse_portia_record(
                "finding_suppression_current_pointer",
                "1",
                {
                    "schema_version": "1",
                    "record_type": "finding_suppression_current_pointer",
                    "module_id": "portia",
                    "suppression_id": suppression_id,
                    "suppression_revision": 1,
                },
            )
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "Finding Suppression is not runtime/schema valid"
            ) from exc
        return self._suppressions.create(revision, pointer)

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
                    "value": current.revision.contract_version,
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
                {
                    "contract_name": "operation_journal",
                    "contract_version": current.revision.contract_version,
                },
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
                    "contract_version": current.revision.contract_version,
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

    def _historical_exact_finding(
        self,
        projection_scope: Mapping[str, object],
        binding: Mapping[str, object],
    ) -> PortiaRecord:
        """Resolve a bound historical finding by its exact pair, never by recency."""
        scope = dict(projection_scope)
        generations = (
            derived_projection_root(self.root, _PROJECTION_KIND, scope)
            / "generations"
        )
        if not generations.is_dir():
            raise WorkflowPrerequisiteError(
                "bound historical Integrity Finding generation is unavailable"
            )
        matches: list[PortiaRecord] = []
        for generation in sorted(generations.iterdir(), key=lambda item: item.name):
            if not generation.is_dir() or not generation.name.startswith("dgen_"):
                raise PortiaCorruptionError(
                    "unexpected artifact in Integrity Finding generation namespace"
                )
            try:
                metadata_raw, _metadata_bytes, _metadata_fp = read_json(
                    generation / "metadata.json"
                )
                metadata = parse_portia_record(
                    "derived_index_metadata", "1", metadata_raw
                )
                data_raw, _data_bytes, data_fp = read_json(generation / "data.json")
            except Exception as exc:
                raise PortiaCorruptionError(
                    "historical Integrity Finding generation is malformed"
                ) from exc
            metadata_data = metadata.to_dict()
            artifact = metadata_data.get("data_artifact")
            try:
                expected_data_fp = ContentFingerprint.from_dict(
                    artifact.get("fingerprint")
                    if isinstance(artifact, dict)
                    else None
                )
            except ValueError as exc:
                raise PortiaCorruptionError(
                    "historical Integrity Finding data fingerprint is invalid"
                ) from exc
            if (
                metadata_data.get("generation_id") != generation.name
                or metadata_data.get("projection_kind") != _PROJECTION_KIND
                or metadata_data.get("projection_scope") != scope
                or metadata_data.get("projection_contract_version")
                != _PROJECTION_CONTRACT_VERSION
                or data_fp != expected_data_fp
            ):
                raise PortiaCorruptionError(
                    "historical Integrity Finding generation identity is inconsistent"
                )
            if not isinstance(data_raw, dict) or set(data_raw) != {"findings"}:
                raise PortiaCorruptionError(
                    "historical Integrity Finding data envelope is invalid"
                )
            raw_findings = data_raw.get("findings")
            if not isinstance(raw_findings, list):
                raise PortiaCorruptionError(
                    "historical Integrity Finding data is not an array"
                )
            for raw in raw_findings:
                try:
                    finding = parse_portia_record("integrity_finding", "2", raw)
                except Exception as exc:
                    raise PortiaCorruptionError(
                        "historical Integrity Finding is malformed"
                    ) from exc
                data = finding.to_dict()
                if (
                    data.get("finding_key") == binding.get("finding_key")
                    and data.get("evaluation_key") == binding.get("evaluation_key")
                ):
                    matches.append(finding)
        if not matches:
            raise WorkflowPrerequisiteError(
                "bound exact historical Integrity Finding is unavailable"
            )
        first = matches[0].to_dict()
        if any(item.to_dict() != first for item in matches[1:]):
            raise PortiaCorruptionError(
                "bound exact historical Integrity Finding is ambiguous"
            )
        if _exact_finding_binding(matches[0]) != dict(binding):
            raise PortiaCorruptionError(
                "historical Integrity Finding disagrees with suppression binding"
            )
        return matches[0]

    @staticmethod
    def _target_evidence(finding: PortiaRecord) -> tuple[tuple[str, str, object], ...]:
        evidence = finding.to_dict().get("evidence")
        if not isinstance(evidence, list):
            return ()
        values: list[tuple[str, str, object]] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            kind = item.get("kind")
            if (
                isinstance(name, str)
                and isinstance(kind, str)
                and any(marker in name for marker in _TARGET_EVIDENCE_MARKERS)
            ):
                values.append((name, kind, deepcopy(item.get("value"))))
        return tuple(sorted(values, key=lambda item: (item[0], item[1], repr(item[2]))))

    @staticmethod
    def _relevant_current_findings(
        current: Sequence[PortiaRecord],
        historical: PortiaRecord,
    ) -> tuple[PortiaRecord, ...]:
        old = historical.to_dict()
        same_key = tuple(
            finding
            for finding in current
            if finding.to_dict().get("finding_key") == old.get("finding_key")
        )
        if same_key:
            return same_key
        return tuple(
            finding
            for finding in current
            if finding.to_dict().get("primary_target") == old.get("primary_target")
            and finding.to_dict().get("rule_id") == old.get("rule_id")
            and finding.to_dict().get("code") == old.get("code")
        )

    def _condition_matches(
        self,
        current_revision: PortiaRecord,
        condition: Mapping[str, object],
        *,
        projection_scope: Mapping[str, object] | None,
        evaluated_at: str,
    ) -> bool:
        kind = condition.get("kind")
        if kind == "fixed_timestamp":
            return _parse_timestamp(
                evaluated_at, description="expiry evaluation time"
            ) >= _parse_timestamp(
                condition.get("expires_at"),
                description="fixed suppression expiry",
            )

        data = current_revision.to_dict()
        binding = data.get("finding_binding")
        policy = data.get("policy")
        if not isinstance(binding, dict) or not isinstance(policy, dict):
            raise PortiaCorruptionError("selected suppression binding is malformed")
        if kind == "policy_version_change":
            policy_id = policy.get("policy_id")
            policy_version = policy.get("policy_version")
            if not isinstance(policy_id, str) or not isinstance(policy_version, str):
                raise PortiaCorruptionError("selected suppression policy is malformed")
            return self._authority.policy_version_changed(policy_id, policy_version)

        if projection_scope is None:
            raise WorkflowPrerequisiteError(
                "finding-based suppression expiry requires its exact projection scope"
            )
        current = self._load_current_findings(projection_scope)
        finding_key = binding.get("finding_key")
        evaluation_key = binding.get("evaluation_key")
        if kind == "target_evaluation_change":
            return not any(
                finding.to_dict().get("finding_key") == finding_key
                and finding.to_dict().get("evaluation_key") == evaluation_key
                for finding in current
            )

        historical = self._historical_exact_finding(projection_scope, binding)
        relevant = self._relevant_current_findings(current, historical)
        if len(relevant) != 1:
            return False
        candidate = relevant[0]
        candidate_data = candidate.to_dict()
        if kind == "rule_version_change":
            return candidate_data.get("rule_version") != binding.get("rule_version")
        if kind == "severity_or_effects_change":
            return (
                candidate_data.get("severity") != binding.get("severity")
                or candidate_data.get("effects") != binding.get("effects")
            )
        if kind == "target_revision_or_fingerprint_change":
            historical_evidence = self._target_evidence(historical)
            current_evidence = self._target_evidence(candidate)
            if not historical_evidence or not current_evidence:
                return False
            return historical_evidence != current_evidence
        raise WorkflowPrerequisiteError(
            "selected suppression expiry condition is not supported"
        )

    def _active_suppression(
        self,
        suppression_id: str,
        expected_pointer: ContentFingerprint,
    ) -> SeriesState:
        current = self._suppressions.load_current(suppression_id)
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError(
                "current suppression pointer changed since caller observation"
            )
        if current.revision.to_dict().get("state") != "active":
            raise WorkflowPrerequisiteError(
                "suppression transition requires the exact active current revision"
            )
        return current

    def _append_suppression_transition(
        self,
        current: SeriesState,
        value: dict[str, object],
    ) -> SeriesState:
        suppression_id = value.get("suppression_id")
        revision_number = value.get("suppression_revision")
        if not isinstance(suppression_id, str) or not isinstance(revision_number, int):
            raise PortiaCorruptionError("suppression successor identity is malformed")
        try:
            revision = parse_portia_record("finding_suppression", "1", value)
            pointer = parse_portia_record(
                "finding_suppression_current_pointer",
                "1",
                {
                    "schema_version": "1",
                    "record_type": "finding_suppression_current_pointer",
                    "module_id": "portia",
                    "suppression_id": suppression_id,
                    "suppression_revision": revision_number,
                },
            )
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "suppression successor is not runtime/schema valid"
            ) from exc
        return self._suppressions.append(
            revision,
            pointer,
            expected_pointer=current.pointer_fingerprint,
        )

    def release_suppression(
        self,
        suppression_id: str,
        *,
        expected_pointer: ContentFingerprint,
        resolving_operation: Mapping[str, object],
        effective_at: str,
        resolved_by: Mapping[str, object],
        rationale: str,
    ) -> SeriesState:
        """Release one exact active suppression through an immutable successor."""
        current = self._active_suppression(suppression_id, expected_pointer)
        self._load_operation_reference(
            resolving_operation,
            description="release resolving operation",
        )
        self._authority.validate_acknowledgement_actor(dict(resolved_by), "reviewed")
        rationale_value = _bounded_rationale(rationale)
        assert rationale_value is not None
        effective = _parse_timestamp(effective_at, description="release effective_at")
        data = current.revision.to_dict()
        starts = _parse_timestamp(data.get("starts_at"), description="suppression starts_at")
        if effective < starts:
            raise WorkflowPrerequisiteError("release predates suppression starts_at")
        prior = data.get("suppression_revision")
        if not isinstance(prior, int):
            raise PortiaCorruptionError("selected suppression revision is malformed")
        successor: dict[str, object] = {
            key: deepcopy(value) for key, value in data.items()
        }
        successor.update(
            {
                "suppression_revision": prior + 1,
                "previous_suppression_revision": prior,
                "state": "released",
                "resolution": {
                    "kind": "release",
                    "prior_revision": prior,
                    "resolving_operation": {
                        key: deepcopy(value)
                        for key, value in resolving_operation.items()
                    },
                    "effective_at": effective_at,
                    "resolved_by": {
                        key: deepcopy(value) for key, value in resolved_by.items()
                    },
                    "rationale": rationale_value,
                },
                "created_at": effective_at,
            }
        )
        return self._append_suppression_transition(current, successor)

    def expire_suppression(
        self,
        suppression_id: str,
        *,
        expected_pointer: ContentFingerprint,
        matched_expiry_condition: Mapping[str, object],
        evaluated_at: str,
        resolved_by: Mapping[str, object],
        projection_scope: Mapping[str, object] | None = None,
    ) -> SeriesState:
        """Expire an active suppression only after authoritative condition proof."""
        current = self._active_suppression(suppression_id, expected_pointer)
        _parse_timestamp(evaluated_at, description="expiry evaluation time")
        self._authority.validate_acknowledgement_actor(dict(resolved_by), "reviewed")
        data = current.revision.to_dict()
        conditions = data.get("expiry_conditions")
        selected = dict(matched_expiry_condition)
        if not isinstance(conditions, list) or selected not in conditions:
            raise WorkflowPrerequisiteError(
                "matched expiry condition is not one persisted on the active suppression"
            )
        if not self._condition_matches(
            current.revision,
            selected,
            projection_scope=projection_scope,
            evaluated_at=evaluated_at,
        ):
            raise WorkflowPrerequisiteError(
                "authoritative evidence does not satisfy the selected expiry condition"
            )
        prior = data.get("suppression_revision")
        if not isinstance(prior, int):
            raise PortiaCorruptionError("selected suppression revision is malformed")
        successor: dict[str, object] = {
            key: deepcopy(value) for key, value in data.items()
        }
        successor.update(
            {
                "suppression_revision": prior + 1,
                "previous_suppression_revision": prior,
                "state": "expired",
                "resolution": {
                    "kind": "expire",
                    "prior_revision": prior,
                    "matched_expiry_condition": selected,
                    "effective_at": evaluated_at,
                    "resolved_by": {
                        key: deepcopy(value) for key, value in resolved_by.items()
                    },
                },
                "created_at": evaluated_at,
            }
        )
        return self._append_suppression_transition(current, successor)

    def supersede_suppression(
        self,
        suppression_id: str,
        *,
        expected_pointer: ContentFingerprint,
        resolving_operation: Mapping[str, object],
        successor_suppression: Mapping[str, object],
        effective_at: str,
        resolved_by: Mapping[str, object],
        rationale: str,
    ) -> SeriesState:
        """Supersede one active series with an exact explicit successor reference."""
        current = self._active_suppression(suppression_id, expected_pointer)
        self._load_operation_reference(
            resolving_operation,
            description="supersession resolving operation",
        )
        successor_ref = _as_mapping(
            successor_suppression,
            description="successor suppression reference",
        )
        if set(successor_ref) != {
            "suppression_id",
            "suppression_revision",
            "contract_version",
        } or successor_ref.get("contract_version") != "1":
            raise WorkflowPrerequisiteError(
                "successor suppression reference is not exact"
            )
        successor_id = successor_ref.get("suppression_id")
        successor_revision = successor_ref.get("suppression_revision")
        if not isinstance(successor_id, str) or successor_id == suppression_id:
            raise WorkflowPrerequisiteError(
                "suppression series cannot supersede itself"
            )
        successor_current = self._suppressions.load_current(successor_id)
        if (
            successor_current.revision.to_dict().get("suppression_revision")
            != successor_revision
            or successor_current.revision.to_dict().get("state") != "active"
        ):
            raise WorkflowPrerequisiteError(
                "successor suppression is not the exact active selected revision"
            )
        self._authority.validate_acknowledgement_actor(dict(resolved_by), "reviewed")
        rationale_value = _bounded_rationale(rationale)
        assert rationale_value is not None
        effective = _parse_timestamp(
            effective_at, description="supersession effective_at"
        )
        data = current.revision.to_dict()
        starts = _parse_timestamp(data.get("starts_at"), description="suppression starts_at")
        if effective < starts:
            raise WorkflowPrerequisiteError(
                "supersession predates suppression starts_at"
            )
        prior = data.get("suppression_revision")
        if not isinstance(prior, int):
            raise PortiaCorruptionError("selected suppression revision is malformed")
        successor: dict[str, object] = {
            key: deepcopy(value) for key, value in data.items()
        }
        successor.update(
            {
                "suppression_revision": prior + 1,
                "previous_suppression_revision": prior,
                "state": "superseded",
                "resolution": {
                    "kind": "supersede",
                    "prior_revision": prior,
                    "resolving_operation": {
                        key: deepcopy(value)
                        for key, value in resolving_operation.items()
                    },
                    "successor_suppression": successor_ref,
                    "effective_at": effective_at,
                    "resolved_by": {
                        key: deepcopy(value) for key, value in resolved_by.items()
                    },
                    "rationale": rationale_value,
                },
                "created_at": effective_at,
            }
        )
        return self._append_suppression_transition(current, successor)

    def require_effect_allowed(
        self,
        projection_scope: Mapping[str, object],
        requested_target: object,
        effect: str,
    ) -> None:
        """Fail closed when an exact current finding applies one named effect."""
        if effect not in {"block_current_use", "block_operation_completion"}:
            raise WorkflowPrerequisiteError(
                "Integrity Finding guard effect is not owned by Slice 31"
            )
        target = _integrity_target(requested_target)
        for finding in self._load_current_findings(projection_scope):
            data = finding.to_dict()
            effects = data.get("effects")
            if (
                isinstance(effects, list)
                and effect in effects
                and data.get("primary_target") == target
            ):
                raise WorkflowPrerequisiteError(
                    f"current Integrity Finding {data.get('finding_key')!r} blocks {effect}"
                )

    def require_operation_completion(self, operation_id: str) -> None:
        """Enforce current operation-scoped completion blockers directly."""
        self.require_effect_allowed(
            self.operation_scope(operation_id),
            {"kind": "operation", "operation_id": operation_id},
            "block_operation_completion",
        )

class IntegrityGuard(QuarantineGuard):
    """Shared workflow guard combining Quarantine and current Integrity Findings."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        quarantine: QuarantineGuard | None = None,
    ) -> None:
        super().__init__(workspace_root)
        self.quarantine = quarantine or self
        self.integrity = IntegrityWorkflowService(self.root)

    def require_allowed(self, requested_target: object, effect: str) -> None:
        if self.quarantine is self:
            super().require_allowed(requested_target, effect)
        else:
            self.quarantine.require_allowed(requested_target, effect)
        if effect != "block_current_use":
            return
        scope = _projection_scope_for_target(requested_target)
        if scope is None:
            return
        self.integrity.require_effect_allowed(scope, requested_target, effect)
