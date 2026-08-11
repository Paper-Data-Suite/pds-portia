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
    / "portia-response-and-communication-examples.md"
)


class Issue17FinalDocumentationTests(unittest.TestCase):
    def test_required_finalization_documents_exist(self) -> None:
        required = [
            VALIDATION_ROOT / "issue-17-application-invalid-matrix.json",
            VALIDATION_ROOT / "issue-17-acceptance-matrix.json",
            VALIDATION_ROOT / "issue-17-response-communication-validation.md",
            VALIDATION_ROOT / "issue-17-final-repository-checkpoint.md",
            EXAMPLE_PATH,
        ]
        for path in required:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file())

    def test_application_invalid_and_acceptance_matrices_are_final(self) -> None:
        invalid = json.loads(
            (
                VALIDATION_ROOT
                / "issue-17-application-invalid-matrix.json"
            ).read_text(encoding="utf-8")
        )
        acceptance = json.loads(
            (
                VALIDATION_ROOT
                / "issue-17-acceptance-matrix.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            (
                invalid["fixture_application_invalid_scenarios"],
                invalid["programmatic_cross_record_invariants"],
                invalid["total_coverage_entries"],
            ),
            (52, 8, 60),
        )
        self.assertEqual(acceptance["criteria_count"], 60)
        self.assertEqual(acceptance["status"], "accepted")
        self.assertEqual(acceptance["pass_count"], 60)
        self.assertEqual(acceptance["pending_count"], 0)
        self.assertTrue(
            all(
                item["status"] == "pass"
                for item in acceptance["criteria"]
            )
        )

    def test_synthetic_examples_cover_all_thirty_two(self) -> None:
        text = EXAMPLE_PATH.read_text(encoding="utf-8")
        rows = [
            int(value)
            for value in re.findall(
                r"^\|\s*(\d+)\s*\|",
                text,
                flags=re.MULTILINE,
            )
        ]
        self.assertEqual(rows, list(range(1, 33)))
        self.assertIn("synthetic", text.lower())

    def test_readme_reconciles_issue17_current_architecture(self) -> None:
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for required in (
            "accepted ADR 0013 for Response and Communication",
            "Response v1 and Communication v1",
            "→ Response and/or Communication",
            "## Accepted Response and Communication Contracts",
            "Issue #17 Validation: Response and Communication Domain Models",
            "Communication is not Account evidence",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_schema_guide_reconciles_issue17_contracts(self) -> None:
        text = (
            REPO_ROOT / "schemas" / "README.md"
        ).read_text(encoding="utf-8")
        for required in (
            "- Response: `rsp_`",
            "- Communication: `comm_`",
            "## Response and Communication contracts",
            "Issue #17 likewise does not add dedicated Response- or Communication-specific",
            "Issue #17 reuses `represented_human_attribution@1` for Response provider",
            "Communication attachments are schema-local",
            "`account_from_communication`",
        ):
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_historical_and_active_design_reconciliation_is_explicit(self) -> None:
        adr2 = (
            REPO_ROOT
            / "docs/decisions/0002-define-portia-module-boundaries.md"
        ).read_text(encoding="utf-8")
        role = (
            REPO_ROOT
            / "docs/design/portia-role-within-paper-data-suite.md"
        ).read_text(encoding="utf-8")
        evidence = (
            REPO_ROOT
            / "docs/design/portia-account-and-observation-domain-models.md"
        ).read_text(encoding="utf-8")
        judgment = (
            REPO_ROOT
            / "docs/design/portia-review-classification-hypothesis-and-determination-domain-models.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Current implementation authority (Issue #17", adr2)
        self.assertIn("family contact", adr2.lower())
        self.assertIn("Current implementation reconciliation (Issue #17", role)
        self.assertIn("Current downstream communication boundary (Issue #17", evidence)
        self.assertIn("Current downstream action/communication authority (Issue #17", judgment)

    def test_final_checkpoint_and_validation_share_exact_anchors(self) -> None:
        checkpoint = (
            VALIDATION_ROOT
            / "issue-17-final-repository-checkpoint.md"
        ).read_text(encoding="utf-8")
        validation = (
            VALIDATION_ROOT
            / "issue-17-response-communication-validation.md"
        ).read_text(encoding="utf-8")

        branch_match = re.search(
            r"pds-portia branch \(pre-closeout\):\n([0-9a-f]{40})",
            checkpoint,
        )
        self.assertIsNotNone(branch_match)
        branch_sha = branch_match.group(1)
        self.assertIn(branch_sha, validation)

        for anchor in (
            "34d8100a1775effc43737409f86ad0486c01fb34",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
        ):
            self.assertIn(anchor, checkpoint)
            self.assertIn(anchor, validation)

        self.assertIn("7 commits ahead", checkpoint)
        self.assertIn("0 behind", checkpoint)

    def test_final_validation_records_pre_and_post_closeout_test_counts(self) -> None:
        validation = (
            VALIDATION_ROOT
            / "issue-17-response-communication-validation.md"
        ).read_text(encoding="utf-8")
        self.assertIn("644 tests", validation)
        self.assertIn("652 tests", validation)
        self.assertIn("pass:    60", validation)
        self.assertIn("pending:  0", validation)
        self.assertNotIn("final repository reconciliation pending", validation.lower())


if __name__ == "__main__":
    unittest.main()
