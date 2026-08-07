from __future__ import annotations

from datetime import date, datetime
from typing import Any
import unittest

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-15"
    / "account"
)

ACCOUNT_SCHEMA_PATH = "schemas/v1/accounts/account.schema.json"

ACCOUNT_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"retracted", "invalidated", "superseded"},
    "retracted": {"superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

ACCOUNT_LIFECYCLE_REASONS = {
    "review_completed",
    "source_retracted",
    "recording_error",
    "wrong_source",
    "wrong_target",
    "invalid_provenance",
    "prohibited_payload",
    "corrected_by_successor",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}

QUALIFYING_REPORTED_SOURCE_KINDS = {
    "roster_student",
    "actor",
    "local_operator",
    "descriptive_person",
}


def _parse_offset(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _source_identity(source: dict[str, Any]) -> tuple[Any, ...]:
    kind = source["kind"]
    if kind == "roster_student":
        ref = source["roster_student_ref"]
        return (kind, ref["class_id"], ref["student_id"])
    if kind == "actor":
        return (kind, source["actor_ref"]["actor_id"])
    if kind == "local_operator":
        return (kind, source["display_label"])
    if kind == "descriptive_person":
        return (
            kind,
            source["description_type"],
            source["display_label"],
        )
    return (
        kind,
        source.get("identity_status"),
        source.get("display_label"),
    )


def _account_ref_identity(
    account_ref: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        account_ref["record_kind"],
        account_ref["record_id"],
        account_ref["contract_version"],
    )


def _work_record_identity(
    work_record_ref: dict[str, Any],
) -> tuple[str, str, str, str]:
    work_ref = work_record_ref["work_ref"]
    record_ref = work_record_ref["record_ref"]
    return (
        work_ref["class_id"],
        work_ref["work_id"],
        record_ref["record_id"],
        record_ref["contract_version"],
    )


def _provided_time_after_created(account: dict[str, Any]) -> bool:
    provided = account["provided_time"]
    created = _parse_offset(account["created_at"])
    precision = provided["precision"]
    if precision == "exact":
        return _parse_offset(provided["at"]) > created
    if precision == "range":
        return _parse_offset(provided["ended_at"]) > created
    if precision == "date_only":
        return date.fromisoformat(provided["date"]) > created.date()
    if precision == "approximate" and provided["approximation"] == "about":
        return _parse_offset(provided["at"]) > created
    return False


def application_errors(account: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if _parse_offset(account["updated_at"]) < _parse_offset(
        account["created_at"]
    ):
        errors.append("updated_at precedes created_at")

    if _provided_time_after_created(account):
        errors.append("provided time follows record creation")

    creation = account["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and account["status"] != "proposed"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    relations = account.get("related_accounts", [])
    relation_ids: list[tuple[str, str, str]] = []
    for relation in relations:
        identity = _account_ref_identity(relation["account_ref"])
        relation_ids.append(identity)
        if relation["account_ref"]["record_id"] == account["account_id"]:
            errors.append("Account relation self-reference")
        if (
            relation["relation"] == "reports_from"
            and account["information_origin"]
            not in {"secondhand", "mixed"}
        ):
            errors.append(
                "reports_from requires secondhand or mixed origin"
            )
        if (
            relation["relation"] == "retracts"
            and account["status"] != "active"
        ):
            errors.append("retraction Account must be active")

    if len(relation_ids) != len(set(relation_ids)):
        errors.append("related Account identity repeated")

    supersedes = account.get("supersedes", [])
    if supersedes:
        identities = [
            _work_record_identity(entry["work_record_ref"])
            for entry in supersedes
        ]
        reasons = [entry["reason"] for entry in supersedes]

        if len(identities) != len(set(identities)):
            errors.append("predecessor Account identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        for entry in supersedes:
            work_ref = entry["work_record_ref"]["work_ref"]
            record_ref = entry["work_record_ref"]["record_ref"]
            same_work = (
                work_ref["class_id"] == account["class_id"]
                and work_ref["work_id"] == account["work_id"]
            )
            same_id = record_ref["record_id"] == account["account_id"]
            reason = entry["reason"]

            if same_work and same_id and reason != "contract_migrated":
                errors.append("Account replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append(
                        "work-root correction requires different work"
                    )
                if not same_id:
                    errors.append(
                        "work-root correction must preserve Account ID"
                    )
            elif reason != "contract_migrated" and not same_work:
                errors.append(
                    "ordinary Account correction cannot cross work roots"
                )

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two predecessors"
                    )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        "non-consolidation correction is one-to-one"
                    )

    return errors


def _participant_ids(target: dict[str, Any]) -> set[str]:
    if target["kind"] == "event_participant":
        return {target["record_ref"]["record_id"]}
    if target["kind"] == "event_participants":
        return {
            item["record_ref"]["record_id"]
            for item in target["targets"]
        }
    return set()


def reported_involved_errors(
    account: dict[str, Any],
    role: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if role["role_type"] != "reported_involved":
        return ["scenario role is not reported_involved"]
    if role["status"] != "active":
        return ["scenario role is not active"]

    account_basis_ids = {
        entry["record_ref"]["record_id"]
        for entry in role.get("basis", [])
        if entry["kind"] == "account_ref"
    }
    if account["account_id"] not in account_basis_ids:
        errors.append("Role does not reference supplied Account")

    if account["work_id"] != role["work_id"]:
        errors.append("Account and Role belong to different Events")

    if account["status"] != "active":
        errors.append("Account is not eligible for current use")

    if account["source"]["kind"] not in QUALIFYING_REPORTED_SOURCE_KINDS:
        errors.append(
            "Account source attribution does not qualify for active Role"
        )

    role_participant = role["target"]["record_ref"]["record_id"]
    account_participants = _participant_ids(account["target"])
    if role_participant not in account_participants:
        errors.append(
            "Account target does not include reported-involved Participant"
        )

    return errors


def retraction_errors(scenario: dict[str, Any]) -> list[str]:
    predecessor = scenario["predecessor"]
    retraction = scenario["retraction_account"]
    transition = scenario["coordinated_transition"]
    errors: list[str] = []

    if predecessor["work_id"] != retraction["work_id"]:
        errors.append("retraction Accounts belong to different Events")

    if _source_identity(predecessor["source"]) != _source_identity(
        retraction["source"]
    ):
        errors.append("retraction represented source differs")

    if retraction["status"] != "active":
        errors.append("retraction Account is not active")

    if predecessor["status"] != "active":
        errors.append("retracted predecessor is not active")

    retract_ids = {
        item["account_ref"]["record_id"]
        for item in retraction.get("related_accounts", [])
        if item["relation"] == "retracts"
    }
    if predecessor["account_id"] not in retract_ids:
        errors.append(
            "retraction Account does not exactly retract predecessor"
        )

    if (
        transition["from_status"] != "active"
        or transition["to_status"] != "retracted"
        or transition["reason"] != "source_retracted"
    ):
        errors.append("coordinated lifecycle transition is not retraction")

    return errors


class Issue15AccountContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "account",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.role_validator = validator_for(
            "event_participant_role",
            "3",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 15)
        self.assertEqual(self.manifest["contract"], "account")
        self.assertEqual(self.manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertTrue(application_errors(value))

    def test_account_is_cataloged_at_immutable_path(self) -> None:
        entry = self.catalog["contracts"]["account"]["1"]
        self.assertEqual(entry["path"], ACCOUNT_SCHEMA_PATH)
        self.assertEqual(
            entry["schema_id"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/"
                + ACCOUNT_SCHEMA_PATH
            ),
        )
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertNotIn("/latest/", entry["schema_id"])
        self.assertNotIn("/current/", entry["schema_id"])

    def test_account_envelope_is_closed_and_event_local(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "class_id",
                "work_id",
                "account_id",
                "status",
                "target",
                "source",
                "information_origin",
                "source_certainty",
                "content",
                "provided_time",
                "creation_source",
                "created_at",
                "created_by",
                "updated_at",
                "updated_by",
            },
        )
        self.assertEqual(
            schema["properties"]["record_type"]["const"],
            "account",
        )
        self.assertEqual(
            schema["properties"]["module_id"]["const"],
            "portia",
        )
        for forbidden in (
            "finding",
            "classification",
            "hypothesis",
            "determination",
            "credibility",
            "credibility_score",
            "reliability",
            "severity",
            "risk_score",
            "policy_violation",
            "diagnosis",
            "intent",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_account_status_and_source_semantics_are_closed(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {
                "proposed",
                "active",
                "retracted",
                "invalidated",
                "superseded",
            },
        )
        self.assertEqual(
            set(schema["properties"]["information_origin"]["enum"]),
            {"firsthand", "secondhand", "mixed", "unknown"},
        )
        self.assertEqual(
            set(schema["properties"]["source_certainty"]["enum"]),
            {
                "stated_certain",
                "stated_uncertain",
                "mixed_or_qualified",
                "not_recorded",
            },
        )

    def test_content_keeps_quote_and_summary_distinct(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        segment = schema["$defs"]["contentSegment"]
        self.assertFalse(segment["additionalProperties"])
        self.assertEqual(
            set(segment["properties"]["representation"]["enum"]),
            {"verbatim_quote", "recorded_summary"},
        )
        self.assertEqual(
            set(segment["required"]),
            {"representation", "text"},
        )

    def test_account_relations_use_exact_same_family_refs(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        relation = schema["$defs"]["accountRelation"]
        self.assertEqual(
            set(relation["properties"]["relation"]["enum"]),
            {"reports_from", "clarifies", "retracts"},
        )
        exact = schema["$defs"]["exactAccountRef"]
        constrained = exact["allOf"][1]["properties"]
        self.assertEqual(constrained["record_kind"]["const"], "account")
        self.assertEqual(constrained["contract_version"]["const"], "1")

    def test_account_has_no_in_place_amendment_surface(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        for forbidden in (
            "amendable_paths",
            "amendment",
            "nonmaterial_metadata",
        ):
            self.assertNotIn(forbidden, schema["properties"])
        self.assertIn(
            "portia.account.amendment_prohibited_v1",
            schema["x-portia-application-invariants"],
        )

    def test_paper_preallocation_is_structurally_prohibited(self) -> None:
        value = load_json(
            FIXTURE_ROOT / "invalid" / "paper-preallocated.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_lifecycle_matrix_matches_adr_0011(self) -> None:
        self.assertEqual(
            ACCOUNT_LIFECYCLE,
            {
                "proposed": {"active", "invalidated", "superseded"},
                "active": {"retracted", "invalidated", "superseded"},
                "retracted": {"superseded"},
                "invalidated": {"superseded"},
                "superseded": set(),
            },
        )

    def test_lifecycle_reason_inventory_matches_adr_0011(self) -> None:
        self.assertEqual(
            ACCOUNT_LIFECYCLE_REASONS,
            {
                "review_completed",
                "source_retracted",
                "recording_error",
                "wrong_source",
                "wrong_target",
                "invalid_provenance",
                "prohibited_payload",
                "corrected_by_successor",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            },
        )
        self.assertIn(
            "retracted",
            ACCOUNT_LIFECYCLE["active"],
        )
        self.assertNotIn(
            "retracted",
            ACCOUNT_LIFECYCLE["proposed"],
        )
        self.assertNotIn(
            "active",
            ACCOUNT_LIFECYCLE["retracted"],
        )

    def test_reported_involved_compatibility_scenarios(self) -> None:
        manifest = load_json(
            FIXTURE_ROOT / "role-compatibility" / "manifest.json"
        )

        for filename in manifest["valid"]:
            with self.subTest(valid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "role-compatibility"
                    / "valid"
                    / filename
                )
                account_errors = list(
                    self.validator.iter_errors(scenario["account"])
                )
                role_errors = list(
                    self.role_validator.iter_errors(scenario["role"])
                )
                self.assertFalse(
                    account_errors,
                    "\n".join(e.message for e in account_errors),
                )
                self.assertFalse(
                    role_errors,
                    "\n".join(e.message for e in role_errors),
                )
                self.assertEqual(
                    reported_involved_errors(
                        scenario["account"],
                        scenario["role"],
                    ),
                    [],
                )

        for filename in manifest["application_invalid"]:
            with self.subTest(application_invalid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "role-compatibility"
                    / "application-invalid"
                    / filename
                )
                self.assertFalse(
                    list(
                        self.validator.iter_errors(
                            scenario["account"]
                        )
                    )
                )
                self.assertFalse(
                    list(
                        self.role_validator.iter_errors(
                            scenario["role"]
                        )
                    )
                )
                self.assertTrue(
                    reported_involved_errors(
                        scenario["account"],
                        scenario["role"],
                    )
                )

    def test_source_evidenced_retraction_scenarios(self) -> None:
        manifest = load_json(
            FIXTURE_ROOT / "retraction" / "manifest.json"
        )

        for filename in manifest["valid"]:
            with self.subTest(valid=filename):
                scenario = load_json(
                    FIXTURE_ROOT / "retraction" / "valid" / filename
                )
                self.assertFalse(
                    list(
                        self.validator.iter_errors(
                            scenario["predecessor"]
                        )
                    )
                )
                self.assertFalse(
                    list(
                        self.validator.iter_errors(
                            scenario["retraction_account"]
                        )
                    )
                )
                self.assertEqual(retraction_errors(scenario), [])

        for filename in manifest["application_invalid"]:
            with self.subTest(application_invalid=filename):
                scenario = load_json(
                    FIXTURE_ROOT
                    / "retraction"
                    / "application-invalid"
                    / filename
                )
                self.assertFalse(
                    list(
                        self.validator.iter_errors(
                            scenario["predecessor"]
                        )
                    )
                )
                self.assertFalse(
                    list(
                        self.validator.iter_errors(
                            scenario["retraction_account"]
                        )
                    )
                )
                self.assertTrue(retraction_errors(scenario))

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_SCHEMA_PATH)
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            {
                "portia.account.canonical_storage_scope",
                "portia.account.path_identity_agreement",
                "portia.account.parent_event_resolution",
                "portia.account.target_resolution",
                "portia.account.target_same_event",
                "portia.account.source_resolution",
                "portia.account.source_recorder_distinction",
                "portia.account.timestamp_chronology",
                "portia.account.provided_time_chronology",
                "portia.account.creation_provenance_immutable",
                "portia.account.paper_provenance_agreement",
                "portia.account.paper_activation_requires_review_history",
                "portia.account.import_activation_requires_review_history",
                "portia.account.information_origin_consistency",
                "portia.account.source_lineage_resolution",
                "portia.account.relation_same_event",
                "portia.account.relation_target_identity_unique",
                "portia.account.relation_self_reference",
                "portia.account.clarification_same_source",
                "portia.account.retraction_same_source",
                (
                    "portia.account."
                    "retraction_requires_active_retraction_account"
                ),
                "portia.account.retraction_predecessor_eligibility",
                "portia.account.retraction_lifecycle_coordination",
                "portia.account.lifecycle_matrix",
                "portia.account.lifecycle_history_reconciliation",
                "portia.account.current_use_eligibility",
                "portia.account.amendment_prohibited_v1",
                "portia.account.predecessor_resolution",
                "portia.account.predecessor_identity_unique",
                "portia.account.self_supersession",
                "portia.account.supersession_reason_uniform",
                "portia.account.replacement_topology",
                "portia.account.supersession_cycle",
                "portia.account.ownership_reconciliation",
                "portia.account.successor_effectiveness",
                "portia.account.incoming_reference_complete",
                "portia.account.no_silent_successor_following",
                (
                    "portia.account."
                    "reported_involved_source_eligibility"
                ),
                (
                    "portia.account."
                    "reported_involved_target_alignment"
                ),
                "portia.account.source_artifact_resolution",
                "portia.account.external_reference_inert",
                "portia.account.no_automatic_finding",
            },
        )


if __name__ == "__main__":
    unittest.main()
