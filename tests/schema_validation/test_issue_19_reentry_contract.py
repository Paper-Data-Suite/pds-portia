from __future__ import annotations
from datetime import date, datetime
from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-19" / "reentry"
SCHEMA_PATH = "schemas/v1/reentries/reentry.schema.json"
EVENT_COORDINATOR_ELIGIBLE_KINDS={"local_operator","actor"}
SUPPORT_COORDINATOR_CONTEXTS={"provider_or_collaborator","coordinator"}

def _dt(v:str)->datetime: return datetime.fromisoformat(v)
def _work(v): return v["class_id"],v["work_kind"],v["work_id"]
def _refwork(r):
    w=r["work_ref"]; return w["class_id"],w["work_kind"],w["work_id"]
def _refid(r):
    w=r["work_ref"]; q=r["record_ref"]; return w["class_id"],w["work_kind"],w["work_id"],q["record_id"],q["contract_version"]
def _ctxwork(c):
    if c["kind"] in {"event","support_process"}: return c["work_ref"]
    if c["kind"] in {"determination","response","communication"}: return c["record_ref"]["work_ref"]
    return None

def application_errors(value:dict[str,Any], *, participants:dict[str,dict[str,Any]]|None=None)->list[str]:
    e=[]
    if _dt(value["updated_at"])<_dt(value["created_at"]): e.append("updated_at precedes created_at")
    p=value["planned_return"]
    if p["kind"]=="window" and "starts_on" in p and date.fromisoformat(p["ends_on"])<date.fromisoformat(p["starts_on"]): e.append("planned return date window reversed")
    if p["kind"]=="window" and "starts_at" in p and _dt(p["ends_at"])<_dt(p["starts_at"]): e.append("planned return exact window reversed")
    c=value["creation_source"]
    if c["type"] in {"paper_capture","import"} and value["status"]=="active": e.append("paper/import activation requires review")
    coord=value["coordinator"]
    if value["work_kind"]=="event" and value["status"]=="active":
        if coord["person"]["kind"] not in EVENT_COORDINATOR_ELIGIBLE_KINDS: e.append("Event Reentry coordinator is not operational")
    if value["work_kind"]=="support_process" and value["status"]=="active" and participants is not None:
        pid=coord["participant_ref"]["record_id"]; pr=participants.get(pid)
        if pr is None: e.append("Support Process coordinator does not resolve")
        else:
            if pr.get("status")!="active": e.append("Support Process coordinator not active")
            if pr.get("class_id")!=value["class_id"]: e.append("Support Process coordinator class mismatch")
            if pr.get("work_id")!=value["work_id"]: e.append("Support Process coordinator work mismatch")
            if not ({x["kind"] for x in pr.get("contexts",[])} & SUPPORT_COORDINATOR_CONTEXTS):
                e.append("Support Process coordinator lacks operational context")
    cw=_ctxwork(value["initiating_context"])
    if cw is not None and cw["class_id"]!=value["class_id"]: e.append("initiating context class mismatch")
    for r in value.get("support_refs",[]):
        if r["work_ref"]["class_id"]!=value["class_id"]: e.append("support plan class mismatch")
        if value["work_kind"]=="support_process" and r["work_ref"]["work_id"]!=value["work_id"]: e.append("Support-Process-owned Reentry plan must share process")
    sup=value.get("supersedes",[])
    if sup:
        ids=[_refid(x["work_record_ref"]) for x in sup]; reasons=[x["reason"] for x in sup]
        if len(ids)!=len(set(ids)): e.append("predecessor identity repeated")
        if len(set(reasons))!=1: e.append("mixed supersession reasons")
        for x in sup:
            r=x["work_record_ref"]; samework=_refwork(r)==_work(value); sameid=r["record_ref"]["record_id"]==value["reentry_id"]; reason=x["reason"]
            if samework and sameid: e.append("Reentry replacement self-reference")
            if reason=="work_root_corrected":
                if samework: e.append("work-root correction requires different work")
                if not sameid: e.append("work-root correction must preserve Reentry ID")
            elif reason!="contract_migrated" and not samework:
                e.append("ordinary Reentry correction cannot cross work roots")
        if len(set(reasons))==1:
            if reasons[0]=="duplicate_consolidated" and len(set(ids))<2: e.append("duplicate consolidation needs two predecessors")
            elif reasons[0]!="duplicate_consolidated" and len(set(ids))!=1: e.append("non-consolidation correction is one-to-one")
    return e

def good_participants():
    return {"spp_coordinator":{"class_id":"eng10_p2_2026","work_id":"sup_alpha","status":"active","contexts":[{"kind":"coordinator"}]}}
