from __future__ import annotations

from datetime import datetime
from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "hypothesis"
SCHEMA_PATH = "schemas/v1/hypotheses/hypothesis.schema.json"

HYPOTHESIS_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}
LIFECYCLE_REASONS = {
    "judgment_recorded", "recording_error", "wrong_author", "wrong_target",
    "invalid_provenance", "prohibited_payload", "corrected_by_successor",
    "duplicate_consolidated", "work_root_corrected", "contract_migrated", "other",
}
SUPERSESSION_REASONS = {
    "hypothesis_corrected", "hypothesis_refined", "hypothesis_reconsidered",
    "author_corrected", "target_corrected", "evidence_role_corrected",
    "duplicate_consolidated", "work_root_corrected", "contract_migrated", "other",
}

def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value)

def _wr_identity(value: dict[str, Any]) -> tuple[str, str, str, str]:
    work=value["work_ref"]; record=value["record_ref"]
    return (work["class_id"], work["work_id"], record["record_id"], record["contract_version"])

def _evidence_identity(entry: dict[str, Any]) -> tuple[Any, ...]:
    evidence=entry["evidence_ref"]
    if evidence["kind"]=="portia_work":
        work=evidence["work_ref"]
        return ("portia_work", work["class_id"], work["work_id"], work["contract_version"])
    if evidence["kind"]=="portia_record":
        return ("portia_record",)+_wr_identity(evidence["work_record_ref"])
    module=evidence["module_work_record_ref"]; work=module["work_ref"]; record=module["record_ref"]
    return (
        "module_record", work["module_id"], work["class_id"], work["work_id"],
        record["module_id"], record["record_kind"], record["record_id"], record["contract_version"],
    )

def application_errors(hypothesis: dict[str, Any]) -> list[str]:
    errors: list[str]=[]
    if _ts(hypothesis["updated_at"]) < _ts(hypothesis["created_at"]):
        errors.append("updated_at precedes created_at")

    review_ref=hypothesis.get("review_ref")
    if review_ref is not None:
        work=review_ref["work_ref"]
        if (work["class_id"], work["work_id"]) != (hypothesis["class_id"], hypothesis["work_id"]):
            errors.append("Review link belongs to different Event")

    creation=hypothesis["creation_source"]
    if creation["type"] in {"paper_capture","import"} and hypothesis["status"]!="proposed" and review_ref is None:
        errors.append("paper/import activation requires accepted review history")

    identities=[]
    for entry in hypothesis["evidence"]:
        identities.append(_evidence_identity(entry))
        evidence=entry["evidence_ref"]
        if evidence["kind"]=="module_record":
            module=evidence["module_work_record_ref"]
            if module["work_ref"]["module_id"] != module["record_ref"]["module_id"]:
                errors.append("module evidence IDs differ")
    if len(identities)!=len(set(identities)):
        errors.append("logical evidence identity repeated")

    supersedes=hypothesis.get("supersedes",[])
    if supersedes:
        predecessor_ids=[_wr_identity(entry["work_record_ref"]) for entry in supersedes]
        reasons=[entry["reason"] for entry in supersedes]
        if len(predecessor_ids)!=len(set(predecessor_ids)):
            errors.append("predecessor identity repeated")
        if len(set(reasons))!=1:
            errors.append("mixed supersession reasons")
        for entry in supersedes:
            work=entry["work_record_ref"]["work_ref"]; record=entry["work_record_ref"]["record_ref"]; reason=entry["reason"]
            same_work=(work["class_id"],work["work_id"])==(hypothesis["class_id"],hypothesis["work_id"])
            same_id=record["record_id"]==hypothesis["hypothesis_id"]
            if same_work and same_id and reason!="contract_migrated":
                errors.append("Hypothesis replacement self-reference")
            if reason=="work_root_corrected":
                if same_work: errors.append("work-root correction requires different work")
                if not same_id: errors.append("work-root correction must preserve Hypothesis ID")
            elif reason!="contract_migrated" and not same_work:
                errors.append("ordinary Hypothesis correction cannot cross work roots")
        if len(set(reasons))==1:
            reason=reasons[0]
            if reason=="duplicate_consolidated" and len(set(predecessor_ids))<2:
                errors.append("duplicate consolidation needs two predecessors")
            elif reason not in {"duplicate_consolidated","contract_migrated"} and len(set(predecessor_ids))!=1:
                errors.append("ordinary correction is one-to-one")
    return errors

