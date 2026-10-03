from __future__ import annotations

import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import (
    ClassMetadataReadError,
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import class_folder, write_class_roster
from pds_core.module_operations import (
    ModuleAttentionReport,
    ModuleAttentionSummary,
    ModuleOperationsRequest,
    invoke_module_operations,
    invoke_module_readiness,
)
from pds_core.rosters import create_roster
from pds_core.workspace import (
    WorkspaceRootError,
    WorkspaceStatus,
    ensure_workspace_root,
)

import portia.pds_operations as operations
import portia.readiness_provider as provider
from portia.pds_operations import get_module_operations_profile
from portia.readiness_provider import (
    CLASS_NOT_READY_CODE,
    READINESS_UNAVAILABLE_CODE,
    WORKSPACE_NOT_READY_CODE,
    evaluate_portia_readiness,
)


def _make_ready_class(
    root: Path,
    *,
    class_id: str = "class_a",
    school_year: str = "2026-2027",
) -> None:
    ensure_workspace_root(root)
    created_at = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            class_id,
            school_year,
            created_at=created_at,
        ),
    )
    write_class_roster(
        root,
        create_roster(
            class_id,
            (
                {
                    "student_id": "student_1",
                    "last_name": "Example",
                    "first_name": "Student",
                    "period": "2",
                },
            ),
        ),
    )


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_missing_request_workspace_never_resolves_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))

    def forbidden_inspection(_root: object = None) -> object:
        raise AssertionError("implicit workspace resolution is forbidden")

    monkeypatch.setattr(provider, "inspect_workspace_root", forbidden_inspection)

    report = evaluate_portia_readiness(ModuleOperationsRequest())

    assert report.evaluation == "unavailable"
    assert report.ready is None
    assert tuple(notice.code for notice in report.notices) == (
        READINESS_UNAVAILABLE_CODE,
    )


def test_missing_explicit_workspace_is_unavailable(tmp_path: Path) -> None:
    root = tmp_path / "missing"

    report = evaluate_portia_readiness(ModuleOperationsRequest(workspace_root=root))

    assert report.evaluation == "unavailable"
    assert report.ready is None
    assert not root.exists()


def test_existing_non_directory_workspace_is_not_ready(tmp_path: Path) -> None:
    root = tmp_path / "workspace-file"
    root.write_text("not a directory", encoding="utf-8")

    report = evaluate_portia_readiness(ModuleOperationsRequest(workspace_root=root))

    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert tuple(notice.code for notice in report.notices) == (
        WORKSPACE_NOT_READY_CODE,
    )


def test_known_nonwritable_workspace_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    status = WorkspaceStatus(
        root=tmp_path,
        source="explicit",
        exists=True,
        is_dir=True,
        is_writable=False,
        config_path=tmp_path / "config.json",
        default_root=tmp_path / "default",
    )
    monkeypatch.setattr(provider, "inspect_workspace_root", lambda _root: status)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path)
    )

    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert report.notices[0].code == WORKSPACE_NOT_READY_CODE


def test_existing_writable_workspace_is_ready_without_class(tmp_path: Path) -> None:
    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path)
    )

    assert report.evaluation == "evaluated"
    assert report.ready is True
    assert report.notices == ()


def test_safely_missing_exact_class_is_not_ready(tmp_path: Path) -> None:
    ensure_workspace_root(tmp_path)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="missing_class")
    )

    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert report.notices[0].code == CLASS_NOT_READY_CODE


def test_valid_exact_core_class_is_ready_without_portia_work(tmp_path: Path) -> None:
    _make_ready_class(tmp_path)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a")
    )

    assert report.evaluation == "evaluated"
    assert report.ready is True
    assert report.notices == ()
    assert not tuple(tmp_path.rglob("portia"))


def test_active_school_year_does_not_invent_readiness_blocker(tmp_path: Path) -> None:
    _make_ready_class(tmp_path, school_year="2026-2027")

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            class_id="class_a",
            active_school_year="2025-2026",
        )
    )

    assert report.evaluation == "evaluated"
    assert report.ready is True


