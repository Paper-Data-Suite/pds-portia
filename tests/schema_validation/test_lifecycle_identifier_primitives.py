from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "issue-12" / "lifecycle-primitives"
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"

SCHEMA_PATHS = [
    "schemas/v1/common/lowercase-token.schema.json",
    "schemas/v1/common/json-pointer.schema.json",
    "schemas/v1/identifiers/portia-lifecycle-transition-id.schema.json",
    "schemas/v1/identifiers/portia-lifecycle-history-correction-id.schema.json",
    "schemas/v1/identifiers/portia-amendment-id.schema.json",
    "schemas/v1/identifiers/portia-statement-of-disagreement-id.schema.json",
    "schemas/v1/identifiers/portia-dependency-id.schema.json",
    "schemas/v1/identifiers/portia-record-migration-id.schema.json",
    "schemas/v1/identifiers/portia-ownership-correction-id.schema.json",
    "schemas/v1/identifiers/portia-exceptional-removal-id.schema.json",
]

ID_PREFIXES = {
    "schemas/v1/identifiers/portia-lifecycle-transition-id.schema.json": "lct_",
    "schemas/v1/identifiers/portia-lifecycle-history-correction-id.schema.json": "lhc_",
    "schemas/v1/identifiers/portia-amendment-id.schema.json": "amd_",
    "schemas/v1/identifiers/portia-statement-of-disagreement-id.schema.json": "sod_",
    "schemas/v1/identifiers/portia-dependency-id.schema.json": "dep_",
    "schemas/v1/identifiers/portia-record-migration-id.schema.json": "mig_",
    "schemas/v1/identifiers/portia-ownership-correction-id.schema.json": "owc_",
    "schemas/v1/identifiers/portia-exceptional-removal-id.schema.json": "rmv_",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(relative_path: str) -> Draft202012Validator:
    schema = load_json(REPOSITORY_ROOT / relative_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


class LifecyclePrimitiveSchemaTests(unittest.TestCase):
    def test_all_new_schemas_are_valid_draft_2020_12(self) -> None:
        for relative_path in SCHEMA_PATHS:
            with self.subTest(schema=relative_path):
                schema = load_json(REPOSITORY_ROOT / relative_path)
                self.assertEqual(
                    schema.get("$schema"),
                    "https://json-schema.org/draft/2020-12/schema",
                )
                Draft202012Validator.check_schema(schema)

    def test_public_ids_match_repository_paths_and_are_unique(self) -> None:
        observed_ids: set[str] = set()
        for relative_path in SCHEMA_PATHS:
            with self.subTest(schema=relative_path):
                schema = load_json(REPOSITORY_ROOT / relative_path)
                expected_id = PUBLIC_SCHEMA_PREFIX + relative_path
                self.assertEqual(schema.get("$id"), expected_id)
                self.assertNotIn(expected_id, observed_ids)
                observed_ids.add(expected_id)

    def test_manifest_valid_fixtures_pass(self) -> None:
        manifest = load_json(FIXTURE_ROOT / "manifest.json")
        for fixture_name, schema_path in manifest["valid"].items():
            with self.subTest(fixture=fixture_name, schema=schema_path):
                instance = load_json(FIXTURE_ROOT / "valid" / fixture_name)
                validator_for(schema_path).validate(instance)

    def test_manifest_invalid_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_ROOT / "manifest.json")
        for fixture_name, schema_path in manifest["invalid"].items():
            with self.subTest(fixture=fixture_name, schema=schema_path):
                instance = load_json(FIXTURE_ROOT / "invalid" / fixture_name)
                with self.assertRaises(ValidationError):
                    validator_for(schema_path).validate(instance)

    def test_identifier_boundaries(self) -> None:
        for schema_path, prefix in ID_PREFIXES.items():
            validator = validator_for(schema_path)
            max_suffix_length = 128 - len(prefix)

            valid_values = [
                prefix + "0",
                prefix + "A",
                prefix + "0LeadingZero",
                prefix + "Mixed_Case-9",
                prefix + ("a" * max_suffix_length),
            ]
            invalid_values = [
                prefix,
                prefix + "_bad",
                prefix + "-bad",
                prefix + ".bad",
                prefix + "bad.period",
                prefix + "bad/slash",
                prefix + "bad space",
                prefix + ("a" * (max_suffix_length + 1)),
                "wrong_" + "a",
            ]

            for value in valid_values:
                with self.subTest(schema=schema_path, valid=value):
                    validator.validate(value)

            for value in invalid_values:
                with self.subTest(schema=schema_path, invalid=value):
                    with self.assertRaises(ValidationError):
                        validator.validate(value)

    def test_lowercase_token_boundaries(self) -> None:
        validator = validator_for("schemas/v1/common/lowercase-token.schema.json")

        for value in ["a", "workflow", "workflow_reason_2", "a" * 128]:
            with self.subTest(valid=value):
                validator.validate(value)

        for value in [
            "",
            "A",
            "1workflow",
            "_workflow",
            "workflow-reason",
            "workflow.reason",
            "a" * 129,
        ]:
            with self.subTest(invalid=value):
                with self.assertRaises(ValidationError):
                    validator.validate(value)

    def test_json_pointer_rfc_6901_syntax(self) -> None:
        validator = validator_for("schemas/v1/common/json-pointer.schema.json")

        valid_values = [
            "",
            "/",
            "//",
            "/a",
            "/a/b",
            "/a~1b",
            "/m~0n",
            "/changes/0/path",
            "/unicode/é",
        ]
        invalid_values = [
            "a",
            "changes/0",
            "~0",
            "/a~",
            "/a~2b",
            "/a~01~",
        ]

        for value in valid_values:
            with self.subTest(valid=value):
                validator.validate(value)

        for value in invalid_values:
            with self.subTest(invalid=value):
                with self.assertRaises(ValidationError):
                    validator.validate(value)


if __name__ == "__main__":
    unittest.main()
