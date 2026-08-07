from __future__ import annotations

from pathlib import Path
from typing import Any
import json
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


EXAMPLE_ROOT = REPO_ROOT / "docs" / "examples" / "issue-14"
EXAMPLE_MANIFEST = EXAMPLE_ROOT / "manifest.json"
VALIDATION_ROOT = REPO_ROOT / "docs" / "validation"
APPLICATION_MATRIX = (
    VALIDATION_ROOT / "issue-14-application-invalid-matrix.json"
)
ACCEPTANCE_MATRIX = (
    VALIDATION_ROOT / "issue-14-acceptance-matrix.json"
)
FIXTURE_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-14"
)

ISSUE_14_PUBLIC_CONTRACTS = {
    ("portia_actor_contact_point_id", "1"),
    ("portia_actor_student_relationship_id", "1"),
    ("portia_actor_roster_student_collision_id", "1"),
    ("exact_actor_ref", "1"),
    ("exact_actor_contact_point_ref", "1"),
    ("exact_actor_student_relationship_ref", "1"),
    ("exact_actor_roster_student_collision_ref", "1"),
    ("exact_actor_directory_record_ref", "1"),
    ("actor_target", "1"),
    ("actor", "1"),
    ("actor_contact_point", "1"),
    ("actor_student_relationship", "1"),
    ("actor_roster_student_collision", "1"),
    ("actor_directory_lifecycle_transition", "1"),
    ("actor_directory_lifecycle_history_correction", "1"),
    ("actor_directory_amendment", "1"),
    ("actor_directory_record_migration", "1"),
    ("actor_directory_exceptional_removal", "1"),
    ("integrity_finding", "2"),
    ("operation_journal", "2"),
    ("operation_lock", "2"),
    ("quarantine_record", "2"),
}

EXPECTED_EXAMPLES = {
    "actor-active.json": ("actor", "1"),
    "actor-duplicate-consolidation.json": ("actor", "1"),
    "actor-conflated-split.json": ("actor", "1"),
    "actor-contact-point.json": ("actor_contact_point", "1"),
    "actor-student-relationship.json": (
        "actor_student_relationship",
        "1",
    ),
    "actor-roster-student-collision.json": (
        "actor_roster_student_collision",
        "1",
    ),
    "actor-directory-lifecycle-transition.json": (
        "actor_directory_lifecycle_transition",
        "1",
    ),
    "actor-directory-lifecycle-history-correction.json": (
        "actor_directory_lifecycle_history_correction",
        "1",
    ),
    "actor-directory-amendment.json": (
        "actor_directory_amendment",
        "1",
    ),
    "actor-directory-record-migration.json": (
        "actor_directory_record_migration",
        "1",
    ),
    "actor-directory-exceptional-removal.json": (
        "actor_directory_exceptional_removal",
        "1",
    ),
    "integrity-finding-v2.json": ("integrity_finding", "2"),
    "operation-journal-v2.json": ("operation_journal", "2"),
    "operation-lock-v2.json": ("operation_lock", "2"),
    "quarantine-record-v2.json": ("quarantine_record", "2"),
    "source-snapshot.json": ("source_snapshot", "1"),
    "derived-index-metadata.json": (
        "derived_index_metadata",
        "1",
    ),
    "derived-current-pointer.json": (
        "derived_current_pointer",
        "1",
    ),
}

MARKDOWN_DOCUMENTS = (
    "README.md",
    "schemas/README.md",
    (
        "docs/design/"
        "portia-actor-directory-domain-model-and-lifecycle.md"
    ),
    "docs/examples/portia-actor-directory-examples.md",
    "docs/validation/issue-14-actor-directory-validation.md",
)

MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RULE_ID_RE = re.compile(r"^[a-z][a-z0-9_.]*$")


