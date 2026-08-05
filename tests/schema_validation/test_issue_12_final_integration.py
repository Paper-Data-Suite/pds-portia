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


EXAMPLE_ROOT = REPO_ROOT / "docs" / "examples" / "issue-12"
EXAMPLE_MANIFEST = EXAMPLE_ROOT / "manifest.json"
MATRIX_PATH = (
    REPO_ROOT
    / "docs"
    / "validation"
    / "issue-12-application-invalid-matrix.json"
)
ISSUE_12_FIXTURE_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-12"
)

EXPECTED_EXAMPLE_CONTRACTS = {
    ("lifecycle_transition", "1"),
    ("lifecycle_history_correction", "1"),
    ("amendment", "1"),
    ("statement_of_disagreement", "1"),
    ("dependency", "1"),
    ("record_migration", "1"),
    ("ownership_correction", "1"),
    ("exceptional_removal", "1"),
    ("event_participant", "3"),
    ("event_participant_role", "3"),
    ("work_relationship", "2"),
    ("integrity_finding", "1"),
}

NEW_MARKDOWN_DOCUMENTS = (
    "docs/decisions/0008-define-lifecycle-correction-and-migration-contracts.md",
    "docs/examples/portia-lifecycle-amendment-correction-and-migration-examples.md",
    "docs/validation/issue-12-lifecycle-amendment-correction-and-migration-validation.md",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_.]*$")


class Issue12FinalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.example_manifest = load_json(EXAMPLE_MANIFEST)
        cls.matrix = load_json(MATRIX_PATH)

    def read(self, relative_path: str) -> str:
        path = REPO_ROOT / relative_path
        self.assertTrue(path.is_file(), relative_path)
        return path.read_text(encoding="utf-8")

    def test_accepted_documents_exist_and_are_linked(self) -> None:
        readme = self.read("README.md")
        schema_guide = self.read("schemas/README.md")
        design = self.read(
            "docs/design/portia-lifecycle-amendment-correction-and-migration-contracts.md"
        )
        adr = self.read(NEW_MARKDOWN_DOCUMENTS[0])
        examples = self.read(NEW_MARKDOWN_DOCUMENTS[1])
        validation = self.read(NEW_MARKDOWN_DOCUMENTS[2])

        self.assertIn("**Status:** Accepted", adr)
        self.assertIn("**Status:** Accepted — implemented", design)
        self.assertIn("ADR 0008", readme)
        self.assertIn(
            "portia-lifecycle-amendment-correction-and-migration-examples.md",
            readme,
        )
        self.assertIn("integrity-finding.schema.json", schema_guide)
        self.assertIn("application-invalid fixtures", validation)
        self.assertIn("issue-12/manifest.json", examples)

    def test_design_status_and_implementation_targets_are_current(self) -> None:
        design = self.read(
            "docs/design/portia-lifecycle-amendment-correction-and-migration-contracts.md"
        )
        self.assertNotIn("implementation pending", design.lower())
        for path in (
            "schemas/v2/event.schema.json",
            "schemas/v3/event-participant.schema.json",
            "schemas/v3/event-participant-role.schema.json",
            "schemas/v2/work-relationship.schema.json",
        ):
            with self.subTest(path=path):
                self.assertIn(path, design)

    def test_adr_records_core_distinctions_and_issue_13_boundary(self) -> None:
        adr = self.read(NEW_MARKDOWN_DOCUMENTS[0])
        for phrase in (
            "Current status and append-only history",
            "Amendment and material correction",
            "Invalidation and supersession",
            "Statements of disagreement",
            "Migration",
            "Ownership correction",
            "Exceptional removal",
            "Integrity findings",
            "Issue #13",
            "silent successor following",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, adr)

    def test_example_manifest_has_exact_contract_set(self) -> None:
        self.assertEqual(self.example_manifest["manifest_version"], "1")
        self.assertEqual(self.example_manifest["issue"], 12)
        actual = {
            (entry["contract"], entry["version"])
            for entry in self.example_manifest["examples"].values()
        }
        self.assertEqual(actual, EXPECTED_EXAMPLE_CONTRACTS)
        self.assertEqual(len(self.example_manifest["examples"]), 12)

    def test_public_examples_validate_against_cataloged_contracts(self) -> None:
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

    def test_example_schema_paths_match_catalog_entries(self) -> None:
        for filename, entry in self.example_manifest["examples"].items():
            with self.subTest(example=filename):
                catalog_entry = self.catalog["contracts"][entry["contract"]][
                    entry["version"]
                ]
                self.assertEqual(catalog_entry["path"], entry["schema_path"])
                self.assertTrue((REPO_ROOT / entry["schema_path"]).is_file())
                self.assertNotIn("/latest/", catalog_entry["schema_id"])
                self.assertNotIn("/current/", catalog_entry["schema_id"])

    def test_application_invalid_matrix_covers_all_manifest_fixtures_once(self) -> None:
        discovered: list[str] = []
        for manifest_path in sorted(ISSUE_12_FIXTURE_ROOT.glob("*/manifest.json")):
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
        self.assertEqual(self.matrix["issue"], 12)
        self.assertEqual(self.matrix["entry_count"], len(matrix_fixtures))
        self.assertEqual(len(matrix_fixtures), len(set(matrix_fixtures)))
        self.assertEqual(set(matrix_fixtures), set(discovered))

    def test_matrix_entries_are_structurally_valid(self) -> None:
        for entry in self.matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
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

    def test_matrix_has_expected_contract_coverage(self) -> None:
        actual = {
            (entry["contract"], entry["version"])
            for entry in self.matrix["entries"]
        }
        self.assertEqual(actual, EXPECTED_EXAMPLE_CONTRACTS)

    def test_matrix_rule_ids_and_schema_paths_are_stable(self) -> None:
        for entry in self.matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertRegex(entry["rule_id"], RULE_ID_RE)
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

    def test_readme_names_current_implementation_targets(self) -> None:
        readme = self.read("README.md")
        self.assertIn("Architecture Decision Records through ADR 0008", readme)
        for phrase in (
            "Event v2",
            "Event Participant v3",
            "Event Participant Role v3",
            "Work Relationship v2",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)
        self.assertNotIn(
            "The current Event, Event Participant, and Event Participant Role v2 contracts are defined",
            readme,
        )

    def test_schema_guide_documents_structural_application_boundary(self) -> None:
        guide = self.read("schemas/README.md")
        for phrase in (
            "Lifecycle and lifecycle-history contracts",
            "Amendment and disagreement contracts",
            "Migration, ownership correction, and exceptional removal",
            "Integrity-finding projection",
            "Application validation remains responsible",
            "Issue #13",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guide)

    def test_issue_12_public_schema_paths_match_ids(self) -> None:
        issue_contracts = EXPECTED_EXAMPLE_CONTRACTS
        for contract, version in sorted(issue_contracts):
            with self.subTest(contract=contract, version=version):
                entry = self.catalog["contracts"][contract][version]
                schema = load_json(REPO_ROOT / entry["path"])
                self.assertEqual(
                    schema["$id"],
                    "https://paper-data-suite.github.io/pds-portia/"
                    + entry["path"],
                )


if __name__ == "__main__":
    unittest.main()
