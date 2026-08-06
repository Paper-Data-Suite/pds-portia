from __future__ import annotations

from pathlib import Path
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
    "operation-journal",
    "operation-current-pointer",
)


def application_errors(journal: dict[str, object]) -> list[str]:
    errors: list[str] = []

    revision = journal["journal_revision"]
    previous = journal["previous_journal_revision"]
    if revision == 1:
        if previous is not None:
            errors.append("revision one has a predecessor")
    elif previous != revision - 1:
        errors.append("journal predecessor is not immediate")

    write_set = journal["write_set"]
    sequences = [step["sequence"] for step in write_set]
    if sequences != list(range(1, len(write_set) + 1)):
        errors.append("write-step sequence is not contiguous")

    step_ids = [step["step_id"] for step in write_set]
    if len(step_ids) != len(set(step_ids)):
        errors.append("write-step identifiers are not unique")

    lock_set = journal["lock_set"]
    lock_sequences = [lock["sequence"] for lock in lock_set]
    if lock_sequences != list(range(1, len(lock_set) + 1)):
        errors.append("lock sequence is not contiguous")

    lock_ids = [lock["lock_id"] for lock in lock_set]
    if len(lock_ids) != len(set(lock_ids)):
        errors.append("lock identifiers are not unique")

    steps_by_id = {
        step["step_id"]: step
        for step in write_set
    }
    for artifact in journal["staged_artifacts"]:
        step = steps_by_id.get(artifact["step_id"])
        if step is None:
            errors.append("staged artifact references an unknown step")
            continue
        if (
            artifact["destination_path"]
            != step["destination_path"]
        ):
            errors.append(
                "staged artifact destination disagrees with step"
            )

    partial = journal["partial_state"]
    classified_fields = (
        "accepted_steps",
        "verified_steps",
        "durable_unverified_steps",
        "indeterminate_steps",
        "remaining_canonical_steps",
        "remaining_post_commit_steps",
    )
    classifications: dict[str, str] = {}
    for field in classified_fields:
        for step_id in partial[field]:
            if step_id not in steps_by_id:
                errors.append(
                    f"{field} references an unknown step"
                )
            prior = classifications.get(step_id)
            if prior is not None:
                errors.append(
                    f"step appears in both {prior} and {field}"
                )
            classifications[step_id] = field

    for step_id in partial["accepted_steps"]:
        step = steps_by_id.get(step_id)
        if (
            step is not None
            and step["disposition"] != "accepted"
        ):
            errors.append(
                "accepted_steps contains a nonaccepted step"
            )

    acquired_lock_ids = {
        lock["lock_id"]
        for lock in lock_set
        if lock["disposition"] == "acquired"
    }
    held_lock_ids = set(partial["held_or_possible_locks"])
    if not held_lock_ids <= set(lock_ids):
        errors.append("partial state references an unknown lock")

    if journal["state"] == "completed":
        if acquired_lock_ids:
            errors.append(
                "completed operation retains acquired locks"
            )
        if held_lock_ids:
            errors.append(
                "completed operation reports held locks"
            )

    return errors


class Issue13OperationJournalContractTests(unittest.TestCase):
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

    def test_manifests_have_expected_contracts(self) -> None:
        expected = {
            "operation-journal": "operation_journal",
            "operation-current-pointer": (
                "operation_current_pointer"
            ),
        }
        for family, contract in expected.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 13)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(manifest["contract"])
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
            validator = self.validator(manifest["contract"])
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

    def test_application_invalid_journals_are_structurally_valid(
        self,
    ) -> None:
        family = "operation-journal"
        manifest = load_json(
            FIXTURE_ROOT / family / "manifest.json"
        )
        validator = self.validator(manifest["contract"])
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
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
                self.assertTrue(application_errors(value))

    def test_valid_journals_pass_application_checks(self) -> None:
        family = "operation-journal"
        manifest = load_json(
            FIXTURE_ROOT / family / "manifest.json"
        )
        for filename in manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / family
                    / "valid"
                    / filename
                )
                self.assertEqual(
                    application_errors(value),
                    [],
                )

    def test_state_and_step_vocabularies_are_closed(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "operation-journal.schema.json"
        )
        self.assertEqual(
            set(schema["properties"]["state"]["enum"]),
            {
                "prepared",
                "staged",
                "committing",
                "committed",
                "recovering",
                "compensating",
                "quarantined",
                "completed",
                "compensated",
                "aborted",
                "failed",
            },
        )
        self.assertEqual(
            set(
                schema["$defs"]["writeStep"]
                ["properties"]["disposition"]["enum"]
            ),
            {
                "pending",
                "staged",
                "durable",
                "verified",
                "accepted",
                "compensated",
                "skipped",
                "blocked",
                "indeterminate",
            },
        )

    def test_pointer_is_minimal_and_explicit(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "operations"
            / "operation-current-pointer.schema.json"
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "operation_id",
                "journal_revision",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        for forbidden in (
            "updated_at",
            "state",
            "operation_kind",
            "intent_digest",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_public_contract_paths_match_catalog(self) -> None:
        expected = {
            "operation_journal": (
                "schemas/v1/operations/"
                "operation-journal.schema.json"
            ),
            "operation_current_pointer": (
                "schemas/v1/operations/"
                "operation-current-pointer.schema.json"
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
