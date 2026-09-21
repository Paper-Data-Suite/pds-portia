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
from portia.storage import PortiaRepository
from portia.views import (
    STUDENT_VIEW_CHRONOLOGY_INVENTORY,
    STUDENT_VIEW_POLICY,
    STUDENT_VIEW_PROJECTION_INVENTORY,
    ChronologizedStudentViewItem,
    DiscoveredStudentWork,
    FilteredStudentTimelineResult,
    FocalParticipantMatch,
    ProjectedField,
    ProjectedStudentViewItem,
    SemanticTimelineMarker,
    StudentChronologyResult,
    StudentChronologyService,
    StudentPrivacyProjectionResult,
    StudentTimelineFilter,
    StudentTimelineFilterService,
    StudentTimelineQuery,
    StudentViewScope,
    StudentWorkDiscoveryResult,
    TimelineStateCriterion,
    chronology_rule,
    order_chronology_items,
)
from tests.workflow_helpers import (
    AGENT,
    event_ref,
    event_wire,
    participant_record,
)


def _child(
    kind: str,
    identifier: str,
    *,
    version: str = "1",
    work: ExactPortiaWorkRef | None = None,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work or event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind=kind,
            record_id=identifier,
            contract_version=version,
        ),
    )


def _discovery(
    *,
    work: ExactPortiaWorkRef | None = None,
) -> StudentWorkDiscoveryResult:
    selected = work or event_ref()
    student = RosterStudentRef(
        class_id=selected.class_id,
        student_id="student_1",
    )
    participant = _child(
        "event_participant",
        "ep_alpha",
        version="3",
        work=selected,
    )
    match = FocalParticipantMatch(
        student_ref=student,
        participant_ref=participant,
    )
    query = StudentTimelineQuery(
        scope=StudentViewScope(
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


def _projection(
    items: tuple[ProjectedStudentViewItem, ...],
) -> StudentPrivacyProjectionResult:
    return StudentPrivacyProjectionResult(
        discovery=_discovery(),
        policy=STUDENT_VIEW_POLICY,
        items=items,
    )


def _projected(
    source: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    *,
    semantic_type: str,
    category: str,
    status: str | None = "active",
    disposition: str = "included",
    fields: tuple[ProjectedField, ...] = (),
) -> ProjectedStudentViewItem:
    return ProjectedStudentViewItem(
        source_ref=source,
        disposition=disposition,  # type: ignore[arg-type]
        category=category,
        semantic_type=semantic_type,
        status=status,
        native_scope="work",
        focal_applicability="whole_work",
        fields=fields,
        reason_code="synthetic_test",
    )


def test_chronology_inventory_covers_every_projectable_contract() -> None:
    assert frozenset(STUDENT_VIEW_CHRONOLOGY_INVENTORY) == frozenset(
        STUDENT_VIEW_PROJECTION_INVENTORY
    )
    assert chronology_rule("event", "2").adapter == "event_occurrence"
    assert chronology_rule("account", "2").adapter == "evidence_time"
    assert chronology_rule("event_participant", "3").adapter == "unknown"
    assert chronology_rule("response", "1").adapter == "started_interval"
    assert chronology_rule("support", "1").adapter == "planned_schedule"
    assert chronology_rule("fidelity", "1").adapter == "evaluated_at"
    assert chronology_rule("follow_up", "1").adapter == "follow_up"
    assert chronology_rule("outcome", "1").adapter == "outcome_timeframe"
    assert chronology_rule("reentry", "1").adapter == "reentry"
    assert chronology_rule("repair", "1").adapter == "repair"


def test_event_date_only_occurrence_stays_date_only(tmp_path: Path) -> None:
    wire = event_wire()
    wire["occurrence"] = {
        "precision": "date_only",
        "date": "2026-09-17",
    }
    record = parse_portia_record("event", "2", wire)
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), record)

    projected = _projected(
        event_ref(),
        semantic_type="event",
        category="work_context",
    )
    result = StudentChronologyService(
        tmp_path,
        repository=repository,
    ).annotate(_projection((projected,)))

    marker = result.items[0].marker
    assert marker.precision == "date_only"
    assert marker.start == "2026-09-17"
    assert marker.end is None
    assert "T00:00" not in repr(marker)