def review_scenario_errors(scenario: dict[str, Any]) -> list[str]:
    review=scenario["review"]; hypothesis=scenario["hypothesis"]; errors=[]
    review_ref=hypothesis.get("review_ref")
    if review_ref is None or review_ref["record_ref"]["record_id"]!=review["review_id"]:
        errors.append("Hypothesis does not resolve supplied Review")
    if (review["class_id"],review["work_id"])!=(hypothesis["class_id"],hypothesis["work_id"]):
        errors.append("Review belongs to different Event")
    if review["target"]!=hypothesis["target"]:
        errors.append("Hypothesis target differs from Review target")
    # Deliberately no author==reviewer rule: represented authorship and Review assignment are distinct.
    return errors

def competition_errors(scenario: dict[str, Any]) -> list[str]:
    review=scenario["review"]; hypotheses=scenario["hypotheses"]; errors=[]
    ids=[value["hypothesis_id"] for value in hypotheses]
    if len(ids)!=len(set(ids)): errors.append("competing Hypothesis identity repeated")
    id_set=set(ids)
    for hypothesis in hypotheses:
        superseded_ids={
            entry["work_record_ref"]["record_ref"]["record_id"]
            for entry in hypothesis.get("supersedes",[])
        }
        if superseded_ids & id_set:
            errors.append("competing Hypotheses must not supersede one another merely because they conflict")
        if review_scenario_errors({"review":review,"hypothesis":hypothesis}):
            errors.append("competing Hypothesis does not share the governing Review scope")
    return errors

def _referenced_account_ids(hypothesis: dict[str, Any]) -> set[str]:
    result=set()
    for entry in hypothesis["evidence"]:
        evidence=entry["evidence_ref"]
        if evidence["kind"]=="portia_record":
            record=evidence["work_record_ref"]["record_ref"]
            if record["record_kind"]=="account": result.add(record["record_id"])
    return result

def account_lineage_findings(scenario: dict[str, Any]) -> list[str]:
    referenced=_referenced_account_ids(scenario["hypothesis"]); findings=[]
    for account in scenario["accounts"]:
        if account["account_id"] not in referenced: continue
        for relation in account.get("related_accounts",[]):
            upstream=relation["account_ref"]["record_id"]
            if upstream in referenced:
                findings.append(f"{account['account_id']} {relation['relation']} {upstream}")
    return findings

