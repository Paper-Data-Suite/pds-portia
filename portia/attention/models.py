"""Immutable presentation-neutral native attention contracts for Portia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, cast

from portia.attention.taxonomy import (
    ATTENTION_CLASSES,
    ATTENTION_DEFINITIONS,
    AttentionClass,
    require_attention_class,
    require_attention_definition,
)
from portia.attention.timing import TimingDecision
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)

PORTIA_ATTENTION_CONTRACT_VERSION: Final[str] = "1"
PORTIA_ATTENTION_PARTIAL_NOTICE: Final[str] = "portia_attention_partial"
PORTIA_ATTENTION_UNAVAILABLE_NOTICE: Final[str] = "portia_attention_unavailable"

AttentionEvaluation: TypeAlias = Literal["evaluated", "unavailable"]
AttentionScopeKind: TypeAlias = Literal["workspace", "class", "work"]
OpaqueAttentionSourceKind: TypeAlias = Literal[
    "quarantine",
    "integrity_finding",
    "recovery_scope",
    "derived_projection",
]


def _require_tuple(value: object, *, field_name: str) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise PortiaLocalValidationError(f"{field_name} must be a tuple")
    return value


@dataclass(frozen=True, slots=True)
class PortiaAttentionScope:
    """Explicit native attention authority boundary.

    Workspace evaluation must be opted into with ``workspace=True``. A work
    scope may also repeat its class ID, but if it does the two values must agree.
    """

    workspace: bool = False
    class_id: str | None = None
    work_ref: ExactPortiaWorkRef | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace, bool):
            raise PortiaLocalValidationError(
                "workspace scope flag must be a bool"
            )

        if self.workspace:
            if self.class_id is not None or self.work_ref is not None:
                raise PortiaLocalValidationError(
                    "workspace scope cannot be combined with class or work scope"
                )
            return

        if self.class_id is not None:
            validate_external_id(self.class_id, "attention class_id")

        if self.work_ref is not None:
            if not isinstance(self.work_ref, ExactPortiaWorkRef):
                raise PortiaLocalValidationError(
                    "attention work_ref must be an ExactPortiaWorkRef"
                )
            if (
                self.class_id is not None
                and self.class_id != self.work_ref.class_id
            ):
                raise PortiaLocalValidationError(
                    "attention class scope must agree with exact work class_id"
                )
            return

        if self.class_id is None:
            raise PortiaLocalValidationError(
                "attention scope must explicitly select workspace, class, or work"
            )

    @property
    def kind(self) -> AttentionScopeKind:
        if self.workspace:
            return "workspace"
        if self.work_ref is not None:
            return "work"
        return "class"

    @classmethod
    def workspace_scope(cls) -> "PortiaAttentionScope":
        return cls(workspace=True)

    @classmethod
    def class_scope(cls, class_id: str) -> "PortiaAttentionScope":
        return cls(class_id=class_id)

    @classmethod
    def work_scope(
        cls,
        work_ref: ExactPortiaWorkRef,
        *,
        class_id: str | None = None,
    ) -> "PortiaAttentionScope":
        return cls(class_id=class_id, work_ref=work_ref)


@dataclass(frozen=True, slots=True)
class PortiaAttentionQuery:
    """One deterministic native attention request."""

    scope: PortiaAttentionScope
    as_of: ExplicitOffsetTimestamp
    active_school_year: str | None = None
    attention_codes: tuple[str, ...] = ()
    attention_classes: tuple[AttentionClass, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PortiaAttentionScope):
            raise PortiaLocalValidationError(
                "attention query requires a PortiaAttentionScope"
            )
        if not isinstance(self.as_of, ExplicitOffsetTimestamp):
            raise PortiaLocalValidationError(
                "attention query as_of must be an ExplicitOffsetTimestamp"
            )

        if self.active_school_year is not None:
            validate_external_id(
                self.active_school_year,
                "attention active_school_year",
            )

        raw_codes = _require_tuple(
            self.attention_codes,
            field_name="attention_codes",
        )
        if not all(isinstance(code, str) for code in raw_codes):
            raise PortiaLocalValidationError(
                "attention_codes must contain only strings"
            )
        codes = cast(tuple[str, ...], raw_codes)
        if len(set(codes)) != len(codes):
            raise PortiaLocalValidationError(
                "attention_codes cannot contain duplicates"
            )
        for code in codes:
            require_attention_definition(code)

        raw_classes = _require_tuple(
            self.attention_classes,
            field_name="attention_classes",
        )
        if not all(isinstance(value, str) for value in raw_classes):
            raise PortiaLocalValidationError(
                "attention_classes must contain only strings"
            )
        classes = cast(tuple[str, ...], raw_classes)
        if len(set(classes)) != len(classes):
            raise PortiaLocalValidationError(
                "attention_classes cannot contain duplicates"
            )
        for attention_class in classes:
            require_attention_class(attention_class)


@dataclass(frozen=True, slots=True)
class FollowUpScheduleQuery:
    """Separate schedule query; future scheduled work is not attention."""

    scope: PortiaAttentionScope
    as_of: ExplicitOffsetTimestamp
    active_school_year: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, PortiaAttentionScope):
            raise PortiaLocalValidationError(
                "Follow-Up schedule query requires a PortiaAttentionScope"
            )
        if not isinstance(self.as_of, ExplicitOffsetTimestamp):
            raise PortiaLocalValidationError(
                "Follow-Up schedule query as_of must be an ExplicitOffsetTimestamp"
            )
        if self.active_school_year is not None:
            validate_external_id(
                self.active_school_year,
                "Follow-Up schedule active_school_year",
            )


@dataclass(frozen=True, slots=True)
class OpaqueAttentionSourceRef:
    """Privacy-safe opaque identity for technical attention sources."""

    kind: OpaqueAttentionSourceKind
    identifier: str

    def __post_init__(self) -> None:
        if self.kind not in {
            "quarantine",
            "integrity_finding",
            "recovery_scope",
            "derived_projection",
        }:
            raise PortiaLocalValidationError(
                f"unsupported opaque attention source kind: {self.kind!r}"
            )
        validate_external_id(
            self.identifier,
            "opaque attention source identifier",
        )


AttentionSourceRef: TypeAlias = (
    ExactPortiaWorkRef | ExactPortiaWorkRecordRef | OpaqueAttentionSourceRef
)


@dataclass(frozen=True, slots=True)
class PortiaAttentionContext:
    """Low-density class/work context, never a student dossier."""

    class_id: str | None = None
    work_ref: ExactPortiaWorkRef | None = None

    def __post_init__(self) -> None:
        if self.class_id is not None:
            validate_external_id(
                self.class_id,
                "attention context class_id",
            )
        if self.work_ref is not None:
            if not isinstance(self.work_ref, ExactPortiaWorkRef):
                raise PortiaLocalValidationError(
                    "attention context work_ref must be an ExactPortiaWorkRef"
                )
            if (
                self.class_id is not None
                and self.class_id != self.work_ref.class_id
            ):
                raise PortiaLocalValidationError(
                    "attention context class_id must agree with work_ref"
                )


@dataclass(frozen=True, slots=True)
class PortiaAttentionItem:
    """One bounded current attention fact."""

    code: str
    source_ref: AttentionSourceRef
    context: PortiaAttentionContext = PortiaAttentionContext()
    reason_codes: tuple[str, ...] = ()
    timing: TimingDecision | None = None

    def __post_init__(self) -> None:
        definition = require_attention_definition(self.code)
        if not isinstance(
            self.source_ref,
            (
                ExactPortiaWorkRef,
                ExactPortiaWorkRecordRef,
                OpaqueAttentionSourceRef,
            ),
        ):
            raise PortiaLocalValidationError(
                "attention source_ref must be an exact or opaque Portia source"
            )
        if not isinstance(self.context, PortiaAttentionContext):
            raise PortiaLocalValidationError(
                "attention context must be a PortiaAttentionContext"
            )

        raw_reasons = _require_tuple(
            self.reason_codes,
            field_name="reason_codes",
        )
        if not all(isinstance(reason, str) for reason in raw_reasons):
            raise PortiaLocalValidationError(
                "attention reason_codes must contain only strings"
            )
        reasons = cast(tuple[str, ...], raw_reasons)
        if len(set(reasons)) != len(reasons):
            raise PortiaLocalValidationError(
                "attention reason_codes cannot contain duplicates"
            )
        for reason in reasons:
            validate_external_id(reason, "attention reason_code")

        if self.timing is not None and not isinstance(
            self.timing,
            TimingDecision,
        ):
            raise PortiaLocalValidationError(
                "attention timing must be a TimingDecision"
            )

        required_timing = definition.timing_classification
        if required_timing is None:
            if self.timing is not None:
                raise PortiaLocalValidationError(
                    "attention timing is not defined for this attention code"
                )
        else:
            if self.timing is None:
                raise PortiaLocalValidationError(
                    "timing-bearing attention code requires a timing decision"
                )
            if self.timing.classification != required_timing:
                raise PortiaLocalValidationError(
                    "attention timing classification must match the native definition"
                )

        if isinstance(self.source_ref, ExactPortiaWorkRef):
            source_work: ExactPortiaWorkRef | None = self.source_ref
        elif isinstance(self.source_ref, ExactPortiaWorkRecordRef):
            source_work = self.source_ref.work_ref
        else:
            source_work = None

        if (
            source_work is not None
            and self.context.class_id is not None
            and source_work.class_id != self.context.class_id
        ):
            raise PortiaLocalValidationError(
                "attention source class must agree with context class_id"
            )
        if (
            source_work is not None
            and self.context.work_ref is not None
            and source_work != self.context.work_ref
        ):
            raise PortiaLocalValidationError(
                "attention exact source work must agree with context work_ref"
            )

        if definition.attention_class not in ATTENTION_CLASSES:
            raise RuntimeError("attention taxonomy contains an invalid class")

    @property
    def attention_class(self) -> AttentionClass:
        return require_attention_definition(self.code).attention_class


@dataclass(frozen=True, slots=True)
class FollowUpScheduleItem:
    """One current Follow-Up and its exact schedule classification."""

    source_ref: ExactPortiaWorkRecordRef
    timing: TimingDecision

    def __post_init__(self) -> None:
        if not isinstance(self.source_ref, ExactPortiaWorkRecordRef):
            raise PortiaLocalValidationError(
                "Follow-Up schedule source must be an ExactPortiaWorkRecordRef"
            )
        if self.source_ref.record_ref.record_kind != "follow_up":
            raise PortiaLocalValidationError(
                "Follow-Up schedule source must reference a follow_up record"
            )
        if not isinstance(self.timing, TimingDecision):
            raise PortiaLocalValidationError(
                "Follow-Up schedule timing must be a TimingDecision"
            )


@dataclass(frozen=True, slots=True)
class PortiaAttentionSummary:
    """Aggregate count for one stable native attention definition."""

    code: str
    label: str
    count: int
    count_unit: str
    attention_class: AttentionClass

    def __post_init__(self) -> None:
        definition = require_attention_definition(self.code)
        if self.label != definition.label:
            raise PortiaLocalValidationError(
                "attention summary label must match the native definition"
            )
        if (
            not isinstance(self.count, int)
            or isinstance(self.count, bool)
            or self.count <= 0
        ):
            raise PortiaLocalValidationError(
                "attention summary count must be a positive integer"
            )
        if self.count_unit != definition.count_unit:
            raise PortiaLocalValidationError(
                "attention summary count_unit must match the native definition"
            )
        if self.attention_class != definition.attention_class:
            raise PortiaLocalValidationError(
                "attention summary class must match the native definition"
            )


@dataclass(frozen=True, slots=True)
class PortiaAttentionNotice:
    """Bounded query-level partial/unavailable notice."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if self.code not in {
            PORTIA_ATTENTION_PARTIAL_NOTICE,
            PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
        }:
            raise PortiaLocalValidationError(
                f"unsupported Portia attention notice code: {self.code!r}"
            )
        if (
            not isinstance(self.message, str)
            or not 1 <= len(self.message) <= 240
        ):
            raise PortiaLocalValidationError(
                "attention notice message must contain 1 to 240 characters"
            )
        if "\n" in self.message or "\r" in self.message:
            raise PortiaLocalValidationError(
                "attention notice message must be single-line"
            )


