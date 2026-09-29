"""Closed teacher-reference export policy for Portia Issue #51.

Slice 1 is deliberately pure and read-only.  It defines the exact v0.2
teacher-reference export surface, reuses the accepted Issue #48 privacy-policy
vocabulary, fails closed for unknown contracts/fields, and establishes the
positive local generation-authorization rule.  Source discovery, projection
decisions, rendering, and persistence belong to later Issue #51 slices.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Final, Literal, TypeAlias

from portia.models import MODEL_REGISTRY
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.views.policy import (
    PROJECTION_DISPOSITIONS,
    PROJECTION_PURPOSES,
    STUDENT_VIEW_CONTRACT_INVENTORY,
    STUDENT_VIEW_POLICY,
    STUDENT_VIEW_PROJECTION_INVENTORY,
    ProjectionPurpose,
    StudentViewProjectionRule,
)

TeacherReferencePurpose: TypeAlias = ProjectionPurpose
TeacherReferenceContractSurface: TypeAlias = Literal[
    "work_root_current",
    "domain_current",
    "correction_context",
    "disagreement_context",
    "never_export",
]
TeacherReferenceFieldDisposition: TypeAlias = Literal[
    "included",
    "withheld",
    "requires_manual_review",
]
TeacherReferenceFieldRepresentation: TypeAlias = Literal[
    "scalar",
    "exact_source",
    "embedded_display_snapshot",
    "kind_value",
    "kind_list",
    "enum_list",
    "none",
]
TeacherReferenceSourceKind: TypeAlias = Literal["portia_work", "portia_record"]

TEACHER_REFERENCE_EXPORT_PURPOSES: Final[tuple[TeacherReferencePurpose, ...]] = (
    "teacher_current",
    "participant_specific",
)
TEACHER_REFERENCE_SOURCE_KINDS: Final[tuple[TeacherReferenceSourceKind, ...]] = (
    "portia_work",
    "portia_record",
)

_POLICY_ID: Final[str] = "teacher_reference_export"
_POLICY_VERSION: Final[str] = "1"
_GENERATION_RULE_ID: Final[str] = "teacher_reference_local_generation"
_GENERATION_RULE_VERSION: Final[str] = "1"
_HEX_SHA256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

if frozenset(TEACHER_REFERENCE_EXPORT_PURPOSES) != frozenset(
    PROJECTION_PURPOSES
):
    raise RuntimeError(
        "teacher-reference purpose inventory drifted from the accepted "
        "Issue #48 projection-purpose vocabulary"
    )

if not {
    "included",
    "withheld",
    "requires_manual_review",
}.issubset(PROJECTION_DISPOSITIONS):
    raise RuntimeError(
        "teacher-reference field dispositions drifted from Issue #48 semantics"
    )


@dataclass(frozen=True, slots=True)
class TeacherReferenceWorkRootContract:
    """One exact work-root contract supported by the v0.2 export workflow."""

    record_kind: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "record_kind")
        validate_external_id(self.contract_version, "contract_version")

    @property
    def exact_key(self) -> tuple[str, str]:
        return (self.record_kind, self.contract_version)


TEACHER_REFERENCE_WORK_ROOTS: Final[
    tuple[TeacherReferenceWorkRootContract, ...]
] = (
    TeacherReferenceWorkRootContract("event", "2"),
    TeacherReferenceWorkRootContract("support_process", "1"),
)
_WORK_ROOT_BY_KEY: Final[Mapping[tuple[str, str], TeacherReferenceWorkRootContract]] = (
    MappingProxyType({item.exact_key: item for item in TEACHER_REFERENCE_WORK_ROOTS})
)

if len(_WORK_ROOT_BY_KEY) != len(TEACHER_REFERENCE_WORK_ROOTS):
    raise RuntimeError("teacher-reference work-root inventory contains duplicates")


@dataclass(frozen=True, slots=True)
class TeacherReferenceFieldRule:
    """One exact field-level export disposition under the closed policy."""

    field_name: str
    disposition: TeacherReferenceFieldDisposition
    representation: TeacherReferenceFieldRepresentation

    def __post_init__(self) -> None:
        validate_external_id(self.field_name, "field_name")
        if self.disposition not in {
            "included",
            "withheld",
            "requires_manual_review",
        }:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference field disposition: "
                f"{self.disposition!r}"
            )
        if self.representation not in {
            "scalar",
            "exact_source",
            "embedded_display_snapshot",
            "kind_value",
            "kind_list",
            "enum_list",
            "none",
        }:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference field representation: "
                f"{self.representation!r}"
            )
        if self.disposition == "withheld" and self.representation != "none":
            raise PortiaLocalValidationError(
                "withheld teacher-reference fields cannot carry a representation"
            )
        if (
            self.disposition == "requires_manual_review"
            and self.representation != "exact_source"
        ):
            raise PortiaLocalValidationError(
                "manual-review teacher-reference fields must bind exact source content"
            )
        if self.disposition == "included" and self.representation in {
            "none",
            "exact_source",
        }:
            raise PortiaLocalValidationError(
                "automatically included teacher-reference fields require a bounded "
                "non-source-dump representation"
            )


@dataclass(frozen=True, slots=True)
class TeacherReferenceContractRule:
    """Closed classification for one exact Portia runtime contract/version."""

    record_kind: str
    contract_version: str
    surface: TeacherReferenceContractSurface
    semantic_category: str
    fields: tuple[TeacherReferenceFieldRule, ...] = ()
    exclusion_reason: str | None = None

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "record_kind")
        validate_external_id(self.contract_version, "contract_version")
        validate_external_id(self.semantic_category, "semantic_category")
        if self.surface not in {
            "work_root_current",
            "domain_current",
            "correction_context",
            "disagreement_context",
            "never_export",
        }:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference contract surface: {self.surface!r}"
            )
        names = tuple(field.field_name for field in self.fields)
        if len(set(names)) != len(names):
            raise PortiaLocalValidationError(
                "teacher-reference contract rule cannot repeat a field"
            )
        if self.surface == "never_export":
            if self.fields:
                raise PortiaLocalValidationError(
                    "never-export contract cannot declare exportable fields"
                )
            if self.exclusion_reason is None:
                raise PortiaLocalValidationError(
                    "never-export contract requires an exclusion reason"
                )
        elif self.exclusion_reason is not None:
            raise PortiaLocalValidationError(
                "export-capable contract cannot carry an exclusion reason"
            )

    @property
    def exact_key(self) -> tuple[str, str]:
        return (self.record_kind, self.contract_version)

    @property
    def may_contribute(self) -> bool:
        return self.surface != "never_export"

    @property
    def source_kind(self) -> TeacherReferenceSourceKind | None:
        if self.surface == "work_root_current":
            return "portia_work"
        if self.surface in {
            "domain_current",
            "correction_context",
            "disagreement_context",
        }:
            return "portia_record"
        return None


def _include(
    field_name: str,
    representation: TeacherReferenceFieldRepresentation = "scalar",
) -> TeacherReferenceFieldRule:
    return TeacherReferenceFieldRule(field_name, "included", representation)


def _manual(field_name: str) -> TeacherReferenceFieldRule:
    return TeacherReferenceFieldRule(
        field_name,
        "requires_manual_review",
        "exact_source",
    )


def _withhold(field_name: str) -> TeacherReferenceFieldRule:
    return TeacherReferenceFieldRule(field_name, "withheld", "none")


def _field_map(
    rules: tuple[TeacherReferenceFieldRule, ...],
) -> dict[str, TeacherReferenceFieldRule]:
    return {rule.field_name: rule for rule in rules}


def _issue48_fields(
    rule: StudentViewProjectionRule,
) -> dict[str, TeacherReferenceFieldRule]:
    fields: dict[str, TeacherReferenceFieldRule] = {}
    for name in rule.safe_scalar_fields:
        fields[name] = _include(name)
    for name in rule.manual_review_fields:
        fields[name] = _manual(name)
    for name in rule.withheld_fields:
        fields[name] = _withhold(name)
    return fields


def _current_contract_rule(
    rule: StudentViewProjectionRule,
) -> TeacherReferenceContractRule:
    fields = _issue48_fields(rule)
    key = rule.exact_key

    # Whole-work teacher-reference projection needs bounded work context beyond the
    # focal-student-oriented Issue #48 view.  Free text and indirect-identification
    # context remain manual review rather than becoming automatically safe.
    if key == ("event", "2"):
        fields.update(
            {
                "occurrence": _manual("occurrence"),
                "summary": _manual("summary"),
                "location": _manual("location"),
                "instructional_context": _withhold("instructional_context"),
                "supersedes": _withhold("supersedes"),
            }
        )
    elif key == ("support_process", "1"):
        fields.update(
            {
                "summary": _manual("summary"),
                "initiation": _manual("initiation"),
                "planned_start_date": _include("planned_start_date"),
                "planned_end_date": _include("planned_end_date"),
                "review_on": _include("review_on"),
                "continues_from": _withhold("continues_from"),
                "supersedes": _withhold("supersedes"),
            }
        )

    # Participant identity may cross only through the frozen display snapshot
    # already embedded in the exact work-owned source.  Later slices still own
    # participant-specific applicability and must never live-dereference Core or
    # Actor Directory merely to enrich this representation.
    if key == ("event_participant", "3"):
        fields["subject"] = _include("subject", "embedded_display_snapshot")
    elif key == ("support_process_participant", "1"):
        fields["person"] = _include("person", "embedded_display_snapshot")
        fields["contexts"] = _include("contexts", "kind_list")
    elif key == ("communication", "1"):
        fields["method"] = _include("method", "kind_value")
        fields["purpose"] = _include("purpose", "kind_value")

    surface: TeacherReferenceContractSurface = (
        "work_root_current"
        if rule.surface == "work_root_current"
        else "domain_current"
    )
    return TeacherReferenceContractRule(
        record_kind=rule.record_kind,
        contract_version=rule.contract_version,
        surface=surface,
        semantic_category=rule.category,
        fields=tuple(fields[name] for name in sorted(fields)),
    )


def _correction_context_rule() -> TeacherReferenceContractRule:
    return TeacherReferenceContractRule(
        record_kind="amendment",
        contract_version="1",
        surface="correction_context",
        semantic_category="correction_context",
        fields=(
            _manual("changes"),
            _withhold("previous_amendment"),
            _manual("reason"),
            _withhold("target"),
            _withhold("target_updated_at_before"),
        ),
    )


def _disagreement_context_rule() -> TeacherReferenceContractRule:
    return TeacherReferenceContractRule(
        record_kind="statement_of_disagreement",
        contract_version="1",
        surface="disagreement_context",
        semantic_category="disagreement_context",
        fields=(
            _include("positions", "enum_list"),
            _withhold("source"),
            _manual("statement"),
            _include("status"),
            _withhold("supersedes"),
            _withhold("target"),
        ),
    )


def _never_export_reason(surface: str) -> str:
    if surface == "legacy_history_only":
        return "legacy_or_historical_representation"
    if surface == "history_context":
        return "history_context_not_selected_for_ordinary_export"
    if surface == "identity_support":
        return "actor_or_identity_support_not_export_content"
    if surface == "administrative_context":
        return "administrative_context_not_export_content"
    if surface == "operational_excluded":
        return "operational_or_integrity_state_not_export_content"
    if surface == "export_excluded":
        return "export_provenance_not_domain_content"
    return "unsupported_teacher_reference_surface"


def _contract_rules() -> tuple[TeacherReferenceContractRule, ...]:
    current = {
        key: _current_contract_rule(rule)
        for key, rule in STUDENT_VIEW_PROJECTION_INVENTORY.items()
    }
    current[("amendment", "1")] = _correction_context_rule()
    current[("statement_of_disagreement", "1")] = _disagreement_context_rule()

    rules: list[TeacherReferenceContractRule] = []
    for key in sorted(STUDENT_VIEW_CONTRACT_INVENTORY):
        export_rule = current.get(key)
        if export_rule is not None:
            rules.append(export_rule)
            continue
        student_rule = STUDENT_VIEW_CONTRACT_INVENTORY[key]
        rules.append(
            TeacherReferenceContractRule(
                record_kind=student_rule.record_kind,
                contract_version=student_rule.contract_version,
                surface="never_export",
                semantic_category="excluded",
                exclusion_reason=_never_export_reason(student_rule.surface),
            )
        )
    return tuple(rules)


TEACHER_REFERENCE_CONTRACT_RULES: Final[tuple[TeacherReferenceContractRule, ...]] = (
    _contract_rules()
)
TEACHER_REFERENCE_CONTRACT_INVENTORY: Final[
    Mapping[tuple[str, str], TeacherReferenceContractRule]
] = MappingProxyType(
    {rule.exact_key: rule for rule in TEACHER_REFERENCE_CONTRACT_RULES}
)
TEACHER_REFERENCE_FIELD_INVENTORY: Final[
    Mapping[tuple[str, str, str], TeacherReferenceFieldRule]
] = MappingProxyType(
    {
        (rule.record_kind, rule.contract_version, field.field_name): field
        for rule in TEACHER_REFERENCE_CONTRACT_RULES
        for field in rule.fields
    }
)

if len(TEACHER_REFERENCE_CONTRACT_INVENTORY) != len(
    TEACHER_REFERENCE_CONTRACT_RULES
):
    raise RuntimeError("teacher-reference contract inventory contains duplicates")

if frozenset(TEACHER_REFERENCE_CONTRACT_INVENTORY) != frozenset(
    STUDENT_VIEW_CONTRACT_INVENTORY
):
    raise RuntimeError(
        "teacher-reference export contract inventory drifted from the accepted "
        "Issue #48 contract inventory"
    )

if frozenset(TEACHER_REFERENCE_CONTRACT_INVENTORY) != frozenset(MODEL_REGISTRY):
    raise RuntimeError(
        "teacher-reference export contract inventory drifted from runtime models"
    )


def teacher_reference_contract_rule(
    record_kind: str,
    contract_version: str,
) -> TeacherReferenceContractRule:
    """Return one exact classified contract or fail closed if it is unknown."""
    validate_external_id(record_kind, "record_kind")
    validate_external_id(contract_version, "contract_version")
    rule = TEACHER_REFERENCE_CONTRACT_INVENTORY.get(
        (record_kind, contract_version)
    )
    if rule is None:
        raise PortiaLocalValidationError(
            "unsupported teacher-reference export contract: "
            f"{record_kind}@{contract_version}"
        )
    return rule


def teacher_reference_field_rule(
    record_kind: str,
    contract_version: str,
    field_name: str,
) -> TeacherReferenceFieldRule:
    """Return one declared field rule; unlisted fields fail closed."""
    contract = teacher_reference_contract_rule(record_kind, contract_version)
    validate_external_id(field_name, "field_name")
    if contract.surface == "never_export":
        raise PortiaLocalValidationError(
            "teacher-reference export contract is never-export: "
            f"{record_kind}@{contract_version}"
        )
    rule = TEACHER_REFERENCE_FIELD_INVENTORY.get(
        (record_kind, contract_version, field_name)
    )
    if rule is None:
        raise PortiaLocalValidationError(
            "field is not declared by the closed teacher-reference export policy: "
            f"{record_kind}@{contract_version}.{field_name}"
        )
    return rule


def require_supported_teacher_reference_work_root(
    record_kind: str,
    contract_version: str,
) -> TeacherReferenceWorkRootContract:
    """Require one exact Event@2 or Support Process@1 work root."""
    teacher_reference_contract_rule(record_kind, contract_version)
    work_root = _WORK_ROOT_BY_KEY.get((record_kind, contract_version))
    if work_root is None:
        raise PortiaLocalValidationError(
            "unsupported teacher-reference export work root: "
            f"{record_kind}@{contract_version}"
        )
    return work_root


@dataclass(frozen=True, slots=True)
class TeacherReferenceGenerationRule:
    """Positive local generation authorization rule for Issue #51."""

    policy_rule_id: str
    policy_rule_version: str
    policy_rule_digest: str
    authorization_kind: str = "policy_rule"
    authorized_result: str = "authorized"
    operator_kind: str = "local_operator"
    scope_kind: str = "work"
    output_custody: str = "local_workspace"
    permitted_source_kinds: tuple[TeacherReferenceSourceKind, ...] = (
        "portia_work",
        "portia_record",
    )

    def __post_init__(self) -> None:
        validate_external_id(self.policy_rule_id, "policy_rule_id")
        validate_external_id(self.policy_rule_version, "policy_rule_version")
        if _HEX_SHA256.fullmatch(self.policy_rule_digest) is None:
            raise PortiaLocalValidationError(
                "policy_rule_digest must be a lowercase SHA-256 hex digest"
            )
        if self.authorization_kind != "policy_rule":
            raise PortiaLocalValidationError(
                "teacher-reference generation must use policy_rule authorization"
            )
        if self.authorized_result != "authorized":
            raise PortiaLocalValidationError(
                "teacher-reference generation rule must represent authorized result"
            )
        if self.operator_kind != "local_operator":
            raise PortiaLocalValidationError(
                "teacher-reference generation rule is local-operator only"
            )
        if self.scope_kind != "work":
            raise PortiaLocalValidationError(
                "teacher-reference generation rule is exact-work scoped"
            )
        if self.output_custody != "local_workspace":
            raise PortiaLocalValidationError(
                "teacher-reference generation rule is local-workspace only"
            )
        if self.permitted_source_kinds != TEACHER_REFERENCE_SOURCE_KINDS:
            raise PortiaLocalValidationError(
                "teacher-reference generation source kinds must remain "
                "portia_work + portia_record"
            )


