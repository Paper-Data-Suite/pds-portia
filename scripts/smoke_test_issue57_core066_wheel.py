"""Qualify installed Portia wheel with authenticated Core 0.6.6 on Windows/Linux."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

EXPECTED_PORTIA_VERSION = "0.2.0"

# Execute with -I from a directory outside the repository, using only the two
# installed wheels. The fixture paths are input DATA, not import locations.
_INSTALLED_SMOKE = r"""
import hashlib
import json
import os
import stat
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pds_core
import portia
from pds_core import local_open
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.pds2 import parse_pds2_payload, serialize_pds2_payload
from pds_core.routes import class_metadata_path, route_registration_path
from portia.capture import FileCapturePreparationService
from portia.capture.contracts import CapturePreparationRequest
from portia.models import CaptureBatchV1, PageTargetV2

fixtures = Path(sys.argv[1]).resolve()
venv_root = Path(sys.argv[2]).resolve()
assert metadata.version("pds-core") == "0.6.6"
assert metadata.version("pds-portia") == "0.2.0"
assert venv_root in Path(portia.__file__).resolve().parents
assert venv_root in Path(pds_core.__file__).resolve().parents
assert "viewer-aliases-v1" not in str(fixtures)

CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}

class Authorized:
    def require_access(self, class_id: str, operation: str) -> None:
        assert class_id == CLASS
        assert isinstance(operation, str) and operation

    def attribution(self) -> Mapping[str, object]:
        return ACTOR

def fixture(relative: str) -> dict[str, object]:
    data = json.loads((fixtures / relative).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data

def make_target(index: int) -> PageTargetV2:
    data = fixture(
        "issue_56/slice_2/valid/page-target-v2-classroom-observation.json"
    )
    data.update(
        class_id=CLASS, work_id=WORK,
        page_target_id=f"ptgt_classroom_{index:02d}", page_index=index,
        created_by=ACTOR, updated_by=ACTOR,
    )
    return PageTargetV2(data)

def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(directory)): p.read_bytes()
        for p in directory.rglob("*") if p.is_file()
    }

def long_root(base: Path) -> Path:
    root = base / "OneDrive-like-school-year" / "Paper-Data-Suite"
    while len(str(root).encode("utf-16-le")) // 2 < 290:
        root = root / "2026-2027-classroom-capture"
    root.mkdir(parents=True)
    return root

