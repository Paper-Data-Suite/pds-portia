"""Bounded generated-path primitives for Portia-owned filesystem infrastructure."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Final

from portia.storage.errors import PortiaPathError

GENERATED_PATH_POLICY_VERSION: Final[str] = "portia_generated_path_v1"
GENERATED_PATH_TOKEN_PREFIX: Final[str] = "pt_"
GENERATED_PATH_TOKEN_HEX_LENGTH: Final[int] = 32
GENERATED_PATH_TOKEN_LENGTH: Final[int] = (
    len(GENERATED_PATH_TOKEN_PREFIX) + GENERATED_PATH_TOKEN_HEX_LENGTH
)
GENERATED_PATH_DOMAIN_MAX_LENGTH: Final[int] = 48

_DOMAIN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_-]*$")
_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{re.escape(GENERATED_PATH_TOKEN_PREFIX)}"
    rf"[0-9a-f]{{{GENERATED_PATH_TOKEN_HEX_LENGTH}}}$"
)


def _validate_domain(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= GENERATED_PATH_DOMAIN_MAX_LENGTH
        or _DOMAIN_PATTERN.fullmatch(value) is None
    ):
        raise PortiaPathError(
            "generated-path domain must be a bounded lowercase infrastructure label"
        )
    return value


def _validate_identity_parts(values: tuple[object, ...]) -> tuple[str, ...]:
    if not values:
        raise PortiaPathError("generated-path token requires canonical identity input")
    parts: list[str] = []
    for value in values:
        if not isinstance(value, str) or value == "":
            raise PortiaPathError(
                "generated-path identity inputs must be nonempty strings"
            )
        parts.append(value)
    return tuple(parts)


def build_generated_path_token(domain: object, *identity_parts: object) -> str:
    """Return one fixed-length opaque token for Portia-owned filesystem use.

    ``domain`` provides versioned namespace separation. ``identity_parts`` must be
    canonical identity/provenance inputs, not display labels. Full identity remains
    in authoritative records; this token is filesystem serialization only.
    """
    safe_domain = _validate_domain(domain)
    safe_parts = _validate_identity_parts(identity_parts)
    descriptor = {
        "domain": safe_domain,
        "identity_parts": safe_parts,
        "policy": GENERATED_PATH_POLICY_VERSION,
    }
    encoded = json.dumps(
        descriptor,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:GENERATED_PATH_TOKEN_HEX_LENGTH]
    return f"{GENERATED_PATH_TOKEN_PREFIX}{digest}"


def validate_generated_path_token(value: object) -> str:
    """Validate an exact token emitted by :func:`build_generated_path_token`."""
    if not isinstance(value, str) or _TOKEN_PATTERN.fullmatch(value) is None:
        raise PortiaPathError("invalid Portia generated-path token")
    return value
