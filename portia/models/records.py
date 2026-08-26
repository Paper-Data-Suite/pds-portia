"""Version-explicit immutable Portia public-record runtime types."""

from __future__ import annotations

from typing import Final

from portia.models.base import PortiaRecord
from portia.models.coverage import modelled_contract_versions
from portia.models.errors import UnsupportedContractError
from portia.models.json_values import JsonValue


class EventV1(PortiaRecord):
    """Exact ``event@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event"
    VERSION = "1"

class EventV2(PortiaRecord):
    """Exact ``event@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event"
    VERSION = "2"

class EventParticipantV1(PortiaRecord):
    """Exact ``event_participant@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant"
    VERSION = "1"

class EventParticipantV2(PortiaRecord):
    """Exact ``event_participant@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant"
    VERSION = "2"

class EventParticipantV3(PortiaRecord):
    """Exact ``event_participant@3`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant"
    VERSION = "3"

class EventParticipantRoleV1(PortiaRecord):
    """Exact ``event_participant_role@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant_role"
    VERSION = "1"

class EventParticipantRoleV2(PortiaRecord):
    """Exact ``event_participant_role@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant_role"
    VERSION = "2"

class EventParticipantRoleV3(PortiaRecord):
    """Exact ``event_participant_role@3`` runtime representation."""

    __slots__ = ()

    CONTRACT = "event_participant_role"
    VERSION = "3"

class WorkRelationshipV1(PortiaRecord):
    """Exact ``work_relationship@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "work_relationship"
    VERSION = "1"

class WorkRelationshipV2(PortiaRecord):
    """Exact ``work_relationship@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "work_relationship"
    VERSION = "2"

class ActorV1(PortiaRecord):
    """Exact ``actor@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor"
    VERSION = "1"

class ActorContactPointV1(PortiaRecord):
    """Exact ``actor_contact_point@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_contact_point"
    VERSION = "1"

class ActorStudentRelationshipV1(PortiaRecord):
    """Exact ``actor_student_relationship@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_student_relationship"
    VERSION = "1"

class ActorRosterStudentCollisionV1(PortiaRecord):
    """Exact ``actor_roster_student_collision@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_roster_student_collision"
    VERSION = "1"

class ActorDirectoryLifecycleTransitionV1(PortiaRecord):
    """Exact ``actor_directory_lifecycle_transition@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_directory_lifecycle_transition"
    VERSION = "1"

class ActorDirectoryLifecycleHistoryCorrectionV1(PortiaRecord):
    """Exact ``actor_directory_lifecycle_history_correction@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_directory_lifecycle_history_correction"
    VERSION = "1"

class ActorDirectoryAmendmentV1(PortiaRecord):
    """Exact ``actor_directory_amendment@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_directory_amendment"
    VERSION = "1"

class ActorDirectoryRecordMigrationV1(PortiaRecord):
    """Exact ``actor_directory_record_migration@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_directory_record_migration"
    VERSION = "1"

class ActorDirectoryExceptionalRemovalV1(PortiaRecord):
    """Exact ``actor_directory_exceptional_removal@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "actor_directory_exceptional_removal"
    VERSION = "1"

class AccountV1(PortiaRecord):
    """Exact ``account@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "account"
    VERSION = "1"

class AccountV2(PortiaRecord):
    """Exact ``account@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "account"
    VERSION = "2"

class ObservationV1(PortiaRecord):
    """Exact ``observation@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "observation"
    VERSION = "1"

class ObservationV2(PortiaRecord):
    """Exact ``observation@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "observation"
    VERSION = "2"

class ReviewV1(PortiaRecord):
    """Exact ``review@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "review"
    VERSION = "1"

class ClassificationV1(PortiaRecord):
    """Exact ``classification@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "classification"
    VERSION = "1"

class HypothesisV1(PortiaRecord):
    """Exact ``hypothesis@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "hypothesis"
    VERSION = "1"

class DeterminationV1(PortiaRecord):
    """Exact ``determination@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "determination"
    VERSION = "1"

class ResponseV1(PortiaRecord):
    """Exact ``response@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "response"
    VERSION = "1"

class CommunicationV1(PortiaRecord):
    """Exact ``communication@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "communication"
    VERSION = "1"

