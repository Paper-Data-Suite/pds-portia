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
    / "issue-19"
)
ACCOUNT_ROOT = FIXTURE_ROOT / "account-v2"
OBSERVATION_ROOT = FIXTURE_ROOT / "observation-v2"

ACCOUNT_V1_PATH = "schemas/v1/accounts/account.schema.json"
ACCOUNT_V2_PATH = "schemas/v2/accounts/account.schema.json"
OBSERVATION_V1_PATH = (
    "schemas/v1/observations/observation.schema.json"
)
OBSERVATION_V2_PATH = (
    "schemas/v2/observations/observation.schema.json"
)

EVENT_TARGET_KINDS = {
    "event",
    "event_participant",
    "event_participants",
}
SUPPORT_TARGET_KINDS = {
    "support_process",
    "support_process_participant",
    "support_process_participants",
}


def _parse_offset(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _evidence_time_after_created(
    evidence_time: dict[str, Any],
    created_at: str,
) -> bool:
    created = _parse_offset(created_at)
    precision = evidence_time["precision"]
    if precision == "exact":
        return _parse_offset(evidence_time["at"]) > created
    if precision == "range":
        return _parse_offset(evidence_time["ended_at"]) > created
    if precision == "date_only":
        return date.fromisoformat(evidence_time["date"]) > created.date()
    if (
        precision == "approximate"
        and evidence_time["approximation"] == "about"
    ):
        return _parse_offset(evidence_time["at"]) > created
    return False


def _work_identity(value: dict[str, Any]) -> tuple[str, str, str]:
    return (
        value["class_id"],
        value["work_kind"],
        value["work_id"],
    )


def _work_ref_identity(
    work_ref: dict[str, Any],
) -> tuple[str, str, str]:
    return (
        work_ref["class_id"],
        work_ref["work_kind"],
        work_ref["work_id"],
    )


def _predecessor_identity(
    work_record_ref: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    work_ref = work_record_ref["work_ref"]
    record_ref = work_record_ref["record_ref"]
    return (
        work_ref["class_id"],
        work_ref["work_kind"],
        work_ref["work_id"],
        record_ref["record_id"],
        record_ref["contract_version"],
    )


def _owner_errors(
    value: dict[str, Any],
    *,
    resolved_event_owners: set[tuple[str, str]] | None = None,
    resolved_support_process_owners: set[tuple[str, str]] | None = None,
) -> list[str]:
    errors: list[str] = []
    identity = (value["class_id"], value["work_id"])
    kind = value["work_kind"]

    if (
        kind == "event"
        and resolved_event_owners is not None
        and identity not in resolved_event_owners
    ):
        errors.append("Event owner does not resolve")
    if (
        kind == "support_process"
        and resolved_support_process_owners is not None
        and identity not in resolved_support_process_owners
    ):
        errors.append("Support Process owner does not resolve")

    target_kind = value["target"]["kind"]
    if kind == "event" and target_kind not in EVENT_TARGET_KINDS:
        errors.append("Event owner requires Event-local target")
    if (
        kind == "support_process"
        and target_kind not in SUPPORT_TARGET_KINDS
    ):
        errors.append(
            "Support Process owner requires Support-Process-local target"
        )
    return errors


def _supersession_errors(
    value: dict[str, Any],
    *,
    record_id_field: str,
    family_label: str,
) -> list[str]:
    errors: list[str] = []
    supersedes = value.get("supersedes", [])
    if not supersedes:
        return errors

    identities = [
        _predecessor_identity(entry["work_record_ref"])
        for entry in supersedes
    ]
    reasons = [entry["reason"] for entry in supersedes]
    if len(identities) != len(set(identities)):
        errors.append(f"predecessor {family_label} identity repeated")
    if len(set(reasons)) != 1:
        errors.append("mixed supersession reasons")

    current_work = _work_identity(value)
    current_id = value[record_id_field]

    for entry in supersedes:
        ref = entry["work_record_ref"]
        work_ref = ref["work_ref"]
        record_ref = ref["record_ref"]
        predecessor_work = _work_ref_identity(work_ref)
        same_work = predecessor_work == current_work
        same_id = record_ref["record_id"] == current_id
        predecessor_version = record_ref["contract_version"]
        reason = entry["reason"]

        if (
            predecessor_version == "1"
            and work_ref["work_kind"] == "support_process"
        ):
            errors.append(
                f"{family_label} v1 cannot have Support Process ownership"
            )

        if reason == "contract_migrated":
            if predecessor_version != "1":
                errors.append(
                    "contract_migrated requires a v1 predecessor"
                )
            if not same_work:
                errors.append(
                    "contract migration must preserve work root"
                )
            if not same_id:
                errors.append(
                    f"contract migration must preserve {family_label} ID"
                )
            continue

        if same_work and same_id:
            errors.append(f"{family_label} replacement self-reference")

        if reason == "work_root_corrected":
            if same_work:
                errors.append(
                    "work-root correction requires different work"
                )
            if not same_id:
                errors.append(
                    f"work-root correction must preserve {family_label} ID"
                )
        elif not same_work:
            errors.append(
                f"ordinary {family_label} correction cannot cross work roots"
            )

    if len(set(reasons)) == 1:
        reason = reasons[0]
        if reason == "duplicate_consolidated":
            if len(set(identities)) < 2:
                errors.append(
                    "duplicate consolidation needs two predecessors"
                )
        elif reason not in {"contract_migrated"}:
            if len(set(identities)) != 1:
                errors.append(
                    "non-consolidation correction is one-to-one"
                )

    return errors


def account_application_errors(
    account: dict[str, Any],
    *,
    resolved_event_owners: set[tuple[str, str]] | None = None,
    resolved_support_process_owners: set[tuple[str, str]] | None = None,
) -> list[str]:
    errors = _owner_errors(
        account,
        resolved_event_owners=resolved_event_owners,
        resolved_support_process_owners=resolved_support_process_owners,
    )

    if _parse_offset(account["updated_at"]) < _parse_offset(
        account["created_at"]
    ):
        errors.append("updated_at precedes created_at")

    if _evidence_time_after_created(
        account["provided_time"],
        account["created_at"],
    ):
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
        ref = relation["account_ref"]
        identity = (
            ref["record_kind"],
            ref["record_id"],
            ref["contract_version"],
        )
        relation_ids.append(identity)

        if ref["record_id"] == account["account_id"]:
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
        if (
            account["work_kind"] == "support_process"
            and ref["contract_version"] == "1"
        ):
            errors.append(
                "Support Process local Account relation cannot reference "
                "Event-local Account v1"
            )

    if len(relation_ids) != len(set(relation_ids)):
        errors.append("related Account identity repeated")

    errors.extend(
        _supersession_errors(
            account,
            record_id_field="account_id",
            family_label="Account",
        )
    )
    return errors


def _measurement_types(
    observation: dict[str, Any],
) -> set[str]:
    return {
        item["measure_type"]
        for item in observation["content"].get("measurements", [])
    }


def observation_application_errors(
    observation: dict[str, Any],
    *,
    resolved_event_owners: set[tuple[str, str]] | None = None,
    resolved_support_process_owners: set[tuple[str, str]] | None = None,
) -> list[str]:
    errors = _owner_errors(
        observation,
        resolved_event_owners=resolved_event_owners,
        resolved_support_process_owners=resolved_support_process_owners,
    )

    if _parse_offset(observation["updated_at"]) < _parse_offset(
        observation["created_at"]
    ):
        errors.append("updated_at precedes created_at")

    if _evidence_time_after_created(
        observation["observation_time"],
        observation["created_at"],
    ):
        errors.append("observation time follows record creation")

    creation = observation["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and observation["status"] != "proposed"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    observer_kind = observation["observer"]["kind"]
    method = observation["method"]
    if observer_kind == "instrument" and method != "instrumented":
        errors.append(
            "instrument observer requires instrumented method"
        )
    if observer_kind == "human" and method == "instrumented":
        errors.append(
            "instrumented method requires instrument observer"
        )

    measure_types = _measurement_types(observation)
    if method == "manual_count" and not (
        {"count", "percentage"} & measure_types
    ):
        errors.append(
            "manual_count requires count or percentage measurement"
        )
    if method == "manual_timing" and not (
        {"duration", "latency"} & measure_types
    ):
        errors.append(
            "manual_timing requires duration or latency measurement"
        )
    if (
        method == "artifact_review"
        and not observation.get("source_artifacts")
    ):
        errors.append("artifact_review requires source artifact")

    errors.extend(
        _supersession_errors(
            observation,
            record_id_field="observation_id",
            family_label="Observation",
        )
    )
    return errors


class Issue19AccountV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "account",
            "2",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(ACCOUNT_ROOT / "manifest.json")

    def test_manifest_and_catalog(self) -> None:
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(self.manifest["contract"], "account")
        self.assertEqual(self.manifest["version"], "2")
        self.assertEqual(
            self.catalog["contracts"]["account"]["2"]["path"],
            ACCOUNT_V2_PATH,
        )
        schema = load_json(REPO_ROOT / ACCOUNT_V2_PATH)
        self.assertEqual(
            schema["$id"],
            "https://paper-data-suite.github.io/pds-portia/"
            + ACCOUNT_V2_PATH,
        )

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(ACCOUNT_ROOT / "valid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    account_application_errors(value),
                    [],
                )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(ACCOUNT_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.validator.iter_errors(value)),
                    f"{filename} unexpectedly passed",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    ACCOUNT_ROOT / "application-invalid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertTrue(account_application_errors(value))

    def test_v1_is_immutable_and_v2_is_dual_owner(self) -> None:
        v1 = load_json(REPO_ROOT / ACCOUNT_V1_PATH)
        v2 = load_json(REPO_ROOT / ACCOUNT_V2_PATH)

        self.assertEqual(
            v1["properties"]["schema_version"],
            {"const": "1"},
        )
        self.assertNotIn("work_kind", v1["properties"])
        self.assertIn(
            "portia-event-id.schema.json",
            v1["properties"]["work_id"]["$ref"],
        )
        self.assertIn(
            "portia-target-ref.schema.json",
            v1["properties"]["target"]["$ref"],
        )

        self.assertEqual(
            v2["properties"]["schema_version"],
            {"const": "2"},
        )
        self.assertEqual(
            set(v2["properties"]["work_kind"]["enum"]),
            {"event", "support_process"},
        )
        self.assertIn("work_kind", v2["required"])
        self.assertFalse(v2["additionalProperties"])

    def test_owner_conditioned_targeting_and_resolution(self) -> None:
        event_value = load_json(
            ACCOUNT_ROOT / "valid" / "event-active.json"
        )
        support_value = load_json(
            ACCOUNT_ROOT / "valid" / "support-process-active.json"
        )

        self.assertEqual(
            account_application_errors(
                event_value,
                resolved_event_owners={
                    (
                        event_value["class_id"],
                        event_value["work_id"],
                    )
                },
            ),
            [],
        )
        self.assertTrue(
            account_application_errors(
                event_value,
                resolved_event_owners=set(),
            )
        )
        self.assertEqual(
            account_application_errors(
                support_value,
                resolved_support_process_owners={
                    (
                        support_value["class_id"],
                        support_value["work_id"],
                    )
                },
            ),
            [],
        )
        self.assertTrue(
            account_application_errors(
                support_value,
                resolved_support_process_owners=set(),
            )
        )

    def test_cross_version_history_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_V2_PATH)
        local_version = schema["$defs"]["exactAccountRef"]["allOf"][1][
            "properties"
        ]["contract_version"]
        predecessor_version = schema["$defs"]["accountWorkRecordRef"][
            "allOf"
        ][1]["properties"]["record_ref"]["allOf"][1]["properties"][
            "contract_version"
        ]
        self.assertEqual(local_version, {"enum": ["1", "2"]})
        self.assertEqual(predecessor_version, {"enum": ["1", "2"]})

    def test_account_remains_source_evidence_not_outcome(self) -> None:
        schema = load_json(REPO_ROOT / ACCOUNT_V2_PATH)
        for forbidden in (
            "outcome",
            "progress",
            "effectiveness",
            "caused_by",
            "causal_effect",
            "risk_score",
            "credibility_score",
            "grade",
        ):
            self.assertNotIn(forbidden, schema["properties"])


class Issue19ObservationV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "observation",
            "2",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(
            OBSERVATION_ROOT / "manifest.json"
        )

    def test_manifest_and_catalog(self) -> None:
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(self.manifest["contract"], "observation")
        self.assertEqual(self.manifest["version"], "2")
        self.assertEqual(
            self.catalog["contracts"]["observation"]["2"]["path"],
            OBSERVATION_V2_PATH,
        )
        schema = load_json(REPO_ROOT / OBSERVATION_V2_PATH)
        self.assertEqual(
            schema["$id"],
            "https://paper-data-suite.github.io/pds-portia/"
            + OBSERVATION_V2_PATH,
        )

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    OBSERVATION_ROOT / "valid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    observation_application_errors(value),
                    [],
                )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    OBSERVATION_ROOT / "invalid" / filename
                )
                self.assertTrue(
                    list(self.validator.iter_errors(value)),
                    f"{filename} unexpectedly passed",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    OBSERVATION_ROOT
                    / "application-invalid"
                    / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertTrue(
                    observation_application_errors(value)
                )

    def test_v1_is_immutable_and_v2_is_dual_owner(self) -> None:
        v1 = load_json(REPO_ROOT / OBSERVATION_V1_PATH)
        v2 = load_json(REPO_ROOT / OBSERVATION_V2_PATH)

        self.assertEqual(
            v1["properties"]["schema_version"],
            {"const": "1"},
        )
        self.assertNotIn("work_kind", v1["properties"])
        self.assertIn(
            "portia-event-id.schema.json",
            v1["properties"]["work_id"]["$ref"],
        )
        self.assertEqual(
            v2["properties"]["schema_version"],
            {"const": "2"},
        )
        self.assertEqual(
            set(v2["properties"]["work_kind"]["enum"]),
            {"event", "support_process"},
        )
        self.assertIn("work_kind", v2["required"])
        self.assertFalse(v2["additionalProperties"])

    def test_support_process_measurement_needs_no_event(self) -> None:
        value = load_json(
            OBSERVATION_ROOT
            / "valid"
            / "support-process-manual-count.json"
        )
        self.assertEqual(value["work_kind"], "support_process")
        self.assertTrue(value["work_id"].startswith("sup_"))
        self.assertNotIn("event_id", value)
        self.assertEqual(
            observation_application_errors(
                value,
                resolved_support_process_owners={
                    (value["class_id"], value["work_id"])
                },
            ),
            [],
        )

    def test_cross_version_history_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / OBSERVATION_V2_PATH)
        predecessor_version = schema["$defs"][
            "observationWorkRecordRef"
        ]["allOf"][1]["properties"]["record_ref"]["allOf"][1][
            "properties"
        ]["contract_version"]
        self.assertEqual(
            predecessor_version,
            {"enum": ["1", "2"]},
        )

    def test_measurement_semantics_are_preserved_not_outcome_fields(self) -> None:
        v1 = load_json(REPO_ROOT / OBSERVATION_V1_PATH)
        v2 = load_json(REPO_ROOT / OBSERVATION_V2_PATH)
        self.assertEqual(
            v2["$defs"]["measurement"],
            v1["$defs"]["measurement"],
        )
        for forbidden in (
            "outcome",
            "progress",
            "effectiveness",
            "caused_by",
            "causal_effect",
            "risk_score",
            "grade",
        ):
            self.assertNotIn(forbidden, v2["properties"])


if __name__ == "__main__":
    unittest.main()
