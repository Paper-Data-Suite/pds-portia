"""Explicit Issue #37 runtime contract/version coverage matrix."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

CoverageDisposition: TypeAlias = Literal[
    "current_v0_2",
    "historical_read",
    "supporting_v0_2",
    "deferred_v0_3",
    "noncanonical_not_modeled",
    "core_owned",
]

MODELLED_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"current_v0_2", "historical_read", "supporting_v0_2"}
)


@dataclass(frozen=True, slots=True)
class RuntimeCoverageEntry:
    contract: str
    version: str
    disposition: CoverageDisposition
    modelled: bool
    catalog_required: bool = True



def _load_coverage_object() -> dict[str, object]:
    text = resources.files("portia").joinpath("runtime-coverage.json").read_text(
        encoding="utf-8"
    )
    value = json.loads(text)
    if not isinstance(value, dict):
        raise RuntimeError("Portia runtime coverage must be a JSON object")
    return cast(dict[str, object], value)


def runtime_coverage() -> tuple[RuntimeCoverageEntry, ...]:
    """Return the immutable explicit contract/version coverage matrix."""
    raw = _load_coverage_object().get("contracts")
    if not isinstance(raw, list):
        raise RuntimeError("Portia runtime coverage contracts must be an array")
    entries: list[RuntimeCoverageEntry] = []
    seen: set[tuple[str, str]] = set()
    allowed = {
        "current_v0_2",
        "historical_read",
        "supporting_v0_2",
        "deferred_v0_3",
        "noncanonical_not_modeled",
        "core_owned",
    }
    for item in raw:
        if not isinstance(item, dict):
            raise RuntimeError("Portia runtime coverage entries must be objects")
        contract = item.get("contract")
        version = item.get("version")
        disposition = item.get("disposition")
        modelled = item.get("modelled")
        catalog_required = item.get("catalog_required", True)
        if not isinstance(contract, str) or not isinstance(version, str):
            raise RuntimeError("coverage contract/version must be strings")
        if not isinstance(disposition, str) or disposition not in allowed:
            raise RuntimeError(f"invalid coverage disposition: {disposition!r}")
        if not isinstance(modelled, bool) or not isinstance(catalog_required, bool):
            raise RuntimeError("coverage modelled/catalog_required must be booleans")
        key = (contract, version)
        if key in seen:
            raise RuntimeError(f"duplicate runtime coverage entry: {contract}@{version}")
        seen.add(key)
        if disposition in MODELLED_DISPOSITIONS and not modelled:
            raise RuntimeError(
                f"modelled disposition must set modelled=true: {contract}@{version}"
            )
        entries.append(
            RuntimeCoverageEntry(
                contract=contract,
                version=version,
                disposition=cast(CoverageDisposition, disposition),
                modelled=modelled,
                catalog_required=catalog_required,
            )
        )
    return tuple(entries)


def modelled_contract_versions() -> frozenset[tuple[str, str]]:
    return frozenset(
        (entry.contract, entry.version) for entry in runtime_coverage() if entry.modelled
    )


def audit_coverage_against_catalog(catalog_path: Path) -> tuple[str, ...]:
    """Return deterministic drift findings against the live source schema catalog."""
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("contracts"), dict):
        return ("schema catalog is malformed",)
    contracts = cast(dict[str, object], raw["contracts"])
    findings: list[str] = []
    for entry in runtime_coverage():
        if not entry.catalog_required:
            continue
        versions = contracts.get(entry.contract)
        if not isinstance(versions, dict):
            findings.append(f"missing catalog contract: {entry.contract}")
            continue
        if entry.version not in versions:
            findings.append(f"missing catalog version: {entry.contract}@{entry.version}")
    return tuple(sorted(findings))
