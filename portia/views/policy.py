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
        _policy_descriptor(),
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
