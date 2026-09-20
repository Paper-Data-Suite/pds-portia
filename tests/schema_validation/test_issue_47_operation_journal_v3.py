from __future__ import annotations

import unittest
from copy import deepcopy

from portia.models import parse_portia_record
from portia.storage.errors import PortiaCorruptionError
from portia.storage.operation_journal import validate_operation_journal_application

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
    / "issue-47"
    / "operation-journal-v3"
)


class Issue47OperationJournalV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "operation_journal", "3", catalog=cls.catalog, store=cls.store
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_catalog_and_immutable_schema_identity(self) -> None:
        entry = self.catalog["contracts"]["operation_journal"]["3"]
        self.assertEqual(
            entry["path"], "schemas/v3/operations/operation-journal.schema.json"
        )
        schema = load_json(REPO_ROOT / entry["path"])
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertEqual(schema["properties"]["schema_version"]["const"], "3")

    def test_valid_fixtures_pass_schema_and_application_validation(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                record = parse_portia_record("operation_journal", "3", value)
                validate_operation_journal_application(record)

    def test_structurally_invalid_action_result_combinations_fail(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid_but_rejected(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "application-invalid" / filename)
                self.assertFalse(list(self.validator.iter_errors(value)))
                record = parse_portia_record("operation_journal", "3", value)
                with self.assertRaises(PortiaCorruptionError):
                    validate_operation_journal_application(record)

    def test_result_branches_are_closed_and_discriminated(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas/v3/operations/operation-journal.schema.json"
        )
        absent_intended = schema["$defs"]["absentIntendedResult"]
        absent_observed = schema["$defs"]["absentObservedResult"]
        present_observed = schema["$defs"]["presentObservedResult"]
        self.assertFalse(absent_intended["additionalProperties"])
        self.assertFalse(absent_observed["additionalProperties"])
        self.assertNotIn("fingerprint", absent_observed["properties"])
        self.assertIn("fingerprint", present_observed["required"])
        self.assertEqual(absent_intended["properties"]["kind"]["const"], "absent")

    def test_unknown_action_and_result_kind_fail_closed(self) -> None:
        value = load_json(FIXTURE_ROOT / "valid" / "v3-present-write.json")
        unknown_action = deepcopy(value)
        unknown_action["write_set"][0]["action"] = "unknown_action"
        self.assertTrue(list(self.validator.iter_errors(unknown_action)))

        unknown_result = deepcopy(value)
        unknown_result["write_set"][0]["intended_result"]["kind"] = "unknown"
        self.assertTrue(list(self.validator.iter_errors(unknown_result)))


if __name__ == "__main__":
    unittest.main()
