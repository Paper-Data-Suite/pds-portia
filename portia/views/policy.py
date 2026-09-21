"""Closed policy identity and contract inventory for student views.

Issue #48 keeps the student timeline/work view derived and fail-closed.  This
module intentionally defines only the immutable policy identity and the exact
contract/version inventory.  Field projection and chronology adapters are
implemented in later slices.
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

ProjectionPurpose: TypeAlias = Literal["teacher_current", "participant_specific"]
ContractSurface: TypeAlias = Literal[
    "work_root_current",
    "legacy_history_only",
    "domain_current",
    "history_context",
    "identity_support",
    "administrative_context",
    "operational_excluded",
    "export_excluded",
]

PROJECTION_PURPOSES: Final[tuple[ProjectionPurpose, ...]] = (
    "participant_specific",
    "teacher_current",
)
PROJECTION_DISPOSITIONS: Final[tuple[str, ...]] = (
    "included",
    "absent",
    "withheld",
    "unavailable",
    "requires_manual_review",
)

_POLICY_ID: Final[str] = "student_timeline_work_view"
_POLICY_VERSION: Final[str] = "1"
_HEX_SHA256: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class StudentViewContractRule:
    """One exact runtime contract/version classification for Issue #48."""

    record_kind: str
    contract_version: str
    surface: ContractSurface

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "record_kind")
        validate_external_id(self.contract_version, "contract_version")
        if self.surface not in {
            "work_root_current",
            "legacy_history_only",
            "domain_current",
            "history_context",
            "identity_support",
            "administrative_context",
            "operational_excluded",
            "export_excluded",
        }:
            raise PortiaLocalValidationError(
                f"unsupported student-view contract surface: {self.surface!r}"
            )

    @property
    def exact_key(self) -> tuple[str, str]:
        return (self.record_kind, self.contract_version)

    @property
    def ordinary_view_candidate(self) -> bool:
        return self.surface not in {
            "identity_support",
            "operational_excluded",
            "export_excluded",
        }


def _rules(
    record_kind: str,
    versions: tuple[str, ...],
    surface: ContractSurface,
) -> tuple[StudentViewContractRule, ...]:
    return tuple(
        StudentViewContractRule(record_kind, version, surface)
        for version in versions
    )


