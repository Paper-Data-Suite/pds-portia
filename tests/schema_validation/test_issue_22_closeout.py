from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

try:
    from .schema_support import REPO_ROOT
except ImportError:
    from schema_support import REPO_ROOT


FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"
VALIDATION_DOC_ROOT = REPO_ROOT / "docs" / "validation"


class Issue22CloseoutTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (VALIDATION_DOC_ROOT / name).read_text(encoding="utf-8")

    def corpus(self) -> dict:
        return json.loads((FIXTURE_ROOT / "corpus.json").read_text(encoding="utf-8"))

    def test_corpus_is_complete_15_positive_37_graph_invalid(self) -> None:
        corpus = self.corpus()
        positives = [s for s in corpus["scenarios"] if s["scenario_kind"] == "positive"]
        negatives = [s for s in corpus["scenarios"] if s["scenario_kind"] == "graph_invalid"]
        self.assertEqual([s["scenario_id"] for s in positives], [f"P22-{i:02d}" for i in range(1, 16)])
        self.assertEqual([s["scenario_id"] for s in negatives], [f"G22-{i:03d}" for i in range(1, 38)])
        self.assertEqual(corpus["planned_positive_scenarios"], [])
        self.assertEqual(corpus["planned_graph_invalid_scenarios"], [])

    def test_every_registered_scenario_descriptor_exists(self) -> None:
        for scenario in self.corpus()["scenarios"]:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertTrue((FIXTURE_ROOT / scenario["path"]).is_file())

    def test_graph_invalid_matrix_matches_all_primary_findings(self) -> None:
        matrix = self.text("issue-22-graph-invalid-matrix.md")
        negatives = [s for s in self.corpus()["scenarios"] if s["scenario_kind"] == "graph_invalid"]
        rows = re.findall(r"^\| (G22-\d{3}) \|.*?\| `([^`]+)` \|", matrix, flags=re.MULTILINE)
        self.assertEqual(len(rows), 37)
        self.assertEqual([sid for sid, _ in rows], [f"G22-{i:03d}" for i in range(1, 38)])
        matrix_findings = dict(rows)
        for scenario in negatives:
            descriptor = json.loads((FIXTURE_ROOT / scenario["path"]).read_text(encoding="utf-8"))
            self.assertEqual(matrix_findings[scenario["scenario_id"]], descriptor["primary_finding_id"])
            self.assertIn(descriptor["primary_finding_id"], descriptor["expected_finding_ids"])

    def test_contract_coverage_has_no_planned_disposition(self) -> None:
        coverage = self.text("issue-22-contract-coverage-matrix.md")
        # A contract named planned_schedule is legitimate; only a coverage-state table cell is prohibited.
        self.assertNotRegex(coverage, r"\|\s*planned\s*\|")
        self.assertNotIn("## Planned end-to-end coverage families", coverage)
        self.assertIn("No relevant family remains `planned`.", coverage)

    def test_required_positive_families_have_final_coverage(self) -> None:
        coverage = self.text("issue-22-contract-coverage-matrix.md")
        for fragment in (
            "| `classification` | 1 | positive_graph | P22-15 |",
            "| `hypothesis` | 1 | positive_graph | P22-15 |",
            "| `intervention` | 1 | positive_graph | P22-15 |",
            "| `operation_journal` | 2 | positive_graph | P22-14 |",
            "| `operation_lock` | 2 | positive_graph | P22-14 |",
        ):
            self.assertIn(fragment, coverage)

    def test_special_administrative_families_have_explicit_disposition(self) -> None:
        coverage = self.text("issue-22-contract-coverage-matrix.md")
        for family in (
            "amendment",
            "ownership_correction",
            "exceptional_removal",
            "integrity_finding",
            "quarantine_record",
            "actor_roster_student_collision",
        ):
            self.assertRegex(coverage, rf"\| `{re.escape(family)}` \| [^|]+ \| existing_focused_fixture_only \|")

    def test_initial_checkpoint_records_exact_pristine_baseline(self) -> None:
        checkpoint = self.text("issue-22-initial-repository-checkpoint.md")
        self.assertIn("53be03d535d5e697b3a0fcfd962fc2c308b1710c", checkpoint)
        self.assertIn("Ran 1095 tests in 177.297s", checkpoint)
        self.assertIn("authoritative pristine starting baseline", checkpoint)

    def test_final_checkpoint_records_drift_and_validation(self) -> None:
        checkpoint = self.text("issue-22-final-repository-checkpoint.md")
        for value in (
            "53be03d535d5e697b3a0fcfd962fc2c308b1710c",
            "6c507213618b68a6dd3ea096e1a898201ff029e6",
            "692768ab42ba6de7440467e9128dee8a422d8037",
            "268fe0ab6f3d74848bf71f1aa1b939adbe242452",
            "Ran 345 tests in 73.038s",
            "Ran 1440 tests in 266.728s",
        ):
            self.assertIn(value, checkpoint)
        self.assertIn("UNCHANGED", checkpoint)
        self.assertIn("MOVED", checkpoint)

    def test_acceptance_matrix_has_no_unchecked_closeout_items(self) -> None:
        acceptance = self.text("issue-22-acceptance-matrix.md")
        self.assertNotRegex(acceptance, r"^- \[ \]", msg="Issue #22 acceptance matrix still contains an unchecked item")
        self.assertIn("## Final closeout evidence (authoritative)", acceptance)

    def test_handoff_package_names_core_architecture_pressure_points(self) -> None:
        handoff = self.text("issue-22-handoff-to-issue-23.md")
        for phrase in (
            "Authority remains distributed",
            "Exact identity dominates convenience matching",
            "Evidence and judgment remain distinct",
            "Operations remain evidence, not domain truth",
            "Derived state remains rebuildable and nonauthoritative",
            "Privacy/export semantics fail closed",
            "Retention is not destruction authority",
        ):
            self.assertIn(phrase, handoff)
        self.assertIn("15 positive synthetic graphs", handoff)
        self.assertIn("37 schema-valid graph-invalid", handoff)

    def test_closeout_evidence_files_are_all_present(self) -> None:
        required = {
            "issue-22-acceptance-matrix.md",
            "issue-22-contract-coverage-matrix.md",
            "issue-22-initial-repository-checkpoint.md",
            "issue-22-final-repository-checkpoint.md",
            "issue-22-graph-invalid-matrix.md",
            "issue-22-handoff-to-issue-23.md",
        }
        self.assertTrue(required <= {p.name for p in VALIDATION_DOC_ROOT.iterdir() if p.is_file()})


if __name__ == "__main__":
    unittest.main()
