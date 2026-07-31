from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable
from referencing.jsonschema import DRAFT202012


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parents[1]
SCHEMA_ROOT = REPO_ROOT / "schemas"
SCHEMA_CATALOG_PATH = SCHEMA_ROOT / "schema-catalog.json"
FIXTURE_ROOT = TEST_DIR / "fixtures"


class SchemaCatalogError(ValueError):
    """Raised when checked-in schema metadata is internally inconsistent."""


@dataclass(frozen=True)
class SchemaStore:
    """Offline schema resources indexed by canonical `$id` values."""

    registry: Registry
    schemas_by_id: Mapping[str, Mapping[str, Any]]
    paths_by_id: Mapping[str, Path]

    def schema_for_id(
        self,
        schema_id: str,
    ) -> Mapping[str, Any]:
        try:
            return self.schemas_by_id[schema_id]
        except KeyError as exc:
            raise SchemaCatalogError(
                f"Unknown schema ID: {schema_id}"
            ) from exc

    def validator_for_id(
        self,
        schema_id: str,
    ) -> Draft202012Validator:
        return Draft202012Validator(
            self.schema_for_id(schema_id),
            registry=self.registry,
            format_checker=FormatChecker(),
        )


def load_json(path: Path) -> Any:
    """Load one JSON value from disk."""

    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaCatalogError(
            f"Could not load JSON from {path}: {exc}"
        ) from exc


def load_json_object(path: Path) -> dict[str, Any]:
    """Load one JSON object from disk."""

    value = load_json(path)
    if not isinstance(value, dict):
        raise SchemaCatalogError(
            f"Expected a JSON object in {path}"
        )
    return value


def schema_paths(
    schema_root: Path = SCHEMA_ROOT,
) -> tuple[Path, ...]:
    """Return all checked-in JSON Schema source files."""

    return tuple(sorted(schema_root.rglob("*.schema.json")))


def _canonical_schema_id(
    schema: Mapping[str, Any],
    path: Path,
) -> str:
    schema_id = schema.get("$id")
    if not isinstance(schema_id, str) or not schema_id:
        raise SchemaCatalogError(
            f"Schema {path} is missing a nonempty string $id"
        )

    parsed = urlparse(schema_id)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
    ):
        raise SchemaCatalogError(
            f"Schema {path} has a noncanonical $id: "
            f"{schema_id}"
        )
    if parsed.fragment:
        raise SchemaCatalogError(
            f"Schema {path} has a fragment in its "
            f"canonical $id: {schema_id}"
        )
    return schema_id


def build_schema_store(
    paths: Iterable[Path] | None = None,
    *,
    validate_references: bool = True,
) -> SchemaStore:
    """Build an offline registry from checked-in schema resources."""

    selected_paths = (
        tuple(paths)
        if paths is not None
        else schema_paths()
    )
    if not selected_paths:
        raise SchemaCatalogError(
            "No JSON Schema files were found"
        )

    registry = Registry()
    schemas_by_id: dict[
        str,
        Mapping[str, Any],
    ] = {}
    paths_by_id: dict[str, Path] = {}

    for path in sorted(selected_paths):
        schema = load_json_object(path)
        Draft202012Validator.check_schema(schema)
        schema_id = _canonical_schema_id(
            schema,
            path,
        )

        prior_path = paths_by_id.get(schema_id)
        if prior_path is not None:
            raise SchemaCatalogError(
                "Duplicate canonical schema ID "
                f"{schema_id!r} in {prior_path} "
                f"and {path}"
            )

        resource = Resource.from_contents(
            schema,
            default_specification=DRAFT202012,
        )
        registry = registry.with_resource(
            schema_id,
            resource,
        )
        schemas_by_id[schema_id] = schema
        paths_by_id[schema_id] = path.resolve()

    store = SchemaStore(
        registry=registry,
        schemas_by_id=schemas_by_id,
        paths_by_id=paths_by_id,
    )
    if validate_references:
        assert_all_references_resolve(store)
    return store


def _iter_references(
    value: Any,
) -> Iterable[str]:
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            yield ref
        for child in value.values():
            yield from _iter_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_references(child)


def assert_all_references_resolve(
    store: SchemaStore,
) -> None:
    """Resolve every `$ref` exclusively from the local registry."""

    for schema_id, schema in (
        store.schemas_by_id.items()
    ):
        resolver = store.registry.resolver(
            base_uri=schema_id
        )
        for ref in _iter_references(schema):
            try:
                resolver.lookup(ref)
            except Unresolvable as exc:
                path = store.paths_by_id[schema_id]
                raise SchemaCatalogError(
                    f"Unresolved $ref {ref!r} "
                    f"in {path}"
                ) from exc


def load_schema_catalog(
    path: Path = SCHEMA_CATALOG_PATH,
) -> dict[str, Any]:
    catalog = load_json_object(path)

    if set(catalog) != {
        "catalog_version",
        "contracts",
    }:
        raise SchemaCatalogError(
            "Schema catalog must contain exactly "
            "'catalog_version' and 'contracts'"
        )
    if catalog["catalog_version"] != "1":
        raise SchemaCatalogError(
            "Unsupported schema catalog version: "
            f"{catalog['catalog_version']!r}"
        )
    if not isinstance(
        catalog["contracts"],
        dict,
    ):
        raise SchemaCatalogError(
            "Schema catalog 'contracts' "
            "must be an object"
        )
    return catalog


