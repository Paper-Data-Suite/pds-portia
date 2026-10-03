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

REPLACEMENT_TEMPORARY_DOMAIN: Final[str] = "replacement_temporary"
REPLACEMENT_TEMPORARY_LEAF_PREFIX: Final[str] = ".portia-tmp-"
REPLACEMENT_TEMPORARY_LEAF_SUFFIX: Final[str] = ".tmp"
REPLACEMENT_TEMPORARY_NONCE_HEX_LENGTH: Final[int] = 32
REPLACEMENT_TEMPORARY_LEAF_LENGTH: Final[int] = (
    len(REPLACEMENT_TEMPORARY_LEAF_PREFIX)
    + GENERATED_PATH_TOKEN_LENGTH
    + len(REPLACEMENT_TEMPORARY_LEAF_SUFFIX)
)

STAGING_OPERATION_DOMAIN: Final[str] = "staging_operation"
STAGING_CANDIDATE_DOMAIN: Final[str] = "staging_candidate"
STAGING_CANDIDATE_LEAF_SUFFIX: Final[str] = ".candidate"
STAGING_CANDIDATE_LEAF_LENGTH: Final[int] = (
    GENERATED_PATH_TOKEN_LENGTH + len(STAGING_CANDIDATE_LEAF_SUFFIX)
)

WORK_STORAGE_REVISION_DOMAIN: Final[str] = "work_storage_revision"
ACTOR_STORAGE_REVISION_DOMAIN: Final[str] = "actor_storage_revision"
STORAGE_REVISION_LEAF_SUFFIX: Final[str] = ".json"
STORAGE_REVISION_LEAF_LENGTH: Final[int] = (
    GENERATED_PATH_TOKEN_LENGTH + len(STORAGE_REVISION_LEAF_SUFFIX)
)

DERIVED_PROJECTION_DOMAIN: Final[str] = "derived_projection"
DERIVED_GENERATION_DOMAIN: Final[str] = "derived_generation"

_DOMAIN_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9_-]*$")
_TOKEN_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^{re.escape(GENERATED_PATH_TOKEN_PREFIX)}"
    rf"[0-9a-f]{{{GENERATED_PATH_TOKEN_HEX_LENGTH}}}$"
)
_REPLACEMENT_TEMPORARY_NONCE_PATTERN: Final[re.Pattern[str]] = re.compile(
    rf"^[0-9a-f]{{{REPLACEMENT_TEMPORARY_NONCE_HEX_LENGTH}}}$"
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


def build_replacement_temporary_leaf(nonce: object) -> str:
    """Return one exact bounded leaf for target-adjacent replacement staging.

    ``nonce`` is infrastructure entropy only. The destination filename is
    intentionally not embedded in the temporary leaf.
    """
    if (
        not isinstance(nonce, str)
        or _REPLACEMENT_TEMPORARY_NONCE_PATTERN.fullmatch(nonce) is None
    ):
        raise PortiaPathError(
            "replacement temporary nonce must be 32 lowercase hexadecimal characters"
        )
    token = build_generated_path_token(REPLACEMENT_TEMPORARY_DOMAIN, nonce)
    leaf = (
        f"{REPLACEMENT_TEMPORARY_LEAF_PREFIX}"
        f"{token}"
        f"{REPLACEMENT_TEMPORARY_LEAF_SUFFIX}"
    )
    if len(leaf) != REPLACEMENT_TEMPORARY_LEAF_LENGTH:
        raise PortiaPathError("replacement temporary leaf exceeded its fixed budget")
    return leaf


def build_staging_operation_token(operation_id: object) -> str:
    """Return the bounded directory token for one staging operation."""
    return build_generated_path_token(STAGING_OPERATION_DOMAIN, operation_id)


def build_staging_candidate_leaf(
    operation_id: object,
    step_id: object,
    destination_relative_path: object,
) -> str:
    """Return one bounded staging leaf bound to operation, step, and destination."""
    token = build_generated_path_token(
        STAGING_CANDIDATE_DOMAIN,
        operation_id,
        step_id,
        destination_relative_path,
    )
    leaf = f"{token}{STAGING_CANDIDATE_LEAF_SUFFIX}"
    if len(leaf) != STAGING_CANDIDATE_LEAF_LENGTH:
        raise PortiaPathError("staging candidate leaf exceeded its fixed budget")
    return leaf


def _build_storage_revision_leaf(
    domain: str,
    record_kind: object,
    record_id: object,
    digest: object,
) -> str:
    token = build_generated_path_token(domain, record_kind, record_id, digest)
    leaf = f"{token}{STORAGE_REVISION_LEAF_SUFFIX}"
    if len(leaf) != STORAGE_REVISION_LEAF_LENGTH:
        raise PortiaPathError("storage-revision leaf exceeded its fixed budget")
    return leaf


def build_work_storage_revision_leaf(
    record_kind: object,
    record_id: object,
    digest: object,
) -> str:
    """Return one bounded work technical-storage revision leaf."""
    return _build_storage_revision_leaf(
        WORK_STORAGE_REVISION_DOMAIN,
        record_kind,
        record_id,
        digest,
    )


def build_actor_storage_revision_leaf(
    record_kind: object,
    record_id: object,
    digest: object,
) -> str:
    """Return one bounded Actor technical-storage revision leaf."""
    return _build_storage_revision_leaf(
        ACTOR_STORAGE_REVISION_DOMAIN,
        record_kind,
        record_id,
        digest,
    )


def build_derived_projection_token(
    projection_kind: object,
    scope_kind: object,
    *scope_identity: object,
) -> str:
    """Return one bounded token for an exact derived projection scope."""
    return build_generated_path_token(
        DERIVED_PROJECTION_DOMAIN,
        projection_kind,
        scope_kind,
        *scope_identity,
    )


def build_derived_generation_token(
    projection_token: object,
    generation_id: object,
) -> str:
    """Return one bounded token for a generation inside one projection scope."""
    return build_generated_path_token(
        DERIVED_GENERATION_DOMAIN,
        projection_token,
        generation_id,
    )
