from __future__ import annotations

from collections.abc import Mapping

import pytest

from portia.workflows import (
    ACKNOWLEDGEMENT_CATEGORIES,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
    TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
    TEACHER_LOCAL_OPERATOR_ROLE,
    TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
    TEACHER_LOCAL_SUPPRESSION_POLICY_VERSION,
    IntegrityOperatorAuthority,
    SuppressionAuthorizationReference,
    SuppressionPolicyDefinition,
    WorkflowPrerequisiteError,
)


def policy_binding(*, policy_id: str = TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
                   policy_version: str = "1") -> dict[str, object]:
    return {"policy_id": policy_id, "policy_version": policy_version}


def authorization_binding(
    *,
    authorized_by: Mapping[str, object] | None = None,
    asserted_role: str = TEACHER_LOCAL_OPERATOR_ROLE,
    kind: str = TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
    reference_id: str = TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
    contract_version: str = TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
) -> dict[str, object]:
    return {
        "authorized_by": dict(
            authorized_by
            or {"type": "local_operator", "display_label": "Local teacher"}
        ),
        "asserted_role": asserted_role,
        "authorization_reference": {
            "kind": kind,
            "reference_id": reference_id,
            "contract_version": contract_version,
        },
    }


def policy(version: str) -> SuppressionPolicyDefinition:
    return SuppressionPolicyDefinition(
        policy_id=TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
        policy_version=version,
        allowed_asserted_roles=frozenset({TEACHER_LOCAL_OPERATOR_ROLE}),
        allowed_attribution_agent_types=frozenset({"local_operator"}),
        authorization_reference=SuppressionAuthorizationReference(
            kind=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_KIND,
            reference_id=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_ID,
            contract_version=TEACHER_LOCAL_AUTHORIZATION_REFERENCE_VERSION,
        ),
    )


def test_production_policy_resolution_is_exact_and_explicit() -> None:
    authority = IntegrityOperatorAuthority.teacher_local()

    historical = authority.resolve_policy(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID,
        TEACHER_LOCAL_SUPPRESSION_POLICY_VERSION,
    )
    current = authority.resolve_current_policy(TEACHER_LOCAL_SUPPRESSION_POLICY_ID)

    assert historical.policy_id == TEACHER_LOCAL_SUPPRESSION_POLICY_ID
    assert historical.policy_version == "1"
    assert current == historical


@pytest.mark.parametrize(
    ("policy_id", "policy_version"),
    [("unknown.policy", "1"), (TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "99")],
)
def test_unknown_policy_or_version_fails_closed(
    policy_id: str,
    policy_version: str,
) -> None:
    authority = IntegrityOperatorAuthority.teacher_local()
    with pytest.raises(WorkflowPrerequisiteError, match="not known"):
        authority.resolve_policy(policy_id, policy_version)


def test_historical_resolution_is_separate_from_explicit_current_selection() -> None:
    authority = IntegrityOperatorAuthority(
        policies=(policy("1"), policy("2")),
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "1"},
    )

    assert authority.resolve_policy(TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "2")
    assert authority.resolve_current_policy(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID
    ).policy_version == "1"
    assert not authority.policy_version_changed(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1"
    )


def test_exact_production_suppression_authorization_is_accepted() -> None:
    authority = IntegrityOperatorAuthority.teacher_local()
    binding = authorization_binding()

    decision = authority.validate_suppression_authorization(
        policy=policy_binding(), authorization=binding
    )

    assert decision.policy.policy_version == "1"
    assert decision.asserted_role == TEACHER_LOCAL_OPERATOR_ROLE
    assert dict(decision.authorized_by) == binding["authorized_by"]


@pytest.mark.parametrize(
    ("policy_value", "authorization_value", "message"),
    [
        (policy_binding(policy_id="wrong.policy"), authorization_binding(), "not known"),
        (policy_binding(policy_version="99"), authorization_binding(), "not known"),
        (
            policy_binding(),
            authorization_binding(asserted_role="teacher"),
            "asserted role",
        ),
        (
            policy_binding(),
            authorization_binding(kind="local_policy"),
            "does not belong",
        ),
        (
            policy_binding(),
            authorization_binding(reference_id="wrong.reference"),
            "does not belong",
        ),
        (
            policy_binding(),
            authorization_binding(contract_version="2"),
            "does not belong",
        ),
        (
            policy_binding(),
            authorization_binding(
                authorized_by={
                    "type": "system_process",
                    "process_id": "portia_integrity_scan",
                }
            ),
            "not allowed",
        ),
    ],
)
def test_suppression_authorization_mismatch_fails_closed(
    policy_value: dict[str, object],
    authorization_value: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match=message):
        IntegrityOperatorAuthority.teacher_local().validate_suppression_authorization(
            policy=policy_value,
            authorization=authorization_value,
        )


