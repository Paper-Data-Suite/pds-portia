"""#60 Slice 4A: immutable, receipt-scoped Paper Interpretation generations.

This writer stores staging candidates only. It never accepts caller-built wire
records, writes canonical facts, changes Page Records, or creates reviews.
Every persisted/reused generation is anchored in an authorized #59 receipt,
verified Core retained bytes and an exact historical capture layout.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping, cast

from pds_core.routes import safe_module_work_descendant

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import CapturePageSpec, resolve_capture_page_spec
from portia.intake.historical_page_regions import (
    AuthorizedHistoricalPage,
    FileHistoricalPageRegionService,
)
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_MARKS_V1,
    InterpretationProfile,
    resolve_interpretation_profile,
)
from portia.intake.local_mark_candidates import (
    FieldCandidate,
    FileLocalMarkCandidateService,
    LocalPageCandidates,
)
from portia.intake.manual_text_candidates import (
    FileManualTextCandidateService,
    ManualTextSelection,
)
from portia.models import PaperInterpretationV1
from portia.models.errors import PortiaModelError
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaPathError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes

_INTERPRETATION_ID = re.compile(r"pint_[a-f0-9]{40}\Z")
_MAX_HISTORY = 4096
_MAX_BYTES = 1_000_000
_MAX_LIMITATIONS = 32


class InterpretationGenerationError(ValueError):
    """Stable non-sensitive processing error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class InterpretationGenerationResult:
    disposition: Literal["created", "reused"]
    record: PaperInterpretationV1


def _identity(page_record_id: str, profile: InterpretationProfile) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes([page_record_id, profile.wire_identity()])
    ).hexdigest()
    return "pint_" + digest[:40]


def _parse(path: Path) -> PaperInterpretationV1:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError("duplicate interpretation key")
            output[key] = value
        return output

    def reject_constant(value: str) -> None:
        raise ValueError("nonfinite interpretation JSON")

    content = read_bytes(path)
    if len(content) > _MAX_BYTES:
        raise PortiaCorruptionError("interpretation_size_limit")
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=reject_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("interpretation must be object")
        return PaperInterpretationV1(value)
    except (ValueError, TypeError, UnicodeError, PortiaModelError) as exc:
        raise PortiaCorruptionError("invalid_saved_paper_interpretation") from exc


def _check_fields(
    result: LocalPageCandidates, spec: CapturePageSpec, profile: InterpretationProfile
) -> None:
    """Application-level exact historical field and candidate validation."""
    if (
        not isinstance(result, LocalPageCandidates)
        or result.profile is not profile
        or result.layout_fingerprint != spec.layout_fingerprint
        or result.registration_method
        not in {
            "measured_sheet_boundary_and_exact_qr_v1",
            "measured_fullframe_qr_and_field_frames_v1",
        }
        or len(result.entries) != len(spec.entries)
    ):
        raise InterpretationGenerationError("candidate_lineage_or_profile_conflict")
    if (
        len(result.limitation_codes) > _MAX_LIMITATIONS
        or len(set(result.limitation_codes)) != len(result.limitation_codes)
        or any(
            not re.fullmatch(r"[a-z][a-z0-9_]*", code)
            for code in result.limitation_codes
        )
    ):
        raise InterpretationGenerationError("invalid_limitation_codes")
    for candidate_entry, declared_entry in zip(
        result.entries, spec.entries, strict=True
    ):
        if candidate_entry.entry_key != declared_entry.entry_key or len(
            candidate_entry.fields
        ) != len(declared_entry.fields):
            raise InterpretationGenerationError("historical_entry_inventory_conflict")
        detected = False
        unreadable = False
        for candidate, declared in zip(
            candidate_entry.fields, declared_entry.fields, strict=True
        ):
            if not isinstance(candidate, FieldCandidate) or (
                candidate.field_key != declared.field_key
                or candidate.region_key != declared.region_key
            ):
                raise InterpretationGenerationError(
                    "historical_field_inventory_conflict"
                )
            if declared.field_type == "choice":
                if candidate.capture_method != "mark_recognition":
                    raise InterpretationGenerationError("mark_method_conflict")
                if (
                    candidate.literal is not None
                    and candidate.literal not in declared.choices
                ):
                    raise InterpretationGenerationError("unknown_mark_token")
                if any(
                    token not in declared.choices for token in candidate.alternatives
                ):
                    raise InterpretationGenerationError("unknown_mark_alternative")
                if candidate.state == "blank":
                    raise InterpretationGenerationError("unchecked_not_blank")
            else:
                expected = (
                    "manual_transcription"
                    if candidate.capture_method == "manual_transcription"
                    else declared.capture_method
                )
                if candidate.capture_method != expected or candidate.state in {
                    "unmarked",
                    "ambiguous",
                }:
                    raise InterpretationGenerationError("text_method_or_state_conflict")
                if candidate.capture_method == "manual_transcription":
                    if profile is not LOCAL_ASSISTED_MARKS_V1:
                        raise InterpretationGenerationError("manual_profile_required")
                    if candidate.state != "candidate_detected" or (
                        candidate.literal is None
                        or declared.max_characters is None
                        or len(candidate.literal) > declared.max_characters
                    ):
                        raise InterpretationGenerationError("manual_field_invalid")
                elif candidate.state != "unreadable":
                    raise InterpretationGenerationError("unqualified_text_provider")
            if candidate.state in {"candidate_detected", "ambiguous"}:
                detected = True
            if candidate.state == "unreadable":
                unreadable = True
        expected_entry = (
            "candidate" if detected else "unreadable" if unreadable else "blank"
        )
        if candidate_entry.state != expected_entry:
            raise InterpretationGenerationError("entry_state_conflicts_with_fields")
        if expected_entry == "unreadable" and not result.limitation_codes:
            raise InterpretationGenerationError("unreadable_requires_limitation")


