"""Error hierarchy for Portia runtime model conversion and validation."""

from __future__ import annotations


class PortiaModelError(ValueError):
    """Base class for Portia runtime-model failures."""


class PortiaWireError(PortiaModelError):
    """Raised when JSON-native input violates the selected public contract."""


class PortiaLocalValidationError(PortiaModelError):
    """Raised when an already-typed local value violates a model invariant."""


class UnsupportedContractError(PortiaModelError):
    """Raised when a contract/version is outside the Issue #37 runtime surface."""