class SupportProcessV1(PortiaRecord):
    """Exact ``support_process@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "support_process"
    VERSION = "1"

class SupportProcessParticipantV1(PortiaRecord):
    """Exact ``support_process_participant@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "support_process_participant"
    VERSION = "1"

class SupportNeedV1(PortiaRecord):
    """Exact ``support_need@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "support_need"
    VERSION = "1"

class SupportGoalV1(PortiaRecord):
    """Exact ``support_goal@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "support_goal"
    VERSION = "1"

class SupportV1(PortiaRecord):
    """Exact ``support@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "support"
    VERSION = "1"

class InterventionV1(PortiaRecord):
    """Exact ``intervention@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "intervention"
    VERSION = "1"

class ImplementationV1(PortiaRecord):
    """Exact ``implementation@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "implementation"
    VERSION = "1"

class FidelityV1(PortiaRecord):
    """Exact ``fidelity@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "fidelity"
    VERSION = "1"

class FollowUpV1(PortiaRecord):
    """Exact ``follow_up@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "follow_up"
    VERSION = "1"

class OutcomeV1(PortiaRecord):
    """Exact ``outcome@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "outcome"
    VERSION = "1"

class ReentryV1(PortiaRecord):
    """Exact ``reentry@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "reentry"
    VERSION = "1"

class RepairV1(PortiaRecord):
    """Exact ``repair@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "repair"
    VERSION = "1"

class LifecycleTransitionV1(PortiaRecord):
    """Exact ``lifecycle_transition@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "lifecycle_transition"
    VERSION = "1"

class LifecycleHistoryCorrectionV1(PortiaRecord):
    """Exact ``lifecycle_history_correction@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "lifecycle_history_correction"
    VERSION = "1"

class AmendmentV1(PortiaRecord):
    """Exact ``amendment@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "amendment"
    VERSION = "1"

class StatementOfDisagreementV1(PortiaRecord):
    """Exact ``statement_of_disagreement@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "statement_of_disagreement"
    VERSION = "1"

class DependencyV1(PortiaRecord):
    """Exact ``dependency@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "dependency"
    VERSION = "1"

class RecordMigrationV1(PortiaRecord):
    """Exact ``record_migration@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "record_migration"
    VERSION = "1"

class OwnershipCorrectionV1(PortiaRecord):
    """Exact ``ownership_correction@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "ownership_correction"
    VERSION = "1"

class ExceptionalRemovalV1(PortiaRecord):
    """Exact ``exceptional_removal@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "exceptional_removal"
    VERSION = "1"

class OperationJournalV1(PortiaRecord):
    """Exact ``operation_journal@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "operation_journal"
    VERSION = "1"

class OperationJournalV2(PortiaRecord):
    """Exact ``operation_journal@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "operation_journal"
    VERSION = "2"

class OperationCurrentPointerV1(PortiaRecord):
    """Exact ``operation_current_pointer@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "operation_current_pointer"
    VERSION = "1"

class OperationLockV1(PortiaRecord):
    """Exact ``operation_lock@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "operation_lock"
    VERSION = "1"

class OperationLockV2(PortiaRecord):
    """Exact ``operation_lock@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "operation_lock"
    VERSION = "2"

class QuarantineRecordV1(PortiaRecord):
    """Exact ``quarantine_record@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "quarantine_record"
    VERSION = "1"

class QuarantineRecordV2(PortiaRecord):
    """Exact ``quarantine_record@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "quarantine_record"
    VERSION = "2"

class QuarantineCurrentPointerV1(PortiaRecord):
    """Exact ``quarantine_current_pointer@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "quarantine_current_pointer"
    VERSION = "1"

class IntegrityFindingV1(PortiaRecord):
    """Exact ``integrity_finding@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "integrity_finding"
    VERSION = "1"

class IntegrityFindingV2(PortiaRecord):
    """Exact ``integrity_finding@2`` runtime representation."""

    __slots__ = ()

    CONTRACT = "integrity_finding"
    VERSION = "2"

class FindingAcknowledgementV1(PortiaRecord):
    """Exact ``finding_acknowledgement@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "finding_acknowledgement"
    VERSION = "1"

class FindingSuppressionV1(PortiaRecord):
    """Exact ``finding_suppression@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "finding_suppression"
    VERSION = "1"

class FindingSuppressionCurrentPointerV1(PortiaRecord):
    """Exact ``finding_suppression_current_pointer@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "finding_suppression_current_pointer"
    VERSION = "1"

