"""Generate all Issue #58 synthetic PDS2 printer samples in a NEW isolated workspace.

Source-checkout qualification only: uses repository's synthetic acceptance fixtures
and authentic Portia/Core preparation, registration and managed PDF services.
Never point --output at a live Paper Data Suite workspace or repository folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Sequence

from pds_core.pds2 import parse_pds2_payload, serialize_pds2_payload
from pds_core.route_registrations import load_route_registration

from portia.capture.contracts import CapturePreparationRequest
from portia.capture.form_catalog import (
    capture_pages_for_form,
    list_supported_capture_forms,
)
from portia.capture.managed_pdf import FileCapturePdfArtifactService
from portia.models import CaptureBatchV1, PageTargetV2

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
SYNTHETIC_CLASS = "class_english10_p2"


def _synthetic_test_helpers() -> tuple[
    Callable[..., Any], Callable[..., Any], Callable[..., Any], Callable[..., Any]
]:
    """Import source-only synthetic fixtures; never read live student work."""
    if not (TESTS / "test_issue57_slice6_preparation.py").is_file():
        raise RuntimeError(
            "physical fixture generator requires a Portia source checkout"
        )
    sys.path.insert(0, str(TESTS))
    preparation_helpers = import_module("test_issue57_slice6_preparation")
    purpose_helpers = import_module("test_issue57_slice4_purposes")
    return (
        preparation_helpers.setup,
        preparation_helpers.batch,
        preparation_helpers.page,
        purpose_helpers.seed_work,
    )


def _publish_pdf(source: Path, destination: Path) -> None:
    # Exact create only; do not silently overwrite prior samples.
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing)


def generate_samples(output: Path) -> dict[str, object]:
    """Persist a completely separate synthetic Core workspace and QR-route inventory."""
    if output.exists() or output.is_symlink():
        raise ValueError("output directory already exists; choose a new folder")
    if output == ROOT or ROOT in output.parents:
        raise ValueError("physical samples must remain outside the source repository")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("choose an existing ordinary parent directory for output")
    output.mkdir(mode=0o700)
    workspace = output / "synthetic_core_workspace"
    workspace.mkdir()
    print_dir = output / "print_ready"
    print_dir.mkdir()
    setup, batch_fn, page_fn, seed_work = _synthetic_test_helpers()
    preparation, auth = setup(workspace)
    event_ref = seed_work(workspace, "event")
    support_ref = seed_work(workspace, "support_process")
    entries: list[dict[str, object]] = []
    for form_id, label in list_supported_capture_forms():
        specs = capture_pages_for_form(form_id)
        if form_id == "daily_classroom_observation":
            specs = (specs[0], specs[1])  # One primary sheet and one continuation.
        else:
            if len(specs) != 1:
                raise RuntimeError("unexpected multi-role core form")
        batch_id = f"cbat_issue58_physical_{form_id}"
        batch_wire = batch_fn().to_dict()
        batch_wire["work_id"] = batch_id
        sample_batch = CaptureBatchV1(batch_wire)
        targets: list[PageTargetV2] = []
        for index, spec in enumerate(specs, start=1):
            raw = page_fn(index).to_dict()
            raw["work_id"] = batch_id
            raw["page_target_id"] = f"ptgt_issue58_{form_id}_{index}"
            raw["template_identity"] = spec.template_identity()
            raw["entry_layout"] = spec.entry_layout()
            raw["page_purpose"] = spec.page_purpose
            raw["capture_mode"] = spec.capture_mode
            if form_id == "event_evidence":
                raw["existing_work_context"] = event_ref.to_dict()
            if form_id == "support_process_evidence":
                raw["existing_work_context"] = support_ref.to_dict()
            target = PageTargetV2(raw)
            spec.assert_page_target_exact(target)
            targets.append(target)
        ready = preparation.prepare(
            CapturePreparationRequest(sample_batch, tuple(targets)),
            authorization=auth,
        )
        if not ready.ready_for_rendering:
            raise RuntimeError(f"{form_id}: synthetic Core routes not fully verified")
        result = FileCapturePdfArtifactService(preparation).generate(
            SYNTHETIC_CLASS, batch_id, authorization=auth
        )
        filename = f"{form_id}.pdf"
        destination = print_dir / filename
        _publish_pdf(result.pdf_path, destination)
        if hashlib.sha256(destination.read_bytes()).hexdigest() != result.sha256:
            raise RuntimeError(f"{form_id}: copied PDF failed exact checksum")
        pages: list[dict[str, object]] = []
        for entry in ready.pages:
            payload = entry.payload
            if payload is None or entry.locator is None:
                raise RuntimeError("synthetic page lacks verified Core locator")
            parsed = parse_pds2_payload(payload)
            if serialize_pds2_payload(parsed) != payload:
                raise RuntimeError("synthetic PDS2 payload is noncanonical")
            registration = load_route_registration(workspace, parsed)
            if registration.target.record_id != entry.target.logical_id:
                raise RuntimeError("reloaded Core route does not match printed page")
            pages.append(
                {
                    "page_index": entry.target.field("page_index"),
                    "page_target_id": entry.target.logical_id,
                    "pds2_payload": payload,
                    "template_identity": entry.target.to_dict()["template_identity"],
                }
            )
        entries.append(
            {
                "form_id": form_id,
                "label": label,
                "pdf": f"print_ready/{filename}",
                "sha256": result.sha256,
                "page_count": len(pages),
                "batch_id": batch_id,
                "pages": pages,
            }
        )
    manifest: dict[str, object] = {
        "schema_version": 1,
        "purpose": "synthetic_physical_acceptance_only",
        "workspace": str(workspace.resolve()),
        "class_id": SYNTHETIC_CLASS,
        "pdfs": entries,
        "physical_print_and_scan_qualified": False,
    }
    (output / "synthetic-route-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args(argv)
    if not args.confirm_synthetic:
        parser.error("pass --confirm-synthetic after choosing a NEW external folder")
    output = args.output.absolute()
    manifest = generate_samples(output)
    pdfs = manifest["pdfs"]
    if not isinstance(pdfs, list):
        raise RuntimeError("synthetic PDF manifest is incomplete")
    print(f"Created {len(pdfs)} synthetic PDF packets in {output}")
    print("Routes are registered in synthetic_core_workspace; do not move it.")
    print("Print at 100% scale, scan at 200 and 300 DPI, then run the scan verifier.")
    print("No physical print/scan success is claimed by this generation step.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
