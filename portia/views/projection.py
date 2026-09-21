"""Closed privacy projection for the Issue #48 current student view."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from portia.models import PortiaRecord
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage import PortiaCorruptionError, PortiaRepository, StoredRecord
from portia.views.currentness import (
    CurrentnessDecision,
    CurrentnessResolver,
    StudentViewCurrentnessResolver,
    TimelineSourceRef,
)
from portia.views.discovery import (
    DiscoveredStudentWork,
    StudentWorkDiscoveryResult,
)
from portia.views.policy import (
    PROJECTION_DISPOSITIONS,
    STUDENT_VIEW_POLICY,
    StudentViewPolicyIdentity,
    known_contract_versions,
    projection_rule,
    projection_rules,
)

ProjectionDisposition = Literal[
    "included",
    "absent",
    "withheld",
    "unavailable",
    "requires_manual_review",
]
FocalApplicability = Literal[
    "whole_work",
    "direct",
    "among_multiple",
    "not_applicable",
]
NativeScope = Literal[
    "work",
    "single_participant",
    "multi_participant",
    "multi_person",
    "record",
]
ProjectedScalar: TypeAlias = str | int | float | bool


@dataclass(frozen=True, slots=True)
class ProjectedField:
    """One policy-allowed field decision; never a raw nested source object."""

    name: str
    disposition: ProjectionDisposition
    value: ProjectedScalar | None = None

    def __post_init__(self) -> None:
        validate_external_id(self.name, "projected_field_name")
        if self.disposition not in PROJECTION_DISPOSITIONS:
            raise PortiaLocalValidationError(
                f"unsupported projection disposition: {self.disposition!r}"
            )
        if self.disposition == "included":
            if self.value is None or not isinstance(
                self.value, (str, int, float, bool)
            ):
                raise PortiaLocalValidationError(
                    "included projected field requires one scalar value"
                )
        elif self.value is not None:
            raise PortiaLocalValidationError(
                "non-included projected field cannot carry a source value"
            )


@dataclass(frozen=True, slots=True)
class ProjectedStudentViewItem:
    """Privacy-minimized representation traceable to one exact source."""

    source_ref: TimelineSourceRef
    disposition: ProjectionDisposition
    category: str
    semantic_type: str
    status: str | None
    native_scope: NativeScope
    focal_applicability: FocalApplicability
    fields: tuple[ProjectedField, ...] = ()
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if self.disposition not in PROJECTION_DISPOSITIONS:
            raise PortiaLocalValidationError(
                f"unsupported projection disposition: {self.disposition!r}"
            )
        validate_external_id(self.category, "projection_category")
        validate_external_id(self.semantic_type, "projection_semantic_type")
        if self.focal_applicability == "not_applicable":
            raise PortiaLocalValidationError(
                "assembled projected item cannot be non-applicable"
            )
        if self.disposition in {"absent", "withheld", "unavailable"} and self.fields:
            raise PortiaLocalValidationError(
                "absent/withheld/unavailable item cannot expose projected fields"
            )
        names = tuple(field.name for field in self.fields)
        if len(set(names)) != len(names):
            raise PortiaLocalValidationError(
                "projected item cannot repeat a projected field"
            )


@dataclass(frozen=True, slots=True)
class ProjectionDecision:
    """Internal exact-source decision; ``absent`` never enters assembled output."""

    source_ref: TimelineSourceRef
    disposition: ProjectionDisposition
    reason_code: str
    item: ProjectedStudentViewItem | None = None

    def __post_init__(self) -> None:
        if self.disposition not in PROJECTION_DISPOSITIONS:
            raise PortiaLocalValidationError(
                f"unsupported projection disposition: {self.disposition!r}"
            )
        if self.disposition == "absent":
            if self.item is not None:
                raise PortiaLocalValidationError(
                    "absent projection decision cannot expose an item"
                )
        elif self.item is None:
            raise PortiaLocalValidationError(
                "non-absent projection decision requires a bounded item"
            )
        if self.item is not None and self.item.disposition != self.disposition:
            raise PortiaLocalValidationError(
                "projection decision and item dispositions must agree"
            )


@dataclass(frozen=True, slots=True)
class StudentPrivacyProjectionResult:
    """Assembled current-view projection with no absent-source side channel."""

    discovery: StudentWorkDiscoveryResult
    policy: StudentViewPolicyIdentity
    items: tuple[ProjectedStudentViewItem, ...]

    def __post_init__(self) -> None:
        if self.discovery.query.mode != "current":
            raise PortiaLocalValidationError(
                "Slice 3 privacy projection supports current mode only"
            )
        if self.policy != STUDENT_VIEW_POLICY:
            raise PortiaLocalValidationError(
                "student privacy result must carry the exact current policy identity"
            )
        if any(item.disposition == "absent" for item in self.items):
            raise PortiaLocalValidationError(
                "assembled student projection cannot expose absent sources"
            )
        refs = tuple(item.source_ref for item in self.items)
        if len(set(refs)) != len(refs):
            raise PortiaLocalValidationError(
                "assembled student projection cannot repeat an exact source"
            )


@dataclass(frozen=True, slots=True)
class _Applicability:
    focal: FocalApplicability
    native_scope: NativeScope
    focal_relation: str | None = None


def _child_reference(work: ExactPortiaWorkRef, stored: StoredRecord) -> ExactPortiaWorkRecordRef:
    identifier = stored.record.logical_id
    if not isinstance(identifier, str):
        raise PortiaCorruptionError("canonical child lacks exact logical identity")
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=stored.record.contract,
            record_id=identifier,
            contract_version=stored.record.contract_version,
        ),
    )


def _source_key(source: TimelineSourceRef) -> tuple[str, ...]:
    if isinstance(source, ExactPortiaWorkRef):
        return (
            source.class_id,
            source.work_kind,
            source.work_id,
            source.contract_version,
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
    )


def _participant_keys(work: DiscoveredStudentWork) -> frozenset[tuple[str, str, str]]:
    return frozenset(
        (
            match.participant_ref.record_ref.record_kind,
            match.participant_ref.record_ref.record_id,
            match.participant_ref.record_ref.contract_version,
        )
        for match in work.focal_matches
    )


def _focal_students(work: DiscoveredStudentWork) -> frozenset[RosterStudentRef]:
    return frozenset(match.student_ref for match in work.focal_matches)


def _local_record_key(value: object) -> tuple[str, str, str]:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("canonical participant target reference is malformed")
    kind = value.get("record_kind")
    identifier = value.get("record_id")
    version = value.get("contract_version")
    if (
        not isinstance(kind, str)
        or not isinstance(identifier, str)
        or not isinstance(version, str)
    ):
        raise PortiaCorruptionError(
            "current-view participant target must carry exact kind/id/version"
        )
    return kind, identifier, version


def _target_applicability(
    value: object,
    work: DiscoveredStudentWork,
) -> _Applicability:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("canonical target is malformed")
    kind = value.get("kind")
    if kind in {"event", "support_process"}:
        return _Applicability("whole_work", "work", "work_context")
    focal = _participant_keys(work)
    if kind in {"event_participant", "support_process_participant"}:
        key = _local_record_key(value.get("record_ref"))
        return _Applicability(
            "direct" if key in focal else "not_applicable",
            "single_participant",
            "target" if key in focal else None,
        )
    if kind in {"event_participants", "support_process_participants"}:
        targets = value.get("targets")
        if not isinstance(targets, Sequence) or isinstance(
            targets, (str, bytes, bytearray)
        ):
            raise PortiaCorruptionError("canonical multi-participant target is malformed")
        matches = False
        for target in targets:
            if not isinstance(target, Mapping):
                raise PortiaCorruptionError(
                    "canonical multi-participant target entry is malformed"
                )
            if _local_record_key(target.get("record_ref")) in focal:
                matches = True
        return _Applicability(
            "among_multiple" if matches else "not_applicable",
            "multi_participant",
            "target" if matches else None,
        )
    raise PortiaCorruptionError(f"unsupported canonical target kind: {kind!r}")


def _attribution_matches(value: object, focal: frozenset[RosterStudentRef]) -> bool:
    if not isinstance(value, Mapping) or value.get("kind") != "roster_student":
        return False
    raw = value.get("roster_student_ref")
    try:
        reference = RosterStudentRef.from_dict(raw)
    except Exception as exc:
        raise PortiaCorruptionError(
            "canonical represented-human roster identity is malformed"
        ) from exc
    return reference in focal


def _observer_matches(value: object, focal: frozenset[RosterStudentRef]) -> bool:
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError("canonical Observation observer is malformed")
    if value.get("kind") != "human":
        return False
    return _attribution_matches(value.get("human_attribution"), focal)


class StudentPrivacyProjectionService:
    """Project discovered work through currentness then positive privacy policy."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        currentness: CurrentnessResolver | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.currentness = currentness or StudentViewCurrentnessResolver(
            self.workspace_root,
            repository=self.repository,
        )

    def project(
        self,
        discovery: StudentWorkDiscoveryResult,
    ) -> StudentPrivacyProjectionResult:
        if discovery.query.mode != "current":
            raise PortiaLocalValidationError(
                "Slice 3 privacy/currentness projection supports current mode only"
            )
        assembled: list[ProjectedStudentViewItem] = []
        for work in discovery.works:
            root_stored = self.repository.load_work(work.work_ref)
            root_decision = self.project_source(work, work.work_ref, root_stored)
            if root_decision.item is not None:
                assembled.append(root_decision.item)

            current_kinds = sorted(
                {
                    rule.record_kind
                    for rule in projection_rules()
                    if rule.surface == "domain_current"
                }
            )
            for kind in current_kinds:
                versions = known_contract_versions(kind)
                for stored in self.repository.list_work_records_mixed_versions(
                    work.work_ref,
                    kind,
                    supported_versions=versions,
                ):
                    try:
                        projection_rule(stored.record.contract, stored.record.contract_version)
                    except PortiaLocalValidationError:
                        # Known legacy/history-only representation: deliberate history
                        # projection belongs to Slice 5, not current mode.
                        continue
                    source = _child_reference(work.work_ref, stored)
                    decision = self.project_source(work, source, stored)
                    if decision.item is not None:
                        assembled.append(decision.item)

        items = tuple(sorted(assembled, key=lambda item: _source_key(item.source_ref)))
        return StudentPrivacyProjectionResult(
            discovery=discovery,
            policy=STUDENT_VIEW_POLICY,
            items=items,
        )

    def project_source(
        self,
        work: DiscoveredStudentWork,
        source_ref: TimelineSourceRef,
        stored: StoredRecord | None = None,
    ) -> ProjectionDecision:
        stored = stored or self._load_source(source_ref)
        applicability = self._applicability(work, source_ref, stored.record)
        if applicability.focal == "not_applicable":
            return ProjectionDecision(
                source_ref,
                "absent",
                "not_focally_applicable",
            )

        currentness = self.currentness.evaluate(source_ref)
        if currentness.state == "noncurrent":
            return ProjectionDecision(
                source_ref,
                "absent",
                currentness.reason_code,
            )
        rule = projection_rule(stored.record.contract, stored.record.contract_version)
        if currentness.state == "unavailable":
            item = ProjectedStudentViewItem(
                source_ref=source_ref,
                disposition="unavailable",
                category=rule.category,
                semantic_type=stored.record.contract,
                status=stored.record.status,
                native_scope=applicability.native_scope,
                focal_applicability=applicability.focal,
                reason_code=currentness.reason_code,
            )
            return ProjectionDecision(
                source_ref,
                "unavailable",
                currentness.reason_code,
                item,
            )
        return self._privacy_project(
            source_ref,
            stored.record,
            applicability,
            currentness,
        )

    def _load_source(self, source_ref: TimelineSourceRef) -> StoredRecord:
        if isinstance(source_ref, ExactPortiaWorkRef):
            return self.repository.load_work(source_ref)
        return self.repository.load_work_record(
            source_ref.work_ref,
            source_ref.record_ref.record_kind,
            source_ref.record_ref.contract_version,
            source_ref.record_ref.record_id,
        )

    def _applicability(
        self,
        work: DiscoveredStudentWork,
        source_ref: TimelineSourceRef,
        record: PortiaRecord,
    ) -> _Applicability:
        if source_ref == work.work_ref:
            return _Applicability("whole_work", "work", "work_context")
        if not isinstance(source_ref, ExactPortiaWorkRecordRef):
            raise PortiaCorruptionError("child projection lacks exact record reference")
        kind = record.contract
        focal_keys = _participant_keys(work)
        if kind in {"event_participant", "support_process_participant"}:
            key = (
                source_ref.record_ref.record_kind,
                source_ref.record_ref.record_id,
                source_ref.record_ref.contract_version,
            )
            return _Applicability(
                "direct" if key in focal_keys else "not_applicable",
                "single_participant",
                "participant" if key in focal_keys else None,
            )
        if kind == "event_participant_role":
            return _target_applicability(record.field("target"), work)
        if kind == "work_relationship":
            allowed = {
                relation.relationship_ref for relation in work.related_context
            }
            return _Applicability(
                "whole_work" if source_ref in allowed else "not_applicable",
                "work",
                "bounded_relationship" if source_ref in allowed else None,
            )
        if kind == "communication":
            return self._communication_applicability(record, work)
        if kind == "account":
            target = _target_applicability(record.field("target"), work)
            source_match = _attribution_matches(
                record.field("source"), _focal_students(work)
            )
            if target.focal != "not_applicable":
                if source_match:
                    return _Applicability(
                        target.focal, target.native_scope, "source_and_target"
                    )
                return target
            if source_match:
                return _Applicability("direct", target.native_scope, "source")
            return _Applicability("not_applicable", target.native_scope)
        if kind == "observation":
            target = _target_applicability(record.field("target"), work)
            observer_match = _observer_matches(
                record.field("observer"), _focal_students(work)
            )
            if target.focal != "not_applicable":
                if observer_match:
                    return _Applicability(
                        target.focal, target.native_scope, "observer_and_target"
                    )
                return target
            if observer_match:
                return _Applicability("direct", target.native_scope, "observer")
            return _Applicability("not_applicable", target.native_scope)
        if kind == "implementation":
            return _target_applicability(record.field("actual_target"), work)
        if kind == "fidelity":
            return self._fidelity_applicability(record, work)
        target_value = record.field("target")
        if target_value is not None:
            return _target_applicability(target_value, work)
        # Every current-view family must have an explicit applicability branch.
        raise PortiaCorruptionError(
            f"student-view applicability adapter missing for {kind!r}"
        )

    def _fidelity_applicability(
        self,
        record: PortiaRecord,
        work: DiscoveredStudentWork,
    ) -> _Applicability:
        raw = record.field("plan_ref")
        if not isinstance(raw, Mapping):
            raise PortiaCorruptionError("canonical Fidelity plan_ref is malformed")
        try:
            plan_ref = ExactLocalRecordRef.from_dict(raw)
        except Exception as exc:
            raise PortiaCorruptionError(
                "canonical Fidelity plan_ref is not exact"
            ) from exc
        plan = self.repository.load_work_record(
            work.work_ref,
            plan_ref.record_kind,
            plan_ref.contract_version,
            plan_ref.record_id,
        )
        return _target_applicability(plan.record.field("target"), work)

    def _communication_applicability(
        self,
        record: PortiaRecord,
        work: DiscoveredStudentWork,
    ) -> _Applicability:
        focal = _focal_students(work)
        sender_match = _attribution_matches(record.field("sender"), focal)
        raw_recipients = record.field("recipients")
        if not isinstance(raw_recipients, Sequence) or isinstance(
            raw_recipients, (str, bytes, bytearray)
        ):
            raise PortiaCorruptionError("canonical Communication recipients malformed")
        recipient_match = False
        for recipient in raw_recipients:
            if not isinstance(recipient, Mapping):
                raise PortiaCorruptionError(
                    "canonical Communication recipient is malformed"
                )
            if _attribution_matches(recipient.get("person"), focal):
                recipient_match = True
        if not sender_match and not recipient_match:
            return _Applicability("not_applicable", "multi_person")
        relation = (
            "sender_and_recipient"
            if sender_match and recipient_match
            else "sender"
            if sender_match
            else "recipient"
        )
        return _Applicability("direct", "multi_person", relation)

    def _privacy_project(
        self,
        source_ref: TimelineSourceRef,
        record: PortiaRecord,
        applicability: _Applicability,
        currentness: CurrentnessDecision,
    ) -> ProjectionDecision:
        del currentness
        rule = projection_rule(record.contract, record.contract_version)
        if record.contract == "communication":
            privacy_scope = record.field("privacy_scope")
            if privacy_scope in {"restricted", "unknown"}:
                item = ProjectedStudentViewItem(
                    source_ref=source_ref,
                    disposition="withheld",
                    category=rule.category,
                    semantic_type=record.contract,
                    status=record.status,
                    native_scope=applicability.native_scope,
                    focal_applicability=applicability.focal,
                    reason_code="communication_privacy_scope_withheld",
                )
                return ProjectionDecision(
                    source_ref,
                    "withheld",
                    "communication_privacy_scope_withheld",
                    item,
                )

        fields: list[ProjectedField] = []
        manual = False
        for name in rule.safe_scalar_fields:
            value = record.field(name)
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                fields.append(ProjectedField(name, "included", value))
            else:
                fields.append(ProjectedField(name, "requires_manual_review"))
                manual = True

        special_fields, special_manual = self._special_fields(
            record, applicability, work_kind=source_ref.work_ref.work_kind
            if isinstance(source_ref, ExactPortiaWorkRecordRef)
            else source_ref.work_kind,
        )
        fields.extend(special_fields)
        manual = manual or special_manual

        for name in rule.manual_review_fields:
            if name == "content" and record.contract == "observation":
                content = record.field("content")
                if isinstance(content, Mapping):
                    if content.get("measurements") is not None:
                        fields.append(
                            ProjectedField(
                                "evidence_shape", "included", "structured_measurement"
                            )
                        )
                    if content.get("narrative") is not None:
                        fields.append(
                            ProjectedField("content", "requires_manual_review")
                        )
                        manual = True
                    continue
            value = record.field(name)
            if value is not None:
                fields.append(ProjectedField(name, "requires_manual_review"))
                manual = True
        for name in rule.withheld_fields:
            if record.field(name) is not None:
                fields.append(ProjectedField(name, "withheld"))

        # Deduplicate special/registry field declarations deterministically.
        deduped: dict[str, ProjectedField] = {}
        for field in fields:
            existing = deduped.get(field.name)
            if existing is None:
                deduped[field.name] = field
                continue
            precedence = {
                "included": 0,
                "absent": 1,
                "withheld": 2,
                "unavailable": 3,
                "requires_manual_review": 4,
            }
            if precedence[field.disposition] > precedence[existing.disposition]:
                deduped[field.name] = field
        projected_fields = tuple(deduped[name] for name in sorted(deduped))
        disposition: ProjectionDisposition = (
            "requires_manual_review" if manual else "included"
        )
        item = ProjectedStudentViewItem(
            source_ref=source_ref,
            disposition=disposition,
            category=rule.category,
            semantic_type=record.contract,
            status=record.status,
            native_scope=applicability.native_scope,
            focal_applicability=applicability.focal,
            fields=projected_fields,
            reason_code=(
                "privacy_manual_review_required" if manual else "privacy_safe_projection"
            ),
        )
        return ProjectionDecision(
            source_ref,
            disposition,
            item.reason_code or "privacy_safe_projection",
            item,
        )

    def _special_fields(
        self,
        record: PortiaRecord,
        applicability: _Applicability,
        *,
        work_kind: str,
    ) -> tuple[list[ProjectedField], bool]:
        del work_kind
        fields: list[ProjectedField] = []
        manual = False
        if applicability.focal_relation is not None:
            fields.append(
                ProjectedField(
                    "focal_relation", "included", applicability.focal_relation
                )
            )
        if record.contract == "support_process_participant":
            raw = record.field("contexts")
            if not isinstance(raw, Sequence) or isinstance(
                raw, (str, bytes, bytearray)
            ):
                raise PortiaCorruptionError(
                    "canonical Support Process Participant contexts malformed"
                )
            kinds: list[str] = []
            for value in raw:
                if not isinstance(value, Mapping) or not isinstance(
                    value.get("kind"), str
                ):
                    raise PortiaCorruptionError(
                        "canonical Support Process Participant context malformed"
                    )
                context_kind = value.get("kind")
                assert isinstance(context_kind, str)
                kinds.append(context_kind)
            fields.append(
                ProjectedField("participant_contexts", "included", "|".join(kinds))
            )
        elif record.contract == "account":
            # ``focal_relation == source`` was established through exact
            # class-qualified roster identity before privacy projection.
            relation = (
                "focal_student"
                if applicability.focal_relation in {"source", "source_and_target"}
                else "third_party_or_other"
            )
            fields.append(ProjectedField("source_relation", "included", relation))
        elif record.contract == "observation":
            relation = (
                "focal_student"
                if applicability.focal_relation in {"observer", "observer_and_target"}
                else "third_party_or_instrument"
            )
            fields.append(ProjectedField("observer_relation", "included", relation))
        elif record.contract == "communication":
            for source_name, projected_name in (
                ("method", "method_kind"),
                ("purpose", "purpose_kind"),
            ):
                value = record.field(source_name)
                kind = value.get("kind") if isinstance(value, Mapping) else None
                if isinstance(kind, str):
                    fields.append(
                        ProjectedField(projected_name, "included", kind)
                    )
                else:
                    fields.append(
                        ProjectedField(projected_name, "requires_manual_review")
                    )
                    manual = True
        return fields, manual
