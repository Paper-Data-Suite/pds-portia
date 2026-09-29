"""Restricted projection decisions and manual review for Portia Issue #51.

Slice 3 turns the exact read-only source observations from Slice 2 into a
restricted in-memory decision manifest.  It applies the closed Slice 1 field
policy, preserves exact source fingerprints and scope applicability, requires
explicit include-exact/omit choices for policy-designated manual-review fields,
and derives the published ``portia_projection_decision_v1`` digest plus the
privacy-minimized disposition summary.

This module renders no artifact and writes no canonical or operational state.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Final, Literal, TypeAlias

from portia.exports.discovery import (
    TeacherReferenceScopeDiscovery,
    TeacherReferenceSourceObservation,
    TeacherReferenceSourceRef,
    TeacherReferenceSourceRole,
)
from portia.exports.policy import (
    TEACHER_REFERENCE_EXPORT_POLICY,
    TeacherReferenceFieldDisposition,
    TeacherReferenceFieldRepresentation,
    teacher_reference_contract_rule,
)
from portia.models.common import AttributionAgent, ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.json_values import FrozenJsonValue, freeze_json, thaw_json
from portia.models.references import ExactPortiaWorkRef
from portia.storage import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaRepository,
    StoredRecord,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.views import FocalApplicability, NativeScope

TeacherReferenceProjectionDisposition: TypeAlias = Literal[
    "included",
    "withheld",
    "unavailable",
    "absent",
    "requires_manual_review",
]
TeacherReferenceManualResolution: TypeAlias = Literal["include_exact", "omit"]
TeacherReferenceManualReviewStatus: TypeAlias = Literal[
    "pending",
    "not_required",
    "resolved",
]

PROJECTION_DECISION_ALGORITHM: Final[str] = "portia_projection_decision_v1"
_FINAL_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"included", "withheld", "unavailable", "absent"}
)


def _source_key(source: TeacherReferenceSourceRef) -> tuple[str, ...]:
    if isinstance(source, ExactPortiaWorkRef):
        return (
            source.class_id,
            source.work_kind,
            source.work_id,
            source.contract_version,
            "",
            "",
            "",
        )
    return (
        source.work_ref.class_id,
        source.work_ref.work_kind,
        source.work_ref.work_id,
        source.work_ref.contract_version,
        source.record_ref.record_kind,
        source.record_ref.record_id,
        source.record_ref.contract_version,
    )


def _source_dict(source: TeacherReferenceSourceRef) -> dict[str, object]:
    if isinstance(source, ExactPortiaWorkRef):
        return {"source_kind": "portia_work", "work_ref": source.to_dict()}
    return {"source_kind": "portia_record", "work_record_ref": source.to_dict()}


def _item_key(item: "TeacherReferenceProjectionItem") -> tuple[str, ...]:
    return (
        *_source_key(item.source_ref),
        "" if item.field_name is None else item.field_name,
    )


def _value_fingerprint(
    value: FrozenJsonValue | None,
    *,
    present: bool,
) -> ContentFingerprint | None:
    if not present:
        return None
    return fingerprint_bytes(canonical_json_bytes(thaw_json(value)))


def _frozen_equal(first: FrozenJsonValue, second: FrozenJsonValue) -> bool:
    return thaw_json(first) == thaw_json(second)


def _represented_value(
    raw: object,
    representation: TeacherReferenceFieldRepresentation,
) -> FrozenJsonValue | None:
    """Return only the bounded automatic representation authorized by policy.

    ``None`` means the representation is not safely available from the exact
    stored field.  Callers must fail closed to withholding rather than widening
    the representation.
    """

    if representation == "scalar":
        if raw is None or not isinstance(raw, (str, int, float, bool)):
            return None
        return freeze_json(raw)

    if representation == "embedded_display_snapshot":
        if not isinstance(raw, Mapping):
            return None
        snapshot = raw.get("display_snapshot")
        if not isinstance(snapshot, Mapping):
            return None
        return freeze_json(snapshot)

    if representation == "kind_value":
        if not isinstance(raw, Mapping):
            return None
        kind = raw.get("kind")
        if not isinstance(kind, str) or not kind:
            return None
        return freeze_json(kind)

    if representation == "kind_list":
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            return None
        kinds: list[str] = []
        for entry in raw:
            if not isinstance(entry, Mapping):
                return None
            kind = entry.get("kind")
            if not isinstance(kind, str) or not kind:
                return None
            kinds.append(kind)
        return freeze_json(kinds)

    if representation == "enum_list":
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            return None
        values: list[str] = []
        for entry in raw:
            if not isinstance(entry, str) or not entry:
                return None
            values.append(entry)
        return freeze_json(values)

    if representation in {"exact_source", "none"}:
        return None

    raise PortiaLocalValidationError(
        f"unsupported teacher-reference field representation: {representation!r}"
    )


@dataclass(frozen=True, slots=True)
class TeacherReferenceProjectionItem:
    """One restricted source/field projection decision.

    Raw manual-review source content is retained only in ``review_value`` and is
    excluded from ``repr``.  Automatically included or explicitly included
    output content is retained only in ``value`` and is likewise excluded from
    ``repr``.  The persisted deliberate-export contract never stores this
    detailed item collection.
    """

    source_ref: TeacherReferenceSourceRef
    source_role: TeacherReferenceSourceRole
    source_fingerprint: ContentFingerprint
    focal_applicability: FocalApplicability
    native_scope: NativeScope
    final_disposition: TeacherReferenceProjectionDisposition
    reason_code: str
    field_name: str | None = None
    policy_disposition: TeacherReferenceFieldDisposition | None = None
    representation: TeacherReferenceFieldRepresentation | None = None
    manual_resolution: TeacherReferenceManualResolution | None = None
    focal_relation: str | None = None
    context_target_ref: TeacherReferenceSourceRef | None = None
    value: FrozenJsonValue | None = field(default=None, repr=False)
    review_value: FrozenJsonValue | None = field(default=None, repr=False)
    value_present: bool = field(default=False, repr=False)
    review_value_present: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if self.final_disposition not in {
            "included",
            "withheld",
            "unavailable",
            "absent",
            "requires_manual_review",
        }:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference projection disposition: "
                f"{self.final_disposition!r}"
            )
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise PortiaLocalValidationError(
                "teacher-reference projection item requires a non-empty reason_code"
            )

        if self.field_name is None:
            if self.policy_disposition is not None or self.representation is not None:
                raise PortiaLocalValidationError(
                    "source-level projection item cannot carry a field policy"
                )
            if self.final_disposition not in {"withheld", "unavailable"}:
                raise PortiaLocalValidationError(
                    "source-level projection item must be withheld or unavailable"
                )
            if (
                self.value_present
                or self.review_value_present
                or self.value is not None
                or self.review_value is not None
            ):
                raise PortiaLocalValidationError(
                    "source-level withheld/unavailable item cannot carry content"
                )
            if self.manual_resolution is not None:
                raise PortiaLocalValidationError(
                    "source-level projection item cannot carry manual resolution"
                )
            return

        validate_external_id(self.field_name, "projection_field_name")
        if self.policy_disposition not in {
            "included",
            "withheld",
            "requires_manual_review",
        }:
            raise PortiaLocalValidationError(
                "field projection item requires an exact closed-policy disposition"
            )
        if self.representation is None:
            raise PortiaLocalValidationError(
                "field projection item requires its policy representation"
            )

        if self.final_disposition == "absent":
            if (
                self.manual_resolution is not None
                or self.value_present
                or self.review_value_present
                or self.value is not None
                or self.review_value is not None
            ):
                raise PortiaLocalValidationError(
                    "absent field item cannot carry projection or manual-review content"
                )
            return

        if self.policy_disposition == "requires_manual_review":
            if not self.review_value_present:
                raise PortiaLocalValidationError(
                    "manual-review projection item requires exact source content"
                )
            if self.manual_resolution is None:
                if self.final_disposition != "requires_manual_review":
                    raise PortiaLocalValidationError(
                        "unresolved manual-review item must remain "
                        "requires_manual_review"
                    )
                if self.value_present or self.value is not None:
                    raise PortiaLocalValidationError(
                        "unresolved manual-review item cannot expose output content"
                    )
                return
            if self.manual_resolution == "include_exact":
                if self.final_disposition != "included" or not self.value_present:
                    raise PortiaLocalValidationError(
                        "include_exact manual resolution must include exact content"
                    )
                if not _frozen_equal(self.review_value, self.value):
                    raise PortiaLocalValidationError(
                        "include_exact manual resolution changed source content"
                    )
            elif self.manual_resolution == "omit":
                if (
                    self.final_disposition != "withheld"
                    or self.value_present
                    or self.value is not None
                ):
                    raise PortiaLocalValidationError(
                        "omit manual resolution must withhold without replacement "
                        "content"
                    )
            else:
                raise PortiaLocalValidationError(
                    f"unsupported manual-review resolution: {self.manual_resolution!r}"
                )
            return

        if (
            self.manual_resolution is not None
            or self.review_value_present
            or self.review_value is not None
        ):
            raise PortiaLocalValidationError(
                "automatic field decision cannot carry manual-review state"
            )
        if self.final_disposition == "included":
            if self.policy_disposition != "included" or not self.value_present:
                raise PortiaLocalValidationError(
                    "included automatic item requires included policy and bounded "
                    "content"
                )
        elif self.final_disposition in {"withheld", "absent"}:
            if self.value_present or self.value is not None:
                raise PortiaLocalValidationError(
                    "withheld/absent field item cannot carry output content"
                )
        else:
            raise PortiaLocalValidationError(
                "automatic field item has incompatible final disposition"
            )

    @property
    def source_kind(self) -> Literal["portia_work", "portia_record"]:
        if isinstance(self.source_ref, ExactPortiaWorkRef):
            return "portia_work"
        return "portia_record"

    @property
    def projected_value_fingerprint(self) -> ContentFingerprint | None:
        return _value_fingerprint(self.value, present=self.value_present)

    @property
    def manual_review_required(self) -> bool:
        return self.policy_disposition == "requires_manual_review"

    @property
    def is_resolved(self) -> bool:
        return self.final_disposition != "requires_manual_review"


@dataclass(frozen=True, slots=True)
class TeacherReferenceManualReviewChoice:
    """One explicit include-exact/omit choice; no replacement text is accepted."""

    source_ref: TeacherReferenceSourceRef
    field_name: str
    resolution: TeacherReferenceManualResolution

    def __post_init__(self) -> None:
        validate_external_id(self.field_name, "manual_review_field_name")
        if self.resolution not in {"include_exact", "omit"}:
            raise PortiaLocalValidationError(
                f"unsupported manual-review resolution: {self.resolution!r}"
            )

    @property
    def key(self) -> tuple[TeacherReferenceSourceRef, str]:
        return (self.source_ref, self.field_name)


@dataclass(frozen=True, slots=True)
class TeacherReferenceManualReview:
    """Restricted review state; only final states map to deliberate_export@1."""

    status: TeacherReferenceManualReviewStatus
    reviewed_projection_digest: str | None = None
    reviewed_at: str | None = None
    reviewed_by: AttributionAgent | None = None

    def __post_init__(self) -> None:
        if self.status not in {"pending", "not_required", "resolved"}:
            raise PortiaLocalValidationError(
                f"unsupported teacher-reference manual-review status: {self.status!r}"
            )
        if self.status in {"pending", "not_required"}:
            if any(
                value is not None
                for value in (
                    self.reviewed_projection_digest,
                    self.reviewed_at,
                    self.reviewed_by,
                )
            ):
                raise PortiaLocalValidationError(
                    f"manual-review status {self.status} cannot carry review metadata"
                )
            return
        digest = self.reviewed_projection_digest
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise PortiaLocalValidationError(
                "resolved manual review requires a lowercase SHA-256 projection digest"
            )
        if self.reviewed_at is None:
            raise PortiaLocalValidationError(
                "resolved manual review requires reviewed_at"
            )
        ExplicitOffsetTimestamp(self.reviewed_at)
        if self.reviewed_by is None or self.reviewed_by.type != "local_operator":
            raise PortiaLocalValidationError(
                "resolved manual review requires a local_operator reviewer"
            )

    def to_export_dict(self) -> dict[str, object]:
        if self.status == "pending":
            raise PortiaLocalValidationError(
                "pending manual review cannot be materialized into export provenance"
            )
        if self.status == "not_required":
            return {"status": "not_required"}
        assert self.reviewed_projection_digest is not None
        assert self.reviewed_at is not None
        assert self.reviewed_by is not None
        return {
            "status": "resolved",
            "reviewed_projection_digest": self.reviewed_projection_digest,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class TeacherReferenceDispositionSummary:
    """Privacy-minimized final counts accepted by deliberate_export@1."""

    included: int
    withheld: int
    unavailable: int
    absent: int
    manual_review_resolved: int
    count_unit: str = "projection_item"

    def __post_init__(self) -> None:
        if self.count_unit != "projection_item":
            raise PortiaLocalValidationError(
                'teacher-reference disposition count_unit must be "projection_item"'
            )
        for name in (
            "included",
            "withheld",
            "unavailable",
            "absent",
            "manual_review_resolved",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise PortiaLocalValidationError(
                    f"disposition summary {name} must be a nonnegative integer"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "count_unit": self.count_unit,
            "included": self.included,
            "withheld": self.withheld,
            "unavailable": self.unavailable,
            "absent": self.absent,
            "manual_review_resolved": self.manual_review_resolved,
        }


def _projection_item_descriptor(
    item: TeacherReferenceProjectionItem,
) -> dict[str, object]:
    descriptor: dict[str, object] = {
        **_source_dict(item.source_ref),
        "source_role": item.source_role,
        "source_representation": item.source_fingerprint.to_dict(),
        "focal_applicability": item.focal_applicability,
        "native_scope": item.native_scope,
        "focal_relation": item.focal_relation,
        "context_target_ref": (
            None
            if item.context_target_ref is None
            else _source_dict(item.context_target_ref)
        ),
        "field_name": item.field_name,
        "policy_disposition": item.policy_disposition,
        "representation": item.representation,
        "final_disposition": item.final_disposition,
        "manual_resolution": item.manual_resolution,
        "reason_code": item.reason_code,
    }
    value_fingerprint = item.projected_value_fingerprint
    descriptor["projected_value_fingerprint"] = (
        None if value_fingerprint is None else value_fingerprint.to_dict()
    )
    return descriptor


def teacher_reference_projection_descriptor(
    discovery: TeacherReferenceScopeDiscovery,
    items: tuple[TeacherReferenceProjectionItem, ...],
) -> dict[str, object]:
    """Return the restricted deterministic digest descriptor, never raw manual text."""

    scope = discovery.scope
    return {
        "projection_decision_algorithm": PROJECTION_DECISION_ALGORITHM,
        "projection_policy": {
            "policy_id": TEACHER_REFERENCE_EXPORT_POLICY.policy_id,
            "policy_version": TEACHER_REFERENCE_EXPORT_POLICY.policy_version,
            "policy_digest": TEACHER_REFERENCE_EXPORT_POLICY.policy_digest,
        },
        "projection_purpose": scope.projection_purpose,
        "export_scope": {"scope": "work", "work_ref": scope.work_ref.to_dict()},
        "focal_subject_ref": (
            None
            if scope.focal_subject_ref is None
            else scope.focal_subject_ref.to_dict()
        ),
        "items": [_projection_item_descriptor(item) for item in items],
    }


def teacher_reference_projection_digest(
    discovery: TeacherReferenceScopeDiscovery,
    items: tuple[TeacherReferenceProjectionItem, ...],
) -> str:
    """Derive the exact published projection-decision digest."""

    if items != tuple(sorted(items, key=_item_key)):
        raise PortiaLocalValidationError(
            "teacher-reference projection digest requires deterministic item ordering"
        )
    descriptor = teacher_reference_projection_descriptor(discovery, items)
    return hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest()


@dataclass(frozen=True, slots=True)
class TeacherReferenceProjectionDecision:
    """Restricted deterministic projection state for one exact discovered scope."""

    discovery: TeacherReferenceScopeDiscovery
    items: tuple[TeacherReferenceProjectionItem, ...]
    manual_review: TeacherReferenceManualReview
    projection_decision_algorithm: str = PROJECTION_DECISION_ALGORITHM

    def __post_init__(self) -> None:
        if self.projection_decision_algorithm != PROJECTION_DECISION_ALGORITHM:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference projection decision algorithm"
            )
        if not self.items:
            raise PortiaLocalValidationError(
                "teacher-reference projection decision requires at least one item"
            )
        if self.items != tuple(sorted(self.items, key=_item_key)):
            raise PortiaLocalValidationError(
                "teacher-reference projection items must use deterministic ordering"
            )
        keys = tuple((item.source_ref, item.field_name) for item in self.items)
        if len(set(keys)) != len(keys):
            raise PortiaLocalValidationError(
                "teacher-reference projection cannot repeat one source/field decision"
            )

        observed = {item.source_ref for item in self.discovery.observations}
        projected = {item.source_ref for item in self.items}
        if projected != observed:
            raise PortiaLocalValidationError(
                "teacher-reference projection must represent every exact discovered "
                "source and no others"
            )
        observation_by_ref = {
            item.source_ref: item for item in self.discovery.observations
        }
        for item in self.items:
            observation = observation_by_ref[item.source_ref]
            if item.source_fingerprint != observation.fingerprint:
                raise PortiaLocalValidationError(
                    "projection item fingerprint differs from exact source observation"
                )
            if item.source_role != observation.source_role:
                raise PortiaLocalValidationError(
                    "projection item source role differs from discovery"
                )
            if item.focal_applicability != observation.focal_applicability:
                raise PortiaLocalValidationError(
                    "projection item applicability differs from discovery"
                )
            if item.context_target_ref != observation.context_target_ref:
                raise PortiaLocalValidationError(
                    "projection item context target differs from discovery"
                )

        unresolved = tuple(
            item
            for item in self.items
            if item.final_disposition == "requires_manual_review"
        )
        manual_items = tuple(item for item in self.items if item.manual_review_required)
        if unresolved:
            if self.manual_review.status != "pending":
                raise PortiaLocalValidationError(
                    "unresolved manual-review items require pending review status"
                )
        elif manual_items:
            if self.manual_review.status != "resolved":
                raise PortiaLocalValidationError(
                    "resolved manual-review items require resolved review status"
                )
            if (
                self.manual_review.reviewed_projection_digest
                != self.projection_decision_digest
            ):
                raise PortiaLocalValidationError(
                    "manual review must bind the exact resolved projection digest"
                )
        elif self.manual_review.status != "not_required":
            raise PortiaLocalValidationError(
                "projection without manual-review fields must be not_required"
            )

    @property
    def projection_decision_digest(self) -> str:
        return teacher_reference_projection_digest(self.discovery, self.items)

    @property
    def unresolved_manual_items(self) -> tuple[TeacherReferenceProjectionItem, ...]:
        return tuple(
            item
            for item in self.items
            if item.final_disposition == "requires_manual_review"
        )

    @property
    def is_final(self) -> bool:
        return (
            not self.unresolved_manual_items
            and self.manual_review.status != "pending"
        )

    @property
    def disposition_summary(self) -> TeacherReferenceDispositionSummary:
        if not self.is_final:
            raise PortiaLocalValidationError(
                "disposition summary requires completed manual review"
            )
        counts = {name: 0 for name in _FINAL_DISPOSITIONS}
        manual_resolved = 0
        for item in self.items:
            if item.final_disposition not in _FINAL_DISPOSITIONS:
                raise PortiaLocalValidationError(
                    "final projection retains unresolved manual-review disposition"
                )
            counts[item.final_disposition] += 1
            if item.manual_resolution is not None:
                manual_resolved += 1
        return TeacherReferenceDispositionSummary(
            included=counts["included"],
            withheld=counts["withheld"],
            unavailable=counts["unavailable"],
            absent=counts["absent"],
            manual_review_resolved=manual_resolved,
        )

    @property
    def contributing_source_refs(self) -> tuple[TeacherReferenceSourceRef, ...]:
        """Return exact sources with at least one final included projection item."""

        if not self.is_final:
            raise PortiaLocalValidationError(
                "contributing sources require completed manual review"
            )
        included = {
            item.source_ref
            for item in self.items
            if item.final_disposition == "included"
        }
        return tuple(sorted(included, key=_source_key))


class TeacherReferenceProjectionService:
    """Apply closed policy to exact discovered sources without writes or rendering."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)

    def project(
        self,
        discovery: TeacherReferenceScopeDiscovery,
    ) -> TeacherReferenceProjectionDecision:
        if not isinstance(discovery, TeacherReferenceScopeDiscovery):
            raise TypeError("discovery must be a TeacherReferenceScopeDiscovery")

        items: list[TeacherReferenceProjectionItem] = []
        for observation in discovery.observations:
            stored = self._load_and_verify(observation)
            if observation.state == "unavailable":
                items.append(
                    self._source_item(
                        observation,
                        "unavailable",
                        observation.state_reason,
                    )
                )
                continue

            if (
                stored.record.contract == "communication"
                and stored.record.field("privacy_scope") in {"restricted", "unknown"}
            ):
                items.append(
                    self._source_item(
                        observation,
                        "withheld",
                        "communication_privacy_scope_withheld",
                    )
                )
                continue

            rule = teacher_reference_contract_rule(
                stored.record.contract,
                stored.record.contract_version,
            )
            data = stored.record.to_dict()
            for field_rule in rule.fields:
                name = field_rule.field_name
                if name not in data:
                    items.append(
                        self._field_item(
                            observation,
                            field_rule.disposition,
                            field_rule.representation,
                            name,
                            "absent",
                            "source_field_absent",
                        )
                    )
                    continue
                raw = data[name]
                if field_rule.disposition == "withheld":
                    items.append(
                        self._field_item(
                            observation,
                            field_rule.disposition,
                            field_rule.representation,
                            name,
                            "withheld",
                            "closed_policy_withheld",
                        )
                    )
                    continue
                if field_rule.disposition == "requires_manual_review":
                    items.append(
                        self._field_item(
                            observation,
                            field_rule.disposition,
                            field_rule.representation,
                            name,
                            "requires_manual_review",
                            "manual_review_required",
                            review_value=freeze_json(raw),
                            review_value_present=True,
                        )
                    )
                    continue

                projected = _represented_value(raw, field_rule.representation)
                if projected is None:
                    items.append(
                        self._field_item(
                            observation,
                            field_rule.disposition,
                            field_rule.representation,
                            name,
                            "withheld",
                            "bounded_representation_unavailable",
                        )
                    )
                    continue
                items.append(
                    self._field_item(
                        observation,
                        field_rule.disposition,
                        field_rule.representation,
                        name,
                        "included",
                        "closed_policy_included",
                        value=projected,
                        value_present=True,
                    )
                )

        ordered = tuple(sorted(items, key=_item_key))
        pending = any(
            item.final_disposition == "requires_manual_review" for item in ordered
        )
        review = TeacherReferenceManualReview(
            "pending" if pending else "not_required"
        )
        return TeacherReferenceProjectionDecision(discovery, ordered, review)

    def resolve_manual_review(
        self,
        decision: TeacherReferenceProjectionDecision,
        choices: Sequence[TeacherReferenceManualReviewChoice],
        *,
        reviewed_at: str,
        reviewed_by: Mapping[str, object],
    ) -> TeacherReferenceProjectionDecision:
        """Resolve every pending manual item with include-exact or omit only."""

        if not isinstance(decision, TeacherReferenceProjectionDecision):
            raise TypeError("decision must be a TeacherReferenceProjectionDecision")
        if decision.manual_review.status != "pending":
            raise PortiaLocalValidationError(
                "manual review resolution requires a pending projection decision"
            )
        for observation in decision.discovery.observations:
            self._load_and_verify(observation)
        reviewer = AttributionAgent.from_dict(reviewed_by)
        if reviewer.type != "local_operator":
            raise PortiaLocalValidationError(
                "manual review resolution requires a local_operator reviewer"
            )
        ExplicitOffsetTimestamp(reviewed_at)

        unresolved = {
            (item.source_ref, item.field_name): item
            for item in decision.unresolved_manual_items
            if item.field_name is not None
        }
        normalized: dict[
            tuple[TeacherReferenceSourceRef, str],
            TeacherReferenceManualReviewChoice,
        ] = {}
        for choice in choices:
            if not isinstance(choice, TeacherReferenceManualReviewChoice):
                raise TypeError(
                    "manual review choices must be "
                    "TeacherReferenceManualReviewChoice values"
                )
            if choice.key in normalized:
                raise PortiaLocalValidationError(
                    "manual review cannot repeat one source/field choice"
                )
            normalized[choice.key] = choice
        if frozenset(normalized) != frozenset(unresolved):
            missing = sorted(
                f"{_source_key(source)}:{field_name}"
                for source, field_name in set(unresolved) - set(normalized)
            )
            extra = sorted(
                f"{_source_key(source)}:{field_name}"
                for source, field_name in set(normalized) - set(unresolved)
            )
            raise PortiaLocalValidationError(
                "manual review must resolve exactly every pending item; "
                f"missing={missing}, extra={extra}"
            )

        resolved: list[TeacherReferenceProjectionItem] = []
        for item in decision.items:
            if item.final_disposition != "requires_manual_review":
                resolved.append(item)
                continue
            assert item.field_name is not None
            choice = normalized[(item.source_ref, item.field_name)]
            if choice.resolution == "include_exact":
                assert item.review_value_present
                resolved.append(
                    replace(
                        item,
                        final_disposition="included",
                        manual_resolution="include_exact",
                        reason_code="manual_review_include_exact",
                        value=item.review_value,
                        value_present=True,
                    )
                )
            else:
                resolved.append(
                    replace(
                        item,
                        final_disposition="withheld",
                        manual_resolution="omit",
                        reason_code="manual_review_omit",
                    )
                )

        ordered = tuple(sorted(resolved, key=_item_key))
        digest = teacher_reference_projection_digest(decision.discovery, ordered)
        review = TeacherReferenceManualReview(
            status="resolved",
            reviewed_projection_digest=digest,
            reviewed_at=reviewed_at,
            reviewed_by=reviewer,
        )
        return TeacherReferenceProjectionDecision(
            decision.discovery,
            ordered,
            review,
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
                "canonical source changed after teacher-reference discovery"
            )
        if stored.record.contract != observation.record_kind:
            raise PortiaCorruptionError(
                "teacher-reference observation contract disagrees with canonical source"
            )
        if stored.record.contract_version != observation.contract_version:
            raise PortiaCorruptionError(
                "teacher-reference observation version disagrees with canonical source"
            )
        return stored

    @staticmethod
    def _source_item(
        observation: TeacherReferenceSourceObservation,
        disposition: Literal["withheld", "unavailable"],
        reason_code: str,
    ) -> TeacherReferenceProjectionItem:
        return TeacherReferenceProjectionItem(
            source_ref=observation.source_ref,
            source_role=observation.source_role,
            source_fingerprint=observation.fingerprint,
            focal_applicability=observation.focal_applicability,
            native_scope=observation.native_scope,
            focal_relation=observation.focal_relation,
            context_target_ref=observation.context_target_ref,
            final_disposition=disposition,
            reason_code=reason_code,
        )

    @staticmethod
    def _field_item(
        observation: TeacherReferenceSourceObservation,
        policy_disposition: TeacherReferenceFieldDisposition,
        representation: TeacherReferenceFieldRepresentation,
        field_name: str,
        final_disposition: TeacherReferenceProjectionDisposition,
        reason_code: str,
        *,
        value: FrozenJsonValue | None = None,
        review_value: FrozenJsonValue | None = None,
        value_present: bool = False,
        review_value_present: bool = False,
    ) -> TeacherReferenceProjectionItem:
        return TeacherReferenceProjectionItem(
            source_ref=observation.source_ref,
            source_role=observation.source_role,
            source_fingerprint=observation.fingerprint,
            focal_applicability=observation.focal_applicability,
            native_scope=observation.native_scope,
            focal_relation=observation.focal_relation,
            context_target_ref=observation.context_target_ref,
            field_name=field_name,
            policy_disposition=policy_disposition,
            representation=representation,
            final_disposition=final_disposition,
            reason_code=reason_code,
            value=value,
            review_value=review_value,
            value_present=value_present,
            review_value_present=review_value_present,
        )