@dataclass(frozen=True, slots=True)
class PortiaAttentionReport:
    """Presentation-neutral deterministic result for one native query."""

    query: PortiaAttentionQuery
    evaluation: AttentionEvaluation
    summaries: tuple[PortiaAttentionSummary, ...] = ()
    items: tuple[PortiaAttentionItem, ...] = ()
    notices: tuple[PortiaAttentionNotice, ...] = ()
    contract_version: str = PORTIA_ATTENTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.query, PortiaAttentionQuery):
            raise PortiaLocalValidationError(
                "attention report query must be a PortiaAttentionQuery"
            )
        if self.evaluation not in {"evaluated", "unavailable"}:
            raise PortiaLocalValidationError(
                f"unsupported attention evaluation: {self.evaluation!r}"
            )
        if self.contract_version != PORTIA_ATTENTION_CONTRACT_VERSION:
            raise PortiaLocalValidationError(
                "unsupported Portia native attention contract version"
            )

        _require_tuple(self.summaries, field_name="summaries")
        if not all(
            isinstance(value, PortiaAttentionSummary)
            for value in self.summaries
        ):
            raise PortiaLocalValidationError(
                "summaries contains an unsupported value"
            )

        _require_tuple(self.items, field_name="items")
        if not all(
            isinstance(value, PortiaAttentionItem) for value in self.items
        ):
            raise PortiaLocalValidationError(
                "items contains an unsupported value"
            )

        _require_tuple(self.notices, field_name="notices")
        if not all(
            isinstance(value, PortiaAttentionNotice) for value in self.notices
        ):
            raise PortiaLocalValidationError(
                "notices contains an unsupported value"
            )

        if self.evaluation == "unavailable":
            if self.summaries or self.items:
                raise PortiaLocalValidationError(
                    "unavailable attention reports cannot contain summaries or items"
                )
            if not any(
                notice.code == PORTIA_ATTENTION_UNAVAILABLE_NOTICE
                for notice in self.notices
            ):
                raise PortiaLocalValidationError(
                    "unavailable attention reports require an unavailable notice"
                )
        elif any(
            notice.code == PORTIA_ATTENTION_UNAVAILABLE_NOTICE
            for notice in self.notices
        ):
            raise PortiaLocalValidationError(
                "evaluated attention reports cannot carry an unavailable notice"
            )

    @property
    def scope(self) -> PortiaAttentionScope:
        """Return the exact scope carried by the originating query."""
        return self.query.scope

    @property
    def as_of(self) -> ExplicitOffsetTimestamp:
        """Return the exact caller-supplied evaluation timestamp."""
        return self.query.as_of