def test_known_noncurrent_policy_rejects_new_suppression() -> None:
    authority = IntegrityOperatorAuthority(
        policies=(policy("1"), policy("2")),
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "2"},
    )
    with pytest.raises(WorkflowPrerequisiteError, match="explicitly current"):
        authority.validate_suppression_authorization(
            policy=policy_binding(policy_version="1"),
            authorization=authorization_binding(),
        )


def test_display_label_is_attribution_only() -> None:
    authority = IntegrityOperatorAuthority.teacher_local()
    first = authority.validate_suppression_authorization(
        policy=policy_binding(),
        authorization=authorization_binding(
            authorized_by={"type": "local_operator", "display_label": "Teacher A"}
        ),
    )
    second = authority.validate_suppression_authorization(
        policy=policy_binding(),
        authorization=authorization_binding(
            authorized_by={"type": "local_operator", "display_label": "Different label"}
        ),
    )

    assert first.policy == second.policy
    assert first.authorized_by["display_label"] == "Teacher A"
    assert second.authorized_by["display_label"] == "Different label"


def test_policy_version_change_uses_explicit_current_selection() -> None:
    unchanged = IntegrityOperatorAuthority.teacher_local()
    changed = IntegrityOperatorAuthority(
        policies=(policy("1"), policy("2")),
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "2"},
    )

    assert not unchanged.policy_version_changed(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1"
    )
    assert changed.policy_version_changed(TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1")


def test_adding_a_greater_version_does_not_select_it() -> None:
    authority = IntegrityOperatorAuthority(
        policies=(policy("1"), policy("9"), policy("10")),
        current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "9"},
    )

    assert authority.resolve_current_policy(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID
    ).policy_version == "9"
    assert not authority.policy_version_changed(
        TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "9"
    )


@pytest.mark.parametrize(
    "authority",
    [
        IntegrityOperatorAuthority(policies=(policy("1"),)),
        IntegrityOperatorAuthority(
            policies=(policy("1"),),
            current_policy_versions={TEACHER_LOCAL_SUPPRESSION_POLICY_ID: "2"},
        ),
    ],
)
def test_missing_or_invalid_current_selection_fails_closed(
    authority: IntegrityOperatorAuthority,
) -> None:
    with pytest.raises(WorkflowPrerequisiteError):
        authority.policy_version_changed(TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "1")


def test_policy_version_change_unknown_authority_fails_closed() -> None:
    authority = IntegrityOperatorAuthority.teacher_local()
    with pytest.raises(WorkflowPrerequisiteError):
        authority.policy_version_changed("unknown.policy", "1")
    with pytest.raises(WorkflowPrerequisiteError):
        authority.policy_version_changed(
            TEACHER_LOCAL_SUPPRESSION_POLICY_ID, "unknown"
        )


@pytest.mark.parametrize("category", sorted(ACKNOWLEDGEMENT_CATEGORIES))
def test_local_operator_may_acknowledge_each_published_category(category: str) -> None:
    IntegrityOperatorAuthority.teacher_local().validate_acknowledgement_actor(
        {"type": "local_operator", "display_label": "Local teacher"},
        category,
    )


def test_unknown_acknowledgement_category_fails_closed() -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="category"):
        IntegrityOperatorAuthority.teacher_local().validate_acknowledgement_actor(
            {"type": "local_operator", "display_label": "Local teacher"},
            "resolved",
        )


def test_unregistered_acknowledgement_system_process_fails_closed() -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="not registered"):
        IntegrityOperatorAuthority.teacher_local().validate_acknowledgement_actor(
            {"type": "system_process", "process_id": "portia_integrity_scan"},
            "reviewed",
        )


def test_test_registry_system_process_permission_is_exact() -> None:
    authority = IntegrityOperatorAuthority(
        acknowledgement_system_processes={"registered_scan": {"reviewed"}}
    )
    authority.validate_acknowledgement_actor(
        {"type": "system_process", "process_id": "registered_scan"}, "reviewed"
    )
    with pytest.raises(WorkflowPrerequisiteError):
        authority.validate_acknowledgement_actor(
            {"type": "system_process", "process_id": "registered_scan"},
            "known_limitation",
        )
    with pytest.raises(WorkflowPrerequisiteError):
        authority.validate_acknowledgement_actor(
            {"type": "system_process", "process_id": "near_miss"}, "reviewed"
        )

