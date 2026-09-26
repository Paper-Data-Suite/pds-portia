"""Application-level opaque Portia identifier generation."""

from __future__ import annotations

import secrets
from collections.abc import Callable

from portia.models.identifiers import validate_portia_id

TokenSource = Callable[[], str]


def _random_token() -> str:
    return secrets.token_hex(16)


class PortiaIdGenerator:
    """Generate opaque family-prefixed IDs with an injectable test seam."""

    def __init__(self, token_source: TokenSource | None = None) -> None:
        self._token_source = token_source or _random_token

    def new(self, prefix: str) -> str:
        """Return one fresh ID validated by Portia's existing ID contract."""

        token = self._token_source()
        if not isinstance(token, str) or not token:
            raise ValueError("token source must return a non-empty string")
        return validate_portia_id(f"{prefix}{token}", prefix, "generated_id")
