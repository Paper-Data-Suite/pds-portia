from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage import PortiaQuarantinedError, PortiaRepository
from portia.views import (
    STUDENT_VIEW_POLICY,
    CurrentnessDecision,
    DiscoveredStudentWork,
    FocalParticipantMatch,
    ProjectedField,
    ProjectionDecision,
    StudentPrivacyProjectionService,
    StudentTimelineQuery,
    StudentViewCurrentnessResolver,
    StudentViewScope,
    StudentWorkDiscoveryResult,
    projection_rule,
    student_view_policy_digest,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
)


class _AlwaysCurrent:
    def evaluate(self, source_ref: object) -> CurrentnessDecision:
        return CurrentnessDecision(source_ref, "current", "synthetic_current")  # type: ignore[arg-type]


class _AlwaysUnavailable:
    def evaluate(self, source_ref: object) -> CurrentnessDecision:
        return CurrentnessDecision(source_ref, "unavailable", "current_use_blocked")  # type: ignore[arg-type]


class _BlockingQuarantine:
    def require_allowed(self, _target: object, effect: str) -> None:
        if effect == "block_current_use":
            raise PortiaQuarantinedError("synthetic current-use block")


def _discovery(work: ExactPortiaWorkRef | None = None) -> StudentWorkDiscoveryResult:
    selected = work or event_ref()
    student = RosterStudentRef(class_id="class_a", student_id="student_1")
    match = FocalParticipantMatch(
        student_ref=student,
        participant_ref=ExactPortiaWorkRecordRef(
            work_ref=selected,
            record_ref=ExactLocalRecordRef(
                record_kind="event_participant",
                record_id="ep_alpha",
                contract_version="3",
            ),
        ),
    )
    query = StudentTimelineQuery(
        StudentViewScope(
            focal_students=(student,),
            allowed_works=(selected,),
        ),
        exact_works=(selected,),
    )
    return StudentWorkDiscoveryResult(
        query=query,
        resolved_students=(student,),
        works=(DiscoveredStudentWork(selected, (match,)),),
    )


def _seed_event(tmp_path: Path, *, status: str = "active") -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record(status=status))
    repository.create_work_record(event_ref(), participant_record())
    return repository


def test_projection_policy_is_closed_and_digest_includes_field_policy() -> None:
    assert projection_rule("communication", "1").adapter == "communication"
    assert "recipients" in projection_rule("communication", "1").withheld_fields
    assert "content" in projection_rule("account", "2").manual_review_fields
    assert STUDENT_VIEW_POLICY.policy_digest == student_view_policy_digest()
    with pytest.raises(Exception, match="unsupported ordinary student-view projection"):
        projection_rule("event", "1")


def test_projected_field_preserves_five_disposition_contract() -> None:
    assert ProjectedField("status", "included", "active").value == "active"
    for disposition in ("absent", "withheld", "unavailable", "requires_manual_review"):
        assert ProjectedField("detail", disposition).disposition == disposition
    with pytest.raises(Exception, match="cannot carry"):
        ProjectedField("detail", "withheld", "secret")


def test_multi_participant_event_omits_unrelated_participant_source_refs(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other_a",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    repository.create_work_record(
        event_ref(),
        participant_record(
            participant_id="ep_other_b",
            subject={"kind": "descriptive_person", "description_type": "visitor", "display_label": "Other"},
        ),
    )
    result = StudentPrivacyProjectionService(
        tmp_path,
        repository=repository,
        currentness=_AlwaysCurrent(),
    ).project(_discovery())

    child_ids = {
        item.source_ref.record_ref.record_id
        for item in result.items
        if isinstance(item.source_ref, ExactPortiaWorkRecordRef)
    }
    assert "ep_alpha" in child_ids
    assert "ep_other_a" not in child_ids
    assert "ep_other_b" not in child_ids
    assert all(field.name != "participant_count" for item in result.items for field in item.fields)


def test_third_party_account_targeting_focal_student_requires_manual_review(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    account = parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": "acct_privacy",
            "status": "active",
            "target": {"kind": "event_participant", "record_ref": {"record_kind": "event_participant", "record_id": "ep_alpha", "contract_version": "3"}},
            "source": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [{"representation": "recorded_summary", "text": "Synthetic narrative that is not automatically privacy-safe."}],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), account)
    result = StudentPrivacyProjectionService(
        tmp_path,
        repository=repository,
        currentness=_AlwaysCurrent(),
    ).project(_discovery())
    item = next(item for item in result.items if item.semantic_type == "account")
    assert item.disposition == "requires_manual_review"
    fields = {field.name: field for field in item.fields}
    assert fields["source_relation"].value == "third_party_or_other"
    assert fields["content"].disposition == "requires_manual_review"
    assert all(
        "Synthetic narrative" not in str(field.value)
        for field in item.fields
    )