def bad_participants():
    return {"spp_coordinator":{"class_id":"eng10_p2_2026","work_id":"sup_alpha","status":"active","contexts":[{"kind":"family_or_support_person"}]}}

class Issue19ReentryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog,cls.store=load_validated_catalog_and_store()
        cls.validator=validator_for("reentry","1",catalog=cls.catalog,store=cls.store)
        cls.manifest=load_json(FIXTURE_ROOT/"manifest.json")
    def test_manifest_and_catalog(self):
        self.assertEqual(self.manifest["contract"],"reentry")
        self.assertEqual(self.catalog["contracts"]["reentry"]["1"],{"schema_id":"https://paper-data-suite.github.io/pds-portia/"+SCHEMA_PATH,"path":SCHEMA_PATH})
    def test_valid_fixtures_pass(self):
        for f in self.manifest["valid"]:
            with self.subTest(filename=f):
                v=load_json(FIXTURE_ROOT/"valid"/f); errs=list(self.validator.iter_errors(v))
                self.assertFalse(errs,"\n".join(x.message for x in errs)); self.assertEqual(application_errors(v,participants=good_participants()),[])
    def test_invalid_fixtures_fail_structurally(self):
        for f in self.manifest["invalid"]:
            with self.subTest(filename=f):
                self.assertTrue(list(self.validator.iter_errors(load_json(FIXTURE_ROOT/"invalid"/f))))
    def test_application_invalid_fixtures_are_structurally_valid(self):
        for f in self.manifest["application_invalid"]:
            with self.subTest(filename=f):
                v=load_json(FIXTURE_ROOT/"application-invalid"/f); errs=list(self.validator.iter_errors(v))
                self.assertFalse(errs,"\n".join(x.message for x in errs))
                p=bad_participants() if f=="support-coordinator-without-operational-context.json" else good_participants()
                self.assertTrue(application_errors(v,participants=p))
    def test_initiating_context_vocabulary_is_closed(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); refs=s["$defs"]["initiatingContext"]["oneOf"]
        found={s["$defs"][x["$ref"].split("/")[-1]]["properties"]["kind"]["const"] for x in refs}
        self.assertEqual(found,{"event","determination","response","support_process","communication","external_or_restricted_process","other"})
    def test_external_context_is_minimal(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); p=s["$defs"]["externalContext"]["properties"]
        self.assertEqual(set(p),{"kind","system_label","reference_id","status_label"})
    def test_planned_element_vocabulary_is_closed(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(set(s["$defs"]["plannedElement"]["properties"]["kind"]["enum"]),{"orientation_or_check_in","schedule_or_environment","academic_access","support_handoff","relationship_reconnection","communication","other"})
    def test_planned_elements_do_not_embed_actual_actions(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(set(s["$defs"]["plannedElement"]["properties"]),{"kind","description"})
    def test_planned_return_preserves_precision(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(len(s["$defs"]["plannedReturn"]["oneOf"]),4); self.assertNotIn("returned",s["properties"])
    def test_workflow_completion_is_not_clearance_or_outcome(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(set(s["properties"]["workflow_state"]["enum"]),{"planned","active","completed","cancelled","unable_to_complete"})
        for k in ("safe","compliant","rehabilitated","relationship_restored","clearance","readiness","success","outcome"): self.assertNotIn(k,s["properties"])
    def test_reentry_has_no_access_barrier_fields(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH)
        for k in ("clearance_required","apology_required","behavior_contract","admission_permission","access_condition","readiness_score","medical_clearance","threat_assessment_clearance"): self.assertNotIn(k,s["properties"])
    def test_support_refs_are_support_or_intervention_only(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); t=str(s["$defs"]["supportPlanRef"]["oneOf"])
        self.assertIn("'const': 'support'",t); self.assertIn("'const': 'intervention'",t); self.assertNotIn("'const': 'implementation'",t)
    def test_lifecycle_is_separate_from_workflow(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(set(s["properties"]["status"]["enum"]),{"proposed","active","invalidated","superseded"}); self.assertNotIn("completed",s["properties"]["status"]["enum"])
    def test_successor_reason_vocabulary_matches_adr(self):
        s=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(set(s["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]),{"coordinator_corrected","target_corrected","context_corrected","timing_corrected","plan_element_corrected","completion_corrected","duplicate_consolidated","work_root_corrected","contract_migrated","other"})
    def test_current_use_coordinator_restriction_is_application_level(self):
        v=load_json(FIXTURE_ROOT/"application-invalid"/"active-event-roster-student-coordinator.json")
        self.assertFalse(list(self.validator.iter_errors(v))); self.assertIn("Event Reentry coordinator is not operational",application_errors(v))

if __name__=="__main__":
    unittest.main()
