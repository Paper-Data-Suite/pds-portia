"""Exact byte fingerprints and deterministic JSON serialization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ContentFingerprint:
    """Exact SHA-256 and byte length for one representation."""

    digest: str
    byte_length: int
    algorithm: str = "sha256"

    def __post_init__(self) -> None:
        if self.algorithm != "sha256":
            raise ValueError('algorithm must be "sha256"')
        if len(self.digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.digest):
            raise ValueError("digest must be 64 lowercase hexadecimal characters")
        if self.byte_length < 0:
            raise ValueError("byte_length must be nonnegative")

    def to_dict(self) -> dict[str, object]:
        return {
            "algorithm": self.algorithm,
            "digest": self.digest,
            "byte_length": self.byte_length,
        }

    @classmethod
    def from_dict(cls, value: object) -> "ContentFingerprint":
        if not isinstance(value, dict):
            raise ValueError("fingerprint must be an object")
        algorithm = value.get("algorithm")
        digest = value.get("digest")
        byte_length = value.get("byte_length")
        if algorithm != "sha256" or not isinstance(digest, str) or not isinstance(byte_length, int):
            raise ValueError("invalid content fingerprint")
        return cls(digest=digest, byte_length=byte_length, algorithm=algorithm)


def fingerprint_bytes(content: bytes) -> ContentFingerprint:
    return ContentFingerprint(hashlib.sha256(content).hexdigest(), len(content))


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes with a final LF."""
    text = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (text + "\n").encode("utf-8")
