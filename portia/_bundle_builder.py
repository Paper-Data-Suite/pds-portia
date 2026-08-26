"""Build the compact runtime JSON-Schema bundle for Issue #37.

This module is intentionally stdlib-only because setuptools imports it while
building an isolated wheel before Portia's runtime dependencies are installed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag

PORTIA_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"
MODELLED_DISPOSITIONS = {"current_v0_2", "historical_read", "supporting_v0_2"}
RUNTIME_VALUE_SCHEMA_IDS = frozenset(
    {
        PORTIA_SCHEMA_PREFIX + "schemas/v1/attribution/attribution-agent.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/provenance/creation-source.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/snapshots/person-display-snapshot.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/targets/portia-target-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/targets/support-process-target-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/judgment-evidence-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/support-processes/planned-schedule.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/roster-student-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/actor-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/local-record-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/portia-work-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/portia-work-record-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/module-work-record-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-local-record-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-portia-work-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-portia-work-record-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-actor-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-actor-contact-point-ref.schema.json",
        PORTIA_SCHEMA_PREFIX + "schemas/v1/references/exact-actor-student-relationship-ref.schema.json",
    }
)


class RuntimeBundleBuildError(RuntimeError):
    """Raised when the runtime contract bundle cannot be built exactly."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeBundleBuildError(f"could not load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeBundleBuildError(f"{path} must contain a JSON object")
    return value


def _schema_id(schema: Mapping[str, Any], path: Path) -> str:
    value = schema.get("$id")
    if not isinstance(value, str) or not value:
        raise RuntimeBundleBuildError(f"schema has no nonempty $id: {path}")
    return value


def _walk_refs(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                refs.add(child)
            else:
                refs.update(_walk_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_walk_refs(child))
    return refs


def _uri_to_repo_path(uri: str, repository_root: Path) -> Path | None:
    document_uri, _fragment = urldefrag(uri)
    if not document_uri.startswith(PORTIA_SCHEMA_PREFIX):
        return None
    relative = document_uri[len(PORTIA_SCHEMA_PREFIX) :]
    if not relative.startswith("schemas/"):
        raise RuntimeBundleBuildError(f"unsupported Portia schema URI: {uri}")
    candidate = (repository_root / relative).resolve()
    schemas_root = (repository_root / "schemas").resolve()
    try:
        candidate.relative_to(schemas_root)
    except ValueError as exc:
        raise RuntimeBundleBuildError(f"schema URI escapes schemas root: {uri}") from exc
    return candidate


def _catalog_schema_paths(catalog: Mapping[str, Any]) -> dict[str, str]:
    """Return the live catalog's schema-id-to-path mapping."""
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict):
        raise RuntimeBundleBuildError("schema catalog contracts must be an object")
    paths: dict[str, str] = {}
    for contract, versions in contracts.items():
        if not isinstance(contract, str) or not isinstance(versions, dict):
            raise RuntimeBundleBuildError("schema catalog contracts must be string-keyed objects")
        for version, entry in versions.items():
            if not isinstance(version, str) or not isinstance(entry, dict):
                raise RuntimeBundleBuildError(
                    f"catalog entry is malformed: {contract}@{version}"
                )
            schema_id = entry.get("schema_id")
            path = entry.get("path")
            if not isinstance(schema_id, str) or not isinstance(path, str):
                raise RuntimeBundleBuildError(
                    f"catalog entry is malformed: {contract}@{version}"
                )
            previous = paths.setdefault(schema_id, path)
            if previous != path:
                raise RuntimeBundleBuildError(
                    f"catalog schema id maps to multiple paths: {schema_id}"
                )
    return paths


