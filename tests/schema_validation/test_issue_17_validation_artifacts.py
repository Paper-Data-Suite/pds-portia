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
    / "portia-response-and-communication-examples.md"
)
REQUIRED_DOCS = [
    VALIDATION_ROOT / "issue-17-application-invalid-matrix.json",
    VALIDATION_ROOT / "issue-17-acceptance-matrix.json",
    VALIDATION_ROOT / "issue-17-response-communication-validation.md",
    EXAMPLE_PATH,
]


class Issue17ValidationArtifactTests(unittest.TestCase):
    def test_required_validation_artifacts_exist(self) -> None:
        for path in REQUIRED_DOCS:
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file())

    def test_application_invalid_matrix_is_complete_and_resolvable(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT
                / "issue-17-application-invalid-matrix.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            matrix["fixture_application_invalid_scenarios"],
            52,
        )
        self.assertEqual(
            matrix["programmatic_cross_record_invariants"],
            8,
        )
        self.assertEqual(matrix["total_coverage_entries"], 60)
        self.assertEqual(len(matrix["entries"]), 52)
        self.assertEqual(
            len(matrix["programmatic_invariants"]),
            8,
        )
        for entry in matrix["entries"]:
            with self.subTest(fixture=entry["fixture"]):
                self.assertTrue(
                    (REPO_ROOT / entry["fixture"]).is_file()
                )
                self.assertTrue(
                    (
                        REPO_ROOT
                        / entry["source_manifest"]
                    ).is_file()
                )
        for entry in matrix["programmatic_invariants"]:
            test_path = entry["test"].split("::", 1)[0]
            with self.subTest(test=test_path):
                self.assertTrue(
                    (REPO_ROOT / test_path).is_file()
                )

    def test_acceptance_matrix_is_provisional_only_for_final_closeout(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT
                / "issue-17-acceptance-matrix.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(matrix["criteria_count"], 60)
        self.assertEqual(len(matrix["criteria"]), 60)
        self.assertEqual(matrix["status"], "provisional")
        self.assertEqual(matrix["pass_count"], 57)
        self.assertEqual(matrix["pending_count"], 3)
        pending = {
            item["statement"]
            for item in matrix["criteria"]
            if item["status"] == "pending"
        }
        self.assertEqual(
            pending,
            {
                "Initial, pre-ADR, and final repository drift checks are recorded.",
                "Final validation note is complete.",
                "README/schema guide and related active documentation are reconciled.",
            },
        )
        self.assertTrue(
            all(
                item["status"] in {"pass", "pending"}
                for item in matrix["criteria"]
            )
        )

    def test_pass_acceptance_evidence_paths_resolve(self) -> None:
        matrix = json.loads(
            (
                VALIDATION_ROOT
                / "issue-17-acceptance-matrix.json"
            ).read_text(encoding="utf-8")
        )
        for item in matrix["criteria"]:
            if item["status"] != "pass":
                continue
            for raw_path in item["evidence"]:
                with self.subTest(
                    criterion=item["criterion_id"],
                    path=raw_path,
                ):
                    self.assertTrue(
                        (REPO_ROOT / raw_path).exists()
                    )

    def test_synthetic_examples_cover_required_thirty_two(self) -> None:
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
        self.assertIn("Communication records a bounded human communication act or attempt", text)
        self.assertIn("Response records an action", text)

    def test_validation_note_records_verified_precloseout_baseline(self) -> None:
        text = (
            VALIDATION_ROOT
            / "issue-17-response-communication-validation.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "0020aca5fc354df65e4699feaaa215a876315d9a",
            text,
        )
        self.assertIn("638 tests", text)
        self.assertIn("644 tests", text)
        self.assertIn(
            "final repository reconciliation pending",
            text.lower(),
        )
        self.assertIn(
            "docs/validation/issue-17-final-repository-checkpoint.md",
            text,
        )


if __name__ == "__main__":
    unittest.main()