def _catalog_entry_fields(
    contract_name: str,
    version: str,
    entry: Any,
) -> tuple[str, str]:
    if not isinstance(entry, dict):
        raise SchemaCatalogError(
            f"Catalog entry "
            f"{contract_name}@{version} "
            "must be an object"
        )
    if set(entry) != {"schema_id", "path"}:
        raise SchemaCatalogError(
            f"Catalog entry "
            f"{contract_name}@{version} "
            "must contain exactly "
            "'schema_id' and 'path'"
        )

    schema_id = entry["schema_id"]
    relative_path = entry["path"]
    if (
        not isinstance(schema_id, str)
        or not schema_id
    ):
        raise SchemaCatalogError(
            f"Catalog entry "
            f"{contract_name}@{version} "
            "has an invalid schema_id"
        )
    if (
        not isinstance(relative_path, str)
        or not relative_path
    ):
        raise SchemaCatalogError(
            f"Catalog entry "
            f"{contract_name}@{version} "
            "has an invalid path"
        )
    return schema_id, relative_path


def validate_schema_catalog(
    catalog: Mapping[str, Any],
    store: SchemaStore,
    *,
    repo_root: Path = REPO_ROOT,
) -> None:
    contracts = catalog["contracts"]
    seen_schema_ids: dict[str, str] = {}

    for contract_name, versions in (
        contracts.items()
    ):
        if (
            not isinstance(contract_name, str)
            or not contract_name
        ):
            raise SchemaCatalogError(
                "Catalog contract names must be "
                "nonempty strings"
            )
        if (
            not isinstance(versions, dict)
            or not versions
        ):
            raise SchemaCatalogError(
                f"Catalog contract "
                f"{contract_name!r} must contain "
                "at least one version"
            )

        for version, entry in versions.items():
            if (
                not isinstance(version, str)
                or not version
            ):
                raise SchemaCatalogError(
                    f"Catalog versions for "
                    f"{contract_name!r} must be "
                    "nonempty strings"
                )

            schema_id, relative_path = (
                _catalog_entry_fields(
                    contract_name,
                    version,
                    entry,
                )
            )
            catalog_key = (
                f"{contract_name}@{version}"
            )

            prior_key = seen_schema_ids.get(
                schema_id
            )
            if prior_key is not None:
                raise SchemaCatalogError(
                    f"Schema ID {schema_id!r} "
                    "is cataloged as both "
                    f"{prior_key} and {catalog_key}"
                )
            seen_schema_ids[schema_id] = (
                catalog_key
            )

            path = Path(relative_path)
            if (
                path.is_absolute()
                or ".." in path.parts
            ):
                raise SchemaCatalogError(
                    f"Catalog path for {catalog_key} "
                    "must be repository-relative "
                    "and nonescaping"
                )

            resolved_path = (
                repo_root / path
            ).resolve()
            try:
                resolved_path.relative_to(
                    repo_root.resolve()
                )
            except ValueError as exc:
                raise SchemaCatalogError(
                    f"Catalog path for {catalog_key} "
                    "escapes the repository root"
                ) from exc

            actual_path = (
                store.paths_by_id.get(schema_id)
            )
            if actual_path is None:
                raise SchemaCatalogError(
                    f"Catalog entry {catalog_key} "
                    "references unknown schema ID "
                    f"{schema_id!r}"
                )
            if actual_path != resolved_path:
                raise SchemaCatalogError(
                    f"Catalog path mismatch for "
                    f"{catalog_key}: expected "
                    f"{actual_path}, found "
                    f"{resolved_path}"
                )


def load_validated_catalog_and_store(
    catalog_path: Path = SCHEMA_CATALOG_PATH,
) -> tuple[dict[str, Any], SchemaStore]:
    store = build_schema_store()
    catalog = load_schema_catalog(
        catalog_path
    )
    validate_schema_catalog(
        catalog,
        store,
    )
    return catalog, store


def schema_id_for(
    contract_name: str,
    version: str,
    catalog: Mapping[str, Any],
) -> str:
    try:
        entry = catalog["contracts"][
            contract_name
        ][version]
    except KeyError as exc:
        raise SchemaCatalogError(
            "Unknown schema contract/version: "
            f"{contract_name}@{version}"
        ) from exc

    schema_id, _ = _catalog_entry_fields(
        contract_name,
        version,
        entry,
    )
    return schema_id


def validator_for(
    contract_name: str,
    version: str,
    *,
    catalog: Mapping[str, Any] | None = None,
    store: SchemaStore | None = None,
) -> Draft202012Validator:
    if catalog is None or store is None:
        loaded_catalog, loaded_store = (
            load_validated_catalog_and_store()
        )
        catalog = loaded_catalog
        store = loaded_store

    return store.validator_for_id(
        schema_id_for(
            contract_name,
            version,
            catalog,
        )
    )
