from __future__ import annotations

import pytest

from portia.exports import (
    TEACHER_REFERENCE_CONTRACT_INVENTORY,
    TEACHER_REFERENCE_EXPORT_POLICY,
    TEACHER_REFERENCE_EXPORT_PURPOSES,
    TEACHER_REFERENCE_GENERATION_RULE,
    TEACHER_REFERENCE_SOURCE_KINDS,
    TEACHER_REFERENCE_WORK_ROOTS,
    require_supported_teacher_reference_work_root,
    require_teacher_reference_generation_authorized,
    teacher_reference_contract_rule,
    teacher_reference_field_rule,
    teacher_reference_generation_rule_digest,
    teacher_reference_policy_descriptor,
    teacher_reference_policy_digest,
)
from portia.models import MODEL_REGISTRY
from portia.models.errors import PortiaLocalValidationError
from portia.views import STUDENT_VIEW_POLICY


def test_policy_identity_and_v02_surface_are_exact_and_deterministic() -> None:
    assert TEACHER_REFERENCE_EXPORT_PURPOSES == (
        "teacher_current",
        "participant_specific",
    )
    assert tuple(item.exact_key for item in TEACHER_REFERENCE_WORK_ROOTS) == (
        ("event", "2"),
        ("support_process", "1"),
    )
    assert TEACHER_REFERENCE_SOURCE_KINDS == ("portia_work", "portia_record")
    assert TEACHER_REFERENCE_EXPORT_POLICY.policy_id == "teacher_reference_export"
    assert TEACHER_REFERENCE_EXPORT_POLICY.policy_version == "1"
    assert len(TEACHER_REFERENCE_EXPORT_POLICY.policy_digest) == 64
    assert (
        TEACHER_REFERENCE_EXPORT_POLICY.policy_digest
        == teacher_reference_policy_digest()
    )
    descriptor = teacher_reference_policy_descriptor()
    basis = descriptor["student_view_policy_basis"]
    assert isinstance(basis, dict)
    assert basis["policy_id"] == STUDENT_VIEW_POLICY.policy_id
    assert basis["policy_version"] == STUDENT_VIEW_POLICY.policy_version
    assert basis["policy_digest"] == STUDENT_VIEW_POLICY.policy_digest


def test_contract_inventory_classifies_every_runtime_contract() -> None:
    assert frozenset(TEACHER_REFERENCE_CONTRACT_INVENTORY) == frozenset(
        MODEL_REGISTRY
    )
    assert teacher_reference_contract_rule("event", "2").surface == (
        "work_root_current"
    )
    assert teacher_reference_contract_rule("support_process", "1").surface == (
        "work_root_current"
    )
    assert teacher_reference_contract_rule("account", "2").surface == (
        "domain_current"
    )
    assert teacher_reference_contract_rule("amendment", "1").surface == (
        "correction_context"
    )
    assert teacher_reference_contract_rule(
        "statement_of_disagreement", "1"
    ).surface == "disagreement_context"


def test_legacy_identity_operational_and_export_contracts_are_never_export() -> None:
    cases = (
        ("event", "1"),
        ("event_participant", "2"),
        ("actor", "1"),
        ("actor_contact_point", "1"),
        ("operation_journal", "4"),
        ("operation_lock", "3"),
        ("quarantine_record", "2"),
        ("integrity_finding", "2"),
        ("source_snapshot", "1"),
        ("export_source_inventory", "1"),
        ("deliberate_export", "1"),
    )
    for record_kind, version in cases:
        rule = teacher_reference_contract_rule(record_kind, version)
        assert rule.surface == "never_export"
        assert rule.may_contribute is False
        assert rule.source_kind is None
        assert rule.exclusion_reason is not None


def test_unknown_contract_and_unsupported_work_root_fail_closed() -> None:
    with pytest.raises(
        PortiaLocalValidationError,
        match="unsupported teacher-reference export contract",
    ):
        teacher_reference_contract_rule("future_student_profile", "1")

    with pytest.raises(
        PortiaLocalValidationError,
        match="unsupported teacher-reference export work root",
    ):
        require_supported_teacher_reference_work_root("event", "1")

    with pytest.raises(
        PortiaLocalValidationError,
        match="unsupported teacher-reference export work root",
    ):
        require_supported_teacher_reference_work_root("account", "2")


def test_work_root_free_text_and_indirect_context_require_manual_review() -> None:
    assert teacher_reference_field_rule(
        "event", "2", "status"
    ).disposition == "included"
    assert teacher_reference_field_rule(
        "event", "2", "summary"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "event", "2", "occurrence"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "event", "2", "location"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "event", "2", "instructional_context"
    ).disposition == "withheld"

    assert teacher_reference_field_rule(
        "support_process", "1", "summary"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "support_process", "1", "initiation"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "support_process", "1", "review_on"
    ).disposition == "included"


def test_exact_embedded_participant_display_snapshot_is_the_identity_boundary() -> None:
    event_subject = teacher_reference_field_rule(
        "event_participant", "3", "subject"
    )
    assert event_subject.disposition == "included"
    assert event_subject.representation == "embedded_display_snapshot"

    support_person = teacher_reference_field_rule(
        "support_process_participant", "1", "person"
    )
    assert support_person.disposition == "included"
    assert support_person.representation == "embedded_display_snapshot"

    contexts = teacher_reference_field_rule(
        "support_process_participant", "1", "contexts"
    )
    assert contexts.disposition == "included"
    assert contexts.representation == "kind_list"


