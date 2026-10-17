"""Issue #57 recovery inventory integrity and bounded restart policy.

All Core registrations are immutable facts about physical page routes, not
inferences from the latest Page Target or from file names. An inconsistent
inventory cannot be repaired by picking a newer route or deleting an old one.
"""

from __future__ import annotations

from collections.abc import Sequence

from pds_core.routing_models import RouteRegistration

from portia.capture.contracts import route_binding_findings
from portia.models import PageTargetV1, PageTargetV2
from portia.storage.errors import PortiaCorruptionError


def audit_capture_route_inventory(
    pages: Sequence[PageTargetV1 | PageTargetV2],
    registrations: Sequence[RouteRegistration],
) -> None:
    """Fail closed on route-target gaps, duplicates and invalid exact bindings.

    This pure check accepts historical v1 Page Targets without rewriting them.
    It never selects one registration as authoritative when multiple exist.
    """
    by_identity: dict[str, PageTargetV1 | PageTargetV2] = {}
    for page in pages:
        identity = page.logical_id
        if identity is None or identity in by_identity:
            raise PortiaCorruptionError("capture inventory has duplicate target IDs")
        by_identity[identity] = page

    used: set[str] = set()
    route_ids: set[str] = set()
    for registration in registrations:
        locator = registration.locator
        route_id = locator.route_id
        if route_id in route_ids:
            raise PortiaCorruptionError("duplicate Core route identifier")
        route_ids.add(route_id)
        reference = registration.target
        if (
            reference.module_id != "portia"
            or reference.record_kind != "capture_page_target"
        ):
            raise PortiaCorruptionError("Core route points outside capture targets")
        page_id = reference.record_id
        if page_id not in by_identity:
            raise PortiaCorruptionError("Core route points to an absent Page Target")
        page = by_identity[page_id]
        if page_id in used:
            raise PortiaCorruptionError("multiple Core routes point to one Page Target")
        used.add(page_id)
        if locator.class_id != page.class_id or locator.work_id != page.work_id:
            raise PortiaCorruptionError("Core route and Page Target owner mismatch")
        if reference.contract_version != page.contract_version:
            raise PortiaCorruptionError("Core route Page Target version mismatch")
        if isinstance(page, PageTargetV2):
            if route_binding_findings(page, registration):
                raise PortiaCorruptionError("Core route target binding is invalid")
            details = registration.module_details
            if (
                details.get("page_target_contract_version") != "2"
                or details.get("template_identity")
                != page.to_dict()["template_identity"]
            ):
                raise PortiaCorruptionError("Core route template snapshot disagrees")
        # Historical v1 registrations are retained as read-only provenance:
        # only the exact reference, owner and contract version are required.
