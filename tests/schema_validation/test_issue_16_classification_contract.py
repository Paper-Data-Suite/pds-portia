from __future__ import annotations

from datetime import datetime
from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "classification"
SCHEMA_PATH = "schemas/v1/classifications/classification.schema.json"

CLASSIFICATION_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}
LIFECYCLE_REASONS = {
    "judgment_recorded", "recording_error", "wrong_selector", "wrong_target",
    "wrong_definition", "invalid_provenance", "prohibited_payload",
    "corrected_by_successor", "duplicate_consolidated", "work_root_corrected",
    "contract_migrated", "other",
}
SUPERSESSION_REASONS = {
    "classification_corrected", "selector_corrected", "target_corrected",
    "definition_corrected", "duplicate_consolidated", "work_root_corrected",
    "contract_migrated", "other",
}

def _ts(v: str) -> datetime:
    return datetime.fromisoformat(v)

def _human_identity(v: dict[str, Any]) -> tuple[Any, ...]:
    k=v["kind"]
    if k=="roster_student":
        r=v["roster_student_ref"]; return (k,r["class_id"],r["student_id"])
    if k=="actor": return (k,v["actor_ref"]["actor_id"])
    if k=="local_operator": return (k,v["display_label"])
    if k=="descriptive_person": return (k,v["description_type"],v["display_label"])
    return (k,v.get("identity_status"),v.get("display_label"))

def _wr_identity(wr: dict[str, Any]) -> tuple[str,str,str,str]:
    w=wr["work_ref"]; r=wr["record_ref"]
    return (w["class_id"],w["work_id"],r["record_id"],r["contract_version"])

def _evidence_identity(e: dict[str, Any]) -> tuple[Any, ...]:
    if e["kind"]=="portia_work":
        w=e["work_ref"]; return ("portia_work",w["class_id"],w["work_id"],w["contract_version"])
    if e["kind"]=="portia_record":
        return ("portia_record",)+_wr_identity(e["work_record_ref"])
    m=e["module_work_record_ref"]; w=m["work_ref"]; r=m["record_ref"]
    return ("module_record",w["module_id"],w["class_id"],w["work_id"],r["module_id"],r["record_kind"],r["record_id"],r["contract_version"])

def application_errors(c: dict[str, Any]) -> list[str]:
    errors=[]
    if _ts(c["updated_at"]) < _ts(c["created_at"]): errors.append("updated_at precedes created_at")
    if c["stage"] in {"reviewer_selected","reviewer_confirmed"} and c["status"]=="active" and "review_ref" not in c:
        errors.append("active reviewer stage requires governing Review")
    if "review_ref" in c:
        w=c["review_ref"]["work_ref"]
        if (w["class_id"],w["work_id"]) != (c["class_id"],c["work_id"]): errors.append("Review link belongs to different Event")
    if "reviewed_classification" in c:
        wr=c["reviewed_classification"]; w=wr["work_ref"]; r=wr["record_ref"]
        if (w["class_id"],w["work_id"]) != (c["class_id"],c["work_id"]): errors.append("reviewed Classification belongs to different Event")
        if r["record_id"]==c["classification_id"]: errors.append("Classification cannot review itself")
    creation=c["creation_source"]
    if creation["type"] in {"paper_capture","import"} and c["status"]!="proposed" and "review_ref" not in c:
        errors.append("paper/import activation requires accepted review history")
    ids=[]
    for e in c.get("basis",[]):
        ids.append(_evidence_identity(e))
        if e["kind"]=="module_record":
            m=e["module_work_record_ref"]
            if m["work_ref"]["module_id"] != m["record_ref"]["module_id"]: errors.append("module basis IDs differ")
    if len(ids)!=len(set(ids)): errors.append("logical basis identity repeated")
    supers=c.get("supersedes",[])
    if supers:
        identities=[_wr_identity(e["work_record_ref"]) for e in supers]
        reasons=[e["reason"] for e in supers]
        if len(identities)!=len(set(identities)): errors.append("predecessor identity repeated")
        if len(set(reasons))!=1: errors.append("mixed supersession reasons")
        for e in supers:
            w=e["work_record_ref"]["work_ref"]; r=e["work_record_ref"]["record_ref"]; reason=e["reason"]
            same_work=(w["class_id"],w["work_id"])==(c["class_id"],c["work_id"]); same_id=r["record_id"]==c["classification_id"]
            if same_work and same_id and reason!="contract_migrated": errors.append("Classification replacement self-reference")
            if reason=="work_root_corrected":
                if same_work: errors.append("work-root correction requires different work")
                if not same_id: errors.append("work-root correction must preserve Classification ID")
            elif reason!="contract_migrated" and not same_work: errors.append("ordinary Classification correction cannot cross work roots")
        if len(set(reasons))==1:
            reason=reasons[0]
            if reason=="duplicate_consolidated" and len(set(identities))<2: errors.append("duplicate consolidation needs two predecessors")
            elif reason not in {"duplicate_consolidated","contract_migrated"} and len(set(identities))!=1: errors.append("ordinary correction is one-to-one")
    return errors

