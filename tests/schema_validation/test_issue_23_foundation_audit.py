from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validate_portia_foundation.py"
SPEC = importlib.util.spec_from_file_location("portia_foundation_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class FoundationAuditValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self._build_minimal_repo()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _copy(self, relpath: str) -> None:
        source = ROOT / relpath
        target = self.root / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    def _build_minimal_repo(self) -> None:
        for relpath in validator.REQUIRED_AUDIT_FILES:
            self._copy(relpath)
        self._copy(".gitattributes")

        decisions_dir = self.root / "docs" / "decisions"
        source_decisions = ROOT / "docs" / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        for source in source_decisions.glob("[0-9][0-9][0-9][0-9]-*.md"):
            self._write_text_lf(
                decisions_dir / source.name,
                f"# {source.name}\n\n- **Status:** Accepted\n",
            )

        schema_catalog = {
            "catalog_version": "1",
            "contracts": {
                "event": {
                    "2": {
                        "schema_id": "https://example.invalid/event-v2",
                        "path": "schemas/v2/event.schema.json",
                    }
                },
                "portia_event_id": {
                    "1": {
                        "schema_id": "https://example.invalid/event-id-v1",
                        "path": "schemas/v1/identifiers/portia-event-id.schema.json",
                    }
                },
            },
        }
        self._write_json("schemas/schema-catalog.json", schema_catalog)
        for relpath in (
            "schemas/v2/event.schema.json",
            "schemas/v1/identifiers/portia-event-id.schema.json",
        ):
            path = self.root / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            self._write_text_lf(path, "{}\n")

        coverage = {
            "fixture_contract": "pds-portia.issue-22-contract-coverage",
            "fixture_version": "1",
            "not_runtime_contract": True,
            "synthetic": True,
            "issue": 22,
            "source_catalog": "schemas/schema-catalog.json",
            "allowed_dispositions": [
                "positive_graph",
                "graph_invalid",
                "existing_focused_fixture_only",
                "foreign_context_only",
                "not_applicable_with_rationale",
            ],
            "contracts": [
                {
                    "contract": "event",
                    "catalog_versions": ["2"],
                    "current_version": "2",
                    "record_operational_family": True,
                    "disposition": "positive_graph",
                    "evidence": "P22-01",
                    "rationale": "fixture",
                },
                {
                    "contract": "portia_event_id",
                    "catalog_versions": ["1"],
                    "current_version": "1",
                    "record_operational_family": False,
                    "disposition": "not_applicable_with_rationale",
                    "evidence": "focused",
                    "rationale": "supporting primitive",
                },
            ],
        }
        self._write_json("tests/fixtures/issue_22/contract-coverage.json", coverage)

        scenarios = []
        for index in range(1, 16):
            scenarios.append(
                {
                    "scenario_id": f"P22-{index:02d}",
                    "scenario_kind": "positive",
                    "path": f"positive/p{index}/scenario.json",
                }
            )
        for index in range(1, 38):
            scenarios.append(
                {
                    "scenario_id": f"G22-{index:03d}",
                    "scenario_kind": "graph_invalid",
                    "path": f"graph-invalid/g{index}/scenario.json",
                }
            )
        corpus = {
            "fixture_contract": "pds-portia.representative-contract-graph-corpus",
            "fixture_version": "1",
            "not_runtime_contract": True,
            "synthetic": True,
            "issue": 22,
            "graph_finding_namespace": "G22",
            "scenarios": scenarios,
            "planned_positive_scenarios": [],
            "planned_graph_invalid_scenarios": [],
        }
        self._write_json("tests/fixtures/issue_22/corpus.json", corpus)

    def _audit(self) -> dict:
        return json.loads(
            (self.root / "docs/audits/portia-foundation-audit.json").read_text(encoding="utf-8")
        )

    def _write_audit(self, audit: dict) -> None:
        self._write_json("docs/audits/portia-foundation-audit.json", audit)

    @staticmethod
    def _write_text_lf(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _write_json(self, relpath: str, value: object) -> None:
        self._write_text_lf(
            self.root / relpath,
            json.dumps(value, indent=2) + "\n",
        )

    def _ready_audit(self, *, resolve_blocker: bool) -> dict:
        audit = self._audit()
        audit["final_verdict"] = "ready_for_implementation"
        audit["final_audited_portia_commit"] = "a" * 40
        if resolve_blocker:
            for finding in audit["findings"]:
                if finding["finding_id"] == "PF-AUD-004":
                    finding["status"] = "resolved"
                    finding["disposition"] = "fixed_in_audit"
                    finding["resolution"] = "validated"
            audit["unresolved_finding_ids"] = []
        return audit

    def _write_ready_approval(self) -> None:
        approval = {
            "approval_record_kind": "pds-portia.foundation-approval",
            "approval_record_version": "1",
            "milestone_issue": 10,
            "audit_issue": 23,
            "verdict": "ready_for_implementation",
            "approved_portia_commit": "a" * 40,
            "audit_record_reference": "docs/audits/portia-foundation-audit.json",
            "findings_record_reference": "docs/audits/portia-foundation-findings.md",
            "traceability_reference": "docs/audits/portia-foundation-traceability.md",
            "adr_disposition_summary": "17 accepted",
            "schema_catalog_coverage": "complete",
            "representative_corpus_result": "pass",
            "validation_evidence": ["fixture"],
            "approved_at": "2026-08-17T22:00:00-04:00",
        }
        self._write_json("docs/audits/portia-foundation-approval.json", approval)

    def assert_has_error(self, fragment: str) -> None:
        errors = validator.validate_repo(self.root)
        self.assertTrue(
            any(fragment in error for error in errors),
            msg=f"expected error containing {fragment!r}; got {errors}",
        )

    def test_completed_not_ready_audit_is_valid(self) -> None:
        self.assertEqual([], validator.validate_repo(self.root))

    def test_duplicate_finding_id_rejected(self) -> None:
        audit = self._audit()
        audit["findings"].append(copy.deepcopy(audit["findings"][0]))
        self._write_audit(audit)
        self.assert_has_error("duplicate finding IDs")

    def test_invalid_classification_rejected(self) -> None:
        audit = self._audit()
        audit["findings"][0]["classification"] = "critical"
        self._write_audit(audit)
        self.assert_has_error("invalid classification")

    def test_invalid_disposition_rejected(self) -> None:
        audit = self._audit()
        audit["findings"][0]["disposition"] = "ignore"
        self._write_audit(audit)
        self.assert_has_error("invalid disposition")

    def test_ready_with_unresolved_blocker_rejected(self) -> None:
        audit = self._ready_audit(resolve_blocker=False)
        self._write_audit(audit)
        self.assert_has_error("unresolved milestone blockers")

    def test_ready_without_approval_rejected(self) -> None:
        audit = self._ready_audit(resolve_blocker=True)
        self._write_audit(audit)
        self.assert_has_error("requires docs/audits/portia-foundation-approval.json")

    def test_not_ready_with_ready_approval_rejected(self) -> None:
        self._write_ready_approval()
        self.assert_has_error("not_ready audit cannot coexist with a ready foundation approval record")

    def test_missing_adr_disposition_rejected(self) -> None:
        audit = self._audit()
        audit["adr_dispositions"] = audit["adr_dispositions"][:-1]
        self._write_audit(audit)
        self.assert_has_error("audit ADR dispositions incomplete")

    def test_missing_exit_traceability_rejected(self) -> None:
        trace = self.root / "docs/audits/portia-foundation-traceability.md"
        text = trace.read_text(encoding="utf-8")
        line = next(line for line in text.splitlines() if line.startswith("| EC-18 |"))
        self._write_text_lf(trace, text.replace(line + "\n", ""))
        self.assert_has_error("traceability missing exit condition EC-18")

    def test_schema_catalog_coverage_mismatch_rejected(self) -> None:
        catalog = json.loads((self.root / "schemas/schema-catalog.json").read_text(encoding="utf-8"))
        catalog["contracts"]["extra"] = {
            "1": {
                "schema_id": "https://example.invalid/extra",
                "path": "schemas/v1/extra.schema.json",
            }
        }
        self._write_json("schemas/schema-catalog.json", catalog)
        extra = self.root / "schemas/v1/extra.schema.json"
        extra.parent.mkdir(parents=True, exist_ok=True)
        self._write_text_lf(extra, "{}\n")
        self.assert_has_error("schema catalog and Issue #22 contract coverage differ")

    def test_broken_audit_relative_link_rejected(self) -> None:
        report = self.root / "docs/audits/portia-foundation-audit.md"
        self._write_text_lf(
            report,
            report.read_text(encoding="utf-8") + "\n[broken](missing-file.md)\n",
        )
        self.assert_has_error("broken repository-relative Markdown link")

    def test_malformed_audit_json_rejected(self) -> None:
        self._write_text_lf(
            self.root / "docs/audits/portia-foundation-audit.json",
            "{",
        )
        self.assert_has_error("cannot parse audit JSON")

    def test_unsafe_path_rejected(self) -> None:
        audit = self._audit()
        audit["findings"][0]["affected_files_or_contracts"].append("../escape.md")
        self._write_audit(audit)
        self.assert_has_error("unsafe affected path")


    def test_missing_lf_checkout_policy_rejected(self) -> None:
        (self.root / ".gitattributes").unlink()
        self.assert_has_error("missing repository line-ending policy")

    def test_fixture_writer_uses_lf_bytes(self) -> None:
        fixture = self.root / "tests/fixtures/issue_22/writer-check.json"
        self._write_text_lf(fixture, "{\n  \"ok\": true\n}\n")
        payload = fixture.read_bytes()
        self.assertIn(b"\n", payload)
        self.assertNotIn(b"\r\n", payload)

    def test_crlf_issue22_fixture_rejected(self) -> None:
        corpus = self.root / "tests/fixtures/issue_22/corpus.json"
        payload = corpus.read_bytes()
        corpus.write_bytes(payload.replace(b"\n", b"\r\n"))
        self.assert_has_error("contain CRLF working-tree bytes")

    def test_finding_count_mismatch_rejected(self) -> None:
        audit = self._audit()
        audit["finding_counts"]["milestone_blocker"] += 1
        self._write_audit(audit)
        self.assert_has_error("finding_counts does not match findings")

    def test_malformed_commit_sha_rejected(self) -> None:
        audit = self._audit()
        audit["starting_portia_commit"] = "not-a-sha"
        self._write_audit(audit)
        self.assert_has_error("starting_portia_commit")

    def test_unbalanced_markdown_fence_rejected(self) -> None:
        report = self.root / "docs/audits/portia-foundation-audit.md"
        self._write_text_lf(
            report,
            report.read_text(encoding="utf-8") + "\n```\n",
        )
        self.assert_has_error("unbalanced triple-backtick fences")


if __name__ == "__main__":
    unittest.main()
