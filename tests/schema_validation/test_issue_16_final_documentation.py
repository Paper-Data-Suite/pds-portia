from __future__ import annotations

from pathlib import Path
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
    / "portia-review-classification-hypothesis-and-determination-examples.md"
)
REQUIRED_DOCS = [
    REPO_ROOT / "docs/validation/issue-16-application-invalid-matrix.json",
    REPO_ROOT / "docs/validation/issue-16-acceptance-matrix.json",
    REPO_ROOT / "docs/validation/issue-16-review-classification-hypothesis-determination-validation.md",
    REPO_ROOT / "docs/validation/issue-16-final-repository-checkpoint.md",
    EXAMPLE_PATH,
]


class Issue16FinalDocumentationTests(unittest.TestCase):
    def test_required_finalization_documents_exist(self) -> None:
        for path in REQUIRED_DOCS:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file())

    def test_application_invalid_matrix_is_complete_and_resolvable(self) -> None:
        matrix = json.loads(
            (VALIDATION_ROOT / "issue-16-application-invalid-matrix.json").read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["fixture_application_invalid_scenarios"], 92)
        self.assertEqual(matrix["programmatic_cross_record_invariants"], 9)
        self.assertEqual(matrix["total_coverage_entries"], 101)
        self.assertEqual(len(matrix["entries"]), 92)
        self.assertEqual(len(matrix["programmatic_invariants"]), 9)
        for entry in matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue((REPO_ROOT / entry["fixture"]).is_file())
                self.assertTrue((REPO_ROOT / entry["source_manifest"]).is_file())
        for entry in matrix["programmatic_invariants"]:
            test_path = entry["test"].split("::", 1)[0]
            with self.subTest(test=test_path):
                self.assertTrue((REPO_ROOT / test_path).is_file())

    def test_acceptance_matrix_has_all_issue_criteria(self) -> None:
        matrix = json.loads(
            (VALIDATION_ROOT / "issue-16-acceptance-matrix.json").read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["criteria_count"], 108)
        self.assertEqual(len(matrix["criteria"]), 108)
        self.assertTrue(all(item["status"] == "pass" for item in matrix["criteria"]))
        self.assertEqual(
            {item["group"] for item in matrix["criteria"]},
            {
                "domain_boundaries", "review", "classification", "hypothesis",
                "determination", "automation", "lifecycle_correction",
                "references_evidence", "paper_import", "shared_infrastructure",
                "schemas_tests", "documentation",
            },
        )

    def test_synthetic_examples_cover_required_twenty_eight(self) -> None:
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        rows = [int(v) for v in re.findall(r"^\|\s*(\d+)\s*\|", text, flags=re.MULTILINE)]
        self.assertEqual(rows, list(range(1, 29)))
        self.assertIn("All named people, classes, identifiers, categories, policies, and situations", text)
        self.assertIn("synthetic", text.lower())

    def test_readme_reconciles_issue16_current_architecture(self) -> None:
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "accepted ADR 0012 for Review",
            "Review v1, Classification v1, Hypothesis v1, and Determination v1",
            "→ Classification and/or Hypothesis",
            "## Accepted Review, Classification, Hypothesis, and Determination Contracts",
            "Issue #16 Validation: Review, Classification, Hypothesis, and Determination",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_schema_guide_reconciles_issue16_contracts(self) -> None:
        text = (REPO_ROOT / "schemas/README.md").read_text(encoding="utf-8")
        for required in (
            "- Review: `rvw_`",
            "- Classification: `cls_`",
            "- Hypothesis: `hyp_`",
            "- Determination: `det_`",
            "## Review, Classification, Hypothesis, and Determination contracts",
            "Issue #16 likewise does not add dedicated exact Review-",
            "Issue #16 reuses `represented_human_attribution@1`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_historical_and_active_design_reconciliation_is_explicit(self) -> None:
        adr1 = (
            REPO_ROOT
            / "docs/decisions/0001-separate-observations-interpretations-and-determinations.md"
        ).read_text(encoding="utf-8")
        role = (REPO_ROOT / "docs/design/portia-role-within-paper-data-suite.md").read_text(encoding="utf-8")
        evidence = (REPO_ROOT / "docs/design/portia-account-and-observation-domain-models.md").read_text(encoding="utf-8")
        self.assertIn("Current implementation authority (Issue #16", adr1)
        self.assertIn("accepted adr 0012", adr1.lower())
        self.assertIn("Current implementation reconciliation (Issue #16", role)
        self.assertIn("Current downstream authority (Issue #16", evidence)

    def test_final_checkpoint_and_validation_anchor_verified_state(self) -> None:
        checkpoint = (VALIDATION_ROOT / "issue-16-final-repository-checkpoint.md").read_text(encoding="utf-8")
        validation = (
            VALIDATION_ROOT / "issue-16-review-classification-hypothesis-determination-validation.md"
        ).read_text(encoding="utf-8")
        for anchor in (
            "f83c8368b7eff86d8527c01cd67cf13ac254522c",
            "35df69904cff3c696876f04e208bbe704bab3e97",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, checkpoint)
                self.assertIn(anchor, validation)
        self.assertIn("589 tests", validation)
        self.assertIn("597 tests", validation)
        self.assertIn("8 commits ahead", checkpoint)
        self.assertIn("0 behind", checkpoint)


if __name__ == "__main__":
    unittest.main()
