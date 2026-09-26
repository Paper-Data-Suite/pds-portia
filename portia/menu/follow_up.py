"""Teacher-facing Complete Follow-Up workflow."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from portia.attention import (
    FollowUpScheduleQuery,
    FollowUpScheduleQueryService,
    PortiaAttentionScope,
    TimingClassification,
    TimingDecision,
)
from portia.menu.authoring import (
    FollowUpCompletionInput,
    prepare_follow_up_completion,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.navigation import (
    NavigationChoice,
    PortiaMenuChoice,
    navigation_hint_with_help,
    parse_menu_navigation,
)
from portia.menu.prompts import (
    CancelMenuAction,
    confirm_write,
    prompt_text,
    select_one,
)
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models import FollowUpV1
from portia.models.references import ExactPortiaWorkRecordRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.repository import PortiaRepository
from portia.workflows import FollowUpWorkflowService, PortiaWorkflowError

_PURPOSE_LABELS = {
    "student_check_in": "Student check-in",
    "family_or_support_person_check_in": "Family/support-person check-in",
    "affected_person_check_in": "Affected-person check-in",
    "event_review": "Event review",
    "response_review": "Response review",
    "support_process_review": "Support Process review",
    "goal_review": "Goal review",
    "implementation_review": "Implementation review",
    "fidelity_review": "Fidelity review",
    "reentry_check": "Reentry check",
    "repair_check": "Repair check",
    "coordination": "Coordination",
    "other": "Other",
}
_CLASSIFICATION_LABELS: dict[TimingClassification, str] = {
    "due": "Due",
    "overdue": "Overdue",
    "scheduled": "Scheduled later",
}
_DISPOSITIONS: tuple[tuple[str | None, str], ...] = (
    (None, "No disposition — record completion only"),
    ("continue_current_support", "Continue current support"),
    ("review_later", "Review later"),
    ("adapt_plan", "Adapt plan"),
    ("fade_or_reduce_support", "Fade or reduce support"),
    ("complete_process", "Complete process"),
    ("discontinue_process", "Discontinue process"),
    ("no_additional_action", "No additional action"),
    ("other", "Other"),
)
_DISPOSITION_PURPOSES = frozenset(
    {
        "response_review",
        "support_process_review",
        "goal_review",
        "implementation_review",
        "fidelity_review",
    }
)


@dataclass(frozen=True, slots=True)
class FollowUpOption:
    """One exact current Follow-Up rendered with bounded teacher context."""

    reference: ExactPortiaWorkRecordRef
    classification: TimingClassification
    workflow_state: str
    purpose_kind: str
    purpose_label: str
    timing_label: str
    work_label: str
    label: str


def _show_result(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _require_operator(state: MenuSessionContext, *, title: str) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        title,
        "Display label",
        help_text=(
            "Enter the teacher-facing name or label for the local operator. "
            "This records provenance only; it is not authentication or institutional authority."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _bounded(value: str, *, limit: int = 72) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _purpose_kind(record: FollowUpV1) -> str:
    purpose = record.field("purpose")
    if not isinstance(purpose, Mapping):
        raise PortiaCorruptionError("current Follow-Up purpose is malformed")
    kind = purpose.get("kind")
    if not isinstance(kind, str):
        raise PortiaCorruptionError("current Follow-Up purpose kind is malformed")
    return kind


def _purpose_label(record: FollowUpV1) -> tuple[str, str]:
    kind = _purpose_kind(record)
    label = _PURPOSE_LABELS.get(kind, kind.replace("_", " ").title())
    purpose = record.field("purpose")
    assert isinstance(purpose, Mapping)
    detail = purpose.get("detail")
    if isinstance(detail, str) and detail.strip():
        label += f" — {_bounded(detail, limit=48)}"
    return kind, label


def _timing_label(timing: TimingDecision) -> str:
    if timing.precision == "date":
        assert isinstance(timing.start, date)
        assert not isinstance(timing.start, datetime)
        assert isinstance(timing.end, date)
        assert not isinstance(timing.end, datetime)
        if timing.start == timing.end:
            return timing.start.isoformat()
        return f"{timing.start.isoformat()} to {timing.end.isoformat()}"
    assert isinstance(timing.start, datetime)
    assert isinstance(timing.end, datetime)
    if timing.start == timing.end:
        return timing.start.isoformat(timespec="minutes")
    return (
        f"{timing.start.isoformat(timespec='minutes')} to "
        f"{timing.end.isoformat(timespec='minutes')}"
    )


def _work_label(repository: PortiaRepository, reference: ExactPortiaWorkRecordRef) -> str:
    work = reference.work_ref
    stored = repository.load_work(work)
    summary = stored.record.field("summary")
    summary_label = _bounded(summary) if isinstance(summary, str) else "No summary"
    kind_label = "Event" if work.work_kind == "event" else "Support Process"
    return f"{work.class_id} — {kind_label} — {summary_label}"


def follow_up_options(
    root: Path,
    *,
    clock: MenuClock,
) -> tuple[FollowUpOption, ...]:
    """Return current Follow-Ups grouped by native schedule classification."""

    query = FollowUpScheduleQuery(
        scope=PortiaAttentionScope.workspace_scope(),
        as_of=clock.now(),
    )
    schedule = FollowUpScheduleQueryService(root).query(query)
    service = FollowUpWorkflowService(root)
    repository = PortiaRepository(root)
    raw: list[FollowUpOption] = []
    for schedule_item in schedule:
        current = service.require_current_use(schedule_item.source_ref)
        if not isinstance(current.record, FollowUpV1):
            raise PortiaCorruptionError("schedule query resolved a non-Follow-Up record")
        state = current.record.field("workflow_state")
        if not isinstance(state, str):
            raise PortiaCorruptionError("current Follow-Up workflow_state is malformed")
        purpose_kind, purpose_label = _purpose_label(current.record)
        work_label = _work_label(repository, schedule_item.source_ref)
        timing_label = _timing_label(schedule_item.timing)
        classification = schedule_item.timing.classification
        label = (
            f"{_CLASSIFICATION_LABELS[classification]} — {work_label} — "
            f"{purpose_label} — {timing_label}"
        )
        raw.append(
            FollowUpOption(
                reference=schedule_item.source_ref,
                classification=classification,
                workflow_state=state,
                purpose_kind=purpose_kind,
                purpose_label=purpose_label,
                timing_label=timing_label,
                work_label=work_label,
                label=label,
            )
        )

    grouped: list[FollowUpOption] = []
    for classification in ("due", "overdue", "scheduled"):
        grouped.extend(item for item in raw if item.classification == classification)

    counts = Counter(item.label.casefold() for item in grouped)
    result: list[FollowUpOption] = []
    for option in grouped:
        label = option.label
        if counts[label.casefold()] > 1:
            label += f" — {option.reference.record_ref.record_id}"
        result.append(
            FollowUpOption(
                reference=option.reference,
                classification=option.classification,
                workflow_state=option.workflow_state,
                purpose_kind=option.purpose_kind,
                purpose_label=option.purpose_label,
                timing_label=option.timing_label,
                work_label=option.work_label,
                label=label,
            )
        )
    return tuple(result)


def _eligible_for_disposition(record: FollowUpV1) -> bool:
    if record.field("work_kind") != "support_process":
        return False
    return _purpose_kind(record) in _DISPOSITION_PURPOSES


def _collect_disposition(record: FollowUpV1) -> tuple[str | None, str | None]:
    if not _eligible_for_disposition(record):
        return None, None
    values = tuple(value for value, _label in _DISPOSITIONS)
    labels = tuple(label for _value, label in _DISPOSITIONS)
    selected = select_one(
        "Complete Follow-Up — Disposition",
        values,
        labels,
        help_text=(
            "A disposition is a human-selected next-workflow note for an eligible "
            "Support Process review. It is not an Outcome and does not change the "
            "Support Process state automatically."
        ),
    )
    if selected != "other":
        return selected, None
    detail = prompt_text(
        "Complete Follow-Up — Disposition",
        "Disposition detail",
        help_text="Describe the other next-workflow disposition in bounded terms.",
    )
    assert detail is not None
    return selected, detail


def complete_follow_up_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
) -> None:
    """Select and explicitly complete one exact current Follow-Up."""

    active_clock = clock or MenuClock()
    root = state.resolve_workspace()
    options = follow_up_options(root, clock=active_clock)
    if not options:
        _show_result(
            "Complete Follow-Up",
            (
                "No current scheduled, due, or overdue Follow-Ups were found.",
                "Completed, cancelled, unable-to-complete, proposed, or "
                "invalidated records are not listed.",
            ),
        )
        return

    option = select_one(
        "Complete Follow-Up",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Due, overdue, and scheduled-later are native schedule classifications. "
            "Scheduled later is not attention. Selecting an item does not modify it."
        ),
    )

    service = FollowUpWorkflowService(root)
    current = service.require_current_use(option.reference)
    if not isinstance(current.record, FollowUpV1):
        raise PortiaCorruptionError("selected record is not a Follow-Up")
    current_state = current.record.field("workflow_state")
    if current_state not in {"scheduled", "in_progress"}:
        raise PortiaConflictError(
            "selected Follow-Up is no longer scheduled or in progress"
        )

    operator = _require_operator(state, title="Complete Follow-Up")
    disposition_kind, disposition_detail = _collect_disposition(current.record)
    candidate = prepare_follow_up_completion(
        FollowUpCompletionInput(
            prior=current.record,
            local_operator_label=operator,
            disposition_kind=disposition_kind,
            disposition_detail=disposition_detail,
        ),
        clock=active_clock,
    )

    preview = [
        f"Schedule status: {_CLASSIFICATION_LABELS[option.classification]}",
        f"Work: {option.work_label}",
        f"Purpose: {option.purpose_label}",
        f"Planned timing: {option.timing_label}",
        f"Current workflow state: {current_state}",
        f"New workflow state: {candidate.field('workflow_state')}",
        f"Completed at: {candidate.field('completed_at')}",
    ]
    disposition = candidate.field("disposition")
    if isinstance(disposition, Mapping):
        kind = disposition.get("kind")
        preview.append(f"Disposition: {kind}")
        preview.append(
            "Disposition is a workflow note only; it does not change the Support Process state."
        )
    preview.extend(
        (
            "Completion records the Follow-Up workflow fact only.",
            "It does not establish success, improvement, resolution, effectiveness, or an Outcome.",
            "No Outcome, Reentry, or Repair record will be created automatically.",
        )
    )

    if not confirm_write(
        "Complete Follow-Up — Confirm",
        "COMPLETE",
        tuple(preview),
        help_text=(
            "This replaces only the selected exact Follow-Up through its canonical "
            "workflow-state service using the currently loaded fingerprint."
        ),
    ):
        return

    accepted = service.transition_workflow_state(
        option.reference,
        candidate,
        expected=current.fingerprint,
    )
    _show_result(
        "Follow-Up Completed",
        (
            f"Workflow state: {accepted.record.field('workflow_state')}",
            f"Completed at: {accepted.record.field('completed_at')}",
            "No Outcome, Reentry, Repair, or Support Process transition was created automatically.",
        ),
    )


def _help() -> None:
    clear_screen()
    print_menu_header("Complete Follow-Up Help")
    print("This task uses Portia's native Follow-Up schedule query.")
    print("Due, overdue, and scheduled later remain separate schedule states.")
    print("Opening, listing, or previewing a Follow-Up is zero-write.")
    print("Completion applies only to the exact selected Follow-Up and is not an Outcome.")
    print()
    pause_for_user()


def _handle_error(exc: Exception) -> None:
    if isinstance(exc, PortiaConflictError):
        message = (
            "The Follow-Up changed before completion. Reopen the list and review "
            "the current record."
        )
    elif isinstance(exc, PortiaRecoveryRequiredError):
        message = "Portia requires recovery before this Follow-Up can be changed."
    elif isinstance(exc, PortiaQuarantinedError):
        message = "This Follow-Up is blocked from current use by Quarantine."
    elif isinstance(exc, PortiaCorruptionError):
        message = "Portia found malformed or inconsistent Follow-Up state."
    elif isinstance(exc, (PortiaStorageError, PortiaWorkflowError, ValueError)):
        message = str(exc)
    else:
        raise exc
    _show_result("Complete Follow-Up", (message,))


def launch_complete_follow_up_menu(state: MenuSessionContext) -> None:
    """Launch the routine Complete Follow-Up teacher task."""

    while True:
        try:
            clear_screen()
            print_menu_header("Complete Follow-Up")
            print("1. Review scheduled Follow-Ups")
            print()
            print("Due, overdue, and scheduled-later items remain distinct.")
            print("Viewing this task does not complete anything.")
            print_navigation()
            print()
            raw = input("Select an option: ").strip()
            navigation = parse_menu_navigation(raw)
            if navigation is PortiaMenuChoice.HELP:
                _help()
            elif navigation is NavigationChoice.BACK:
                return
            elif raw == "1":
                complete_follow_up_once(state)
            else:
                print(navigation_hint_with_help())
                pause_for_user()
        except CancelMenuAction:
            continue
        except (
            PortiaConflictError,
            PortiaCorruptionError,
            PortiaQuarantinedError,
            PortiaRecoveryRequiredError,
            PortiaStorageError,
            PortiaWorkflowError,
            ValueError,
        ) as exc:
            _handle_error(exc)
