from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parents[1]
FIXTURE_ROOT = TEST_DIR / "fixtures"

SCHEMA_CASES = {
    "event": REPO_ROOT / "schemas" / "event.schema.json",
    "event_participant": REPO_ROOT
    / "schemas"
    / "event-participant.schema.json",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class SchemaMetaValidationTests(unittest.TestCase):
    def test_schemas_are_valid_draft_2020_12(self) -> None:
        for schema_name, schema_path in SCHEMA_CASES.items():
            with self.subTest(schema=schema_name):
                Draft202012Validator.check_schema(load_json(schema_path))


class FixtureValidationTests(unittest.TestCase):
    def validator_for(self, schema_name: str) -> Draft202012Validator:
        return Draft202012Validator(
            load_json(SCHEMA_CASES[schema_name]),
            format_checker=FormatChecker(),
        )

    def fixture_paths(
        self,
        schema_name: str,
        expected_result: str,
    ) -> list[Path]:
        fixture_dir = FIXTURE_ROOT / schema_name / expected_result
        return sorted(fixture_dir.glob("*.json"))

    def assert_valid_fixture_set(self, schema_name: str) -> None:
        validator = self.validator_for(schema_name)
        paths = self.fixture_paths(schema_name, "valid")
        self.assertTrue(paths, f"No valid fixtures found for {schema_name}")

        for path in paths:
            with self.subTest(schema=schema_name, fixture=path.name):
                errors = sorted(
                    validator.iter_errors(load_json(path)),
                    key=lambda error: list(error.absolute_path),
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def assert_invalid_fixture_set(self, schema_name: str) -> None:
        validator = self.validator_for(schema_name)
        paths = self.fixture_paths(schema_name, "invalid")
        self.assertTrue(paths, f"No invalid fixtures found for {schema_name}")

        for path in paths:
            with self.subTest(schema=schema_name, fixture=path.name):
                errors = list(validator.iter_errors(load_json(path)))
                self.assertTrue(
                    errors,
                    f"{path.name} unexpectedly passed validation",
                )

    def test_valid_event_fixtures(self) -> None:
        self.assert_valid_fixture_set("event")

    def test_invalid_event_fixtures(self) -> None:
        self.assert_invalid_fixture_set("event")

    def test_valid_event_participant_fixtures(self) -> None:
        self.assert_valid_fixture_set("event_participant")

    def test_invalid_event_participant_fixtures(self) -> None:
        self.assert_invalid_fixture_set("event_participant")


if __name__ == "__main__":
    unittest.main()
