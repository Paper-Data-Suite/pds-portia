from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

try:
    from .schema_support import REPO_ROOT
except ImportError:
    from schema_support import REPO_ROOT


VALIDATION_ROOT = REPO_ROOT / "docs" / "validation"
EXAMPLE_PATH = (
    REPO_ROOT
    / "docs"
    / "examples"
    / "portia-follow-up-outcome-reentry-repair-examples.md"
)
MANIFESTS = [
    ("account_v2", "account-v2"),
    ("observation_v2", "observation-v2"),
    ("follow_up", "follow-up"),
    ("outcome", "outcome"),
    ("reentry", "reentry"),
    ("repair", "repair"),
]


class Issue19FinalDocumentationTests(unittest.TestCase):
    def test_required_finalization_documents_exist(self) -> None:
        required = [
            VALIDATION_ROOT / "issue-19-application-invalid-matrix.json",
            VALIDATION_ROOT / "issue-19-acceptance-matrix.json",
            VALIDATION_ROOT
            / "issue-19-follow-up-outcome-reentry-repair-validation.md",
            VALIDATION_ROOT / "issue-19-final-repository-checkpoint.md",
            EXAMPLE_PATH,
        ]
        for path in required:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file())

    def test_application_invalid_matrix_matches_manifests_and_resolves(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT / "issue-19-application-invalid-matrix.json"
            ).read_text(encoding="utf-8")
        )

        expected_fixtures: set[str] = set()
        for _, directory in MANIFESTS:
            manifest_path = (
                REPO_ROOT
                / "tests"
                / "schema_validation"
                / "fixtures"
                / "issue-19"
                / directory
                / "manifest.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for filename in manifest["application_invalid"]:
                expected_fixtures.add(
                    str(
                        (
                            Path("tests")
                            / "schema_validation"
                            / "fixtures"
                            / "issue-19"
                            / directory
                            / "application-invalid"
                            / filename
                        ).as_posix()
                    )
                )

        self.assertEqual(len(expected_fixtures), 80)
        self.assertEqual(matrix["fixture_application_invalid_scenarios"], 80)
        self.assertEqual(matrix["programmatic_cross_record_invariants"], 26)
        self.assertEqual(matrix["total_coverage_entries"], 106)
        self.assertEqual(len(matrix["entries"]), 80)
        self.assertEqual(len(matrix["programmatic_invariants"]), 26)

        matrix_fixtures = {entry["fixture"] for entry in matrix["entries"]}
        self.assertEqual(matrix_fixtures, expected_fixtures)

        for entry in matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue((REPO_ROOT / entry["fixture"]).is_file())
                self.assertTrue((REPO_ROOT / entry["source_manifest"]).is_file())
                self.assertTrue((REPO_ROOT / entry["test"]).is_file())

        for entry in matrix["programmatic_invariants"]:
            path = entry["test"].split("::", 1)[0]
            with self.subTest(test=path):
                self.assertTrue((REPO_ROOT / path).is_file())

    def test_acceptance_matrix_mirrors_all_88_issue_criteria(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT / "issue-19-acceptance-matrix.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["criteria_count"], 88)
        self.assertEqual(len(matrix["criteria"]), 88)
        self.assertEqual(matrix["status"], "accepted")
        self.assertEqual(matrix["pass_count"], 88)
        self.assertEqual(matrix["pending_count"], 0)
        self.assertTrue(
            all(item["status"] == "pass" for item in matrix["criteria"])
        )
        self.assertEqual(
            {item["group"] for item in matrix["criteria"]},
            {
                "architecture",
                "follow_up_perspective",
                "outcome_recurrence_causality",
                "support_process_review_closure",
                "reentry",
                "repair",
                "lifecycle_infrastructure_cross_year",
                "paper_privacy_automation_core",
                "schemas_fixtures_tests_docs",
            },
        )

    def test_all_acceptance_evidence_paths_resolve(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT / "issue-19-acceptance-matrix.json"
            ).read_text(encoding="utf-8")
        )
        for item in matrix["criteria"]:
            self.assertTrue(item["evidence"])
            for raw_path in item["evidence"]:
                with self.subTest(
                    criterion=item["criterion_id"],
                    path=raw_path,
                ):
                    self.assertTrue((REPO_ROOT / raw_path).exists())

    def test_examples_cover_50_synthetic_scenarios_and_key_distinctions(self) -> None:
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        rows = [
            int(value)
            for value in re.findall(
                r"^\|\s*(\d+)\s*\|",
                text,
                flags=re.MULTILINE,
            )
        ]
        self.assertEqual(rows, list(range(1, 51)))
        self.assertGreaterEqual(text.lower().count("synthetic"), 50)
        for required in (
            "scheduled Follow-Up",
            "≠ completed Follow-Up",
            "Account / Observation",
            "≠ Outcome evaluation",
            "Reentry completed",
            "≠ clearance",
            "Repair completed",
            "≠ remorse",
            "temporal sequence / linkage",
            "≠ causation",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_readme_schema_guide_and_active_designs_are_reconciled(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_normalized = " ".join(readme.split())
        for required in (
            "### Issue #19 current implementation",
            "accepted ADR 0015",
            (
                "Account v2, Observation v2, Follow-Up v1, Outcome v1, "
                "Reentry v1, and Repair v1"
            ),
            "scheduled Follow-Up ≠ completed Follow-Up",
            "Reentry completed ≠ clearance",
            "Repair completed ≠ remorse",
            "intervention_record_set",
        ):
            with self.subTest(readme=required):
                self.assertIn(required, readme_normalized)

        schema = (REPO_ROOT / "schemas" / "README.md").read_text(
            encoding="utf-8"
        )
        for required in (
            "- Follow-Up: `fup_`",
            "- Outcome: `out_`",
            "- Reentry: `ren_`",
            "- Repair: `rpr_`",
            "## Follow-Up, Outcome, Reentry, and Repair contracts",
            "`account@2`",
            "`observation@2`",
            "Issue #19 adds no generic target or exact-reference family",
            "`repair_action@1`",
        ):
            with self.subTest(schema=required):
                self.assertIn(required, schema)

        issue19 = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-follow-up-outcome-reentry-repair-domain-models.md"
        ).read_text(encoding="utf-8")
        evidence = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-account-and-observation-domain-models.md"
        ).read_text(encoding="utf-8")
        support = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-support-process-support-intervention-implementation-fidelity-domain-models.md"
        ).read_text(encoding="utf-8")
        role = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-role-within-paper-data-suite.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "Current implementation reconciliation (Issue #19 closeout)",
            issue19,
        )
        self.assertIn(
            "Current implementation reconciliation (Issue #19: Account/Observation v2)",
            evidence,
        )
        self.assertIn(
            "Current downstream Follow-Up / Outcome / Reentry / Repair boundary (Issue #19)",
            support,
        )
        self.assertIn(
            "Current implementation reconciliation (Issue #19: downstream support documentation)",
            role,
        )

    def test_final_checkpoint_and_validation_record_exact_closeout_state(self) -> None:
        checkpoint = (
            VALIDATION_ROOT / "issue-19-final-repository-checkpoint.md"
        ).read_text(encoding="utf-8")
        validation = (
            VALIDATION_ROOT
            / "issue-19-follow-up-outcome-reentry-repair-validation.md"
        ).read_text(encoding="utf-8")

        for anchor in (
            "9958c10",
            "0d08495557721681b11d081e91c8b416a556df8a",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
            "9e5f9217ff2a935a98a12f7fc76ae2e74774159c",
        ):
            self.assertIn(anchor, checkpoint)
            self.assertIn(anchor, validation)

        for text in (checkpoint, validation):
            self.assertIn("9 commits ahead, 0 behind", text)
            self.assertIn("872 tests", text)
            self.assertIn("880 tests", text)
            self.assertIn("pass:     88", text)
            self.assertIn("pending:   0", text)

        self.assertIn("fixture application-invalid:       80", validation)
        self.assertIn("programmatic integration checks:   26", validation)
        self.assertIn("total coverage entries:           106", validation)

    def test_validation_records_boundaries_cross_year_and_synthetic_only(self) -> None:
        text = (
            VALIDATION_ROOT
            / "issue-19-follow-up-outcome-reentry-repair-validation.md"
        ).read_text(encoding="utf-8")
        for required in (
            "Support Process completed",
            "later Event / recurrence",
            "Missing derived state never",
            "`continues_from`",
            "Paper templates must not fabricate",
            "intervention_record_set",
            "does not implement a producer profile",
            "50 synthetic examples",
            "No real student, family, staff, or support data is committed.",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

        self.assertNotIn(
            "final repository reconciliation pending",
            text.lower(),
        )


if __name__ == "__main__":
    unittest.main()
