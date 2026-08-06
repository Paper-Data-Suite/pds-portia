from __future__ import annotations

from datetime import datetime
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
    / "issue-13"
)

FAMILIES = (
    "finding-acknowledgement",
    "finding-suppression",
    "finding-suppression-current-pointer",
)

KNOWN_FINDING_EVALUATIONS = {
    (
        "finding:derived_state:projection_stale:work_example",
        "evaluation:derived_state:projection_stale:work_example:v1",
    )
}


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )


def acknowledgement_application_errors(
    record: dict[str, object],
) -> list[str]:
    pair = (
        record["finding_key"],
        record["evaluation_key"],
    )
    if pair not in KNOWN_FINDING_EVALUATIONS:
        return [
            "acknowledgement does not target a known exact evaluation"
        ]
    return []


def suppression_application_errors(
    record: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    revision = record["suppression_revision"]
    previous = record["previous_suppression_revision"]

    if revision == 1:
        if previous is not None:
            errors.append("revision one has a predecessor")
    elif previous != revision - 1:
        errors.append("suppression predecessor is not immediate")

    resolution = record["resolution"]
    if resolution is not None:
        if resolution["prior_revision"] != previous:
            errors.append(
                "resolution prior revision disagrees with envelope"
            )
        if resolution["kind"] == "supersede":
            successor = resolution["successor_suppression"]
            if (
                successor["suppression_id"]
                == record["suppression_id"]
            ):
                errors.append(
                    "suppression series supersedes itself"
                )

    starts_at = parse_timestamp(record["starts_at"])
    for condition in record["expiry_conditions"]:
        if condition["kind"] != "fixed_timestamp":
            continue
        expires_at = parse_timestamp(condition["expires_at"])
        if expires_at <= starts_at:
            errors.append(
                "fixed expiry is not later than suppression start"
            )

    return errors


class Issue13FindingAdministrationContractTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def validator(self, contract: str):
        return validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_manifests_have_expected_contracts(self) -> None:
        expected = {
            "finding-acknowledgement": (
                "finding_acknowledgement"
            ),
            "finding-suppression": "finding_suppression",
            "finding-suppression-current-pointer": (
                "finding_suppression_current_pointer"
            ),
        }
        for family, contract in expected.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(
                    manifest["manifest_version"],
                    "1",
                )
                self.assertEqual(manifest["issue"], 13)
                self.assertEqual(
                    manifest["contract"],
                    contract,
                )
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(
                manifest["contract"]
            )
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
                    errors = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        errors,
                        "\n".join(
                            error.message for error in errors
                        ),
                    )

    def test_invalid_fixtures_fail(self) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(
                manifest["contract"]
            )
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

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        checks = {
            "finding-acknowledgement": (
                self.validator("finding_acknowledgement"),
                acknowledgement_application_errors,
            ),
            "finding-suppression": (
                self.validator("finding_suppression"),
                suppression_application_errors,
            ),
        }
        for family, (validator, checker) in checks.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
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
                    structural_errors = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural_errors,
                        "\n".join(
                            error.message
                            for error in structural_errors
                        ),
                    )
                    self.assertTrue(checker(value))

    def test_valid_values_pass_application_checks(self) -> None:
        checks = {
            "finding-acknowledgement": (
                acknowledgement_application_errors
            ),
            "finding-suppression": (
                suppression_application_errors
            ),
        }
        for family, checker in checks.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
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
                    self.assertEqual(checker(value), [])

    def test_acknowledgement_cannot_encode_resolution(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "finding-acknowledgement.schema.json"
        )
        for forbidden in (
            "resolved",
            "suppressed",
            "severity",
            "effects",
            "state",
        ):
            self.assertNotIn(
                forbidden,
                schema["properties"],
            )
        self.assertFalse(schema["additionalProperties"])

    def test_suppression_eligibility_is_structurally_narrow(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "finding-suppression.schema.json"
        )
        binding = schema["$defs"]["findingBinding"]
        self.assertEqual(
            set(binding["properties"]["severity"]["enum"]),
            {"advisory", "warning"},
        )
        self.assertEqual(
            set(
                binding["properties"]["effects"]
                ["items"]["enum"]
            ),
            {"attention", "review_required"},
        )
        self.assertEqual(
            schema["properties"]["expiry_conditions"]["minItems"],
            1,
        )

    def test_suppression_pointer_is_minimal(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / (
                "finding-suppression-current-pointer"
                ".schema.json"
            )
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "suppression_id",
                "suppression_revision",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("state", schema["properties"])
        self.assertNotIn("expires_at", schema["properties"])

    def test_public_contract_paths_match_catalog(self) -> None:
        expected = {
            "finding_acknowledgement": (
                "schemas/v1/operations/"
                "finding-acknowledgement.schema.json"
            ),
            "finding_suppression": (
                "schemas/v1/operations/"
                "finding-suppression.schema.json"
            ),
            "finding_suppression_current_pointer": (
                "schemas/v1/operations/"
                "finding-suppression-current-pointer"
                ".schema.json"
            ),
        }
        for contract, path in expected.items():
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


if __name__ == "__main__":
    unittest.main()
