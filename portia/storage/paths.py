"""Pure deterministic path helpers for Portia persistence."""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from pds_core.routes import (
    class_module_dir,
    module_work_collection_dir,
    module_work_dir,
    safe_module_work_descendant,
)
from pds_core.routing_models import ModuleWorkRef

from portia.models.identifiers import validate_external_id, validate_portia_id
from portia.models.references import ExactPortiaWorkRef, PortiaWorkRef
from portia.storage.errors import PortiaPathError


def _work_model(work: PortiaWorkRef | ExactPortiaWorkRef) -> ModuleWorkRef:
    return ModuleWorkRef(module_id="portia", class_id=work.class_id, work_id=work.work_id)


def work_root(root: str | Path, work: PortiaWorkRef | ExactPortiaWorkRef) -> Path:
    return module_work_dir(root, _work_model(work))


def work_collection_root(root: str | Path, class_id: str) -> Path:
    """Return the bounded canonical Portia work collection for one class."""
    return module_work_collection_dir(root, class_id, "portia")


def work_manifest_path(root: str | Path, work: PortiaWorkRef | ExactPortiaWorkRef) -> Path:
    return safe_module_work_descendant(root, _work_model(work), "work.json")


def work_record_path(
    root: str | Path,
    work: PortiaWorkRef | ExactPortiaWorkRef,
    record_kind: str,
    record_id: str,
) -> Path:
    kind = validate_external_id(record_kind, "record_kind")
    identifier = validate_external_id(record_id, "record_id")
    return safe_module_work_descendant(
        root,
        _work_model(work),
        f"records/{kind}/{identifier}.json",
    )


def work_storage_history_path(
    root: str | Path,
    work: PortiaWorkRef | ExactPortiaWorkRef,
    record_kind: str,
    record_id: str,
    digest: str,
) -> Path:
    kind = validate_external_id(record_kind, "record_kind")
    identifier = validate_external_id(record_id, "record_id")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise PortiaPathError("storage-history digest must be lowercase SHA-256")
    return safe_module_work_descendant(
        root,
        _work_model(work),
        f"history/storage_revisions/{kind}/{identifier}/{digest}.json",
    )


def portia_root(root: str | Path) -> Path:
    return Path(root) / "portia"


def actors_root(root: str | Path) -> Path:
    return portia_root(root) / "actors"


def actor_root(root: str | Path, actor_id: str) -> Path:
    return actors_root(root) / validate_portia_id(actor_id, "actr_", "actor_id")


def actor_record_path(root: str | Path, actor_id: str) -> Path:
    return actor_root(root, actor_id) / "actor.json"


def actor_child_path(
    root: str | Path,
    actor_id: str,
    record_kind: str,
    record_id: str,
) -> Path:
    kind = validate_external_id(record_kind, "record_kind")
    identifier = validate_external_id(record_id, "record_id")
    return actor_root(root, actor_id) / "records" / kind / f"{identifier}.json"


def actor_storage_history_path(
    root: str | Path,
    actor_id: str,
    record_kind: str,
    record_id: str,
    digest: str,
) -> Path:
    kind = validate_external_id(record_kind, "record_kind")
    identifier = validate_external_id(record_id, "record_id")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise PortiaPathError("storage-history digest must be lowercase SHA-256")
    return (
        actor_root(root, actor_id)
        / "history"
        / "storage_revisions"
        / kind
        / identifier
        / f"{digest}.json"
    )


def actor_directory_removal_path(root: str | Path, removal_id: str) -> Path:
    identifier = validate_portia_id(removal_id, "rmv_", "removal_id")
    return portia_root(root) / "actor-directory-removals" / f"{identifier}.json"


def operations_root(root: str | Path) -> Path:
    return portia_root(root) / "operations"


def operation_root(root: str | Path, operation_id: str) -> Path:
    identifier = validate_portia_id(operation_id, "op_", "operation_id")
    return operations_root(root) / identifier


def operation_revision_path(root: str | Path, operation_id: str, revision: int) -> Path:
    if isinstance(revision, bool) or revision < 1:
        raise PortiaPathError("journal revision must be an integer >= 1")
    return operation_root(root, operation_id) / "revisions" / f"{revision}.json"


def operation_current_path(root: str | Path, operation_id: str) -> Path:
    return operation_root(root, operation_id) / "current.json"


def locks_root(root: str | Path) -> Path:
    return portia_root(root) / "locks"


def lock_path(root: str | Path, lock_id: str) -> Path:
    if not lock_id.startswith("lock_") or len(lock_id) != 69:
        raise PortiaPathError("invalid Portia lock identifier")
    suffix = lock_id[5:]
    if any(ch not in "0123456789abcdef" for ch in suffix):
        raise PortiaPathError("invalid Portia lock identifier")
    return locks_root(root) / f"{lock_id}.json"


def quarantine_root(root: str | Path, quarantine_id: str) -> Path:
    identifier = validate_portia_id(quarantine_id, "qnt_", "quarantine_id")
    return portia_root(root) / "quarantines" / identifier


def quarantine_revision_path(root: str | Path, quarantine_id: str, revision: int) -> Path:
    if isinstance(revision, bool) or revision < 1:
        raise PortiaPathError("quarantine revision must be an integer >= 1")
    return quarantine_root(root, quarantine_id) / "revisions" / f"{revision}.json"


def quarantine_current_path(root: str | Path, quarantine_id: str) -> Path:
    return quarantine_root(root, quarantine_id) / "current.json"