def test_structured_observation_can_project_without_narrative(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path)
    observation = parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "observation_id": "obs_privacy",
            "status": "active",
            "target": {"kind": "event_participant", "record_ref": {"record_kind": "event_participant", "record_id": "ep_alpha", "contract_version": "3"}},
            "observer": {"kind": "human", "human_attribution": {"kind": "local_operator", "display_label": "Synthetic Teacher"}},
            "method": "manual_count",
            "content": {"measurements": [{"measure_type": "count", "value": 3, "unit": "count"}]},
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), observation)
    result = StudentPrivacyProjectionService(
        tmp_path,
        repository=repository,
        currentness=_AlwaysCurrent(),
    ).project(_discovery())
    item = next(item for item in result.items if item.semantic_type == "observation")
    assert item.disposition == "included"
    fields = {field.name: field.value for field in item.fields if field.disposition == "included"}
    assert fields["method"] == "manual_count"
    assert fields["evidence_shape"] == "structured_measurement"


def test_restricted_communication_is_withheld_without_recipient_leak(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    communication = parse_portia_record(
        "communication",
        "1",
        {
            "schema_version": "1",
            "record_type": "communication",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "communication_id": "comm_privacy",
            "status": "active",
            "sender": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "recipients": [
                {"person": {"kind": "roster_student", "roster_student_ref": {"class_id": "class_a", "student_id": "student_1"}, "display_snapshot": {"display_name": "Focal Student"}}, "participation": "participated"},
                {"person": {"kind": "descriptive_person", "description_type": "family_member", "display_label": "Unrelated Recipient"}, "participation": "not_established"},
            ],
            "method": {"kind": "email"},
            "purpose": {"kind": "information_sharing"},
            "act_state": "completed",
            "privacy_scope": "restricted",
            "started_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), communication)
    result = StudentPrivacyProjectionService(
        tmp_path,
        repository=repository,
        currentness=_AlwaysCurrent(),
    ).project(_discovery())
    item = next(item for item in result.items if item.semantic_type == "communication")
    assert item.disposition == "withheld"
    assert item.fields == ()
    assert "Unrelated Recipient" not in repr(item)


def test_unavailable_is_distinct_from_absent_and_preserves_no_raw_guard_detail(
    tmp_path: Path,
) -> None:
    repository = _seed_event(tmp_path)
    service = StudentPrivacyProjectionService(
        tmp_path,
        repository=repository,
        currentness=_AlwaysUnavailable(),
    )
    result = service.project(_discovery())
    assert result.items
    assert all(item.disposition == "unavailable" for item in result.items)
    assert all(item.reason_code == "current_use_blocked" for item in result.items)
    assert "synthetic current-use block" not in repr(result)


def test_root_currentness_preserves_closed_event_but_blocks_obsolete_and_quarantine(
    tmp_path: Path,
) -> None:
    closed_repo = PortiaRepository(tmp_path / "closed")
    closed_repo.create_work(event_ref(), event_record(status="closed"))
    closed = StudentViewCurrentnessResolver(
        tmp_path / "closed", repository=closed_repo
    ).evaluate(event_ref())
    assert closed.state == "current"

    invalid_repo = PortiaRepository(tmp_path / "invalid")
    invalid_repo.create_work(event_ref(), event_record(status="invalidated"))
    invalid = StudentViewCurrentnessResolver(
        tmp_path / "invalid", repository=invalid_repo
    ).evaluate(event_ref())
    assert invalid.state == "noncurrent"

    blocked_repo = PortiaRepository(tmp_path / "blocked")
    blocked_repo.create_work(event_ref(), event_record(status="active"))
    blocked = StudentViewCurrentnessResolver(
        tmp_path / "blocked",
        repository=blocked_repo,
        quarantine=_BlockingQuarantine(),  # type: ignore[arg-type]
    ).evaluate(event_ref())
    assert blocked.state == "unavailable"
    assert blocked.reason_code == "current_use_blocked"



def test_child_currentness_delegates_to_existing_account_authority(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record(status="active"))
    repository.create_work_record(
        event_ref(),
        participant_record(
            subject={"kind": "unknown_person", "reason": "identity_not_known"}
        ),
    )
    account = parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": "acct_currentness",
            "status": "active",
            "target": {"kind": "event_participant", "record_ref": {"record_kind": "event_participant", "record_id": "ep_alpha", "contract_version": "3"}},
            "source": {"kind": "local_operator", "display_label": "Synthetic Teacher"},
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [{"representation": "recorded_summary", "text": "Synthetic current-use account."}],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), account)
    reference = ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind="account",
            record_id="acct_currentness",
            contract_version="2",
        ),
    )

    decision = StudentViewCurrentnessResolver(
        tmp_path,
        repository=repository,
    ).evaluate(reference)

    assert decision.state == "current"
    assert decision.reason_code == "current_representation"

def test_projection_decision_absent_cannot_enter_assembled_item() -> None:
    decision = ProjectionDecision(event_ref(), "absent", "not_focally_applicable")
    assert decision.item is None
