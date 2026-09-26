"""Ephemeral process-local context for the Portia teacher menu."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pds_core.identifiers import validate_identifier
from pds_core.workspace import resolve_workspace_root

from portia.models.identifiers import validate_portia_id

WorkKind = Literal["event", "support_process"]


@dataclass(slots=True)
class MenuSessionContext:
    """Navigation convenience only; no field is durable Portia state."""

    workspace_root: Path | None = None
    selected_class_id: str | None = None
    selected_work_kind: WorkKind | None = None
    selected_work_id: str | None = None
    local_operator_label: str | None = None

    def resolve_workspace(self, explicit_root: str | Path | None = None) -> Path:
        """Resolve Core workspace authority and invalidate stale target context."""

        resolved = resolve_workspace_root(explicit_root)
        if self.workspace_root is not None and self.workspace_root != resolved:
            self.clear_target_context()
        self.workspace_root = resolved
        return resolved

    def clear_target_context(self) -> None:
        """Forget selected canonical targets without changing any stored record."""

        self.selected_class_id = None
        self.selected_work_kind = None
        self.selected_work_id = None

    def remember_local_operator(self, display_label: str) -> None:
        """Remember process-local write attribution; this is not authentication."""

        normalized = " ".join(display_label.split())
        if not normalized:
            raise ValueError("local operator display label must not be blank")
        self.local_operator_label = normalized

    def remember_class(self, class_id: str) -> None:
        """Remember one exact Core class identifier for process-local navigation."""

        validated = validate_identifier(class_id, "class_id")
        if self.selected_class_id != validated:
            self.selected_work_kind = None
            self.selected_work_id = None
        self.selected_class_id = validated

    def remember_work(
        self,
        *,
        class_id: str,
        work_kind: WorkKind,
        work_id: str,
    ) -> None:
        """Remember one exact Portia work after validating its family identity."""

        prefixes: dict[WorkKind, str] = {
            "event": "evt_",
            "support_process": "sup_",
        }
        self.remember_class(class_id)
        validated_work = validate_portia_id(
            work_id,
            prefixes[work_kind],
            "work_id",
        )
        self.selected_work_kind = work_kind
        self.selected_work_id = validated_work
