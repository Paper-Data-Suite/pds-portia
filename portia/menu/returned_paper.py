"""Guided one-file returned-paper intake with per-page Needs Attention review.

Choosing a file never infers a class or student. Core retains source bytes;
only verified Portia pages become operational receipts, not domain facts.
"""

from __future__ import annotations

from pathlib import Path

from portia.intake.recovery import RetainedRecoveryError
from portia.intake.retention import IntakeSourceError
from portia.intake.teacher import (
    TeacherPageResult,
    TeacherReturnedPaperService,
    TeacherSourceResult,
)
from portia.menu.capture_forms import LocalWorkspaceCaptureAuthority
from portia.menu.context import MenuSessionContext
from portia.menu.prompts import CancelMenuAction, confirm_write, prompt_text, select_one
from portia.menu.ui import clear_screen, pause_for_user, print_menu_header
from portia.storage.errors import PortiaStorageError

_STATUS_LABELS = {
    "recorded": "Recorded",
    "already_recorded": "Already recorded",
    "needs_attention": "Needs attention",
    "retryable": "Retryable",
    "conflict": "Conflict - inspect before retry",
}
_SOURCE_ERROR_LABELS = {
    "invalid_path": "The selected path is not valid",
    "unsafe_path": "The source path uses an unsafe link or alias",
    "source_unavailable": "The selected file cannot be read",
    "source_changed": "The source file changed during intake; use a stable scan",
    "source_rejected": "The source type, header or file size is not supported",
    "unsupported_content": "The file content is unsupported",
    "invalid_document": "The PDF/image is malformed or cannot be decoded safely",
    "protected_document": "Encrypted or password-protected PDF files are unsupported",
    "too_many_pages": "The PDF exceeds the page-count safety limit",
    "page_too_large": "The page exceeds the pixel safety limit",
    "retention_failed": "Core could not retain the original source",
    "retained_integrity_failure": "Core-retained source verification needs attention",
}
_REASON_LABELS = {
    "missing_qr": "No QR code was found; check the page or rescan",
    "unreadable_qr": "A QR code could not be read; rescan this sheet",
    "ambiguous_qr": "More than one code was found; review the sheet",
    "invalid_qr": "The QR code is not a valid PDS2 page locator",
    "foreign_module": "This page belongs to another PDS module",
    "render_failed": "The page could not be inspected safely",
    "authorization_denied": "Class access is not authorized",
    "batch_unavailable": "The saved capture packet could not be found",
    "batch_cancelled": "This capture packet was cancelled",
    "route_unavailable": "The page's registered route is unavailable",
    "route_inactive": "The page route is no longer active",
    "registration_conflict": "The QR route and saved registration disagree",
    "target_unavailable": "The original Page Target could not be found",
    "target_conflict": "The original Page Target does not match",
    "route_error": "Route verification could not be completed",
    "operation_lock_requires_recovery": "An interrupted operation needs review",
    "persistence_interrupted": "Saving this page was interrupted; retry",
    "persisted_state_conflict": "Saved Page Record history conflicts; inspect it",
    "page_discovery_unavailable": "Page discovery interrupted; original source remains retained",
    "route_verification_unavailable": "Routing interrupted; retained source can be retried",
    "page_receipts_need_recovery": "Saving interrupted; some page receipts may already exist",
    "received": "Page recorded for later review",
}