def test_issue48_field_semantics_are_reused_for_domain_content() -> None:
    assert teacher_reference_field_rule(
        "account", "2", "information_origin"
    ).disposition == "included"
    assert teacher_reference_field_rule(
        "account", "2", "content"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "account", "2", "source"
    ).disposition == "withheld"
    assert teacher_reference_field_rule(
        "observation", "2", "content"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "communication", "1", "summary"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "communication", "1", "recipients"
    ).disposition == "withheld"
    assert teacher_reference_field_rule(
        "communication", "1", "method"
    ).representation == "kind_value"


def test_correction_and_disagreement_context_remain_bounded() -> None:
    assert teacher_reference_field_rule(
        "amendment", "1", "changes"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "amendment", "1", "target"
    ).disposition == "withheld"

    assert teacher_reference_field_rule(
        "statement_of_disagreement", "1", "status"
    ).disposition == "included"
    positions = teacher_reference_field_rule(
        "statement_of_disagreement", "1", "positions"
    )
    assert positions.disposition == "included"
    assert positions.representation == "enum_list"
    assert teacher_reference_field_rule(
        "statement_of_disagreement", "1", "statement"
    ).disposition == "requires_manual_review"
    assert teacher_reference_field_rule(
        "statement_of_disagreement", "1", "source"
    ).disposition == "withheld"


def test_unlisted_field_and_never_export_contract_field_fail_closed() -> None:
    with pytest.raises(
        PortiaLocalValidationError,
        match="field is not declared by the closed teacher-reference export policy",
    ):
        teacher_reference_field_rule("event", "2", "created_at")

    with pytest.raises(
        PortiaLocalValidationError,
        match="teacher-reference export contract is never-export",
    ):
        teacher_reference_field_rule(
            "actor_contact_point", "1", "contact_value"
        )


def test_generation_rule_identity_is_deterministic_and_policy_rule_only() -> None:
    assert TEACHER_REFERENCE_GENERATION_RULE.policy_rule_id == (
        "teacher_reference_local_generation"
    )
    assert TEACHER_REFERENCE_GENERATION_RULE.policy_rule_version == "1"
    assert TEACHER_REFERENCE_GENERATION_RULE.authorization_kind == "policy_rule"
    assert TEACHER_REFERENCE_GENERATION_RULE.authorized_result == "authorized"
    assert len(TEACHER_REFERENCE_GENERATION_RULE.policy_rule_digest) == 64
    assert (
        TEACHER_REFERENCE_GENERATION_RULE.policy_rule_digest
        == teacher_reference_generation_rule_digest()
    )


def test_generation_rule_allows_only_bounded_local_teacher_reference_intent() -> None:
    rule = require_teacher_reference_generation_authorized(
        projection_purpose="teacher_current",
        work_kind="event",
        work_contract_version="2",
        operator_kind="local_operator",
        source_kinds=("portia_work", "portia_record", "portia_record"),
    )
    assert rule is TEACHER_REFERENCE_GENERATION_RULE

    participant_rule = require_teacher_reference_generation_authorized(
        projection_purpose="participant_specific",
        work_kind="support_process",
        work_contract_version="1",
        operator_kind="local_operator",
        source_kinds=("portia_work",),
    )
    assert participant_rule is TEACHER_REFERENCE_GENERATION_RULE


@pytest.mark.parametrize(
    ("kwargs", "match"),
    (
        (
            {
                "projection_purpose": "student_facing",
                "work_kind": "event",
                "work_contract_version": "2",
                "operator_kind": "local_operator",
                "source_kinds": ("portia_work",),
            },
            "unsupported teacher-reference projection purpose",
        ),
        (
            {
                "projection_purpose": "teacher_current",
                "work_kind": "event",
                "work_contract_version": "1",
                "operator_kind": "local_operator",
                "source_kinds": ("portia_work",),
            },
            "unsupported teacher-reference export work root",
        ),
        (
            {
                "projection_purpose": "teacher_current",
                "work_kind": "event",
                "work_contract_version": "2",
                "operator_kind": "system_process",
                "source_kinds": ("portia_work",),
            },
            "requires a local_operator",
        ),
        (
            {
                "projection_purpose": "teacher_current",
                "work_kind": "event",
                "work_contract_version": "2",
                "operator_kind": "local_operator",
                "source_kinds": ("portia_record",),
            },
            "must include the exact Portia work root",
        ),
        (
            {
                "projection_purpose": "teacher_current",
                "work_kind": "event",
                "work_contract_version": "2",
                "operator_kind": "local_operator",
                "source_kinds": ("portia_work", "module_record"),
            },
            "contains unsupported source kind",
        ),
        (
            {
                "projection_purpose": "teacher_current",
                "work_kind": "event",
                "work_contract_version": "2",
                "operator_kind": "local_operator",
                "source_kinds": ("portia_work",),
                "output_custody": "external_delivery",
            },
            "limited to local workspace custody",
        ),
    ),
)
def test_generation_rule_rejects_broadened_authority(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(PortiaLocalValidationError, match=match):
        require_teacher_reference_generation_authorized(**kwargs)  # type: ignore[arg-type]
