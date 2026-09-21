"""Current-representation authority for the Issue #48 student view.

The view layer does not invent a second lifecycle engine.  Child records use
existing family ``require_current_use`` services.  Work roots use a narrower
representation-currentness rule so a closed/cancelled Event or a completed
Support Process is not confused with an obsolete superseded representation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, Protocol

from portia.models.errors import PortiaLocalValidationError
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage import (
    PortiaQuarantinedError,
    PortiaRepository,
    QuarantineGuard,
)
from portia.views.policy import projection_rule
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    CommunicationWorkflowService,
    DeterminationWorkflowService,
    FidelityWorkflowService,
    FollowUpWorkflowService,
    HypothesisWorkflowService,
    ImplementationWorkflowService,
    InterventionWorkflowService,
    ObservationWorkflowService,
    OutcomeWorkflowService,
    ParticipantWorkflowService,
    ReentryWorkflowService,
    RepairWorkflowService,
    ResponseWorkflowService,
    ReviewWorkflowService,
    RoleWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportWorkflowService,
    WorkRelationshipService,
)
from portia.workflows.common import work_target
from portia.workflows.errors import WorkflowPrerequisiteError

CurrentnessState = Literal["current", "noncurrent", "unavailable"]
TimelineSourceRef = ExactPortiaWorkRef | ExactPortiaWorkRecordRef


@dataclass(frozen=True, slots=True)
class CurrentnessDecision:
    """Bounded current-representation decision for one exact canonical source."""

    source_ref: TimelineSourceRef
    state: CurrentnessState
    reason_code: str

    def __post_init__(self) -> None:
        if self.state not in {"current", "noncurrent", "unavailable"}:
            raise PortiaLocalValidationError(
                f"unsupported currentness state: {self.state!r}"
            )
        if not isinstance(self.reason_code, str) or not self.reason_code:
            raise PortiaLocalValidationError(
                "currentness reason_code must be a non-empty string"
            )


class CurrentnessResolver(Protocol):
    def evaluate(self, source_ref: TimelineSourceRef) -> CurrentnessDecision: ...


_CHILD_SERVICES: Final[dict[str, type[object]]] = {
    "event_participant": ParticipantWorkflowService,
    "event_participant_role": RoleWorkflowService,
    "work_relationship": WorkRelationshipService,
    "account": AccountWorkflowService,
    "observation": ObservationWorkflowService,
    "review": ReviewWorkflowService,
    "classification": ClassificationWorkflowService,
    "hypothesis": HypothesisWorkflowService,
    "determination": DeterminationWorkflowService,
    "response": ResponseWorkflowService,
    "communication": CommunicationWorkflowService,
    "support_process_participant": SupportProcessParticipantWorkflowService,
    "support_need": SupportNeedWorkflowService,
    "support_goal": SupportGoalWorkflowService,
    "support": SupportWorkflowService,
    "intervention": InterventionWorkflowService,
    "implementation": ImplementationWorkflowService,
    "fidelity": FidelityWorkflowService,
    "follow_up": FollowUpWorkflowService,
    "outcome": OutcomeWorkflowService,
    "reentry": ReentryWorkflowService,
    "repair": RepairWorkflowService,
}


class StudentViewCurrentnessResolver:
    """Resolve current-view authority without timestamp/currentness inference."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.quarantine = quarantine or QuarantineGuard(self.workspace_root)

    def evaluate(self, source_ref: TimelineSourceRef) -> CurrentnessDecision:
        if isinstance(source_ref, ExactPortiaWorkRef):
            return self._work_root(source_ref)
        if not isinstance(source_ref, ExactPortiaWorkRecordRef):
            raise TypeError("source_ref must be an exact Portia work/source reference")
        return self._child(source_ref)

    def _work_root(self, work: ExactPortiaWorkRef) -> CurrentnessDecision:
        projection_rule(work.work_kind, work.contract_version)
        stored = self.repository.load_work(work)
        status = stored.record.status
        if status in {"invalidated", "superseded"}:
            return CurrentnessDecision(work, "noncurrent", "obsolete_representation")
        if work.work_kind == "event":
            if status == "draft":
                return CurrentnessDecision(work, "noncurrent", "draft_not_current")
            if status not in {"active", "closed", "cancelled"}:
                return CurrentnessDecision(work, "noncurrent", "event_not_current")
        elif work.work_kind == "support_process":
            if status == "proposed":
                return CurrentnessDecision(
                    work, "noncurrent", "proposed_support_process_not_current"
                )
            if status != "active":
                return CurrentnessDecision(
                    work, "noncurrent", "support_process_not_current"
                )
        else:
            raise PortiaLocalValidationError(
                f"unsupported current-view work root: {work.work_kind}"
            )
        try:
            self.quarantine.require_allowed(work_target(work), "block_current_use")
        except PortiaQuarantinedError:
            return CurrentnessDecision(work, "unavailable", "current_use_blocked")
        return CurrentnessDecision(work, "current", "current_representation")

    def _child(self, reference: ExactPortiaWorkRecordRef) -> CurrentnessDecision:
        rule = projection_rule(
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
        )
        if rule.surface != "domain_current":
            raise PortiaLocalValidationError(
                "child currentness requires a current domain projection contract"
            )
        stored = self.repository.load_work_record(
            reference.work_ref,
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
        if stored.record.status != "active":
            return CurrentnessDecision(
                reference, "noncurrent", "inactive_canonical_representation"
            )
        service_type = _CHILD_SERVICES.get(reference.record_ref.record_kind)
        if service_type is None:
            raise PortiaLocalValidationError(
                "no current-use authority registered for "
                f"{reference.record_ref.record_kind!r}"
            )
        service = service_type(  # type: ignore[call-arg]
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
        )
        require_current = getattr(service, "require_current_use", None)
        if not callable(require_current):
            raise RuntimeError(
                "registered current-use service lacks require_current_use: "
                f"{service_type.__name__}"
            )
        try:
            require_current(reference)
        except PortiaQuarantinedError:
            return CurrentnessDecision(
                reference, "unavailable", "current_use_blocked"
            )
        except WorkflowPrerequisiteError:
            # Preserve existence without claiming ordinary current truth.  The
            # detailed prerequisite/recovery explanation belongs to explicit
            # workflow/attention surfaces, not the generic student view.
            return CurrentnessDecision(
                reference, "unavailable", "current_authority_unavailable"
            )
        return CurrentnessDecision(reference, "current", "current_representation")
