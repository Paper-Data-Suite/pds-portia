"""Issue #59 real isolated wheel/scan-extra/retained-page acceptance.

The official Core wheel is installed first, followed by the built Portia wheel
with [scan]. No repository source or editable Portia import is used in the probe.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path

_PROBE = r"""
import hashlib
import io
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

import cv2
import numpy
import pymupdf
import qrcode
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from pds_core.pds2 import serialize_pds2_payload
from pds_core.routing_models import ModuleWorkRef, RouteLocator
from portia.intake import (
    FileCoreRetainedSourceRecoveryService,
    FilePageQrDiscoveryService,
    FilePageRecordService,
    FilePageRouteDispatchService,
    FileRetainFirstIntakeService,
    TeacherReturnedPaperService,
)
from portia.menu.main import render_main_menu

assert version("pds-core") == sys.argv[1], "incorrect installed official Core"
assert version("pds-portia") == "0.2.0", "development package version changed"
assert "11. Scan / Import Returned Paper" in render_main_menu()
assert all((cv2.__version__, numpy.__version__, pymupdf.VersionBind))
assert callable(FilePageRecordService) and callable(FilePageRouteDispatchService)
assert callable(TeacherReturnedPaperService)

payload = serialize_pds2_payload(RouteLocator(
    "PDS2", ModuleWorkRef("portia", "class_pkg_smoke", "cbat_pkg_smoke"),
    "rt_pkg_smoke",
))
code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                     border=4, box_size=8)
code.add_data(payload)
code.make(fit=True)
qr = code.make_image(fill_color="black", back_color="white").convert("RGB")

with tempfile.TemporaryDirectory(prefix="issue59_installed_") as temp:
    root = Path(temp)
    workspace = root / "workspace"
    workspace.mkdir()
    pdf = root / "returned.pdf"
    image_bytes = io.BytesIO()
    qr.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    writer = canvas.Canvas(str(pdf), pagesize=(612, 792))
    writer.drawImage(ImageReader(image_bytes), 58, 485, width=190, height=190)
    writer.showPage()
    writer.drawString(50, 700, "synthetic blank page, no QR")
    writer.showPage()
    writer.save()

    intake = FileRetainFirstIntakeService(workspace)
    discover = FilePageQrDiscoveryService(workspace)
    retained = intake.admit_and_retain(pdf)
    assert retained.page_count == 2
    assert retained.core_source.retained_source_path.read_bytes() == pdf.read_bytes()
    assert retained.core_source.source_sha256 == hashlib.sha256(pdf.read_bytes()).hexdigest()
    result = discover.discover(retained)
    assert [x.status for x in result.pages] == ["candidate_unverified", "missing_qr"]
    assert [x.identity.source_page_number for x in result.pages] == [1, 2]
    assert result.pages[0].candidate_locator.route_id == "rt_pkg_smoke"
    recovered = FileCoreRetainedSourceRecoveryService(workspace)
    candidates = recovered.recent()
    match = next(x for x in candidates if x.source_scan_id == retained.core_source.source_scan_id)
    recovered_source = recovered.load(match)
    assert recovered_source.core_source.source_sha256 == retained.core_source.source_sha256
    assert [x.status for x in discover.discover(recovered_source).pages] == [
        "candidate_unverified", "missing_qr"
    ]

    for name, extension, image_format in (("phone.png", "png", "PNG"),
                                           ("phone.jpg", "jpg", "JPEG")):
        photo = Image.new("RGB", (1050, 1100), "white")
        photo.paste(qr.resize((400, 400)), (85, 90))
        source = root / name
        photo.save(source, format=image_format, quality=97)
        one = intake.admit_and_retain(source)
        assert one.page_count == 1
        assert discover.discover(one).pages[0].status == "candidate_unverified"

print("Issue #59 installed wheel PDF/JPEG/PNG, Core custody and restart smoke passed")
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()
    portia_wheel = args.portia_wheel.resolve(strict=True)
    core_wheel = args.core_wheel.resolve(strict=True)
    if not (
        portia_wheel.name.startswith("pds_portia-") and portia_wheel.suffix == ".whl"
    ):
        raise ValueError("expected built Portia wheel")
    if not (
        core_wheel.name.startswith("pds_core-0.6.") and core_wheel.suffix == ".whl"
    ):
        raise ValueError("expected official Core 0.6.x wheel")
    expected_core = core_wheel.name.split("-")[1]
    with tempfile.TemporaryDirectory(prefix="portia_issue59_wheel_") as tmp:
        root = Path(tmp)
        env_path = root / "env"
        venv.EnvBuilder(with_pip=True).create(env_path)
        executable = (
            env_path / "Scripts" / "python.exe"
            if os.name == "nt"
            else env_path / "bin" / "python"
        )

        def run(args_to_run: list[str]) -> None:
            subprocess.run(args_to_run, cwd=root, check=True)

        run(
            [
                str(executable),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(core_wheel),
            ]
        )
        run(
            [
                str(executable),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                f"{portia_wheel}[scan]",
            ]
        )
        run([str(executable), "-m", "pip", "check"])
        child_env = os.environ.copy()
        child_env.pop("PYTHONPATH", None)
        child_env["PYTHONDONTWRITEBYTECODE"] = "1"
        subprocess.run(
            [str(executable), "-c", _PROBE, expected_core],
            cwd=root,
            env=child_env,
            check=True,
        )
    print(
        f"Issue #59 isolated {expected_core} Core installed-wheel qualification passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
