"""Pure Slice 1 tests: no disk writes, routing registrations, or domain creation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pds_core.pds2 import serialize_pds2_payload
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ROUTE_REGISTRATION_SCHEMA_VERSION,
    ModuleRecordRef,
    ModuleWorkRef,
    RouteLocator,
    RouteRegistration,
)

from portia.capture import (
    CapturePreparationError,
    CapturePreparationRequest,
    CapturePreparationResult,
    PagePreparationResult,
    route_binding_findings,
)
from portia.models import CaptureBatchV1, PageTargetV1, PageTargetV2

ROOT = Path(__file__).resolve().parents[1]


def _wire(path: str) -> dict[str, object]:
    result = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def _batch() -> CaptureBatchV1:
    data = _wire("tests/fixtures/issue_20/valid/01-capture_batch.json")
    data["class_id"] = "class_english12_p3"
    data["work_id"] = "cbat_classroom_20261011"
    return CaptureBatchV1(data)


def _target() -> PageTargetV2:
    data = _wire(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    return PageTargetV2(data)


def _registration(
    target: PageTargetV1 | PageTargetV2,
    *,
    status: str = "active",
    target_version: str | None = None,
    target_id: str | None = None,
) -> RouteRegistration:
    assert target.class_id is not None
    assert target.work_id is not None
    assert target.logical_id is not None
    work = ModuleWorkRef(
        module_id="portia", class_id=target.class_id, work_id=target.work_id
    )
    return RouteRegistration(
        schema_version=ROUTE_REGISTRATION_SCHEMA_VERSION,
        locator=RouteLocator(schema=PDS2_SCHEMA, work=work, route_id="rt_synthetic_01"),
        target=ModuleRecordRef(
            module_id="portia",
            record_kind="capture_page_target",
            record_id=target_id or target.logical_id,
            contract_version=target_version or target.contract_version,
        ),
        created_at="2026-10-14T22:00:00-04:00",
        status=status,
        human_fallback="PORTIA PAPER",
    )


def test_current_page_binding_and_pds2_roundtrip() -> None:
    page = _target()
    registration = _registration(page)
    assert route_binding_findings(page, registration) == ()
    assert serialize_pds2_payload(registration.locator).startswith("PDS2|m=portia|")


def test_historical_page_v1_exact_version_is_read_compatible() -> None:
    prior = PageTargetV1(_wire("tests/fixtures/issue_20/valid/02-page_target.json"))
    assert route_binding_findings(prior, _registration(prior)) == ()
    assert route_binding_findings(prior, _registration(prior, target_version="2")) == (
        "registration_target_mismatch",
    )


def test_registration_must_be_active_and_exactly_targeted() -> None:
    page = _target()
    assert route_binding_findings(page, _registration(page, status="retired")) == (
        "registration_not_active",
    )
    wrong = _registration(page, target_id="ptgt_other")
    assert route_binding_findings(page, wrong) == (
        "registration_target_mismatch",
    )


def test_request_checks_current_models_exact_owner_and_duplicate_positions() -> None:
    batch, page = _batch(), _target()
    assert CapturePreparationRequest(batch, (page,)).targets == (page,)
    with pytest.raises(CapturePreparationError, match="at least one"):
        CapturePreparationRequest(batch, ())
    with pytest.raises(CapturePreparationError, match="unique"):
        CapturePreparationRequest(batch, (page, page))

    other = page.to_dict()
    other["class_id"] = "class_other"
    with pytest.raises(CapturePreparationError, match="class/work"):
        CapturePreparationRequest(batch, (PageTargetV2(other),))

    closed = batch.to_dict()
    closed["status"] = "closed"
    with pytest.raises(CapturePreparationError, match="must be open"):
        CapturePreparationRequest(CaptureBatchV1(closed), (page,))

    historical = PageTargetV1(
        _wire("tests/fixtures/issue_20/valid/02-page_target.json")
    )
    with pytest.raises(CapturePreparationError, match="page_target@2"):
        CapturePreparationRequest(batch, (historical,))  # type: ignore[arg-type]


def test_unverified_results_cannot_leak_printable_route_or_claim_ready() -> None:
    batch, page = _batch(), _target()
    reg = _registration(page)
    payload = serialize_pds2_payload(reg.locator)
    incomplete = PagePreparationResult(status="retryable", target=page)
    result = CapturePreparationResult(batch, (incomplete,))
    assert not result.ready_for_rendering
    assert not CapturePreparationResult(batch, ()).ready_for_rendering
    with pytest.raises(CapturePreparationError, match="unverified result"):
        PagePreparationResult(
            status="retryable", target=page, locator=reg.locator, payload=payload
        )
    with pytest.raises(CapturePreparationError, match="needs locator"):
        PagePreparationResult(status="verified", target=page)


def test_verified_result_requires_consistent_route_registration() -> None:
    batch, page = _batch(), _target()
    registration = _registration(page)
    payload = serialize_pds2_payload(registration.locator)
    verified = PagePreparationResult(
        status="verified",
        target=page,
        locator=registration.locator,
        payload=payload,
        registration=registration,
    )
    assert CapturePreparationResult(batch, (verified,)).ready_for_rendering
    with pytest.raises(CapturePreparationError, match="registration/target"):
        PagePreparationResult(
            status="verified",
            target=page,
            locator=registration.locator,
            payload=payload,
            registration=_registration(page, target_id="ptgt_other"),
        )
    with pytest.raises(CapturePreparationError, match="payload/locator"):
        PagePreparationResult(
            status="verified",
            target=page,
            locator=registration.locator,
            payload=serialize_pds2_payload(
                RouteLocator(
                    schema=PDS2_SCHEMA,
                    work=registration.locator.work,
                    route_id="rt_different",
                )
            ),
            registration=registration,
        )


def test_no_domain_mutations_in_slice1_api() -> None:
    """Only immutable Portia models/Core routing models are exposed here."""
    batch, page = _batch(), _target()
    _ = CapturePreparationRequest(batch, (page,))
    assert batch.work_kind == "capture_batch"
    assert page.record_type == "capture_page_target"
    assert page.to_dict()["page_purpose"] == "classroom_observation_capture"
    assert "existing_work_context" not in page.to_dict()
