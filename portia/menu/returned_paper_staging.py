"""#60 Slice 6B: optional teacher confirmation and source-wide staging display.

This is a UI adapter only. The Slice 6A service reauthorizes original source
and Page Records per page; the menu never supplies candidate content or facts.
No Capture Review or canonical behavior record is created here.
"""

from __future__ import annotations

from pathlib import Path

from portia.capture.contracts import CaptureAuthorization
from portia.intake.teacher import TeacherSourceResult
from portia.intake.teacher_staging import (
    FileTeacherPaperStagingService,
    TeacherStagedPage,
    TeacherStagingSummary,
)
from portia.menu.prompts import CancelMenuAction, confirm_write, select_one
from portia.menu.ui import clear_screen, pause_for_user, print_menu_header

_STATUS = {
    "review_required": "Ready for human review",
    "needs_attention": "Needs attention",
    "retryable": "Retryable - inspect before retry",
    "conflict": "Conflict - recovery required",
    "access_denied": "Access denied",
}
_NEXT_ACTION = {
    "candidate_review_required": "Review proposals individually when Capture Review is available (#61).",
    "partial_interpretation": "Some text or marks could not be interpreted; manual follow-up is required.",
    "unresolved_proposal_mapping": "No exact mapping is qualified for some entries; resolve them manually.",
    "page_not_recorded": "Inspect the original intake page status or rescan this sheet.",
    "receipt_work_unavailable": "The saved Capture Batch locator is unavailable; inspect intake history.",
    "duplicate_receipt_in_source": "The same Page Record appeared twice; inspect source routing.",
    "class_access_denied": "Access for the verified class is unavailable; do not bypass it.",
    "persisted_history_needs_recovery": "Inspect immutable record history before retrying.",
    "source_or_route_verification_failed": "Check Core custody and the original page route before retrying.",
    "field_interpretation_unavailable": "A field or page could not be measured; preserve source for manual handling.",
    "proposal_mapping_unavailable": "An exact mapping could not be established; preserve staging history.",
    "staging_interrupted": "Some writes may exist; resume the same retained scan to reconcile.",
}


def _display(title: str, lines: tuple[str, ...]) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _page_label(page: TeacherStagedPage) -> str:
    return (
        f"Source page {page.source_page_number}: {_STATUS[page.status]} "
        f"- {page.proposals_created + page.proposals_reused} proposal(s)"
    )


def _show_page(page: TeacherStagedPage) -> None:
    lines = (
        f"Original source page: {page.source_page_number}",
        f"Staging status: {_STATUS[page.status]}",
        f"Proposals created: {page.proposals_created}",
        f"Proposals reused: {page.proposals_reused}",
        f"Entries requiring attention: {page.attention_entries}",
        f"Next action: {_NEXT_ACTION.get(page.reason, 'Inspect this page before retrying.')}",
        "Source candidates and proposals are not confirmed facts.",
        "No Capture Review or canonical behavior record was created.",
    )
    _display("Returned Paper - Staging Page Details", lines)


def _review_staging(source: TeacherSourceResult, staged: TeacherStagingSummary) -> None:
    """Show all physical pages without revealing scan text, paths or identities."""
    if (
        not isinstance(staged, TeacherStagingSummary)
        or len(source.pages) != len(staged.pages)
        or any(
            observed.identity.source_page_number != candidate.source_page_number
            for observed, candidate in zip(source.pages, staged.pages, strict=True)
        )
    ):
        raise ValueError("teacher_staging_source_order_conflict")
    totals = staged.summary()
    _display(
        "Returned Paper - Staging Summary",
        (
            f"Original source pages: {totals['source_pages']}",
            f"Pages with interpretation history: {totals['staged_pages']}",
            f"Pages needing attention: {totals['needs_attention_pages']}",
            f"New Capture Proposals: {totals['proposals_created']}",
            f"Reused Capture Proposals: {totals['proposals_reused']}",
            "Candidates and proposals require separate human review (#61).",
            "Even a complete interpretation is not a verified account of events.",
            "The original scan remains in Core custody.",
        ),
    )
    try:
        selection = select_one(
            "Returned Paper - Staging Pages",
            (*staged.pages, None),
            (*(_page_label(page) for page in staged.pages), "Return to Portia"),
            help_text=(
                "Results follow physical scan page order. Select one for its "
                "status and next action. N/P paginate; B/M/Q navigate."
            ),
        )
    except CancelMenuAction:
        return
    if selection is not None:
        _show_page(selection)


def offer_stage(
    source: TeacherSourceResult,
    workspace_root: str | Path,
    *,
    authorization: CaptureAuthorization,
    service: FileTeacherPaperStagingService | None = None,
) -> None:
    """No recognition/proposal write until explicit uppercase STAGE.

    Declining leaves the already retained original and Page Records unchanged.
    A staging error is reported by the caller because earlier pages may have
    succeeded and no all-or-nothing transaction is claimed.
    """
    if not isinstance(source, TeacherSourceResult):
        raise TypeError("verified_source_required")
    if source.accepted == 0:
        return
    confirmed = confirm_write(
        "Returned Paper - Confirm Candidate Staging",
        "STAGE",
        (
            f"Original source pages: {len(source.pages)}",
            f"Verified Page Records: {source.accepted}",
            f"Pages requiring intake follow-up: {source.requires_attention}",
            "Recheck existing Core-retained pages; do NOT retain a second scan.",
            "Create/reuse immutable interpretation candidates and eligible proposals.",
            "Unreadable text/uncertain marks and unmapped entries need attention.",
            "No teacher approval, person matching or canonical records are created.",
        ),
        help_text=(
            "You may cancel without changing interpretations or proposals. "
            "STAGE checks each verified page independently; a partial result "
            "does not count as review or acceptance."
        ),
    )
    if not confirmed:
        return
    worker = service or FileTeacherPaperStagingService(workspace_root)
    staged = worker.stage_source(source, authorization=authorization)
    _review_staging(source, staged)
