from __future__ import annotations

import pytest

from portia.models import MODEL_REGISTRY
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.views import (
    STUDENT_VIEW_CONTRACT_INVENTORY,
    STUDENT_VIEW_POLICY,
    StudentTimelineItem,
    StudentTimelineQuery,
    StudentTimelineResult,
    StudentViewScope,
    StudentWorkView,
    contract_rule,
    student_view_policy_digest,
)


def event(
    class_id: str = "class_a",
    work_id: str = "evt_one",
    version: str = "2",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="event",
        contract_version=version,
    )


def support_process(
    class_id: str = "class_a",
    work_id: str = "sup_one",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def child(
    work: ExactPortiaWorkRef,
    record_kind: str,
    record_id: str,
    version: str = "1",
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=record_kind,
            record_id=record_id,
            contract_version=version,
        ),
    )


def test_contract_inventory_explicitly_classifies_every_runtime_contract() -> None:
    assert frozenset(STUDENT_VIEW_CONTRACT_INVENTORY) == frozenset(MODEL_REGISTRY)
    assert contract_rule("event", "2").surface == "work_root_current"
    assert contract_rule("event", "1").surface == "legacy_history_only"
    assert contract_rule("event_participant", "3").surface == "domain_current"
    assert contract_rule("operation_journal", "3").surface == "operational_excluded"
    assert contract_rule("deliberate_export", "1").surface == "export_excluded"


def test_unknown_contract_fails_closed() -> None:
    with pytest.raises(
        PortiaLocalValidationError,
        match="unsupported student-view contract",
    ):
        contract_rule("future_behavior_profile", "1")


def test_policy_identity_is_exact_and_deterministic() -> None:
    assert STUDENT_VIEW_POLICY.policy_id == "student_timeline_work_view"
    assert STUDENT_VIEW_POLICY.policy_version == "1"
    assert len(STUDENT_VIEW_POLICY.policy_digest) == 64
    assert STUDENT_VIEW_POLICY.policy_digest == student_view_policy_digest()


def test_scope_preserves_class_qualified_roster_identity() -> None:
    student_a = RosterStudentRef(class_id="class_a", student_id="student_17")
    student_b = RosterStudentRef(class_id="class_b", student_id="student_17")
    event_a = event()
    support_b = support_process(class_id="class_b", work_id="sup_two")

    scope = StudentViewScope(
        focal_students=(student_a, student_b),
        allowed_works=(event_a, support_b),
        history_allowed=True,
    )

    assert scope.class_ids == frozenset({"class_a", "class_b"})
    assert scope.allows_student(student_a)
    assert scope.allows_student(student_b)
    assert scope.allows_work(event_a)
    assert scope.allows_work(support_b)
    assert not scope.allows_work(event(class_id="class_c", work_id="evt_other"))


def test_scope_rejects_work_outside_explicit_owner_class_scope() -> None:
    student = RosterStudentRef(class_id="class_a", student_id="student_17")
    with pytest.raises(
        PortiaLocalValidationError,
        match="outside the explicit allowed work-owner class scope",
    ):
        StudentViewScope(
            focal_students=(student,),
            allowed_works=(event(class_id="class_b"),),
        )


def test_scope_can_deliberately_separate_focal_and_work_owner_class() -> None:
    student = RosterStudentRef(class_id="class_b", student_id="student_17")
    cross_class_event = event(class_id="class_a")
    scope = StudentViewScope(
        focal_students=(student,),
        allowed_class_ids=("class_a",),
        allowed_works=(cross_class_event,),
    )

    assert scope.class_ids == frozenset({"class_b"})
    assert scope.work_class_ids == frozenset({"class_a"})
    assert scope.allows_student(student)
    assert scope.allows_work(cross_class_event)
    assert not scope.allows_work(event(class_id="class_b", work_id="evt_other"))


def test_scope_rejects_duplicate_allowed_owner_class() -> None:
    student = RosterStudentRef(class_id="class_a", student_id="student_17")
    with pytest.raises(PortiaLocalValidationError, match="cannot repeat"):
        StudentViewScope(
            focal_students=(student,),
            allowed_class_ids=("class_a", "class_a"),
        )


