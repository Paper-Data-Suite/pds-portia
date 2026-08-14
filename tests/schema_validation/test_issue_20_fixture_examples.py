from __future__ import annotations

import json
import unittest
from pathlib import Path

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "issue_20"
MANIFEST_PATH = FIXTURE_ROOT / "manifest.json"

ISSUE_20_PUBLIC_SCHEMA_IDS = {
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/capture-batch.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/page-target.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/page-record.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/paper-interpretation.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/capture-proposal.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/capture-review.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/capture/capture-materialization.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/imports/import-batch.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/imports/import-source-record.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/imports/import-proposal.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/imports/import-review.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/imports/import-materialization.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-capture-batch-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-page-target-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-page-record-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-paper-interpretation-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-capture-proposal-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-capture-review-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-import-batch-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-import-source-record-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-import-proposal-id.schema.json",
    "https://paper-data-suite.github.io/pds-portia/schemas/v1/identifiers/portia-import-review-id.schema.json",
}


class Issue20FixtureExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = build_schema_store()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.examples = cls.manifest["examples"]

    def test_fixture_manifest_is_bounded_unique_and_large_enough(self) -> None:
        self.assertEqual(self.manifest["fixture_manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 20)
        self.assertGreaterEqual(len(self.examples), 50)
        example_ids = [example["example_id"] for example in self.examples]
        paths = [example["path"] for example in self.examples]
        self.assertEqual(len(example_ids), len(set(example_ids)))
        self.assertEqual(len(paths), len(set(paths)))

    def test_every_public_issue_20_contract_has_valid_and_invalid_fixture(self) -> None:
        coverage: dict[str, set[str]] = {}
        for example in self.examples:
            if example["contract_kind"] == "scenario":
                continue
            coverage.setdefault(example["schema_id"], set()).add(
                example["expected"]
            )
        self.assertEqual(set(coverage), ISSUE_20_PUBLIC_SCHEMA_IDS)
        for schema_id in ISSUE_20_PUBLIC_SCHEMA_IDS:
            with self.subTest(schema_id=schema_id):
                self.assertEqual(coverage[schema_id], {"valid", "invalid"})

    def test_manifest_examples_match_schema_expectations(self) -> None:
        for example in self.examples:
            with self.subTest(example_id=example["example_id"]):
                fixture_path = FIXTURE_ROOT / example["path"]
                self.assertTrue(fixture_path.is_file())
                value = json.loads(fixture_path.read_text(encoding="utf-8"))
                validator = self.store.validator_for_id(example["schema_id"])
                errors = list(validator.iter_errors(value))
                if example["expected"] == "valid":
                    self.assertFalse(
                        errors,
                        "\n".join(error.message for error in errors),
                    )
                elif example["expected"] == "invalid":
                    self.assertTrue(errors)
                else:
                    self.fail(
                        f"Unsupported fixture expectation: {example['expected']}"
                    )

    def test_fixture_files_are_manifested_exactly_once(self) -> None:
        manifested = {example["path"] for example in self.examples}
        actual = {
            path.relative_to(FIXTURE_ROOT).as_posix()
            for path in FIXTURE_ROOT.rglob("*.json")
            if path != MANIFEST_PATH
        }
        self.assertEqual(manifested, actual)


if __name__ == "__main__":
    unittest.main()
