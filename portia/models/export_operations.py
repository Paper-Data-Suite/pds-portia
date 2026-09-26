"""Typed deliberate-export coordinated-operation identities for Issue #88."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_portia_id
from portia.models.schema_runtime import validate_schema_id

_BASE: Final[str] = "https://paper-data-suite.github.io/pds-portia/schemas/v1/"
DELIBERATE_EXPORT_REF_SCHEMA_ID: Final[str] = (
    _BASE + "references/deliberate-export-ref.schema.json"
)
DELIBERATE_EXPORT_TARGET_SCHEMA_ID: Final[str] = (
    _BASE + "targets/deliberate-export-target.schema.json"
)


@dataclass(frozen=True, slots=True)
class DeliberateExportRef:
    """Exact identity-only reference to one deliberate-export representation."""

    export_id: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_portia_id(self.export_id, "pexp_", "export_id")
        if self.contract_version != "1":
            raise PortiaLocalValidationError(
                "deliberate export reference contract_version must be 1"
            )

    @classmethod
    def from_dict(cls, data: object) -> "DeliberateExportRef":
        validate_schema_id(DELIBERATE_EXPORT_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            export_id=cast(str, mapping["export_id"]),
            contract_version=cast(str, mapping["contract_version"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "export_id": self.export_id,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class DeliberateExportTarget:
    """Exact operational target for one deliberate-export identity."""

    export_ref: DeliberateExportRef
    kind: str = "deliberate_export"

    def __post_init__(self) -> None:
        if self.kind != "deliberate_export":
            raise PortiaLocalValidationError(
                "deliberate export target kind must be deliberate_export"
            )
        if not isinstance(self.export_ref, DeliberateExportRef):
            raise PortiaLocalValidationError(
                "deliberate export target requires DeliberateExportRef"
            )

    @classmethod
    def from_dict(cls, data: object) -> "DeliberateExportTarget":
        validate_schema_id(DELIBERATE_EXPORT_TARGET_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            export_ref=DeliberateExportRef.from_dict(mapping["export_ref"]),
            kind=cast(str, mapping["kind"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind,
            "export_ref": self.export_ref.to_dict(),
        }