def _source_sort_key(source_ref: AttentionSourceRef) -> tuple[str, ...]:
    if isinstance(source_ref, ExactPortiaWorkRecordRef):
        work = source_ref.work_ref
        record = source_ref.record_ref
        return (
            "record",
            work.class_id,
            work.work_kind,
            work.work_id,
            work.contract_version,
            record.record_kind,
            record.record_id,
            record.contract_version,
        )
    if isinstance(source_ref, ExactPortiaWorkRef):
        return (
            "work",
            source_ref.class_id,
            source_ref.work_kind,
            source_ref.work_id,
            source_ref.contract_version,
        )
    return ("opaque", source_ref.kind, source_ref.identifier)


def attention_item_sort_key(
    item: PortiaAttentionItem,
) -> tuple[object, ...]:
    """Deterministic ordering only; this key carries no priority semantics."""
    definition = require_attention_definition(item.code)
    timing_key = (
        ("", "", "")
        if item.timing is None
        else item.timing.deterministic_key()
    )
    context_class = item.context.class_id or ""
    context_work = (
        _source_sort_key(item.context.work_ref)
        if item.context.work_ref is not None
        else ("",)
    )
    return (
        definition.definition_order,
        timing_key,
        context_class,
        context_work,
        _source_sort_key(item.source_ref),
        item.reason_codes,
    )


