from __future__ import annotations

from pathlib import Path
import re
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


EXAMPLE_ROOT = REPO_ROOT / "docs" / "examples" / "issue-13"
EXAMPLE_MANIFEST = EXAMPLE_ROOT / "manifest.json"
MATRIX_PATH = (
    REPO_ROOT
    / "docs"
    / "validation"
    / "issue-13-application-invalid-matrix.json"
)
FIXTURE_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-13"
)

ISSUE_13_CONTRACTS = {
    ("portia_operation_id", "1"),
    ("portia_operation_step_id", "1"),
    ("portia_lock_id", "1"),
    ("portia_quarantine_id", "1"),
    ("portia_finding_acknowledgement_id", "1"),
    ("portia_finding_suppression_id", "1"),
    ("portia_derived_generation_id", "1"),
    ("workspace_relative_path", "1"),
    ("sha256_digest", "1"),
    ("content_fingerprint", "1"),
    ("operation_ref", "1"),
    ("operation_journal_ref", "1"),
    ("quarantine_ref", "1"),
    ("derived_generation_ref", "1"),
    ("operation_journal", "1"),
    ("operation_current_pointer", "1"),
    ("operation_lock", "1"),
    ("quarantine_record", "1"),
    ("quarantine_current_pointer", "1"),
    ("finding_acknowledgement", "1"),
    ("finding_suppression", "1"),
    ("finding_suppression_current_pointer", "1"),
    ("source_snapshot", "1"),
    ("derived_index_metadata", "1"),
    ("derived_current_pointer", "1"),
}

EXPECTED_EXAMPLE_CONTRACTS = {
    ("operation_journal", "1"),
    ("operation_current_pointer", "1"),
    ("operation_lock", "1"),
    ("quarantine_record", "1"),
    ("quarantine_current_pointer", "1"),
    ("finding_acknowledgement", "1"),
    ("finding_suppression", "1"),
    ("finding_suppression_current_pointer", "1"),
    ("source_snapshot", "1"),
    ("derived_index_metadata", "1"),
    ("derived_current_pointer", "1"),
}

NEW_MARKDOWN_DOCUMENTS = (
    "docs/design/portia-coordinated-persistence-recovery-and-derived-index-contracts.md",
    "docs/decisions/0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md",
    "docs/examples/portia-coordinated-persistence-recovery-and-derived-index-examples.md",
    "docs/validation/issue-13-coordinated-persistence-recovery-and-derived-index-validation.md",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_.]*$")