def _result_identity(result: dict[str, Any]) -> tuple[Any, ...]:
    if result["kind"]=="unable_to_determine": return ("unable_to_determine",)
    d=result["definition"]; return ("category_selected",d["scheme_id"],d["scheme_version"],d["category_code"])

def review_scenario_errors(s: dict[str, Any]) -> list[str]:
    review=s["review"]; prior=s["reviewed_classification"]; current=s["classification"]; errors=[]
    rr=current.get("review_ref")
    if rr is None or rr["record_ref"]["record_id"] != review["review_id"]: errors.append("Classification does not resolve supplied Review")
    if (review["class_id"],review["work_id"]) != (current["class_id"],current["work_id"]): errors.append("Review belongs to different Event")
    if current["status"]=="active" and current["stage"] in {"reviewer_selected","reviewer_confirmed"}:
        if review["status"]!="active" or review["review_state"]!="completed": errors.append("active reviewer Classification requires active completed Review")
    if _human_identity(current["selector"]) != _human_identity(review["reviewer"]): errors.append("selector differs from Review reviewer")
    if review["target"] != current["target"]: errors.append("Classification target differs from Review target")
    reviewed=current.get("reviewed_classification")
    if reviewed is not None:
        if reviewed["record_ref"]["record_id"] != prior["classification_id"]: errors.append("reviewed Classification reference does not resolve supplied record")
        if (prior["class_id"],prior["work_id"]) != (current["class_id"],current["work_id"]): errors.append("reviewed Classification belongs to different Event")
    if current["stage"]=="reviewer_confirmed" and _result_identity(current["result"]) != _result_identity(prior["result"]): errors.append("reviewer-confirmed result differs")
    if current["stage"]=="reviewer_selected" and reviewed is not None and current["classification_id"]!=prior["classification_id"]:
        # Ordinary disagreement is intentionally allowed and does not require supersession.
        pass
    return errors