def test_scope_rejects_duplicate_exact_roster_identity() -> None:
    student = RosterStudentRef(class_id="class_a", student_id="student_17")
    with pytest.raises(PortiaLocalValidationError, match="cannot repeat"):
        StudentViewScope(focal_students=(student, student))




def test_legacy_work_scope_requires_explicit_history_authority() -> None:
    with pytest.raises(
        PortiaLocalValidationError,
        match="legacy work scope requires explicit history authority",
    ):
        StudentViewScope(
            focal_students=(
                RosterStudentRef(
                    class_id="class_a",
                    student_id="student_17",
                ),
            ),
            allowed_works=(event(version="1"),),
        )


def test_history_query_requires_explicit_history_authority() -> None:
    scope = StudentViewScope(
        focal_students=(
            RosterStudentRef(class_id="class_a", student_id="student_17"),
        )
    )
    with pytest.raises(
        PortiaLocalValidationError,
        match="history mode requires explicit history authority",
    ):
        StudentTimelineQuery(scope=scope, mode="history")


def test_current_query_rejects_legacy_work_root() -> None:
    legacy = event(version="1")
    scope = StudentViewScope(
        focal_students=(
            RosterStudentRef(class_id="class_a", student_id="student_17"),
        ),
        allowed_works=(legacy,),
        history_allowed=True,
    )
    with pytest.raises(
        PortiaLocalValidationError,
        match="current-view work scope requires a current work-root",
    ):
        StudentTimelineQuery(
            scope=scope,
            mode="current",
            exact_works=(legacy,),
        )

    history = StudentTimelineQuery(
        scope=scope,
        mode="history",
        exact_works=(legacy,),
    )
    assert history.selected_works == (legacy,)


def test_query_narrowing_cannot_escape_scope() -> None:
    selected = event()
    scope = StudentViewScope(
        focal_students=(
            RosterStudentRef(class_id="class_a", student_id="student_17"),
        ),
        allowed_works=(selected,),
    )
    with pytest.raises(
        PortiaLocalValidationError,
        match="outside the explicit student view scope",
    ):
        StudentTimelineQuery(
            scope=scope,
            exact_works=(event(work_id="evt_other"),),
        )


def test_timeline_item_keeps_exact_source_without_native_payload() -> None:
    work = event()
    source = child(work, "account", "acct_one", version="2")
    item = StudentTimelineItem(source)

    assert item.source_ref == source
    assert item.work_ref == work
    assert item.record_kind == "account"
    assert item.contract_version == "2"


def test_timeline_item_rejects_operational_or_export_source() -> None:
    work = event()
    with pytest.raises(
        PortiaLocalValidationError,
        match="cannot expose an identity, operational, or export-only contract",
    ):
        StudentTimelineItem(
            child(work, "operation_journal", "op_one", version="3")
        )


def test_work_and_timeline_results_remain_inside_exact_scope() -> None:
    selected = event()
    item = StudentTimelineItem(
        child(selected, "observation", "obs_one", version="2")
    )
    scope = StudentViewScope(
        focal_students=(
            RosterStudentRef(class_id="class_a", student_id="student_17"),
        ),
        allowed_works=(selected,),
    )
    query = StudentTimelineQuery(scope=scope, exact_works=(selected,))
    work_view = StudentWorkView(work_ref=selected, items=(item,))
    result = StudentTimelineResult(
        query=query,
        items=(item,),
        works=(work_view,),
    )

    assert result.items == (item,)
    assert result.works == (work_view,)

    foreign = event(work_id="evt_other")
    foreign_item = StudentTimelineItem(
        child(foreign, "observation", "obs_other", version="2")
    )
    with pytest.raises(PortiaLocalValidationError, match="outside query scope"):
        StudentTimelineResult(query=query, items=(foreign_item,))


def test_current_result_rejects_legacy_historical_item() -> None:
    current = event()
    scope = StudentViewScope(
        focal_students=(
            RosterStudentRef(class_id="class_a", student_id="student_17"),
        ),
        history_allowed=True,
    )
    query = StudentTimelineQuery(scope=scope)
    legacy_item = StudentTimelineItem(
        child(current, "event_participant", "ep_legacy", version="2")
    )

    with pytest.raises(
        PortiaLocalValidationError,
        match="cannot contain legacy historical representations",
    ):
        StudentTimelineResult(query=query, items=(legacy_item,))