STUDENT_VIEW_CONTRACT_RULES: Final[tuple[StudentViewContractRule, ...]] = (
    *_rules("event", ("1",), "legacy_history_only"),
    *_rules("event", ("2",), "work_root_current"),
    *_rules("event_participant", ("1", "2"), "legacy_history_only"),
    *_rules("event_participant", ("3",), "domain_current"),
    *_rules("event_participant_role", ("1", "2"), "legacy_history_only"),
    *_rules("event_participant_role", ("3",), "domain_current"),
    *_rules("work_relationship", ("1",), "legacy_history_only"),
    *_rules("work_relationship", ("2",), "domain_current"),
    *_rules("actor", ("1",), "identity_support"),
    *_rules("actor_contact_point", ("1",), "identity_support"),
    *_rules("actor_student_relationship", ("1",), "identity_support"),
    *_rules("actor_roster_student_collision", ("1",), "identity_support"),
    *_rules(
        "actor_directory_lifecycle_transition",
        ("1",),
        "identity_support",
    ),
    *_rules(
        "actor_directory_lifecycle_history_correction",
        ("1",),
        "identity_support",
    ),
    *_rules("actor_directory_amendment", ("1",), "identity_support"),
    *_rules("actor_directory_record_migration", ("1",), "identity_support"),
    *_rules(
        "actor_directory_exceptional_removal",
        ("1",),
        "identity_support",
    ),
    *_rules("account", ("1", "2"), "domain_current"),
    *_rules("observation", ("1", "2"), "domain_current"),
    *_rules("review", ("1",), "domain_current"),
    *_rules("classification", ("1",), "domain_current"),
    *_rules("hypothesis", ("1",), "domain_current"),
    *_rules("determination", ("1",), "domain_current"),
    *_rules("response", ("1",), "domain_current"),
    *_rules("communication", ("1",), "domain_current"),
    *_rules("support_process", ("1",), "work_root_current"),
    *_rules("support_process_participant", ("1",), "domain_current"),
    *_rules("support_need", ("1",), "domain_current"),
    *_rules("support_goal", ("1",), "domain_current"),
    *_rules("support", ("1",), "domain_current"),
    *_rules("intervention", ("1",), "domain_current"),
    *_rules("implementation", ("1",), "domain_current"),
    *_rules("fidelity", ("1",), "domain_current"),
    *_rules("follow_up", ("1",), "domain_current"),
    *_rules("outcome", ("1",), "domain_current"),
    *_rules("reentry", ("1",), "domain_current"),
    *_rules("repair", ("1",), "domain_current"),
    *_rules("lifecycle_transition", ("1",), "history_context"),
    *_rules("lifecycle_history_correction", ("1",), "history_context"),
    *_rules("amendment", ("1",), "history_context"),
    *_rules("statement_of_disagreement", ("1",), "history_context"),
    *_rules("dependency", ("1",), "administrative_context"),
    *_rules("record_migration", ("1",), "administrative_context"),
    *_rules("ownership_correction", ("1", "2"), "administrative_context"),
    *_rules("exceptional_removal", ("1",), "administrative_context"),
    *_rules("operation_journal", ("1", "2", "3"), "operational_excluded"),
    *_rules("operation_current_pointer", ("1",), "operational_excluded"),
    *_rules("operation_lock", ("1", "2"), "operational_excluded"),
    *_rules("quarantine_record", ("1", "2"), "operational_excluded"),
    *_rules("quarantine_current_pointer", ("1",), "operational_excluded"),
    *_rules("integrity_finding", ("1", "2"), "operational_excluded"),
    *_rules("finding_acknowledgement", ("1",), "operational_excluded"),
    *_rules("finding_suppression", ("1",), "operational_excluded"),
    *_rules(
        "finding_suppression_current_pointer",
        ("1",),
        "operational_excluded",
    ),
    *_rules("source_snapshot", ("1",), "operational_excluded"),
    *_rules("derived_index_metadata", ("1",), "operational_excluded"),
    *_rules("derived_current_pointer", ("1",), "operational_excluded"),
    *_rules("export_source_inventory", ("1",), "export_excluded"),
    *_rules("deliberate_export", ("1",), "export_excluded"),
)

STUDENT_VIEW_CONTRACT_INVENTORY: Final[
    Mapping[tuple[str, str], StudentViewContractRule]
] = MappingProxyType(
    {rule.exact_key: rule for rule in STUDENT_VIEW_CONTRACT_RULES}
)

if len(STUDENT_VIEW_CONTRACT_INVENTORY) != len(STUDENT_VIEW_CONTRACT_RULES):
    raise RuntimeError("student-view contract inventory contains duplicate exact keys")

if frozenset(STUDENT_VIEW_CONTRACT_INVENTORY) != frozenset(MODEL_REGISTRY):
    missing = sorted(
        frozenset(MODEL_REGISTRY) - frozenset(STUDENT_VIEW_CONTRACT_INVENTORY)
    )
    extra = sorted(
        frozenset(STUDENT_VIEW_CONTRACT_INVENTORY) - frozenset(MODEL_REGISTRY)
    )
    raise RuntimeError(
        "student-view contract inventory drift: "
        f"missing={missing}, extra={extra}"
    )


def contract_rule(
    record_kind: str,
    contract_version: str,
) -> StudentViewContractRule:
    """Return one explicitly classified exact contract or fail closed."""
    validate_external_id(record_kind, "record_kind")
    validate_external_id(contract_version, "contract_version")
    rule = STUDENT_VIEW_CONTRACT_INVENTORY.get((record_kind, contract_version))
    if rule is None:
        raise PortiaLocalValidationError(
            "unsupported student-view contract: "
            f"{record_kind}@{contract_version}"
        )
    return rule


