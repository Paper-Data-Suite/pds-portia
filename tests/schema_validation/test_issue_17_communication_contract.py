from __future__ import annotations

from datetime import datetime
import json
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
    / "issue-17"
    / "communication"
)
COMMUNICATION_SCHEMA_PATH = "schemas/v1/communications/communication.schema.json"

COMMUNICATION_LIFECYCLE = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

COMMUNICATION_SUPERSESSION_REASONS = {
    "sender_corrected",
    "recipient_corrected",
    "method_corrected",
    "purpose_corrected",
    "timing_corrected",
    "content_summary_corrected",
    "attachment_corrected",
    "relation_corrected",
    "privacy_scope_corrected",
    "duplicate_consolidated",
    "work_root_corrected",
    "contract_migrated",
    "other",
}

RELATION_KIND_REQUIREMENTS = {
    "responds_to": {"communication"},
    "conveys_determination": {"determination"},
    "documents_handoff_for": {"response"},
    "relates_to_response": {"response"},
    "account_from_communication": {"account"},
}


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _person_identity(person: dict[str, Any]) -> tuple[Any, ...]:
    kind = person["kind"]
    if kind == "roster_student":
        ref = person["roster_student_ref"]
        return (kind, ref["class_id"], ref["student_id"])
    if kind == "actor":
        return (kind, person["actor_ref"]["actor_id"])
    if kind == "local_operator":
        return (kind, person["display_label"])
    if kind == "descriptive_person":
        return (
            kind,
            person["description_type"],
            person["display_label"],
        )
    return (
        kind,
        person["identity_status"],
        person.get("display_label"),
    )


def _work_record_identity(
    ref: dict[str, Any],
) -> tuple[str, str, str, str, str]:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        work["class_id"],
        work["work_kind"],
        work["work_id"],
        record["record_id"],
        record["contract_version"],
    )


def _same_work(
    communication: dict[str, Any],
    ref: dict[str, Any],
) -> bool:
    work = ref["work_ref"]
    return (
        work["class_id"] == communication["class_id"]
        and work["work_kind"] == communication["work_kind"]
        and work["work_id"] == communication["work_id"]
    )