class Issue16HypothesisContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog,cls.store=load_validated_catalog_and_store()
        cls.validator=validator_for("hypothesis","1",catalog=cls.catalog,store=cls.store)
        cls.review_validator=validator_for("review","1",catalog=cls.catalog,store=cls.store)
        cls.account_validator=validator_for("account","1",catalog=cls.catalog,store=cls.store)
        cls.manifest=load_json(FIXTURE_ROOT/"manifest.json")
        cls.review_scenarios=load_json(FIXTURE_ROOT/"review-scenarios"/"manifest.json")
        cls.competition_scenarios=load_json(FIXTURE_ROOT/"competition-scenarios"/"manifest.json")
        cls.lineage_scenarios=load_json(FIXTURE_ROOT/"lineage-scenarios"/"manifest.json")

    def test_manifest_metadata(self):
        self.assertEqual((self.manifest["issue"],self.manifest["contract"],self.manifest["version"]),(16,"hypothesis","1"))

    def test_valid_roots(self):
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value=load_json(FIXTURE_ROOT/"valid"/filename); errors=list(self.validator.iter_errors(value))
                self.assertFalse(errors,"\n".join(error.message for error in errors)); self.assertEqual(application_errors(value),[])

    def test_structural_invalid_roots(self):
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                self.assertTrue(list(self.validator.iter_errors(load_json(FIXTURE_ROOT/"invalid"/filename))))

    def test_application_invalid_roots(self):
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value=load_json(FIXTURE_ROOT/"application-invalid"/filename); errors=list(self.validator.iter_errors(value))
                self.assertFalse(errors,"\n".join(error.message for error in errors)); self.assertTrue(application_errors(value))

    def test_valid_review_scenarios(self):
        for filename in self.review_scenarios["valid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"review-scenarios"/"valid"/filename)
                hypothesis_errors=list(self.validator.iter_errors(scenario["hypothesis"]))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(hypothesis_errors,"\n".join(error.message for error in hypothesis_errors))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertEqual(review_scenario_errors(scenario),[])

    def test_application_invalid_review_scenarios(self):
        for filename in self.review_scenarios["application_invalid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"review-scenarios"/"application-invalid"/filename)
                hypothesis_errors=list(self.validator.iter_errors(scenario["hypothesis"]))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(hypothesis_errors,"\n".join(error.message for error in hypothesis_errors))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertTrue(review_scenario_errors(scenario))

    def test_competing_hypotheses_may_coexist(self):
        for filename in self.competition_scenarios["valid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"competition-scenarios"/"valid"/filename)
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                for hypothesis in scenario["hypotheses"]:
                    errors=list(self.validator.iter_errors(hypothesis))
                    self.assertFalse(errors,"\n".join(error.message for error in errors))
                    self.assertEqual(application_errors(hypothesis),[])
                self.assertEqual(competition_errors(scenario),[])

    def test_known_account_lineage_is_detectable_without_weight_inference(self):
        for filename in self.lineage_scenarios["valid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"lineage-scenarios"/"valid"/filename)
                errors=list(self.validator.iter_errors(scenario["hypothesis"]))
                self.assertFalse(errors,"\n".join(error.message for error in errors))
                self.assertEqual(application_errors(scenario["hypothesis"]),[])
                for account in scenario["accounts"]:
                    account_errors=list(self.account_validator.iter_errors(account))
                    self.assertFalse(account_errors,"\n".join(error.message for error in account_errors))
                findings=account_lineage_findings(scenario)
                if filename=="known-account-lineage-preserved.json": self.assertTrue(findings)
                else: self.assertEqual(findings,[])

    def test_catalog_and_schema_identity(self):
        entry=self.catalog["contracts"]["hypothesis"]["1"]; self.assertEqual(entry["path"],SCHEMA_PATH)
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(schema["$id"],entry["schema_id"])
        self.assertNotIn("/latest/",schema["$id"]); self.assertNotIn("/current/",schema["$id"])

    def test_envelope_and_semantic_boundaries(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]["status"]["enum"]),{"proposed","active","invalidated","superseded"})
        self.assertEqual(set(schema["properties"]["consideration_state"]["enum"]),{"under_consideration","set_aside"})
        forbidden={
            "student_id","student_label","finding","determination","diagnosis","behavioral_function","fba_result",
            "confidence","confidence_percent","truth_probability","evidence_score","credibility_score","risk_score",
            "AI_confidence","automatic_hypothesis",
        }
        for field in forbidden: self.assertNotIn(field,schema["properties"])

    def test_human_target_and_evidence_reuse(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        self.assertEqual(schema["properties"]["target"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/targets/portia-target-ref.schema.json")
        self.assertEqual(schema["properties"]["author"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/attribution/represented-human-attribution.schema.json")
        relation=schema["$defs"]["evidenceRelation"]
        self.assertEqual(set(relation["properties"]["relation"]["enum"]),{"supporting","contrary","contextual"})
        self.assertEqual(relation["properties"]["evidence_ref"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/references/judgment-evidence-ref.schema.json")

    def test_unsupported_hypothesis_is_allowed(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertNotIn("minItems",schema["properties"]["evidence"])
        value=load_json(FIXTURE_ROOT/"valid"/"event-under-consideration-empty-evidence.json"); self.assertEqual(value["evidence"],[])

    def test_set_aside_is_not_invalidation(self):
        value=load_json(FIXTURE_ROOT/"valid"/"event-set-aside-empty-evidence.json")
        self.assertEqual((value["status"],value["consideration_state"]),("active","set_aside"))
        self.assertEqual(application_errors(value),[])

    def test_lifecycle_and_reason_inventory_matches_adr(self):
        self.assertEqual(HYPOTHESIS_LIFECYCLE["active"],{"invalidated","superseded"})
        self.assertEqual(LIFECYCLE_REASONS,{
            "judgment_recorded","recording_error","wrong_author","wrong_target","invalid_provenance",
            "prohibited_payload","corrected_by_successor","duplicate_consolidated","work_root_corrected",
            "contract_migrated","other",
        })
        self.assertEqual(SUPERSESSION_REASONS,{
            "hypothesis_corrected","hypothesis_refined","hypothesis_reconsidered","author_corrected",
            "target_corrected","evidence_role_corrected","duplicate_consolidated","work_root_corrected",
            "contract_migrated","other",
        })
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        self.assertEqual(set(schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]),SUPERSESSION_REASONS)

    def test_no_parallel_hypothesis_shared_contracts(self):
        names=set(self.catalog["contracts"])
        for name in (
            "hypothesis_dependency","hypothesis_amendment","hypothesis_operation_journal",
            "hypothesis_quarantine","hypothesis_integrity_finding","hypothesis_confidence","hypothesis_fba",
        ):
            self.assertNotIn(name,names)

if __name__ == "__main__": unittest.main()
