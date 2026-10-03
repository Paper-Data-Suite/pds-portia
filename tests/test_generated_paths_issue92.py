from __future__ import annotations

import pytest

from portia.storage.errors import PortiaPathError
from portia.storage.generated_paths import (
    GENERATED_PATH_TOKEN_LENGTH,
    build_generated_path_token,
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
