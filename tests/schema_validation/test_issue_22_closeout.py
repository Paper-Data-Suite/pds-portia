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
COVERAGE_MANIFEST_PATH = FIXTURE_ROOT / "contract-coverage.json"
SCHEMA_CATALOG_PATH = REPO_ROOT / "schemas" / "schema-catalog.json"
VALIDATION_DOC_ROOT = REPO_ROOT / "docs" / "validation"


class Issue22CloseoutTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (VALIDATION_DOC_ROOT / name).read_text(encoding="utf-8")

    def corpus(self) -> dict:
        return json.loads((FIXTURE_ROOT / "corpus.json").read_text(encoding="utf-8"))

    def coverage_manifest(self) -> dict:
        return json.loads(COVERAGE_MANIFEST_PATH.read_text(encoding="utf-8"))

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
        manifest = self.coverage_manifest()
        catalog = json.loads(SCHEMA_CATALOG_PATH.read_text(encoding="utf-8"))

        # A contract named planned_schedule is legitimate; only a coverage-state
        # table cell / manifest disposition is prohibited.
        self.assertNotRegex(coverage, r"\|\s*planned\s*\|")
        self.assertNotIn("## Planned end-to-end coverage families", coverage)
        self.assertIn("No relevant family remains `planned`.", coverage)

        self.assertEqual(manifest["source_catalog"], "schemas/schema-catalog.json")
        entries = manifest["contracts"]
        names = [entry["contract"] for entry in entries]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), set(catalog["contracts"]))

        allowed = set(manifest["allowed_dispositions"])
        self.assertNotIn("planned", allowed)
        record_families: set[str] = set()
        for entry in entries:
            contract = entry["contract"]
            versions = sorted(catalog["contracts"][contract], key=int)
            self.assertEqual(entry["catalog_versions"], versions)
            self.assertEqual(entry["current_version"], versions[-1])
            self.assertIn(entry["disposition"], allowed)
            self.assertNotEqual(entry["disposition"], "planned")
            self.assertTrue(entry["rationale"])
            if entry["record_operational_family"]:
                record_families.add(contract)
            else:
                self.assertEqual(
                    entry["disposition"],
                    "not_applicable_with_rationale",
                )

        markdown_rows = set(
            re.findall(
                r"^\| `([^`]+)` \| [^|]+ \| "
                r"(?:positive_graph|existing_focused_fixture_only) \|",
                coverage,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(markdown_rows, record_families)
        self.assertEqual(len(entries), 161)
        self.assertEqual(len(record_families), 67)

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
            "Ran 11 tests in 0.661s",
            "Ran 12 tests in 1.507s",
            "Ran 356 tests in 47.168s",
            "Ran 1451 tests in 211.912s",
        ):
            self.assertIn(value, checkpoint)
        self.assertIn("UNCHANGED", checkpoint)
        self.assertIn("MOVED", checkpoint)

    def test_acceptance_matrix_has_no_unchecked_closeout_items(self) -> None:
        acceptance = self.text("issue-22-acceptance-matrix.md")
        self.assertNotRegex(
            acceptance,
            r"^- \[ \]",
            msg="Issue #22 acceptance matrix still contains an unchecked item",
        )
        self.assertIn("## Final closeout evidence (authoritative)", acceptance)
        self.assertIn("356/356", acceptance)
        self.assertIn("1451/1451", acceptance)
        self.assertIn("issue-22-end-to-end-validation.md", acceptance)

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
        self.assertIn("356 / 356 OK", handoff)
        self.assertIn("1451 / 1451 OK", handoff)
        self.assertIn("issue-22-end-to-end-validation.md", handoff)

    def test_closeout_evidence_files_are_all_present(self) -> None:
        required = {
            "issue-22-acceptance-matrix.md",
            "issue-22-contract-coverage-matrix.md",
            "issue-22-end-to-end-validation.md",
            "issue-22-initial-repository-checkpoint.md",
            "issue-22-final-repository-checkpoint.md",
            "issue-22-graph-invalid-matrix.md",
            "issue-22-handoff-to-issue-23.md",
        }
        self.assertTrue(
            required <= {p.name for p in VALIDATION_DOC_ROOT.iterdir() if p.is_file()}
        )

        walkthrough = (
            REPO_ROOT / "docs" / "examples" / "representative-end-to-end-contract-graphs.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Issue #22 — in progress", walkthrough)
        self.assertNotIn("| P22-14 | Planned |", walkthrough)
        self.assertIn("| P22-15 | Implemented in Slice 21 |", walkthrough)

        design = (
            REPO_ROOT / "docs" / "design" / "portia-representative-synthetic-graph-corpus.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("## Planned extension", design)


if __name__ == "__main__":
    unittest.main()
