"""Installed Portia module-operations profile for Core v1."""

from __future__ import annotations

from importlib import import_module
from typing import Final, cast

from pds_core.module_operations import (
    MODULE_OPERATIONS_CONTRACT_VERSION,
    ModuleAttentionProvider,
    ModuleAttentionReport,
    ModuleOperationsProfile,
    ModuleOperationsRequest,
    ModuleReadinessProvider,
    ModuleReadinessReport,
    validate_module_operations_profile,
)

PORTIA_MODULE_ID: Final[str] = "portia"


def _load_attention_provider() -> ModuleAttentionProvider:
    """Load the dedicated attention adapter only when attention is invoked."""

    module = import_module("portia.attention_provider")
    return cast(
        ModuleAttentionProvider,
        getattr(module, "evaluate_portia_attention"),
    )


def _load_readiness_provider() -> ModuleReadinessProvider:
    """Load the dedicated readiness adapter only when readiness is invoked."""

    module = import_module("portia.readiness_provider")
    return cast(
        ModuleReadinessProvider,
        getattr(module, "evaluate_portia_readiness"),
    )


def evaluate_portia_attention(
    request: ModuleOperationsRequest,
    /,
) -> ModuleAttentionReport:
    """Lazily evaluate Portia-owned attention for one neutral Core request."""

    return _load_attention_provider()(request)


def evaluate_portia_readiness(
    request: ModuleOperationsRequest,
    /,
) -> ModuleReadinessReport:
    """Lazily evaluate Portia-owned readiness for one neutral Core request."""

    return _load_readiness_provider()(request)


def get_module_operations_profile() -> ModuleOperationsProfile:
    """Return Portia's validated Core v1 operations profile."""

    return validate_module_operations_profile(
        ModuleOperationsProfile(
            module_id=PORTIA_MODULE_ID,
            supported_core_operations_contract_versions=frozenset(
                {MODULE_OPERATIONS_CONTRACT_VERSION}
            ),
            readiness_provider=evaluate_portia_readiness,
            attention_provider=evaluate_portia_attention,
        )
    )


__all__ = [
    "PORTIA_MODULE_ID",
    "evaluate_portia_attention",
    "evaluate_portia_readiness",
    "get_module_operations_profile",
]
