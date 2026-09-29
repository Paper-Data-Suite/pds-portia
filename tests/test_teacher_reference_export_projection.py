from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from portia.exports import (
    PROJECTION_DECISION_ALGORITHM,
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
    teacher_reference_projection_descriptor,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.models.json_values import thaw_json
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaConflictError, PortiaRepository, StoredRecord
from portia.views import CurrentnessDecision
from portia.workflows import AmendmentResolution, WorkflowPrerequisiteError
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    event_wire,
    participant_record,
)

LATER = "2026-08-26T12:05:00-04:00"
REVIEWED = "2026-09-28T20:30:00-04:00"
REVIEWER = {"type": "local_operator", "display_label": "Synthetic Teacher"}


def child(
    work: ExactPortiaWorkRef,
    kind: str,
    identifier: str,
    version: str,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=kind,
            record_id=identifier,
            contract_version=version,
        ),
    )


class _Currentness:
    def __init__(self, unavailable: frozenset[str] = frozenset()) -> None:
        self.unavailable = unavailable

    def evaluate(
        self,
        source_ref: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> CurrentnessDecision:
        if isinstance(source_ref, ExactPortiaWorkRef):
            return CurrentnessDecision(source_ref, "current", "synthetic_current")
        if source_ref.record_ref.record_id in self.unavailable:
            return CurrentnessDecision(
                source_ref,
                "unavailable",
                "synthetic_unavailable",
            )
        return CurrentnessDecision(source_ref, "current", "synthetic_current")


class _Disagreements:
    def __init__(self, records: tuple[StoredRecord, ...]) -> None:
        self.records = records

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        assert all(item.record.work_id == work.work_id for item in self.records)
        return self.records

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        try:
            return next(
                item
                for item in self.records
                if item.record.logical_id == reference.record_ref.record_id
            )
        except StopIteration as exc:
            raise WorkflowPrerequisiteError("synthetic missing disagreement") from exc


class _Amendments:
    def __init__(
        self,
        repository: PortiaRepository,
        selected: dict[ExactPortiaWorkRef | ExactPortiaWorkRecordRef, StoredRecord],
    ) -> None:
        self.repository = repository
        self.selected = selected

    def require_reconciled(
        self,
        reference: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> AmendmentResolution:
        if isinstance(reference, ExactPortiaWorkRef):
            target = self.repository.load_work(reference)
        else:
            target = self.repository.load_work_record(
                reference.work_ref,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        selected = self.selected.get(reference)
        return AmendmentResolution(
            reference=reference,
            target=target,
            amendments=() if selected is None else (selected,),
            selected_amendment=selected,
            policies=(),
            reconciliation_error=None,
        )


def _seed_event(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), participant_record())
    return repository


def _account(account_id: str = "acct_alpha") -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "work_kind": "event",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "source": {"kind": "local_operator", "display_label": "Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Sensitive exact account wording.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _communication() -> PortiaRecord:
    return parse_portia_record(
        "communication",
        "1",
        {
            "schema_version": "1",
            "record_type": "communication",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "communication_id": "comm_private",
            "status": "active",
            "sender": {"kind": "local_operator", "display_label": "Teacher"},
            "recipients": [
                {
                    "person": {
                        "kind": "roster_student",
                        "roster_student_ref": {
                            "class_id": "class_a",
                            "student_id": "student_1",
                        },
                        "display_snapshot": {"display_name": "Focal Student"},
                    },
                    "participation": "participated",
                }
            ],
            "method": {"kind": "email"},
            "purpose": {"kind": "information_sharing"},
            "act_state": "completed",
            "privacy_scope": "restricted",
            "summary": "Sensitive restricted communication.",
            "started_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _disagreement() -> PortiaRecord:
    return parse_portia_record(
        "statement_of_disagreement",
        "1",
        {
            "schema_version": "1",
            "record_type": "statement_of_disagreement",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "disagreement_id": "sod_alpha",
            "status": "active",
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "source": {"kind": "local_operator", "display_label": "Teacher"},
            "positions": ["qualifies_record"],
            "statement": {
                "representation": "recorded_summary",
                "text": "Sensitive disagreement wording.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _amendment() -> PortiaRecord:
    return parse_portia_record(
        "amendment",
        "1",
        {
            "schema_version": "1",
            "record_type": "amendment",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "amendment_id": "amd_root",
            "target": {
                "kind": "work",
                "work_kind": "event",
                "contract_version": "2",
            },
            "previous_amendment": None,
            "target_updated_at_before": TIMESTAMP,
            "changes": [
                {
                    "path": "/summary",
                    "operation": "replace",
                    "before": {"present": True, "value": "before"},
                    "after": {"present": True, "value": "after"},
                }
            ],
            "reason": {"code": "spelling_corrected"},
            "creation_source": {"type": "digital_entry"},
            "created_at": LATER,
            "created_by": AGENT,
        },
    )


def _decision(
    tmp_path: Path,
    *,
    repository: PortiaRepository | None = None,
    currentness: _Currentness | None = None,
    disagreements: _Disagreements | None = None,
    amendments: _Amendments | None = None,
):
    repo = repository or _seed_event(tmp_path)
    discovery = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repo,
        currentness=currentness or _Currentness(),
        disagreements=disagreements,
        amendments=amendments,
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))
    return TeacherReferenceProjectionService(
        tmp_path,
        repository=repo,
    ).project(discovery)


def _item(decision: object, source: object, field_name: str | None):
    items = getattr(decision, "items")
    return next(
        item
        for item in items
        if item.source_ref == source and item.field_name == field_name
    )


def _resolve_all(
    service: TeacherReferenceProjectionService,
    decision: object,
    *,
    include: frozenset[tuple[object, str]] = frozenset(),
):
    choices = []
    for item in getattr(decision, "unresolved_manual_items"):
        assert item.field_name is not None
        key = (item.source_ref, item.field_name)
        choices.append(
            TeacherReferenceManualReviewChoice(
                item.source_ref,
                item.field_name,
                "include_exact" if key in include else "omit",
            )
        )
    return service.resolve_manual_review(
        decision,
        choices,
        reviewed_at=REVIEWED,
        reviewed_by=REVIEWER,
    )


def test_projection_uses_published_algorithm_and_closed_field_decisions(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)

    assert decision.projection_decision_algorithm == "portia_projection_decision_v1"
    assert PROJECTION_DECISION_ALGORITHM == "portia_projection_decision_v1"
    assert _item(decision, event_ref(), "status").final_disposition == "included"
    assert _item(decision, event_ref(), "summary").final_disposition == (
        "requires_manual_review"
    )
    assert _item(decision, event_ref(), "instructional_context").final_disposition == (
        "absent"
    )
    absent_manual = [
        item
        for item in decision.items
        if item.final_disposition == "absent"
        and item.policy_disposition == "requires_manual_review"
    ]
    assert absent_manual
    assert all(not item.review_value_present for item in absent_manual)
    assert decision.manual_review.status == "pending"


def test_embedded_participant_snapshot_excludes_stable_roster_identity(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    participant = child(event_ref(), "event_participant", "ep_alpha", "3")
    subject = _item(decision, participant, "subject")

    assert subject.final_disposition == "included"
    assert thaw_json(subject.value) == {"display_name": "Same Display"}
    assert "student_1" not in repr(subject)
    descriptor = json.dumps(
        teacher_reference_projection_descriptor(decision.discovery, decision.items),
        sort_keys=True,
    )
    assert "student_1" not in descriptor
    # Decision digest binds a value fingerprint rather than display text.
    assert "Same Display" not in descriptor


def test_participant_without_embedded_snapshot_is_withheld_not_name_enriched(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(
        event_ref(),
        participant_record(
            subject={
                "kind": "descriptive_person",
                "description_type": "visitor",
                "display_label": "Do Not Enrich Me",
            }
        ),
    )
    decision = _decision(tmp_path, repository=repository)
    participant = child(event_ref(), "event_participant", "ep_alpha", "3")
    subject = _item(decision, participant, "subject")

    assert subject.final_disposition == "withheld"
    assert subject.reason_code == "bounded_representation_unavailable"
    assert subject.value is None
    assert "Do Not Enrich Me" not in repr(subject)


def test_manual_review_retains_exact_source_without_exposing_raw_text(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    summary = _item(decision, event_ref(), "summary")

    assert summary.review_value is not None
    assert thaw_json(summary.review_value) == "Synthetic neutral classroom context."
    assert summary.value is None
    assert "Synthetic neutral classroom context." not in repr(summary)
    descriptor = json.dumps(
        teacher_reference_projection_descriptor(decision.discovery, decision.items),
        sort_keys=True,
    )
    assert "Synthetic neutral classroom context." not in descriptor


def test_projection_item_presence_flags_preserve_present_json_null(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    occurrence = _item(decision, event_ref(), "occurrence")

    pending_null = replace(
        occurrence,
        review_value=None,
        review_value_present=True,
    )
    assert pending_null.final_disposition == "requires_manual_review"
    assert pending_null.review_value_present
    assert pending_null.review_value is None

    included_null = replace(
        pending_null,
        final_disposition="included",
        manual_resolution="include_exact",
        reason_code="manual_review_include_exact",
        value=None,
        value_present=True,
    )
    assert included_null.final_disposition == "included"
    assert included_null.manual_resolution == "include_exact"
    assert included_null.value_present
    assert included_null.value is None
    assert included_null.projected_value_fingerprint is not None


def test_manual_include_preserves_exact_content_and_omit_creates_no_replacement_text(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    service = TeacherReferenceProjectionService(tmp_path)
    include_key = (event_ref(), "summary")
    resolved = _resolve_all(service, decision, include=frozenset({include_key}))

    summary = _item(resolved, event_ref(), "summary")
    occurrence = _item(resolved, event_ref(), "occurrence")
    assert summary.final_disposition == "included"
    assert summary.manual_resolution == "include_exact"
    assert thaw_json(summary.value) == "Synthetic neutral classroom context."
    assert occurrence.final_disposition == "withheld"
    assert occurrence.manual_resolution == "omit"
    assert occurrence.value is None
    assert set(TeacherReferenceManualReviewChoice.__dataclass_fields__) == {
        "source_ref",
        "field_name",
        "resolution",
    }


def test_manual_review_requires_exactly_one_choice_for_every_pending_item(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    service = TeacherReferenceProjectionService(tmp_path)
    unresolved = decision.unresolved_manual_items
    assert unresolved

    first = unresolved[0]
    assert first.field_name is not None
    one = TeacherReferenceManualReviewChoice(
        first.source_ref,
        first.field_name,
        "omit",
    )
    with pytest.raises(PortiaLocalValidationError, match="exactly every pending"):
        service.resolve_manual_review(
            decision,
            [one],
            reviewed_at=REVIEWED,
            reviewed_by=REVIEWER,
        )

    complete = [
        TeacherReferenceManualReviewChoice(item.source_ref, item.field_name, "omit")
        for item in unresolved
        if item.field_name is not None
    ]
    with pytest.raises(PortiaLocalValidationError, match="cannot repeat"):
        service.resolve_manual_review(
            decision,
            [*complete, complete[0]],
            reviewed_at=REVIEWED,
            reviewed_by=REVIEWER,
        )


def test_manual_review_requires_local_operator_and_explicit_offset_timestamp(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    service = TeacherReferenceProjectionService(tmp_path)
    choices = [
        TeacherReferenceManualReviewChoice(item.source_ref, item.field_name, "omit")
        for item in decision.unresolved_manual_items
        if item.field_name is not None
    ]

    with pytest.raises(PortiaLocalValidationError, match="local_operator"):
        service.resolve_manual_review(
            decision,
            choices,
            reviewed_at=REVIEWED,
            reviewed_by={"type": "system_process", "process_id": "test"},
        )
    with pytest.raises(PortiaLocalValidationError, match="RFC 3339"):
        service.resolve_manual_review(
            decision,
            choices,
            reviewed_at="2026-09-28T20:30:00",
            reviewed_by=REVIEWER,
        )


def test_resolved_review_binds_exact_projection_digest_and_export_shape(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    resolved = _resolve_all(TeacherReferenceProjectionService(tmp_path), decision)

    assert resolved.is_final
    assert resolved.manual_review.status == "resolved"
    assert resolved.manual_review.reviewed_projection_digest == (
        resolved.projection_decision_digest
    )
    assert resolved.manual_review.to_export_dict() == {
        "status": "resolved",
        "reviewed_projection_digest": resolved.projection_decision_digest,
        "reviewed_at": REVIEWED,
        "reviewed_by": REVIEWER,
    }


def test_pending_projection_cannot_produce_final_disposition_summary(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    with pytest.raises(PortiaLocalValidationError, match="completed manual review"):
        _ = decision.disposition_summary


def test_disposition_summary_keeps_included_withheld_unavailable_absent_distinct(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), _account("acct_unavailable"))
    decision = _decision(
        tmp_path,
        repository=repository,
        currentness=_Currentness(frozenset({"acct_unavailable"})),
    )
    resolved = _resolve_all(
        TeacherReferenceProjectionService(tmp_path, repository=repository),
        decision,
        include=frozenset({(event_ref(), "summary")}),
    )
    summary = resolved.disposition_summary

    assert summary.included > 0
    assert summary.withheld > 0
    assert summary.unavailable == 1
    assert summary.absent > 0
    assert summary.manual_review_resolved > 0
    assert summary.to_dict()["count_unit"] == "projection_item"


def test_projection_digest_is_deterministic_and_changes_with_manual_resolution(
    tmp_path: Path,
) -> None:
    decision = _decision(tmp_path)
    service = TeacherReferenceProjectionService(tmp_path)
    second = service.project(decision.discovery)
    assert decision.projection_decision_digest == second.projection_decision_digest

    omitted = _resolve_all(service, decision)
    included = _resolve_all(
        service,
        second,
        include=frozenset({(event_ref(), "summary")}),
    )
    assert omitted.projection_decision_digest != included.projection_decision_digest


def test_restricted_communication_is_source_level_withheld_without_field_leak(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), _communication())
    decision = _decision(tmp_path, repository=repository)
    source = child(event_ref(), "communication", "comm_private", "1")
    items = [item for item in decision.items if item.source_ref == source]

    assert len(items) == 1
    assert items[0].field_name is None
    assert items[0].final_disposition == "withheld"
    assert items[0].reason_code == "communication_privacy_scope_withheld"
    assert "Sensitive restricted communication" not in repr(items[0])


def test_account_source_stays_withheld_while_content_requires_manual_review(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), _account())
    decision = _decision(tmp_path, repository=repository)
    source = child(event_ref(), "account", "acct_alpha", "2")

    assert _item(decision, source, "source").final_disposition == "withheld"
    content = _item(decision, source, "content")
    assert content.final_disposition == "requires_manual_review"
    assert thaw_json(content.review_value)[0]["text"] == (
        "Sensitive exact account wording."
    )


def test_correction_and_disagreement_context_keep_distinct_roles_and_policy(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    disagreement_stored = repository.create_work_record(event_ref(), _disagreement())
    amendment_stored = repository.create_work_record(event_ref(), _amendment())
    decision = _decision(
        tmp_path,
        repository=repository,
        disagreements=_Disagreements((disagreement_stored,)),
        amendments=_Amendments(repository, {event_ref(): amendment_stored}),
    )

    disagreement_ref = child(
        event_ref(), "statement_of_disagreement", "sod_alpha", "1"
    )
    amendment_ref = child(event_ref(), "amendment", "amd_root", "1")
    positions = _item(decision, disagreement_ref, "positions")
    statement = _item(decision, disagreement_ref, "statement")
    changes = _item(decision, amendment_ref, "changes")

    assert positions.source_role == "disagreement_context"
    assert thaw_json(positions.value) == ["qualifies_record"]
    assert statement.final_disposition == "requires_manual_review"
    assert changes.source_role == "correction_context"
    assert changes.final_disposition == "requires_manual_review"
    assert _item(decision, amendment_ref, "target").final_disposition == "withheld"


def test_projection_rejects_source_changed_after_exact_discovery(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    discovery = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))
    prior = repository.load_work(event_ref())
    changed = event_wire(updated_at=LATER)
    changed["summary"] = "Changed after discovery."
    repository.replace_work(
        event_ref(),
        parse_portia_record("event", "2", changed),
        expected=prior.fingerprint,
    )

    with pytest.raises(PortiaConflictError, match="changed after"):
        TeacherReferenceProjectionService(
            tmp_path,
            repository=repository,
        ).project(discovery)


def test_fully_withheld_or_unavailable_source_is_not_a_contributing_source(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(event_ref(), _communication())
    repository.create_work_record(event_ref(), _account("acct_unavailable"))
    decision = _decision(
        tmp_path,
        repository=repository,
        currentness=_Currentness(frozenset({"acct_unavailable"})),
    )
    resolved = _resolve_all(
        TeacherReferenceProjectionService(tmp_path, repository=repository),
        decision,
    )

    assert event_ref() in resolved.contributing_source_refs
    assert child(event_ref(), "communication", "comm_private", "1") not in (
        resolved.contributing_source_refs
    )
    assert child(event_ref(), "account", "acct_unavailable", "2") not in (
        resolved.contributing_source_refs
    )


def test_projection_and_manual_resolution_are_zero_write(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path)
    discovery = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    service = TeacherReferenceProjectionService(tmp_path, repository=repository)
    decision = service.project(discovery)
    _resolve_all(service, decision)

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after


def test_source_change_before_manual_resolution_invalidates_review(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    decision = _decision(tmp_path, repository=repository)
    prior = repository.load_work(event_ref())
    changed = event_wire(updated_at=LATER)
    changed["summary"] = "Changed before manual review resolution."
    repository.replace_work(
        event_ref(),
        parse_portia_record("event", "2", changed),
        expected=prior.fingerprint,
    )
    choices = [
        TeacherReferenceManualReviewChoice(item.source_ref, item.field_name, "omit")
        for item in decision.unresolved_manual_items
        if item.field_name is not None
    ]

    with pytest.raises(PortiaConflictError, match="changed after"):
        TeacherReferenceProjectionService(
            tmp_path,
            repository=repository,
        ).resolve_manual_review(
            decision,
            choices,
            reviewed_at=REVIEWED,
            reviewed_by=REVIEWER,
        )
