import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ISSUE_20_CONTRACTS = {
    "capture_batch",
    "page_target",
    "page_record",
    "paper_interpretation",
    "capture_proposal",
    "capture_review",
    "capture_materialization",
    "import_batch",
    "import_source_record",
    "import_proposal",
    "import_review",
    "import_materialization",
    "portia_capture_batch_id",
    "portia_page_target_id",
    "portia_page_record_id",
    "portia_paper_interpretation_id",
    "portia_capture_proposal_id",
    "portia_capture_review_id",
    "portia_import_batch_id",
    "portia_import_source_record_id",
    "portia_import_proposal_id",
    "portia_import_review_id",
}

ISSUE_20_PREFIXES = {
    "cbat_",
    "ptgt_",
    "prec_",
    "pint_",
    "cprp_",
    "crev_",
    "ibat_",
    "isrc_",
    "iprp_",
    "irev_",
}


class Issue20CloseoutDocumentationTests(unittest.TestCase):
    def read(self, relpath: str) -> str:
        return (ROOT / relpath).read_text(encoding="utf-8")

    def test_adr_0016_is_accepted_and_preserves_core_ownership(self):
        text = self.read(
            "docs/decisions/"
            "0016-define-paper-assisted-capture-pds2-routing-and-import-contracts.md"
        )
        self.assertIn("**Status:** Accepted", text)
        self.assertIn("Core remains the sole owner of generic PDS2", text)
        self.assertIn("Capture Batch is the non-domain Portia work root", text)
        self.assertIn("Import is a distinct source path", text)
        self.assertIn("Quarantine is exceptional integrity isolation", text)

    def test_all_issue_20_public_contracts_are_cataloged(self):
        catalog = json.loads(self.read("schemas/schema-catalog.json"))
        contracts = set(catalog["contracts"])
        self.assertTrue(ISSUE_20_CONTRACTS <= contracts)
        self.assertEqual(22, len(ISSUE_20_CONTRACTS))

    def test_public_contract_inventory_is_complete(self):
        text = self.read(
            "docs/validation/issue-20-public-contract-and-core-reuse-inventory.md"
        )
        for name in sorted(ISSUE_20_CONTRACTS):
            self.assertIn(name, text)
        self.assertIn("22 public Issue #20 contracts total", text)
        self.assertIn("ModuleWorkRef", text)
        self.assertIn("RouteRegistration", text)
        self.assertIn("RetainedSourceScan", text)

    def test_readme_reconciles_issue_20_boundary(self):
        text = self.read("README.md")
        self.assertIn("### Issue #20 current implementation", text)
        self.assertIn("Capture Batch", text)
        self.assertIn("Page Target", text)
        self.assertIn("Import Source Record", text)
        self.assertIn("Core retains ownership of generic PDS2 routing", text)

    def test_schema_guide_reconciles_issue_19_and_20_identifiers(self):
        text = self.read("schemas/README.md")
        for prefix in sorted(ISSUE_20_PREFIXES):
            self.assertIn(prefix, text)
        for prefix in ("fup_", "out_", "ren_", "rpr_"):
            self.assertIn(prefix, text)
        self.assertIn("## Issue #20 paper-capture and import contracts", text)

    def test_acceptance_matrix_is_fully_closed(self):
        text = self.read("docs/validation/issue-20-acceptance-matrix.md")
        self.assertIn("82 criteria tracked", text)
        self.assertIn("82 passed", text)
        self.assertIn("0 pending", text)
        self.assertEqual(82, text.count("| Passed |"))
        self.assertNotIn("Pending final validation", text)
        self.assertNotIn("TBD", text)
        self.assertNotIn("TODO", text)

    def test_pre_adr_drift_checkpoint_records_quillan_delta(self):
        text = self.read("docs/validation/issue-20-pre-adr-drift-checkpoint.md")
        self.assertIn("c69533fa980cf41aa92c52978617e170263f6135", text)
        self.assertIn("6c507213618b68a6dd3ea096e1a898201ff029e6", text)
        self.assertIn("b03ffad0749db0dce47e68f095a8d477fa69eb2d", text)
        self.assertIn("047e47f60730b8a5540b5e1d92f008ffad37eede", text)
        self.assertIn("No Issue #20 Portia paper/import decision requires revision", text)
        final_text = self.read(
            "docs/validation/issue-20-final-repository-drift-and-validation.md"
        )
        self.assertIn("Ran 1020 tests in 130.205s", final_text)
        self.assertIn("82 passed", final_text)
        self.assertIn("52 synthetic examples total", final_text)
        self.assertIn("No additional Issue #20 workflow contract is required", final_text)


if __name__ == "__main__":
    unittest.main()
