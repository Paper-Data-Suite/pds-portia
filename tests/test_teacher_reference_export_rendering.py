from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.exports import (
    EXPORT_SOURCE_INVENTORY_ALGORITHM,
    TEACHER_REFERENCE_ARTIFACT_FORMAT,
    TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE,
    TEACHER_REFERENCE_RENDERER_ID,
    TeacherReferenceExportScope,
    TeacherReferenceHtmlRenderer,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
    TeacherReferenceSourceInventoryService,
    teacher_reference_source_inventory_digest,
)
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage import PortiaConflictError, PortiaRepository
from portia.storage.fingerprint import fingerprint_bytes
from portia.views import CurrentnessDecision
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_ref,
    event_wire,
    participant_record,
)

REVIEWED = "2026-09-29T19:00:00-04:00"
REVIEWER = {"type": "local_operator", "display_label": "Synthetic Teacher"}


class _Currentness:
    def evaluate(
        self,
        source_ref: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> CurrentnessDecision:
        return CurrentnessDecision(source_ref, "current", "synthetic_current")


def _communication() -> object:
    return parse_portia_record(
        "communication",
        "1",
        {
            "schema_version": "1",
            "record_type": "communication",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "communication_id": "comm_private",
            "status": "active",
            "sender": {"kind": "local_operator", "display_label": "Teacher"},
            "recipients": [
                {
                    "person": {
                        "kind": "roster_student",
                        "roster_student_ref": {
                            "class_id": "class_a",
                            "student_id": "student_1",
                        },
                        "display_snapshot": {"display_name": "Same Display"},
                    },
                    "participation": "participated",
                }
            ],
            "method": {"kind": "email"},
            "purpose": {"kind": "information_sharing"},
            "act_state": "completed",
            "privacy_scope": "restricted",
            "summary": "Private communication should never render.",
            "started_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _seed_event(
    tmp_path: Path,
    *,
    summary: str = "Synthetic neutral classroom context.",
    restricted_communication: bool = False,
) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    wire = event_wire()
    wire["summary"] = summary
    repository.create_work(event_ref(), parse_portia_record("event", "2", wire))
    repository.create_work_record(event_ref(), participant_record())
    if restricted_communication:
        repository.create_work_record(event_ref(), _communication())
    return repository


def _final_decision(
    tmp_path: Path,
    *,
    repository: PortiaRepository | None = None,
    include_summary: bool = True,
):
    repo = repository or _seed_event(tmp_path)
    discovery = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repo,
        currentness=_Currentness(),
    ).discover(TeacherReferenceExportScope("teacher_current", event_ref()))
    service = TeacherReferenceProjectionService(tmp_path, repository=repo)
    pending = service.project(discovery)
    choices = []
    for item in pending.unresolved_manual_items:
        assert item.field_name is not None
        include = item.source_ref == event_ref() and item.field_name == "summary"
        choices.append(
            TeacherReferenceManualReviewChoice(
                item.source_ref,
                item.field_name,
                "include_exact" if include and include_summary else "omit",
            )
        )
    resolved = service.resolve_manual_review(
        pending,
        choices,
        reviewed_at=REVIEWED,
        reviewed_by=REVIEWER,
    )
    return repo, resolved


def _inventory(tmp_path: Path, repository: PortiaRepository, decision: object):
    return TeacherReferenceSourceInventoryService(
        tmp_path,
        repository=repository,
    ).author(decision)


def test_inventory_uses_exact_contributing_canonical_fingerprints(
    tmp_path: Path,
) -> None:
    repository, decision = _final_decision(tmp_path)
    inventory = _inventory(tmp_path, repository, decision)
    value = inventory.to_dict()

    assert value["inventory_algorithm"] == "portia_export_source_inventory_v1"
    assert EXPORT_SOURCE_INVENTORY_ALGORITHM == "portia_export_source_inventory_v1"
    assert value["inventory_digest"] == teacher_reference_source_inventory_digest(
        inventory.entries
    )
    entries = inventory.entries
    sort_keys = [
        (
            str(entry["source_role"]),
            str(entry["source_kind"]),
            json.dumps(
                entry.get("work_ref", entry.get("work_record_ref")),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        for entry in entries
    ]
    assert sort_keys == sorted(sort_keys)

    assert entries
    for entry, source_ref in zip(entries, inventory.source_refs, strict=True):
        if isinstance(source_ref, ExactPortiaWorkRef):
            stored = repository.load_work(source_ref)
            assert entry["source_kind"] == "portia_work"
            assert entry["work_ref"] == source_ref.to_dict()
        else:
            stored = repository.load_work_record(
                source_ref.work_ref,
                source_ref.record_ref.record_kind,
                source_ref.record_ref.contract_version,
                source_ref.record_ref.record_id,
            )
            assert entry["source_kind"] == "portia_record"
            assert entry["work_record_ref"] == source_ref.to_dict()
        assert entry["representation_digest"] == stored.fingerprint.digest
        assert entry["byte_length"] == stored.fingerprint.byte_length
        assert "path" not in entry
        assert "workspace_relative_path" not in entry


def test_inventory_excludes_fully_withheld_considered_source(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path, restricted_communication=True)
    _, decision = _final_decision(tmp_path, repository=repository)
    inventory = _inventory(tmp_path, repository, decision)

    serialized = repr(inventory.to_dict())
    assert "comm_private" not in serialized
    assert "Private communication should never render." not in serialized
    assert set(inventory.source_refs) == set(decision.contributing_source_refs)


def test_inventory_rejects_source_drift_after_review(tmp_path: Path) -> None:
    repository, decision = _final_decision(tmp_path)
    prior = repository.load_work(event_ref())
    changed = event_wire(updated_at="2026-09-29T19:05:00-04:00")
    changed["summary"] = "Changed after review."
    repository.replace_work(
        event_ref(),
        parse_portia_record("event", "2", changed),
        expected=prior.fingerprint,
    )

    with pytest.raises(PortiaConflictError, match="changed after"):
        _inventory(tmp_path, repository, decision)


def test_html_rendering_is_deterministic_escaped_and_self_contained(
    tmp_path: Path,
) -> None:
    source_text = '<script>alert("x & y")</script>\nSecond line'
    repository = _seed_event(tmp_path, summary=source_text)
    _, decision = _final_decision(tmp_path, repository=repository)
    inventory = _inventory(tmp_path, repository, decision)
    renderer = TeacherReferenceHtmlRenderer()

    first = renderer.render(decision, inventory)
    second = renderer.render(decision, inventory)

    assert first.content == second.content
    assert first.fingerprint == second.fingerprint
    assert first.fingerprint == fingerprint_bytes(first.content)
    assert first.renderer_id == "portia_deliberate_export_artifact_v1"
    assert TEACHER_REFERENCE_RENDERER_ID == "portia_deliberate_export_artifact_v1"
    assert first.output_format == TEACHER_REFERENCE_ARTIFACT_FORMAT == "html"
    assert first.media_type == TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE == "text/html"
    assert first.byte_length == len(first.content)
    assert "\r" not in first.text
    assert first.text.endswith("\n")
    assert "<script>" not in first.text.lower()
    assert "&lt;script&gt;" in first.text
    assert "x &amp; y" in first.text
    assert "Second line" in first.text
    assert "http://" not in first.text
    assert "https://" not in first.text
    assert "<script" not in first.text.lower()
    assert " src=" not in first.text.lower()
    assert " href=" not in first.text.lower()


def test_html_preserves_semantic_sections_and_embedded_display_only(
    tmp_path: Path,
) -> None:
    repository, decision = _final_decision(tmp_path)
    inventory = _inventory(tmp_path, repository, decision)
    artifact = TeacherReferenceHtmlRenderer().render(decision, inventory)

    assert "Portia Teacher Reference" in artifact.text
    assert "local teacher-reference summary" in artifact.text
    assert "not an official institutional record" in artifact.text
    assert "Work Context" in artifact.text
    assert "Participants / Participation" in artifact.text
    assert "<h3>Event</h3>" in artifact.text
    assert "<h3>Event Participant</h3>" in artifact.text
    assert "Same Display" in artifact.text
    assert "student_1" not in artifact.text
    assert "roster_student_ref" not in artifact.text
    assert "record_type" not in artifact.text
    assert "schema_version" not in artifact.text
    assert "operation_id" not in artifact.text
    assert inventory.inventory_digest not in artifact.text
    assert str(tmp_path) not in artifact.text


def test_renderer_outputs_only_final_included_projection_content(tmp_path: Path) -> None:
    repository = _seed_event(tmp_path, restricted_communication=True)
    _, decision = _final_decision(tmp_path, repository=repository)
    inventory = _inventory(tmp_path, repository, decision)
    artifact = TeacherReferenceHtmlRenderer().render(decision, inventory)

    assert "Private communication should never render." not in artifact.text
    assert "Communication" not in artifact.text
    assert "requires_manual_review" not in artifact.text
    assert "withheld" not in artifact.text.lower()
    assert "unavailable" not in artifact.text.lower()


def test_inventory_and_renderer_are_zero_write(tmp_path: Path) -> None:
    repository, decision = _final_decision(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    inventory = _inventory(tmp_path, repository, decision)
    TeacherReferenceHtmlRenderer().render(decision, inventory)

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after
