from __future__ import annotations

import pytest

from portia.storage.errors import PortiaPathError
from portia.storage.generated_paths import (
    GENERATED_PATH_TOKEN_LENGTH,
    REPLACEMENT_TEMPORARY_LEAF_LENGTH,
    STAGING_CANDIDATE_LEAF_LENGTH,
    STORAGE_REVISION_LEAF_LENGTH,
    build_actor_storage_revision_leaf,
    build_derived_generation_token,
    build_derived_projection_token,
    build_generated_path_token,
    build_replacement_temporary_leaf,
    build_staging_candidate_leaf,
    build_staging_operation_token,
    build_work_storage_revision_leaf,
    validate_generated_path_token,
)


def test_generated_path_token_has_stable_domain_separated_vector() -> None:
    token = build_generated_path_token(
        "staging_candidate",
        "op_example",
        "step_example",
    )
    assert token == "pt_e5e9e37131974f9e7bf8e99751d5924d"
    assert len(token) == GENERATED_PATH_TOKEN_LENGTH == 35
    assert validate_generated_path_token(token) == token


def test_generated_path_token_is_domain_separated() -> None:
    staging = build_generated_path_token("staging_candidate", "op_a", "step_a")
    temporary = build_generated_path_token("replacement_temporary", "op_a", "step_a")
    assert staging != temporary


def test_generated_path_token_preserves_identity_part_boundaries() -> None:
    left = build_generated_path_token("path_budget_probe", "a", "bc")
    right = build_generated_path_token("path_budget_probe", "ab", "c")
    assert left != right


def test_generated_path_token_length_does_not_expand_with_identity_text() -> None:
    short = build_generated_path_token("path_budget_probe", "record_a")
    long = build_generated_path_token("path_budget_probe", "record_" + "x" * 4096)
    assert len(short) == GENERATED_PATH_TOKEN_LENGTH
    assert len(long) == GENERATED_PATH_TOKEN_LENGTH
    assert short != long


@pytest.mark.parametrize(
    "domain",
    (
        "",
        "Uppercase",
        "contains.dot",
        "contains/slash",
        "x" * 49,
    ),
)
def test_generated_path_domain_is_closed_and_bounded(domain: str) -> None:
    with pytest.raises(PortiaPathError):
        build_generated_path_token(domain, "record_a")


def test_generated_path_token_requires_identity_and_rejects_malformed_tokens() -> None:
    with pytest.raises(PortiaPathError):
        build_generated_path_token("path_budget_probe")
    with pytest.raises(PortiaPathError):
        build_generated_path_token("path_budget_probe", "")

    for value in (
        "pt_short",
        "pt_" + "G" * 32,
        "../pt_" + "0" * 32,
        "pt_" + "0" * 33,
    ):
        with pytest.raises(PortiaPathError):
            validate_generated_path_token(value)


def test_replacement_temporary_leaf_has_exact_fixed_budget() -> None:
    leaf = build_replacement_temporary_leaf("0" * 32)
    assert leaf == ".portia-tmp-pt_28b43f3c114ed5960673ce4a94bbde1a.tmp"
    assert len(leaf) == REPLACEMENT_TEMPORARY_LEAF_LENGTH == 51
    assert "/" not in leaf
    assert "\\" not in leaf


@pytest.mark.parametrize(
    "nonce",
    (
        "",
        "0" * 31,
        "0" * 33,
        "A" * 32,
        "g" * 32,
        "../" + "0" * 32,
    ),
)
def test_replacement_temporary_leaf_rejects_invalid_nonce(nonce: str) -> None:
    with pytest.raises(PortiaPathError):
        build_replacement_temporary_leaf(nonce)


def test_staging_tokens_have_stable_bounded_vectors() -> None:
    destination = (
        "classes/class_a/modules/portia/work/evt_a/"
        "records/account/acc_a.json"
    )
    operation = build_staging_operation_token("op_test")
    candidate = build_staging_candidate_leaf(
        "op_test",
        "step_test",
        destination,
    )
    assert operation == "pt_dcc99bffa04701fc8e0b752e946c9a37"
    assert candidate == "pt_6303d89e16dcca94b69851be93be9e4f.candidate"
    assert len(operation) == GENERATED_PATH_TOKEN_LENGTH == 35
    assert len(candidate) == STAGING_CANDIDATE_LEAF_LENGTH == 45


def test_staging_candidate_length_does_not_expand_with_destination() -> None:
    short = build_staging_candidate_leaf("op_test", "step_test", "a/b.json")
    long = build_staging_candidate_leaf(
        "op_test",
        "step_test",
        "deep/" + ("segment/" * 300) + "record.json",
    )
    assert len(short) == STAGING_CANDIDATE_LEAF_LENGTH
    assert len(long) == STAGING_CANDIDATE_LEAF_LENGTH
    assert short != long


def test_storage_revision_leaves_are_bounded_and_owner_domain_separated() -> None:
    digest = "0" * 64
    work = build_work_storage_revision_leaf("event", "evt_storage", digest)
    actor = build_actor_storage_revision_leaf(
        "actor_contact_point",
        "acp_example",
        digest,
    )
    assert work == "pt_2e6035b755b19fadf7f89d25f68056ea.json"
    assert actor == "pt_ff35a0d1de570f2f6c965455e15df548.json"
    assert len(work) == STORAGE_REVISION_LEAF_LENGTH == 40
    assert len(actor) == STORAGE_REVISION_LEAF_LENGTH
    assert work != actor


def test_storage_revision_leaf_does_not_expand_with_record_identity() -> None:
    digest = "f" * 64
    short = build_work_storage_revision_leaf("event", "evt_a", digest)
    long = build_work_storage_revision_leaf(
        "record_" + "x" * 4096,
        "id_" + "y" * 4096,
        digest,
    )
    assert len(short) == STORAGE_REVISION_LEAF_LENGTH
    assert len(long) == STORAGE_REVISION_LEAF_LENGTH
    assert short != long


def test_derived_tokens_have_stable_bounded_vectors() -> None:
    projection = build_derived_projection_token(
        "current_state_view",
        "work",
        "class_english10_p2",
        "evt_example",
    )
    generation = build_derived_generation_token(
        projection,
        "dgen_example",
    )
    assert projection == "pt_751b1943be160f1db511eddae43de8ef"
    assert generation == "pt_a677e8eb837245e8362aa3b29023a008"
    assert len(projection) == GENERATED_PATH_TOKEN_LENGTH
    assert len(generation) == GENERATED_PATH_TOKEN_LENGTH
