"""Deterministic Portia persistence errors."""

from __future__ import annotations


class PortiaStorageError(RuntimeError):
    """Base class for Portia persistence failures."""


class PortiaNotFoundError(PortiaStorageError):
    """A required persisted artifact is absent."""


class PortiaConflictError(PortiaStorageError):
    """Observed persisted state does not match the caller's expected state."""


class PortiaCorruptionError(PortiaStorageError):
    """Persisted bytes cannot be trusted as the expected Portia artifact."""


class PortiaOwnershipError(PortiaStorageError):
    """A record does not agree with the canonical owner implied by its path."""


class PortiaPathError(PortiaStorageError):
    """A requested persistence path is unsafe or outside its allowed root."""


class PortiaLockError(PortiaStorageError):
    """A Portia operation lock could not be acquired or released safely."""


class PortiaRecoveryRequiredError(PortiaStorageError):
    """Durable state requires explicit recovery before ordinary mutation."""


class PortiaAmbiguousRecoveryError(PortiaRecoveryRequiredError):
    """Durable evidence admits more than one plausible recovery continuation."""


class PortiaQuarantinedError(PortiaRecoveryRequiredError):
    """An active Quarantine explicitly blocks the requested ordinary effect."""


class PortiaOperationPartialCommitError(PortiaRecoveryRequiredError):
    """Canonical effects became durable and require explicit operation recovery."""

    def __init__(
        self,
        *,
        operation_id: str,
        accepted_steps: tuple[str, ...],
        held_lock_ids: tuple[str, ...],
    ) -> None:
        self.operation_id = operation_id
        self.accepted_steps = accepted_steps
        self.held_lock_ids = held_lock_ids
        super().__init__(
            "operation has accepted durable effects and requires explicit recovery: "
            f"{operation_id}"
        )
