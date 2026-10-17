"""Verify *real* scanned synthetic Issue #58 pages against persisted Core routes.

Input: images (PNG/JPEG) exported by an actual office scanner. This is an
optional physical qualification tool; OpenCV must be installed separately.
No scanning/OCR records are ingested into a production PDS workspace.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Sequence, cast

from pds_core.pds2 import parse_pds2_payload, serialize_pds2_payload
from pds_core.route_registrations import load_route_registration


def _expectations(value: object) -> tuple[Path, dict[str, tuple[str, str]]]:
    if not isinstance(value, dict) or value.get("purpose") != (
        "synthetic_physical_acceptance_only"
    ):
        raise ValueError("not an Issue #58 synthetic physical qualification manifest")
    workspace = value.get("workspace")
    pdfs = value.get("pdfs")
    if not isinstance(workspace, str) or not isinstance(pdfs, list):
        raise ValueError("manifest is missing synthetic route provenance")
    expected: dict[str, tuple[str, str]] = {}
    for item in pdfs:
        if not isinstance(item, dict):
            raise ValueError("manifest form is invalid")
        form = item.get("form_id")
        pages = item.get("pages")
        if not isinstance(form, str) or not isinstance(pages, list):
            raise ValueError("manifest form/pages are invalid")
        for page in pages:
            if not isinstance(page, dict):
                raise ValueError("manifest page is invalid")
            index = page.get("page_index")
            payload = page.get("pds2_payload")
            target = page.get("page_target_id")
            if (
                type(index) is not int
                or not isinstance(payload, str)
                or not isinstance(target, str)
            ):
                raise ValueError("manifest page identity is incomplete")
            key = f"{form}:{index}"
            if key in expected:
                raise ValueError("duplicate synthetic form/page identity")
            expected[key] = (payload, target)
    if len(expected) != 10:
        raise ValueError("physical manifest must cover all ten initial layouts")
    return Path(workspace), expected


def _decode_scan(image: Path) -> str:
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError as exc:
        raise RuntimeError(
            "physical QR decoding requires optional opencv-python-headless; "
            "install it only in this qualification environment"
        ) from exc
    if not image.is_file():
        raise ValueError(f"scan image does not exist: {image}")
    pixels = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
    if pixels is None:
        raise ValueError(f"could not decode scanner image pixels: {image}")
    detector = cv2.QRCodeDetector()
    payload, _points, _straight = detector.detectAndDecode(pixels)
    if not isinstance(payload, str) or not payload:
        raise ValueError(f"no QR value decoded from actual scan: {image}")
    return payload


def verify(manifest_path: Path, scan_args: Sequence[str], *, partial: bool) -> int:
    data: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    workspace, expected = _expectations(data)
    scans: dict[str, Path] = {}
    for assignment in scan_args:
        if "=" not in assignment:
            raise ValueError("scan arguments must be form_id:page_index=path.png")
        key, filename = assignment.split("=", 1)
        if key not in expected or key in scans or not filename:
            raise ValueError(f"unexpected or repeated physical scan identity: {key}")
        scans[key] = Path(filename)
    if not scans:
        raise ValueError("at least one physical scanner image is required")
    if not partial and set(scans) != set(expected):
        missing = sorted(set(expected) - set(scans))
        raise ValueError(
            f"physical qualification incomplete; missing {', '.join(missing)}"
        )
    successes = 0
    for key, image in sorted(scans.items()):
        payload, target_id = expected[key]
        decoded = _decode_scan(image)
        locator = parse_pds2_payload(decoded)
        if decoded != payload or serialize_pds2_payload(locator) != decoded:
            raise ValueError(f"decoded QR disagrees with exact registered PDS2: {key}")
        registration = load_route_registration(workspace, locator)
        if (
            registration.target.record_id != target_id
            or registration.status != "active"
        ):
            raise ValueError(f"decoded QR has no exact active Core Page Target: {key}")
        successes += 1
        print(f"PASS {key}: decoded exact active Core route")
    print(f"Verified {successes}/{len(expected)} distinct physical page layouts")
    if partial:
        print("PARTIAL evidence only: full physical qualification remains open")
    else:
        print(
            "Physical QR route check passed; record print-scale/DPI/readability separately"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--scan",
        action="append",
        default=[],
        help='one entry of the form "focused_monitoring:1=C:\\scans\\page.png"',
    )
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    return verify(
        args.manifest, cast(Sequence[str], args.scan), partial=args.allow_partial
    )


if __name__ == "__main__":
    raise SystemExit(main())