def current_work_root_rule(
    record_kind: str,
    contract_version: str,
) -> StudentViewContractRule:
    """Require one exact current work-root representation."""
    rule = contract_rule(record_kind, contract_version)
    if rule.surface != "work_root_current":
        raise PortiaLocalValidationError(
            "student current-view work scope requires a current work-root "
            f"contract, not {record_kind}@{contract_version}"
        )
    return rule


@dataclass(frozen=True, slots=True)
class StudentViewPolicyIdentity:
    """Exact immutable identity for the code-owned Issue #48 projection policy."""

    policy_id: str
    policy_version: str
    policy_digest: str

    def __post_init__(self) -> None:
        validate_external_id(self.policy_id, "policy_id")
        validate_external_id(self.policy_version, "policy_version")
        if _HEX_SHA256.fullmatch(self.policy_digest) is None:
            raise PortiaLocalValidationError(
                "policy_digest must be a lowercase SHA-256 hex digest"
            )

ProjectionCategory = Literal[
    "work_context",
    "participation",
    "evidence",
    "judgment",
    "response",
    "support",
    "implementation",
    "follow_up",
]
ProjectionAdapterKind = Literal[
    "work_root",
    "participant",
    "role",
    "relationship",
    "account",
    "observation",
    "judgment",
    "response",
    "communication",
    "support",
    "implementation",
    "fidelity",
    "follow_up",
    "outcome",
    "reentry",
    "repair",
]


@dataclass(frozen=True, slots=True)
class StudentViewProjectionRule:
    """Positive field policy for one exact current-view contract."""

    record_kind: str
    contract_version: str
    surface: ContractSurface
    category: ProjectionCategory
    adapter: ProjectionAdapterKind
    safe_scalar_fields: tuple[str, ...] = ()
    manual_review_fields: tuple[str, ...] = ()
    withheld_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        contract = contract_rule(self.record_kind, self.contract_version)
        if contract.surface != self.surface:
            raise PortiaLocalValidationError(
                "projection rule surface disagrees with contract inventory"
            )
        if self.surface not in {"work_root_current", "domain_current"}:
            raise PortiaLocalValidationError(
                "ordinary current-view projection rule must name a current surface"
            )
        for group in (
            self.safe_scalar_fields,
            self.manual_review_fields,
            self.withheld_fields,
        ):
            if len(set(group)) != len(group):
                raise PortiaLocalValidationError(
                    "projection rule cannot repeat a field within one disposition"
                )
        all_fields = (
            *self.safe_scalar_fields,
            *self.manual_review_fields,
            *self.withheld_fields,
        )
        if len(set(all_fields)) != len(all_fields):
            raise PortiaLocalValidationError(
                "projection rule field dispositions must be mutually exclusive"
            )

    @property
    def exact_key(self) -> tuple[str, str]:
        return (self.record_kind, self.contract_version)


def _projection_rule(
    record_kind: str,
    versions: tuple[str, ...],
    category: ProjectionCategory,
    adapter: ProjectionAdapterKind,
    *,
    safe: tuple[str, ...] = (),
    manual: tuple[str, ...] = (),
    withheld: tuple[str, ...] = (),
) -> tuple[StudentViewProjectionRule, ...]:
    rules: list[StudentViewProjectionRule] = []
    for version in versions:
        surface = contract_rule(record_kind, version).surface
        rules.append(
            StudentViewProjectionRule(
                record_kind,
                version,
                surface,
                category,
                adapter,
                safe,
                manual,
                withheld,
            )
        )
    return tuple(rules)


