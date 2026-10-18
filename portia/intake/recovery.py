"""Issue #59 Slice 7: restart-safe discovery of Core-retained original scans.

Core still owns the original bytes.  A candidate is only a *possible* retained
source; loading it rereads and verifies the Core path, complete file structure,
source digest prefix, full SHA-256, size, and page count.  Nothing is rewritten.
"""

from __future__ import annotations

import hmac
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Final

from pds_core.scan_retention import RetainedSourceScan
from pds_core.scan_routes import scans_source_dir

from portia.intake.contracts import SourceFormat, SourceSafetyLimits
from portia.intake.retention import (
    FileRetainFirstIntakeService,
    IntakeSourceError,
    RetainedIntakeSource,
    _assert_retained_under_root,
    _assert_safe_path,
    _hash_file,
)

_CORE_NAME: Final[re.Pattern[str]] = re.compile(
    r"(?P<clock>\d{8}T\d{12}Z)__(?P<stem>[A-Za-z0-9_-]{1,200})__"
    r"(?P<digest>[0-9a-f]{12})\.(?P<extension>pdf|jpg|jpeg|png)\Z"
)
_DATE_NAME: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
# Core 0.6.3 lacks the newer public filename maximum. 255 is a
# conservative cross-version filesystem leaf guard; the page-reference
# contract additionally limits reconstructed scan IDs to 128 characters.
_MAX_CORE_FILENAME_LENGTH: Final[int] = 255
_MAX_INVENTORY_ENTRIES: Final[int] = 8192
_MAX_RECENT: Final[int] = 64
_FORMATS: Final[dict[str, SourceFormat]] = {
    "pdf": SourceFormat.PDF,
    "jpg": SourceFormat.JPEG,
    "jpeg": SourceFormat.JPEG,
    "png": SourceFormat.PNG,
}


class RetainedRecoveryError(RuntimeError):
    """Recovery refused to trust an unsafe or changed Core-retained source."""


@dataclass(frozen=True, slots=True)
class RetainedSourceCandidate:
    """Read-only, *unverified* catalog entry; not yet permission to route pages."""

    relative_path: str
    source_scan_id: str
    intake_timestamp: datetime
    source_format: SourceFormat
    digest_prefix: str

    @property
    def label(self) -> str:
        # No scan contents, file stem or Core route identifiers in menu labels.
        stamp = self.intake_timestamp.strftime("%Y-%m-%d %H:%M UTC")
        return f"{self.source_format.value.upper()} retained {stamp}"