def _query_accepts_item(
    query: PortiaAttentionQuery,
    item: PortiaAttentionItem,
) -> bool:
    if query.attention_codes and item.code not in query.attention_codes:
        return False
    if (
        query.attention_classes
        and item.attention_class not in query.attention_classes
    ):
        return False
    return True


def build_attention_report(
    query: PortiaAttentionQuery,
    items: tuple[PortiaAttentionItem, ...] = (),
    *,
    notices: tuple[PortiaAttentionNotice, ...] = (),
    evaluation: AttentionEvaluation = "evaluated",
) -> PortiaAttentionReport:
    """Filter, order, and aggregate already-authoritative native items.

    This helper performs no discovery, storage access, repair, recovery,
    acknowledgement, suppression, Quarantine mutation, or derived rebuild.
    """
    if not isinstance(query, PortiaAttentionQuery):
        raise PortiaLocalValidationError(
            "build_attention_report requires a PortiaAttentionQuery"
        )

    _require_tuple(items, field_name="items")
    if not all(isinstance(item, PortiaAttentionItem) for item in items):
        raise PortiaLocalValidationError(
            "items contains an unsupported value"
        )

    _require_tuple(notices, field_name="notices")
    if not all(
        isinstance(notice, PortiaAttentionNotice) for notice in notices
    ):
        raise PortiaLocalValidationError(
            "notices contains an unsupported value"
        )

    if evaluation == "unavailable":
        return PortiaAttentionReport(
            query=query,
            evaluation="unavailable",
            summaries=(),
            items=(),
            notices=notices,
        )
    if evaluation != "evaluated":
        raise PortiaLocalValidationError(
            f"unsupported attention evaluation: {evaluation!r}"
        )

    selected = tuple(
        sorted(
            (
                item
                for item in items
                if _query_accepts_item(query, item)
            ),
            key=attention_item_sort_key,
        )
    )

    counts: dict[str, int] = {}
    for item in selected:
        counts[item.code] = counts.get(item.code, 0) + 1

    summaries = tuple(
        PortiaAttentionSummary(
            code=definition.code,
            label=definition.label,
            count=counts[definition.code],
            count_unit=definition.count_unit,
            attention_class=definition.attention_class,
        )
        for definition in ATTENTION_DEFINITIONS
        if counts.get(definition.code, 0) > 0
    )

    return PortiaAttentionReport(
        query=query,
        evaluation="evaluated",
        summaries=summaries,
        items=selected,
        notices=notices,
    )
