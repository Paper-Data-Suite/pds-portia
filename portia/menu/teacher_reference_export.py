"""Contextual teacher-reference export workflow for the Portia teacher menu."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

from portia.exports import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionFailure,
    TeacherReferenceExportExecutionService,
    TeacherReferenceExportExecutionSuccess,
    TeacherReferenceExportHistoryEntry,
    TeacherReferenceExportHistoryService,
    TeacherReferenceExportPreparation,
    TeacherReferenceExportPreparationService,
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionDecision,
    TeacherReferenceProjectionItem,
    TeacherReferenceProjectionService,
    TeacherReferencePurpose,
    TeacherReferenceScopeDiscoveryService,
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
from portia.menu.prompts import CancelMenuAction, confirm_write, prompt_text, select_one
from portia.menu.selectors import StudentOption
from portia.menu.ui import (
    clear_screen,
    pause_for_user,
    print_menu_header,
    print_navigation,
)
from portia.models.errors import PortiaLocalValidationError
from portia.models.json_values import thaw_json
from portia.models.references import ExactPortiaWorkRecordRef
from portia.storage.errors import PortiaStorageError
from portia.views import StudentWorkTimelineView

_DEPLOYMENT_INSTANCE_ID = "local_teacher_menu"


def _actor(display_label: str) -> dict[str, object]:
    return {"type": "local_operator", "display_label": display_label}


def _operator(state: MenuSessionContext) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        "Export Teacher Reference — Attribution",
        "Display label",
        help_text=(
            "This identifies the local operator requesting the local teacher-reference "
            "export. It is provenance, not authentication, disclosure authority, or "
            "institutional approval."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _purpose_label(purpose: str) -> str:
    if purpose == "teacher_current":
        return "Whole work"
    if purpose == "participant_specific":
        return "Selected participant"
    return purpose.replace("_", " ").title()


def _verification_label(value: str) -> str:
    labels = {
        "available_verified": "Available and verified",
        "artifact_missing": "Artifact missing",
        "artifact_mismatch": "Artifact mismatch",
        "operation_recovery_required": "Operation recovery required",
        "provenance_invalid": "Provenance invalid",
    }
    return labels.get(value, value.replace("_", " ").title())


def _source_label(item: TeacherReferenceProjectionItem) -> str:
    source = item.source_ref
    if isinstance(source, ExactPortiaWorkRecordRef):
        return (
            f"{source.record_ref.record_kind} "
            f"({source.record_ref.record_id})"
        )
    return f"{source.work_kind} ({source.work_id})"


def _review_value(item: TeacherReferenceProjectionItem) -> str:
    if not item.review_value_present:
        raise PortiaLocalValidationError(
            "manual-review item does not retain exact source content"
        )
    value = thaw_json(item.review_value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        indent=2,
        sort_keys=True,
    )


def _resolve_manual_review(
    decision: TeacherReferenceProjectionDecision,
    projection: TeacherReferenceProjectionService,
    *,
    operator: str,
    clock: MenuClock,
) -> TeacherReferenceProjectionDecision:
    pending = decision.unresolved_manual_items
    if not pending:
        return decision

    choices: list[TeacherReferenceManualReviewChoice] = []
    for index, item in enumerate(pending, start=1):
        assert item.field_name is not None
        while True:
            clear_screen()
            print_menu_header("Export Teacher Reference — Manual Review")
            print(f"Item {index} of {len(pending)}")
            print(f"Source: {_source_label(item)}")
            print(f"Field: {item.field_name.replace('_', ' ').title()}")
            print()
            print("Exact source value:")
            print(_review_value(item))
            print()
            print("1. Include exact source content")
            print("2. Omit this content")
            print_navigation()
            print()
            raw = input("Select an option: ").strip()
            navigation = parse_menu_navigation(raw)
            if navigation is PortiaMenuChoice.HELP:
                clear_screen()
                print_menu_header("Export Teacher Reference — Manual Review Help")
                print(
                    "Portia does not summarize, rewrite, sanitize, or automatically "
                    "redact manual-review content. Choose Include exact to export the "
                    "source value unchanged, or Omit to leave it out."
                )
                print()
                pause_for_user()
                continue
            if navigation is NavigationChoice.BACK:
                raise CancelMenuAction
            if raw == "1":
                choices.append(
                    TeacherReferenceManualReviewChoice(
                        item.source_ref,
                        item.field_name,
                        "include_exact",
                    )
                )
                break
            if raw == "2":
                choices.append(
                    TeacherReferenceManualReviewChoice(
                        item.source_ref,
                        item.field_name,
                        "omit",
                    )
                )
                break
            print(navigation_hint_with_help())
            pause_for_user()

    reviewed_at = clock.now().text
    return projection.resolve_manual_review(
        decision,
        choices,
        reviewed_at=reviewed_at,
        reviewed_by=_actor(operator),
    )


def _choose_focal_participant(
    work: StudentWorkTimelineView,
) -> ExactPortiaWorkRecordRef | None:
    refs = work.focal_participant_refs
    if not refs:
        return None
    if len(refs) == 1:
        return refs[0]
    return select_one(
        "Export Teacher Reference — Participant",
        refs,
        tuple(
            f"{ref.record_ref.record_kind} — exact {ref.record_ref.record_id}"
            for ref in refs
        ),
        help_text=(
            "More than one exact focal participant representation is available for "
            "the selected roster student in this work. Choose the exact record; "
            "display names are not identity authority."
        ),
    )


def _preview_lines(
    preparation: TeacherReferenceExportPreparation,
) -> tuple[str, ...]:
    preview = preparation.preview
    lines: list[str] = [
        f"Selected work: {preview.selected_work}",
        f"Scope: {_purpose_label(preview.projection_purpose)}",
    ]
    if preview.focal_participant is not None:
        lines.append(f"Focal participant: {preview.focal_participant}")
    lines.extend(
        (
            f"Format: {preview.artifact_format} ({preview.media_type})",
            "Included sections: "
            + (", ".join(preview.included_sections) or "None"),
            (
                "Projection items: "
                f"{preview.included_count} included; "
                f"{preview.withheld_count} withheld; "
                f"{preview.unavailable_count} unavailable; "
                f"{preview.absent_count} absent"
            ),
        )
    )
    if preview.manual_review_decisions:
        lines.append("Manual-review decisions:")
        for item in preview.manual_review_decisions:
            action = "Include exact" if item.resolution == "include_exact" else "Omit"
            lines.append(
                f"  {item.record_kind}.{item.field_name}: {action}"
            )
    for warning in preview.warnings:
        lines.append(f"Warning: {warning}")
    lines.extend(
        (
            "",
            "Exact outgoing HTML:",
            preview.artifact_html,
            "Technical details:",
            f"  Export ID: {preview.export_id}",
            f"  Output: {preview.artifact_relative_path}",
            f"  Artifact bytes: {preview.artifact_byte_length}",
            f"  Artifact SHA-256: {preview.artifact_sha256}",
            f"  Source inventory: {preview.source_inventory_digest}",
            f"  Projection decision: {preview.projection_decision_digest}",
            f"  Preparation: {preview.preparation_digest}",
        )
    )
    return tuple(lines)


def _show_execution_result(
    result: TeacherReferenceExportExecutionSuccess | TeacherReferenceExportExecutionFailure,
    preparation: TeacherReferenceExportPreparation,
) -> None:
    clear_screen()
    if isinstance(result, TeacherReferenceExportExecutionSuccess):
        print_menu_header("Teacher Reference Created")
        generated = preparation.deliberate_export.field("generated_at")
        print("Teacher reference created.")
        print("Format: HTML")
        if isinstance(generated, str):
            print(f"Generated: {generated}")
        print(f"Output: {result.artifact_relative_path}")
        print("Verification: Available and verified")
        print()
        print(
            "This is a local teacher reference. Generation does not mean the "
            "artifact was sent, shared, filed, delivered, received, or accepted "
            "by a school system."
        )
    else:
        print_menu_header("Teacher Reference — Not Created")
        print(result.message)
        print(f"Status: {result.code.replace('_', ' ').title()}")
        if result.durable_state_may_exist:
            print(
                "Durable operation state may exist. Use the accepted export recovery "
                "path rather than creating replacement provenance."
            )
        print()
        print(f"Operation ID: {result.operation_id}")
    print()
    pause_for_user()


def _run_export(
    state: MenuSessionContext,
    root: Path,
    work: StudentWorkTimelineView,
    *,
    participant_specific: bool,
    clock: MenuClock,
    id_generator: PortiaIdGenerator | None,
    deployment_instance_id: str,
    process_instance_id: str,
) -> None:
    focal: ExactPortiaWorkRecordRef | None = None
    if participant_specific:
        focal = _choose_focal_participant(work)
        if focal is None:
            clear_screen()
            print_menu_header("Export Teacher Reference")
            print(
                "No exact focal participant is available for the selected student "
                "in this work, so a participant-specific export cannot be prepared."
            )
            print()
            pause_for_user()
            return

    operator = _operator(state)
    requested_at = clock.now().text
    purpose: TeacherReferencePurpose = (
        "participant_specific" if participant_specific else "teacher_current"
    )
    scope = TeacherReferenceExportScope(
        projection_purpose=purpose,
        work_ref=work.work_ref,
        focal_subject_ref=focal,
    )
    discovery = TeacherReferenceScopeDiscoveryService(root).discover(scope)
    projection = TeacherReferenceProjectionService(root)
    decision = projection.project(discovery)
    decision = _resolve_manual_review(
        decision,
        projection,
        operator=operator,
        clock=clock,
    )
    if decision.disposition_summary.included == 0:
        clear_screen()
        print_menu_header("Export Teacher Reference — Nothing to Export")
        print(
            "The privacy projection contains no included content. Portia will not "
            "create a misleading empty teacher reference."
        )
        print()
        pause_for_user()
        return

    generated_at = clock.now().text
    preparation = TeacherReferenceExportPreparationService(
        root,
        id_generator=id_generator,
    ).prepare(
        decision,
        requested_at=requested_at,
        requested_by=_actor(operator),
        generated_at=generated_at,
        deployment_instance_id=deployment_instance_id,
        process_instance_id=process_instance_id,
    )
    confirmed = confirm_write(
        "Export Teacher Reference — Final Preview",
        TEACHER_REFERENCE_CONFIRMATION,
        _preview_lines(preparation),
        help_text=(
            "Review the exact outgoing HTML. EXPORT authorizes only this exact "
            "preparation. If material state changes, execution fails closed and "
            "requires a new preview. Generation is not disclosure or delivery."
        ),
    )
    if not confirmed:
        return

    result = TeacherReferenceExportExecutionService(root).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=clock.now().text,
    )
    _show_execution_result(result, preparation)


def _history_line(entry: TeacherReferenceExportHistoryEntry) -> tuple[str, ...]:
    generated = entry.generated_at or "Generated time unavailable"
    purpose = (
        _purpose_label(entry.projection_purpose)
        if entry.projection_purpose is not None
        else "Purpose unavailable"
    )
    artifact_format = entry.artifact_format or "Format unavailable"
    lines = [
        f"{generated} — {purpose} — {artifact_format.upper()}",
        f"   Verification: {_verification_label(entry.verification_status)}",
        f"   Export ID: {entry.export_id}",
    ]
    if entry.artifact_relative_path is not None:
        lines.append(f"   Artifact: {entry.artifact_relative_path}")
    if entry.operation_id is not None:
        lines.append(f"   Operation ID: {entry.operation_id}")
    return tuple(lines)


def _show_history(root: Path, work: StudentWorkTimelineView) -> None:
    entries = TeacherReferenceExportHistoryService(root).list_for_work(work.work_ref)
    clear_screen()
    print_menu_header("Teacher Reference Export History")
    kind = "Event" if work.work_ref.work_kind == "event" else "Support Process"
    print(f"{kind} — exact {work.work_ref.work_id}")
    print()
    if not entries:
        print("No prior teacher-reference exports are recorded for this exact work.")
    else:
        print(
            "Listed newest first for navigation only; chronological order does not "
            "make any export current, official, active, or best."
        )
        print()
        for entry in entries:
            for line in _history_line(entry):
                print(line)
            print()
    print(
        "History verification is read-only. Missing or mismatched historical bytes "
        "are reported, never regenerated here."
    )
    print()
    pause_for_user()


def launch_teacher_reference_work_menu(
    state: MenuSessionContext,
    root: Path,
    student: StudentOption,
    work: StudentWorkTimelineView,
    *,
    show_current: Callable[[], None],
    clock: MenuClock | None = None,
    id_generator: PortiaIdGenerator | None = None,
    deployment_instance_id: str = _DEPLOYMENT_INSTANCE_ID,
    process_instance_id: str | None = None,
) -> None:
    """Open contextual export/history actions for one exact current work item."""

    active_clock = clock or MenuClock()
    process_id = process_instance_id or f"pid_{os.getpid()}"
    show_current()

    while True:
        clear_screen()
        print_menu_header("View Timeline — Current Work")
        kind = "Event" if work.work_ref.work_kind == "event" else "Support Process"
        print(f"{kind} — exact {work.work_ref.work_id}")
        print(f"Selected student: {student.display_name} — {student.class_id}")
        print()
        print("1. View current work details")
        print("2. Export this work for teacher reference")
        if work.focal_participant_refs:
            print("3. Export this student's view of this work")
        else:
            print("3. Export this student's view — unavailable")
        print("4. View prior exports for this work")
        print_navigation()
        print()
        raw = input("Select an option: ").strip()
        navigation = parse_menu_navigation(raw)
        if navigation is PortiaMenuChoice.HELP:
            clear_screen()
            print_menu_header("View Timeline — Teacher Reference Help")
            print(
                "A teacher-reference export is a deliberate local artifact for your "
                "own reference. It is not an official record, disclosure "
                "authorization, delivery record, or institutional filing. Creating "
                "it does not by itself authorize disclosure, delivery, filing, "
                "sharing, or receipt."
            )
            print(
                "Whole-work export uses teacher_current scope. The selected-student "
                "option uses one exact participant record from this work only; it "
                "does not create a student-global dossier."
            )
            print(
                "Preparation and preview are read-only. No export operation begins "
                "until you review the exact outgoing HTML and type EXPORT exactly."
            )
            print()
            pause_for_user()
            continue
        if navigation is NavigationChoice.BACK:
            return
        if raw == "1":
            show_current()
            continue
        if raw == "4":
            try:
                _show_history(root, work)
            except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError) as exc:
                clear_screen()
                print_menu_header("Teacher Reference History — Unable to Display")
                print(str(exc))
                print()
                pause_for_user()
            continue
        if raw in {"2", "3"}:
            if raw == "3" and not work.focal_participant_refs:
                print(
                    "Participant-specific export is unavailable because this student "
                    "has no exact focal participant in the selected work."
                )
                pause_for_user()
                continue
            try:
                _run_export(
                    state,
                    root,
                    work,
                    participant_specific=(raw == "3"),
                    clock=active_clock,
                    id_generator=id_generator,
                    deployment_instance_id=deployment_instance_id,
                    process_instance_id=process_id,
                )
            except CancelMenuAction:
                continue
            except (
                PortiaLocalValidationError,
                PortiaStorageError,
                TypeError,
                ValueError,
            ) as exc:
                clear_screen()
                print_menu_header("Export Teacher Reference — Unable to Prepare")
                print(str(exc))
                print()
                pause_for_user()
            continue
        print(navigation_hint_with_help())
        pause_for_user()


__all__ = ["launch_teacher_reference_work_menu"]