def _require_same_page(
    a: AuthorizedHistoricalPage, b: AuthorizedHistoricalPage
) -> None:
    if (
        a.class_id != b.class_id
        or a.work_id != b.work_id
        or a.page_record_id != b.page_record_id
        or a.source_page_number != b.source_page_number
        or a.receipt.to_dict() != b.receipt.to_dict()
        or a.plan != b.plan
        or a.retained.page_identity(a.source_page_number)
        != b.retained.page_identity(b.source_page_number)
    ):
        raise InterpretationGenerationError("page_authority_changed")


class FilePaperInterpretationGenerationService:
    """Versioned, never-overwritten staging records beneath Capture Batches."""

    def __init__(self, root: str | Path) -> None:
        self.pages = FileHistoricalPageRegionService(root)
        self.marks = FileLocalMarkCandidateService(root)
        self.manual = FileManualTextCandidateService(root)
        self.batches = self.pages.receipts.batches
        self.root = self.batches.root

    def _collection(self, class_id: str, work_id: str) -> Path:
        return self.batches._safe(
            safe_module_work_descendant(
                self.root,
                self.batches._work(class_id, work_id),
                "records/paper_interpretation",
            )
        )

    def _inventory(
        self, class_id: str, work_id: str
    ) -> tuple[PaperInterpretationV1, ...]:
        folder = self._collection(class_id, work_id)
        if not folder.exists():
            if folder.is_symlink():
                raise PortiaPathError("unsafe_interpretation_collection")
            return ()
        if not folder.is_dir():
            raise PortiaCorruptionError("interpretation_collection_not_directory")
        children = tuple(folder.iterdir())
        if len(children) > _MAX_HISTORY:
            raise PortiaCorruptionError("interpretation_inventory_limit")
        records: list[PaperInterpretationV1] = []
        names: set[str] = set()
        for path in sorted(children, key=lambda item: item.name):
            self.batches._safe(path)
            if (
                not path.is_file()
                or path.suffix != ".json"
                or _INTERPRETATION_ID.fullmatch(path.stem) is None
                or path.name.casefold() in names
            ):
                raise PortiaCorruptionError("interpretation_inventory_invalid")
            names.add(path.name.casefold())
            saved = _parse(path)
            data = saved.to_dict()
            profile_wire = data["interpreter_profile"]
            try:
                profile = resolve_interpretation_profile(
                    cast(Mapping[str, object], profile_wire)
                )
            except ValueError as exc:
                raise PortiaCorruptionError(
                    "unknown_persisted_interpreter_profile"
                ) from exc
            if (
                saved.class_id != class_id
                or saved.work_id != work_id
                or saved.logical_id != path.stem
                or saved.module_id != "portia"
                or saved.record_type != "paper_interpretation"
                or path.stem != _identity(cast(str, data["page_record_id"]), profile)
            ):
                raise PortiaCorruptionError("interpretation_identity_conflict")
            records.append(saved)
        return tuple(records)

    @staticmethod
    def _lineage(
        saved: PaperInterpretationV1,
        page: AuthorizedHistoricalPage,
        profile: InterpretationProfile,
    ) -> None:
        data = saved.to_dict()
        if (
            data.get("page_record_id") != page.page_record_id
            or data.get("page_target_id") != page.receipt.field("page_target_id")
            or data.get("layout_snapshot") != dict(page.plan.layout.layout_identity)
            or data.get("interpreter_profile") != profile.wire_identity()
        ):
            raise PortiaCorruptionError("interpretation_historical_lineage_conflict")

    def _commit(
        self,
        page: AuthorizedHistoricalPage,
        profile: InterpretationProfile,
        candidate: LocalPageCandidates,
        actor: Mapping[str, object],
        *,
        authorization: CaptureAuthorization,
    ) -> InterpretationGenerationResult:
        """Same-profile exact replay; changed profile appends a new generation."""
        spec = resolve_capture_page_spec(dict(page.plan.layout.layout_identity))
        _check_fields(candidate, spec, profile)
        if candidate.source_page_number != page.source_page_number:
            raise InterpretationGenerationError("physical_source_page_conflict")
        # Rechecks inside the same lock that excludes batch transitions and
        # concurrent writers. No prior generation or Page Record is rewritten.
        with self.batches._lifecycle_lock(page.class_id, page.work_id):
            refreshed = self.pages.resolve(
                page.class_id,
                page.work_id,
                page.page_record_id,
                authorization=authorization,
                profile_identity=profile.wire_identity(),
            )
            _require_same_page(page, refreshed)
            records = self._inventory(page.class_id, page.work_id)
            ours = [
                r for r in records if r.field("page_record_id") == page.page_record_id
            ]
            known: set[int] = set()
            replay: PaperInterpretationV1 | None = None
            for record in ours:
                version = record.field("generation")
                if (
                    not isinstance(version, int)
                    or isinstance(version, bool)
                    or version in known
                ):
                    raise PortiaCorruptionError("duplicate_interpretation_generation")
                known.add(version)
                registered_profile = resolve_interpretation_profile(
                    cast(Mapping[str, object], record.to_dict()["interpreter_profile"])
                )
                self._lineage(record, refreshed, registered_profile)
                if record.logical_id == _identity(page.page_record_id, profile):
                    if replay is not None:
                        raise PortiaCorruptionError("duplicate_interpretation_profile")
                    replay = record
                elif registered_profile == profile:
                    raise PortiaCorruptionError("same_profile_duplicate_identity")
            if known != set(range(1, len(known) + 1)):
                raise PortiaCorruptionError("interpretation_generation_history_gap")
            if replay is not None:
                old = replay.to_dict()
                if (
                    old["entries"] != candidate.entry_map()
                    or old["limitation_codes"] != list(candidate.limitation_codes)
                    or old["interpretation_status"] != candidate.interpretation_status
                ):
                    raise PortiaConflictError("same_profile_changed_candidates")
                return InterpretationGenerationResult("reused", replay)
            if len(records) >= _MAX_HISTORY:
                raise PortiaCorruptionError("interpretation_inventory_limit")
            now = datetime.now(timezone.utc).isoformat()
            content = {
                "schema_version": "1",
                "record_type": "paper_interpretation",
                "module_id": "portia",
                "class_id": page.class_id,
                "work_id": page.work_id,
                "page_target_id": page.receipt.field("page_target_id"),
                "page_record_id": page.page_record_id,
                "interpretation_id": _identity(page.page_record_id, profile),
                "generation": (max(known) + 1) if known else 1,
                "layout_snapshot": dict(page.plan.layout.layout_identity),
                "interpreter_profile": profile.wire_identity(),
                "interpretation_status": candidate.interpretation_status,
                "limitation_codes": list(candidate.limitation_codes),
                "entries": candidate.entry_map(),
                "interpreted_at": now,
                "interpreted_by": dict(actor),
                "created_at": now,
                "created_by": dict(actor),
            }
            saved = PaperInterpretationV1(content)
            payload = canonical_json_bytes(saved.to_dict())
            if len(payload) > _MAX_BYTES:
                raise InterpretationGenerationError("interpretation_size_limit")
            dest = self.batches._safe(
                self._collection(page.class_id, page.work_id)
                / (cast(str, saved.logical_id) + ".json")
            )
            # Exclusive identity. Never replace, overwrite, repair or delete.
            exclusive_create(dest, payload)
            persisted = _parse(self.batches._safe(dest))
            if persisted.to_dict() != saved.to_dict():
                raise PortiaCorruptionError("interpretation_readback_mismatch")
            return InterpretationGenerationResult("created", persisted)

    def stage_marks(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
    ) -> InterpretationGenerationResult:
        profile = LOCAL_MARKS_V1
        authorization.require_access(class_id, "capture_interpretation.persist")
        actor = self.batches._actor(authorization)
        page = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile.wire_identity(),
        )
        candidate = self.marks.interpret(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile.wire_identity(),
        )
        return self._commit(
            page, profile, candidate, actor, authorization=authorization
        )

    def stage_manual(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        selection: ManualTextSelection,
        *,
        authorization: CaptureAuthorization,
    ) -> InterpretationGenerationResult:
        profile = LOCAL_ASSISTED_MARKS_V1
        authorization.require_access(class_id, "capture_interpretation.persist")
        actor = self.batches._actor(authorization)
        page = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile.wire_identity(),
        )
        staged = self.manual.transcribe_one(
            class_id,
            work_id,
            page_record_id,
            selection,
            authorization=authorization,
            profile_identity=profile.wire_identity(),
        )
        if dict(staged.operator) != dict(actor):
            raise InterpretationGenerationError("manual_operator_changed")
        return self._commit(
            page, profile, staged.page, actor, authorization=authorization
        )