STUDENT_VIEW_PROJECTION_RULES: Final[tuple[StudentViewProjectionRule, ...]] = (
    *_projection_rule("event", ("2",), "work_context", "work_root", safe=("status",), withheld=("summary",)),
    *_projection_rule("support_process", ("1",), "work_context", "work_root", safe=("status", "workflow_state"), withheld=("summary", "initiation")),
    *_projection_rule("event_participant", ("3",), "participation", "participant", safe=("status",), withheld=("subject",)),
    *_projection_rule("event_participant_role", ("3",), "participation", "role", safe=("status", "role_type"), withheld=("target", "basis")),
    *_projection_rule("work_relationship", ("2",), "participation", "relationship", safe=("status", "relationship_type"), withheld=("source", "target")),
    *_projection_rule("account", ("1", "2"), "evidence", "account", safe=("status", "information_origin", "source_certainty"), manual=("content", "elicitation_context"), withheld=("target", "source", "related_accounts", "source_artifacts")),
    *_projection_rule("observation", ("1", "2"), "evidence", "observation", safe=("status", "method"), manual=("content", "method_detail"), withheld=("target", "observer", "source_artifacts")),
    *_projection_rule("review", ("1",), "judgment", "judgment", safe=("status", "review_state"), manual=("trigger", "question", "evidence_considered"), withheld=("target", "reviewer", "requested_by", "review_subjects")),
    *_projection_rule("classification", ("1",), "judgment", "judgment", safe=("status", "stage"), manual=("result", "basis"), withheld=("target", "selector", "review_ref", "reviewed_classification")),
    *_projection_rule("hypothesis", ("1",), "judgment", "judgment", safe=("status", "consideration_state"), manual=("proposition", "rationale", "evidence"), withheld=("target", "author", "review_ref")),
    *_projection_rule("determination", ("1",), "judgment", "judgment", safe=("status", "authority_context", "process_basis"), manual=("question", "outcome", "rationale", "basis"), withheld=("target", "decision_maker", "review_ref")),
    *_projection_rule("response", ("1",), "response", "response", safe=("status", "execution_state"), manual=("action",), withheld=("target", "provider", "review_ref", "determination_ref")),
    *_projection_rule("communication", ("1",), "response", "communication", safe=("status", "privacy_scope", "act_state"), manual=("summary",), withheld=("sender", "recipients", "attachments", "relations")),
    *_projection_rule("support_process_participant", ("1",), "participation", "participant", safe=("status",), withheld=("person",)),
    *_projection_rule("support_need", ("1",), "support", "support", safe=("status", "need_kind"), manual=("description", "kind_detail"), withheld=("target",)),
    *_projection_rule("support_goal", ("1",), "support", "support", safe=("status",), manual=("description", "planned_criteria", "measurement_approach"), withheld=("target",)),
    *_projection_rule("support", ("1",), "support", "support", safe=("status", "plan_state"), manual=("strategy", "schedule"), withheld=("target", "need_refs", "goal_refs", "provider_plan")),
    *_projection_rule("intervention", ("1",), "support", "support", safe=("status", "plan_state"), manual=("strategy", "schedule", "monitoring_approach"), withheld=("target", "need_refs", "goal_refs", "provider_plan")),
    *_projection_rule("implementation", ("1",), "implementation", "implementation", safe=("status", "execution_state"), manual=("variation", "summary"), withheld=("plan_ref", "actual_target", "implementation_provider")),
    *_projection_rule("fidelity", ("1",), "implementation", "fidelity", safe=("status", "result"), manual=("summary", "instrument_result"), withheld=("plan_ref", "evaluator_ref", "scope", "basis")),
    *_projection_rule("follow_up", ("1",), "follow_up", "follow_up", safe=("status", "workflow_state"), manual=("purpose", "disposition"), withheld=("target", "owner", "related_records")),
    *_projection_rule("outcome", ("1",), "follow_up", "outcome", safe=("status", "result"), manual=("result_detail", "limitations", "summary"), withheld=("target", "evaluator", "scope", "basis")),
    *_projection_rule("reentry", ("1",), "follow_up", "reentry", safe=("status", "workflow_state"), manual=("planned_elements",), withheld=("target", "coordinator", "support_refs")),
    *_projection_rule("repair", ("1",), "follow_up", "repair", safe=("status", "workflow_state"), manual=("focus", "actions"), withheld=("target", "facilitator", "participants", "context_refs")),
)