with TemporaryDirectory(prefix="portia-issue57-core066-") as folder:
    root = long_root(Path(folder))
    metadata_file = class_metadata_path(root, CLASS)
    metadata_file.parent.mkdir(parents=True)
    write_class_metadata(
        metadata_file,
        create_class_metadata(
            CLASS, "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    service = FileCapturePreparationService(root)
    auth = Authorized()
    batch = CaptureBatchV1(fixture("issue_20/valid/01-capture_batch.json"))
    first = make_target(1)
    second = make_target(2)
    request = CapturePreparationRequest(batch, (second, first))
    result = service.prepare(request, authorization=auth)
    assert result.ready_for_rendering, result
    assert len(result.pages) == 2
    assert tuple(p.target.field("page_index") for p in result.pages) == (1, 2)
    for item in result.pages:
        assert item.status == "verified"
        assert item.locator is not None and item.registration is not None
        assert item.payload is not None
        assert parse_pds2_payload(item.payload) == item.locator
        assert serialize_pds2_payload(item.locator) == item.payload
        assert item.registration.target.contract_version == "2"
        assert item.registration.target.record_kind == "capture_page_target"
        assert item.registration.target.record_id == item.target.logical_id
        assert item.registration.module_details["template_identity"] == (
            item.target.to_dict()["template_identity"]
        )
        route = route_registration_path(root, item.locator)
        assert route.is_file()
        contents = route.read_bytes()
        assert b"viewer-aliases-v1" not in contents
        assert b"OneDrive-like-school-year" not in contents

    before = snapshot(root)
    replay = service.prepare(request, authorization=auth)
    assert replay.ready_for_rendering
    assert [p.payload for p in replay.pages] == [p.payload for p in result.pages]
    assert snapshot(root) == before, "Exact retry rewrote durable capture records"
    inspected = service.inspect(CLASS, WORK, authorization=auth)
    assert inspected.ready_for_rendering
    assert snapshot(root) == before, "Inspection modified durable state"
    # No fabricated behavior-domain Event/Support Process work roots.
    work_collection = metadata_file.parent / "modules" / "portia" / "work"
    assert not any(
        path.name.startswith(("evt_", "sup_")) for path in work_collection.iterdir()
    )

    preview = root / "preview"
    preview.mkdir()
    html = preview / "synthetic-classroom-preview.html"
    css = preview / "style.css"
    html.write_text(
        '<!doctype html><link rel="stylesheet" href="style.css">'
        '<h1>Portia installed Core 0.6.6 synthetic preview</h1>',
        encoding="utf-8",
    )
    css.write_text("h1 { font-family: sans-serif }", encoding="utf-8")
    original_digest = hashlib.sha256(html.read_bytes()).hexdigest()
    assert len(str(html).encode("utf-16-le")) // 2 > 240

    if sys.platform == "win32":
        captures = []
        def fake_shell_handoff(path):
            captures.append(Path(path))
        link = None
        try:
            with patch.object(os, "startfile", fake_shell_handoff, create=True):
                returned = local_open.open_local_path(html)
            assert returned == html.resolve()
            assert len(captures) == 1
            handoff = captures[0]
            assert "viewer-aliases-v1" in str(handoff)
            assert len(str(handoff).encode("utf-16-le")) // 2 <= 240
            assert os.path.samefile(handoff, html)
            assert os.path.samefile(handoff.parent / "style.css", css)
            link = handoff.parent
            assert bool(
                getattr(link.lstat(), "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
            )
        finally:
            if link is not None and link.exists():
                # Test-created junction only; remove link, never recurse into source.
                link.rmdir()
        assert not os.path.lexists(link) if link is not None else True
    else:
        with patch.object(local_open.subprocess, "run") as opened:
            returned = local_open.open_local_path(html)
        assert returned == html.resolve()
        assert opened.call_count == 1
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        assert opened.call_args.args[0][0] == opener

    assert hashlib.sha256(html.read_bytes()).hexdigest() == original_digest
    assert css.is_file()
    # Viewer handoff/alias cleanup cannot affect Portia's canonical records.
    for relative, bytes_before in before.items():
        assert (root / relative).read_bytes() == bytes_before
    after_view = service.inspect(CLASS, WORK, authorization=auth)
    assert after_view.ready_for_rendering
    assert [p.payload for p in after_view.pages] == [p.payload for p in result.pages]
    routes = [route_registration_path(root, p.locator) for p in result.pages]
    assert len(routes) == 2 and all(route.exists() for route in routes)

print(json.dumps({
    "installed_core": "0.6.6", "installed_portia": "0.2.0",
    "qualified_platform": sys.platform, "multi_page": True,
    "idempotent": True, "durable_reloaded_routes": True,
    "viewer_alias_isolation": True, "canonical_bytes_preserved": True,
    "no_fabricated_domain_work": True,
}, sort_keys=True))
"""


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    done = subprocess.run(
        command, cwd=cwd, env=env, check=False, text=True, capture_output=True
    )
    if done.returncode:
        raise RuntimeError(
            f"Command failed ({done.returncode}): {command[:3]}\n"
            f"stdout:\n{done.stdout[-5000:]}\nstderr:\n{done.stderr[-5000:]}"
        )
    return done.stdout


def smoke(portia_wheel: Path, core_wheel: Path, fixtures: Path) -> None:
    verifier = Path(__file__).resolve().with_name("verify_core_wheel.py")
    checked = subprocess.run(
        [sys.executable, str(verifier), str(core_wheel)],
        check=False,
        capture_output=True,
        text=True,
    )
    if checked.returncode != 0 or "pds-core 0.6.6" not in checked.stdout:
        raise RuntimeError(
            "Slice 8 needs authenticated Core 0.6.6: " + checked.stderr.strip()
        )
    if portia_wheel.name != f"pds_portia-{EXPECTED_PORTIA_VERSION}-py3-none-any.whl":
        raise RuntimeError("Unexpected Portia wheel identity")
    if not fixtures.joinpath("issue_20/valid/01-capture_batch.json").is_file():
        raise RuntimeError("Synthetic fixtures directory was not found")

    with tempfile.TemporaryDirectory(prefix="portia57-installed-") as folder:
        root = Path(folder)
        environment = root / "venv"
        external = root / "external-cwd"
        external.mkdir()
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Only external capture libraries are resolved online. Core and Portia
        # still come exclusively from the authenticated, exact supplied wheels.
        env.pop("PIP_NO_INDEX", None)
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "reportlab>=4.2,<5",
                "qrcode>=7.4,<9",
                "pypdf>=5,<7",
            ],
            cwd=external,
            env=env,
        )
        env["PIP_NO_INDEX"] = "1"
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                "--no-index",
                str(core_wheel.resolve()),
                str(portia_wheel.resolve()),
            ],
            cwd=external,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=external, env=env)
        output = _run(
            [
                str(python),
                "-I",
                "-c",
                _INSTALLED_SMOKE,
                str(fixtures.resolve()),
                str(environment.resolve()),
            ],
            cwd=external,
            env=env,
        )
        print(output.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    parser.add_argument("--fixtures", type=Path, default=Path("tests/fixtures"))
    args = parser.parse_args()
    try:
        smoke(args.portia_wheel, args.core_wheel, args.fixtures)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(
            f"Issue #57 Core 0.6.6 installed qualification FAILED: {exc}",
            file=sys.stderr,
        )
        return 1
    print("Issue #57 Core 0.6.6 installed qualification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
