from __future__ import annotations

from pathlib import Path

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.attention.derived_sources import DERIVED_ATTENTION_PROJECTIONS
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.derived import DerivedStore
from portia.storage.paths import derived_current_path, derived_data_path
from portia.workflows import IntegrityWorkflowService
from tests.test_workflow_integrity_operators import (
    _completed_operation,
    _install_generation,
)
from tests.workflow_helpers import event_ref

AS_OF = ExplicitOffsetTimestamp("2026-09-16T13:00:00-04:00")


def _query() -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(event_ref()),
        as_of=AS_OF,
        attention_codes=("portia_derived_state_stale",),
    )


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (
                str(path.relative_to(root)),
                path.read_bytes(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def _install_current_projection(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    operation_ref = _completed_operation(tmp_path)
    scope = IntegrityWorkflowService.operation_scope("op_integrity_authority")
    _install_generation(
        tmp_path,
        scope,
        [],
        operation_ref,
        generation_id="dgen_attention_slice5",
    )
    return operation_ref, scope


def test_closed_registry_contains_only_current_production_projection() -> None:
    assert [
        (
            definition.projection_kind,
            definition.scope_kind,
            definition.missing_is_optional,
        )
        for definition in DERIVED_ATTENTION_PROJECTIONS
    ] == [
        ("active_integrity_finding_index", "operation", True),
    ]


def test_optional_missing_projection_is_not_stale_attention(tmp_path: Path) -> None:
    _completed_operation(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    assert report.evaluation == "evaluated"
    assert report.items == ()
    assert report.notices == ()


def test_fresh_selected_projection_is_not_stale_attention(tmp_path: Path) -> None:
    _install_current_projection(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    assert report.items == ()
    assert report.notices == ()


def test_stale_selected_projection_is_derived_attention(tmp_path: Path) -> None:
    _operation_ref, _scope = _install_current_projection(tmp_path)
    (tmp_path / "integrity-authority-source.json").write_bytes(
        b'{"authority":"changed"}\n'
    )

    report = AttentionQueryService(tmp_path).query(_query())

    stale = [
        item for item in report.items
        if item.code == "portia_derived_state_stale"
    ]
    assert len(stale) == 1
    assert stale[0].source_ref.kind == "derived_projection"
    assert stale[0].reason_codes == (
        "projection_active_integrity_finding_index",
        "scope_operation",
    )
    assert report.notices == ()


def test_corrupt_selected_pointer_is_partial_not_stale(tmp_path: Path) -> None:
    _operation_ref, scope = _install_current_projection(tmp_path)
    derived_current_path(
        tmp_path,
        "active_integrity_finding_index",
        scope,
    ).write_bytes(b"{not-json")

    report = AttentionQueryService(tmp_path).query(_query())

    assert report.evaluation == "evaluated"
    assert report.items == ()
    assert len(report.notices) == 1
    assert report.notices[0].code == "portia_attention_partial"


def test_selected_data_fingerprint_mismatch_is_partial_not_stale(
    tmp_path: Path,
) -> None:
    _operation_ref, scope = _install_current_projection(tmp_path)
    current = DerivedStore(tmp_path).load_current(
        "active_integrity_finding_index",
        scope,
        require_fresh=False,
    )
    generation_id = current.metadata.to_dict()["generation_id"]
    assert isinstance(generation_id, str)
    derived_data_path(
        tmp_path,
        "active_integrity_finding_index",
        scope,
        generation_id,
    ).write_bytes(b'{"findings":[],"unexpected":true}\n')

    report = AttentionQueryService(tmp_path).query(_query())

    assert report.items == ()
    assert len(report.notices) == 1
    assert report.notices[0].code == "portia_attention_partial"


def test_stale_query_is_zero_write(tmp_path: Path) -> None:
    _install_current_projection(tmp_path)
    (tmp_path / "integrity-authority-source.json").write_bytes(
        b'{"authority":"changed"}\n'
    )
    before = _snapshot(tmp_path)

    report = AttentionQueryService(tmp_path).query(_query())

    assert any(
        item.code == "portia_derived_state_stale"
        for item in report.items
    )
    assert _snapshot(tmp_path) == before
