from __future__ import annotations

from pathlib import Path

from portia.menu.identifiers import PortiaIdGenerator
from portia.models.references import ExactPortiaWorkRef
from portia.storage.paths import (
    derived_metadata_path,
    finding_suppression_revision_path,
    legacy_derived_metadata_path,
    operation_revision_path,
    quarantine_revision_path,
)

REPRESENTATIVE_DEEP_ROOT_LENGTH = 119
SHALLOW_RELATIVE_PATH_BUDGET = 96
LEGACY_WINDOWS_REFERENCE_LENGTH = 260


def _generated(prefix: str) -> str:
    return PortiaIdGenerator(token_source=lambda: "a" * 32).new(prefix)


def _relative_text(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _projected_absolute_length(relative: str) -> int:
    return REPRESENTATIVE_DEEP_ROOT_LENGTH + 1 + len(relative)


def test_routine_workspace_level_series_remain_shallow_with_generated_ids() -> None:
    root = Path("workspace")
    operation = _generated("op_")
    quarantine = _generated("qnt_")
    suppression = _generated("fsup_")
    export_id = _generated("pexp_")

    relatives = {
        "operation": _relative_text(
            operation_revision_path(root, operation, 123),
            root,
        ),
        "quarantine": _relative_text(
            quarantine_revision_path(root, quarantine, 123),
            root,
        ),
        "suppression": _relative_text(
            finding_suppression_revision_path(root, suppression, 123),
            root,
        ),
        "teacher_reference_export": (
            f"portia/exports/{export_id}/artifact.html"
        ),
    }

    assert {name: len(value) for name, value in relatives.items()} == {
        "operation": 72,
        "quarantine": 74,
        "suppression": 84,
        "teacher_reference_export": 66,
    }
    assert all(
        len(value) <= SHALLOW_RELATIVE_PATH_BUDGET
        for value in relatives.values()
    )
    assert all(
        _projected_absolute_length(value) < LEGACY_WINDOWS_REFERENCE_LENGTH
        for value in relatives.values()
    )


def test_teacher_reference_export_path_does_not_expand_with_display_text() -> None:
    export_id = _generated("pexp_")
    artifact = f"portia/exports/{export_id}/artifact.html"
    provenance = f"portia/exports/{export_id}/export.json"

    sensitive_display_values = (
        "Student Name " + "x" * 256,
        "Event title " + "y" * 256,
        "source-file-" + "z" * 256 + ".pdf",
    )
    for value in sensitive_display_values:
        assert value not in artifact
        assert value not in provenance

    assert artifact.endswith("/artifact.html")
    assert provenance.endswith("/export.json")


def test_derived_scope_geometry_is_explicit_remaining_path_pressure() -> None:
    root = Path("workspace")
    token = "a" * 32
    work = ExactPortiaWorkRef(
        module_id="portia",
        class_id="class_english11_p2_2026_2027",
        work_id=f"evt_{token}",
        work_kind="event",
        contract_version="2",
    )
    generation_id = f"dgen_{token}"
    projection = "current_state_view"

    scopes: dict[str, dict[str, object]] = {
        "work": {"scope": "work", "work_ref": work.to_dict()},
        "class": {
            "scope": "class",
            "class_id": "class_english11_p2_2026_2027",
        },
        "workspace": {
            "scope": "workspace",
            "workspace_id": "local_workspace_2026",
        },
        "operation": {
            "scope": "operation",
            "operation_ref": {
                "operation_id": f"op_{token}",
                "contract_version": "2",
            },
        },
        "graph": {
            "scope": "graph",
            "graph_id": "graph_" + "g" * 32,
        },
    }

    legacy_lengths = {
        name: len(
            _relative_text(
                legacy_derived_metadata_path(
                    root,
                    projection,
                    scope,
                    generation_id,
                ),
                root,
            )
        )
        for name, scope in scopes.items()
    }

    assert legacy_lengths == {
        "work": 184,
        "class": 142,
        "workspace": 128,
        "operation": 143,
        "graph": 142,
    }

    legacy_projected = {
        name: REPRESENTATIVE_DEEP_ROOT_LENGTH + 1 + length
        for name, length in legacy_lengths.items()
    }
    assert legacy_projected == {
        "work": 304,
        "class": 262,
        "workspace": 248,
        "operation": 263,
        "graph": 262,
    }

    bounded_lengths = {
        name: len(
            _relative_text(
                derived_metadata_path(
                    root,
                    projection,
                    scope,
                    generation_id,
                ),
                root,
            )
        )
        for name, scope in scopes.items()
    }
    assert bounded_lengths == {
        "work": 115,
        "class": 115,
        "workspace": 115,
        "operation": 115,
        "graph": 115,
    }
    assert all(
        _projected_absolute_length(
            _relative_text(
                derived_metadata_path(
                    root,
                    projection,
                    scope,
                    generation_id,
                ),
                root,
            )
        )
        == 235
        for scope in scopes.values()
    )

    # 260 is only a historical pressure reference, not Portia's universal limit.
    assert legacy_projected["work"] > LEGACY_WINDOWS_REFERENCE_LENGTH
    assert legacy_projected["class"] > LEGACY_WINDOWS_REFERENCE_LENGTH
    assert legacy_projected["operation"] > LEGACY_WINDOWS_REFERENCE_LENGTH