def application_errors(
    communication: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    created_at = _parse(communication["created_at"])
    updated_at = _parse(communication["updated_at"])
    started_at = _parse(communication["started_at"])
    ended_at = (
        _parse(communication["ended_at"])
        if "ended_at" in communication
        else None
    )

    if updated_at < created_at:
        errors.append("updated_at precedes created_at")
    if started_at > updated_at:
        errors.append("Communication starts after the recorded revision")
    if ended_at is not None and ended_at < started_at:
        errors.append("Communication ended_at precedes started_at")
    if ended_at is not None and ended_at > updated_at:
        errors.append("Communication ended_at follows the recorded revision")

    creation = communication["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and communication["status"] != "proposed"
    ):
        errors.append("paper/import activation requires accepted review history")

    if communication["work_kind"] == "support_process":
        errors.append(
            "Support Process owner is unavailable until Issue #18 publishes "
            "the canonical Support Process contract"
        )

    historical_only = (
        creation["type"] in {"paper_capture", "import"}
        and communication["status"] == "proposed"
    )

    if communication["method"]["kind"] == "unknown" and not historical_only:
        errors.append("unknown method is historical/import-only")
    if communication["purpose"]["kind"] == "unknown" and not historical_only:
        errors.append("unknown purpose is historical/import-only")
    if communication["act_state"] == "unknown" and not historical_only:
        errors.append("unknown act state is historical/import-only")
    if communication["privacy_scope"] == "unknown" and not historical_only:
        errors.append("unknown privacy scope is historical/import-only")

    sender = communication["sender"]
    if (
        communication["status"] == "active"
        and sender["kind"] == "unidentified_person"
    ):
        errors.append("active current-use sender must be resolved")

    recipient_keys = []
    for item in communication["recipients"]:
        person = item["person"]
        recipient_keys.append(_person_identity(person))

        if item["participation"] == "unknown" and not historical_only:
            errors.append("unknown participation is historical/import-only")

        if (
            communication["status"] == "active"
            and person["kind"] == "unidentified_person"
        ):
            errors.append("active current-use recipient must be resolved")

        endpoint = item.get("endpoint_ref")
        if endpoint is not None:
            actor_id = person["actor_ref"]["actor_id"]
            if endpoint["actor_id"] != actor_id:
                errors.append("Contact Point Actor does not match recipient Actor")

    if len(recipient_keys) != len(set(recipient_keys)):
        errors.append("logical recipient identity repeated")

    if (
        communication["act_state"] == "recipient_unavailable"
        and any(
            item["participation"] == "participated"
            for item in communication["recipients"]
        )
    ):
        errors.append(
            "recipient-unavailable Communication cannot establish participation"
        )

    for attachment in communication.get("attachments", []):
        kind = attachment["kind"]
        if kind == "module_record":
            ref = attachment["module_work_record_ref"]
            if (
                ref["work_ref"]["module_id"]
                != ref["record_ref"]["module_id"]
            ):
                errors.append("module attachment has mismatched module IDs")
        elif kind == "portia_record":
            ref = attachment["record_ref"]
            record = ref["record_ref"]
            if (
                _same_work(communication, ref)
                and record["record_kind"] == "communication"
                and record["record_id"]
                == communication["communication_id"]
            ):
                errors.append("Communication cannot attach itself")

    relation_keys = []
    for relation in communication.get("relations", []):
        ref = relation["record_ref"]
        record = ref["record_ref"]
        relation_kind = relation["relation"]

        relation_keys.append(
            (
                relation_kind,
                ref["work_ref"]["class_id"],
                ref["work_ref"]["work_kind"],
                ref["work_ref"]["work_id"],
                record["record_kind"],
                record["record_id"],
                record["contract_version"],
            )
        )

        required_kinds = RELATION_KIND_REQUIREMENTS.get(relation_kind)
        if (
            required_kinds is not None
            and record["record_kind"] not in required_kinds
        ):
            errors.append(
                f"{relation_kind} relation has incompatible record kind"
            )

        if relation_kind == "responds_to":
            if not _same_work(communication, ref):
                errors.append("responds_to must remain within the owning work")
            if (
                record["record_kind"] == "communication"
                and record["record_id"]
                == communication["communication_id"]
            ):
                errors.append("Communication cannot respond to itself")

    if len(relation_keys) != len(set(relation_keys)):
        errors.append("logical Communication relation repeated")

    supersedes = communication.get("supersedes", [])
    if supersedes:
        identities = [
            _work_record_identity(item["work_record_ref"])
            for item in supersedes
        ]
        reasons = [item["reason"] for item in supersedes]

        if len(identities) != len(set(identities)):
            errors.append("predecessor Communication identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        for item in supersedes:
            ref = item["work_record_ref"]
            record = ref["record_ref"]
            same_work = _same_work(communication, ref)
            same_id = (
                record["record_id"]
                == communication["communication_id"]
            )
            reason = item["reason"]

            if (
                same_work
                and same_id
                and reason != "contract_migrated"
            ):
                errors.append("Communication replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append(
                        "work-root correction requires different work"
                    )
                if not same_id:
                    errors.append(
                        "work-root correction must preserve Communication ID"
                    )
            elif reason != "contract_migrated" and not same_work:
                errors.append(
                    "ordinary Communication correction cannot cross work roots"
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


class Issue17CommunicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "communication",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")
        cls.schema = load_json(
            REPO_ROOT / COMMUNICATION_SCHEMA_PATH
        )

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 17)
        self.assertEqual(self.manifest["contract"], "communication")
        self.assertEqual(self.manifest["version"], "1")
        self.assertEqual(len(self.manifest["valid"]), 14)
        self.assertEqual(len(self.manifest["invalid"]), 22)
        self.assertEqual(
            len(self.manifest["application_invalid"]),
            33,
        )

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "valid" / filename
                )
                structural = list(
                    self.validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(
                        error.message for error in structural
                    ),
                )
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "invalid" / filename
                )
                self.assertTrue(
                    list(self.validator.iter_errors(value))
                )

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "application-invalid"
                    / filename
                )
                structural = list(
                    self.validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(
                        error.message for error in structural
                    ),
                )

    def test_application_invalid_fixtures_fail_rules(self) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "application-invalid"
                    / filename
                )
                self.assertTrue(application_errors(value))

    def test_work_local_and_message_archive_boundaries(self) -> None:
        properties = self.schema["properties"]
        self.assertEqual(
            set(properties["work_kind"]["enum"]),
            {"event", "support_process"},
        )
        self.assertNotIn("body", properties)
        self.assertNotIn("message_body", properties)
        self.assertNotIn("delivery_status", properties)
        self.assertNotIn("read_at", properties)
        self.assertNotIn("legal_notice_satisfied", properties)
        self.assertNotIn("family_engagement_score", properties)

        summary = properties["summary"]
        self.assertEqual(summary["allOf"][1]["maxLength"], 4000)

    def test_recipient_participation_and_contact_point_boundaries(
        self,
    ) -> None:
        recipient = self.schema["$defs"]["recipient"]
        self.assertIn("participation", recipient["required"])
        self.assertEqual(
            set(
                recipient["properties"]["participation"]["enum"]
            ),
            {"participated", "not_established", "unknown"},
        )
        endpoint = recipient["properties"]["endpoint_ref"]
        endpoint_text = json.dumps(endpoint)
        self.assertIn(
            "exact-actor-contact-point-ref.schema.json",
            endpoint_text,
        )
        self.assertNotIn("email", recipient["properties"])
        self.assertNotIn("phone", recipient["properties"])

    def test_attachments_are_schema_local_and_closed(self) -> None:
        attachment_text = json.dumps(
            self.schema["$defs"]["attachment"]
        )
        self.assertNotIn(
            "source-artifact-ref.schema.json",
            attachment_text,
        )
        self.assertEqual(
            {
                "workspaceFileAttachment",
                "portiaRecordAttachment",
                "moduleRecordAttachment",
                "externalRecordAttachment",
            },
            {
                item["$ref"].split("/")[-1]
                for item in self.schema["$defs"]["attachment"]["oneOf"]
            },
        )

    def test_relations_are_typed_exact_record_links(self) -> None:
        relation = self.schema["$defs"]["relation"]
        self.assertTrue(
            relation["properties"]["record_ref"]["$ref"].endswith(
                "/exact-portia-work-record-ref.schema.json"
            )
        )
        values = set(
            relation["properties"]["relation"]["enum"]
        )
        self.assertTrue(
            {
                "responds_to",
                "conveys_determination",
                "documents_handoff_for",
                "relates_to_response",
                "account_from_communication",
            }.issubset(values)
        )

    def test_lifecycle_and_supersession_vocabularies_are_closed(
        self,
    ) -> None:
        self.assertEqual(
            set(self.schema["properties"]["status"]["enum"]),
            set(COMMUNICATION_LIFECYCLE),
        )
        reasons = set(
            self.schema["$defs"]["supersessionEntry"]
            ["properties"]["reason"]["enum"]
        )
        self.assertEqual(
            reasons,
            COMMUNICATION_SUPERSESSION_REASONS,
        )

    def test_application_invariants_declare_issue_17_boundaries(
        self,
    ) -> None:
        invariants = set(
            self.schema["x-portia-application-invariants"]
        )
        required = {
            "portia.communication.support_process_current_use_requires_published_owner",
            "portia.communication.recipient_logical_identity_unique",
            "portia.communication.recipient_listing_not_participation",
            "portia.communication.endpoint_actor_owner_agreement",
            "portia.communication.contact_preference_not_consent",
            "portia.communication.contact_verification_not_delivery",
            "portia.communication.repeated_attempt_separate_record",
            "portia.communication.summary_not_account_evidence",
            "portia.communication.attachment_external_inert",
            "portia.communication.relation_kind_compatibility",
            "portia.communication.amendment_prohibited_v1",
            "portia.communication.no_silent_successor_following",
            "portia.communication.no_engagement_scoring",
            "portia.communication.no_delivery_inference",
            "portia.communication.no_automatic_external_send",
        }
        self.assertTrue(required.issubset(invariants))


if __name__ == "__main__":
    unittest.main()
