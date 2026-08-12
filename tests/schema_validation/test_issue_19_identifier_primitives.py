from __future__ import annotations

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
    / "issue-19"
    / "identifiers"
)

IDENTIFIER_SPECS = {
    "portia_follow_up_id": (
        "fup_",
        "schemas/v1/identifiers/portia-follow-up-id.schema.json",
    ),
    "portia_outcome_id": (
        "out_",
        "schemas/v1/identifiers/portia-outcome-id.schema.json",
    ),
    "portia_reentry_id": (
        "ren_",
        "schemas/v1/identifiers/portia-reentry-id.schema.json",
    ),
    "portia_repair_id": (
        "rpr_",
        "schemas/v1/identifiers/portia-repair-id.schema.json",
    ),
}


class Issue19IdentifierPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")
        cls.validators = {
            name: validator_for(
                name,
                "1",
                catalog=cls.catalog,
                store=cls.store,
            )
            for name in IDENTIFIER_SPECS
        }

    def test_manifest_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(
            set(self.manifest["contracts"]),
            set(IDENTIFIER_SPECS),
        )

    def test_catalog_entries_are_exact(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        contracts = self.catalog["contracts"]
        for name, (_prefix, path) in IDENTIFIER_SPECS.items():
            with self.subTest(contract=name):
                self.assertEqual(
                    contracts[name]["1"],
                    {
                        "schema_id": base + path,
                        "path": path,
                    },
                )
                schema = load_json(REPO_ROOT / path)
                self.assertEqual(schema["$id"], base + path)
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )

    def test_identifier_fixtures(self) -> None:
        for name, validator in self.validators.items():
            contract = self.manifest["contracts"][name]
            self.assertEqual(contract["version"], "1")
            for value in contract["valid"]:
                with self.subTest(
                    contract=name,
                    value=value,
                    expected="valid",
                ):
                    self.assertFalse(
                        list(validator.iter_errors(value))
                    )
            for value in contract["invalid"]:
                with self.subTest(
                    contract=name,
                    value=value,
                    expected="invalid",
                ):
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_identifier_length_boundaries(self) -> None:
        for name, (prefix, _path) in IDENTIFIER_SPECS.items():
            validator = self.validators[name]
            at_limit = prefix + ("a" * (128 - len(prefix)))
            too_long = prefix + ("a" * (129 - len(prefix)))
            with self.subTest(contract=name):
                self.assertEqual(len(at_limit), 128)
                self.assertFalse(
                    list(validator.iter_errors(at_limit))
                )
                self.assertTrue(
                    list(validator.iter_errors(too_long))
                )

    def test_identifier_families_do_not_cross_validate(self) -> None:
        items = list(IDENTIFIER_SPECS.items())
        for index, (name, (_prefix, _path)) in enumerate(items):
            other_name, (other_prefix, _other_path) = items[
                (index + 1) % len(items)
            ]
            with self.subTest(
                contract=name,
                wrong_family=other_name,
            ):
                self.assertTrue(
                    list(
                        self.validators[name].iter_errors(
                            other_prefix + "example"
                        )
                    )
                )

    def test_identifiers_are_opaque_and_semantically_narrow(self) -> None:
        forbidden_schema_keywords = {
            "properties",
            "required",
            "enum",
            "oneOf",
            "anyOf",
            "allOf",
        }
        expected_words = {
            "portia_follow_up_id": "no student",
            "portia_outcome_id": "no student",
            "portia_reentry_id": "no student",
            "portia_repair_id": "no student",
        }
        for name, (prefix, path) in IDENTIFIER_SPECS.items():
            schema = load_json(REPO_ROOT / path)
            with self.subTest(contract=name):
                self.assertEqual(schema["type"], "string")
                self.assertEqual(schema["minLength"], len(prefix) + 1)
                self.assertEqual(schema["maxLength"], 128)
                self.assertTrue(
                    forbidden_schema_keywords.isdisjoint(schema)
                )
                description = schema["description"].lower()
                self.assertIn(
                    expected_words[name],
                    description,
                )
                self.assertIn(
                    f"the {prefix} prefix",
                    description,
                )


if __name__ == "__main__":
    unittest.main()
