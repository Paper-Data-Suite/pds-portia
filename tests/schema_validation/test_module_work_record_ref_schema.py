from __future__ import annotations

import unittest
from pathlib import Path

try:
    from .schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )


FIXTURES = (
    FIXTURE_ROOT
    / "shared"
    / "references"
    / "module_work_record_ref"
)


def application_issues(value: object) -> set[str]:
    if not isinstance(value, dict):
        return {"not_object"}
    work_ref = value.get("work_ref")
    record_ref = value.get("record_ref")
    if not isinstance(work_ref, dict) or not isinstance(record_ref, dict):
        return {"missing_nested_ref"}

    issues: set[str] = set()
    if work_ref.get("module_id") != record_ref.get("module_id"):
        issues.add("module_id_mismatch")
    return issues


class ModuleWorkRecordRefSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "module_work_record_ref",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )

    def fixture_paths(self, category: str) -> list[Path]:
        return sorted((FIXTURES / category).glob("*.json"))

    def test_contract_is_cataloged(self) -> None:
        self.assertEqual(
            schema_id_for(
                "module_work_record_ref",
                "1",
                self.catalog,
            ),
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/references/"
                "module-work-record-ref.schema.json"
            ),
        )

    def test_valid_fixtures(self) -> None:
        paths = self.fixture_paths("valid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                self.assertFalse(application_issues(value))

    def test_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                errors = list(
                    self.validator.iter_errors(load_json(path))
                )
                self.assertTrue(
                    errors,
                    f"{path.name} unexpectedly passed structural validation",
                )

    def test_application_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("application_invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "Application-invalid fixture must remain structurally valid:\n"
                    + "\n".join(error.message for error in errors),
                )
                self.assertEqual(
                    application_issues(value),
                    {"module_id_mismatch"},
                )

    def test_top_level_and_nested_values_are_closed(self) -> None:
        schema_id = schema_id_for(
            "module_work_record_ref",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(
            set(schema["required"]),
            {"work_ref", "record_ref"},
        )
        self.assertEqual(
            set(schema["properties"]),
            {"work_ref", "record_ref"},
        )
        self.assertFalse(schema["additionalProperties"])

        work_ref = schema["$defs"]["moduleWorkRef"]
        self.assertEqual(
            set(work_ref["required"]),
            {"module_id", "class_id", "work_id"},
        )
        self.assertFalse(work_ref["additionalProperties"])

        record_ref = schema["$defs"]["moduleRecordRef"]
        self.assertEqual(
            set(record_ref["required"]),
            {
                "module_id",
                "record_kind",
                "record_id",
                "contract_version",
            },
        )
        self.assertFalse(record_ref["additionalProperties"])

    def test_contract_version_is_required_and_nullable(self) -> None:
        null_fixture = load_json(
            FIXTURES / "valid" / "scoreform-null-contract-version.json"
        )
        self.assertIsNone(
            null_fixture["record_ref"]["contract_version"]
        )
        self.validator.validate(null_fixture)

    def test_module_equality_is_application_validation(self) -> None:
        mismatch = load_json(
            FIXTURES / "application_invalid" / "module-id-mismatch.json"
        )
        self.validator.validate(mismatch)
        self.assertIn("module_id_mismatch", application_issues(mismatch))


if __name__ == "__main__":
    unittest.main()
