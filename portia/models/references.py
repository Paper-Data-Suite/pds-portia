"""Typed immutable Portia reference values."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from pds_core.routing_models import (
    ModuleRecordRef,
    ModuleWorkRef,
    RoutingModelError,
    module_record_ref_from_dict,
    module_record_ref_to_dict,
    module_work_ref_from_dict,
    module_work_ref_to_dict,
    validate_module_record_ref,
    validate_module_work_ref,
)

from portia.models.errors import PortiaLocalValidationError, PortiaWireError
from portia.models.identifiers import validate_external_id, validate_portia_id
from portia.models.schema_runtime import validate_schema_id

_BASE: Final[str] = "https://paper-data-suite.github.io/pds-portia/schemas/v1/references/"
ROSTER_STUDENT_REF_SCHEMA_ID: Final[str] = _BASE + "roster-student-ref.schema.json"
ACTOR_REF_SCHEMA_ID: Final[str] = _BASE + "actor-ref.schema.json"
LOCAL_RECORD_REF_SCHEMA_ID: Final[str] = _BASE + "local-record-ref.schema.json"
PORTIA_WORK_REF_SCHEMA_ID: Final[str] = _BASE + "portia-work-ref.schema.json"
PORTIA_WORK_RECORD_REF_SCHEMA_ID: Final[str] = _BASE + "portia-work-record-ref.schema.json"
MODULE_WORK_RECORD_REF_SCHEMA_ID: Final[str] = _BASE + "module-work-record-ref.schema.json"
EXACT_LOCAL_RECORD_REF_SCHEMA_ID: Final[str] = _BASE + "exact-local-record-ref.schema.json"
EXACT_PORTIA_WORK_REF_SCHEMA_ID: Final[str] = _BASE + "exact-portia-work-ref.schema.json"
EXACT_PORTIA_WORK_RECORD_REF_SCHEMA_ID: Final[str] = (
    _BASE + "exact-portia-work-record-ref.schema.json"
)
EXACT_ACTOR_REF_SCHEMA_ID: Final[str] = _BASE + "exact-actor-ref.schema.json"
EXACT_ACTOR_CONTACT_POINT_REF_SCHEMA_ID: Final[str] = (
    _BASE + "exact-actor-contact-point-ref.schema.json"
)
EXACT_ACTOR_STUDENT_RELATIONSHIP_REF_SCHEMA_ID: Final[str] = (
    _BASE + "exact-actor-student-relationship-ref.schema.json"
)


@dataclass(frozen=True, slots=True)
class RosterStudentRef:
    """Exact class-qualified Core roster identity."""

    class_id: str
    student_id: str

    def __post_init__(self) -> None:
        validate_external_id(self.class_id, "class_id")
        validate_external_id(self.student_id, "student_id")

    @classmethod
    def from_dict(cls, data: object) -> "RosterStudentRef":
        validate_schema_id(ROSTER_STUDENT_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(class_id=cast(str, mapping["class_id"]), student_id=cast(str, mapping["student_id"]))

    def to_dict(self) -> dict[str, object]:
        return {"class_id": self.class_id, "student_id": self.student_id}


@dataclass(frozen=True, slots=True)
class ActorRef:
    """Identity-only reference to one Portia Actor Directory record."""

    actor_id: str

    def __post_init__(self) -> None:
        validate_portia_id(self.actor_id, "actr_", "actor_id")

    @classmethod
    def from_dict(cls, data: object) -> "ActorRef":
        validate_schema_id(ACTOR_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(actor_id=cast(str, mapping["actor_id"]))

    def to_dict(self) -> dict[str, object]:
        return {"actor_id": self.actor_id}


@dataclass(frozen=True, slots=True)
class LocalRecordRef:
    """Typed record reference inside one unambiguous containing Portia work."""

    record_kind: str
    record_id: str
    contract_version: str | None

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "record_kind")
        validate_external_id(self.record_id, "record_id")
        if self.contract_version is not None:
            validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "LocalRecordRef":
        validate_schema_id(LOCAL_RECORD_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        version = mapping["contract_version"]
        return cls(
            record_kind=cast(str, mapping["record_kind"]),
            record_id=cast(str, mapping["record_id"]),
            contract_version=cast(str | None, version),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_kind": self.record_kind,
            "record_id": self.record_id,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class PortiaWorkRef:
    """Complete version-aware reference to one Portia Event or Support Process."""

    class_id: str
    work_id: str
    work_kind: str
    contract_version: str | None
    module_id: str = "portia"

    def __post_init__(self) -> None:
        validate_external_id(self.class_id, "class_id")
        if self.module_id != "portia":
            raise PortiaLocalValidationError('module_id must be "portia".')
        if self.work_kind == "event":
            validate_portia_id(self.work_id, "evt_", "work_id")
        elif self.work_kind == "support_process":
            validate_portia_id(self.work_id, "sup_", "work_id")
        else:
            raise PortiaLocalValidationError(
                "work_kind must be event or support_process."
            )
        if self.contract_version is not None:
            validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "PortiaWorkRef":
        validate_schema_id(PORTIA_WORK_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            class_id=cast(str, mapping["class_id"]),
            work_id=cast(str, mapping["work_id"]),
            work_kind=cast(str, mapping["work_kind"]),
            contract_version=cast(str | None, mapping["contract_version"]),
            module_id=cast(str, mapping["module_id"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "class_id": self.class_id,
            "work_id": self.work_id,
            "work_kind": self.work_kind,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class PortiaWorkRecordRef:
    """Complete reference to one child record in one explicit Portia work."""

    work_ref: PortiaWorkRef
    record_ref: LocalRecordRef

    @classmethod
    def from_dict(cls, data: object) -> "PortiaWorkRecordRef":
        validate_schema_id(PORTIA_WORK_RECORD_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            work_ref=PortiaWorkRef.from_dict(mapping["work_ref"]),
            record_ref=LocalRecordRef.from_dict(mapping["record_ref"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "work_ref": self.work_ref.to_dict(),
            "record_ref": self.record_ref.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ModuleWorkRecordRef:
    """Portia structural composition of exact Core work and record refs."""

    work_ref: ModuleWorkRef
    record_ref: ModuleRecordRef

    def __post_init__(self) -> None:
        try:
            validate_module_work_ref(self.work_ref)
            validate_module_record_ref(self.record_ref)
        except RoutingModelError as exc:
            raise PortiaLocalValidationError(f"invalid Core reference: {exc}") from exc

    @classmethod
    def from_dict(cls, data: object) -> "ModuleWorkRecordRef":
        validate_schema_id(MODULE_WORK_RECORD_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        try:
            work = module_work_ref_from_dict(mapping["work_ref"])
            record = module_record_ref_from_dict(mapping["record_ref"])
        except RoutingModelError as exc:
            raise PortiaWireError(f"invalid Core reference: {exc}") from exc
        return cls(work_ref=work, record_ref=record)

    def to_dict(self) -> dict[str, object]:
        return {
            "work_ref": module_work_ref_to_dict(self.work_ref),
            "record_ref": module_record_ref_to_dict(self.record_ref),
        }


@dataclass(frozen=True, slots=True)
class ExactLocalRecordRef:
    """Reference to one exact historical/current local record representation."""

    record_kind: str
    record_id: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_external_id(self.record_kind, "record_kind")
        validate_external_id(self.record_id, "record_id")
        validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "ExactLocalRecordRef":
        validate_schema_id(EXACT_LOCAL_RECORD_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            record_kind=cast(str, mapping["record_kind"]),
            record_id=cast(str, mapping["record_id"]),
            contract_version=cast(str, mapping["contract_version"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_kind": self.record_kind,
            "record_id": self.record_id,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class ExactPortiaWorkRef:
    """Reference to one exact Portia work representation."""

    class_id: str
    work_id: str
    work_kind: str
    contract_version: str
    module_id: str = "portia"

    def __post_init__(self) -> None:
        validate_external_id(self.class_id, "class_id")
        if self.module_id != "portia":
            raise PortiaLocalValidationError('module_id must be "portia".')
        if self.work_kind == "event":
            validate_portia_id(self.work_id, "evt_", "work_id")
        elif self.work_kind == "support_process":
            validate_portia_id(self.work_id, "sup_", "work_id")
        else:
            raise PortiaLocalValidationError(
                "work_kind must be event or support_process."
            )
        validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "ExactPortiaWorkRef":
        validate_schema_id(EXACT_PORTIA_WORK_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            class_id=cast(str, mapping["class_id"]),
            work_id=cast(str, mapping["work_id"]),
            work_kind=cast(str, mapping["work_kind"]),
            contract_version=cast(str, mapping["contract_version"]),
            module_id=cast(str, mapping["module_id"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "class_id": self.class_id,
            "work_id": self.work_id,
            "work_kind": self.work_kind,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class ExactPortiaWorkRecordRef:
    """Reference to one exact child representation in one exact Portia work."""

    work_ref: ExactPortiaWorkRef
    record_ref: ExactLocalRecordRef

    @classmethod
    def from_dict(cls, data: object) -> "ExactPortiaWorkRecordRef":
        validate_schema_id(EXACT_PORTIA_WORK_RECORD_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            work_ref=ExactPortiaWorkRef.from_dict(mapping["work_ref"]),
            record_ref=ExactLocalRecordRef.from_dict(mapping["record_ref"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "work_ref": self.work_ref.to_dict(),
            "record_ref": self.record_ref.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ExactActorRef:
    """Reference to one exact Actor root representation."""

    actor_id: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_portia_id(self.actor_id, "actr_", "actor_id")
        validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "ExactActorRef":
        validate_schema_id(EXACT_ACTOR_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            actor_id=cast(str, mapping["actor_id"]),
            contract_version=cast(str, mapping["contract_version"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class ExactActorContactPointRef:
    """Reference to one exact Contact Point beneath one Actor."""

    actor_id: str
    contact_point_id: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_portia_id(self.actor_id, "actr_", "actor_id")
        validate_portia_id(self.contact_point_id, "acp_", "contact_point_id")
        validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "ExactActorContactPointRef":
        validate_schema_id(EXACT_ACTOR_CONTACT_POINT_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            actor_id=cast(str, mapping["actor_id"]),
            contact_point_id=cast(str, mapping["contact_point_id"]),
            contract_version=cast(str, mapping["contract_version"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "contact_point_id": self.contact_point_id,
            "contract_version": self.contract_version,
        }


@dataclass(frozen=True, slots=True)
class ExactActorStudentRelationshipRef:
    """Reference to one exact Actor-to-Student Relationship representation."""

    actor_id: str
    relationship_id: str
    contract_version: str

    def __post_init__(self) -> None:
        validate_portia_id(self.actor_id, "actr_", "actor_id")
        validate_portia_id(self.relationship_id, "asrel_", "relationship_id")
        validate_external_id(self.contract_version, "contract_version")

    @classmethod
    def from_dict(cls, data: object) -> "ExactActorStudentRelationshipRef":
        validate_schema_id(EXACT_ACTOR_STUDENT_RELATIONSHIP_REF_SCHEMA_ID, data)
        mapping = cast(Mapping[str, object], data)
        return cls(
            actor_id=cast(str, mapping["actor_id"]),
            relationship_id=cast(str, mapping["relationship_id"]),
            contract_version=cast(str, mapping["contract_version"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "relationship_id": self.relationship_id,
            "contract_version": self.contract_version,
        }
