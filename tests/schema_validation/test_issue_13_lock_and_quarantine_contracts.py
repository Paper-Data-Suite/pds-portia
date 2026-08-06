from __future__ import annotations

import hashlib
import json
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
    "operation-lock",
    "quarantine-record",
    "quarantine-current-pointer",
)


def expected_lock_id(lock: dict[str, object]) -> str:
    payload = {
        "lock_scope": lock["lock_scope"],
        "protected_target": lock["protected_target"],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "lock_" + hashlib.sha256(encoded).hexdigest()


def lock_application_errors(
    lock: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    if lock["lock_id"] != expected_lock_id(lock):
        errors.append("lock ID does not match canonical key")

    if lock["lock_scope"] == "operation":
        target_operation = (
            lock["protected_target"]["operation_ref"]
            ["operation_id"]
        )
        owner_operation = (
            lock["owning_operation"]["operation_id"]
        )
        if target_operation != owner_operation:
            errors.append(
                "operation lock target and owner disagree"
            )
    return errors


def quarantine_application_errors(
    record: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    revision = record["quarantine_revision"]
    previous = record["previous_quarantine_revision"]

    if revision == 1:
        if previous is not None:
            errors.append("revision one has a predecessor")
    elif previous != revision - 1:
        errors.append("quarantine predecessor is not immediate")

    resolution = record["resolution"]
    if resolution is not None:
        if resolution["prior_revision"] != previous:
            errors.append(
                "resolution prior revision disagrees with envelope"
            )
        if resolution["kind"] == "supersede":
            successor = resolution["successor_quarantine"]
            if (
                successor["quarantine_id"]
                == record["quarantine_id"]
            ):
                errors.append(
                    "quarantine series supersedes itself"
                )
    return errors


class Issue13LockAndQuarantineContractTests(
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
            "operation-lock": "operation_lock",
            "quarantine-record": "quarantine_record",
            "quarantine-current-pointer": (
                "quarantine_current_pointer"
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
                            error.message
                            for error in errors
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
        validators = {
            "operation-lock": (
                self.validator("operation_lock"),
                lock_application_errors,
            ),
            "quarantine-record": (
                self.validator("quarantine_record"),
                quarantine_application_errors,
            ),
        }
        for family, (validator, checker) in validators.items():
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
            "operation-lock": lock_application_errors,
            "quarantine-record": (
                quarantine_application_errors
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

    def test_lock_has_no_expiry_or_mutable_state(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "operation-lock.schema.json"
        )
        for forbidden in (
            "expires_at",
            "released_at",
            "state",
            "heartbeat_at",
            "updated_at",
        ):
            self.assertNotIn(
                forbidden,
                schema["properties"],
            )
        self.assertFalse(schema["additionalProperties"])

    def test_quarantine_is_not_lifecycle(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "quarantine-record.schema.json"
        )
        for forbidden in (
            "status",
            "lifecycle_status",
            "removed",
            "supersedes_target",
        ):
            self.assertNotIn(
                forbidden,
                schema["properties"],
            )
        self.assertEqual(
            set(schema["properties"]["state"]["enum"]),
            {"active", "released", "superseded"},
        )

    def test_quarantine_pointer_is_minimal(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "quarantine-current-pointer.schema.json"
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "quarantine_id",
                "quarantine_revision",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("state", schema["properties"])
        self.assertNotIn("updated_at", schema["properties"])

    def test_public_contract_paths_match_catalog(self) -> None:
        expected = {
            "operation_lock": (
                "schemas/v1/operations/"
                "operation-lock.schema.json"
            ),
            "quarantine_record": (
                "schemas/v1/operations/"
                "quarantine-record.schema.json"
            ),
            "quarantine_current_pointer": (
                "schemas/v1/operations/"
                "quarantine-current-pointer.schema.json"
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
