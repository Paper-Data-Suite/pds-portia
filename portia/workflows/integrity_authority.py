"""Closed teacher-local authority for Integrity Finding operator workflows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from portia.workflows.errors import WorkflowPrerequisiteError

TEACHER_LOCAL_SUPPRESSION_POLICY_ID = "portia.finding_suppression.teacher_local"
TEACHER_LOCAL_SUPPRESSION_POLICY_VERSION = "1"
TEACHER_LOCAL_OPERATOR_ROLE = "teacher_local_operator"
TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND = "portia_local_authority"
TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID = (
    "portia.teacher_local_workspace_operator"
)
TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION = "1"

ACKNOWLEDGEMENT_CATEGORIES = frozenset(
    {
        "reviewed",
        "assigned_for_follow_up",
        "known_limitation",
        "awaiting_external_evidence",
    }
)


@dataclass(frozen=True, slots=True)
class SuppressionAuthorizationReference:
    """One exact package-owned authorization-reference binding."""

    kind: str
    reference_id: str
    contract_version: str


@dataclass(frozen=True, slots=True)
class SuppressionPolicyDefinition:
    """One immutable known version of a bounded suppression policy."""

    policy_id: str
    policy_version: str
    allowed_asserted_roles: frozenset[str]
    allowed_attribution_agent_types: frozenset[str]
    authorization_reference: SuppressionAuthorizationReference


@dataclass(frozen=True, slots=True)
class SuppressionAuthorizationDecision:
    """Validated exact authority while preserving attribution-only agent data."""

    policy: SuppressionPolicyDefinition
    authorized_by: Mapping[str, object]
    asserted_role: str
    authorization_reference: SuppressionAuthorizationReference


_TEACHER_LOCAL_REFERENCE = SuppressionAuthorizationReference(
    kind=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
    reference_id=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
    contract_version=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
)
_TEACHER_LOCAL_POLICY_V1 = SuppressionPolicyDefinition(
    policy_id=TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
    policy_version=TEACHER_LOCAL_SUPPRESSION_POLICY_VERSION,
    allowed_asserted_roles=frozenset({TEACHER_LOCAL_OPERATOR_ROLE}),
    allowed_attribution_agent_types=frozenset({"local_operator"}),
    authorization_reference=_TEACHER_LOCAL_REFERENCE,
)


def _mapping(
    value: object,
    *,
    fields: frozenset[str],
    description: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise WorkflowPrerequisiteError(
            f"{description} does not have the exact supported authority shape"
        )
    return value


def _string(value: object, *, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise WorkflowPrerequisiteError(f"{description} is not a supported token")
    return value


def _attribution_agent(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise WorkflowPrerequisiteError("attribution agent is not an object")
    agent_type = value.get("type")
    if agent_type == "local_operator":
        agent = _mapping(
            value,
            fields=frozenset({"type", "display_label"}),
            description="local-operator attribution",
        )
        label = agent.get("display_label")
        if not isinstance(label, str) or not label.strip():
            raise WorkflowPrerequisiteError(
                "local-operator attribution has no display label"
            )
        return agent
    if agent_type == "system_process":
        agent = _mapping(
            value,
            fields=frozenset({"type", "process_id"}),
            description="system-process attribution",
        )
        _string(agent.get("process_id"), description="system process ID")
        return agent
    raise WorkflowPrerequisiteError(
        "attribution-agent form is not authorized for Integrity Finding operations"
    )


class IntegrityOperatorAuthority:
    """Explicit package authority for bounded teacher-local finding operations.

    This is application-local capability, not authentication, institutional role
    assignment, Actor Directory authority, or a general permissions system.
    """

    def __init__(
        self,
        *,
        policies: Iterable[SuppressionPolicyDefinition] | None = None,
        current_policy_versions: Mapping[str, str] | None = None,
        acknowledgement_system_processes: Mapping[str, Iterable[str]] | None = None,
    ) -> None:
        production_policies = policies is None
        selected_policies = (
            (_TEACHER_LOCAL_POLICY_V1,) if policies is None else tuple(policies)
        )
        policy_keys = [
            (definition.policy_id, definition.policy_version)
            for definition in selected_policies
        ]
        if len(policy_keys) != len(set(policy_keys)):
            raise WorkflowPrerequisiteError(
                "Integrity Finding authority contains duplicate policy versions"
            )
        self._policies = tuple(selected_policies)

        current_items: tuple[tuple[str, str], ...]
        if current_policy_versions is None:
            current_items = (
                (
                    TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
                    TEACHER_LOCAL_SUPPRESSION_POLICY_VERSION,
                ),
            ) if production_policies else ()
        else:
            current_items = tuple(sorted(current_policy_versions.items()))
        self._current_policy_versions = current_items

        permissions = acknowledgement_system_processes or {}
        self._acknowledgement_system_processes = tuple(
            sorted(
                (process_id, frozenset(categories))
                for process_id, categories in permissions.items()
            )
        )

    @classmethod
    def teacher_local(cls) -> IntegrityOperatorAuthority:
        """Return the package-owned production teacher-local authority."""
        return cls()

    def resolve_policy(
        self,
        policy_id: str,
        policy_version: str,
    ) -> SuppressionPolicyDefinition:
        """Resolve one exact known historical policy version."""
        for definition in self._policies:
            if (
                definition.policy_id == policy_id
                and definition.policy_version == policy_version
            ):
                return definition
        raise WorkflowPrerequisiteError(
            "suppression policy ID/version is not known to application authority"
        )

    def resolve_current_policy(self, policy_id: str) -> SuppressionPolicyDefinition:
        """Resolve only the version explicitly selected as current."""
        known_policy = any(
            definition.policy_id == policy_id for definition in self._policies
        )
        if not known_policy:
            raise WorkflowPrerequisiteError(
                "suppression policy ID is not known to application authority"
            )
        selections = [
            version
            for selected_id, version in self._current_policy_versions
            if selected_id == policy_id
        ]
        if len(selections) != 1:
            raise WorkflowPrerequisiteError(
                "suppression policy has no unambiguous explicit current version"
            )
        return self.resolve_policy(policy_id, selections[0])

    def validate_suppression_authorization(
        self,
        *,
        policy: Mapping[str, object],
        authorization: Mapping[str, object],
    ) -> SuppressionAuthorizationDecision:
        """Validate an exact current policy and its exact authority binding."""
        policy_value = _mapping(
            policy,
            fields=frozenset({"policy_id", "policy_version"}),
            description="suppression policy binding",
        )
        policy_id = _string(
            policy_value.get("policy_id"), description="suppression policy ID"
        )
        policy_version = _string(
            policy_value.get("policy_version"),
            description="suppression policy version",
        )
        definition = self.resolve_policy(policy_id, policy_version)
        current = self.resolve_current_policy(policy_id)
        if current.policy_version != definition.policy_version:
            raise WorkflowPrerequisiteError(
                "new suppression requires the explicitly current policy version"
            )

        authorization_value = _mapping(
            authorization,
            fields=frozenset(
                {"authorized_by", "asserted_role", "authorization_reference"}
            ),
            description="suppression authorization binding",
        )
        agent = _attribution_agent(authorization_value.get("authorized_by"))
        agent_type = _string(
            agent.get("type"), description="authorized attribution-agent type"
        )
        if agent_type not in definition.allowed_attribution_agent_types:
            raise WorkflowPrerequisiteError(
                "attribution-agent form is not allowed by suppression policy"
            )
        asserted_role = _string(
            authorization_value.get("asserted_role"),
            description="suppression asserted role",
        )
        if asserted_role not in definition.allowed_asserted_roles:
            raise WorkflowPrerequisiteError(
                "asserted role is not allowed by suppression policy"
            )

        reference_value = _mapping(
            authorization_value.get("authorization_reference"),
            fields=frozenset({"kind", "reference_id", "contract_version"}),
            description="suppression authorization reference",
        )
        reference = SuppressionAuthorizationReference(
            kind=_string(
                reference_value.get("kind"),
                description="authorization-reference kind",
            ),
            reference_id=_string(
                reference_value.get("reference_id"),
                description="authorization-reference ID",
            ),
            contract_version=_string(
                reference_value.get("contract_version"),
                description="authorization-reference contract version",
            ),
        )
        if reference != definition.authorization_reference:
            raise WorkflowPrerequisiteError(
                "authorization reference does not belong to suppression policy"
            )

        return SuppressionAuthorizationDecision(
            policy=definition,
            authorized_by=MappingProxyType(dict(agent)),
            asserted_role=asserted_role,
            authorization_reference=reference,
        )

    def policy_version_changed(
        self,
        policy_id: str,
        bound_policy_version: str,
    ) -> bool:
        """Prove change against exact known history and explicit current selection."""
        bound = self.resolve_policy(policy_id, bound_policy_version)
        current = self.resolve_current_policy(policy_id)
        return current.policy_version != bound.policy_version

    def validate_acknowledgement_actor(
        self,
        acknowledged_by: Mapping[str, object],
        acknowledgement_category: str,
    ) -> None:
        """Authorize one bounded acknowledgement category before persistence."""
        if acknowledgement_category not in ACKNOWLEDGEMENT_CATEGORIES:
            raise WorkflowPrerequisiteError(
                "acknowledgement category is not authorized by teacher-local policy"
            )
        agent = _attribution_agent(acknowledged_by)
        agent_type = agent.get("type")
        if agent_type == "local_operator":
            return
        process_id = _string(
            agent.get("process_id"), description="acknowledgement system process ID"
        )
        for registered_id, categories in self._acknowledgement_system_processes:
            if registered_id == process_id and acknowledgement_category in categories:
                return
        raise WorkflowPrerequisiteError(
            "system process is not registered for acknowledgement category"
        )
