from __future__ import annotations

from datetime import datetime
from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "determination"
SCHEMA_PATH = "schemas/v1/determinations/determination.schema.json"

DETERMINATION_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}
LIFECYCLE_REASONS = {
    "judgment_recorded", "recording_error", "wrong_decision_maker", "wrong_target",
    "wrong_authority", "wrong_process_basis", "invalid_provenance", "prohibited_payload",
    "corrected_by_successor", "duplicate_consolidated", "work_root_corrected",
    "contract_migrated", "other",
}
SUPERSESSION_REASONS = {
    "outcome_corrected", "question_corrected", "decision_maker_corrected",
    "target_corrected", "authority_corrected", "process_basis_corrected",
    "reconsidered", "reversed_on_reconsideration", "duplicate_consolidated",
    "work_root_corrected", "contract_migrated", "other",
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

def _outcome_identity(outcome: dict[str, Any]) -> tuple[Any, ...]:
    kind=outcome["kind"]
    if kind=="conclusion":
        return (kind,outcome["text"])
    if kind=="coded_conclusion":
        return (kind,outcome["scheme_id"],outcome["scheme_version"],outcome["code"])
    return (kind,)

def _recorded_institutional_maker_eligible(value: dict[str, Any]) -> bool:
    kind=value["kind"]
    if kind in {"actor","local_operator","unidentified_person"}:
        return True
    if kind=="descriptive_person":
        return value["description_type"]=="school_staff"
    return False

def application_errors(determination: dict[str, Any]) -> list[str]:
    errors: list[str]=[]
    if _ts(determination["updated_at"]) < _ts(determination["created_at"]):
        errors.append("updated_at precedes created_at")

    authority=determination["authority_context"]
    maker=determination["decision_maker"]
    if authority["kind"]=="teacher_local" and maker["kind"]!="local_operator":
        errors.append("teacher-local Determination requires local-operator decision-maker")
    if authority["kind"]=="recorded_institutional" and not _recorded_institutional_maker_eligible(maker):
        errors.append("decision-maker attribution is ineligible for recorded-institutional current representation")

    review_ref=determination.get("review_ref")
    if review_ref is not None:
        work=review_ref["work_ref"]
        if (work["class_id"],work["work_id"]) != (determination["class_id"],determination["work_id"]):
            errors.append("Review link belongs to different Event")

    creation=determination["creation_source"]
    if creation["type"] in {"paper_capture","import"} and determination["status"]!="proposed" and review_ref is None:
        errors.append("paper/import activation requires accepted review history")

    identities=[]
    for entry in determination.get("basis",[]):
        identities.append(_evidence_identity(entry))
        evidence=entry["evidence_ref"]
        if evidence["kind"]=="module_record":
            module=evidence["module_work_record_ref"]
            if module["work_ref"]["module_id"] != module["record_ref"]["module_id"]:
                errors.append("module basis IDs differ")
    if len(identities)!=len(set(identities)):
        errors.append("logical basis identity repeated")

    supersedes=determination.get("supersedes",[])
    if supersedes:
        predecessor_ids=[_wr_identity(entry["work_record_ref"]) for entry in supersedes]
        reasons=[entry["reason"] for entry in supersedes]
        if len(predecessor_ids)!=len(set(predecessor_ids)):
            errors.append("predecessor identity repeated")
        if len(set(reasons))!=1:
            errors.append("mixed supersession reasons")
        for entry in supersedes:
            work=entry["work_record_ref"]["work_ref"]; record=entry["work_record_ref"]["record_ref"]; reason=entry["reason"]
            same_work=(work["class_id"],work["work_id"])==(determination["class_id"],determination["work_id"])
            same_id=record["record_id"]==determination["determination_id"]
            if same_work and same_id and reason!="contract_migrated":
                errors.append("Determination replacement self-reference")
            if reason=="work_root_corrected":
                if same_work: errors.append("work-root correction requires different work")
                if not same_id: errors.append("work-root correction must preserve Determination ID")
            elif reason!="contract_migrated" and not same_work:
                errors.append("ordinary Determination correction cannot cross work roots")
            if reason in {"reconsidered","reversed_on_reconsideration"} and review_ref is None:
                errors.append("reconsideration successor requires governing Review")
        if len(set(reasons))==1:
            reason=reasons[0]
            if reason=="duplicate_consolidated" and len(set(predecessor_ids))<2:
                errors.append("duplicate consolidation needs two predecessors")
            elif reason not in {"duplicate_consolidated","contract_migrated"} and len(set(predecessor_ids))!=1:
                errors.append("ordinary correction is one-to-one")
    return errors

def review_scenario_errors(scenario: dict[str, Any]) -> list[str]:
    review=scenario["review"]; determination=scenario["determination"]; errors=[]
    review_ref=determination.get("review_ref")
    if review_ref is None or review_ref["record_ref"]["record_id"]!=review["review_id"]:
        errors.append("Determination does not resolve supplied Review")
    if (review["class_id"],review["work_id"]) != (determination["class_id"],determination["work_id"]):
        errors.append("Review belongs to different Event")
    if review["target"] != determination["target"]:
        errors.append("Determination target differs from Review target")
    if determination["status"]=="active" and (review["status"]!="active" or review["review_state"]!="completed"):
        errors.append("active linked Determination requires active completed Review")
    # Deliberately no reviewer==decision-maker rule. Review assignment and decision attribution are distinct.
    return errors

def reconsideration_scenario_errors(scenario: dict[str, Any]) -> list[str]:
    review=scenario["review"]; prior=scenario["prior_determination"]; current=scenario["determination"]
    errors=review_scenario_errors({"review":review,"determination":current})

    if review["trigger"]["kind"]!="reconsideration":
        errors.append("reconsideration Review trigger is not reconsideration")
    if review["question"]["kind"]!="reconsideration":
        errors.append("reconsideration Review question is not reconsideration")

    if (prior["class_id"],prior["work_id"]) != (current["class_id"],current["work_id"]):
        errors.append("prior Determination belongs to different Event")
    if prior["target"] != current["target"]:
        errors.append("reconsidered Determination target differs from predecessor target")

    expected_prior=(prior["class_id"],prior["work_id"],prior["determination_id"],"1")
    subjects={_wr_identity(value) for value in review.get("review_subjects",[])}
    if expected_prior not in subjects:
        errors.append("reconsideration Review does not subject the supplied prior Determination")

    supersedes=current.get("supersedes",[])
    matches=[
        entry for entry in supersedes
        if _wr_identity(entry["work_record_ref"])==expected_prior
        and entry["reason"] in {"reconsidered","reversed_on_reconsideration"}
    ]
    if len(matches)!=1:
        errors.append("reconsideration successor does not exactly replace supplied prior Determination")
    elif matches[0]["reason"]=="reversed_on_reconsideration" and _outcome_identity(current["outcome"])==_outcome_identity(prior["outcome"]):
        errors.append("reversed-on-reconsideration outcome did not change")
    return errors

class Issue16DeterminationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog,cls.store=load_validated_catalog_and_store()
        cls.validator=validator_for("determination","1",catalog=cls.catalog,store=cls.store)
        cls.review_validator=validator_for("review","1",catalog=cls.catalog,store=cls.store)
        cls.manifest=load_json(FIXTURE_ROOT/"manifest.json")
        cls.review_scenarios=load_json(FIXTURE_ROOT/"review-scenarios"/"manifest.json")
        cls.reconsideration_scenarios=load_json(FIXTURE_ROOT/"reconsideration-scenarios"/"manifest.json")

    def test_manifest_metadata(self):
        self.assertEqual((self.manifest["issue"],self.manifest["contract"],self.manifest["version"]),(16,"determination","1"))

    def test_valid_roots(self):
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value=load_json(FIXTURE_ROOT/"valid"/filename); errors=list(self.validator.iter_errors(value))
                self.assertFalse(errors,"\n".join(error.message for error in errors))
                self.assertEqual(application_errors(value),[])

    def test_structural_invalid_roots(self):
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                self.assertTrue(list(self.validator.iter_errors(load_json(FIXTURE_ROOT/"invalid"/filename))))

    def test_application_invalid_roots(self):
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value=load_json(FIXTURE_ROOT/"application-invalid"/filename); errors=list(self.validator.iter_errors(value))
                self.assertFalse(errors,"\n".join(error.message for error in errors))
                self.assertTrue(application_errors(value))

    def test_valid_review_scenarios(self):
        for filename in self.review_scenarios["valid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"review-scenarios"/"valid"/filename)
                determination_errors=list(self.validator.iter_errors(scenario["determination"]))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(determination_errors,"\n".join(error.message for error in determination_errors))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertEqual(application_errors(scenario["determination"]),[])
                self.assertEqual(review_scenario_errors(scenario),[])

    def test_application_invalid_review_scenarios(self):
        for filename in self.review_scenarios["application_invalid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"review-scenarios"/"application-invalid"/filename)
                determination_errors=list(self.validator.iter_errors(scenario["determination"]))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(determination_errors,"\n".join(error.message for error in determination_errors))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertTrue(review_scenario_errors(scenario))

    def test_valid_reconsideration_scenarios(self):
        for filename in self.reconsideration_scenarios["valid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"reconsideration-scenarios"/"valid"/filename)
                for key in ("prior_determination","determination"):
                    errors=list(self.validator.iter_errors(scenario[key]))
                    self.assertFalse(errors,"\n".join(error.message for error in errors))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertEqual(application_errors(scenario["determination"]),[])
                self.assertEqual(reconsideration_scenario_errors(scenario),[])

    def test_application_invalid_reconsideration_scenarios(self):
        for filename in self.reconsideration_scenarios["application_invalid"]:
            with self.subTest(filename=filename):
                scenario=load_json(FIXTURE_ROOT/"reconsideration-scenarios"/"application-invalid"/filename)
                for key in ("prior_determination","determination"):
                    errors=list(self.validator.iter_errors(scenario[key]))
                    self.assertFalse(errors,"\n".join(error.message for error in errors))
                review_errors=list(self.review_validator.iter_errors(scenario["review"]))
                self.assertFalse(review_errors,"\n".join(error.message for error in review_errors))
                self.assertTrue(reconsideration_scenario_errors(scenario))

    def test_catalog_and_schema_identity(self):
        entry=self.catalog["contracts"]["determination"]["1"]; self.assertEqual(entry["path"],SCHEMA_PATH)
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertEqual(schema["$id"],entry["schema_id"])
        self.assertNotIn("/latest/",schema["$id"]); self.assertNotIn("/current/",schema["$id"])

    def test_envelope_and_semantic_boundaries(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH); self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["properties"]["status"]["enum"]),{"proposed","active","invalidated","superseded"})
        forbidden={
            "student_id","student_label","finding","classification","hypothesis","response","consequence",
            "punishment","credibility","credibility_score","risk_score","automatic_determination","policy_violation",
        }
        for field in forbidden: self.assertNotIn(field,schema["properties"])

    def test_human_target_and_basis_reuse(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        self.assertEqual(schema["properties"]["target"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/targets/portia-target-ref.schema.json")
        self.assertEqual(schema["properties"]["decision_maker"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/attribution/represented-human-attribution.schema.json")
        relation=schema["$defs"]["evidenceRelation"]
        self.assertEqual(set(relation["properties"]["relation"]["enum"]),{"supporting","contrary","contextual"})
        self.assertEqual(relation["properties"]["evidence_ref"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/references/judgment-evidence-ref.schema.json")

    def test_authority_context_is_closed_and_non_authenticating(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        authority=schema["$defs"]
        self.assertEqual(set(authority["teacherLocalAuthority"]["properties"]["scope"]["enum"]),{"classroom_management","teacher_review","teacher_support_coordination","other"})
        self.assertEqual(set(authority["recordedInstitutionalAuthority"]["properties"]["authority_status"]["enum"]),{"documented_basis","asserted","unknown"})
        self.assertEqual(authority["recordedInstitutionalAuthority"]["properties"]["authority_basis"]["items"]["$ref"],"https://paper-data-suite.github.io/pds-portia/schemas/v1/provenance/source-artifact-ref.schema.json")

    def test_process_basis_is_separate_from_authority(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        identified=schema["$defs"]["identifiedProcessBasis"]
        self.assertEqual(set(identified["properties"]),{"kind","policy","process"})
        self.assertEqual(schema["$defs"]["teacherLocalProcessBasis"]["properties"]["kind"]["const"],"teacher_local")
        self.assertEqual(schema["$defs"]["unknownProcessBasis"]["properties"]["kind"]["const"],"unknown")

    def test_outcome_union_is_closed_and_preserves_uncertainty(self):
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        outcome=schema["$defs"]["determinationOutcome"]["oneOf"]
        self.assertEqual(len(outcome),5)
        self.assertEqual(schema["$defs"]["conclusion"]["properties"]["kind"]["const"],"conclusion")
        self.assertEqual(schema["$defs"]["codedConclusion"]["properties"]["kind"]["const"],"coded_conclusion")
        for kind in ("insufficient_information","unable_to_determine","not_applicable"):
            self.assertEqual(schema["$defs"][kind]["properties"]["kind"]["const"],kind)

    def test_coded_outcome_identity_is_versioned(self):
        coded=load_json(REPO_ROOT/SCHEMA_PATH)["$defs"]["codedConclusion"]
        self.assertEqual(set(coded["required"]),{"kind","scheme_id","scheme_version","code","label","definition_text"})
        valid=load_json(FIXTURE_ROOT/"valid"/"teacher-local-coded-conclusion.json")
        self.assertEqual(_outcome_identity(valid["outcome"])[:1],("coded_conclusion",))

    def test_decision_maker_role_eligibility_is_application_level(self):
        teacher=load_json(FIXTURE_ROOT/"valid"/"teacher-local-conclusion.json")
        institutional=load_json(FIXTURE_ROOT/"valid"/"recorded-institutional-documented-basis.json")
        self.assertEqual(teacher["decision_maker"]["kind"],"local_operator")
        self.assertIn(institutional["decision_maker"]["kind"],{"actor","local_operator","descriptive_person","unidentified_person"})
        self.assertEqual(application_errors(teacher),[])
        self.assertEqual(application_errors(institutional),[])

    def test_lifecycle_and_reason_inventory_matches_adr(self):
        self.assertEqual(DETERMINATION_LIFECYCLE["active"],{"invalidated","superseded"})
        self.assertEqual(LIFECYCLE_REASONS,{
            "judgment_recorded","recording_error","wrong_decision_maker","wrong_target","wrong_authority",
            "wrong_process_basis","invalid_provenance","prohibited_payload","corrected_by_successor",
            "duplicate_consolidated","work_root_corrected","contract_migrated","other",
        })
        self.assertEqual(SUPERSESSION_REASONS,{
            "outcome_corrected","question_corrected","decision_maker_corrected","target_corrected",
            "authority_corrected","process_basis_corrected","reconsidered","reversed_on_reconsideration",
            "duplicate_consolidated","work_root_corrected","contract_migrated","other",
        })
        schema=load_json(REPO_ROOT/SCHEMA_PATH)
        self.assertEqual(set(schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]),SUPERSESSION_REASONS)

    def test_no_parallel_determination_shared_contracts(self):
        names=set(self.catalog["contracts"])
        for name in (
            "determination_dependency","determination_amendment","determination_operation_journal",
            "determination_quarantine","determination_integrity_finding","determination_authority_registry",
            "determination_policy_registry","determination_risk_score",
        ):
            self.assertNotIn(name,names)

if __name__ == "__main__": unittest.main()
