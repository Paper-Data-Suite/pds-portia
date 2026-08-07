from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import hashlib
import json
import re
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
    / "actor-derived-state"
)

SCHEMA_FAMILIES = {
    "source-snapshot": "source_snapshot",
    "derived-index-metadata": "derived_index_metadata",
    "derived-current-pointer": "derived_current_pointer",
}

PROJECTION_DATA_ROOT = FIXTURE_ROOT / "projection-data-examples"

ACTOR_PROJECTION_KINDS = {
    "incoming_reference_index",
    "replacement_frontier_index",
    "lifecycle_timeline",
}

FORBIDDEN_DERIVED_KEYS = {
    "display_name",
    "actor_display_name",
    "student_name",
    "organization",
    "title",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "contact_value",
    "contact_hash",
    "email_hash",
    "phone_hash",
    "relationship_detail",
    "relationship_source_detail",
    "verification_detail",
    "source_detail",
    "removed_payload",
    "payload",
}

EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
PHONE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:\+?1[\s().-]*)?"
    r"(?:\d[\s().-]*){10}(?![A-Za-z0-9])"
)


def canonical_snapshot_digest(snapshot: dict[str, Any]) -> str:
    payload = {
        key: snapshot[key]
        for key in (
            "snapshot_algorithm",
            "projection_kind",
            "projection_scope",
            "authorization_scope",
            "discovery_roots",
            "source_contracts",
            "entries",
        )
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fingerprint_for_json(value: Any) -> dict[str, Any]:
    encoded = (
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    return {
        "algorithm": "sha256",
        "digest": hashlib.sha256(encoded).hexdigest(),
        "byte_length": len(encoded),
    }


def snapshot_application_errors(
    snapshot: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if snapshot["source_snapshot_digest"] != (
        canonical_snapshot_digest(snapshot)
    ):
        errors.append("source snapshot digest mismatch")

    entry_paths = [
        entry["workspace_relative_path"]
        for entry in snapshot["entries"]
    ]
    if entry_paths != sorted(entry_paths):
        errors.append("source entries are not sorted")
    if len(entry_paths) != len(set(entry_paths)):
        errors.append("source path appears more than once")

    source_contracts = [
        (
            item["contract_name"],
            item["contract_version"],
        )
        for item in snapshot["source_contracts"]
    ]
    if source_contracts != sorted(source_contracts):
        errors.append("source contracts are not sorted")
    if len(source_contracts) != len(set(source_contracts)):
        errors.append("source contract appears more than once")

    if snapshot["projection_kind"] in ACTOR_PROJECTION_KINDS:
        scope = snapshot["projection_scope"]["scope"]
        if scope not in {"workspace", "graph"}:
            errors.append("Actor projection uses work/class scope")

    if snapshot["projection_kind"] == "incoming_reference_index":
        coverage = snapshot["authorization_scope"]["coverage"]
        if coverage == "complete":
            roots = set(snapshot["discovery_roots"])
            if "portia/actors" not in roots:
                errors.append("complete Actor scan omits Actor root")
            if "classes" not in roots:
                errors.append("complete incoming-reference scan omits classes")

    return errors


def metadata_application_errors(
    metadata: dict[str, Any],
    data_values: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    snapshot = metadata["source_snapshot"]

    if metadata["projection_kind"] != snapshot["projection_kind"]:
        errors.append("projection kind disagrees with snapshot")
    if metadata["projection_scope"] != snapshot["projection_scope"]:
        errors.append("projection scope disagrees with snapshot")
    if metadata["authorization_scope"] != snapshot[
        "authorization_scope"
    ]:
        errors.append("authorization scope disagrees with snapshot")

    generated_at = datetime.fromisoformat(
        metadata["generated_at"].replace("Z", "+00:00")
    )
    observed_at = datetime.fromisoformat(
        snapshot["observed_at"].replace("Z", "+00:00")
    )
    if generated_at < observed_at:
        errors.append("generation predates source observation")

    errors.extend(snapshot_application_errors(snapshot))

    matching_data = None
    for value in data_values.values():
        if (
            value["projection_kind"] == metadata["projection_kind"]
            and value["projection_scope"] == metadata["projection_scope"]
            and value["authorization_scope"]
            == metadata["authorization_scope"]
            and value["source_snapshot_digest"]
            == snapshot["source_snapshot_digest"]
        ):
            matching_data = value
            break

    if matching_data is None:
        errors.append("matching data example is unavailable")
    elif metadata["data_artifact"]["fingerprint"] != (
        fingerprint_for_json(matching_data)
    ):
        errors.append("data artifact fingerprint mismatch")

    expected_prefix = (
        f"portia/derived/{metadata['projection_kind']}/"
    )
    if not metadata["data_artifact"][
        "workspace_relative_path"
    ].startswith(expected_prefix):
        errors.append("data artifact path kind mismatch")

    return errors


def logical_actor_id(ref: dict[str, Any]) -> str:
    return ref["actor_id"]


def exact_target_identity(target: dict[str, Any]) -> tuple[str, ...]:
    kind = target["kind"]
    if kind == "actor":
        ref = target["actor_ref"]
        return (kind, ref["actor_id"], ref["contract_version"])
    if kind == "actor_contact_point":
        ref = target["contact_point_ref"]
        return (
            kind,
            ref["actor_id"],
            ref["contact_point_id"],
            ref["contract_version"],
        )
    if kind == "actor_student_relationship":
        ref = target["relationship_ref"]
        return (
            kind,
            ref["actor_id"],
            ref["relationship_id"],
            ref["contract_version"],
        )
    raise ValueError(f"Unsupported example target kind: {kind}")


def privacy_errors(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_DERIVED_KEYS:
                errors.append(f"forbidden key {path}.{key}")
            errors.extend(
                privacy_errors(child, f"{path}.{key}")
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                privacy_errors(child, f"{path}[{index}]")
            )
    elif isinstance(value, str):
        if EMAIL_PATTERN.search(value):
            errors.append(f"email-like value at {path}")
        if PHONE_PATTERN.search(value):
            errors.append(f"phone-like value at {path}")

    return errors


def incoming_data_errors(value: dict[str, Any]) -> list[str]:
    errors = privacy_errors(value)

    expected_keys = {
        "schema_version",
        "record_type",
        "projection_kind",
        "projection_scope",
        "authorization_scope",
        "source_snapshot_digest",
        "completeness",
        "limitations",
        "entries",
    }
    if set(value) != expected_keys:
        errors.append("incoming-reference envelope is not closed")

    if value["record_type"] != "incoming_reference_index_data":
        errors.append("wrong incoming-reference record type")
    if value["projection_kind"] != "incoming_reference_index":
        errors.append("wrong incoming-reference projection kind")

    coverage = value["authorization_scope"]["coverage"]
    if coverage == "complete":
        if value["completeness"] != "complete":
            errors.append("complete coverage does not claim complete")
        if value["limitations"]:
            errors.append("complete coverage has limitations")
    else:
        if value["completeness"] == "complete":
            errors.append("limited scan claims complete")
        if not value["limitations"]:
            errors.append("limited scan omits limitations")
        if value.get("exceptional_removal_eligible") is True:
            errors.append("limited scan claims removal eligibility")

    target_identities: list[tuple[str, ...]] = []
    for entry in value["entries"]:
        allowed_entry_keys = {"target", "incoming_references"}
        if set(entry) != allowed_entry_keys:
            errors.append("incoming-reference entry is not closed")
            continue

        identity = exact_target_identity(entry["target"])
        target_identities.append(identity)

        paths = []
        for incoming in entry["incoming_references"]:
            required = {
                "source_record",
                "reference_path",
                "reference_class",
                "current_use_disposition",
            }
            if set(incoming) != required:
                errors.append("incoming reference is not closed")
                continue
            source = incoming["source_record"]
            if set(source) != {
                "contract_name",
                "contract_version",
                "workspace_relative_path",
            }:
                errors.append("source record is not closed")
            paths.append(source["workspace_relative_path"])

        if paths != sorted(paths):
            errors.append("incoming references are not sorted")

    if target_identities != sorted(target_identities):
        errors.append("incoming-reference targets are not sorted")
    if len(target_identities) != len(set(target_identities)):
        errors.append("incoming-reference target repeats")

    return errors


def replacement_data_errors(
    value: dict[str, Any],
) -> list[str]:
    errors = privacy_errors(value)

    expected_keys = {
        "schema_version",
        "record_type",
        "projection_kind",
        "projection_scope",
        "authorization_scope",
        "source_snapshot_digest",
        "selection_policy",
        "entries",
    }
    if set(value) != expected_keys:
        errors.append("replacement-frontier envelope is not closed")

    if value["record_type"] != "replacement_frontier_index_data":
        errors.append("wrong replacement-frontier record type")
    if value["projection_kind"] != "replacement_frontier_index":
        errors.append("wrong replacement-frontier projection kind")
    if value["selection_policy"] != "explicit_only":
        errors.append("replacement frontier permits silent following")

    source_ids: list[str] = []
    for entry in value["entries"]:
        required = {
            "source",
            "direct_successors",
            "frontier",
            "resolution_state",
            "automatic_follow",
        }
        if set(entry) != required:
            errors.append("replacement entry is not closed")
            continue

        source_id = logical_actor_id(entry["source"])
        source_ids.append(source_id)

        if entry["automatic_follow"] is not False:
            errors.append("entry permits automatic following")

        for field in ("direct_successors", "frontier"):
            actor_ids = [
                logical_actor_id(ref)
                for ref in entry[field]
            ]
            if actor_ids != sorted(actor_ids):
                errors.append(f"{field} is not sorted")
            if len(actor_ids) != len(set(actor_ids)):
                errors.append(f"{field} repeats logical Actor")
            terminal_self_frontier = (
                field == "frontier"
                and entry["resolution_state"] == "terminal_current"
                and actor_ids == [source_id]
            )
            if source_id in actor_ids and not terminal_self_frontier:
                errors.append("replacement graph contains self-cycle")

        if entry["resolution_state"] == "superseded_split":
            if len(entry["frontier"]) < 2:
                errors.append("split frontier has fewer than two Actors")
        if entry["resolution_state"] == "terminal_current":
            if entry["direct_successors"]:
                errors.append("terminal Actor has direct successors")
            frontier_ids = [
                logical_actor_id(ref)
                for ref in entry["frontier"]
            ]
            if frontier_ids != [source_id]:
                errors.append("terminal frontier does not select itself")

    if source_ids != sorted(source_ids):
        errors.append("replacement sources are not sorted")
    if len(source_ids) != len(set(source_ids)):
        errors.append("replacement source repeats")

    return errors


def lifecycle_data_errors(value: dict[str, Any]) -> list[str]:
    errors = privacy_errors(value)

    expected_keys = {
        "schema_version",
        "record_type",
        "projection_kind",
        "projection_scope",
        "authorization_scope",
        "source_snapshot_digest",
        "target",
        "creation_status",
        "selected_terminal_transition_id",
        "selected_status",
        "transitions",
        "history_corrections",
    }
    if set(value) != expected_keys:
        errors.append("lifecycle timeline envelope is not closed")

    if value["record_type"] != "lifecycle_timeline_data":
        errors.append("wrong lifecycle timeline record type")
    if value["projection_kind"] != "lifecycle_timeline":
        errors.append("wrong lifecycle projection kind")

    selected = [
        transition
        for transition in value["transitions"]
        if transition["selected"]
    ]
    if not selected:
        errors.append("timeline has no selected branch")
    elif selected[-1]["transition_id"] != (
        value["selected_terminal_transition_id"]
    ):
        errors.append("selected terminal transition disagrees")
    elif selected[-1]["new_status"] != value["selected_status"]:
        errors.append("selected status disagrees")

    return errors


def projection_data_errors(value: dict[str, Any]) -> list[str]:
    kind = value.get("projection_kind")
    if kind == "incoming_reference_index":
        return incoming_data_errors(value)
    if kind == "replacement_frontier_index":
        return replacement_data_errors(value)
    if kind == "lifecycle_timeline":
        return lifecycle_data_errors(value)
    return ["unknown Actor-derived example projection kind"]


class Issue14ActorDerivedStateCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.data_manifest = load_json(
            PROJECTION_DATA_ROOT / "manifest.json"
        )
        cls.data_values = {
            filename: load_json(
                PROJECTION_DATA_ROOT / "valid" / filename
            )
            for filename in cls.data_manifest["valid"]
        }
        cls.metadata_values = {}
        metadata_manifest = load_json(
            FIXTURE_ROOT
            / "derived-index-metadata"
            / "manifest.json"
        )
        for filename in metadata_manifest["valid"]:
            cls.metadata_values[filename] = load_json(
                FIXTURE_ROOT
                / "derived-index-metadata"
                / "valid"
                / filename
            )

    def validator(self, contract: str):
        return validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_schema_manifests_reuse_version_1_contracts(
        self,
    ) -> None:
        for family, contract in SCHEMA_FAMILIES.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 14)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_schema_fixtures_pass_structurally(
        self,
    ) -> None:
        for family, contract in SCHEMA_FAMILIES.items():
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
                        FIXTURE_ROOT
                        / family
                        / "valid"
                        / filename
                    )
                    errors = list(validator.iter_errors(value))
                    self.assertFalse(
                        errors,
                        "\n".join(
                            error.message for error in errors
                        ),
                    )

    def test_invalid_schema_fixtures_fail_structurally(
        self,
    ) -> None:
        for family, contract in SCHEMA_FAMILIES.items():
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
                        FIXTURE_ROOT
                        / family
                        / "invalid"
                        / filename
                    )
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_valid_source_snapshots_pass_application_checks(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_ROOT / "source-snapshot" / "manifest.json"
        )
        for filename in manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "source-snapshot"
                    / "valid"
                    / filename
                )
                self.assertEqual(
                    snapshot_application_errors(value),
                    [],
                )

    def test_source_snapshot_application_invalid_matrix(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_ROOT / "source-snapshot" / "manifest.json"
        )
        validator = self.validator("source_snapshot")
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "source-snapshot"
                    / "application-invalid"
                    / filename
                )
                structural = list(validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(
                        error.message for error in structural
                    ),
                )
                self.assertTrue(
                    snapshot_application_errors(value)
                )

    def test_valid_metadata_passes_application_checks(
        self,
    ) -> None:
        for filename, value in self.metadata_values.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    metadata_application_errors(
                        value,
                        self.data_values,
                    ),
                    [],
                )

    def test_metadata_application_invalid_matrix(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_ROOT
            / "derived-index-metadata"
            / "manifest.json"
        )
        validator = self.validator("derived_index_metadata")
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "derived-index-metadata"
                    / "application-invalid"
                    / filename
                )
                structural = list(validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(
                        error.message for error in structural
                    ),
                )
                self.assertTrue(
                    metadata_application_errors(
                        value,
                        self.data_values,
                    )
                )

    def test_valid_pointers_resolve_exact_metadata(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_ROOT
            / "derived-current-pointer"
            / "manifest.json"
        )
        metadata_by_generation = {
            value["generation_id"]: value
            for value in self.metadata_values.values()
        }
        for filename in manifest["valid"]:
            with self.subTest(filename=filename):
                pointer = load_json(
                    FIXTURE_ROOT
                    / "derived-current-pointer"
                    / "valid"
                    / filename
                )
                generation = metadata_by_generation[
                    pointer["generation_ref"]["generation_id"]
                ]
                self.assertEqual(
                    pointer["projection_kind"],
                    generation["projection_kind"],
                )
                self.assertEqual(
                    pointer["projection_scope"],
                    generation["projection_scope"],
                )
                self.assertEqual(
                    pointer["generation_ref"]["contract_version"],
                    "1",
                )

    def test_pointer_application_invalid_matrix(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_ROOT
            / "derived-current-pointer"
            / "manifest.json"
        )
        validator = self.validator("derived_current_pointer")
        metadata_by_generation = {
            value["generation_id"]: value
            for value in self.metadata_values.values()
        }
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
                pointer = load_json(
                    FIXTURE_ROOT
                    / "derived-current-pointer"
                    / "application-invalid"
                    / filename
                )
                structural = list(validator.iter_errors(pointer))
                self.assertFalse(
                    structural,
                    "\n".join(
                        error.message for error in structural
                    ),
                )
                generation = metadata_by_generation.get(
                    pointer["generation_ref"]["generation_id"]
                )
                invalid = generation is None
                if generation is not None:
                    invalid = invalid or (
                        pointer["projection_kind"]
                        != generation["projection_kind"]
                    )
                    invalid = invalid or (
                        pointer["projection_scope"]
                        != generation["projection_scope"]
                    )
                self.assertTrue(invalid)

    def test_valid_projection_data_examples_pass(
        self,
    ) -> None:
        for filename, value in self.data_values.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    projection_data_errors(value),
                    [],
                )

    def test_projection_data_application_invalid_matrix(
        self,
    ) -> None:
        for filename in self.data_manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    PROJECTION_DATA_ROOT
                    / "application-invalid"
                    / filename
                )
                self.assertTrue(projection_data_errors(value))

    def test_actor_sources_use_existing_source_roles(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/projections/source-snapshot.schema.json"
        )
        roles = set(
            schema["$defs"]["sourceEntry"][
                "properties"
            ]["source_role"]["enum"]
        )
        self.assertEqual(
            roles,
            {
                "canonical_domain",
                "operational_revision",
                "operational_pointer",
                "operational_lock",
                "quarantine_state",
                "finding_acknowledgement",
                "finding_suppression",
                "source_projection",
            },
        )
        self.assertNotIn("actor_domain", roles)

        manifest = load_json(
            FIXTURE_ROOT / "source-snapshot" / "manifest.json"
        )
        for filename in manifest["valid"]:
            value = load_json(
                FIXTURE_ROOT
                / "source-snapshot"
                / "valid"
                / filename
            )
            for entry in value["entries"]:
                if entry["workspace_relative_path"].startswith(
                    "portia/actors/"
                ):
                    self.assertEqual(
                        entry["source_role"],
                        "canonical_domain",
                    )

    def test_actor_projection_kinds_are_reused_not_added(
        self,
    ) -> None:
        filenames = (
            "source-snapshot.schema.json",
            "derived-index-metadata.schema.json",
            "derived-current-pointer.schema.json",
        )
        vocabularies = []
        for filename in filenames:
            schema = load_json(
                REPO_ROOT
                / "schemas/v1/projections"
                / filename
            )
            vocabularies.append(
                tuple(
                    schema["properties"]["projection_kind"][
                        "enum"
                    ]
                )
            )
        self.assertTrue(
            all(
                vocabulary == vocabularies[0]
                for vocabulary in vocabularies[1:]
            )
        )
        vocabulary = set(vocabularies[0])
        self.assertTrue(ACTOR_PROJECTION_KINDS <= vocabulary)
        self.assertNotIn("actor_search_index", vocabulary)
        self.assertNotIn("actor_duplicate_index", vocabulary)

    def test_authorization_limited_generation_cannot_prove_absence(
        self,
    ) -> None:
        value = self.data_values[
            "incoming-reference-authorization-limited.json"
        ]
        self.assertEqual(
            value["authorization_scope"]["coverage"],
            "authorization_limited",
        )
        self.assertEqual(value["completeness"], "indeterminate")
        self.assertTrue(value["limitations"])
        self.assertNotIn(
            "exceptional_removal_eligible",
            value,
        )

    def test_replacement_frontier_never_silently_follows(
        self,
    ) -> None:
        value = self.data_values[
            "replacement-frontier-actor-graph.json"
        ]
        self.assertEqual(
            value["selection_policy"],
            "explicit_only",
        )
        self.assertTrue(
            all(
                entry["automatic_follow"] is False
                for entry in value["entries"]
            )
        )

    def test_current_pointer_contains_no_truth_or_freshness_claim(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/projections/"
            "derived-current-pointer.schema.json"
        )
        for forbidden in (
            "fresh",
            "complete",
            "authorization_scope",
            "identity_truth",
            "duplicate_equivalence",
            "contact_validity",
            "relationship_authority",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_all_valid_actor_derived_payloads_are_privacy_safe(
        self,
    ) -> None:
        values: list[Any] = list(self.data_values.values())

        for family in SCHEMA_FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            for filename in manifest["valid"]:
                values.append(
                    load_json(
                        FIXTURE_ROOT
                        / family
                        / "valid"
                        / filename
                    )
                )

        for index, value in enumerate(values):
            with self.subTest(index=index):
                self.assertEqual(privacy_errors(value), [])

    def test_whole_file_digests_do_not_create_contact_indexes(
        self,
    ) -> None:
        for value in self.data_values.values():
            text = json.dumps(value, sort_keys=True)
            self.assertNotIn("contact_hash", text)
            self.assertNotIn("email_hash", text)
            self.assertNotIn("phone_hash", text)
        metadata = self.metadata_values[
            "incoming-reference-complete.json"
        ]
        self.assertEqual(
            metadata["data_artifact"]["fingerprint"][
                "algorithm"
            ],
            "sha256",
        )

    def test_public_contract_paths_remain_version_1(
        self,
    ) -> None:
        expected = {
            "source_snapshot": (
                "schemas/v1/projections/"
                "source-snapshot.schema.json"
            ),
            "derived_index_metadata": (
                "schemas/v1/projections/"
                "derived-index-metadata.schema.json"
            ),
            "derived_current_pointer": (
                "schemas/v1/projections/"
                "derived-current-pointer.schema.json"
            ),
        }
        for contract, path in expected.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + path
                    ),
                )


if __name__ == "__main__":
    unittest.main()
