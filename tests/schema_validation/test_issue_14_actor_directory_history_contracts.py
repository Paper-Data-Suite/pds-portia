from __future__ import annotations

from datetime import datetime
from typing import Any
import unittest

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-14"
    / "actor-directory-history"
)

FAMILIES = {
    "lifecycle-transition": (
        "actor_directory_lifecycle_transition"
    ),
    "lifecycle-history-correction": (
        "actor_directory_lifecycle_history_correction"
    ),
    "amendment": "actor_directory_amendment",
}

SCHEMA_PATHS = {
    "actor_directory_lifecycle_transition": (
        "schemas/v1/actors/"
        "actor-directory-lifecycle-transition.schema.json"
    ),
    "actor_directory_lifecycle_history_correction": (
        "schemas/v1/actors/"
        "actor-directory-lifecycle-history-correction.schema.json"
    ),
    "actor_directory_amendment": (
        "schemas/v1/actors/"
        "actor-directory-amendment.schema.json"
    ),
}

LEGAL_TRANSITIONS = {
    "proposed": {"active", "inactive", "invalidated", "superseded"},
    "active": {"inactive", "invalidated", "superseded"},
    "inactive": {"active", "invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

ACTOR_PATHS = {
    "/display/display_name",
    "/display/organization",
    "/display/title",
    "/actor_category",
}
CONTACT_PATHS = {
    "/contact/label",
    "/contact/other_label",
    "/use_preference",
    "/source",
    "/verification",
}
RELATIONSHIP_PATHS = {
    "/relationship/detail",
    "/basis/detail",
    "/review",
    "/effective_period/starts_on",
    "/effective_period/ends_on",
}


def parse_timestamp(value: str) -> datetime:
    normalized = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )
    return datetime.fromisoformat(normalized)


def target_actor_id(target: dict[str, Any]) -> str:
    kind = target["kind"]
    if kind == "actor":
        return target["actor_ref"]["actor_id"]
    if kind == "actor_contact_point":
        return target["contact_point_ref"]["actor_id"]
    if kind == "actor_student_relationship":
        return target["relationship_ref"]["actor_id"]
    return target["collision_ref"]["actor_id"]


def target_version(target: dict[str, Any]) -> str:
    kind = target["kind"]
    if kind == "actor":
        return target["actor_ref"]["contract_version"]
    if kind == "actor_contact_point":
        return target["contact_point_ref"]["contract_version"]
    if kind == "actor_student_relationship":
        return target["relationship_ref"]["contract_version"]
    return target["collision_ref"]["contract_version"]


def transition_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if target_actor_id(value["target"]) != value["actor_id"]:
        errors.append("target Actor ownership mismatch")

    if target_version(value["target"]) != "1":
        errors.append("unsupported target contract version")

    if parse_timestamp(value["effective_at"]) > parse_timestamp(
        value["recorded_at"]
    ):
        errors.append("effective_at follows recorded_at")

    if value["previous_transition_id"] == value["transition_id"]:
        errors.append("self predecessor")

    if value["previous_transition_id"] == "lct_missing":
        errors.append("missing predecessor")

    if value["transition_id"] == "lct_bad_status_link":
        errors.append("predecessor status mismatch")

    if value["new_status"] not in LEGAL_TRANSITIONS[
        value["prior_status"]
    ]:
        errors.append("illegal transition")

    code = value["reason"]["code"]
    if (
        value["prior_status"] == "proposed"
        and value["new_status"] == "active"
        and code != "review_completed"
    ):
        errors.append("reason incompatible with transition")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    if value["transition_id"] == "lct_branch":
        errors.append("selected head branches")

    return errors


def correction_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if target_actor_id(value["target"]) != value["actor_id"]:
        errors.append("target Actor ownership mismatch")

    if value["previous_correction_id"] == value["correction_id"]:
        errors.append("self correction predecessor")

    if value["previous_correction_id"] == "lhc_missing":
        errors.append("missing prior correction")

    if (
        value["selected_terminal_transition_id"]
        == "lct_missing"
    ):
        errors.append("selected transition missing")

    selected = value["selected_terminal_transition_id"]
    excluded = set(value["excluded_transition_ids"])
    replacement = set(value["replacement_transition_ids"])

    if selected is not None and selected in excluded:
        errors.append("selected terminal is excluded")

    if (
        "lct_unselected_replacement"
        in value["replacement_transition_ids"]
    ):
        errors.append("replacement is not in selected branch")

    if excluded & replacement:
        errors.append("excluded and replacement sets overlap")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    if "CONTACT_VALUE:" in value["rationale"]:
        errors.append("privacy-unsafe rationale")

    return errors


def normalized_state(value: dict[str, Any]) -> Any:
    if value["present"] is False:
        return ("absent",)
    return ("present", value["value"])


def amendment_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if target_actor_id(value["target"]) != value["actor_id"]:
        errors.append("target Actor ownership mismatch")

    kind = value["target"]["kind"]
    allowed = {
        "actor": ACTOR_PATHS,
        "actor_contact_point": CONTACT_PATHS,
        "actor_student_relationship": RELATIONSHIP_PATHS,
    }[kind]

    paths = [change["path"] for change in value["changes"]]
    if any(path not in allowed for path in paths):
        errors.append("path is not allowed for target kind")

    if len(paths) != len(set(paths)):
        errors.append("duplicate change path")

    for change in value["changes"]:
        if normalized_state(change["before"]) == normalized_state(
            change["after"]
        ):
            errors.append("before and after are equal")

        if (
            change["path"] == "/contact/other_label"
            and change["after"].get("present") is True
            and "@" in str(change["after"].get("value", ""))
        ):
            errors.append("contact value disguised as label")

    if value["prior_fingerprint"] == value["resulting_fingerprint"]:
        errors.append("fingerprints do not differ")

    if parse_timestamp(value["effective_at"]) > parse_timestamp(
        value["recorded_at"]
    ):
        errors.append("effective_at follows recorded_at")

    if value["previous_amendment_id"] == value["amendment_id"]:
        errors.append("self amendment predecessor")

    if value["previous_amendment_id"] == "amd_missing":
        errors.append("missing prior amendment")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    return errors


def application_errors(
    contract: str,
    value: dict[str, Any],
) -> list[str]:
    if contract == "actor_directory_lifecycle_transition":
        return transition_errors(value)
    if contract == (
        "actor_directory_lifecycle_history_correction"
    ):
        return correction_errors(value)
    return amendment_errors(value)


class Issue14ActorDirectoryHistoryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_manifests_have_expected_metadata(self) -> None:
        for family, contract in FAMILIES.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 14)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["valid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "valid"
                        / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertEqual(
                        application_errors(contract, value),
                        [],
                    )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "invalid"
                        / filename
                    )
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_application_invalid_fixtures_pass_schema_only(
        self,
    ) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["application_invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "application-invalid"
                        / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertTrue(
                        application_errors(contract, value)
                    )

    def test_contracts_are_cataloged_at_immutable_paths(
        self,
    ) -> None:
        for contract, path in SCHEMA_PATHS.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + path
                    ),
                )
                schema = load_json(REPO_ROOT / path)
                self.assertEqual(
                    schema["$id"],
                    entry["schema_id"],
                )

    def test_history_targets_exclude_collision_records(self) -> None:
        for contract, path in SCHEMA_PATHS.items():
            with self.subTest(contract=contract):
                schema = load_json(REPO_ROOT / path)
                target = schema["properties"]["target"]
                self.assertEqual(
                    target["allOf"][0]["$ref"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/schemas/v1/references/"
                        "exact-actor-directory-record-ref.schema.json"
                    ),
                )
                self.assertEqual(
                    target["allOf"][1]["not"]["properties"][
                        "kind"
                    ]["const"],
                    "actor_roster_student_collision",
                )

    def test_transition_predecessor_is_actor_root_local_id(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_lifecycle_transition"
            ]
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "actor_id",
                "transition_id",
                "target",
                "prior_status",
                "new_status",
                "reason",
                "previous_transition_id",
                "effective_at",
                "recorded_at",
                "recorded_by",
                "operation_ref",
            },
        )
        self.assertNotIn("class_id", schema["properties"])
        self.assertNotIn("work_id", schema["properties"])
        self.assertNotIn("creation_source", schema["properties"])
        self.assertNotIn("created_at", schema["properties"])

    def test_transition_reason_vocabulary_is_closed(self) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_lifecycle_transition"
            ]
        )
        codes = set(
            schema["$defs"]["recognizedReason"][
                "properties"
            ]["code"]["enum"]
        )
        self.assertEqual(
            codes,
            {
                "review_completed",
                "made_inactive",
                "reactivated",
                "identity_invalidated",
                "assertion_invalidated",
                "contact_obsolete",
                "relationship_ended",
                "corrected_by_successor",
                "duplicate_consolidated",
                "wrong_actor_corrected",
                "wrong_student_corrected",
                "roster_student_collision",
                "contract_migrated",
                "prohibited_payload",
                "source_disproved",
            },
        )

    def test_history_correction_selects_without_rewriting(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_lifecycle_history_correction"
            ]
        )
        self.assertIn(
            "selected_terminal_transition_id",
            schema["properties"],
        )
        self.assertIn(
            "excluded_transition_ids",
            schema["properties"],
        )
        self.assertIn(
            "replacement_transition_ids",
            schema["properties"],
        )
        for forbidden in (
            "transitions",
            "replacement_history",
            "updated_at",
            "effective_at",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_amendment_change_union_is_typed_and_closed(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS["actor_directory_amendment"]
        )
        change = schema["$defs"]["change"]
        self.assertEqual(len(change["oneOf"]), 14)
        paths = {
            branch["properties"]["path"]["const"]
            for branch in change["oneOf"]
        }
        self.assertEqual(
            paths,
            ACTOR_PATHS | CONTACT_PATHS | RELATIONSHIP_PATHS,
        )
        for branch in change["oneOf"]:
            self.assertFalse(branch["additionalProperties"])

    def test_amendment_excludes_material_and_sensitive_paths(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS["actor_directory_amendment"]
        )
        paths = {
            branch["properties"]["path"]["const"]
            for branch in schema["$defs"]["change"]["oneOf"]
        }
        for forbidden in (
            "/actor_id",
            "/contact_point_id",
            "/relationship_id",
            "/status",
            "/contact/kind",
            "/contact/address",
            "/contact/number",
            "/student_ref",
            "/relationship/type",
            "/basis/kind",
            "/creation_source",
            "/created_at",
            "/created_by",
            "/supersedes",
            "/updated_at",
            "/updated_by",
        ):
            self.assertNotIn(forbidden, paths)

    def test_amendment_binds_exact_prior_and_resulting_bytes(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS["actor_directory_amendment"]
        )
        self.assertEqual(
            schema["properties"]["prior_fingerprint"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "content-fingerprint.schema.json"
            ),
        )
        self.assertEqual(
            schema["properties"]["resulting_fingerprint"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "content-fingerprint.schema.json"
            ),
        )


if __name__ == "__main__":
    unittest.main()
