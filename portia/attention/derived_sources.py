"""Closed derived-projection attention registry for Issue #49 Slice 5."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias

from portia.attention.models import (
    OpaqueAttentionSourceRef,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionQuery,
)
from portia.attention.operational_sources import OperationalAttentionSourceService
from portia.attention.taxonomy import require_attention_definition
from portia.storage.derived import DerivedStore
from portia.storage.errors import PortiaRecoveryRequiredError
from portia.workflows.integrity import IntegrityWorkflowService

DerivedAttentionScopeKind: TypeAlias = Literal["operation"]


@dataclass(frozen=True, slots=True)
class DerivedAttentionProjectionDefinition:
    """One explicitly registered production derived projection family."""

    projection_kind: str
    scope_kind: DerivedAttentionScopeKind
    missing_is_optional: bool


DERIVED_ATTENTION_PROJECTIONS: Final[
    tuple[DerivedAttentionProjectionDefinition, ...]
] = (
    DerivedAttentionProjectionDefinition(
        projection_kind="active_integrity_finding_index",
        scope_kind="operation",
        missing_is_optional=True,
    ),
)


def _query_wants_stale(query: PortiaAttentionQuery) -> bool:
    code = "portia_derived_state_stale"
    definition = require_attention_definition(code)
    if query.attention_codes and code not in query.attention_codes:
        return False
    if (
        query.attention_classes
        and definition.attention_class not in query.attention_classes
    ):
        return False
    return True


def _context(query: PortiaAttentionQuery) -> PortiaAttentionContext:
    scope = query.scope
    if scope.kind == "work":
        assert scope.work_ref is not None
        return PortiaAttentionContext(
            class_id=scope.work_ref.class_id,
            work_ref=scope.work_ref,
        )
    if scope.kind == "class":
        assert scope.class_id is not None
        return PortiaAttentionContext(class_id=scope.class_id)
    return PortiaAttentionContext()


def _source_identifier(projection_kind: str, operation_id: str) -> str:
    digest = hashlib.sha256(
        f"{projection_kind}\x00operation\x00{operation_id}".encode("utf-8")
    ).hexdigest()
    return f"projection_{digest}"


class DerivedAttentionSourceService:
    """Read-only stale-state interpretation over a closed projection registry."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        operational: OperationalAttentionSourceService,
    ) -> None:
        self.root = Path(workspace_root)
        self.operational = operational
        self.store = DerivedStore(self.root)

    def items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        """Return stale registered projections without rebuilding anything."""
        if not _query_wants_stale(query):
            return ()

        context = _context(query)
        operation_ids = self.operational.operation_ids_for_scope(
            query.scope,
            selected_only=True,
        )
        items: list[PortiaAttentionItem] = []
        for definition in DERIVED_ATTENTION_PROJECTIONS:
            if definition.scope_kind != "operation":
                raise RuntimeError(
                    "unsupported code-owned derived attention scope kind"
                )
            for operation_id in operation_ids:
                scope = IntegrityWorkflowService.operation_scope(operation_id)
                if not self.store.has_current_pointer(
                    definition.projection_kind,
                    scope,
                ):
                    if definition.missing_is_optional:
                        continue
                    raise PortiaRecoveryRequiredError(
                        "required registered derived state is unavailable"
                    )

                try:
                    self.store.load_current(
                        definition.projection_kind,
                        scope,
                        require_fresh=True,
                    )
                except PortiaRecoveryRequiredError:
                    items.append(
                        PortiaAttentionItem(
                            code="portia_derived_state_stale",
                            source_ref=OpaqueAttentionSourceRef(
                                kind="derived_projection",
                                identifier=_source_identifier(
                                    definition.projection_kind,
                                    operation_id,
                                ),
                            ),
                            context=context,
                            reason_codes=(
                                f"projection_{definition.projection_kind}",
                                "scope_operation",
                            ),
                        )
                    )

        return tuple(items)
