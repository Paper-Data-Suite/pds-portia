from __future__ import annotations

import json
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
    / "portia-support-process-support-intervention-implementation-fidelity-examples.md"
)
MANIFESTS = [
    ("support_process", "support-process"),
    ("support_process_participant", "support-process-participant"),
    ("support_need", "support-need"),
    ("support_goal", "support-goal"),
    ("support", "support"),
    ("intervention", "intervention"),
    ("implementation", "implementation"),
    ("fidelity", "fidelity"),
]


class Issue18FinalDocumentationTests(unittest.TestCase):
    def test_required_finalization_documents_exist(self) -> None:
        required = [
            VALIDATION_ROOT / "issue-18-application-invalid-matrix.json",
            VALIDATION_ROOT / "issue-18-acceptance-matrix.json",
            VALIDATION_ROOT / "issue-18-support-process-support-intervention-implementation-fidelity-validation.md",
            VALIDATION_ROOT / "issue-18-final-repository-checkpoint.md",
            EXAMPLE_PATH,
        ]
        for path in required:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file())

    def test_application_invalid_matrix_matches_manifests_and_resolves(self) -> None:
        matrix = json.loads(
            (VALIDATION_ROOT / "issue-18-application-invalid-matrix.json").read_text(encoding="utf-8")
        )
        expected_fixture_count = 0
        for _, directory in MANIFESTS:
            manifest = json.loads(
                (
                    REPO_ROOT
                    / "tests"
                    / "schema_validation"
                    / "fixtures"
                    / "issue-18"
                    / directory
                    / "manifest.json"
                ).read_text(encoding="utf-8")
            )
            expected_fixture_count += len(manifest["application_invalid"])

        self.assertEqual(expected_fixture_count, 122)
        self.assertEqual(matrix["fixture_application_invalid_scenarios"], 122)
        self.assertEqual(matrix["programmatic_cross_record_invariants"], 13)
        self.assertEqual(matrix["total_coverage_entries"], 135)
        self.assertEqual(len(matrix["entries"]), 122)
        self.assertEqual(len(matrix["programmatic_invariants"]), 13)

        for entry in matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue((REPO_ROOT / entry["fixture"]).is_file())
                self.assertTrue((REPO_ROOT / entry["source_manifest"]).is_file())
        for entry in matrix["programmatic_invariants"]:
            path = entry["test"].split("::", 1)[0]
            with self.subTest(test=path):
                self.assertTrue((REPO_ROOT / path).is_file())

    def test_acceptance_matrix_mirrors_all_128_issue_criteria(self) -> None:
        matrix = json.loads(
            (VALIDATION_ROOT / "issue-18-acceptance-matrix.json").read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["criteria_count"], 128)
        self.assertEqual(len(matrix["criteria"]), 128)
        self.assertEqual(matrix["status"], "accepted")
        self.assertEqual(matrix["pass_count"], 128)
        self.assertEqual(matrix["pending_count"], 0)
        self.assertTrue(all(item["status"] == "pass" for item in matrix["criteria"]))
        self.assertEqual(
            {item["group"] for item in matrix["criteria"]},
            {
                "architecture",
                "support_process",
                "needs_goals",
                "support_intervention_planning",
                "implementation",
                "adaptation_correction",
                "fidelity",
                "cross_event_fba",
                "communication_integration",
                "lifecycle_cross_year_shared",
                "paper_privacy_automation_core",
                "schemas_tests_docs",
            },
        )

    def test_all_acceptance_evidence_paths_resolve(self) -> None:
        matrix = json.loads(
            (VALIDATION_ROOT / "issue-18-acceptance-matrix.json").read_text(encoding="utf-8")
        )
        for item in matrix["criteria"]:
            self.assertTrue(item["evidence"])
            for raw_path in item["evidence"]:
                with self.subTest(criterion=item["criterion_id"], path=raw_path):
                    self.assertTrue((REPO_ROOT / raw_path).exists())

    def test_examples_cover_50_synthetic_scenarios(self) -> None:
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        rows = [
            int(value)
            for value in re.findall(r"^\|\s*(\d+)\s*\|", text, flags=re.MULTILINE)
        ]
        self.assertEqual(rows, list(range(1, 51)))
        self.assertGreaterEqual(text.lower().count("synthetic"), 50)
        self.assertIn("planned Support / Intervention", text)
        self.assertIn("≠ actual Implementation", text)
        self.assertIn("≠ Fidelity", text)
        self.assertIn("≠ Outcome", text)

    def test_readme_schema_guide_and_active_designs_are_reconciled(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_normalized = " ".join(readme.split())
        for required in (
            "### Issue #18 current implementation",
            "accepted ADR 0014 for Support Process",
            "Support Process v1, Support Process Participant v1",
            "planned activity ≠ actual Implementation",
            "Communication is not Implementation",
            "intervention_record_set",
        ):
            with self.subTest(readme=required):
                self.assertIn(required, readme_normalized)

        schema = (REPO_ROOT / "schemas" / "README.md").read_text(encoding="utf-8")
        for required in (
            "- Support Process Participant: `spp_`",
            "- Support Need: `spn_`",
            "- Support Goal: `spg_`",
            "- Support: `spt_`",
            "- Intervention: `int_`",
            "- Implementation: `imp_`",
            "- Fidelity: `fid_`",
            "## Support Process, Support, Intervention, Implementation, and Fidelity contracts",
            "planned_schedule@1",
            "Issue #18 adds no dedicated exact-reference family",
            "Support Process-owned Communication",
        ):
            with self.subTest(schema=required):
                self.assertIn(required, schema)

        role = (
            REPO_ROOT / "docs" / "design" / "portia-role-within-paper-data-suite.md"
        ).read_text(encoding="utf-8")
        response = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-response-and-communication-domain-models.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Current implementation reconciliation (Issue #18: Support Process layer)",
            role,
        )
        self.assertIn("Current downstream Support Process boundary (Issue #18)", response)

    def test_final_checkpoint_and_validation_record_exact_closeout_state(self) -> None:
        checkpoint = (
            VALIDATION_ROOT / "issue-18-final-repository-checkpoint.md"
        ).read_text(encoding="utf-8")
        validation = (
            VALIDATION_ROOT
            / "issue-18-support-process-support-intervention-implementation-fidelity-validation.md"
        ).read_text(encoding="utf-8")
        for anchor in (
            "4d23d30e1a1e7a86733cd9754b436e7da96d4b1c",
            "5898ad79a7d405dc1e23b94753a0eeba793c8e72",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
        ):
            self.assertIn(anchor, checkpoint)
            self.assertIn(anchor, validation)
        self.assertIn("9 commits ahead", checkpoint)
        self.assertIn("0 behind", checkpoint)
        self.assertIn("754 tests", checkpoint)
        self.assertIn("762 tests", checkpoint)
        self.assertIn("754 tests", validation)
        self.assertIn("762 tests", validation)
        self.assertIn("pass:    128", validation)
        self.assertIn("pending:   0", validation)

    def test_validation_records_boundaries_and_synthetic_data_only(self) -> None:
        text = (
            VALIDATION_ROOT
            / "issue-18-support-process-support-intervention-implementation-fidelity-validation.md"
        ).read_text(encoding="utf-8")
        for required in (
            "planned Support / Intervention",
            "Fidelity / implementation quality",
            "Issue #19 remains authoritative",
            "Paper preallocation cannot fabricate",
            "intervention_record_set",
            "No real student, family, staff, or support data is committed.",
            "50 synthetic examples",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn("final repository reconciliation pending", text.lower())


if __name__ == "__main__":
    unittest.main()