def test_readable_invalid_class_metadata_is_not_ready(tmp_path: Path) -> None:
    _make_ready_class(tmp_path)
    folder = class_folder(tmp_path, "class_a")
    folder.metadata_path.write_text("{not-json", encoding="utf-8")

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a")
    )

    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert report.notices[0].code == CLASS_NOT_READY_CODE


def test_readable_invalid_roster_encoding_is_not_ready(tmp_path: Path) -> None:
    _make_ready_class(tmp_path)
    folder = class_folder(tmp_path, "class_a")
    folder.roster_path.write_bytes(b"\xff\xfe\xff")

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a")
    )

    assert report.evaluation == "evaluated"
    assert report.ready is False
    assert report.notices[0].code == CLASS_NOT_READY_CODE


def test_uninspectable_class_metadata_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _make_ready_class(tmp_path)

    def unreadable(*_args: object, **_kwargs: object) -> object:
        try:
            raise OSError("synthetic access failure")
        except OSError as cause:
            raise ClassMetadataReadError("synthetic read failure") from cause

    monkeypatch.setattr(provider, "load_class_metadata_for_class", unreadable)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a")
    )

    assert report.evaluation == "unavailable"
    assert report.ready is None
    assert report.notices[0].code == READINESS_UNAVAILABLE_CODE


def test_workspace_inspection_failure_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def unavailable(_root: object) -> object:
        raise WorkspaceRootError("synthetic inspection failure")

    monkeypatch.setattr(provider, "inspect_workspace_root", unavailable)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path)
    )

    assert report.evaluation == "unavailable"
    assert report.ready is None


def test_readiness_is_byte_for_byte_read_only(tmp_path: Path) -> None:
    _make_ready_class(tmp_path)
    before = _snapshot(tmp_path)

    report = evaluate_portia_readiness(
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a")
    )

    assert report.ready is True
    assert _snapshot(tmp_path) == before


def test_ready_true_and_nonempty_attention_are_independently_valid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _make_ready_class(tmp_path)

    def fake_attention(_request: ModuleOperationsRequest) -> ModuleAttentionReport:
        return ModuleAttentionReport(
            evaluation="evaluated",
            summaries=(
                ModuleAttentionSummary(
                    code="portia_follow_up_due",
                    label="Follow-Ups due",
                    count=1,
                    class_id="class_a",
                ),
            ),
        )

    monkeypatch.setattr(
        operations,
        "_load_attention_provider",
        lambda: fake_attention,
    )

    readiness, attention = invoke_module_operations(
        get_module_operations_profile(),
        ModuleOperationsRequest(workspace_root=tmp_path, class_id="class_a"),
    )

    assert readiness.code == "module_operations.evaluated"
    assert readiness.report is not None
    assert readiness.report.ready is True
    assert attention.code == "module_operations.evaluated"
    assert attention.report is not None
    assert attention.report.summaries


def test_unexpected_readiness_exception_is_left_for_core_failure_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def unexpected(_root: object) -> object:
        raise AssertionError("synthetic programming failure")

    monkeypatch.setattr(provider, "inspect_workspace_root", unexpected)

    result = invoke_module_readiness(
        get_module_operations_profile(),
        ModuleOperationsRequest(workspace_root=tmp_path),
    )

    assert result.code == "module_operations.provider_failed"
    assert result.report is None


def test_invalid_readiness_result_remains_core_result_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        operations,
        "_load_readiness_provider",
        lambda: lambda _request: object(),
    )

    result = invoke_module_readiness(
        get_module_operations_profile(),
        ModuleOperationsRequest(workspace_root=tmp_path),
    )

    assert result.code == "module_operations.result_invalid"
    assert result.report is None


def test_readiness_source_is_separate_from_attention_and_mutation() -> None:
    source = inspect.getsource(provider)

    for forbidden in (
        "AttentionQueryService",
        "evaluate_portia_attention",
        "ensure_workspace_root",
        ".mkdir(",
        ".write_text(",
        ".write_bytes(",
        "tempfile",
    ):
        assert forbidden not in source
