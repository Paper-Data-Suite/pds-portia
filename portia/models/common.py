"""Shared immutable text, timestamp, attribution, and provenance values."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Final, Self

from portia.models.errors import PortiaLocalValidationError
from portia.models.json_values import (
    FrozenJsonMapping,
    JsonValue,
    freeze_json_mapping,
    thaw_json_mapping,
)
from portia.models.schema_runtime import validate_schema_id

_BASE: Final[str] = "https://paper-data-suite.github.io/pds-portia/schemas/v1/"
ATTRIBUTION_AGENT_SCHEMA_ID: Final[str] = _BASE + "attribution/attribution-agent.schema.json"
CREATION_SOURCE_SCHEMA_ID: Final[str] = _BASE + "provenance/creation-source.schema.json"
PERSON_DISPLAY_SNAPSHOT_SCHEMA_ID: Final[str] = _BASE + "snapshots/person-display-snapshot.schema.json"
PORTIA_TARGET_REF_SCHEMA_ID: Final[str] = _BASE + "targets/portia-target-ref.schema.json"
SUPPORT_PROCESS_TARGET_REF_SCHEMA_ID: Final[str] = (
    _BASE + "targets/support-process-target-ref.schema.json"
)
JUDGMENT_EVIDENCE_REF_SCHEMA_ID: Final[str] = (
    _BASE + "references/judgment-evidence-ref.schema.json"
)
PLANNED_SCHEDULE_SCHEMA_ID: Final[str] = (
    _BASE + "support-processes/planned-schedule.schema.json"
)


@dataclass(frozen=True, slots=True)
class ExplicitOffsetTimestamp:
    """RFC 3339 timestamp preserving the exact accepted lexical representation."""

    text: str
    _parsed: datetime = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise PortiaLocalValidationError("timestamp must be a string.")
        if re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}"
            r"(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})",
            self.text,
        ) is None:
            raise PortiaLocalValidationError("timestamp must be an RFC 3339 date-time.")
        candidate = self.text[:-1] + "+00:00" if self.text.endswith("Z") else self.text
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise PortiaLocalValidationError("timestamp must be a valid RFC 3339 date-time.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise PortiaLocalValidationError("timestamp must carry an explicit UTC offset or Z.")
        object.__setattr__(self, "_parsed", parsed)

    @property
    def datetime(self) -> datetime:
        """Return the timezone-aware parsed instant without changing wire text."""
        return self._parsed


@dataclass(frozen=True, slots=True, init=False)
class _SchemaValue:
    _data: FrozenJsonMapping

    SCHEMA_ID: ClassVar[str] = ""

    def __init__(self, data: Mapping[str, object]) -> None:
        validate_schema_id(self.SCHEMA_ID, data)
        object.__setattr__(self, "_data", freeze_json_mapping(data))

    @property
    def data(self) -> dict[str, JsonValue]:
        return thaw_json_mapping(self._data)

    @classmethod
    def from_dict(cls, data: object) -> Self:
        if not isinstance(data, Mapping):
            raise PortiaLocalValidationError("value must be a mapping.")
        return cls(data)

    def to_dict(self) -> dict[str, JsonValue]:
        return self.data


class AttributionAgent(_SchemaValue):
    """Exact accepted attribution-agent value; never an authority inference."""

    __slots__ = ()

    SCHEMA_ID = ATTRIBUTION_AGENT_SCHEMA_ID

    @property
    def type(self) -> str:
        return str(self._data["type"])


class CreationSource(_SchemaValue):
    """Exact accepted creation provenance value."""

    __slots__ = ()

    SCHEMA_ID = CREATION_SOURCE_SCHEMA_ID

    @property
    def type(self) -> str:
        return str(self._data["type"])


class PersonDisplaySnapshot(_SchemaValue):
    """Nonauthoritative historical display snapshot."""

    __slots__ = ()

    SCHEMA_ID = PERSON_DISPLAY_SNAPSHOT_SCHEMA_ID

    @property
    def display_name(self) -> str:
        return str(self._data["display_name"])


class PortiaTargetRef(_SchemaValue):
    """Accepted Event-local target union without identity inference."""

    __slots__ = ()
    SCHEMA_ID = PORTIA_TARGET_REF_SCHEMA_ID

    @property
    def kind(self) -> str:
        return str(self._data["kind"])


class SupportProcessTargetRef(_SchemaValue):
    """Accepted Support Process target union."""

    __slots__ = ()
    SCHEMA_ID = SUPPORT_PROCESS_TARGET_REF_SCHEMA_ID

    @property
    def kind(self) -> str:
        return str(self._data["kind"])


class JudgmentEvidenceRef(_SchemaValue):
    """Typed judgment-evidence locator with no truth/weight inference."""

    __slots__ = ()
    SCHEMA_ID = JUDGMENT_EVIDENCE_REF_SCHEMA_ID

    @property
    def kind(self) -> str:
        return str(self._data["kind"])


class PlannedSchedule(_SchemaValue):
    """Planning-only schedule value; it never establishes Implementation."""

    __slots__ = ()
    SCHEMA_ID = PLANNED_SCHEDULE_SCHEMA_ID

    @property
    def kind(self) -> str:
        return str(self._data["kind"])