class FileCoreRetainedSourceRecoveryService:
    """Find and reopen Core originals after an interrupted Portia session.

    The Core v0.6.x retain API does not publish a source enumeration/readback
    method. This adapter walks only Core's public scans_source_dir layout;
    it NEVER claims to restore the original pre-retention basename from a
    sanitized filename, and it never copies the bytes back into Portia.
    """

    def __init__(
        self, workspace_root: str | Path, *, limits: SourceSafetyLimits | None = None
    ) -> None:
        from portia.intake.contracts import DEFAULT_SOURCE_LIMITS

        selected_limits = DEFAULT_SOURCE_LIMITS if limits is None else limits
        if not isinstance(selected_limits, SourceSafetyLimits):
            raise TypeError("limits must be SourceSafetyLimits")
        self.root = Path(workspace_root).absolute()
        self.limits = selected_limits
        self.intake = FileRetainFirstIntakeService(self.root, limits=self.limits)

    def recent(self, *, limit: int = 24) -> tuple[RetainedSourceCandidate, ...]:
        """Enumerate bounded Core-named files; no class data or scan bytes read."""
        if type(limit) is not int or not 1 <= limit <= _MAX_RECENT:
            raise ValueError("recovery list limit is outside permitted range")
        directory = scans_source_dir(self.root)
        _assert_safe_path(self.root)
        if not directory.exists():
            return ()
        _assert_safe_path(directory)
        if not directory.is_dir():
            raise RetainedRecoveryError("Core retained-source location is invalid")

        entries = 0
        candidates: list[RetainedSourceCandidate] = []
        try:
            for date_directory in directory.iterdir():
                entries += 1
                if entries > _MAX_INVENTORY_ENTRIES:
                    raise RetainedRecoveryError("Core retained inventory is too large")
                _assert_safe_path(date_directory)
                if not date_directory.is_dir():
                    continue
                if not _strict_date(date_directory.name):
                    continue
                for path in date_directory.iterdir():
                    entries += 1
                    if entries > _MAX_INVENTORY_ENTRIES:
                        raise RetainedRecoveryError(
                            "Core retained inventory is too large"
                        )
                    _assert_safe_path(path)
                    if not path.is_file():
                        continue
                    candidate = self._candidate(path)
                    if candidate is not None:
                        candidates.append(candidate)
        except OSError as exc:
            raise RetainedRecoveryError(
                "Core retained inventory cannot be inspected"
            ) from exc
        # Exact most recent Core retention first, independent of filesystem order.
        candidates.sort(
            key=lambda item: (item.intake_timestamp, item.source_scan_id),
            reverse=True,
        )
        return tuple(candidates[:limit])

    def load(self, candidate: RetainedSourceCandidate) -> RetainedIntakeSource:
        """Verify one exact Core source without making a new intake identity."""
        if not isinstance(candidate, RetainedSourceCandidate):
            raise TypeError("recovery requires a Core retained-source candidate")
        # Only recomputed canonical Core candidates are trusted. No caller
        # supplied arbitrary absolute/relative filesystem path can be opened.
        path = self.root / candidate.relative_path
        base = scans_source_dir(self.root)
        try:
            relative = path.relative_to(base)
        except ValueError as exc:
            raise RetainedRecoveryError(
                "candidate leaves the Core source store"
            ) from exc
        if len(relative.parts) != 2:
            raise RetainedRecoveryError("candidate has an invalid Core path")
        _assert_safe_path(path)
        observed = self._candidate(path)
        if observed is None or observed != candidate:
            raise RetainedRecoveryError("candidate no longer matches Core provenance")
        try:
            preflight = self.intake.preflight(path)
            if preflight.source_format != candidate.source_format:
                raise RetainedRecoveryError("retained file format changed")
            if not hmac.compare_digest(
                preflight.source_sha256[:12], candidate.digest_prefix
            ):
                raise RetainedRecoveryError(
                    "retained source digest differs from Core name"
                )
            # A second complete hash catches ordinary changes while the
            # candidate was being validated. No destructive cleanup occurs.
            digest, count = _hash_file(path, self.limits.max_source_bytes)
            if digest != preflight.source_sha256 or count != preflight.byte_count:
                raise RetainedRecoveryError("retained source changed during recovery")
        except IntakeSourceError as exc:
            raise RetainedRecoveryError("retained file is not safe to resume") from exc

        core = RetainedSourceScan(
            source_scan_id=candidate.source_scan_id,
            # Core's public retained filename cannot reconstruct the original
            # pre-retention basename. Use exact retained leaf, not an invention.
            source_filename=path.name,
            source_sha256=digest,
            retained_source_path=path,
            retained_source_relative_path=candidate.relative_path,
            intake_timestamp=candidate.intake_timestamp,
            intake_date=candidate.intake_timestamp.date(),
        )
        _assert_retained_under_root(self.root, core)
        return RetainedIntakeSource(
            core_source=core,
            source_format=preflight.source_format,
            byte_count=count,
            page_count=preflight.page_count,
        )

    def _candidate(self, path: Path) -> RetainedSourceCandidate | None:
        if len(path.name) > _MAX_CORE_FILENAME_LENGTH or len("scan_" + path.stem) > 128:
            return None
        match = _CORE_NAME.fullmatch(path.name)
        if match is None or not _strict_date(path.parent.name):
            return None
        try:
            stamp = datetime.strptime(match.group("clock"), "%Y%m%dT%H%M%S%fZ")
            timestamp = stamp.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if timestamp.date().isoformat() != path.parent.name:
            return None
        try:
            relative = path.relative_to(self.root).as_posix()
        except ValueError:
            return None
        return RetainedSourceCandidate(
            relative_path=relative,
            source_scan_id="scan_" + path.stem,
            intake_timestamp=timestamp,
            source_format=_FORMATS[match.group("extension")],
            digest_prefix=match.group("digest"),
        )


def _strict_date(value: str) -> bool:
    if _DATE_NAME.fullmatch(value) is None:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