class SourceSnapshotV1(PortiaRecord):
    """Exact ``source_snapshot@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "source_snapshot"
    VERSION = "1"

class DerivedIndexMetadataV1(PortiaRecord):
    """Exact ``derived_index_metadata@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "derived_index_metadata"
    VERSION = "1"

class DerivedCurrentPointerV1(PortiaRecord):
    """Exact ``derived_current_pointer@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "derived_current_pointer"
    VERSION = "1"

class ExportSourceInventoryV1(PortiaRecord):
    """Exact ``export_source_inventory@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "export_source_inventory"
    VERSION = "1"

class DeliberateExportV1(PortiaRecord):
    """Exact ``deliberate_export@1`` runtime representation."""

    __slots__ = ()

    CONTRACT = "deliberate_export"
    VERSION = "1"

_RECORD_TYPES: Final[tuple[type[PortiaRecord], ...]] = (
    EventV1,
    EventV2,
    EventParticipantV1,
    EventParticipantV2,
    EventParticipantV3,
    EventParticipantRoleV1,
    EventParticipantRoleV2,
    EventParticipantRoleV3,
    WorkRelationshipV1,
    WorkRelationshipV2,
    ActorV1,
    ActorContactPointV1,
    ActorStudentRelationshipV1,
    ActorRosterStudentCollisionV1,
    ActorDirectoryLifecycleTransitionV1,
    ActorDirectoryLifecycleHistoryCorrectionV1,
    ActorDirectoryAmendmentV1,
    ActorDirectoryRecordMigrationV1,
    ActorDirectoryExceptionalRemovalV1,
    AccountV1,
    AccountV2,
    ObservationV1,
    ObservationV2,
    ReviewV1,
    ClassificationV1,
    HypothesisV1,
    DeterminationV1,
    ResponseV1,
    CommunicationV1,
    SupportProcessV1,
    SupportProcessParticipantV1,
    SupportNeedV1,
    SupportGoalV1,
    SupportV1,
    InterventionV1,
    ImplementationV1,
    FidelityV1,
    FollowUpV1,
    OutcomeV1,
    ReentryV1,
    RepairV1,
    LifecycleTransitionV1,
    LifecycleHistoryCorrectionV1,
    AmendmentV1,
    StatementOfDisagreementV1,
    DependencyV1,
    RecordMigrationV1,
    OwnershipCorrectionV1,
    ExceptionalRemovalV1,
    OperationJournalV1,
    OperationJournalV2,
    OperationCurrentPointerV1,
    OperationLockV1,
    OperationLockV2,
    QuarantineRecordV1,
    QuarantineRecordV2,
    QuarantineCurrentPointerV1,
    IntegrityFindingV1,
    IntegrityFindingV2,
    FindingAcknowledgementV1,
    FindingSuppressionV1,
    FindingSuppressionCurrentPointerV1,
    SourceSnapshotV1,
    DerivedIndexMetadataV1,
    DerivedCurrentPointerV1,
    ExportSourceInventoryV1,
    DeliberateExportV1,
)

MODEL_REGISTRY: Final[dict[tuple[str, str], type[PortiaRecord]]] = {
    (model.CONTRACT, model.VERSION): model for model in _RECORD_TYPES
}


def assert_registry_matches_coverage() -> None:
    """Raise if the explicit classes and coverage matrix drift apart."""
    expected = modelled_contract_versions()
    actual = frozenset(MODEL_REGISTRY)
    if expected != actual:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise RuntimeError(
            f"runtime model registry drift: missing={missing}, extra={extra}"
        )


def parse_portia_record(contract: str, version: str, data: object) -> PortiaRecord:
    """Parse one exact contract/version without implicit migration."""
    model_type = MODEL_REGISTRY.get((contract, version))
    if model_type is None:
        raise UnsupportedContractError(
            f"unsupported Portia runtime contract: {contract}@{version}"
        )
    return model_type.from_dict(data)


def portia_record_to_dict(record: PortiaRecord) -> dict[str, JsonValue]:
    """Return the exact JSON-native representation of a typed record."""
    if not isinstance(record, PortiaRecord):
        raise TypeError("record must be a PortiaRecord")
    return record.to_dict()


assert_registry_matches_coverage()