def test_account_range_preserves_source_offsets_and_range(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    root = parse_portia_record("event", "2", event_wire())
    repository.create_work(event_ref(), root)
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
            "account_id": "acct_chronology",
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic chronology evidence.",
                }
            ],
            "provided_time": {
                "precision": "range",
                "started_at": "2026-09-18T08:15:00-04:00",
                "ended_at": "2026-09-18T09:45:00-04:00",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-18T10:00:00-04:00",
            "created_by": AGENT,
            "updated_at": "2026-09-18T10:00:00-04:00",
            "updated_by": AGENT,
        },
    )
    repository.create_work_record(event_ref(), account)
    source = _child("account", "acct_chronology", version="2")
    projected = _projected(
        source,
        semantic_type="account",
        category="evidence",
    )

    result = StudentChronologyService(
        tmp_path,
        repository=repository,
    ).annotate(_projection((projected,)))

    marker = result.items[0].marker
    assert marker.basis == "account_provided_time"
    assert marker.precision == "timestamp_range"
    assert marker.start == "2026-09-18T08:15:00-04:00"
    assert marker.end == "2026-09-18T09:45:00-04:00"


def test_audit_timestamp_is_not_participant_occurrence_fallback(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    repository.create_work(
        event_ref(),
        parse_portia_record("event", "2", event_wire()),
    )
    repository.create_work_record(
        event_ref(),
        participant_record(
            created_at="2026-09-19T07:00:00-04:00",
            updated_at="2026-09-19T08:00:00-04:00",
        ),
    )
    source = _child("event_participant", "ep_alpha", version="3")
    projected = _projected(
        source,
        semantic_type="event_participant",
        category="participation",
    )

    result = StudentChronologyService(
        tmp_path,
        repository=repository,
    ).annotate(_projection((projected,)))

    marker = result.items[0].marker
    assert marker.precision == "unknown"
    assert marker.start is None
    assert "2026-09-19" not in repr(marker)


def test_privacy_limited_item_does_not_read_or_expose_semantic_time(
    tmp_path: Path,
) -> None:
    source = _child("communication", "comm_hidden")
    projected = _projected(
        source,
        semantic_type="communication",
        category="response",
        disposition="withheld",
    )

    result = StudentChronologyService(tmp_path).annotate(
        _projection((projected,))
    )

    assert result.items[0].marker == SemanticTimelineMarker(
        "privacy_limited",
        "unknown",
    )


def _filter_chronology() -> StudentChronologyResult:
    event_item = _projected(
        event_ref(),
        semantic_type="event",
        category="work_context",
    )
    account = _projected(
        _child("account", "acct_filter", version="2"),
        semantic_type="account",
        category="evidence",
    )
    follow_up = _projected(
        _child("follow_up", "fu_filter"),
        semantic_type="follow_up",
        category="follow_up",
        fields=(
            ProjectedField(
                "workflow_state",
                "included",
                "completed",
            ),
        ),
    )
    unknown = _projected(
        _child("review", "rev_filter"),
        semantic_type="review",
        category="judgment",
    )
    projection = _projection((event_item, account, follow_up, unknown))
    values = (
        ChronologizedStudentViewItem(
            event_item,
            SemanticTimelineMarker(
                "event_occurrence",
                "date_only",
                "2026-09-01",
            ),
        ),
        ChronologizedStudentViewItem(
            account,
            SemanticTimelineMarker(
                "account_provided_time",
                "exact_timestamp",
                "2026-09-02T09:00:00-04:00",
            ),
        ),
        ChronologizedStudentViewItem(
            follow_up,
            SemanticTimelineMarker(
                "follow_up_planned_timing",
                "date_range",
                "2026-09-03",
                "2026-09-05",
                planned=True,
            ),
        ),
        ChronologizedStudentViewItem(
            unknown,
            SemanticTimelineMarker(
                "semantic_time_not_recorded",
                "unknown",
            ),
        ),
    )
    return StudentChronologyResult(
        projection,
        order_chronology_items(values),
    )


def test_filter_combines_date_family_category_status_and_safe_state() -> None:
    chronology = _filter_chronology()
    result = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(
            date_from="2026-09-04",
            date_to="2026-09-04",
            record_families=("follow_up",),
            categories=("follow_up",),
            statuses=("active",),
            states=(
                TimelineStateCriterion(
                    "workflow_state",
                    "completed",
                ),
            ),
        ),
    )

    assert isinstance(result, FilteredStudentTimelineResult)
    assert tuple(item.item.semantic_type for item in result.items) == (
        "follow_up",
    )


