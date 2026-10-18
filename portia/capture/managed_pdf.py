"""Immutable, authorized generation and explicit recovery of Portia PDS2 PDFs.

The physical output is a teacher-local *blank form*, not domain evidence, proof
of printing, or a retained returned page. Core owns its individual page routes.
"""

from __future__ import annotations

import hashlib
import io
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from portia.capture.contracts import CaptureAuthorization
from portia.capture.pdf_rendering import (
    RenderedCapturePdf,
    render_verified_capture_batch_pdf,
)
from portia.capture.preparation import FileCapturePreparationService
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaRecoveryRequiredError,
    PortiaStorageError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exact_delete, exclusive_create, read_bytes

ARTIFACT_RECEIPT_VERSION = "portia_capture_pdf_receipt_v1"
_MAX_PDF_BYTES = 8_000_000
_PDF_NAME = "capture-packet.pdf"
_RECEIPT_NAME = "capture-packet.receipt.json"
_LOCK_NAME = ".capture-packet-generation.lock"


class ManagedCapturePdfError(ValueError):
    """A capture PDF is invalid or an artifact operation cannot be accepted."""


@dataclass(frozen=True, slots=True)
class ManagedCapturePdf:
    """Verified managed artifact, not evidence of printing or page return."""

    pdf_path: Path
    receipt_path: Path
    sha256: str
    page_count: int
    page_target_ids: tuple[str, ...]
    state: Literal["created", "reused", "recovered", "verified"]


def _is_pdf_image(value: object) -> bool:
    """Identify vector-incompatible raster image XObjects."""
    if not hasattr(value, "get_object"):
        return False
    resolved = value.get_object()
    return isinstance(resolved, dict) and resolved.get("/Subtype") == "/Image"


def _validate_pdf(content: bytes, expected: RenderedCapturePdf) -> None:
    """Validate actual PDF structure, exact page order, geometry and fallback."""
    if not 0 < len(content) <= _MAX_PDF_BYTES:
        raise ManagedCapturePdfError("PDF exceeds allowed size or is empty")
    if hashlib.sha256(content).hexdigest() != expected.sha256:
        raise ManagedCapturePdfError("renderer PDF digest does not match bytes")
    if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
        raise ManagedCapturePdfError("PDF envelope is incomplete")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) != expected.page_count:
            raise ManagedCapturePdfError("PDF page count or encryption is invalid")
        for page, identity in zip(reader.pages, expected.pages, strict=True):
            media = page.mediabox
            if (round(float(media.width)), round(float(media.height))) != (612, 792):
                raise ManagedCapturePdfError("PDF sheet is not US Letter")
            text = page.extract_text() or ""
            if identity.pds2_payload not in "".join(text.split()):
                raise ManagedCapturePdfError("PDF page lacks its full PDS2 fallback")
            resources = page.get("/Resources")
            if resources is not None and hasattr(resources, "get_object"):
                obj = resources.get_object()
                xobjects = obj.get("/XObject", {})
                if hasattr(xobjects, "get_object"):
                    xobjects = xobjects.get_object()
                if any(_is_pdf_image(x) for x in xobjects.values()):
                    raise ManagedCapturePdfError("capture QR must remain vector-only")
    except ManagedCapturePdfError:
        raise
    except (
        PyPdfError,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        AttributeError,
        OSError,
    ) as exc:
        raise ManagedCapturePdfError("PDF structure cannot be verified") from exc


def _receipt(rendered: RenderedCapturePdf, class_id: str, work_id: str) -> bytes:
    record: dict[str, object] = {
        "receipt_version": ARTIFACT_RECEIPT_VERSION,
        "module_id": "portia",
        "class_id": class_id,
        "capture_batch_id": work_id,
        "renderer_version": rendered.renderer_version,
        "pdf_sha256": rendered.sha256,
        "pdf_bytes": len(rendered.pdf_bytes),
        "page_count": rendered.page_count,
        "pages": [
            {
                "page_index": page.page_index,
                "page_target_id": page.page_target_id,
                "template_identity": dict(page.template_identity),
                "pds2_payload": page.pds2_payload,
            }
            for page in rendered.pages
        ],
        "status": "pdf_ready_not_printed",
    }
    return canonical_json_bytes(record)


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


