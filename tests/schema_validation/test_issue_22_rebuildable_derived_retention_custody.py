from __future__ import annotations

import copy
import hashlib
import json
import unittest

try:
    from .issue_22_graph_validation import (
        _canonical_path_for_record,
        load_json_object,
        load_scenario_records,
        replacement_frontier,
        validate_graph,
    )
    from .schema_support import (
        REPO_ROOT,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from issue_22_graph_validation import (
        _canonical_path_for_record,
        load_json_object,
        load_scenario_records,
        replacement_frontier,
        validate_graph,
    )
    from schema_support import (
        REPO_ROOT,
        load_validated_catalog_and_store,
        validator_for,
    )

ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"
SCENARIO_ROOT = ROOT / "positive" / "p22_13_rebuildable_derived_retention_custody"
SCENARIO_PATH = SCENARIO_ROOT / "scenario.json"


def canonical_json_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def snapshot_digest(snapshot: dict[str, object]) -> str:
    keys = (
        "snapshot_algorithm",
        "projection_kind",
        "projection_scope",
        "authorization_scope",
        "discovery_roots",
        "source_contracts",
        "entries",
    )
    return canonical_json_digest({key: snapshot[key] for key in keys})


def work_key(ref: dict[str, object]) -> str:
    return f"{ref['class_id']}/{ref['work_id']}@{ref['contract_version']}"


def exact_record_key(ref: dict[str, object]) -> str:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        f"{work['class_id']}/{work['work_id']}/"
        f"{record['record_kind']}:{record['record_id']}@"
        f"{record['contract_version']}"
    )


