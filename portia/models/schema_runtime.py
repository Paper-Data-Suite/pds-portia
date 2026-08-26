"""Runtime structural validation against the compiled Portia contract bundle.

The production wheel uses only the standard library.  In a source checkout, the
same bundle is compiled in memory from the accepted repository schemas when the
built package resource is absent.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from importlib import resources
from pathlib import Path
from typing import Any, cast
from urllib.parse import urldefrag, urlsplit

from portia.models.errors import PortiaWireError, UnsupportedContractError
from portia.models.json_values import json_equality_key


@dataclass(frozen=True, slots=True)
class RuntimeContractBundle:
    """Resolved runtime schema bundle and contract/version lookup."""

    contracts: Mapping[str, Mapping[str, str]]
    schemas: Mapping[str, Mapping[str, Any]]


_BUNDLE: RuntimeContractBundle | None = None


def _load_json_object(text: str, description: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{description} must contain a JSON object")
    return value


def _source_repository_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "schemas" / "schema-catalog.json").is_file() and (
            parent / "portia" / "runtime-coverage.json"
        ).is_file():
            return parent
    return None


def _bundle_from_object(raw: Mapping[str, Any]) -> RuntimeContractBundle:
    contracts_raw = raw.get("contracts")
    schemas_raw = raw.get("schemas")
    if not isinstance(contracts_raw, dict) or not isinstance(schemas_raw, dict):
        raise RuntimeError("runtime contract bundle is malformed")

    contracts: dict[str, dict[str, str]] = {}
    for contract, versions_raw in contracts_raw.items():
        if not isinstance(contract, str) or not isinstance(versions_raw, dict):
            raise RuntimeError("runtime bundle contract map is malformed")
        versions: dict[str, str] = {}
        for version, schema_id in versions_raw.items():
            if not isinstance(version, str) or not isinstance(schema_id, str):
                raise RuntimeError("runtime bundle version map is malformed")
            versions[version] = schema_id
        contracts[contract] = versions

    schemas: dict[str, Mapping[str, Any]] = {}
    for schema_id, schema_raw in schemas_raw.items():
        if not isinstance(schema_id, str) or not isinstance(schema_raw, dict):
            raise RuntimeError("runtime bundle schema map is malformed")
        schemas[schema_id] = cast(Mapping[str, Any], schema_raw)
    return RuntimeContractBundle(contracts=contracts, schemas=schemas)


def load_runtime_contract_bundle() -> RuntimeContractBundle:
    """Load the installed bundle or compile it from a source checkout."""
    global _BUNDLE
    if _BUNDLE is not None:
        return _BUNDLE

    package_root = resources.files("portia")
    resource = package_root.joinpath("_runtime_contract_bundle.json")
    try:
        if resource.is_file():
            raw = _load_json_object(
                resource.read_text(encoding="utf-8"), "runtime contract bundle"
            )
            _BUNDLE = _bundle_from_object(raw)
            return _BUNDLE
    except (FileNotFoundError, OSError):
        pass

    repository_root = _source_repository_root()
    if repository_root is None:
        raise RuntimeError(
            "Portia runtime contract bundle is unavailable and no source schemas were found."
        )

    # The builder is stdlib-only and safe to use from an editable source checkout.
    from portia._bundle_builder import build_runtime_bundle

    _BUNDLE = _bundle_from_object(build_runtime_bundle(repository_root))
    return _BUNDLE


def schema_id_for(contract: str, version: str) -> str:
    """Return the exact schema identity for a modelled contract/version."""
    bundle = load_runtime_contract_bundle()
    versions = bundle.contracts.get(contract)
    if versions is None or version not in versions:
        raise UnsupportedContractError(
            f"unsupported Portia runtime contract: {contract}@{version}"
        )
    return versions[version]


def validate_wire_contract(contract: str, version: str, data: object) -> None:
    """Validate JSON-native input against the exact public contract."""
    bundle = load_runtime_contract_bundle()
    schema_id = schema_id_for(contract, version)
    schema = bundle.schemas.get(schema_id)
    if schema is None:
        raise RuntimeError(f"runtime bundle is missing schema: {schema_id}")
    _validate(schema, data, bundle=bundle, document_id=schema_id, path="$", depth=0)


def _resolve_pointer(document: object, fragment: str) -> object:
    if fragment in {"", "#"}:
        return document
    pointer = fragment[1:] if fragment.startswith("#") else fragment
    if not pointer:
        return document
    if not pointer.startswith("/"):
        raise RuntimeError(f"unsupported JSON pointer fragment: {fragment}")
    current = document
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                raise RuntimeError(f"unresolvable JSON pointer: {fragment}")
            current = current[token]
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as exc:
                raise RuntimeError(f"unresolvable JSON pointer: {fragment}") from exc
        else:
            raise RuntimeError(f"unresolvable JSON pointer: {fragment}")
    return current


def _resolve_ref(
    ref: str,
    *,
    bundle: RuntimeContractBundle,
    document_id: str,
) -> tuple[Mapping[str, Any] | bool, str]:
    target_uri, fragment = urldefrag(ref)
    target_id = target_uri or document_id
    document = bundle.schemas.get(target_id)
    if document is None:
        raise RuntimeError(f"runtime bundle cannot resolve schema reference: {ref}")
    resolved = _resolve_pointer(document, f"#{fragment}" if fragment else "")
    if isinstance(resolved, bool):
        return resolved, target_id
    if not isinstance(resolved, Mapping):
        raise RuntimeError(f"schema reference did not resolve to a schema: {ref}")
    return cast(Mapping[str, Any], resolved), target_id


def _schema_matches(
    schema: object,
    value: object,
    *,
    bundle: RuntimeContractBundle,
    document_id: str,
    path: str,
    depth: int,
) -> bool:
    try:
        _validate(
            schema,
            value,
            bundle=bundle,
            document_id=document_id,
            path=path,
            depth=depth,
        )
    except PortiaWireError:
        return False
    return True


def _json_type_matches(expected: str, value: object) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, Mapping)
    return False


def _validate_type(expected: object, value: object, path: str) -> None:
    if isinstance(expected, str):
        if not _json_type_matches(expected, value):
            raise PortiaWireError(f"{path}: expected JSON type {expected}.")
        return
    if isinstance(expected, list) and all(isinstance(item, str) for item in expected):
        types = cast(list[str], expected)
        if not any(_json_type_matches(item, value) for item in types):
            raise PortiaWireError(
                f"{path}: expected one of JSON types {', '.join(types)}."
            )
        return
    raise RuntimeError("runtime schema has malformed type keyword")


def _validate_format(format_name: str, value: str, path: str) -> None:
    if format_name == "date":
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise PortiaWireError(f"{path}: expected an RFC 3339 full-date.") from exc
    elif format_name == "date-time":
        if re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})",
            value,
        ) is None:
            raise PortiaWireError(f"{path}: expected an RFC 3339 date-time.")
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise PortiaWireError(f"{path}: expected an RFC 3339 date-time.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise PortiaWireError(f"{path}: date-time must include an explicit offset.")
    elif format_name == "email":
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise PortiaWireError(f"{path}: expected an email-shaped string.")
    elif format_name in {"uri", "uri-reference"}:
        if not value or any(character.isspace() for character in value):
            raise PortiaWireError(f"{path}: expected a URI-shaped string.")
        try:
            parsed_uri = urlsplit(value)
        except ValueError as exc:
            raise PortiaWireError(f"{path}: expected a URI-shaped string.") from exc
        if format_name == "uri" and not parsed_uri.scheme:
            raise PortiaWireError(f"{path}: expected an absolute URI.")
    # Unknown annotation formats remain annotations, matching JSON Schema semantics.


def _number(value: object, path: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PortiaWireError(f"{path}: expected a number.")
    result = float(value)
    if not math.isfinite(result):
        raise PortiaWireError(f"{path}: JSON numbers must be finite.")
    return result


def _validate(
    schema: object,
    value: object,
    *,
    bundle: RuntimeContractBundle,
    document_id: str,
    path: str,
    depth: int,
) -> None:
    if depth > 256:
        raise RuntimeError("runtime schema validation exceeded recursion limit")
    if schema is True:
        return
    if schema is False:
        raise PortiaWireError(f"{path}: value is prohibited by the public contract.")
    if not isinstance(schema, Mapping):
        raise RuntimeError("runtime schema node must be an object or boolean")
    node = cast(Mapping[str, Any], schema)

    ref = node.get("$ref")
    if ref is not None:
        if not isinstance(ref, str):
            raise RuntimeError("runtime schema has malformed $ref")
        target, target_id = _resolve_ref(ref, bundle=bundle, document_id=document_id)
        _validate(
            target,
            value,
            bundle=bundle,
            document_id=target_id,
            path=path,
            depth=depth + 1,
        )

    if "type" in node:
        _validate_type(node["type"], value, path)

    if "const" in node and json_equality_key(value) != json_equality_key(node["const"]):
        raise PortiaWireError(f"{path}: value does not match the contract constant.")

    enum = node.get("enum")
    if enum is not None:
        if not isinstance(enum, list):
            raise RuntimeError("runtime schema has malformed enum")
        value_key = json_equality_key(value)
        if not any(value_key == json_equality_key(candidate) for candidate in enum):
            raise PortiaWireError(f"{path}: value is not in the allowed vocabulary.")

    all_of = node.get("allOf")
    if all_of is not None:
        if not isinstance(all_of, list):
            raise RuntimeError("runtime schema has malformed allOf")
        for child in all_of:
            _validate(
                child,
                value,
                bundle=bundle,
                document_id=document_id,
                path=path,
                depth=depth + 1,
            )

    any_of = node.get("anyOf")
    if any_of is not None:
        if not isinstance(any_of, list):
            raise RuntimeError("runtime schema has malformed anyOf")
        if not any(
            _schema_matches(
                child,
                value,
                bundle=bundle,
                document_id=document_id,
                path=path,
                depth=depth + 1,
            )
            for child in any_of
        ):
            raise PortiaWireError(f"{path}: value matches no allowed contract branch.")

    one_of = node.get("oneOf")
    if one_of is not None:
        if not isinstance(one_of, list):
            raise RuntimeError("runtime schema has malformed oneOf")
        matches = sum(
            _schema_matches(
                child,
                value,
                bundle=bundle,
                document_id=document_id,
                path=path,
                depth=depth + 1,
            )
            for child in one_of
        )
        if matches != 1:
            raise PortiaWireError(
                f"{path}: value must match exactly one allowed contract branch."
            )

    if "not" in node and _schema_matches(
        node["not"],
        value,
        bundle=bundle,
        document_id=document_id,
        path=path,
        depth=depth + 1,
    ):
        raise PortiaWireError(f"{path}: value matches a prohibited contract branch.")

    if_schema = node.get("if")
    if if_schema is not None:
        condition = _schema_matches(
            if_schema,
            value,
            bundle=bundle,
            document_id=document_id,
            path=path,
            depth=depth + 1,
        )
        branch = node.get("then") if condition else node.get("else")
        if branch is not None:
            _validate(
                branch,
                value,
                bundle=bundle,
                document_id=document_id,
                path=path,
                depth=depth + 1,
            )

    if isinstance(value, str):
        min_length = node.get("minLength")
        max_length = node.get("maxLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise PortiaWireError(f"{path}: string is shorter than allowed.")
        if isinstance(max_length, int) and len(value) > max_length:
            raise PortiaWireError(f"{path}: string is longer than allowed.")
        pattern = node.get("pattern")
        if pattern is not None:
            if not isinstance(pattern, str):
                raise RuntimeError("runtime schema has malformed pattern")
            if re.search(pattern, value) is None:
                raise PortiaWireError(f"{path}: string does not match the required pattern.")
        format_name = node.get("format")
        if isinstance(format_name, str):
            _validate_format(format_name, value, path)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = _number(value, path)
        for keyword, description in (
            ("minimum", "minimum"),
            ("maximum", "maximum"),
            ("exclusiveMinimum", "exclusive minimum"),
            ("exclusiveMaximum", "exclusive maximum"),
        ):
            bound = node.get(keyword)
            if isinstance(bound, (int, float)) and not isinstance(bound, bool):
                numeric_bound = float(bound)
                valid = (
                    (keyword == "minimum" and numeric >= numeric_bound)
                    or (keyword == "maximum" and numeric <= numeric_bound)
                    or (keyword == "exclusiveMinimum" and numeric > numeric_bound)
                    or (keyword == "exclusiveMaximum" and numeric < numeric_bound)
                )
                if not valid:
                    raise PortiaWireError(f"{path}: number violates the {description}.")
        multiple = node.get("multipleOf")
        if isinstance(multiple, (int, float)) and not isinstance(multiple, bool):
            divisor = float(multiple)
            if divisor <= 0:
                raise RuntimeError("runtime schema has invalid multipleOf")
            quotient = numeric / divisor
            if not math.isclose(quotient, round(quotient), rel_tol=1e-12, abs_tol=1e-12):
                raise PortiaWireError(f"{path}: number violates multipleOf.")

    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise PortiaWireError(f"{path}: object keys must be strings.")
        mapping = cast(Mapping[str, object], value)
        required = node.get("required", [])
        if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
            raise RuntimeError("runtime schema has malformed required")
        missing = [cast(str, key) for key in required if key not in mapping]
        if missing:
            raise PortiaWireError(
                f"{path}: missing required field(s): {', '.join(sorted(missing))}."
            )
        min_properties = node.get("minProperties")
        max_properties = node.get("maxProperties")
        if isinstance(min_properties, int) and len(mapping) < min_properties:
            raise PortiaWireError(f"{path}: object has too few properties.")
        if isinstance(max_properties, int) and len(mapping) > max_properties:
            raise PortiaWireError(f"{path}: object has too many properties.")

        properties_raw = node.get("properties", {})
        if not isinstance(properties_raw, Mapping):
            raise RuntimeError("runtime schema has malformed properties")
        properties = cast(Mapping[str, object], properties_raw)
        pattern_properties_raw = node.get("patternProperties", {})
        if not isinstance(pattern_properties_raw, Mapping):
            raise RuntimeError("runtime schema has malformed patternProperties")
        pattern_properties = cast(Mapping[str, object], pattern_properties_raw)

        evaluated: set[str] = set()
        for key, child_value in mapping.items():
            if key in properties:
                evaluated.add(key)
                _validate(
                    properties[key],
                    child_value,
                    bundle=bundle,
                    document_id=document_id,
                    path=f"{path}.{key}",
                    depth=depth + 1,
                )
            for pattern_text, child_schema in pattern_properties.items():
                if re.search(pattern_text, key) is not None:
                    evaluated.add(key)
                    _validate(
                        child_schema,
                        child_value,
                        bundle=bundle,
                        document_id=document_id,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                    )

        additional = node.get("additionalProperties", True)
        extras = [key for key in mapping if key not in evaluated]
        if additional is False and extras:
            raise PortiaWireError(
                f"{path}: unknown field(s): {', '.join(sorted(extras))}."
            )
        if isinstance(additional, Mapping) or isinstance(additional, bool) and additional is False:
            if additional is not False:
                for key in extras:
                    _validate(
                        additional,
                        mapping[key],
                        bundle=bundle,
                        document_id=document_id,
                        path=f"{path}.{key}",
                        depth=depth + 1,
                    )

        dependent_required = node.get("dependentRequired")
        if dependent_required is not None:
            if not isinstance(dependent_required, Mapping):
                raise RuntimeError("runtime schema has malformed dependentRequired")
            for trigger, dependencies in dependent_required.items():
                if trigger not in mapping:
                    continue
                if not isinstance(dependencies, list) or any(
                    not isinstance(item, str) for item in dependencies
                ):
                    raise RuntimeError("runtime schema has malformed dependentRequired entry")
                absent = [cast(str, item) for item in dependencies if item not in mapping]
                if absent:
                    raise PortiaWireError(
                        f"{path}: field {trigger} requires {', '.join(sorted(absent))}."
                    )

        dependent_schemas = node.get("dependentSchemas")
        if dependent_schemas is not None:
            if not isinstance(dependent_schemas, Mapping):
                raise RuntimeError("runtime schema has malformed dependentSchemas")
            for trigger, child_schema in dependent_schemas.items():
                if trigger in mapping:
                    _validate(
                        child_schema,
                        value,
                        bundle=bundle,
                        document_id=document_id,
                        path=path,
                        depth=depth + 1,
                    )

        property_names = node.get("propertyNames")
        if property_names is not None:
            for key in mapping:
                _validate(
                    property_names,
                    key,
                    bundle=bundle,
                    document_id=document_id,
                    path=f"{path}.<property-name>",
                    depth=depth + 1,
                )

    if isinstance(value, list):
        min_items = node.get("minItems")
        max_items = node.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            raise PortiaWireError(f"{path}: array has too few items.")
        if isinstance(max_items, int) and len(value) > max_items:
            raise PortiaWireError(f"{path}: array has too many items.")
        if node.get("uniqueItems") is True:
            keys = [json_equality_key(item) for item in value]
            if len(set(keys)) != len(keys):
                raise PortiaWireError(f"{path}: array contains duplicate items.")

        prefix_items = node.get("prefixItems")
        prefix_count = 0
        if prefix_items is not None:
            if not isinstance(prefix_items, list):
                raise RuntimeError("runtime schema has malformed prefixItems")
            prefix_count = min(len(value), len(prefix_items))
            for index in range(prefix_count):
                _validate(
                    prefix_items[index],
                    value[index],
                    bundle=bundle,
                    document_id=document_id,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                )

        items = node.get("items")
        if items is not None:
            start = prefix_count if prefix_items is not None else 0
            for index in range(start, len(value)):
                _validate(
                    items,
                    value[index],
                    bundle=bundle,
                    document_id=document_id,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                )

        contains = node.get("contains")
        if contains is not None:
            matches = sum(
                _schema_matches(
                    contains,
                    item,
                    bundle=bundle,
                    document_id=document_id,
                    path=f"{path}[{index}]",
                    depth=depth + 1,
                )
                for index, item in enumerate(value)
            )
            minimum = node.get("minContains", 1)
            maximum = node.get("maxContains")
            if not isinstance(minimum, int):
                raise RuntimeError("runtime schema has malformed minContains")
            if matches < minimum:
                raise PortiaWireError(f"{path}: array does not satisfy contains.")
            if isinstance(maximum, int) and matches > maximum:
                raise PortiaWireError(f"{path}: array exceeds maxContains.")


def validate_schema_id(schema_id: str, data: object) -> None:
    """Validate a reusable embedded value by its canonical Portia schema ID."""
    bundle = load_runtime_contract_bundle()
    schema = bundle.schemas.get(schema_id)
    if schema is None:
        raise UnsupportedContractError(
            f"schema is not in the Issue #37 runtime closure: {schema_id}"
        )
    _validate(schema, data, bundle=bundle, document_id=schema_id, path="$", depth=0)