class Issue13FinalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.example_manifest = load_json(EXAMPLE_MANIFEST)
        cls.matrix = load_json(MATRIX_PATH)

    def read(self, relative_path: str) -> str:
        path = REPO_ROOT / relative_path
        self.assertTrue(path.is_file(), relative_path)
        return path.read_text(encoding="utf-8")

    def test_readme_and_schema_guide_are_reconciled(self) -> None:
        readme = self.read("README.md")
        guide = self.read("schemas/README.md")
        self.assertIn("Architecture Decision Records through ADR 0009", readme)
        self.assertIn("Accepted Coordinated Persistence", readme)
        self.assertNotIn("Issue #13 remains responsible", readme)
        self.assertNotIn("Issue #13 coordinated persistence", readme)
        for phrase in (
            "Coordinated operation journals and pointers",
            "Locks and Quarantine",
            "Finding acknowledgement and suppression",
            "Deterministic source snapshots and derived generations",
            "Issue #13 defines those public operational",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_design_is_accepted_and_contains_final_drift_anchors(self) -> None:
        design = self.read(NEW_MARKDOWN_DOCUMENTS[0])
        self.assertIn("**Status:** Accepted — implemented and validated", design)
        self.assertIn("Final cross-repository checkpoint", design)
        self.assertNotIn("The next slice should begin", design)
        self.assertNotIn("Remaining issue work is", design)
        for anchor in (
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
            "44778d43b13b8c5f66b9adc24a6674692816300f",
            "840cf492b3503d5d6eba77c7ca2130cf21125d0c",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, design)

    def test_issue_13_contract_inventory_is_cataloged(self) -> None:
        actual = {
            (contract, version)
            for contract, version in ISSUE_13_CONTRACTS
            if contract in self.catalog["contracts"]
            and version in self.catalog["contracts"][contract]
        }
        self.assertEqual(actual, ISSUE_13_CONTRACTS)
        self.assertEqual(len(ISSUE_13_CONTRACTS), 25)

    def test_issue_13_schema_paths_match_ids(self) -> None:
        for contract, version in sorted(ISSUE_13_CONTRACTS):
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract][version]
                schema = load_json(REPO_ROOT / entry["path"])
                self.assertEqual(
                    schema["$id"],
                    "https://paper-data-suite.github.io/pds-portia/"
                    + entry["path"],
                )
                self.assertNotIn("/latest/", schema["$id"])
                self.assertNotIn("/current/", schema["$id"])

    def test_example_manifest_has_exact_contract_set(self) -> None:
        self.assertEqual(self.example_manifest["manifest_version"], "1")
        self.assertEqual(self.example_manifest["issue"], 13)
        actual = {
            (entry["contract"], entry["version"])
            for entry in self.example_manifest["examples"].values()
        }
        self.assertEqual(actual, EXPECTED_EXAMPLE_CONTRACTS)
        self.assertEqual(len(self.example_manifest["examples"]), 11)

    def test_public_examples_validate(self) -> None:
        for filename, entry in self.example_manifest["examples"].items():
            with self.subTest(example=filename):
                example_path = EXAMPLE_ROOT / filename
                self.assertTrue(example_path.is_file(), filename)
                validator = validator_for(
                    entry["contract"],
                    entry["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(load_json(example_path)))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                catalog_entry = self.catalog["contracts"][entry["contract"]][
                    entry["version"]
                ]
                self.assertEqual(entry["schema_path"], catalog_entry["path"])

    def test_application_invalid_matrix_covers_every_fixture_once(self) -> None:
        discovered: list[str] = []
        for manifest_path in sorted(FIXTURE_ROOT.glob("*/manifest.json")):
            manifest = load_json(manifest_path)
            for filename in manifest.get("application_invalid", {}):
                discovered.append(
                    (
                        manifest_path.parent
                        / "application-invalid"
                        / filename
                    ).relative_to(REPO_ROOT).as_posix()
                )
        matrix_fixtures = [entry["fixture"] for entry in self.matrix["entries"]]
        self.assertEqual(self.matrix["matrix_version"], "1")
        self.assertEqual(self.matrix["issue"], 13)
        self.assertEqual(self.matrix["entry_count"], 23)
        self.assertEqual(len(matrix_fixtures), len(set(matrix_fixtures)))
        self.assertEqual(set(matrix_fixtures), set(discovered))

    def test_matrix_entries_are_structurally_valid(self) -> None:
        for entry in self.matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue(entry["structurally_valid"])
                self.assertRegex(entry["rule_id"], RULE_ID_RE)
                fixture_path = REPO_ROOT / entry["fixture"]
                self.assertTrue(fixture_path.is_file(), entry["fixture"])
                validator = validator_for(
                    entry["contract"],
                    entry["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(load_json(fixture_path)))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                catalog_entry = self.catalog["contracts"][entry["contract"]][
                    entry["version"]
                ]
                self.assertEqual(entry["schema_path"], catalog_entry["path"])

    def test_new_markdown_relative_links_resolve(self) -> None:
        for relative_path in NEW_MARKDOWN_DOCUMENTS:
            document_path = REPO_ROOT / relative_path
            text = self.read(relative_path)
            for target in MARKDOWN_LINK_RE.findall(text):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target_path = target.split("#", 1)[0]
                if not target_path:
                    continue
                resolved = (document_path.parent / target_path).resolve()
                with self.subTest(document=relative_path, target=target):
                    self.assertTrue(resolved.exists(), target)

    def test_validation_record_matches_fixture_totals(self) -> None:
        validation = self.read(NEW_MARKDOWN_DOCUMENTS[3])
        for phrase in (
            "25 independently cataloged version-1 public contracts",
            "23 structurally valid fixtures",
            "44 structurally invalid fixtures",
            "23 structurally valid application-invalid fixtures",
            "No Issue #12 public schema was modified in place",
            "Production handoff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, validation)


if __name__ == "__main__":
    unittest.main()