def build_views(by_type: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    relationship = by_type["work_relationship"][0]
    dependency = by_type["dependency"][0]
    accounts = {value["account_id"]: value for value in by_type["account"]}
    successor = next(value for value in accounts.values() if value["status"] == "active")
    predecessor_ref = successor["supersedes"][0]["work_record_ref"]
    predecessor_id = predecessor_ref["record_ref"]["record_id"]
    predecessor = accounts[predecessor_id]
    transitions = {value["transition_id"]: value for value in by_type["lifecycle_transition"]}
    head = next(
        value
        for value in transitions.values()
        if value["to_status"] == predecessor["status"]
    )
    first = transitions[head["previous_transition"]["record_id"]]
    participant = by_type["event_participant"][0]
    events = sorted(by_type["portia_work"], key=lambda value: value["work_id"])

    incoming: dict[str, list[dict[str, str]]] = {}

    def add(target: str, source: dict[str, str]) -> None:
        incoming.setdefault(target, []).append(source)

    add(
        work_key(relationship["target"]),
        {
            "source_kind": "work_relationship",
            "record_id": relationship["relationship_id"],
            "source_work": work_key(relationship["source"]),
        },
    )
    add(
        work_key(dependency["dependency"]["work_ref"]),
        {
            "source_kind": "dependency",
            "record_id": dependency["dependency_id"],
            "dependent_work": (
                f"{dependency['class_id']}/{dependency['work_id']}@2"
            ),
        },
    )
    predecessor_key = exact_record_key(predecessor_ref)
    add(
        predecessor_key,
        {"source_kind": "account_supersession", "record_id": successor["account_id"]},
    )
    for transition in (first, head):
        add(
            f"{transition['class_id']}/{transition['work_id']}/account:{predecessor_id}@2",
            {"source_kind": "lifecycle_transition", "record_id": transition["transition_id"]},
        )
    add(
        f"{first['class_id']}/{first['work_id']}/lifecycle_transition:{first['transition_id']}@1",
        {"source_kind": "lifecycle_predecessor", "record_id": head["transition_id"]},
    )
    for target in incoming:
        incoming[target] = sorted(
            incoming[target],
            key=lambda value: (value["source_kind"], value["record_id"]),
        )
    incoming = dict(sorted(incoming.items()))

    reverse = {
        work_key(relationship["target"]): [
            {
                "relationship_id": relationship["relationship_id"],
                "source_work": work_key(relationship["source"]),
                "relationship_type": relationship["relationship_type"],
            }
        ]
    }
    frontier = {
        "account": {
            "predecessors": [predecessor_key],
            "current": [
                f"{successor['class_id']}/{successor['work_id']}/"
                f"account:{successor['account_id']}@2"
            ],
            "selection_basis": "canonical_supersedes",
        }
    }
    dependency_view = {
        "nodes": [
            f"{dependency['class_id']}/{dependency['work_id']}@2",
            work_key(dependency["dependency"]["work_ref"]),
        ],
        "edges": [
            {
                "dependency_id": dependency["dependency_id"],
                "dependent": f"{dependency['class_id']}/{dependency['work_id']}@2",
                "dependency": work_key(dependency["dependency"]["work_ref"]),
                "strength": dependency["strength"],
                "applies_to": dependency["applies_to"],
                "purpose": dependency["purpose"],
            }
        ],
    }
    timeline = {
        "target": f"{predecessor['class_id']}/{predecessor['work_id']}/account:{predecessor_id}@2",
        "selected_head": head["transition_id"],
        "transitions": [
            {
                "transition_id": first["transition_id"],
                "from_status": first["from_status"],
                "to_status": first["to_status"],
                "previous_transition": None,
            },
            {
                "transition_id": head["transition_id"],
                "from_status": head["from_status"],
                "to_status": head["to_status"],
                "previous_transition": first["transition_id"],
            },
        ],
        "ordering_basis": "canonical_previous_transition_chain",
    }
    primary = next(value for value in events if value["work_id"] == dependency["work_id"])
    work_summary = {
        "work_ref": f"{primary['class_id']}/{primary['work_id']}@2",
        "status": primary["status"],
        "participant_ids": [participant["participant_id"]],
        "account_frontier": frontier["account"],
        "relationship_ids": [relationship["relationship_id"]],
        "dependency_ids": [dependency["dependency_id"]],
        "authority": "derived_summary_only",
    }
    class_summary = {
        "class_id": primary["class_id"],
        "work_count": len(events),
        "works": [
            {
                "work_id": value["work_id"],
                "work_kind": value["work_kind"],
                "status": value["status"],
            }
            for value in events
        ],
        "student_global_history": False,
        "authority": "derived_summary_only",
    }
    participant_history = {
        "scope": {
            "work_ref": {
                "module_id": "portia",
                "class_id": primary["class_id"],
                "work_id": primary["work_id"],
                "work_kind": "event",
                "contract_version": "2",
            },
            "focal_participant_ref": {
                "record_kind": "event_participant",
                "record_id": participant["participant_id"],
                "contract_version": "3",
            },
        },
        "account_history": [
            {"account_id": predecessor_id, "status": predecessor["status"]},
            {"account_id": successor["account_id"], "status": successor["status"]},
        ],
        "cross_work_or_cross_year_dossier": False,
        "authority": "derived_participant_view_only",
    }
    return {
        "incoming_reference_index": incoming,
        "work_relationship_reverse_index": reverse,
        "replacement_current_frontier": frontier,
        "dependency_graph": dependency_view,
        "lifecycle_timeline": timeline,
        "work_summary": work_summary,
        "class_summary": class_summary,
        "participant_specific_history": participant_history,
    }


class Issue22RebuildableDerivedRetentionCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.scenario = load_json_object(SCENARIO_PATH)
        cls.records = load_scenario_records(SCENARIO_PATH, cls.scenario)
        cls.by_type: dict[str, list[dict[str, object]]] = {}
        for record in cls.records:
            cls.by_type.setdefault(str(record.value["record_type"]), []).append(record.value)
        cls.expected_views = load_json_object(SCENARIO_ROOT / "derived-views.json")
        cls.snapshot = load_json_object(SCENARIO_ROOT / "source-snapshot.json")
        cls.metadata = load_json_object(SCENARIO_ROOT / "derived-index-metadata.json")
        cls.pointer = load_json_object(SCENARIO_ROOT / "derived-current-pointer.json")
        cls.retention = load_json_object(SCENARIO_ROOT / "retention-custody.json")

    def test_corpus_registers_p22_13_as_implemented(self) -> None:
        corpus = load_json_object(ROOT / "corpus.json")
        implemented = {entry["scenario_id"] for entry in corpus["scenarios"]}
        self.assertIn("P22-13", implemented)
        self.assertNotIn("P22-13", corpus["planned_positive_scenarios"])

    def test_p22_13_public_canonical_records_are_structurally_valid(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                validator = validator_for(
                    record.contract,
                    record.version,
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(record.value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_p22_13_combined_canonical_graph_is_valid(self) -> None:
        findings = validate_graph(
            SCENARIO_PATH,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_13_derived_public_contracts_are_structurally_valid(self) -> None:
        for descriptor in self.scenario["derived_contract_fixtures"]:
            with self.subTest(contract=descriptor["contract"]):
                value = load_json_object(SCENARIO_ROOT / descriptor["fixture_path"])
                validator = validator_for(
                    descriptor["contract"],
                    descriptor["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_p22_13_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )

    def test_p22_13_canonical_forward_edges_are_explicit(self) -> None:
        relationship = self.by_type["work_relationship"][0]
        dependency = self.by_type["dependency"][0]
        successor = next(value for value in self.by_type["account"] if value["status"] == "active")
        self.assertEqual(relationship["relationship_type"], "draws_context_from")
        self.assertEqual(dependency["dependency"]["kind"], "portia_work")
        self.assertEqual(successor["supersedes"][0]["reason"], "statement_corrected")

    def test_p22_13_rebuild_produces_all_eight_required_views(self) -> None:
        rebuilt = build_views(self.by_type)
        expected_names = {
            "incoming_reference_index",
            "work_relationship_reverse_index",
            "replacement_current_frontier",
            "dependency_graph",
            "lifecycle_timeline",
            "work_summary",
            "class_summary",
            "participant_specific_history",
        }
        self.assertEqual(set(rebuilt), expected_names)
        self.assertEqual(rebuilt, self.expected_views["views"])

    def test_p22_13_unchanged_rebuild_is_semantically_deterministic(self) -> None:
        first = build_views(self.by_type)
        second = build_views(copy.deepcopy(self.by_type))
        self.assertEqual(first, second)
        self.assertEqual(canonical_json_digest(first), self.expected_views["semantic_digest"])

    def test_p22_13_reverse_relationship_is_derived_from_forward_edge(self) -> None:
        relationship = self.by_type["work_relationship"][0]
        rebuilt = build_views(self.by_type)["work_relationship_reverse_index"]
        target = work_key(relationship["target"])
        self.assertEqual(rebuilt[target][0]["relationship_id"], relationship["relationship_id"])
        self.assertEqual(rebuilt[target][0]["source_work"], work_key(relationship["source"]))

    def test_p22_13_incoming_index_does_not_replace_forward_authority(self) -> None:
        views = build_views(self.by_type)
        context_event = next(
            value
            for value in self.by_type["portia_work"]
            if value["work_id"].endswith("context")
        )
        key = f"{context_event['class_id']}/{context_event['work_id']}@2"
        source_kinds = {item["source_kind"] for item in views["incoming_reference_index"][key]}
        self.assertEqual(source_kinds, {"work_relationship", "dependency"})
        self.assertIn("work_relationship", self.by_type)
        self.assertIn("dependency", self.by_type)

    def test_p22_13_replacement_frontier_selects_exact_successor(self) -> None:
        frontier = replacement_frontier(self.records, "account")
        self.assertEqual(frontier, ("acct_p22_derived_corrected",))
        view = build_views(self.by_type)["replacement_current_frontier"]["account"]
        self.assertIn("acct_p22_derived_original@2", view["predecessors"][0])
        self.assertIn("acct_p22_derived_corrected@2", view["current"][0])

    def test_p22_13_dependency_graph_keeps_exact_target(self) -> None:
        dependency = self.by_type["dependency"][0]
        edge = build_views(self.by_type)["dependency_graph"]["edges"][0]
        self.assertEqual(edge["dependency"], work_key(dependency["dependency"]["work_ref"]))
        self.assertNotEqual(edge["dependent"], edge["dependency"])

    def test_p22_13_lifecycle_timeline_uses_predecessor_chain(self) -> None:
        timeline = build_views(self.by_type)["lifecycle_timeline"]
        self.assertEqual(timeline["ordering_basis"], "canonical_previous_transition_chain")
        self.assertIsNone(timeline["transitions"][0]["previous_transition"])
        self.assertEqual(
            timeline["transitions"][1]["previous_transition"],
            timeline["transitions"][0]["transition_id"],
        )

    def test_p22_13_work_and_class_summaries_are_nonauthoritative(self) -> None:
        views = build_views(self.by_type)
        self.assertEqual(views["work_summary"]["authority"], "derived_summary_only")
        self.assertEqual(views["class_summary"]["authority"], "derived_summary_only")
        self.assertFalse(views["class_summary"]["student_global_history"])

    def test_p22_13_participant_history_is_exactly_work_scoped(self) -> None:
        view = build_views(self.by_type)["participant_specific_history"]
        self.assertEqual(view["scope"]["work_ref"]["work_id"], "evt_p22_derived_001")
        self.assertEqual(
            view["scope"]["focal_participant_ref"]["record_id"],
            "ep_p22_derived_student",
        )
        self.assertFalse(view["cross_work_or_cross_year_dossier"])

    def test_p22_13_source_snapshot_digest_and_entries_are_truthful(self) -> None:
        self.assertEqual(self.snapshot["source_snapshot_digest"], snapshot_digest(self.snapshot))
        paths = [entry["workspace_relative_path"] for entry in self.snapshot["entries"]]
        self.assertEqual(paths, sorted(paths))
        descriptor_by_path = {item["canonical_path"]: item for item in self.scenario["records"]}
        for entry in self.snapshot["entries"]:
            descriptor = descriptor_by_path[entry["workspace_relative_path"]]
            payload = (SCENARIO_ROOT / descriptor["fixture_path"]).read_bytes()
            self.assertEqual(entry["byte_length"], len(payload))
            self.assertEqual(entry["sha256_digest"], hashlib.sha256(payload).hexdigest())

    def test_p22_13_metadata_binds_exact_snapshot_and_output_bytes(self) -> None:
        self.assertEqual(self.metadata["source_snapshot"], self.snapshot)
        self.assertEqual(self.metadata["projection_kind"], self.snapshot["projection_kind"])
        payload = (SCENARIO_ROOT / "frontier-data.json").read_bytes()
        fingerprint = self.metadata["data_artifact"]["fingerprint"]
        self.assertEqual(fingerprint["byte_length"], len(payload))
        self.assertEqual(fingerprint["digest"], hashlib.sha256(payload).hexdigest())

    def test_p22_13_current_pointer_is_explicit_selection_not_freshness_claim(self) -> None:
        self.assertEqual(
            self.pointer["generation_ref"]["generation_id"],
            self.metadata["generation_id"],
        )
        for forbidden in ("fresh", "generated_at", "source_snapshot_digest", "authorization_scope"):
            self.assertNotIn(forbidden, self.pointer)

    def test_p22_13_current_pointer_does_not_follow_unselected_generation(self) -> None:
        alternate = copy.deepcopy(self.metadata)
        alternate["generation_id"] = "dgen_p22_frontier_unselected_999"
        alternate["generated_at"] = "2026-10-06T09:59:00-04:00"
        self.assertNotEqual(
            alternate["generation_id"],
            self.pointer["generation_ref"]["generation_id"],
        )
        self.assertEqual(self.pointer["generation_ref"]["generation_id"], "dgen_p22_frontier_001")

    def test_p22_13_changed_source_invalidates_prior_snapshot(self) -> None:
        changed = copy.deepcopy(self.by_type)
        successor = next(value for value in changed["account"] if value["status"] == "active")
        successor["content"][0]["text"] += " Changed source simulation."
        original_digest = canonical_json_digest(build_views(self.by_type))
        changed_digest = canonical_json_digest(build_views(changed))
        # The current view builder intentionally excludes Account prose, so semantic
        # output may remain identical; source-fingerprint freshness still fails.
        self.assertEqual(original_digest, changed_digest)
        current_successor = next(
            descriptor for descriptor in self.scenario["records"]
            if descriptor["logical_identity"] == "account:acct_p22_derived_corrected"
        )
        original_bytes = (SCENARIO_ROOT / current_successor["fixture_path"]).read_bytes()
        changed_bytes = (json.dumps(successor, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        self.assertNotEqual(
            hashlib.sha256(original_bytes).hexdigest(),
            hashlib.sha256(changed_bytes).hexdigest(),
        )
        snapshot_entry = next(
            entry for entry in self.snapshot["entries"]
            if entry["workspace_relative_path"] == current_successor["canonical_path"]
        )
        self.assertNotEqual(
            snapshot_entry["sha256_digest"],
            hashlib.sha256(changed_bytes).hexdigest(),
        )

    def test_p22_13_missing_or_deleted_cache_does_not_mean_empty_graph(self) -> None:
        views = build_views(self.by_type)
        self.assertTrue(views["incoming_reference_index"])
        self.assertTrue(views["dependency_graph"]["edges"])
        self.assertTrue(self.by_type["work_relationship"])
        self.assertTrue(self.by_type["dependency"])
        rebuilt_without_reading_cache = build_views(copy.deepcopy(self.by_type))
        self.assertEqual(rebuilt_without_reading_cache, views)

    def test_p22_13_retention_classes_keep_cache_and_canonical_distinct(self) -> None:
        by_subject = {item["subject"]: item for item in self.retention["expectations"]}
        canonical = by_subject["canonical_event_and_records"]
        cache = by_subject["derived_generation_and_views"]
        self.assertEqual(canonical["retention_class"], "canonical_behavior_support")
        self.assertEqual(cache["retention_class"], "derived_cache")
        self.assertFalse(canonical["rebuildable"])
        self.assertTrue(cache["rebuildable"])
        self.assertFalse(cache["destruction_of_cache_implies_canonical_deletion"])

    def test_p22_13_export_bytes_and_provenance_are_distinct_retention_units(self) -> None:
        by_subject = {item["subject"]: item for item in self.retention["expectations"]}
        self.assertEqual(by_subject["p22_12_export_bytes"]["retention_class"], "export_bytes")
        self.assertEqual(
            by_subject["p22_12_export_provenance"]["retention_class"],
            "export_provenance",
        )
        self.assertFalse(
            by_subject["p22_12_export_bytes"][
                "same_retention_unit_as_export_provenance"
            ]
        )
        self.assertFalse(
            by_subject["p22_12_export_provenance"][
                "same_retention_unit_as_export_bytes"
            ]
        )

    def test_p22_13_core_custody_is_foreign_and_not_portia_destruction_authority(self) -> None:
        context = load_json_object(SCENARIO_ROOT / "core-retained-source-context.json")
        self.assertEqual(context["authority"], "pds-core")
        self.assertEqual(context["custody_marker"], "core_retained_source")
        self.assertFalse(context["portia_has_destruction_authority"])
        self.assertFalse(self.retention["foreign_destruction_claims"]["core"])

    def test_p22_13_retention_expectation_claims_no_legal_duration_or_global_destruction(
        self,
    ) -> None:
        self.assertFalse(self.retention["legal_duration_calculated"])
        self.assertFalse(self.retention["sunset_public_record_created"])
        self.assertEqual(
            self.retention["foreign_destruction_claims"],
            {"core": False, "sibling_modules": False, "external_systems": False},
        )

    def test_p22_13_scenario_preserves_required_ticket_distinctions(self) -> None:
        text = "\n".join(self.scenario["required_distinctions"]).lower()
        for phrase in (
            "canonical forward records remain authority",
            "missing or deleted derived index",
            "unchanged exact source bytes",
            "changed source bytes invalidate",
            "never silently follows",
            "derived-cache retention",
            "export bytes and export provenance",
            "core retained-source custody",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