def _generation_rule_descriptor() -> dict[str, object]:
    return {
        "policy_rule_id": _GENERATION_RULE_ID,
        "policy_rule_version": _GENERATION_RULE_VERSION,
        "authorization_kind": "policy_rule",
        "authorized_result": "authorized",
        "operator_kind": "local_operator",
        "supported_purposes": list(TEACHER_REFERENCE_EXPORT_PURPOSES),
        "supported_work_roots": [
            {
                "record_kind": item.record_kind,
                "contract_version": item.contract_version,
            }
            for item in TEACHER_REFERENCE_WORK_ROOTS
        ],
        "scope_kind": "work",
        "permitted_source_kinds": list(TEACHER_REFERENCE_SOURCE_KINDS),
        "output_custody": "local_workspace",
        "authorizes_only": "local_teacher_reference_artifact_generation",
        "does_not_authorize": [
            "disclosure",
            "delivery",
            "recipient_identity",
            "recipient_consent",
            "guardian_authority",
            "legal_entitlement",
            "institutional_approval",
        ],
    }


def teacher_reference_generation_rule_digest() -> str:
    """Return the deterministic digest of the generation-rule definition."""
    payload = json.dumps(
        _generation_rule_descriptor(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


TEACHER_REFERENCE_GENERATION_RULE: Final[TeacherReferenceGenerationRule] = (
    TeacherReferenceGenerationRule(
        policy_rule_id=_GENERATION_RULE_ID,
        policy_rule_version=_GENERATION_RULE_VERSION,
        policy_rule_digest=teacher_reference_generation_rule_digest(),
    )
)


def require_teacher_reference_generation_authorized(
    *,
    projection_purpose: str,
    work_kind: str,
    work_contract_version: str,
    operator_kind: str,
    source_kinds: tuple[str, ...],
    output_custody: str = "local_workspace",
) -> TeacherReferenceGenerationRule:
    """Apply the pure positive generation rule to one bounded intent.

    This does not authorize disclosure or source traversal.  Later slices remain
    responsible for proving that each exact source belongs to the selected work
    or is explicitly permitted correction/disagreement context.
    """
    if projection_purpose not in TEACHER_REFERENCE_EXPORT_PURPOSES:
        raise PortiaLocalValidationError(
            "unsupported teacher-reference projection purpose: "
            f"{projection_purpose!r}"
        )
    require_supported_teacher_reference_work_root(
        work_kind,
        work_contract_version,
    )
    if operator_kind != TEACHER_REFERENCE_GENERATION_RULE.operator_kind:
        raise PortiaLocalValidationError(
            "teacher-reference generation requires a local_operator"
        )
    if output_custody != TEACHER_REFERENCE_GENERATION_RULE.output_custody:
        raise PortiaLocalValidationError(
            "teacher-reference generation is limited to local workspace custody"
        )
    if not source_kinds or "portia_work" not in source_kinds:
        raise PortiaLocalValidationError(
            "teacher-reference generation source set must include the exact "
            "Portia work root"
        )
    unsupported = sorted(
        set(source_kinds) - set(TEACHER_REFERENCE_SOURCE_KINDS)
    )
    if unsupported:
        raise PortiaLocalValidationError(
            "teacher-reference generation source set contains unsupported source "
            f"kind(s): {', '.join(unsupported)}"
        )
    return TEACHER_REFERENCE_GENERATION_RULE


def _field_descriptor(rule: TeacherReferenceFieldRule) -> dict[str, object]:
    return {
        "field_name": rule.field_name,
        "disposition": rule.disposition,
        "representation": rule.representation,
    }


def _contract_descriptor(rule: TeacherReferenceContractRule) -> dict[str, object]:
    descriptor: dict[str, object] = {
        "record_kind": rule.record_kind,
        "contract_version": rule.contract_version,
        "surface": rule.surface,
        "semantic_category": rule.semantic_category,
        "fields": [_field_descriptor(field) for field in rule.fields],
    }
    if rule.exclusion_reason is not None:
        descriptor["exclusion_reason"] = rule.exclusion_reason
    return descriptor


def teacher_reference_policy_descriptor() -> dict[str, object]:
    """Return the immutable JSON-compatible policy definition used for hashing."""
    return {
        "policy_id": _POLICY_ID,
        "policy_version": _POLICY_VERSION,
        "supported_purposes": list(TEACHER_REFERENCE_EXPORT_PURPOSES),
        "supported_work_roots": [
            {
                "record_kind": item.record_kind,
                "contract_version": item.contract_version,
            }
            for item in TEACHER_REFERENCE_WORK_ROOTS
        ],
        "permitted_source_kinds": list(TEACHER_REFERENCE_SOURCE_KINDS),
        "unknown_contract_behavior": "fail_closed",
        "unknown_field_behavior": "fail_closed",
        "live_core_roster_enrichment": "forbidden",
        "live_actor_directory_enrichment": "forbidden",
        "student_view_policy_basis": {
            "policy_id": STUDENT_VIEW_POLICY.policy_id,
            "policy_version": STUDENT_VIEW_POLICY.policy_version,
            "policy_digest": STUDENT_VIEW_POLICY.policy_digest,
        },
        "generation_authorization_rule": {
            "policy_rule_id": TEACHER_REFERENCE_GENERATION_RULE.policy_rule_id,
            "policy_rule_version": (
                TEACHER_REFERENCE_GENERATION_RULE.policy_rule_version
            ),
            "policy_rule_digest": (
                TEACHER_REFERENCE_GENERATION_RULE.policy_rule_digest
            ),
        },
        "contract_inventory": [
            _contract_descriptor(rule)
            for rule in TEACHER_REFERENCE_CONTRACT_RULES
        ],
    }


def teacher_reference_policy_digest() -> str:
    """Return the deterministic digest of the frozen Slice-1 export policy."""
    payload = json.dumps(
        teacher_reference_policy_descriptor(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportPolicy:
    """Exact immutable identity and declared surface for the export policy."""

    policy_id: str
    policy_version: str
    policy_digest: str
    supported_purposes: tuple[TeacherReferencePurpose, ...]
    supported_work_roots: tuple[TeacherReferenceWorkRootContract, ...]

    def __post_init__(self) -> None:
        validate_external_id(self.policy_id, "policy_id")
        validate_external_id(self.policy_version, "policy_version")
        if _HEX_SHA256.fullmatch(self.policy_digest) is None:
            raise PortiaLocalValidationError(
                "policy_digest must be a lowercase SHA-256 hex digest"
            )
        if self.supported_purposes != TEACHER_REFERENCE_EXPORT_PURPOSES:
            raise PortiaLocalValidationError(
                "teacher-reference export policy purpose inventory drift"
            )
        if self.supported_work_roots != TEACHER_REFERENCE_WORK_ROOTS:
            raise PortiaLocalValidationError(
                "teacher-reference export policy work-root inventory drift"
            )


TEACHER_REFERENCE_EXPORT_POLICY: Final[TeacherReferenceExportPolicy] = (
    TeacherReferenceExportPolicy(
        policy_id=_POLICY_ID,
        policy_version=_POLICY_VERSION,
        policy_digest=teacher_reference_policy_digest(),
        supported_purposes=TEACHER_REFERENCE_EXPORT_PURPOSES,
        supported_work_roots=TEACHER_REFERENCE_WORK_ROOTS,
    )
)


__all__ = [
    "TEACHER_REFERENCE_CONTRACT_INVENTORY",
    "TEACHER_REFERENCE_CONTRACT_RULES",
    "TEACHER_REFERENCE_EXPORT_POLICY",
    "TEACHER_REFERENCE_EXPORT_PURPOSES",
    "TEACHER_REFERENCE_FIELD_INVENTORY",
    "TEACHER_REFERENCE_GENERATION_RULE",
    "TEACHER_REFERENCE_SOURCE_KINDS",
    "TEACHER_REFERENCE_WORK_ROOTS",
    "TeacherReferenceContractRule",
    "TeacherReferenceContractSurface",
    "TeacherReferenceExportPolicy",
    "TeacherReferenceFieldDisposition",
    "TeacherReferenceFieldRepresentation",
    "TeacherReferenceFieldRule",
    "TeacherReferenceGenerationRule",
    "TeacherReferencePurpose",
    "TeacherReferenceSourceKind",
    "TeacherReferenceWorkRootContract",
    "require_supported_teacher_reference_work_root",
    "require_teacher_reference_generation_authorized",
    "teacher_reference_contract_rule",
    "teacher_reference_field_rule",
    "teacher_reference_generation_rule_digest",
    "teacher_reference_policy_descriptor",
    "teacher_reference_policy_digest",
]