class Issue16ClassificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog,cls.store=load_validated_catalog_and_store()
        cls.validator=validator_for("classification","1",catalog=cls.catalog,store=cls.store)
        cls.review_validator=validator_for("review","1",catalog=cls.catalog,store=cls.store)
        cls.manifest=load_json(FIXTURE_ROOT/"manifest.json")
        cls.scenarios=load_json(FIXTURE_ROOT/"review-scenarios"/"manifest.json")
    def test_manifest_metadata(self):
        self.assertEqual((self.manifest["issue"],self.manifest["contract"],self.manifest["version"]),(16,"classification","1"))
    def test_valid_roots(self):
        for f in self.manifest["valid"]:
            with self.subTest(filename=f):
                v=load_json(FIXTURE_ROOT/"valid"/f); e=list(self.validator.iter_errors(v)); self.assertFalse(e,"\n".join(x.message for x in e)); self.assertEqual(application_errors(v),[])
    def test_structural_invalid_roots(self):
        for f in self.manifest["invalid"]:
            with self.subTest(filename=f): self.assertTrue(list(self.validator.iter_errors(load_json(FIXTURE_ROOT/"invalid"/f))))
    def test_application_invalid_roots(self):
        for f in self.manifest["application_invalid"]:
            with self.subTest(filename=f):
                v=load_json(FIXTURE_ROOT/"application-invalid"/f); e=list(self.validator.iter_errors(v)); self.assertFalse(e,"\n".join(x.message for x in e)); self.assertTrue(application_errors(v))
    def test_valid_review_scenarios(self):
        for f in self.scenarios["valid"]:
            with self.subTest(filename=f):
                s=load_json(FIXTURE_ROOT/"review-scenarios"/"valid"/f)
                for k in ("reviewed_classification","classification"):
                    e=list(self.validator.iter_errors(s[k])); self.assertFalse(e,"\n".join(x.message for x in e))
                e=list(self.review_validator.iter_errors(s["review"])); self.assertFalse(e,"\n".join(x.message for x in e))
                self.assertEqual(review_scenario_errors(s),[])
    def test_application_invalid_review_scenarios(self):
        for f in self.scenarios["application_invalid"]:
            with self.subTest(filename=f):
                s=load_json(FIXTURE_ROOT/"review-scenarios"/"application-invalid"/f)
                for k in ("reviewed_classification","classification"):
                    e=list(self.validator.iter_errors(s[k])); self.assertFalse(e,"\n".join(x.message for x in e))
                e=list(self.review_validator.iter_errors(s["review"])); self.assertFalse(e,"\n".join(x.message for x in e))
                self.assertTrue(review_scenario_errors(s))
    def test_catalog_and_schema_identity(self):
        entry=self.catalog["contracts"]["classification"]["1"]; self.assertEqual(entry["path"],SCHEMA_PATH)
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(schema["$id"],entry["schema_id"]); self.assertNotIn("/latest/",schema["$id"]); self.assertNotIn("/current/",schema["$id"])
    def test_envelope_and_semantic_shortcuts(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]["stage"]["enum"]),{"reporter_selected","reviewer_selected","reviewer_confirmed","unknown"})
        self.assertEqual(set(schema["properties"]["status"]["enum"]),{"proposed","active","invalidated","superseded"})
        for forbidden in ("student_id","student_label","finding","determination","credibility","credibility_score","risk_score","policy_violation","behavioral_function","automatic_classification"):
            self.assertNotIn(forbidden,schema["properties"])
    def test_result_identity_is_historical_and_closed(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH); d=schema["$defs"]["definitionSnapshot"]
        self.assertFalse(d["additionalProperties"]); self.assertEqual(set(d["required"]),{"scheme_id","scheme_version","category_code","category_label","definition_text"})
        self.assertEqual(len(schema["$defs"]["classificationResult"]["oneOf"]),2)
    def test_reviewer_confirmed_structurally_requires_predecessor(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        self.assertTrue(any(x.get("then",{}).get("required")==["reviewed_classification"] for x in schema["allOf"]))
    def test_lifecycle_and_reason_inventory_matches_adr(self):
        self.assertEqual(CLASSIFICATION_LIFECYCLE["active"],{"invalidated","superseded"})
        self.assertEqual(LIFECYCLE_REASONS,{"judgment_recorded","recording_error","wrong_selector","wrong_target","wrong_definition","invalid_provenance","prohibited_payload","corrected_by_successor","duplicate_consolidated","work_root_corrected","contract_migrated","other"})
        self.assertEqual(SUPERSESSION_REASONS,{"classification_corrected","selector_corrected","target_corrected","definition_corrected","duplicate_consolidated","work_root_corrected","contract_migrated","other"})
    def test_no_parallel_classification_shared_contracts(self):
        names=set(self.catalog["contracts"])
        for n in ("classification_dependency","classification_amendment","classification_operation_journal","classification_quarantine","classification_integrity_finding"):
            self.assertNotIn(n,names)

if __name__ == "__main__": unittest.main()
