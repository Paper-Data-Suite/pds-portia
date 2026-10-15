from __future__ import annotations

import importlib.util
from pathlib import Path

from portia.models import runtime_coverage
from portia.models.records import MODEL_REGISTRY

ROOT = Path(__file__).resolve().parents[1]


def _load_validator():
    path = ROOT / "scripts" / "validate_issue56_closeout.py"
    spec = importlib.util.spec_from_file_location("issue56_closeout", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue56_closeout_validator_accepts_repository() -> None:
    validator = _load_validator()
    assert validator.validate(ROOT) == ()


def test_issue56_has_no_active_v03_runtime_deferrals() -> None:
    assert not [
        entry
        for entry in runtime_coverage()
        if entry.disposition == "deferred_v0_3"
    ]


def test_issue56_runtime_model_count_is_84() -> None:
    assert len(MODEL_REGISTRY) == 84


def test_issue56_authoritative_repository_gate_is_wired() -> None:
    source = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    assert "scripts/validate_issue56_closeout.py" in source
    assert "scripts/smoke_test_issue56_import_chain_runtime_wheel.py" in source
    assert "Portia Issue #56 repository qualification passed" in source


def test_issue56_git_blob_digest_is_stable_across_windows_crlf(tmp_path: Path) -> None:
    validator = _load_validator()
    schema = tmp_path / "fixture.schema.json"
    canonical = b'{\n  "kind": "capture_batch"\n}\n'
    schema.write_bytes(canonical)
    expected_blob = validator._git_blob_sha1(schema)

    schema.write_bytes(canonical.replace(b"\n", b"\r\n"))
    assert validator._git_blob_sha1(schema) == expected_blob


def test_issue56_git_blob_digest_rejects_content_drift(tmp_path: Path) -> None:
    validator = _load_validator()
    schema = tmp_path / "fixture.schema.json"
    schema.write_bytes(b'{"kind": "capture_batch"}\n')
    expected_blob = validator._git_blob_sha1(schema)

    schema.write_bytes(b'{"kind": "capture_review"}\r\n')
    assert validator._git_blob_sha1(schema) != expected_blob


def test_issue56_wrapped_design_prose_marker_is_accepted() -> None:
    validator = _load_validator()
    design = (
        ROOT
        / "docs/design/issue-56-v03-capture-import-runtime-reconciliation.md"
    ).read_text(encoding="utf-8")
    normalized_design = " ".join(design.split())
    assert (
        "structured human-confirmed classroom-session analytics"
        in normalized_design
    )
    assert validator.validate(ROOT) == ()