STUDENT_VIEW_PROJECTION_INVENTORY: Final[Mapping[tuple[str, str], StudentViewProjectionRule]] = MappingProxyType(
    {rule.exact_key: rule for rule in STUDENT_VIEW_PROJECTION_RULES}
)

_CURRENT_PROJECTION_KEYS: Final[frozenset[tuple[str, str]]] = frozenset(
    rule.exact_key
    for rule in STUDENT_VIEW_CONTRACT_RULES
    if rule.surface in {"work_root_current", "domain_current"}
)
if frozenset(STUDENT_VIEW_PROJECTION_INVENTORY) != _CURRENT_PROJECTION_KEYS:
    missing = sorted(_CURRENT_PROJECTION_KEYS - frozenset(STUDENT_VIEW_PROJECTION_INVENTORY))
    extra = sorted(frozenset(STUDENT_VIEW_PROJECTION_INVENTORY) - _CURRENT_PROJECTION_KEYS)
    raise RuntimeError(
        "student-view projection inventory drift: "
        f"missing={missing}, extra={extra}"
    )


def projection_rule(record_kind: str, contract_version: str) -> StudentViewProjectionRule:
    """Return one exact positive current-view projection adapter or fail closed."""
    contract_rule(record_kind, contract_version)
    rule = STUDENT_VIEW_PROJECTION_INVENTORY.get((record_kind, contract_version))
    if rule is None:
        raise PortiaLocalValidationError(
            "unsupported ordinary student-view projection contract: "
            f"{record_kind}@{contract_version}"
        )
    return rule


def projection_rules() -> tuple[StudentViewProjectionRule, ...]:
    return STUDENT_VIEW_PROJECTION_RULES


def known_contract_versions(record_kind: str) -> frozenset[str]:
    versions = frozenset(
        version for kind, version in STUDENT_VIEW_CONTRACT_INVENTORY if kind == record_kind
    )
    if not versions:
        raise PortiaLocalValidationError(
            f"student-view contract kind is not classified: {record_kind!r}"
        )
    return versions


def projection_policy_descriptor() -> list[dict[str, object]]:
    return [
        {
            "record_kind": rule.record_kind,
            "contract_version": rule.contract_version,
            "surface": rule.surface,
            "category": rule.category,
            "adapter": rule.adapter,
            "safe_scalar_fields": list(rule.safe_scalar_fields),
            "manual_review_fields": list(rule.manual_review_fields),
            "withheld_fields": list(rule.withheld_fields),
        }
        for rule in STUDENT_VIEW_PROJECTION_RULES
    ]



def _policy_descriptor() -> dict[str, object]:
    return {
        "policy_id": _POLICY_ID,
        "policy_version": _POLICY_VERSION,
        "projection_purposes": list(PROJECTION_PURPOSES),
        "projection_dispositions": list(PROJECTION_DISPOSITIONS),
        "identity_basis": "core_roster_class_id_plus_student_id",
        "ordinary_projection_persistence": "none",
        "unknown_contract_behavior": "fail_closed",
        "contract_inventory": [
            {
                "record_kind": rule.record_kind,
                "contract_version": rule.contract_version,
                "surface": rule.surface,
            }
            for rule in STUDENT_VIEW_CONTRACT_RULES
        ],
    }


def student_view_policy_digest() -> str:
    """Return the deterministic digest of the frozen Slice-1 policy descriptor."""
    payload = json.dumps(
        _policy_descriptor() | {
            "projection_inventory": projection_policy_descriptor(),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return sha256(payload).hexdigest()


STUDENT_VIEW_POLICY: Final[StudentViewPolicyIdentity] = StudentViewPolicyIdentity(
    policy_id=_POLICY_ID,
    policy_version=_POLICY_VERSION,
    policy_digest=student_view_policy_digest(),
)