def finding_acknowledgement_path(root: str | Path, acknowledgement_id: str) -> Path:
    identifier = validate_portia_id(acknowledgement_id, "fack_", "acknowledgement_id")
    return portia_root(root) / "finding_acknowledgements" / f"{identifier}.json"


def finding_suppression_root(root: str | Path, suppression_id: str) -> Path:
    identifier = validate_portia_id(suppression_id, "fsup_", "suppression_id")
    return portia_root(root) / "finding_suppressions" / identifier


def finding_suppression_revision_path(root: str | Path, suppression_id: str, revision: int) -> Path:
    if isinstance(revision, bool) or revision < 1:
        raise PortiaPathError("suppression revision must be an integer >= 1")
    return finding_suppression_root(root, suppression_id) / "revisions" / f"{revision}.json"


def finding_suppression_current_path(root: str | Path, suppression_id: str) -> Path:
    return finding_suppression_root(root, suppression_id) / "current.json"


def _exact_work_from_scope(scope: dict[str, object]) -> ExactPortiaWorkRef:
    work = scope.get("work_ref")
    if not isinstance(work, dict):
        raise PortiaPathError("work projection scope requires work_ref")
    try:
        return ExactPortiaWorkRef(
            module_id=str(work.get("module_id", "portia")),
            class_id=str(work["class_id"]),
            work_id=str(work["work_id"]),
            work_kind=str(work["work_kind"]),
            contract_version=str(work["contract_version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PortiaPathError("work projection scope has an invalid work_ref") from exc


def derived_projection_root(
    root: str | Path,
    projection_kind: str,
    scope: object,
) -> Path:
    """Return the accepted derived-projection root for one exact scope.

    Work-scoped projections remain beneath the owning work ``derived/`` boundary.
    Class scope uses the Core class/module boundary.  Workspace, operation, and
    graph scopes use Portia's bounded workspace-owned derived namespace.
    """
    kind = validate_external_id(projection_kind, "projection_kind")
    if not isinstance(scope, dict):
        raise PortiaPathError("projection scope must be an object")
    scope_kind = scope.get("scope")

    if scope_kind == "work":
        work = _exact_work_from_scope(scope)
        return work_root(root, work) / "derived" / kind

    if scope_kind == "class":
        class_id = validate_external_id(scope.get("class_id"), "class_id")
        return class_module_dir(root, class_id, "portia") / "derived" / kind

    if scope_kind == "workspace":
        workspace_id = scope.get("workspace_id")
        if workspace_id is None:
            raise PortiaPathError(
                "workspace-scoped derived state requires an authoritative workspace_id; "
                "Portia must not manufacture one from a filesystem path"
            )
        identity = validate_external_id(workspace_id, "workspace_id")
        return portia_root(root) / "derived" / kind / f"workspace_{identity}"

    if scope_kind == "operation":
        operation = scope.get("operation_ref")
        if not isinstance(operation, dict):
            raise PortiaPathError("operation scope requires operation_ref")
        operation_id = validate_portia_id(
            operation.get("operation_id"), "op_", "operation_id"
        )
        return portia_root(root) / "derived" / kind / f"operation_{operation_id}"

    if scope_kind == "graph":
        graph_id = validate_external_id(scope.get("graph_id"), "graph_id")
        return portia_root(root) / "derived" / kind / f"graph_{graph_id}"

    raise PortiaPathError(f"unsupported projection scope: {scope_kind!r}")


def derived_generation_root(
    root: str | Path,
    projection_kind: str,
    scope: object,
    generation_id: str,
) -> Path:
    generation = validate_portia_id(generation_id, "dgen_", "generation_id")
    return (
        derived_projection_root(root, projection_kind, scope)
        / "generations"
        / generation
    )


def derived_metadata_path(
    root: str | Path,
    projection_kind: str,
    scope: object,
    generation_id: str,
) -> Path:
    return (
        derived_generation_root(root, projection_kind, scope, generation_id)
        / "metadata.json"
    )


def derived_data_path(
    root: str | Path,
    projection_kind: str,
    scope: object,
    generation_id: str,
) -> Path:
    return (
        derived_generation_root(root, projection_kind, scope, generation_id)
        / "data.json"
    )


def derived_current_path(
    root: str | Path,
    projection_kind: str,
    scope: object,
) -> Path:
    return derived_projection_root(root, projection_kind, scope) / "current.json"


def validate_workspace_relative_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or value == "" or value != value.strip() or "\\" in value:
        raise PortiaPathError("workspace-relative path must be nonempty normalized POSIX text")
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        raise PortiaPathError("workspace-relative path must be relative")
    if any(part in {"", ".", ".."} for part in posix.parts):
        raise PortiaPathError("workspace-relative path contains unsafe components")
    return posix


def resolve_workspace_relative(root: str | Path, relative_path: object) -> Path:
    relative = validate_workspace_relative_path(relative_path)
    return Path(root).joinpath(*relative.parts)


def workspace_relative(root: str | Path, path: str | Path) -> str:
    base = Path(root).resolve(strict=False)
    candidate = Path(path).resolve(strict=False)
    try:
        relative = candidate.relative_to(base)
    except ValueError as exc:
        raise PortiaPathError("path is outside the selected workspace") from exc
    if not relative.parts:
        raise PortiaPathError("path must identify a workspace descendant")
    return PurePosixPath(*relative.parts).as_posix()
