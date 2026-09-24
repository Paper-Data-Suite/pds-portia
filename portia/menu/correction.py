"""Teacher-facing Correct / Retract workflow."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from portia.menu.authoring import (
    AccountCorrectionInput,
    AccountRetractionInput,
    EvidenceInvalidationInput,
    ObservationCorrectionInput,
    event_summary_amendment_change,
    prepare_account_retraction,
    prepare_account_statement_correction,
    prepare_evidence_invalidation,
    prepare_observation_content_correction,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
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
from portia.menu.selectors import ClassOption, class_options
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models import PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.repository import StoredRecord
from portia.workflows import (
    AccountWorkflowService,
    AmendmentWorkflowService,
    EventWorkflowService,
    ObservationWorkflowService,
    PortiaWorkflowError,
    SupportProcessWorkflowService,
)

_ACCOUNT_INVALIDATION_REASONS = (
    ("recording_error", "Recording error"),
    ("wrong_source", "Wrong source"),
    ("wrong_target", "Wrong target"),
    ("invalid_provenance", "Invalid provenance"),
    ("prohibited_payload", "Prohibited payload"),
    ("other", "Other record-validity reason"),
)
_OBSERVATION_INVALIDATION_REASONS = (
    ("recording_error", "Recording error"),
    ("wrong_observer", "Wrong observer"),
    ("wrong_target", "Wrong target"),
    ("wrong_method", "Wrong method"),
    ("measurement_error", "Measurement error"),
    ("invalid_provenance", "Invalid provenance"),
    ("prohibited_payload", "Prohibited payload"),
    ("other", "Other record-validity reason"),
)


@dataclass(frozen=True, slots=True)
class WorkOption:
    work: ExactPortiaWorkRef
    stored: StoredRecord
    label: str


@dataclass(frozen=True, slots=True)
class EvidenceOption:
    reference: ExactPortiaWorkRecordRef
    stored: StoredRecord
    label: str


def _show_result(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _operator(state: MenuSessionContext) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        "Correct / Retract — Attribution",
        "Display label",
        help_text=(
            "This identifies the local operator recording the correction. "
            "It is provenance, not authentication or institutional authority."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _choose_class(root: Path) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError("No Core classes with both metadata and rosters are available.")
    return select_one(
        "Correct / Retract — Class",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact Core class that owns the Event or Support Process. "
            "The numbered selection carries canonical class identity."
        ),
    )


def _work_options(root: Path, class_id: str) -> tuple[WorkOption, ...]:
    preliminary: list[tuple[ExactPortiaWorkRef, StoredRecord, str]] = []

    for stored in EventWorkflowService(root).list(class_id):
        record = stored.record
        if record.work_id is None or record.status not in {"draft", "active", "closed"}:
            continue
        summary = record.field("summary")
        label = (
            f"Event — {summary if isinstance(summary, str) else 'No summary'} "
            f"— {(record.status or 'unknown').title()}"
        )
        preliminary.append(
            (
                ExactPortiaWorkRef(
                    class_id=class_id,
                    work_id=record.work_id,
                    work_kind="event",
                    contract_version="2",
                ),
                stored,
                label,
            )
        )

    for stored in SupportProcessWorkflowService(root).list(class_id):
        record = stored.record
        if record.work_id is None or record.status not in {"proposed", "active"}:
            continue
        summary = record.field("summary")
        workflow_state = record.field("workflow_state")
        state_label = (
            workflow_state.replace("_", " ").title()
            if isinstance(workflow_state, str)
            else "State unavailable"
        )
        label = (
            f"Support Process — "
            f"{summary if isinstance(summary, str) else 'No summary'} "
            f"— {(record.status or 'unknown').title()} / {state_label}"
        )
        preliminary.append(
            (
                ExactPortiaWorkRef(
                    class_id=class_id,
                    work_id=record.work_id,
                    work_kind="support_process",
                    contract_version="1",
                ),
                stored,
                label,
            )
        )

    counts = Counter(label.casefold() for _work, _stored, label in preliminary)
    options: list[WorkOption] = []
    for work, stored, label in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact {work.work_id}"
        options.append(WorkOption(work, stored, label))
    return tuple(options)


def _choose_work(root: Path, state: MenuSessionContext) -> WorkOption:
    owner = _choose_class(root)
    options = _work_options(root, owner.class_id)
    if not options:
        raise ValueError("No routine Event or Support Process correction targets are available.")
    selected = select_one(
        "Correct / Retract — Work",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact work containing the representation that needs correction. "
            "This does not modify anything."
        ),
    )
    if selected.work.work_kind == "event":
        state.remember_work(
            class_id=selected.work.class_id,
            work_kind="event",
            work_id=selected.work.work_id,
        )
    elif selected.work.work_kind == "support_process":
        state.remember_work(
            class_id=selected.work.class_id,
            work_kind="support_process",
            work_id=selected.work.work_id,
        )
    else:
        raise ValueError("routine correction work must be Event or Support Process")
    return selected


def _account_text(record: PortiaRecord) -> str:
    content = record.field("content")
    if isinstance(content, tuple):
        values = list(content)
    elif isinstance(content, list):
        values = content
    else:
        return "Account content"
    if len(values) == 1 and isinstance(values[0], Mapping):
        text = values[0].get("text")
        if isinstance(text, str):
            return " ".join(text.split())
    return "Account content"


def _observation_text(record: PortiaRecord) -> str:
    content = record.field("content")
    if isinstance(content, Mapping):
        text = content.get("narrative")
        if isinstance(text, str):
            return " ".join(text.split())
    return "Observation content"


def _evidence_options(
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    family: str,
) -> tuple[EvidenceOption, ...]:
    if family == "account":
        stored_items = AccountWorkflowService(root).list(work)
    elif family == "observation":
        stored_items = ObservationWorkflowService(root).list(work)
    else:
        raise ValueError(f"unsupported evidence family {family!r}")

    preliminary: list[tuple[ExactPortiaWorkRecordRef, StoredRecord, str]] = []
    for stored in stored_items:
        record = stored.record
        if record.status != "active" or record.logical_id is None:
            continue
        reference = ExactPortiaWorkRecordRef(
            work_ref=work,
            record_ref=ExactLocalRecordRef(
                record_kind=family,
                record_id=record.logical_id,
                contract_version=record.contract_version,
            ),
        )
        text = _account_text(record) if family == "account" else _observation_text(record)
        bounded = text if len(text) <= 96 else text[:95].rstrip() + "…"
        label = f"{family.title()} — {bounded}"
        preliminary.append((reference, stored, label))

    counts = Counter(label.casefold() for _ref, _stored, label in preliminary)
    options: list[EvidenceOption] = []
    for reference, stored, label in preliminary:
        if counts[label.casefold()] > 1:
            label += f" — exact {reference.record_ref.record_id}"
        options.append(EvidenceOption(reference, stored, label))
    return tuple(options)


def _choose_evidence(
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    family: str,
    title: str,
) -> EvidenceOption:
    options = _evidence_options(root, work, family=family)
    if not options:
        raise ValueError(f"No active {family.title()} records are available in this work.")
    return select_one(
        title,
        options,
        tuple(item.label for item in options),
        help_text=(
            f"Choose the exact active {family.title()} representation. "
            "Display text is context only; correction authority uses the exact reference."
        ),
    )


def _operation_error(title: str, exc: Exception) -> None:
    if isinstance(exc, PortiaConflictError):
        message = (
            "The canonical record changed after you selected it. "
            "Nothing was force-overwritten; reselect and review the current state."
        )
    elif isinstance(exc, PortiaOperationPartialCommitError):
        message = (
            "Some durable operation steps were accepted before the operation stopped. "
            "Do not retry blindly; recovery inspection is required."
        )
    elif isinstance(exc, PortiaRecoveryRequiredError):
        message = "This target requires recovery inspection before another correction write."
    else:
        message = "The requested correction is not permitted by the current canonical authority."
    _show_result(title, (message,))


def _correct_event_summary(
    state: MenuSessionContext,
    root: Path,
    selected: WorkOption,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    if selected.work.work_kind != "event":
        _show_result(
            "Correct / Retract — Event Summary",
            ("Nonmaterial summary Amendment is available only for Event records.",),
        )
        return
    current = EventWorkflowService(root).load_exact(selected.work)
    before = current.record.field("summary")
    if not isinstance(before, str):
        raise ValueError("The selected Event has no amendable summary text.")
    corrected = prompt_text(
        "Correct / Retract — Event Summary",
        "Corrected wording",
        help_text=(
            "Use this only for a nonmaterial wording correction that preserves the "
            "same underlying Event meaning. A material factual change requires a "
            "successor correction workflow rather than Amendment."
        ),
        default=before,
    )
    assert corrected is not None
    change = event_summary_amendment_change(current.record, corrected)
    if not confirm_write(
        "Correct / Retract — Event Summary",
        "AMEND",
        (
            f"Current: {before}",
            f"Corrected: {corrected}",
            "Typing AMEND confirms this wording correction is semantically equivalent.",
        ),
        help_text=(
            "Amendment is restricted to registered nonmaterial paths. "
            "It preserves immutable Amendment history and guarded target replacement."
        ),
    ):
        return
    operator = _operator(state)
    timestamp = clock.now().text
    AmendmentWorkflowService(root).apply_amendment(
        selected.work,
        expected=current.fingerprint,
        amendment_id=ids.new("amd_"),
        changes=(change,),
        reason_code="transcription_corrected",
        created_at=timestamp,
        created_by={"type": "local_operator", "display_label": operator},
        semantic_equivalence_confirmed=True,
        operation_id=ids.new("op_"),
    )
    _show_result(
        "Correct / Retract — Event Summary",
        ("The nonmaterial Event summary Amendment was applied.",),
    )


def _correct_account(
    state: MenuSessionContext,
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    selected = _choose_evidence(
        root, work, family="account", title="Correct / Retract — Account"
    )
    corrected = prompt_text(
        "Correct / Retract — Account",
        "Corrected statement",
        help_text=(
            "This is a material successor correction. The original Account remains "
            "historical and is superseded only through the Account correction service."
        ),
        default=_account_text(selected.stored.record),
    )
    assert corrected is not None
    operator = _operator(state)
    successor = prepare_account_statement_correction(
        AccountCorrectionInput(work, selected.stored.record, corrected, operator),
        clock=clock,
        ids=ids,
    )
    if not confirm_write(
        "Correct / Retract — Account",
        "CORRECT",
        (
            f"Current: {_account_text(selected.stored.record)}",
            f"Successor: {_account_text(successor)}",
            "The current Account will become historical as superseded.",
        ),
        help_text="Correction creates a new exact Account successor; it does not edit history in place.",
    ):
        return
    AccountWorkflowService(root).correct(
        selected.reference,
        successor,
        expected=selected.stored.fingerprint,
        transition_id=ids.new("lct_"),
        operation_id=ids.new("op_"),
    )
    _show_result("Correct / Retract — Account", ("The corrected Account successor was recorded.",))


def _retract_account(
    state: MenuSessionContext,
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    selected = _choose_evidence(
        root, work, family="account", title="Correct / Retract — Retract Account"
    )
    statement = prompt_text(
        "Correct / Retract — Retract Account",
        "Retraction statement",
        help_text=(
            "Record what the same represented source communicated to withdraw the "
            "earlier Account. Teacher-only status toggling cannot establish retraction."
        ),
    )
    assert statement is not None
    operator = _operator(state)
    retraction = prepare_account_retraction(
        AccountRetractionInput(work, selected.stored.record, statement, operator),
        clock=clock,
        ids=ids,
    )
    if not confirm_write(
        "Correct / Retract — Retract Account",
        "RETRACT",
        (
            f"Account: {_account_text(selected.stored.record)}",
            f"Retraction evidence: {_account_text(retraction)}",
            "Retraction requires the same represented source; the workflow service will verify it.",
        ),
        help_text=(
            "RETRACT creates same-source retraction evidence and transitions the "
            "selected Account through the explicit source-retraction workflow."
        ),
    ):
        return
    AccountWorkflowService(root).retract(
        selected.reference,
        retraction,
        expected=selected.stored.fingerprint,
        transition_id=ids.new("lct_"),
        operation_id=ids.new("op_"),
    )
    _show_result(
        "Correct / Retract — Retract Account",
        ("The source-evidenced Account retraction was recorded.",),
    )


def _invalidate_evidence(
    state: MenuSessionContext,
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    family: str,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    selected = _choose_evidence(
        root,
        work,
        family=family,
        title=f"Correct / Retract — Invalidate {family.title()}",
    )
    reasons = (
        _ACCOUNT_INVALIDATION_REASONS
        if family == "account"
        else _OBSERVATION_INVALIDATION_REASONS
    )
    reason = select_one(
        f"Correct / Retract — Invalidate {family.title()}",
        reasons,
        tuple(label for _code, label in reasons),
        help_text=(
            "Invalidation means the record representation is not valid for current use. "
            "It is distinct from source retraction and from a successor factual correction."
        ),
    )
    reason_code = reason[0]
    reason_detail = None
    if reason_code == "other":
        reason_detail = prompt_text(
            f"Correct / Retract — Invalidate {family.title()}",
            "Reason detail",
            help_text="Describe the bounded record-validity reason.",
        )
        assert reason_detail is not None
    operator = _operator(state)
    candidate = prepare_evidence_invalidation(
        EvidenceInvalidationInput(selected.stored.record, operator),
        clock=clock,
    )
    if not confirm_write(
        f"Correct / Retract — Invalidate {family.title()}",
        "INVALIDATE",
        (
            selected.label,
            f"Reason: {reason[1]}",
            "The substantive evidence fields will not be rewritten.",
        ),
        help_text="Invalidation uses the family's lifecycle authority and preserves history.",
    ):
        return
    service = (
        AccountWorkflowService(root)
        if family == "account"
        else ObservationWorkflowService(root)
    )
    service.transition_lifecycle(
        selected.reference,
        candidate,
        expected=selected.stored.fingerprint,
        transition_id=ids.new("lct_"),
        reason_code=reason_code,
        reason_detail=reason_detail,
        operation_id=ids.new("op_"),
    )
    _show_result(
        f"Correct / Retract — Invalidate {family.title()}",
        (f"The selected {family.title()} was invalidated through lifecycle authority.",),
    )


def _correct_observation(
    state: MenuSessionContext,
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    selected = _choose_evidence(
        root, work, family="observation", title="Correct / Retract — Observation"
    )
    corrected = prompt_text(
        "Correct / Retract — Observation",
        "Corrected observation narrative",
        help_text=(
            "This creates a material Observation successor. It is for correcting the "
            "recorded direct-observation narrative, not for adding interpretation."
        ),
        default=_observation_text(selected.stored.record),
    )
    assert corrected is not None
    operator = _operator(state)
    successor = prepare_observation_content_correction(
        ObservationCorrectionInput(work, selected.stored.record, corrected, operator),
        clock=clock,
        ids=ids,
    )
    if not confirm_write(
        "Correct / Retract — Observation",
        "CORRECT",
        (
            f"Current: {_observation_text(selected.stored.record)}",
            f"Successor: {_observation_text(successor)}",
            "The current Observation will become historical as superseded.",
        ),
        help_text="Correction creates a new exact Observation successor rather than editing history.",
    ):
        return
    ObservationWorkflowService(root).correct(
        selected.reference,
        successor,
        expected=selected.stored.fingerprint,
        transition_id=ids.new("lct_"),
        operation_id=ids.new("op_"),
    )
    _show_result(
        "Correct / Retract — Observation",
        ("The corrected Observation successor was recorded.",),
    )


def _advanced_notice() -> None:
    _show_result(
        "Correct / Retract — Other Record Families",
        (
            "This routine surface does not provide generic editing or deletion.",
            "Other record families require their exact family correction/lifecycle service.",
            "Ownership Correction and Exceptional Removal belong under Advanced Portia tools.",
        ),
    )


def _work_menu(
    state: MenuSessionContext,
    root: Path,
    selected: WorkOption,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> None:
    while True:
        clear_screen()
        print_menu_header("Correct / Retract")
        print(selected.label)
        print()
        if selected.work.work_kind == "event":
            print("1. Correct Event summary — nonmaterial Amendment")
        print("2. Correct reported information — Account successor")
        print("3. Retract reported information — same-source Account retraction")
        print("4. Invalidate reported information — Account lifecycle")
        print("5. Correct direct observation — Observation successor")
        print("6. Invalidate direct observation — Observation lifecycle")
        print("7. Other record family / expert correction")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Correct / Retract Help")
            print("Correction is family-specific. There is no generic edit, delete, or set-status operation.")
            print("Account retraction requires same-source retraction evidence.")
            print("A nonmaterial Amendment requires explicit semantic-equivalence confirmation.")
            print("Material corrections create successors and preserve the predecessor as history.")
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        try:
            if raw == "1" and selected.work.work_kind == "event":
                _correct_event_summary(state, root, selected, clock=clock, ids=ids)
            elif raw == "2":
                _correct_account(state, root, selected.work, clock=clock, ids=ids)
            elif raw == "3":
                _retract_account(state, root, selected.work, clock=clock, ids=ids)
            elif raw == "4":
                _invalidate_evidence(
                    state, root, selected.work, family="account", clock=clock, ids=ids
                )
            elif raw == "5":
                _correct_observation(state, root, selected.work, clock=clock, ids=ids)
            elif raw == "6":
                _invalidate_evidence(
                    state,
                    root,
                    selected.work,
                    family="observation",
                    clock=clock,
                    ids=ids,
                )
            elif raw == "7":
                _advanced_notice()
            else:
                print(navigation_hint_with_help())
                pause_for_user()
        except CancelMenuAction:
            continue
        except (
            PortiaWorkflowError,
            PortiaStorageError,
            ValueError,
        ) as exc:
            _operation_error("Correct / Retract — Not Applied", exc)


def launch_correct_retract_menu(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    """Launch bounded routine correction without generic record mutation."""

    selected_clock = clock or MenuClock()
    selected_ids = ids or PortiaIdGenerator()
    while True:
        clear_screen()
        print_menu_header("Correct / Retract")
        print("Choose an exact Event or Support Process, then an accepted family correction.")
        print()
        print("1. Choose an Event or Support Process")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("Correct / Retract Help")
            print("This surface never edits arbitrary JSON, deletes records, or forces current state.")
            print("Available actions are determined by accepted family workflow authority.")
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        if raw != "1":
            print(navigation_hint_with_help())
            pause_for_user()
            continue
        try:
            root = state.resolve_workspace()
            selected = _choose_work(root, state)
            _work_menu(
                state,
                root,
                selected,
                clock=selected_clock,
                ids=selected_ids,
            )
        except CancelMenuAction:
            continue
        except (PortiaWorkflowError, PortiaStorageError, ValueError) as exc:
            _operation_error("Correct / Retract — Unable to Open", exc)
