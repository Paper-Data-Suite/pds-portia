"""Deterministic teacher-reference HTML rendering for Portia Issue #51 Slice 4.

The renderer consumes only the already-final closed-policy projection and the
exact contributing-source inventory.  It performs no Core roster or Actor
Directory lookup, reads no canonical records, adds no conclusions, and writes
nothing.  Output is one self-contained UTF-8/LF HTML document with no scripts,
network dependencies, remote assets, or hidden raw source JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Final

from portia.exports.discovery import TeacherReferenceSourceRef
from portia.exports.inventory import TeacherReferenceSourceInventory
from portia.exports.projection import (
    TeacherReferenceProjectionDecision,
    TeacherReferenceProjectionItem,
)
from portia.models.errors import PortiaLocalValidationError
from portia.models.json_values import FrozenJsonValue, thaw_json
from portia.models.references import ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes

TEACHER_REFERENCE_RENDERER_ID: Final[str] = "portia_deliberate_export_artifact_v1"
TEACHER_REFERENCE_ARTIFACT_FORMAT: Final[str] = "html"
TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE: Final[str] = "text/html"

_TEACHER_REFERENCE_DISCLAIMER: Final[str] = (
    "This is a local teacher-reference summary generated from selected Portia "
    "records. It is not an official institutional record, legal-completeness "
    "certification, disclosure record, delivery receipt, discipline "
    "determination, risk assessment, or statement that the represented "
    "information is complete."
)

_SECTION_ORDER: Final[tuple[str, ...]] = (
    "Work Context",
    "Participants / Participation",
    "Reported Information",
    "Direct Observations",
    "Review / Classification / Hypothesis / Determination",
    "Response / Communication",
    "Support / Goals / Intervention",
    "Implementation / Fidelity",
    "Follow-Up / Outcome / Reentry / Repair",
    "Correction / Disagreement Context",
)

_RECORD_SECTION: Final[dict[str, str]] = {
    "event": "Work Context",
    "support_process": "Work Context",
    "work_relationship": "Work Context",
    "event_participant": "Participants / Participation",
    "event_participant_role": "Participants / Participation",
    "support_process_participant": "Participants / Participation",
    "account": "Reported Information",
    "observation": "Direct Observations",
    "review": "Review / Classification / Hypothesis / Determination",
    "classification": "Review / Classification / Hypothesis / Determination",
    "hypothesis": "Review / Classification / Hypothesis / Determination",
    "determination": "Review / Classification / Hypothesis / Determination",
    "response": "Response / Communication",
    "communication": "Response / Communication",
    "support_need": "Support / Goals / Intervention",
    "support_goal": "Support / Goals / Intervention",
    "support": "Support / Goals / Intervention",
    "intervention": "Support / Goals / Intervention",
    "implementation": "Implementation / Fidelity",
    "fidelity": "Implementation / Fidelity",
    "follow_up": "Follow-Up / Outcome / Reentry / Repair",
    "outcome": "Follow-Up / Outcome / Reentry / Repair",
    "reentry": "Follow-Up / Outcome / Reentry / Repair",
    "repair": "Follow-Up / Outcome / Reentry / Repair",
    "amendment": "Correction / Disagreement Context",
    "statement_of_disagreement": "Correction / Disagreement Context",
}

_RECORD_LABEL: Final[dict[str, str]] = {
    "event": "Event",
    "support_process": "Support Process",
    "work_relationship": "Work Relationship",
    "event_participant": "Event Participant",
    "event_participant_role": "Event Participant Role",
    "support_process_participant": "Support Process Participant",
    "account": "Account",
    "observation": "Observation",
    "review": "Review",
    "classification": "Classification",
    "hypothesis": "Hypothesis",
    "determination": "Determination",
    "response": "Response",
    "communication": "Communication",
    "support_need": "Support Need",
    "support_goal": "Support Goal",
    "support": "Support",
    "intervention": "Intervention",
    "implementation": "Implementation",
    "fidelity": "Fidelity",
    "follow_up": "Follow-Up",
    "outcome": "Outcome",
    "reentry": "Reentry",
    "repair": "Repair",
    "amendment": "Amendment",
    "statement_of_disagreement": "Statement of Disagreement",
}


def _record_kind(source: TeacherReferenceSourceRef) -> str:
    if isinstance(source, ExactPortiaWorkRef):
        return source.work_kind
    return source.record_ref.record_kind


def _source_order(source: TeacherReferenceSourceRef) -> tuple[str, ...]:
    if isinstance(source, ExactPortiaWorkRef):
        return (
            source.class_id,
            source.work_kind,
            source.work_id,
            source.contract_version,
            "",
            "",
            "",
        )
    return (
        source.work_ref.class_id,
        source.work_ref.work_kind,
        source.work_ref.work_id,
        source.work_ref.contract_version,
        source.record_ref.record_kind,
        source.record_ref.record_id,
        source.record_ref.contract_version,
    )


def _label(name: str) -> str:
    return " ".join(piece.capitalize() for piece in name.split("_"))


def _scalar_html(value: object) -> str:
    if value is None:
        return '<span class="null-value">(null)</span>'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return escape(str(value), quote=True)
    if isinstance(value, str):
        return escape(value, quote=True).replace("\r\n", "\n").replace(
            "\r", "\n"
        ).replace("\n", "<br>\n")
    raise PortiaLocalValidationError(
        f"unsupported projected scalar type: {type(value).__name__}"
    )


def _value_html(value: FrozenJsonValue | None) -> str:
    thawed = thaw_json(value)
    if isinstance(thawed, dict):
        lines = ['<dl class="structured-value">']
        for key in sorted(thawed):
            lines.append(f"<dt>{escape(_label(key), quote=True)}</dt>")
            lines.append(f"<dd>{_python_value_html(thawed[key])}</dd>")
        lines.append("</dl>")
        return "\n".join(lines)
    if isinstance(thawed, list):
        lines = ['<ol class="structured-list">']
        for item in thawed:
            lines.append(f"<li>{_python_value_html(item)}</li>")
        lines.append("</ol>")
        return "\n".join(lines)
    return _scalar_html(thawed)


def _python_value_html(value: object) -> str:
    if isinstance(value, dict):
        lines = ['<dl class="structured-value">']
        for key in sorted(value):
            if not isinstance(key, str):
                raise PortiaLocalValidationError(
                    "projected mapping contains a non-string key"
                )
            lines.append(f"<dt>{escape(_label(key), quote=True)}</dt>")
            lines.append(f"<dd>{_python_value_html(value[key])}</dd>")
        lines.append("</dl>")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = ['<ol class="structured-list">']
        for item in value:
            lines.append(f"<li>{_python_value_html(item)}</li>")
        lines.append("</ol>")
        return "\n".join(lines)
    return _scalar_html(value)


def _included_by_source(
    decision: TeacherReferenceProjectionDecision,
) -> dict[TeacherReferenceSourceRef, tuple[TeacherReferenceProjectionItem, ...]]:
    grouped: dict[TeacherReferenceSourceRef, list[TeacherReferenceProjectionItem]] = {}
    for item in decision.items:
        if item.final_disposition != "included":
            continue
        if item.field_name is None or not item.value_present:
            raise PortiaLocalValidationError(
                "included teacher-reference projection item lacks bounded content"
            )
        grouped.setdefault(item.source_ref, []).append(item)
    return {
        source: tuple(items)
        for source, items in grouped.items()
    }


@dataclass(frozen=True, slots=True)
class TeacherReferenceRenderedArtifact:
    """One deterministic in-memory HTML candidate; no filesystem locator yet."""

    content: bytes
    fingerprint: ContentFingerprint
    renderer_id: str = TEACHER_REFERENCE_RENDERER_ID
    output_format: str = TEACHER_REFERENCE_ARTIFACT_FORMAT
    media_type: str = TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE

    def __post_init__(self) -> None:
        if self.renderer_id != TEACHER_REFERENCE_RENDERER_ID:
            raise PortiaLocalValidationError(
                "unsupported teacher-reference renderer identity"
            )
        if self.output_format != "html" or self.media_type != "text/html":
            raise PortiaLocalValidationError(
                "teacher-reference Slice 4 renderer supports HTML only"
            )
        if self.fingerprint != fingerprint_bytes(self.content):
            raise PortiaLocalValidationError(
                "teacher-reference artifact fingerprint does not match exact bytes"
            )
        try:
            text = self.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PortiaLocalValidationError(
                "teacher-reference artifact must be valid UTF-8"
            ) from exc
        if "\r" in text or not text.endswith("\n"):
            raise PortiaLocalValidationError(
                "teacher-reference artifact must use LF line endings with final LF"
            )

    @property
    def byte_length(self) -> int:
        return self.fingerprint.byte_length

    @property
    def representation_digest(self) -> str:
        return self.fingerprint.digest

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


class TeacherReferenceHtmlRenderer:
    """Render one final projection + exact inventory into deterministic HTML."""

    def render(
        self,
        decision: TeacherReferenceProjectionDecision,
        inventory: TeacherReferenceSourceInventory,
    ) -> TeacherReferenceRenderedArtifact:
        if not isinstance(decision, TeacherReferenceProjectionDecision):
            raise TypeError("decision must be a TeacherReferenceProjectionDecision")
        if not isinstance(inventory, TeacherReferenceSourceInventory):
            raise TypeError("inventory must be a TeacherReferenceSourceInventory")
        if not decision.is_final:
            raise PortiaLocalValidationError(
                "teacher-reference rendering requires completed manual review"
            )

        expected_refs = frozenset(decision.contributing_source_refs)
        actual_refs = frozenset(inventory.source_refs)
        if expected_refs != actual_refs or len(inventory.source_refs) != len(actual_refs):
            raise PortiaLocalValidationError(
                "teacher-reference renderer inventory does not bind exact contributing sources"
            )

        included = _included_by_source(decision)
        if not included:
            raise PortiaLocalValidationError(
                "teacher-reference renderer requires at least one included projection item"
            )
        if frozenset(included) != expected_refs:
            raise PortiaLocalValidationError(
                "teacher-reference included content and contributing-source inventory drifted"
            )

        section_sources: dict[str, list[TeacherReferenceSourceRef]] = {
            section: [] for section in _SECTION_ORDER
        }
        for source in sorted(included, key=_source_order):
            kind = _record_kind(source)
            section = _RECORD_SECTION.get(kind)
            if section is None:
                raise PortiaLocalValidationError(
                    f"no teacher-reference renderer section for {kind!r}"
                )
            section_sources[section].append(source)

        purpose = decision.discovery.scope.projection_purpose
        purpose_label = (
            "Teacher current work reference"
            if purpose == "teacher_current"
            else "Participant-specific work reference"
        )
        lines = [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            "<title>Portia Teacher Reference</title>",
            "</head>",
            "<body>",
            "<header>",
            "<h1>Portia Teacher Reference</h1>",
            f'<p class="reference-purpose">{escape(purpose_label, quote=True)}</p>',
            f'<p class="reference-disclaimer">{escape(_TEACHER_REFERENCE_DISCLAIMER, quote=True)}</p>',
            "</header>",
        ]

        for section in _SECTION_ORDER:
            sources = section_sources[section]
            if not sources:
                continue
            lines.append("<section>")
            lines.append(f"<h2>{escape(section, quote=True)}</h2>")
            for source in sources:
                kind = _record_kind(source)
                label = _RECORD_LABEL[kind]
                lines.append("<article>")
                lines.append(f"<h3>{escape(label, quote=True)}</h3>")
                lines.append('<dl class="record-fields">')
                for item in included[source]:
                    assert item.field_name is not None
                    lines.append(
                        f"<dt>{escape(_label(item.field_name), quote=True)}</dt>"
                    )
                    lines.append(f"<dd>{_value_html(item.value)}</dd>")
                lines.append("</dl>")
                lines.append("</article>")
            lines.append("</section>")

        lines.extend(["</body>", "</html>", ""])
        content = "\n".join(lines).encode("utf-8")
        return TeacherReferenceRenderedArtifact(
            content=content,
            fingerprint=fingerprint_bytes(content),
        )


__all__ = [
    "TEACHER_REFERENCE_ARTIFACT_FORMAT",
    "TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE",
    "TEACHER_REFERENCE_RENDERER_ID",
    "TeacherReferenceHtmlRenderer",
    "TeacherReferenceRenderedArtifact",
]
