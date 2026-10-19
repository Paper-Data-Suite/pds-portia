"""#60 Slice 6A: source-wide teacher staging of existing returned-page receipts.

One Core-retained source may contain many distinct Capture Batches/classes.
Every page is independently authorized and verified against its saved receipt
before interpreting; no raw QR, menu-supplied identity or filename is authority.
Interpretations and proposals remain noncanonical, requiring #61 review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from portia.capture.contracts import CaptureAuthorization
from portia.intake.capture_proposal_persistence import (
    CaptureProposalPersistenceError,
    FileCaptureProposalPersistenceService,
)
from portia.intake.capture_proposal_planning import ProposalPlanningError
from portia.intake.historical_page_regions import HistoricalPageError
from portia.intake.interpretation_generations import (
    FilePaperInterpretationGenerationService,
    InterpretationGenerationError,
    _require_same_page,
)
from portia.intake.interpretation_history import FilePaperInterpretationHistoryService
from portia.intake.interpretation_profiles import LOCAL_MARKS_V1
from portia.intake.local_mark_candidates import LocalRecognitionError
from portia.intake.teacher import TeacherSourceResult
from portia.storage.errors import PortiaStorageError

StagePageStatus = Literal[
    "review_required", "needs_attention", "retryable", "conflict", "access_denied"
]
_ACCEPTED = frozenset({"recorded", "already_recorded"})
_MAX_PAGES = 128


@dataclass(frozen=True, slots=True)
class TeacherStagedPage:
    """Privacy-minimized per-physical-page outcome; no candidate literal."""

    source_page_number: int
    status: StagePageStatus
    reason: str
    interpretation_id: str | None = None
    generation: int | None = None
    proposals_created: int = 0
    proposals_reused: int = 0
    attention_entries: int = 0

    def __post_init__(self) -> None:
        if type(self.source_page_number) is not int or self.source_page_number < 1:
            raise ValueError("invalid_staging_page_number")
        if not self.reason or len(self.reason) > 80 or not self.reason.isascii():
            raise ValueError("invalid_staging_status_code")
        if any(
            char not in "abcdefghijklmnopqrstuvwxyz_0123456789" for char in self.reason
        ):
            raise ValueError("invalid_staging_status_code")
        if (self.interpretation_id is None) != (self.generation is None):
            raise ValueError("incomplete_staging_generation_reference")
        if self.generation is not None and (
            type(self.generation) is not int or self.generation < 1
        ):
            raise ValueError("invalid_staging_generation")
        if any(
            type(n) is not int or n < 0
            for n in (
                self.proposals_created,
                self.proposals_reused,
                self.attention_entries,
            )
        ):
            raise ValueError("invalid_staging_counts")
        if self.status in {"review_required", "needs_attention"} and (
            self.interpretation_id is None
        ):
            # Unaccepted pages legitimately need attention but have no generation.
            if (
                self.proposals_created
                or self.proposals_reused
                or self.attention_entries
            ):
                raise ValueError("unaccepted_page_claimed_staging_counts")
        if self.status in {"retryable", "conflict", "access_denied"} and (
            self.interpretation_id is not None
            or self.proposals_created
            or self.proposals_reused
            or self.attention_entries
        ):
            raise ValueError("failed_page_claimed_staging_success")
        if self.status == "review_required" and not (
            self.proposals_created + self.proposals_reused
        ):
            raise ValueError("review_required_without_proposal")

    @property
    def requires_human_review(self) -> bool:
        return self.proposals_created + self.proposals_reused > 0

    def summary(self) -> dict[str, object]:
        return {
            "source_page_number": self.source_page_number,
            "status": self.status,
            "reason": self.reason,
            "generation": self.generation,
            "proposals_created": self.proposals_created,
            "proposals_reused": self.proposals_reused,
            "needs_attention_entries": self.attention_entries,
            "requires_human_review": self.requires_human_review,
        }


@dataclass(frozen=True, slots=True)
class TeacherStagingSummary:
    """One outcome per original physical source page, in original order."""

    pages: tuple[TeacherStagedPage, ...] = field(repr=False)

    @property
    def staged_pages(self) -> int:
        return sum(item.interpretation_id is not None for item in self.pages)

    @property
    def needs_attention_pages(self) -> int:
        return sum(item.status != "review_required" for item in self.pages)

    def summary(self) -> dict[str, object]:
        return {
            "source_pages": len(self.pages),
            "staged_pages": self.staged_pages,
            "needs_attention_pages": self.needs_attention_pages,
            "proposals_created": sum(item.proposals_created for item in self.pages),
            "proposals_reused": sum(item.proposals_reused for item in self.pages),
            "human_review_required": any(
                item.requires_human_review for item in self.pages
            ),
            "pages": [item.summary() for item in self.pages],
        }


class FileTeacherPaperStagingService:
    """After #59 receipt intake, stage each verified page without re-retention.

    The menu/result work ID is a lookup hint only. Saved Page Record, PDS2 route,
    Core custody, source-page identity and historical layout are rechecked by
    the protected services before any immutable staging write. Existing manual
    interpretations are preserved; a replay never overwrites them with OMR.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.generations = FilePaperInterpretationGenerationService(workspace_root)
        self.history = FilePaperInterpretationHistoryService(workspace_root)
        self.proposals = FileCaptureProposalPersistenceService(workspace_root)

    def stage_source(
        self,
        result: TeacherSourceResult,
        *,
        authorization: CaptureAuthorization,
    ) -> TeacherStagingSummary:
        if not isinstance(result, TeacherSourceResult):
            raise TypeError("verified_teacher_source_result_required")
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted_capture_authorization_required")
        if not 1 <= len(result.pages) <= _MAX_PAGES:
            raise ValueError("invalid_source_page_inventory")
        output: list[TeacherStagedPage] = []
        seen: set[tuple[str, str, str]] = set()
        for index, item in enumerate(result.pages, 1):
            if item.identity != result.source.page_identity(index):
                raise ValueError("physical_source_inventory_changed")
            number = item.identity.source_page_number
            if item.status not in _ACCEPTED:
                output.append(
                    TeacherStagedPage(number, "needs_attention", "page_not_recorded")
                )
                continue
            if not item.class_id or not item.work_id or not item.receipt_id:
                output.append(
                    TeacherStagedPage(
                        number, "needs_attention", "receipt_work_unavailable"
                    )
                )
                continue
            key = (item.class_id, item.work_id, item.receipt_id)
            if key in seen:
                output.append(
                    TeacherStagedPage(number, "conflict", "duplicate_receipt_in_source")
                )
                continue
            seen.add(key)
            try:
                authorization.require_access(
                    item.class_id, "capture_interpretation.teacher_stage"
                )
                first = self.generations.pages.resolve(
                    item.class_id,
                    item.work_id,
                    item.receipt_id,
                    authorization=authorization,
                    profile_identity=LOCAL_MARKS_V1.wire_identity(),
                )
                if (
                    first.retained.page_identity(first.source_page_number)
                    != item.identity
                ):
                    raise HistoricalPageError("source_page_identity_conflict")
                previous = self.history.history(
                    item.class_id,
                    item.work_id,
                    item.receipt_id,
                    authorization=authorization,
                )
                if previous.latest is None:
                    selected = self.generations.stage_marks(
                        item.class_id,
                        item.work_id,
                        item.receipt_id,
                        authorization=authorization,
                    ).record
                else:
                    # Derived latest immutable generation; do not re-run an old
                    # mark profile over an existing assisted manual generation.
                    selected = previous.latest
                identifier = selected.logical_id
                generation = selected.field("generation")
                if identifier is None or type(generation) is not int:
                    raise InterpretationGenerationError("invalid_selected_generation")
                last = self.generations.pages.resolve(
                    item.class_id,
                    item.work_id,
                    item.receipt_id,
                    authorization=authorization,
                    profile_identity=LOCAL_MARKS_V1.wire_identity(),
                )
                _require_same_page(first, last)
                proposed = self.proposals.stage(
                    item.class_id,
                    item.work_id,
                    item.receipt_id,
                    identifier,
                    generation,
                    authorization=authorization,
                )
                if selected.field("interpretation_status") == "partial":
                    state: StagePageStatus = "needs_attention"
                    reason = "partial_interpretation"
                elif proposed.attention_entries or not (
                    proposed.created + proposed.reused
                ):
                    state = "needs_attention"
                    reason = "unresolved_proposal_mapping"
                else:
                    state = "review_required"
                    reason = "candidate_review_required"
                output.append(
                    TeacherStagedPage(
                        number,
                        state,
                        reason,
                        identifier,
                        generation,
                        proposed.created,
                        proposed.reused,
                        proposed.attention_entries,
                    )
                )
            except PermissionError:
                output.append(
                    TeacherStagedPage(number, "access_denied", "class_access_denied")
                )
            except PortiaStorageError:
                output.append(
                    TeacherStagedPage(
                        number, "conflict", "persisted_history_needs_recovery"
                    )
                )
            except HistoricalPageError:
                output.append(
                    TeacherStagedPage(
                        number, "conflict", "source_or_route_verification_failed"
                    )
                )
            except (InterpretationGenerationError, LocalRecognitionError):
                output.append(
                    TeacherStagedPage(
                        number, "needs_attention", "field_interpretation_unavailable"
                    )
                )
            except (ProposalPlanningError, CaptureProposalPersistenceError):
                output.append(
                    TeacherStagedPage(
                        number, "needs_attention", "proposal_mapping_unavailable"
                    )
                )
            except (OSError, ValueError, RuntimeError):
                # No source text, paths or exception strings in teacher reports.
                # A post-write unknown is recovered through immutable replay.
                output.append(
                    TeacherStagedPage(number, "retryable", "staging_interrupted")
                )
        return TeacherStagingSummary(tuple(output))