def _show(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _page_label(page: TeacherPageResult) -> str:
    label = _STATUS_LABELS[page.status]
    form = (
        page.form_name.replace("_", " ").title()
        if page.form_name is not None
        else "Unresolved form"
    )
    return f"Source page {page.identity.source_page_number}: {label} - {form}"


def _show_page(page: TeacherPageResult) -> None:
    lines = [
        f"Original source page: {page.identity.source_page_number}",
        f"Outcome: {_STATUS_LABELS[page.status]}",
        _REASON_LABELS.get(page.reason, "Further review is required"),
    ]
    if page.class_id is not None:
        lines.append(f"Verified class: {page.class_id}")
    if page.form_name is not None:
        lines.append(f"Original form: {page.form_name.replace('_', ' ').title()}")
    if page.page_target_index is not None:
        lines.append(f"Page Target index: {page.page_target_index}")
    if page.template_page_ordinal is not None:
        lines.append(f"Printed form page: {page.template_page_ordinal}")
    if page.receipt_id is not None:
        lines.append("Page Record: saved and verified")
    lines.append("No scanned handwriting or student claim has been accepted.")
    _show("Returned Paper - Page Details", tuple(lines))


def _review(result: TeacherSourceResult) -> None:
    original = result.source.core_source.source_filename
    state = {
        "completed": "Completed",
        "completed_with_exceptions": "Completed with exceptions",
        "retained_needs_attention": "Retained - needs attention",
    }[result.status]
    _show(
        "Returned Paper - Source Summary",
        (
            f"Original file: {original}",
            f"Status: {state}",
            f"Source pages: {len(result.pages)}",
            f"Saved or previously recorded pages: {result.accepted}",
            f"Pages needing attention: {result.requires_attention}",
            "Source PDF/image bytes remain in Core custody.",
            "Page Records do not confirm observations or other behavior facts.",
        ),
    )
    try:
        selection = select_one(
            "Returned Paper - Pages and Needs Attention",
            (*result.pages, None),
            (*(_page_label(page) for page in result.pages), "Return to Portia"),
            help_text=(
                "Pages are numbered as scanned, not by printed form order. "
                "Select a page for status and recommended follow-up. "
                "N/P switch pages; B/M/Q retain their usual navigation meaning."
            ),
        )
    except CancelMenuAction:
        return
    if selection is not None:
        _show_page(selection)


def _choose_file() -> Path:
    raw = prompt_text(
        "Scan / Import Returned Paper",
        "PDF, JPEG or PNG file",
        help_text=(
            "Scan the whole stack to ONE PDF and paste its path here. "
            "A file in your scanner inbox can also be selected by full path. "
            "JPEG and PNG photographs are supported; TIFF is not."
        ),
    )
    if raw is None:
        raise ValueError("A source path is required")
    if len(raw) > 4096:
        raise ValueError("The source path is too long")
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        raw = raw[1:-1]
    return Path(raw).expanduser()


def launch_returned_paper_menu(
    state: MenuSessionContext,
    *,
    service: TeacherReturnedPaperService | None = None,
) -> None:
    """Process or retry one file; no manual PDF splitting or route assignment."""
    try:
        root = state.resolve_workspace()
        gateway = service or TeacherReturnedPaperService(
            root, authorization=LocalWorkspaceCaptureAuthority(root)
        )
        options = ["new", "recover"]
        labels = [
            "Choose one returned PDF/image or scanner-inbox file",
            "Resume a previously Core-retained scan (after restart)",
        ]
        if state.last_retained_paper is not None:
            options.append("retry")
            labels.append("Retry the last Core-retained source (no duplicate scan)")
        choice = select_one(
            "Scan / Import Returned Paper",
            tuple(options),
            tuple(labels),
            help_text=(
                "One PDF may contain many independently routed Portia forms. "
                "An unreadable page stays under Core custody for follow-up."
            ),
        )
        if choice == "retry":
            assert state.last_retained_paper is not None
            result = gateway.resume_retained(state.last_retained_paper)
        elif choice == "recover":
            prior = gateway.recent_retained()
            if not prior:
                _show(
                    "Returned Paper - Recovery",
                    (
                        "There are no compatible prior Core-retained scans.",
                        "You can select a new returned file instead.",
                    ),
                )
                return
            chosen = select_one(
                "Returned Paper - Resume Prior Scan",
                prior,
                tuple(item.label for item in prior),
                help_text="Recheck exact Core bytes before processing. No second intake event.",
            )
            result = gateway.resume_recovered(chosen)
        else:
            path = _choose_file()
            preflight = gateway.inspect(path)
            if not confirm_write(
                "Scan / Import - Confirm Core Retention",
                "RETAIN",
                (
                    f"File: {preflight.original_path.name}",
                    f"Pages: {preflight.page_count}",
                    f"Format: {preflight.source_format.value.upper()}",
                    "The original will be durably retained in Core.",
                    "Verified Portia pages receive operational Page Records.",
                    "No behavior records or handwriting interpretations are created.",
                ),
                help_text="Core custody is retained even if some pages later fail.",
            ):
                return
            result = gateway.process_file(path)
        state.last_retained_paper = result.source
        _review(result)
    except CancelMenuAction:
        return
    except RetainedRecoveryError:
        _show(
            "Returned Paper - Recovery Needs Attention",
            (
                "The retained scan did not pass Core provenance or content checks.",
                "No Core original was removed or rewritten.",
                "Review the retained scan or choose a new source file.",
            ),
        )
    except IntakeSourceError as exc:
        _show(
            "Returned Paper - File Needs Attention",
            (
                _SOURCE_ERROR_LABELS.get(exc.code, "The scan could not be accepted"),
                "If retention began, the original may already be in Core custody.",
                "Correct the source problem before trying again.",
            ),
        )
    except (ValueError, TypeError, OSError, RuntimeError, PortiaStorageError) as exc:
        # Do not print exception strings: filesystem paths, scanner filenames
        # and route details can contain unnecessary protected information.
        _show(
            "Returned Paper - Needs Attention",
            (
                "The source was not accepted as a completed intake.",
                "If retention began, the original may already be in Core custody.",
                "Review the selected file and retry explicitly; do not delete retained bytes.",
                f"Diagnostic type: {type(exc).__name__}",
            ),
        )
