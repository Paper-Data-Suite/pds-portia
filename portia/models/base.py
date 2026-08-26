"""Immutable schema-backed base class for Portia public runtime records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar, cast

from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError
from portia.models.json_values import (
    FrozenJsonMapping,
    FrozenJsonValue,
    JsonValue,
    freeze_json_mapping,
    thaw_json_mapping,
)
from portia.models.schema_runtime import validate_wire_contract

IDENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "event": ("work_id",),
    "event_participant": ("participant_id",),
    "event_participant_role": ("role_id",),
    "work_relationship": ("relationship_id",),
    "actor": ("actor_id",),
    "actor_contact_point": ("contact_point_id",),
    "actor_student_relationship": ("relationship_id",),
    "actor_roster_student_collision": ("collision_id",),
    "account": ("account_id",),
    "observation": ("observation_id",),
    "review": ("review_id",),
    "classification": ("classification_id",),
    "hypothesis": ("hypothesis_id",),
    "determination": ("determination_id",),
    "response": ("response_id",),
    "communication": ("communication_id",),
    "support_process": ("work_id", "support_process_id"),
    "support_process_participant": ("participant_id",),
    "support_need": ("need_id",),
    "support_goal": ("goal_id",),
    "support": ("support_id",),
    "intervention": ("intervention_id",),
    "implementation": ("implementation_id",),
    "fidelity": ("fidelity_id",),
    "follow_up": ("follow_up_id",),
    "outcome": ("outcome_id",),
    "reentry": ("reentry_id",),
    "repair": ("repair_id",),
    "lifecycle_transition": ("transition_id",),
    "lifecycle_history_correction": ("correction_id",),
    "amendment": ("amendment_id",),
    "statement_of_disagreement": ("disagreement_id",),
    "dependency": ("dependency_id",),
    "record_migration": ("migration_id",),
    "ownership_correction": ("ownership_correction_id", "correction_id"),
    "exceptional_removal": ("removal_id",),
    "actor_directory_lifecycle_transition": ("transition_id",),
    "actor_directory_lifecycle_history_correction": ("correction_id",),
    "actor_directory_amendment": ("amendment_id",),
    "actor_directory_record_migration": ("migration_id",),
    "actor_directory_exceptional_removal": ("removal_id",),
    "operation_journal": ("operation_id",),
    "operation_current_pointer": ("operation_id",),
    "operation_lock": ("lock_id",),
    "quarantine_record": ("quarantine_id",),
    "quarantine_current_pointer": ("quarantine_id",),
    "integrity_finding": ("finding_id",),
    "finding_acknowledgement": ("acknowledgement_id",),
    "finding_suppression": ("suppression_id",),
    "finding_suppression_current_pointer": ("suppression_id",),
    "source_snapshot": ("snapshot_id",),
    "derived_index_metadata": ("generation_id", "index_id"),
    "derived_current_pointer": ("generation_id", "pointer_id"),
    "deliberate_export": ("export_id",),
}


@dataclass(frozen=True, slots=True, init=False)
class PortiaRecord:
    """One exact immutable public Portia contract representation.

    The full accepted wire object is retained as deeply frozen JSON.  Subclasses
    make contract/version identity explicit while shared typed value objects are
    available for callers that need reference-level operations.
    """

    _data: FrozenJsonMapping = field(repr=False)

    CONTRACT: ClassVar[str] = ""
    VERSION: ClassVar[str] = ""

    def __init__(self, data: Mapping[str, object]) -> None:
        if not self.CONTRACT or not self.VERSION:
            raise TypeError("PortiaRecord base class cannot be instantiated directly")
        validate_wire_contract(self.CONTRACT, self.VERSION, data)
        object.__setattr__(self, "_data", freeze_json_mapping(data))

    @property
    def contract(self) -> str:
        return self.CONTRACT

    @property
    def contract_version(self) -> str:
        return self.VERSION

    @property
    def schema_version(self) -> str | None:
        value = self._data.get("schema_version")
        return value if isinstance(value, str) else None

    @property
    def record_type(self) -> str | None:
        value = self._data.get("record_type")
        return value if isinstance(value, str) else None

    @property
    def module_id(self) -> str | None:
        value = self._data.get("module_id")
        return value if isinstance(value, str) else None

    @property
    def work_kind(self) -> str | None:
        value = self._data.get("work_kind")
        return value if isinstance(value, str) else None

    @property
    def data(self) -> dict[str, JsonValue]:
        """Return an isolated JSON-native copy of the exact public wire value."""
        return thaw_json_mapping(self._data)

    def to_dict(self) -> dict[str, JsonValue]:
        return self.data

    @classmethod
    def from_dict(cls, data: object) -> "PortiaRecord":
        if not isinstance(data, Mapping):
            raise PortiaLocalValidationError("record input must be a mapping.")
        if any(not isinstance(key, str) for key in data):
            raise PortiaLocalValidationError("record input keys must be strings.")
        return cls(cast(Mapping[str, object], data))

    def field(self, name: str) -> FrozenJsonValue | None:
        """Return one frozen field without making absent equivalent to null."""
        return self._data.get(name)

    @property
    def logical_id(self) -> str | None:
        """Return the record/work opaque identifier where this family has one."""
        for field_name in IDENTITY_FIELDS.get(self.CONTRACT, ()):
            value = self._data.get(field_name)
            if isinstance(value, str):
                return value
        return None

    @property
    def class_id(self) -> str | None:
        value = self._data.get("class_id")
        return value if isinstance(value, str) else None

    @property
    def work_id(self) -> str | None:
        value = self._data.get("work_id")
        if isinstance(value, str):
            return value
        work_ref = self._data.get("work_ref")
        if isinstance(work_ref, Mapping):
            nested = work_ref.get("work_id")
            return nested if isinstance(nested, str) else None
        return None

    @property
    def status(self) -> str | None:
        value = self._data.get("status")
        return value if isinstance(value, str) else None

    @property
    def created_at(self) -> ExplicitOffsetTimestamp | None:
        value = self._data.get("created_at")
        return ExplicitOffsetTimestamp(value) if isinstance(value, str) else None

    @property
    def updated_at(self) -> ExplicitOffsetTimestamp | None:
        value = self._data.get("updated_at")
        return ExplicitOffsetTimestamp(value) if isinstance(value, str) else None

    def __repr__(self) -> str:
        identity = self.logical_id
        suffix = f", logical_id={identity!r}" if identity is not None else ""
        return (
            f"{type(self).__name__}(contract={self.CONTRACT!r}, "
            f"version={self.VERSION!r}{suffix})"
        )
