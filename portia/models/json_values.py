"""Deeply immutable JSON-compatible runtime values."""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import TypeAlias, cast

from portia.models.errors import PortiaWireError

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
FrozenJsonValue: TypeAlias = (
    JsonScalar | tuple["FrozenJsonValue", ...] | Mapping[str, "FrozenJsonValue"]
)
FrozenJsonMapping: TypeAlias = Mapping[str, FrozenJsonValue]


def freeze_json(value: object, *, path: str = "$") -> FrozenJsonValue:
    """Return an immutable JSON value without normalizing lexical content."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PortiaWireError(f"{path}: JSON numbers must be finite.")
        return value
    if isinstance(value, list):
        return tuple(
            freeze_json(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        result: dict[str, FrozenJsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise PortiaWireError(f"{path}: object keys must be strings.")
            result[key] = freeze_json(item, path=f"{path}.{key}")
        return MappingProxyType(result)
    raise PortiaWireError(
        f"{path}: value must be JSON-compatible, got {type(value).__name__}."
    )


def freeze_json_mapping(value: object, *, path: str = "$") -> FrozenJsonMapping:
    """Freeze a JSON object and reject every other top-level type."""
    frozen = freeze_json(value, path=path)
    if not isinstance(frozen, Mapping):
        raise PortiaWireError(f"{path}: record must be a JSON object.")
    return frozen


def thaw_json(value: FrozenJsonValue) -> JsonValue:
    """Return an isolated JSON-native mutable copy of a frozen value."""
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return value


def thaw_json_mapping(value: FrozenJsonMapping) -> dict[str, JsonValue]:
    """Return an isolated JSON-native copy of a frozen object."""
    thawed = thaw_json(cast(FrozenJsonValue, value))
    if not isinstance(thawed, dict):  # defensive; mapping input guarantees this.
        raise TypeError("frozen mapping thaw did not produce an object")
    return thawed


def json_equality_key(value: object) -> object:
    """Return a hashable key preserving JSON equality semantics for uniqueItems."""
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("number", Decimal(value))
    if isinstance(value, float):
        if not math.isfinite(value):
            return ("invalid-number", repr(value))
        return ("number", Decimal(str(value)))
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("list", tuple(json_equality_key(item) for item in value))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            return ("invalid-object", id(value))
        return (
            "object",
            tuple(
                sorted(
                    (cast(str, key), json_equality_key(item))
                    for key, item in value.items()
                )
            ),
        )
    return ("non-json", id(value))