class FileCapturePdfArtifactService:
    """Contained immutable one-packet-per-Batch storage with explicit recovery.

    A different physical copy of the same verified PDF is permitted, but a
    returned paper source is always separately retained in future #59. A new
    session/form revision needs a *new* Capture Batch, targets and Core routes.
    """

    def __init__(self, preparation: FileCapturePreparationService) -> None:
        if not isinstance(preparation, FileCapturePreparationService):
            raise ManagedCapturePdfError("verified preparation service required")
        self.preparation = preparation
        self.root = preparation.root

    def _locations(self, class_id: str, work_id: str) -> tuple[Path, Path, Path]:
        # Public Core's typed work ref validates opaque class/batch IDs, and
        # Portia's existing safe-path guard rejects symlinks and junctions.
        self.preparation.batches._work(class_id, work_id)
        directory = self.root / "portia" / "capture_forms" / class_id / work_id
        guard = self.preparation.batches._safe
        return (
            guard(directory / _PDF_NAME),
            guard(directory / _RECEIPT_NAME),
            guard(directory / _LOCK_NAME),
        )

    def _authorize(
        self, class_id: str, action: str, authorization: CaptureAuthorization
    ) -> None:
        self.preparation.batches._authorize(class_id, action, authorization)

    @staticmethod
    def _result(
        pdf: Path,
        receipt: Path,
        rendered: RenderedCapturePdf,
        state: Literal["created", "reused", "recovered", "verified"],
    ) -> ManagedCapturePdf:
        return ManagedCapturePdf(
            pdf,
            receipt,
            rendered.sha256,
            rendered.page_count,
            tuple(page.page_target_id for page in rendered.pages),
            state,
        )

    def _verify_existing(
        self,
        pdf: Path,
        receipt: Path,
        rendered: RenderedCapturePdf,
        receipt_bytes: bytes,
    ) -> None:
        if not _present(pdf) or not _present(receipt):
            raise PortiaRecoveryRequiredError(
                "incomplete PDF/receipt pair; use explicit capture PDF recovery"
            )
        # Recheck links after IO and compare exact bytes, not just metadata.
        self.preparation.batches._safe(pdf)
        self.preparation.batches._safe(receipt)
        if read_bytes(receipt) != receipt_bytes:
            raise PortiaConflictError("existing immutable capture PDF receipt differs")
        if read_bytes(pdf) != rendered.pdf_bytes:
            raise PortiaConflictError("existing immutable capture PDF differs")
        _validate_pdf(read_bytes(pdf), rendered)

    def _install(self, destination: Path, content: bytes) -> None:
        """Stage then atomically publish exclusively via same-volume hard link.

        No `os.replace` or ordinary final-file writes: neither is allowed to
        clobber an issued form or expose a partially written apparent PDF.
        A crash may leave an owned temporary candidate; never auto-sweep it.
        """
        dest = self.preparation.batches._safe(destination)
        candidate = self.preparation.batches._safe(
            dest.with_name("." + dest.name + ".stage-" + secrets.token_hex(12))
        )
        fingerprint = exclusive_create(candidate, content)
        try:
            if read_bytes(self.preparation.batches._safe(candidate)) != content:
                raise PortiaCorruptionError("staged capture artifact changed")
            self.preparation.batches._safe(dest)
            try:
                os.link(candidate, dest)
            except FileExistsError as exc:
                raise PortiaConflictError(
                    "capture artifact was concurrently installed"
                ) from exc
            except OSError as exc:
                raise PortiaStorageError(
                    "exclusive atomic artifact publication unavailable"
                ) from exc
            if read_bytes(self.preparation.batches._safe(dest)) != content:
                raise PortiaCorruptionError("installed capture artifact has changed")
        finally:
            # Remove exactly one proven operation-owned staging path. If its
            # identity/bytes drifted, preserve it for explicit investigation.
            if _present(candidate):
                exact_delete(
                    self.preparation.batches._safe(candidate), expected=fingerprint
                )

    def _work(
        self,
        class_id: str,
        work_id: str,
        authorization: CaptureAuthorization,
        *,
        mode: Literal["generate", "recover", "inspect"],
    ) -> ManagedCapturePdf:
        if mode not in {"generate", "recover", "inspect"}:
            raise ManagedCapturePdfError("unknown PDF artifact operation")
        self._authorize(class_id, "capture_form." + mode, authorization)
        pdf, receipt, lock = self._locations(class_id, work_id)
        if mode == "inspect":
            # Read-only mode does not create directories or take a write lock.
            rendered = render_verified_capture_batch_pdf(
                self.preparation, class_id, work_id, authorization=authorization
            )
            self._verify_existing(
                pdf, receipt, rendered, _receipt(rendered, class_id, work_id)
            )
            return self._result(pdf, receipt, rendered, "verified")

        if _present(lock):
            raise PortiaRecoveryRequiredError(
                "capture PDF generation lock already exists; manual review required"
            )
        lock_content = canonical_json_bytes(
            {
                "operation": "capture_pdf." + mode,
                "class_id": class_id,
                "work_id": work_id,
                "nonce": secrets.token_hex(16),
            }
        )
        try:
            lock_fingerprint = exclusive_create(lock, lock_content)
        except PortiaConflictError as exc:
            raise PortiaRecoveryRequiredError(
                "concurrent/interrupted PDF generation; inspect retained lock"
            ) from exc
        try:
            # Serialize against Batch close and route registration changes.
            with self.preparation.batches._lifecycle_lock(class_id, work_id):
                rendered = render_verified_capture_batch_pdf(
                    self.preparation, class_id, work_id, authorization=authorization
                )
                _validate_pdf(rendered.pdf_bytes, rendered)
                expected_receipt = _receipt(rendered, class_id, work_id)
                has_pdf, has_receipt = _present(pdf), _present(receipt)
                if has_pdf and has_receipt:
                    self._verify_existing(pdf, receipt, rendered, expected_receipt)
                    return self._result(pdf, receipt, rendered, "reused")
                if mode == "generate" and (has_pdf or has_receipt):
                    raise PortiaRecoveryRequiredError(
                        "interrupted PDF/receipt publication; explicitly recover"
                    )
                if mode == "recover" and not (has_pdf or has_receipt):
                    raise PortiaRecoveryRequiredError(
                        "nothing persisted to recover; choose ordinary generation"
                    )
                # Recovery never overwrites. Proven surviving half must match
                # this exact deterministic render and receipt before completing.
                if (
                    has_pdf
                    and read_bytes(self.preparation.batches._safe(pdf))
                    != rendered.pdf_bytes
                ):
                    raise PortiaConflictError(
                        "interrupted PDF bytes differ; manual recovery"
                    )
                if (
                    has_receipt
                    and read_bytes(self.preparation.batches._safe(receipt))
                    != expected_receipt
                ):
                    raise PortiaConflictError(
                        "interrupted receipt bytes differ; manual recovery"
                    )
                if not has_pdf:
                    self._install(pdf, rendered.pdf_bytes)
                if not has_receipt:
                    self._install(receipt, expected_receipt)
                self._verify_existing(pdf, receipt, rendered, expected_receipt)
                return self._result(
                    pdf,
                    receipt,
                    rendered,
                    "recovered" if mode == "recover" else "created",
                )
        finally:
            # A process crash retains the exclusive lock. Ordinary failures
            # release only this exact lock; never erase another generation's.
            exact_delete(
                self.preparation.batches._safe(lock), expected=lock_fingerprint
            )

    def generate(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> ManagedCapturePdf:
        """Create a complete immutable artifact or idempotently reuse exact bytes."""
        return self._work(class_id, work_id, authorization, mode="generate")

    def recover(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> ManagedCapturePdf:
        """Explicitly complete missing counterpart after exact verified re-render."""
        return self._work(class_id, work_id, authorization, mode="recover")

    def inspect(
        self, class_id: str, work_id: str, *, authorization: CaptureAuthorization
    ) -> ManagedCapturePdf:
        """Read-only verification; never open the viewer or assert PDF was printed."""
        return self._work(class_id, work_id, authorization, mode="inspect")
