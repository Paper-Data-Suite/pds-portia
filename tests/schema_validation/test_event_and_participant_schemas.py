from __future__ import annotations

import unittest
from pathlib import Path

try:
    from .schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )


SCHEMA_CASES = {
    "event": ("event", "1"),
    "event_participant": (
        "event_participant",
        "1",
    ),
    "event_participant_role": (
        "event_participant_role",
        "1",
    ),
}


class SchemaMetaValidationTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def test_cataloged_legacy_schemas_are_available(
        self,
    ) -> None:
        for schema_name, (
            contract_name,
            version,
        ) in SCHEMA_CASES.items():
            with self.subTest(
                schema=schema_name
            ):
                validator_for(
                    contract_name,
                    version,
                    catalog=self.catalog,
                    store=self.store,
                )


class FixtureValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def validator_for(
        self,
        schema_name: str,
    ):
        contract_name, version = (
            SCHEMA_CASES[schema_name]
        )
        return validator_for(
            contract_name,
            version,
            catalog=self.catalog,
            store=self.store,
        )

    def fixture_paths(
        self,
        schema_name: str,
        expected_result: str,
    ) -> list[Path]:
        fixture_dir = (
            FIXTURE_ROOT
            / schema_name
            / expected_result
        )
        return sorted(
            fixture_dir.glob("*.json")
        )

    def assert_valid_fixture_set(
        self,
        schema_name: str,
    ) -> None:
        validator = self.validator_for(
            schema_name
        )
        paths = self.fixture_paths(
            schema_name,
            "valid",
        )
        self.assertTrue(
            paths,
            f"No valid fixtures found for "
            f"{schema_name}",
        )

        for path in paths:
            with self.subTest(
                schema=schema_name,
                fixture=path.name,
            ):
                errors = sorted(
                    validator.iter_errors(
                        load_json(path)
                    ),
                    key=lambda error: list(
                        error.absolute_path
                    ),
                )
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message
                        for error in errors
                    ),
                )

    def assert_invalid_fixture_set(
        self,
        schema_name: str,
    ) -> None:
        validator = self.validator_for(
            schema_name
        )
        paths = self.fixture_paths(
            schema_name,
            "invalid",
        )
        self.assertTrue(
            paths,
            f"No invalid fixtures found for "
            f"{schema_name}",
        )

        for path in paths:
            with self.subTest(
                schema=schema_name,
                fixture=path.name,
            ):
                errors = list(
                    validator.iter_errors(
                        load_json(path)
                    )
                )
                self.assertTrue(
                    errors,
                    f"{path.name} unexpectedly "
                    "passed validation",
                )

    def test_valid_event_fixtures(
        self,
    ) -> None:
        self.assert_valid_fixture_set(
            "event"
        )

    def test_invalid_event_fixtures(
        self,
    ) -> None:
        self.assert_invalid_fixture_set(
            "event"
        )

    def test_valid_event_participant_fixtures(
        self,
    ) -> None:
        self.assert_valid_fixture_set(
            "event_participant"
        )

    def test_invalid_event_participant_fixtures(
        self,
    ) -> None:
        self.assert_invalid_fixture_set(
            "event_participant"
        )

    def test_valid_event_participant_role_fixtures(
        self,
    ) -> None:
        self.assert_valid_fixture_set(
            "event_participant_role"
        )

    def test_invalid_event_participant_role_fixtures(
        self,
    ) -> None:
        self.assert_invalid_fixture_set(
            "event_participant_role"
        )


if __name__ == "__main__":
    unittest.main()
