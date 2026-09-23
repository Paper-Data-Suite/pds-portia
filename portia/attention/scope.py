"""Exact Core class and Portia work discovery for native attention orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pds_core.classes import list_class_folders
from pds_core.identifiers import IdentifierValidationError, validate_identifier
from pds_core.routes import classes_dir

from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaCorruptionError
from portia.storage.repository import PortiaRepository, StoredRecord

_SUPPORTED_WORK_ROOTS: tuple[tuple[str, str], ...] = (
    ("event", "2"),
    ("support_process", "1"),
)


@dataclass(frozen=True, slots=True)
class WorkspaceClassDiscovery:
    """Core-owned valid classes plus bounded evidence of skipped malformed dirs."""

    class_ids: tuple[str, ...]
    incomplete: bool = False


def class_exists(workspace_root: str | Path, class_id: str) -> bool:
    """Return whether Core exposes the requested exact class folder."""
    try:
        validate_identifier(class_id, "class_id")
    except IdentifierValidationError:
        return False
    return any(
        folder.class_id == class_id
        for folder in list_class_folders(workspace_root)
    )


def discover_workspace_classes(
    workspace_root: str | Path,
) -> WorkspaceClassDiscovery:
    """Discover Core class scopes and detect malformed class directories.

    Core's ``list_class_folders`` remains the positive class authority. The
    canonical Core classes collection is inspected only to determine whether
    Core skipped a directory because its identity was malformed; no Portia
    storage semantics are inferred from directory names.
    """
    folders = list_class_folders(workspace_root)
    class_ids = tuple(sorted(folder.class_id for folder in folders))
    accepted = set(class_ids)
    root = classes_dir(workspace_root)

    try:
        entries = tuple(sorted(root.iterdir(), key=lambda entry: entry.name))
    except (FileNotFoundError, NotADirectoryError):
        return WorkspaceClassDiscovery(class_ids=class_ids)
    except OSError as exc:
        raise PortiaCorruptionError(
            "Core class collection could not be inspected safely"
        ) from exc

    incomplete = False
    for entry in entries:
        try:
            is_dir = entry.is_dir()
        except OSError:
            incomplete = True
            continue
        if not is_dir:
            continue
        try:
            validate_identifier(entry.name, "class_id")
        except IdentifierValidationError:
            incomplete = True
            continue
        if entry.name not in accepted:
            incomplete = True

    return WorkspaceClassDiscovery(
        class_ids=class_ids,
        incomplete=incomplete,
    )


def _work_ref(stored: StoredRecord, class_id: str) -> ExactPortiaWorkRef:
    data = stored.record.to_dict()
    work_id = data.get("work_id")
    work_kind = data.get("work_kind")
    if not isinstance(work_id, str) or not isinstance(work_kind, str):
        raise PortiaCorruptionError(
            "canonical Portia work root has incomplete exact identity"
        )
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind=work_kind,
        contract_version=stored.record.contract_version,
    )


def class_work_refs(
    repository: PortiaRepository,
    class_id: str,
) -> tuple[ExactPortiaWorkRef, ...]:
    """Strictly discover supported current Portia work roots in one class."""
    refs: list[ExactPortiaWorkRef] = []
    for work_kind, version in _SUPPORTED_WORK_ROOTS:
        refs.extend(
            _work_ref(stored, class_id)
            for stored in repository.list_works(
                class_id,
                work_kind=work_kind,
                version=version,
            )
        )
    return tuple(
        sorted(
            set(refs),
            key=lambda work: (
                work.class_id,
                work.work_kind,
                work.work_id,
                work.contract_version,
            ),
        )
    )
