"""Zero-write prepared teacher-reference export candidates for Issue #51 Slice 5."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Final

from portia.exports.inventory import (
    TeacherReferenceSourceInventory,
    TeacherReferenceSourceInventoryService,
)
from portia.exports.policy import (
    TEACHER_REFERENCE_EXPORT_POLICY,
    TEACHER_REFERENCE_GENERATION_RULE,
    require_teacher_reference_generation_authorized,
)
from portia.exports.projection import (
    TeacherReferenceProjectionDecision,
    TeacherReferenceProjectionItem,
)
from portia.exports.rendering import (
    TEACHER_REFERENCE_ARTIFACT_FORMAT,
    TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE,
    TeacherReferenceHtmlRenderer,
    TeacherReferenceRenderedArtifact,
)
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import (
    AttributionAgent,
    DeliberateExportV1,
    ExplicitOffsetTimestamp,
    OperationJournalV4,
    OperationLockV3,
)
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id, validate_portia_id
from portia.models.json_values import thaw_json
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaConflictError, PortiaRepository
from portia.storage.deliberate_export_operations import (
    DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
    deliberate_export_immutable_plan,
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.locks import derive_lock_id, validate_operation_lock_application
from portia.storage.operation_journal import validate_operation_journal_application
from portia.storage.paths import resolve_workspace_relative

TEACHER_REFERENCE_PREPARATION_ID: Final[str] = "teacher_reference_export_preparation"
TEACHER_REFERENCE_PREPARATION_VERSION: Final[str] = "1"
TEACHER_REFERENCE_AUTHORIZATION_SCOPE_ID: Final[str] = "teacher_reference_work_export"

_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(r"<h2>([^<]+)</h2>")


def _digest(value: object) -> str:
    return fingerprint_bytes(canonical_json_bytes(value)).digest


def _record_kind(item: TeacherReferenceProjectionItem) -> str:
    if isinstance(item.source_ref, ExactPortiaWorkRef):
        return item.source_ref.work_kind
    return item.source_ref.record_ref.record_kind


def _work_label(work_ref: ExactPortiaWorkRef) -> str:
    label = "Event" if work_ref.work_kind == "event" else "Support Process"
    return f"{label} ({work_ref.work_id})"


def _purpose_label(purpose: str) -> str:
    if purpose == "teacher_current":
        return "Teacher current work reference"
    if purpose == "participant_specific":
        return "Participant-specific work reference"
    raise PortiaLocalValidationError(
        f"unsupported teacher-reference preview purpose: {purpose!r}"
    )


def _focal_display(decision: TeacherReferenceProjectionDecision) -> str | None:
    focal = decision.discovery.scope.focal_subject_ref
    if focal is None:
        return None
    for item in decision.items:
        if (
            item.source_ref == focal
            and item.final_disposition == "included"
            and item.value_present
            and item.field_name in {"subject", "person"}
        ):
            value = thaw_json(item.value)
            if isinstance(value, dict):
                for key in ("display_name", "display_label"):
                    candidate = value.get(key)
                    if isinstance(candidate, str) and candidate.strip():
                        return candidate
    return "Selected participant"


@dataclass(frozen=True, slots=True)
class TeacherReferenceGenerationAuthorization:
    """Exact positive policy-rule generation provenance for one preparation."""

    evaluated_at: str
    recorded_by: AttributionAgent
    authorization_scope_id: str = TEACHER_REFERENCE_AUTHORIZATION_SCOPE_ID

    def __post_init__(self) -> None:
        validate_external_id(self.authorization_scope_id, "authorization_scope_id")
        ExplicitOffsetTimestamp(self.evaluated_at)
        if self.recorded_by.type != "local_operator":
            raise PortiaLocalValidationError(
                "teacher-reference generation authorization requires local_operator recording"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "policy_rule",
            "result": "authorized",
            "authorization_scope_id": self.authorization_scope_id,
            "policy_rule_id": TEACHER_REFERENCE_GENERATION_RULE.policy_rule_id,
            "policy_rule_version": TEACHER_REFERENCE_GENERATION_RULE.policy_rule_version,
            "policy_rule_digest": TEACHER_REFERENCE_GENERATION_RULE.policy_rule_digest,
            "evaluated_at": self.evaluated_at,
            "recorded_by": self.recorded_by.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class TeacherReferencePreviewManualDecision:
    """Teacher-readable summary of one already-resolved manual projection item."""

    record_kind: str
    field_name: str
    resolution: str

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "preview_record_kind")
        validate_external_id(self.field_name, "preview_field_name")
        if self.resolution not in {"include_exact", "omit"}:
            raise PortiaLocalValidationError(
                "teacher-reference preview manual decision is invalid"
            )


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportPreview:
    """Presentation-independent preview of the exact outgoing artifact candidate."""

    selected_work: str
    projection_purpose: str
    projection_purpose_label: str
    focal_participant: str | None
    artifact_format: str
    media_type: str
    included_sections: tuple[str, ...]
    included_count: int
    withheld_count: int
    unavailable_count: int
    absent_count: int
    manual_review_decisions: tuple[TeacherReferencePreviewManualDecision, ...]
    warnings: tuple[str, ...]
    artifact_html: str
    export_id: str
    artifact_relative_path: str
    artifact_byte_length: int
    artifact_sha256: str
    source_inventory_digest: str
    projection_decision_digest: str
    preparation_digest: str

    def __post_init__(self) -> None:
        if self.artifact_format != "html" or self.media_type != "text/html":
            raise PortiaLocalValidationError(
                "teacher-reference preview supports the exact HTML candidate only"
            )
        validate_portia_id(self.export_id, "pexp_", "preview_export_id")
        if not self.artifact_html.endswith("\n"):
            raise PortiaLocalValidationError(
                "teacher-reference preview must carry exact rendered HTML"
            )
        for value in (
            self.included_count,
            self.withheld_count,
            self.unavailable_count,
            self.absent_count,
            self.artifact_byte_length,
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise PortiaLocalValidationError(
                    "teacher-reference preview counts/length must be nonnegative integers"
                )


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportPreparation:
    """One exact immutable zero-write export candidate reviewed before confirmation."""

    decision: TeacherReferenceProjectionDecision
    inventory: TeacherReferenceSourceInventory
    artifact: TeacherReferenceRenderedArtifact
    authorization: TeacherReferenceGenerationAuthorization
    export_id: str
    operation_id: str
    artifact_relative_path: str
    provenance_relative_path: str
    deliberate_export: DeliberateExportV1
    operation_journal: OperationJournalV4
    operation_lock: OperationLockV3
    preparation_fingerprint: ContentFingerprint
    preview: TeacherReferenceExportPreview
    preparation_id: str = TEACHER_REFERENCE_PREPARATION_ID
    preparation_version: str = TEACHER_REFERENCE_PREPARATION_VERSION

    def __post_init__(self) -> None:
        if self.preparation_id != TEACHER_REFERENCE_PREPARATION_ID:
            raise PortiaLocalValidationError("unsupported teacher-reference preparation")
        if self.preparation_version != TEACHER_REFERENCE_PREPARATION_VERSION:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference preparation version"
            )
        if not self.decision.is_final:
            raise PortiaLocalValidationError(
                "teacher-reference preparation requires a final projection"
            )
        validate_portia_id(self.export_id, "pexp_", "export_id")
        validate_portia_id(self.operation_id, "op_", "operation_id")
        if self.artifact_relative_path != (
            f"portia/exports/{self.export_id}/artifact.html"
        ):
            raise PortiaLocalValidationError(
                "teacher-reference artifact path must be exact export-scoped HTML"
            )
        if self.provenance_relative_path != (
            f"portia/exports/{self.export_id}/export.json"
        ):
            raise PortiaLocalValidationError(
                "teacher-reference provenance path must be exact export.json"
            )
        validate_operation_journal_application(self.operation_journal)
        validate_operation_lock_application(self.operation_lock)
        validate_deliberate_export_lock_agreement(
            self.operation_journal,
            self.operation_lock,
        )
        validate_deliberate_export_candidate_reconciliation(
            self.operation_journal,
            self.deliberate_export,
        )
        if self.preparation_fingerprint != _preparation_fingerprint(
            self.decision,
            self.inventory,
            self.artifact,
            self.authorization,
            self.export_id,
            self.operation_id,
            self.artifact_relative_path,
            self.provenance_relative_path,
            self.deliberate_export,
            self.operation_journal,
            self.operation_lock,
        ):
            raise PortiaLocalValidationError(
                "teacher-reference preparation fingerprint does not bind exact candidate"
            )
        if self.preview.preparation_digest != self.preparation_digest:
            raise PortiaLocalValidationError(
                "teacher-reference preview does not bind exact preparation"
            )
        if self.preview.artifact_html != self.artifact.text:
            raise PortiaLocalValidationError(
                "teacher-reference preview differs from exact artifact bytes"
            )

    @property
    def preparation_digest(self) -> str:
        return self.preparation_fingerprint.digest

    @property
    def artifact_bytes(self) -> bytes:
        return self.artifact.content

    @property
    def provenance_bytes(self) -> bytes:
        return canonical_json_bytes(self.deliberate_export.to_dict())


def _preparation_fingerprint(
    decision: TeacherReferenceProjectionDecision,
    inventory: TeacherReferenceSourceInventory,
    artifact: TeacherReferenceRenderedArtifact,
    authorization: TeacherReferenceGenerationAuthorization,
    export_id: str,
    operation_id: str,
    artifact_relative_path: str,
    provenance_relative_path: str,
    deliberate_export: DeliberateExportV1,
    operation_journal: OperationJournalV4,
    operation_lock: OperationLockV3,
) -> ContentFingerprint:
    journal_bytes = canonical_json_bytes(operation_journal.to_dict())
    lock_bytes = canonical_json_bytes(operation_lock.to_dict())
    immutable_plan = deliberate_export_immutable_plan(operation_journal)
    descriptor: dict[str, object] = {
        "preparation_id": TEACHER_REFERENCE_PREPARATION_ID,
        "preparation_version": TEACHER_REFERENCE_PREPARATION_VERSION,
        "work_ref": decision.discovery.scope.work_ref.to_dict(),
        "focal_subject_ref": (
            None
            if decision.discovery.scope.focal_subject_ref is None
            else decision.discovery.scope.focal_subject_ref.to_dict()
        ),
        "projection_purpose": decision.discovery.scope.projection_purpose,
        "projection_policy": {
            "policy_id": TEACHER_REFERENCE_EXPORT_POLICY.policy_id,
            "policy_version": TEACHER_REFERENCE_EXPORT_POLICY.policy_version,
            "policy_digest": TEACHER_REFERENCE_EXPORT_POLICY.policy_digest,
        },
        "authorization": authorization.to_dict(),
        "projection_decision_algorithm": decision.projection_decision_algorithm,
        "projection_decision_digest": decision.projection_decision_digest,
        "disposition_summary": decision.disposition_summary.to_dict(),
        "manual_review": decision.manual_review.to_export_dict(),
        "source_inventory": inventory.to_dict(),
        "renderer": {
            "renderer_id": artifact.renderer_id,
            "format": artifact.output_format,
            "media_type": artifact.media_type,
            "fingerprint": artifact.fingerprint.to_dict(),
        },
        "future_identity": {
            "export_id": export_id,
            "operation_id": operation_id,
            "artifact_relative_path": artifact_relative_path,
            "provenance_relative_path": provenance_relative_path,
        },
        "deliberate_export": deliberate_export.to_dict(),
        "operation_journal_candidate_fingerprint": fingerprint_bytes(
            journal_bytes
        ).to_dict(),
        "operation_journal_immutable_plan_digest": hashlib.sha256(
            immutable_plan
        ).hexdigest(),
        "operation_lock_candidate_fingerprint": fingerprint_bytes(lock_bytes).to_dict(),
    }
    return fingerprint_bytes(canonical_json_bytes(descriptor))


def _preflight(
    target: dict[str, object],
    role: str,
    path: str,
    contract_version: str,
    observed_at: str,
) -> dict[str, object]:
    return {
        "target": target,
        "representation_role": role,
        "expected_state": {"presence": "must_be_absent"},
        "workspace_relative_path": path,
        "contract_version": contract_version,
        "source_basis": "canonical",
        "source_projection": None,
        "selected_state": [],
        "observed_at": observed_at,
    }


def _write_step(
    *,
    step_id: str,
    sequence: int,
    role: str,
    target: dict[str, object],
    path: str,
    contract_version: str,
    fingerprint: ContentFingerprint,
    selected_state: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "step_id": step_id,
        "sequence": sequence,
        "phase": "canonical_gate",
        "action": "exclusive_create",
        "target": target,
        "representation_role": role,
        "destination_path": path,
        "precondition": {"presence": "must_be_absent"},
        "intended_result": {
            "kind": "present",
            "contract_version": contract_version,
            "fingerprint": fingerprint.to_dict(),
            "selected_state": selected_state,
        },
        "disposition": "staged",
        "observed_result": None,
        "compensation_step_id": None,
        "reason_code": None,
    }


def _manual_preview(
    decision: TeacherReferenceProjectionDecision,
) -> tuple[TeacherReferencePreviewManualDecision, ...]:
    values: list[TeacherReferencePreviewManualDecision] = []
    for item in decision.items:
        if item.field_name is None or item.manual_resolution is None:
            continue
        values.append(
            TeacherReferencePreviewManualDecision(
                record_kind=_record_kind(item),
                field_name=item.field_name,
                resolution=item.manual_resolution,
            )
        )
    return tuple(values)


def _warnings(decision: TeacherReferenceProjectionDecision) -> tuple[str, ...]:
    summary = decision.disposition_summary
    warnings = [
        "Local teacher reference only; this export is not a disclosure or official institutional record."
    ]
    if summary.withheld:
        warnings.append(
            f"{summary.withheld} projection item(s) are withheld by policy or manual choice."
        )
    if summary.unavailable:
        warnings.append(
            f"{summary.unavailable} projection item(s) were unavailable and are not represented as false/no."
        )
    if summary.manual_review_resolved:
        warnings.append(
            f"{summary.manual_review_resolved} manual-review item(s) were explicitly resolved."
        )
    if decision.discovery.scope.projection_purpose == "participant_specific":
        warnings.append(
            "Participant-specific scope does not establish recipient or disclosure authorization."
        )
    return tuple(warnings)


class TeacherReferenceExportPreparationService:
    """Build one exact reviewed export candidate without any persistence writes."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        id_generator: PortiaIdGenerator | None = None,
        inventory_service: TeacherReferenceSourceInventoryService | None = None,
        renderer: TeacherReferenceHtmlRenderer | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.id_generator = id_generator or PortiaIdGenerator()
        self.inventory_service = inventory_service or TeacherReferenceSourceInventoryService(
            self.workspace_root,
            repository=self.repository,
        )
        self.renderer = renderer or TeacherReferenceHtmlRenderer()

    def prepare(
        self,
        decision: TeacherReferenceProjectionDecision,
        *,
        requested_at: str,
        requested_by: Mapping[str, object],
        generated_at: str,
        generated_by: Mapping[str, object] | None = None,
        deployment_instance_id: str,
        process_instance_id: str,
    ) -> TeacherReferenceExportPreparation:
        if not isinstance(decision, TeacherReferenceProjectionDecision):
            raise TypeError("decision must be a TeacherReferenceProjectionDecision")
        if not decision.is_final:
            raise PortiaLocalValidationError(
                "teacher-reference preparation requires completed manual review"
            )

        requester = AttributionAgent.from_dict(requested_by)
        generator = AttributionAgent.from_dict(
            requested_by if generated_by is None else generated_by
        )
        if requester.type != "local_operator" or generator.type != "local_operator":
            raise PortiaLocalValidationError(
                "teacher-reference preparation requires local_operator attribution"
            )
        requested_ts = ExplicitOffsetTimestamp(requested_at)
        generated_ts = ExplicitOffsetTimestamp(generated_at)
        if generated_ts.datetime < requested_ts.datetime:
            raise PortiaLocalValidationError(
                "teacher-reference generation cannot predate its request"
            )
        if decision.manual_review.reviewed_at is not None:
            reviewed = ExplicitOffsetTimestamp(decision.manual_review.reviewed_at)
            if generated_ts.datetime < reviewed.datetime:
                raise PortiaLocalValidationError(
                    "teacher-reference generation cannot predate manual review"
                )
        validate_external_id(deployment_instance_id, "deployment_instance_id")
        validate_external_id(process_instance_id, "process_instance_id")

        inventory = self.inventory_service.author(decision)
        artifact = self.renderer.render(decision, inventory)
        source_kinds = tuple(
            sorted({str(entry["source_kind"]) for entry in inventory.entries})
        )
        require_teacher_reference_generation_authorized(
            projection_purpose=decision.discovery.scope.projection_purpose,
            work_kind=decision.discovery.scope.work_ref.work_kind,
            work_contract_version=decision.discovery.scope.work_ref.contract_version,
            operator_kind=requester.type,
            source_kinds=source_kinds,
        )
        authorization = TeacherReferenceGenerationAuthorization(
            evaluated_at=generated_at,
            recorded_by=generator,
        )

        export_id = self.id_generator.new("pexp_")
        operation_id = self.id_generator.new("op_")
        artifact_step_id = self.id_generator.new("step_")
        provenance_step_id = self.id_generator.new("step_")
        if artifact_step_id == provenance_step_id:
            raise PortiaLocalValidationError(
                "teacher-reference preparation requires distinct operation step IDs"
            )
        artifact_path = f"portia/exports/{export_id}/artifact.html"
        provenance_path = f"portia/exports/{export_id}/export.json"
        artifact_target = resolve_workspace_relative(self.workspace_root, artifact_path)
        provenance_target = resolve_workspace_relative(
            self.workspace_root,
            provenance_path,
        )
        if artifact_target.exists() or provenance_target.exists():
            raise PortiaConflictError(
                "prospective teacher-reference export identity is already present"
            )

        target: dict[str, object] = {
            "kind": "deliberate_export",
            "export_ref": {"export_id": export_id, "contract_version": "1"},
        }
        lock_id = derive_lock_id("deliberate_export", target)
        lock_target = self.workspace_root / f"portia/locks/{lock_id}.json"
        if lock_target.exists():
            raise PortiaConflictError(
                "prospective teacher-reference export lock identity is already present"
            )

        committed_revision = 2
        export_data: dict[str, object] = {
            "schema_version": "1",
            "record_type": "deliberate_export",
            "module_id": "portia",
            "export_id": export_id,
            "projection_purpose": decision.discovery.scope.projection_purpose,
            "export_scope": {
                "scope": "work",
                "work_ref": decision.discovery.scope.work_ref.to_dict(),
            },
            "projection_policy": {
                "policy_id": TEACHER_REFERENCE_EXPORT_POLICY.policy_id,
                "policy_version": TEACHER_REFERENCE_EXPORT_POLICY.policy_version,
                "policy_digest": TEACHER_REFERENCE_EXPORT_POLICY.policy_digest,
            },
            "authorization": authorization.to_dict(),
            "source_inventory": inventory.to_dict(),
            "projection_decision_algorithm": decision.projection_decision_algorithm,
            "projection_decision_digest": decision.projection_decision_digest,
            "disposition_summary": decision.disposition_summary.to_dict(),
            "manual_review": decision.manual_review.to_export_dict(),
            "output": {
                "format": artifact.output_format,
                "media_type": artifact.media_type,
                "workspace_relative_path": artifact_path,
                "byte_length": artifact.byte_length,
                "sha256_digest": artifact.representation_digest,
            },
            "operation_journal_ref": {
                "operation_id": operation_id,
                "journal_revision": committed_revision,
                "contract_version": "4",
            },
            "requested_at": requested_at,
            "requested_by": requester.to_dict(),
            "generated_at": generated_at,
            "generated_by": generator.to_dict(),
        }
        focal = decision.discovery.scope.focal_subject_ref
        if focal is not None:
            export_data["focal_subject_ref"] = focal.to_dict()
        deliberate_export = DeliberateExportV1(export_data)
        provenance_fp = fingerprint_bytes(
            canonical_json_bytes(deliberate_export.to_dict())
        )

        preflight = [
            _preflight(
                target,
                "deliberate_export_artifact",
                artifact_path,
                DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
                generated_at,
            ),
            _preflight(
                target,
                "deliberate_export_provenance",
                provenance_path,
                "1",
                generated_at,
            ),
        ]
        write_set = [
            _write_step(
                step_id=artifact_step_id,
                sequence=1,
                role="deliberate_export_artifact",
                target=target,
                path=artifact_path,
                contract_version=DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
                fingerprint=artifact.fingerprint,
                selected_state=[],
            ),
            _write_step(
                step_id=provenance_step_id,
                sequence=2,
                role="deliberate_export_provenance",
                target=target,
                path=provenance_path,
                contract_version="1",
                fingerprint=provenance_fp,
                selected_state=[
                    {
                        "name": "committed_journal_revision",
                        "kind": "integer",
                        "value": committed_revision,
                    }
                ],
            ),
        ]
        intent_descriptor = {
            "operation_kind": "generate_deliberate_export",
            "primary_target": target,
            "artifact": {
                "path": artifact_path,
                "fingerprint": artifact.fingerprint.to_dict(),
            },
            "provenance": {
                "path": provenance_path,
                "fingerprint": provenance_fp.to_dict(),
            },
        }
        journal_data: dict[str, object] = {
            "schema_version": "4",
            "record_type": "operation_journal",
            "module_id": "portia",
            "operation_id": operation_id,
            "operation_kind": "generate_deliberate_export",
            "intent_digest": _digest(intent_descriptor),
            "scope": "workspace",
            "primary_target": target,
            "affected_targets": [],
            "intent_facts": [],
            "initiated_at": requested_at,
            "initiated_by": requester.to_dict(),
            "authorization_references": [],
            "journal_revision": 1,
            "previous_journal_revision": None,
            "state": "staged",
            "preflight_snapshot_digest": _digest(preflight),
            "preflight_snapshot": preflight,
            "lock_set": [
                {
                    "lock_id": lock_id,
                    "sequence": 1,
                    "lock_scope": "deliberate_export",
                    "protected_target": target,
                    "lock_path": f"portia/locks/{lock_id}.json",
                    "disposition": "planned",
                    "fingerprint": None,
                    "acquired_at": None,
                    "released_at": None,
                }
            ],
            "write_set": write_set,
            "staged_artifacts": [],
            "commit_point": {"reached": False, "reached_at": None},
            "compensation_plan": [],
            "recovery_plan": [
                "resume",
                "complete_remaining_steps",
                "abandon_preacceptance_artifacts",
                "require_manual_review",
            ],
            "partial_state": {
                "durability_assessment": "none",
                "accepted_steps": [],
                "verified_steps": [],
                "durable_unverified_steps": [],
                "indeterminate_steps": [],
                "remaining_canonical_steps": [
                    artifact_step_id,
                    provenance_step_id,
                ],
                "remaining_post_commit_steps": [],
                "current_pointer_changes": [],
                "held_or_possible_locks": [],
                "quarantined_targets": [],
                "active_finding_keys": [],
                "recommended_disposition": "resume",
            },
            "created_at": generated_at,
            "updated_at": generated_at,
        }
        operation_journal = OperationJournalV4(journal_data)
        if planned_deliberate_export_commit_revision(operation_journal) != committed_revision:
            raise PortiaLocalValidationError(
                "teacher-reference journal reserved the wrong committed revision"
            )
        operation_lock = OperationLockV3(
            {
                "schema_version": "3",
                "record_type": "operation_lock",
                "module_id": "portia",
                "lock_id": lock_id,
                "lock_scope": "deliberate_export",
                "protected_target": target,
                "owning_operation": {"operation_id": operation_id},
                "acquired_at": generated_at,
                "deployment_instance_id": deployment_instance_id,
                "process_instance_id": process_instance_id,
            }
        )
        validate_operation_journal_application(operation_journal)
        validate_operation_lock_application(operation_lock)
        validate_deliberate_export_lock_agreement(operation_journal, operation_lock)
        validate_deliberate_export_candidate_reconciliation(
            operation_journal,
            deliberate_export,
        )

        prep_fp = _preparation_fingerprint(
            decision,
            inventory,
            artifact,
            authorization,
            export_id,
            operation_id,
            artifact_path,
            provenance_path,
            deliberate_export,
            operation_journal,
            operation_lock,
        )
        section_names = tuple(unescape(item) for item in _SECTION_PATTERN.findall(artifact.text))
        summary = decision.disposition_summary
        preview = TeacherReferenceExportPreview(
            selected_work=_work_label(decision.discovery.scope.work_ref),
            projection_purpose=decision.discovery.scope.projection_purpose,
            projection_purpose_label=_purpose_label(
                decision.discovery.scope.projection_purpose
            ),
            focal_participant=_focal_display(decision),
            artifact_format=TEACHER_REFERENCE_ARTIFACT_FORMAT,
            media_type=TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE,
            included_sections=section_names,
            included_count=summary.included,
            withheld_count=summary.withheld,
            unavailable_count=summary.unavailable,
            absent_count=summary.absent,
            manual_review_decisions=_manual_preview(decision),
            warnings=_warnings(decision),
            artifact_html=artifact.text,
            export_id=export_id,
            artifact_relative_path=artifact_path,
            artifact_byte_length=artifact.byte_length,
            artifact_sha256=artifact.representation_digest,
            source_inventory_digest=inventory.inventory_digest,
            projection_decision_digest=decision.projection_decision_digest,
            preparation_digest=prep_fp.digest,
        )
        return TeacherReferenceExportPreparation(
            decision=decision,
            inventory=inventory,
            artifact=artifact,
            authorization=authorization,
            export_id=export_id,
            operation_id=operation_id,
            artifact_relative_path=artifact_path,
            provenance_relative_path=provenance_path,
            deliberate_export=deliberate_export,
            operation_journal=operation_journal,
            operation_lock=operation_lock,
            preparation_fingerprint=prep_fp,
            preview=preview,
        )


__all__ = [
    "TEACHER_REFERENCE_AUTHORIZATION_SCOPE_ID",
    "TEACHER_REFERENCE_PREPARATION_ID",
    "TEACHER_REFERENCE_PREPARATION_VERSION",
    "TeacherReferenceExportPreparation",
    "TeacherReferenceExportPreparationService",
    "TeacherReferenceExportPreview",
    "TeacherReferenceGenerationAuthorization",
    "TeacherReferencePreviewManualDecision",
]