def test_date_filter_uses_interval_overlap_and_excludes_unknown_time() -> None:
    chronology = _filter_chronology()

    overlap = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(
            date_from="2026-09-05",
            date_to="2026-09-06",
        ),
    )
    assert tuple(item.item.semantic_type for item in overlap.items) == (
        "follow_up",
    )

    no_date = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(
            record_families=("review",),
        ),
    )
    assert tuple(item.item.semantic_type for item in no_date.items) == (
        "review",
    )


def test_state_filter_cannot_use_withheld_or_manual_field() -> None:
    chronology = _filter_chronology()
    account = next(
        item for item in chronology.items if item.item.semantic_type == "account"
    )
    altered = ChronologizedStudentViewItem(
        _projected(
            account.source_ref,
            semantic_type="account",
            category="evidence",
            fields=(
                ProjectedField(
                    "workflow_state",
                    "requires_manual_review",
                ),
            ),
        ),
        account.marker,
    )
    projection = _projection((altered.item,))
    one = StudentChronologyResult(projection, (altered,))

    result = StudentTimelineFilterService().apply(
        one,
        StudentTimelineFilter(
            states=(
                TimelineStateCriterion(
                    "workflow_state",
                    "completed",
                ),
            ),
        ),
    )
    assert result.items == ()


def test_mode_filter_never_widens_current_projection() -> None:
    chronology = _filter_chronology()

    history_only = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(modes=("history",)),
    )
    assert history_only.items == ()

    current = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(modes=("current",)),
    )
    assert len(current.items) == len(chronology.items)


def test_descending_sort_keeps_unknown_time_last() -> None:
    chronology = _filter_chronology()
    result = StudentTimelineFilterService().apply(
        chronology,
        StudentTimelineFilter(sort_direction="descending"),
    )

    assert tuple(item.item.semantic_type for item in result.items) == (
        "follow_up",
        "account",
        "event",
        "review",
    )
    assert result.items[-1].marker.precision == "unknown"


def test_neutral_exact_identity_breaks_equal_time_ties() -> None:
    first = _projected(
        _child("account", "acct_a", version="2"),
        semantic_type="account",
        category="evidence",
    )
    second = _projected(
        _child("account", "acct_b", version="2"),
        semantic_type="account",
        category="evidence",
    )
    marker = SemanticTimelineMarker(
        "account_provided_time",
        "exact_timestamp",
        "2026-09-20T10:00:00-04:00",
    )
    ordered = order_chronology_items(
        (
            ChronologizedStudentViewItem(second, marker),
            ChronologizedStudentViewItem(first, marker),
        )
    )

    assert ordered[0].source_ref == first.source_ref
    assert ordered[1].source_ref == second.source_ref


def test_filter_rejects_unsupported_family_category_and_state() -> None:
    with pytest.raises(Exception, match="unsupported student-view family"):
        StudentTimelineFilter(record_families=("future_profile",))
    with pytest.raises(Exception, match="unsupported student-view category"):
        StudentTimelineFilter(categories=("severity",))
    with pytest.raises(Exception, match="unsupported timeline state field"):
        TimelineStateCriterion("risk_state", "high")  # type: ignore[arg-type]


def test_marker_rejects_fabricated_or_invalid_precision() -> None:
    with pytest.raises(Exception, match="explicit UTC offset"):
        SemanticTimelineMarker(
            "event_occurrence",
            "exact_timestamp",
            "2026-09-20T10:00:00",
        )
    with pytest.raises(Exception, match="cannot end before"):
        SemanticTimelineMarker(
            "planned_window",
            "date_range",
            "2026-09-21",
            "2026-09-20",
        )