def _catalog_entry(
    catalog: Mapping[str, Any], contract: str, version: str
) -> tuple[str, str]:
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict):
        raise RuntimeBundleBuildError("schema catalog contracts must be an object")
    versions = contracts.get(contract)
    if not isinstance(versions, dict):
        raise RuntimeBundleBuildError(f"coverage contract is absent from catalog: {contract}")
    entry = versions.get(version)
    if not isinstance(entry, dict):
        raise RuntimeBundleBuildError(
            f"coverage version is absent from catalog: {contract}@{version}"
        )
    schema_id = entry.get("schema_id")
    path = entry.get("path")
    if not isinstance(schema_id, str) or not isinstance(path, str):
        raise RuntimeBundleBuildError(
            f"catalog entry is malformed: {contract}@{version}"
        )
    return schema_id, path


def build_runtime_bundle(repository_root: Path) -> dict[str, Any]:
    """Compile the modelled v0.2 schema closure into one deterministic bundle."""
    repository_root = repository_root.resolve()
    catalog = _load_object(repository_root / "schemas" / "schema-catalog.json")
    coverage = _load_object(repository_root / "portia" / "runtime-coverage.json")
    raw_entries = coverage.get("contracts")
    if not isinstance(raw_entries, list):
        raise RuntimeBundleBuildError("runtime coverage contracts must be an array")

    contract_map: dict[str, dict[str, str]] = {}
    pending: list[Path] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise RuntimeBundleBuildError("runtime coverage entries must be objects")
        contract = raw.get("contract")
        version = raw.get("version")
        disposition = raw.get("disposition")
        modelled = raw.get("modelled")
        catalog_required = raw.get("catalog_required", True)
        if not isinstance(contract, str) or not isinstance(version, str):
            raise RuntimeBundleBuildError("coverage contract/version must be strings")
        if not isinstance(disposition, str) or not isinstance(modelled, bool):
            raise RuntimeBundleBuildError(
                f"coverage entry has invalid disposition/modelled: {contract}@{version}"
            )
        if disposition in MODELLED_DISPOSITIONS and not modelled:
            raise RuntimeBundleBuildError(
                f"modelled disposition must set modelled=true: {contract}@{version}"
            )
        if modelled:
            schema_id, relative = _catalog_entry(catalog, contract, version)
            contract_map.setdefault(contract, {})[version] = schema_id
            pending.append(repository_root / relative)
        elif catalog_required:
            _catalog_entry(catalog, contract, version)

    catalog_schema_paths = _catalog_schema_paths(catalog)
    for schema_id in sorted(RUNTIME_VALUE_SCHEMA_IDS):
        runtime_relative = catalog_schema_paths.get(schema_id)
        if runtime_relative is None:
            raise RuntimeBundleBuildError(
                f"runtime value schema is absent from the live catalog: {schema_id}"
            )
        target = (repository_root / runtime_relative).resolve()
        uri_target = _uri_to_repo_path(schema_id, repository_root)
        if uri_target is None:  # pragma: no cover - constant set is Portia-owned.
            raise RuntimeBundleBuildError(
                f"runtime value schema is outside Portia schema space: {schema_id}"
            )
        if uri_target.resolve() != target:
            raise RuntimeBundleBuildError(
                "runtime value schema URI/path disagrees with the live catalog: "
                f"{schema_id} -> {runtime_relative}"
            )
        pending.append(target)

    schemas: dict[str, Any] = {}
    seen_paths: set[Path] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        schema = _load_object(resolved)
        schema_id = _schema_id(schema, resolved)
        existing = schemas.get(schema_id)
        if existing is not None and existing != schema:
            raise RuntimeBundleBuildError(f"duplicate schema $id with different content: {schema_id}")
        schemas[schema_id] = schema
        for ref in sorted(_walk_refs(schema)):
            ref_target = _uri_to_repo_path(ref, repository_root)
            if ref_target is not None:
                pending.append(ref_target)

    return {
        "bundle_contract": "pds-portia.runtime-contract-bundle",
        "bundle_version": "1",
        "coverage_version": coverage.get("coverage_version"),
        "contracts": contract_map,
        "schemas": {key: schemas[key] for key in sorted(schemas)},
    }


def write_runtime_bundle(repository_root: Path, output_path: Path) -> None:
    """Write a deterministic compact runtime bundle."""
    bundle = build_runtime_bundle(repository_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