class Issue14FinalIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.example_manifest = load_json(EXAMPLE_MANIFEST)
        cls.application_matrix = load_json(APPLICATION_MATRIX)
        cls.acceptance_matrix = load_json(ACCEPTANCE_MATRIX)

    def read(self, relative_path: str) -> str:
        path = REPO_ROOT / relative_path
        self.assertTrue(path.is_file(), relative_path)
        return path.read_text(encoding="utf-8")

    def test_readme_and_schema_guide_are_reconciled(self) -> None:
        readme = self.read("README.md")
        guide = self.read("schemas/README.md")

        for phrase in (
            "Architecture Decision Records through ADR 0009",
            "ADR 0010",
            "Accepted Actor Directory Contracts",
            "Actor Directory version-1 record family",
            "Issue #14 Validation",
            "Portia Actor Directory Examples",
        ):
            with self.subTest(document="README.md", phrase=phrase):
                self.assertIn(phrase, readme)

        self.assertIn(
            "portia/actors/<actor_id>/actor.json",
            readme,
        )
        self.assertNotIn(
            "defining the Actor Directory schema and Actor lifecycle",
            readme,
        )

        for phrase in (
            "Actor Contact Point: `acp_`",
            "Actor-to-Student Relationship: `asrel_`",
            "Actor–Roster Student Collision: `arsc_`",
            "Actor Directory contracts",
            "Actor-aware operational version 2",
        ):
            with self.subTest(document="schemas/README.md", phrase=phrase):
                self.assertIn(phrase, guide)

    def test_design_is_final_and_links_validation_record(self) -> None:
        design = self.read(
            "docs/design/"
            "portia-actor-directory-domain-model-and-lifecycle.md"
        )
        self.assertIn(
            "**Status:** Accepted — implemented and validated",
            design,
        )
        self.assertIn("Final implementation record", design)
        self.assertIn(
            "issue-14-actor-directory-validation.md",
            design,
        )
        for stale in (
            "implementation pending",
            "The next slice should implement",
            "Immediate next slice",
            "contract belong to the next slice",
        ):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, design)

    def test_issue_14_public_contract_inventory_is_cataloged(
        self,
    ) -> None:
        actual = {
            (contract, version)
            for contract, version in ISSUE_14_PUBLIC_CONTRACTS
            if contract in self.catalog["contracts"]
            and version in self.catalog["contracts"][contract]
        }
        self.assertEqual(actual, ISSUE_14_PUBLIC_CONTRACTS)
        self.assertEqual(len(ISSUE_14_PUBLIC_CONTRACTS), 22)

    def test_issue_14_schema_paths_match_ids(self) -> None:
        for contract, version in sorted(ISSUE_14_PUBLIC_CONTRACTS):
            with self.subTest(contract=contract, version=version):
                entry = self.catalog["contracts"][contract][version]
                schema = load_json(REPO_ROOT / entry["path"])
                self.assertEqual(
                    schema["$id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + entry["path"]
                    ),
                )
                self.assertNotIn("/latest/", schema["$id"])
                self.assertNotIn("/current/", schema["$id"])

    def test_published_version_1_operational_contracts_remain(
        self,
    ) -> None:
        expected = {
            "integrity_finding": (
                "schemas/v1/projections/"
                "integrity-finding.schema.json"
            ),
            "operation_journal": (
                "schemas/v1/operations/"
                "operation-journal.schema.json"
            ),
            "operation_lock": (
                "schemas/v1/operations/"
                "operation-lock.schema.json"
            ),
            "quarantine_record": (
                "schemas/v1/operations/"
                "quarantine-record.schema.json"
            ),
        }
        for contract, path in expected.items():
            with self.subTest(contract=contract):
                self.assertEqual(
                    self.catalog["contracts"][contract]["1"]["path"],
                    path,
                )
                self.assertIn(
                    "2",
                    self.catalog["contracts"][contract],
                )

    def test_example_manifest_has_expected_inventory(self) -> None:
        self.assertEqual(
            self.example_manifest["manifest_version"],
            "1",
        )
        self.assertEqual(self.example_manifest["issue"], 14)
        self.assertEqual(
            set(self.example_manifest["examples"]),
            set(EXPECTED_EXAMPLES),
        )
        self.assertEqual(
            len(self.example_manifest["examples"]),
            18,
        )

        actual = {
            filename: (
                entry["contract"],
                entry["version"],
            )
            for filename, entry
            in self.example_manifest["examples"].items()
        }
        self.assertEqual(actual, EXPECTED_EXAMPLES)

    def test_public_examples_validate_and_match_sources(self) -> None:
        for filename, entry in self.example_manifest[
            "examples"
        ].items():
            with self.subTest(example=filename):
                example_path = EXAMPLE_ROOT / filename
                source_path = REPO_ROOT / entry["source_fixture"]
                self.assertTrue(example_path.is_file(), filename)
                self.assertTrue(
                    source_path.is_file(),
                    entry["source_fixture"],
                )

                example = load_json(example_path)
                self.assertEqual(example, load_json(source_path))

                validator = validator_for(
                    entry["contract"],
                    entry["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(example))
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message for error in errors
                    ),
                )

                catalog_entry = self.catalog["contracts"][
                    entry["contract"]
                ][entry["version"]]
                self.assertEqual(
                    entry["schema_path"],
                    catalog_entry["path"],
                )

    def discovered_application_invalid(self) -> list[str]:
        discovered: list[str] = []
        for manifest_path in sorted(
            FIXTURE_ROOT.rglob("manifest.json")
        ):
            manifest = load_json(manifest_path)
            for filename in manifest.get(
                "application_invalid",
                {},
            ):
                discovered.append(
                    (
                        manifest_path.parent
                        / "application-invalid"
                        / filename
                    ).relative_to(REPO_ROOT).as_posix()
                )
        return discovered

    def test_application_invalid_matrix_is_complete(self) -> None:
        discovered = self.discovered_application_invalid()
        entries = self.application_matrix["entries"]
        matrix_fixtures = [
            entry["fixture"]
            for entry in entries
        ]

        self.assertEqual(
            self.application_matrix["matrix_version"],
            "1",
        )
        self.assertEqual(self.application_matrix["issue"], 14)
        self.assertEqual(
            self.application_matrix["entry_count"],
            157,
        )
        self.assertEqual(len(entries), 157)
        self.assertEqual(
            len(matrix_fixtures),
            len(set(matrix_fixtures)),
        )
        self.assertEqual(
            set(matrix_fixtures),
            set(discovered),
        )

    def test_application_invalid_matrix_entries_are_valid(
        self,
    ) -> None:
        for entry in self.application_matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue(entry["structurally_valid"])
                self.assertRegex(entry["rule_id"], RULE_ID_RE)
                fixture_path = REPO_ROOT / entry["fixture"]
                self.assertTrue(
                    fixture_path.is_file(),
                    entry["fixture"],
                )

                contract = entry.get("contract")
                if contract is None:
                    self.assertIsNone(entry["public_contract"])
                    self.assertIsNone(entry["schema_path"])
                    continue

                validator = validator_for(
                    contract,
                    entry["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(
                    validator.iter_errors(load_json(fixture_path))
                )
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message for error in errors
                    ),
                )
                catalog_entry = self.catalog["contracts"][
                    contract
                ][entry["version"]]
                self.assertEqual(
                    entry["schema_path"],
                    catalog_entry["path"],
                )

    def test_matrix_rule_ids_match_fixture_manifests(
        self,
    ) -> None:
        by_fixture = {
            entry["fixture"]: entry
            for entry in self.application_matrix["entries"]
        }
        for manifest_path in sorted(
            FIXTURE_ROOT.rglob("manifest.json")
        ):
            manifest = load_json(manifest_path)
            for filename, metadata in manifest.get(
                "application_invalid",
                {},
            ).items():
                fixture = (
                    manifest_path.parent
                    / "application-invalid"
                    / filename
                ).relative_to(REPO_ROOT).as_posix()
                self.assertEqual(
                    by_fixture[fixture]["rule_id"],
                    metadata["rule_id"],
                )

    def test_acceptance_matrix_is_complete_and_grounded(
        self,
    ) -> None:
        matrix = self.acceptance_matrix
        self.assertEqual(matrix["matrix_version"], "1")
        self.assertEqual(matrix["issue"], 14)
        self.assertEqual(matrix["criterion_count"], 41)
        self.assertEqual(len(matrix["criteria"]), 41)

        ids = [entry["id"] for entry in matrix["criteria"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            ids,
            [f"AC-{index:02d}" for index in range(1, 42)],
        )

        for entry in matrix["criteria"]:
            with self.subTest(criterion=entry["id"]):
                self.assertEqual(entry["status"], "complete")
                self.assertTrue(entry["criterion"].strip())
                self.assertTrue(entry["evidence"])
                for evidence in entry["evidence"]:
                    self.assertTrue(
                        (REPO_ROOT / evidence).exists(),
                        evidence,
                    )

    def test_validation_record_matches_final_totals(self) -> None:
        validation = self.read(
            "docs/validation/"
            "issue-14-actor-directory-validation.md"
        )
        for phrase in (
            "22 independently cataloged public contract versions",
            "26 fixture manifests",
            "124 structurally and application-valid",
            "220 structurally invalid fixtures",
            "157 structurally valid application-invalid",
            "18 synthetic machine-readable examples",
            "41 completed criteria",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
            "d60966f8486bf93fb0185e3662b76d3b79ce9dcb",
            "92621e1d765583c6dcc46d5d92bb9bd199fdc2bf",
            "Production and consuming-domain handoff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, validation)

    def test_documentation_relative_links_resolve(self) -> None:
        for relative_path in MARKDOWN_DOCUMENTS:
            document_path = REPO_ROOT / relative_path
            text = self.read(relative_path)
            for target in MARKDOWN_LINK_RE.findall(text):
                if target.startswith(
                    ("http://", "https://", "mailto:", "#")
                ):
                    continue
                target_path = target.split("#", 1)[0]
                if not target_path:
                    continue
                resolved = (
                    document_path.parent / target_path
                ).resolve()
                with self.subTest(
                    document=relative_path,
                    target=target,
                ):
                    self.assertTrue(resolved.exists(), target)

    def test_actor_examples_are_synthetic(self) -> None:
        serialized = "\n".join(
            json.dumps(
                load_json(EXAMPLE_ROOT / filename),
                sort_keys=True,
            )
            for filename in self.example_manifest["examples"]
        )
        self.assertNotRegex(
            serialized,
            r"@(gmail|yahoo|outlook|hotmail)\.",
        )
        self.assertNotIn("real student", serialized.lower())
        self.assertNotIn("real family", serialized.lower())
        self.assertIn("synthetic", serialized.lower())


if __name__ == "__main__":
    unittest.main()
