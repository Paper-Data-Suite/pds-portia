from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
    / "issue-14"
    / "actor-aware-operations"
)

FAMILIES = {
    "integrity-finding": "integrity_finding",
    "operation-journal": "operation_journal",
    "operation-lock": "operation_lock",
    "quarantine-record": "quarantine_record",
}

SCHEMA_PATHS = {
    "integrity_finding": (
        "schemas/v2/projections/integrity-finding.schema.json"
    ),
    "operation_journal": (
        "schemas/v2/operations/operation-journal.schema.json"
    ),
    "operation_lock": (
        "schemas/v2/operations/operation-lock.schema.json"
    ),
    "quarantine_record": (
        "schemas/v2/operations/quarantine-record.schema.json"
    ),
}

SENSITIVE_TOKENS = {
    "contact_value",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "display_name",
    "student_name",
    "relationship_narrative",
    "removed_payload",
}


def actor_refs_from_target(
    target: dict[str, Any],
) -> list[dict[str, str]]:
    if target.get("kind") == "actor_set":
        return target["actor_refs"]
    return []


def actor_set_errors(
    target: dict[str, Any],
) -> list[str]:
    refs = actor_refs_from_target(target)
    if not refs:
        return []

    errors: list[str] = []
    ordered = sorted(
        refs,
        key=lambda item: (
            item["actor_id"],
            item["contract_version"],
        ),
    )
    if refs != ordered:
        errors.append("Actor set is not deterministically sorted")

    actor_ids = [item["actor_id"] for item in refs]
    if len(actor_ids) != len(set(actor_ids)):
        errors.append(
            "Actor set repeats one logical Actor across versions"
        )
    return errors


def actor_directory_ref_version(
    target: dict[str, Any],
) -> str | None:
    if target.get("kind") != "actor_directory_record":
        return None
    exact = target["actor_directory_record_ref"]
    kind = exact["kind"]
    if kind == "actor":
        return exact["actor_ref"]["contract_version"]
    if kind == "actor_contact_point":
        return exact["contact_point_ref"]["contract_version"]
    if kind == "actor_student_relationship":
        return exact["relationship_ref"]["contract_version"]
    return exact["collision_ref"]["contract_version"]


def contains_actor_target(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("kind") in {
            "actor_directory_record",
            "actor_set",
            "actor_directory_collection",
        }:
            return True
        return any(contains_actor_target(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_actor_target(item) for item in value)
    return False


def iter_targets(value: Any):
    if isinstance(value, dict):
        if value.get("kind") in {
            "actor_directory_record",
            "actor_set",
            "actor_directory_collection",
        }:
            yield value
        for child in value.values():
            yield from iter_targets(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_targets(child)


def sensitive_name(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in SENSITIVE_TOKENS
        or "contact_value" in lowered
        or "display_name" in lowered
        or "student_name" in lowered
    )


def integrity_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = [value["primary_target"], *value["related_targets"]]
    for target in targets:
        errors.extend(actor_set_errors(target))
        version = actor_directory_ref_version(target)
        if version is not None and version != "1":
            errors.append("unsupported Actor target version")

    if value["code"] == "actor_duplicate_candidate":
        if value["assessment"]["result"] != "indeterminate":
            errors.append("duplicate candidate represented as confirmed")
        if value["severity"] not in {"advisory", "warning"}:
            errors.append("duplicate candidate severity is excessive")
        prohibited = {
            "block_current_use",
            "block_lifecycle_writes",
            "block_operation_completion",
            "block_work_writes",
            "block_class_writes",
            "quarantine_target",
        }
        if prohibited.intersection(value["effects"]):
            errors.append("duplicate candidate has blocking effect")

    if value["primary_target"]["kind"] == (
        "actor_directory_collection"
    ):
        for fact in value["evidence"]:
            if (
                fact["name"] == "exact_actor_known"
                and fact["kind"] == "boolean"
                and fact["value"] is True
            ):
                errors.append(
                    "collection target used despite exact Actor identity"
                )

    for fact in value["evidence"]:
        if sensitive_name(fact["name"]):
            errors.append("sensitive evidence fact name")
        if fact["name"] == "prior_actor_id":
            errors.append("finding silently retargeted")

    return errors


def actor_record_sort_key(
    target: dict[str, Any],
) -> tuple[str, ...]:
    exact = target["actor_directory_record_ref"]
    kind = exact["kind"]
    order = {
        "actor": "1",
        "actor_contact_point": "2",
        "actor_student_relationship": "3",
        "actor_roster_student_collision": "4",
    }[kind]
    if kind == "actor":
        ref = exact["actor_ref"]
        return (order, ref["actor_id"])
    if kind == "actor_contact_point":
        ref = exact["contact_point_ref"]
        return (order, ref["actor_id"], ref["contact_point_id"])
    if kind == "actor_student_relationship":
        ref = exact["relationship_ref"]
        return (order, ref["actor_id"], ref["relationship_id"])
    ref = exact["collision_ref"]
    return (order, ref["actor_id"], ref["collision_id"])


def journal_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    actor_targets = list(iter_targets(value))

    if actor_targets and value["scope"] != "workspace":
        errors.append("Actor operation does not use workspace scope")

    for target in actor_targets:
        errors.extend(actor_set_errors(target))

    for entry in value["preflight_snapshot"]:
        if entry["target"].get("kind") == "actor_set":
            errors.append("Actor set used as preflight representation")
    for step in value["write_set"]:
        if step["target"].get("kind") == "actor_set":
            errors.append("Actor set used as write-step target")

    primary = value["primary_target"]
    if (
        primary.get("kind") == "actor_directory_collection"
        and value["operation_kind"]
        not in {"integrity_scan", "rebuild_projection"}
    ):
        errors.append("collection target used for single-record operation")

    if (
        value["operation_kind"] == "consolidate_duplicates"
        and primary.get("kind") != "actor_set"
    ):
        errors.append("Actor consolidation lacks Actor-set primary target")

    if (
        primary.get("kind") == "workspace"
        and any(
            target.get("kind") == "actor_directory_record"
            for target in actor_targets
        )
    ):
        errors.append("generic workspace primary hides exact Actor target")

    for fact in value["intent_facts"]:
        if sensitive_name(fact["name"]):
            errors.append("sensitive intent fact")
        if (
            fact["name"] == "claimed_complete_subset"
            and fact["kind"] == "boolean"
            and fact["value"] is True
        ):
            errors.append("partial Actor operation claimed complete")

    actor_locks = [
        entry
        for entry in value["lock_set"]
        if entry["lock_scope"]
        in {
            "actor_directory_collection",
            "actor_directory_record",
        }
    ]
    if actor_locks:
        scopes = [entry["lock_scope"] for entry in value["lock_set"]]
        if scopes[0] == "actor_directory_collection":
            pass
        elif "actor_directory_collection" in scopes:
            errors.append("Actor collection lock is not first")

        record_targets = [
            entry["protected_target"]
            for entry in value["lock_set"]
            if entry["lock_scope"] == "actor_directory_record"
        ]
        if record_targets != sorted(
            record_targets,
            key=actor_record_sort_key,
        ):
            errors.append("Actor record locks are not sorted")

        if scopes[-1] != "operation":
            errors.append("operation lock is not last")

    return errors


def deterministic_lock_id(
    lock_scope: str,
    protected_target: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "lock_scope": lock_scope,
            "protected_target": protected_target,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "lock_" + hashlib.sha256(payload).hexdigest()


def lock_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = deterministic_lock_id(
        value["lock_scope"],
        value["protected_target"],
    )
    if value["lock_id"] != expected:
        errors.append("deterministic lock ID mismatch")

    version = actor_directory_ref_version(
        value["protected_target"]
    )
    if version is not None and version != "1":
        errors.append("unsupported Actor target version")

    operation_id = value["owning_operation"]["operation_id"]
    if operation_id == "op_single_contact_update" and (
        value["lock_scope"] == "actor_directory_collection"
    ):
        errors.append("unnecessary Actor collection lock")
    if operation_id == "op_missing":
        errors.append("owning operation does not resolve")

    target = value["protected_target"]
    if target.get("kind") == "operation":
        if (
            target["operation_ref"]["operation_id"]
            != operation_id
        ):
            errors.append("operation lock owner mismatch")

    return errors


def quarantine_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    target = value["target"]
    errors.extend(actor_set_errors(target))

    version = actor_directory_ref_version(target)
    if version is not None and version != "1":
        errors.append("unsupported Actor target version")

    if (
        target.get("kind") == "actor_directory_collection"
        and "block_actor_directory_writes"
        not in value["effects"]
    ):
        errors.append("collection quarantine lacks Actor write block")

    if (
        target.get("kind") == "actor_set"
        and "Independent exact Actor controls are sufficient"
        in value["reason_detail"]
    ):
        errors.append("Actor-set quarantine is unnecessarily broad")

    if value["reason"] == "actor_roster_collision":
        if target.get("kind") != "actor_directory_record":
            errors.append("roster-collision reason target mismatch")
        else:
            exact = target["actor_directory_record_ref"]
            if exact["kind"] != "actor":
                errors.append("roster-collision reason target mismatch")

    detail = value["reason_detail"]
    if "CONTACT_VALUE" in detail or "@" in detail:
        errors.append("quarantine copied contact value")

    if (
        value["origin"]["applying_operation"]["operation_id"]
        == "op_missing"
    ):
        errors.append("applying operation does not resolve")

    return errors


def application_errors(
    contract: str,
    value: dict[str, Any],
) -> list[str]:
    if contract == "integrity_finding":
        return integrity_errors(value)
    if contract == "operation_journal":
        return journal_errors(value)
    if contract == "operation_lock":
        return lock_errors(value)
    return quarantine_errors(value)


class Issue14ActorAwareOperationalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(
            contract,
            "2",
            catalog=self.catalog,
            store=self.store,
        )

    def test_manifests_have_expected_metadata(self) -> None:
        for family, contract in FAMILIES.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 14)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "2")

    def test_valid_fixtures_pass(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["valid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT / family / "valid" / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertEqual(
                        application_errors(contract, value),
                        [],
                    )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT / family / "invalid" / filename
                    )
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_application_invalid_fixtures_pass_schema_only(
        self,
    ) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["application_invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "application-invalid"
                        / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertTrue(
                        application_errors(contract, value)
                    )

    def test_version_two_contracts_are_cataloged(self) -> None:
        for contract, path in SCHEMA_PATHS.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["2"]
                self.assertEqual(entry["path"], path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + path
                    ),
                )
                schema = load_json(REPO_ROOT / path)
                self.assertEqual(schema["$id"], entry["schema_id"])

    def test_version_one_contracts_remain_cataloged(self) -> None:
        for contract in SCHEMA_PATHS:
            with self.subTest(contract=contract):
                self.assertIn(
                    "1",
                    self.catalog["contracts"][contract],
                )
                self.assertIn(
                    "2",
                    self.catalog["contracts"][contract],
                )

    def test_integrity_v2_adds_three_actor_targets(self) -> None:
        schema = load_json(
            REPO_ROOT / SCHEMA_PATHS["integrity_finding"]
        )
        refs = {
            item["$ref"].rsplit("/", 1)[-1]
            for item in schema["$defs"]["findingTarget"]["oneOf"]
            if "$ref" in item
        }
        self.assertTrue(
            {
                "actorDirectoryRecordTarget",
                "actorSetTarget",
                "actorDirectoryCollectionTarget",
            }.issubset(refs)
        )
        actor_set = schema["$defs"]["actorSetTarget"]
        self.assertEqual(
            actor_set["properties"]["actor_refs"]["minItems"],
            2,
        )
        self.assertTrue(
            actor_set["properties"]["actor_refs"]["uniqueItems"]
        )

    def test_integrity_v2_preserves_severity_and_effects(self) -> None:
        v1 = load_json(
            REPO_ROOT
            / "schemas/v1/projections/integrity-finding.schema.json"
        )
        v2 = load_json(
            REPO_ROOT / SCHEMA_PATHS["integrity_finding"]
        )
        self.assertEqual(
            v1["properties"]["severity"],
            v2["properties"]["severity"],
        )
        self.assertEqual(
            v1["properties"]["effects"],
            v2["properties"]["effects"],
        )

    def test_journal_v2_preserves_operation_vocabularies(
        self,
    ) -> None:
        v1 = load_json(
            REPO_ROOT
            / "schemas/v1/operations/operation-journal.schema.json"
        )
        v2 = load_json(
            REPO_ROOT / SCHEMA_PATHS["operation_journal"]
        )
        self.assertEqual(
            v2["properties"]["schema_version"]["const"],
            "2",
        )
        self.assertEqual(
            v1["properties"]["operation_kind"],
            v2["properties"]["operation_kind"],
        )
        self.assertEqual(
            v1["properties"]["scope"],
            v2["properties"]["scope"],
        )

    def test_journal_v2_adds_actor_lock_scopes(self) -> None:
        schema = load_json(
            REPO_ROOT / SCHEMA_PATHS["operation_journal"]
        )
        scopes = set(
            schema["$defs"]["lockEntry"]["properties"][
                "lock_scope"
            ]["enum"]
        )
        self.assertIn("actor_directory_collection", scopes)
        self.assertIn("actor_directory_record", scopes)

    def test_lock_v2_has_no_actor_set_target(self) -> None:
        schema = load_json(
            REPO_ROOT / SCHEMA_PATHS["operation_lock"]
        )
        scopes = set(schema["properties"]["lock_scope"]["enum"])
        self.assertIn("actor_directory_collection", scopes)
        self.assertIn("actor_directory_record", scopes)
        target_text = json.dumps(schema["$defs"]["lockTarget"])
        self.assertNotIn('"actor_set"', target_text)

    def test_quarantine_v2_adds_actor_write_effect(self) -> None:
        schema = load_json(
            REPO_ROOT / SCHEMA_PATHS["quarantine_record"]
        )
        effects = set(
            schema["properties"]["effects"]["items"]["enum"]
        )
        self.assertIn("block_actor_directory_writes", effects)

    def test_pointer_and_finding_admin_contracts_stay_v1(
        self,
    ) -> None:
        for contract in (
            "operation_current_pointer",
            "quarantine_current_pointer",
            "finding_acknowledgement",
            "finding_suppression",
            "finding_suppression_current_pointer",
        ):
            with self.subTest(contract=contract):
                self.assertEqual(
                    set(self.catalog["contracts"][contract]),
                    {"1"},
                )


if __name__ == "__main__":
    unittest.main()
