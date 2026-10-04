"""Establish isolated installed-wheel acceptance foundations for Issue #53.

Slice 1 owns the exact-artifact, environment-isolation, and deep-workspace
boundary. Later Issue #53 slices extend the installed probe with the continuous
production-service story while preserving this single environment and workspace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

CORE_064_FILENAME: Final[str] = "pds_core-0.6.4-py3-none-any.whl"
CORE_064_SHA256: Final[str] = (
    "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
)
EXPECTED_CORE_VERSION: Final[str] = "0.6.4"
EXPECTED_PORTIA_VERSION: Final[str] = "0.2.0"
TARGET_DEEP_WORKSPACE_LENGTH: Final[int] = 119
SYNTHETIC_SCHOOL_YEAR: Final[str] = "2026-2027"
PRIMARY_CLASS_ID: Final[str] = "eng10_p2_2026"
SECONDARY_CLASS_ID: Final[str] = "journalism_p6_2026"
COLLISION_STUDENT_ID: Final[str] = "student_shared_001"
GUARDIAN_ACTOR_ID: Final[str] = "actr_guardian_001"
COUNSELOR_ACTOR_ID: Final[str] = "actr_counselor_001"
GUARDIAN_CONTACT_POINT_ID: Final[str] = "acp_guardian_email_001"
PRIMARY_EVENT_ID: Final[str] = "evt_issue53_primary"
PRIMARY_EVENT_PARTICIPANT_ID: Final[str] = "ep_issue53_primary"
CROSS_EVENT_PARTICIPANT_ID: Final[str] = "ep_issue53_cross"
EVENT_ACCOUNT_ID: Final[str] = "acct_issue53_cross_report"
EVENT_OBSERVATION_ID: Final[str] = "obs_issue53_cross_observed"

_AUTHORITY_ENVIRONMENT_KEYS: Final[frozenset[str]] = frozenset(
    {"PYTHONPATH", "PDS_WORKSPACE_ROOT"}
)
_PDS_RUNTIME_DISTRIBUTIONS: Final[frozenset[str]] = frozenset(
    {
        "pds-core",
        "pds-portia",
        "pds-scoreform",
        "pds-quillan",
        "pds-concord",
        "pds-meridian",
        "pds-vitrine",
        "pds-paper-data-suite",
    }
)

_FOUNDATION_PROBE = r"""
import importlib
import json
import os
import sys
from importlib import metadata
from pathlib import Path

from pds_core.workspace import ensure_workspace_root


def _inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


workspace = Path(sys.argv[1]).resolve()
environment = Path(sys.argv[2]).resolve()
repository = Path(sys.argv[3]).resolve()

if "PYTHONPATH" in {key.upper() for key in os.environ}:
    raise RuntimeError("PYTHONPATH leaked into Issue #53 installed acceptance")
if "PDS_WORKSPACE_ROOT" in {key.upper() for key in os.environ}:
    raise RuntimeError(
        "PDS_WORKSPACE_ROOT leaked into Issue #53 installed acceptance"
    )
if os.environ.get("PYTHONNOUSERSITE") != "1":
    raise RuntimeError("Issue #53 installed acceptance requires PYTHONNOUSERSITE=1")
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise RuntimeError(
        "Issue #53 installed acceptance requires PYTHONDONTWRITEBYTECODE=1"
    )

versions = {
    "pds-core": metadata.version("pds-core"),
    "pds-portia": metadata.version("pds-portia"),
}
if versions["pds-core"] != "0.6.4":
    raise RuntimeError("installed Core version does not match Issue #53 authority")
if versions["pds-portia"] != "0.2.0":
    raise RuntimeError("installed Portia version does not match Issue #53 candidate")

for import_name in ("pds_core", "portia"):
    module = importlib.import_module(import_name)
    module_file = getattr(module, "__file__", None)
    if not isinstance(module_file, str):
        raise RuntimeError(f"{import_name} has no installed module file")
    resolved = Path(module_file).resolve()
    if not _inside(resolved, environment):
        raise RuntimeError(f"{import_name} import resolved outside the temporary venv")
    if _inside(resolved, repository):
        raise RuntimeError(f"{import_name} import resolved into the source checkout")

installed_pds = {
    (distribution.metadata.get("Name") or "").strip().lower()
    for distribution in metadata.distributions()
    if (distribution.metadata.get("Name") or "").strip().lower().startswith("pds-")
}
expected_pds = {"pds-core", "pds-portia"}
if installed_pds != expected_pds:
    raise RuntimeError(
        "Issue #53 isolated runtime contains unexpected PDS distributions"
    )

created = ensure_workspace_root(workspace, create=True).resolve()
if created != workspace:
    raise RuntimeError("Core normalized the Issue #53 workspace unexpectedly")
if len(str(created)) < 119:
    raise RuntimeError("Issue #53 workspace did not meet deep-path geometry")
if not (created / ".pds" / "workspace.json").is_file():
    raise RuntimeError("Core workspace marker was not created")

print(
    json.dumps(
        {
            "core_version": versions["pds-core"],
            "portia_version": versions["pds-portia"],
            "workspace_length": len(str(created)),
            "workspace_marker": True,
            "pds_runtime_distributions": sorted(installed_pds),
        },
        sort_keys=True,
    )
)
"""


_CORE_SETUP_PROBE = r"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pds_core.class_metadata import (
    create_class_metadata,
    load_class_metadata_for_class,
    write_class_metadata_for_class,
)
from pds_core.classes import load_class_roster, write_class_roster
from pds_core.rosters import create_roster, student_display_name
from pds_core.school_years import get_active_school_year, open_school_year

from portia.identity.roster import CoreRosterResolver
from portia.models.references import RosterStudentRef


SCHOOL_YEAR = "2026-2027"
PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
CREATED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

workspace = Path(sys.argv[1]).resolve()

opened = open_school_year(
    workspace,
    SCHOOL_YEAR,
    opened_at=CREATED_AT,
)
if opened.active_school_year != SCHOOL_YEAR or opened.closed_at is not None:
    raise RuntimeError("Core active school-year state did not open as expected")
if get_active_school_year(workspace) != SCHOOL_YEAR:
    raise RuntimeError("Core active school-year lookup disagrees with written state")

for class_id in (PRIMARY_CLASS_ID, SECONDARY_CLASS_ID):
    metadata_record = create_class_metadata(
        class_id,
        SCHOOL_YEAR,
        created_at=CREATED_AT,
    )
    write_class_metadata_for_class(workspace, metadata_record)

primary_roster = create_roster(
    PRIMARY_CLASS_ID,
    (
        {
            "student_id": COLLISION_STUDENT_ID,
            "last_name": "Synthetic",
            "first_name": "Shared",
            "period": "2",
        },
        {
            "student_id": "student_primary_002",
            "last_name": "Synthetic",
            "first_name": "Primary",
            "period": "2",
        },
    ),
)
secondary_roster = create_roster(
    SECONDARY_CLASS_ID,
    (
        {
            "student_id": COLLISION_STUDENT_ID,
            "last_name": "Synthetic",
            "first_name": "Shared",
            "period": "6",
        },
        {
            "student_id": "student_secondary_002",
            "last_name": "Synthetic",
            "first_name": "Secondary",
            "period": "6",
        },
    ),
)

write_class_roster(workspace, primary_roster)
write_class_roster(workspace, secondary_roster)

primary_metadata = load_class_metadata_for_class(workspace, PRIMARY_CLASS_ID)
secondary_metadata = load_class_metadata_for_class(workspace, SECONDARY_CLASS_ID)
if primary_metadata.school_year != SCHOOL_YEAR:
    raise RuntimeError("primary class metadata lost the active school year")
if secondary_metadata.school_year != SCHOOL_YEAR:
    raise RuntimeError("secondary class metadata lost the active school year")

loaded_primary = load_class_roster(workspace, PRIMARY_CLASS_ID)
loaded_secondary = load_class_roster(workspace, SECONDARY_CLASS_ID)
if loaded_primary.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("primary Core roster reloaded under the wrong class")
if loaded_secondary.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("secondary Core roster reloaded under the wrong class")

primary_ref = RosterStudentRef(
    class_id=PRIMARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)
secondary_ref = RosterStudentRef(
    class_id=SECONDARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)
if primary_ref == secondary_ref:
    raise RuntimeError("Portia collapsed distinct class-qualified roster references")

resolver = CoreRosterResolver(workspace)
primary_resolution = resolver.resolve_reference(primary_ref)
secondary_resolution = resolver.resolve_reference(secondary_ref)

if primary_resolution.reference != primary_ref:
    raise RuntimeError("primary Portia roster resolution changed exact identity")
if secondary_resolution.reference != secondary_ref:
    raise RuntimeError("secondary Portia roster resolution changed exact identity")
if primary_resolution.reference == secondary_resolution.reference:
    raise RuntimeError("Portia resolver merged cross-class roster identities")

primary_student = primary_resolution.student
secondary_student = secondary_resolution.student
if primary_student.student_id != secondary_student.student_id:
    raise RuntimeError("synthetic collision no longer shares the local student_id")
if primary_student.class_id == secondary_student.class_id:
    raise RuntimeError("synthetic collision no longer spans distinct Core classes")
if student_display_name(primary_student) != student_display_name(secondary_student):
    raise RuntimeError("synthetic collision no longer shares the display name")
if primary_student == secondary_student:
    raise RuntimeError("class-qualified Core student records were merged")

print(
    json.dumps(
        {
            "active_school_year": get_active_school_year(workspace),
            "class_count": 2,
            "roster_count": 2,
            "primary_roster_count": len(loaded_primary.students),
            "secondary_roster_count": len(loaded_secondary.students),
            "collision_local_student_id_equal": (
                primary_student.student_id == secondary_student.student_id
            ),
            "collision_display_name_equal": (
                student_display_name(primary_student)
                == student_display_name(secondary_student)
            ),
            "collision_reference_distinct": primary_ref != secondary_ref,
            "resolver_reference_distinct": (
                primary_resolution.reference != secondary_resolution.reference
            ),
        },
        sort_keys=True,
    )
)
"""

_ACTOR_SETUP_PROBE = r"""
import json
import sys
from collections.abc import Mapping
from datetime import date
from pathlib import Path

from pds_core.rosters import student_display_name

from portia.identity import (
    ActorDirectoryService,
    CoreRosterResolver,
    RosterStudentNotFoundError,
)
from portia.models import parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorStudentRelationshipRef,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
GUARDIAN_ACTOR_ID = "actr_guardian_001"
COUNSELOR_ACTOR_ID = "actr_counselor_001"
CONTACT_POINT_ID = "acp_guardian_email_001"
AS_OF = date(2026, 10, 4)
STAMP = "2026-10-04T12:00:00-04:00"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
service = ActorDirectoryService(workspace)


def actor_wire(actor_id, display_name, category, title=None):
    display = {"display_name": display_name}
    if title is not None:
        display["title"] = title
    return {
        "schema_version": "1",
        "record_type": "actor",
        "module_id": "portia",
        "actor_id": actor_id,
        "status": "active",
        "display": display,
        "actor_category": {"kind": category},
        "creation_source": {"type": "digital_entry"},
        "created_at": STAMP,
        "created_by": AGENT,
        "updated_at": STAMP,
        "updated_by": AGENT,
    }


def relationship_wire(
    actor_id,
    relationship_id,
    class_id,
    student_id,
    relationship_type,
):
    return {
        "schema_version": "1",
        "record_type": "actor_student_relationship",
        "module_id": "portia",
        "actor_id": actor_id,
        "relationship_id": relationship_id,
        "status": "active",
        "student_ref": {"class_id": class_id, "student_id": student_id},
        "relationship": {"type": relationship_type},
        "basis": {"kind": "local_operator_knowledge"},
        "review": {
            "kind": "locally_reviewed",
            "reviewed_at": STAMP,
            "reviewed_by": AGENT,
        },
        "effective_period": {"starts_on": "2026-09-01"},
        "creation_source": {"type": "digital_entry"},
        "created_at": STAMP,
        "created_by": AGENT,
        "updated_at": STAMP,
        "updated_by": AGENT,
    }


guardian = parse_portia_record(
    "actor",
    "1",
    actor_wire(
        GUARDIAN_ACTOR_ID,
        "Shared Synthetic",
        "family_or_caregiver",
    ),
)
counselor = parse_portia_record(
    "actor",
    "1",
    actor_wire(
        COUNSELOR_ACTOR_ID,
        "Synthetic Counselor",
        "school_staff",
        title="Counselor",
    ),
)
guardian_created = service.create_actor(guardian)
counselor_created = service.create_actor(counselor)

for stored in (guardian_created, counselor_created):
    relative_parts = stored.path.resolve().relative_to(workspace).parts
    if relative_parts[:2] != ("portia", "actors"):
        raise RuntimeError("Actor was not persisted in workspace-scoped Actor Directory")
    if PRIMARY_CLASS_ID in relative_parts or SECONDARY_CLASS_ID in relative_parts:
        raise RuntimeError("Actor identity was incorrectly persisted under a Core class")

contact = parse_portia_record(
    "actor_contact_point",
    "1",
    {
        "schema_version": "1",
        "record_type": "actor_contact_point",
        "module_id": "portia",
        "actor_id": GUARDIAN_ACTOR_ID,
        "contact_point_id": CONTACT_POINT_ID,
        "status": "active",
        "contact": {
            "kind": "email",
            "address": "guardian.issue53@example.invalid",
            "label": "personal",
        },
        "use_preference": "preferred",
        "source": {"kind": "local_operator_knowledge"},
        "verification": {
            "kind": "locally_confirmed",
            "verified_at": STAMP,
            "verified_by": AGENT,
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": STAMP,
        "created_by": AGENT,
        "updated_at": STAMP,
        "updated_by": AGENT,
    },
)
service.create_actor_child(GUARDIAN_ACTOR_ID, contact)

relationships = (
    (
        GUARDIAN_ACTOR_ID,
        "asrel_guardian_primary",
        PRIMARY_CLASS_ID,
        COLLISION_STUDENT_ID,
        "caregiver",
    ),
    (
        GUARDIAN_ACTOR_ID,
        "asrel_guardian_secondary",
        SECONDARY_CLASS_ID,
        COLLISION_STUDENT_ID,
        "caregiver",
    ),
    (
        COUNSELOR_ACTOR_ID,
        "asrel_counselor_primary",
        PRIMARY_CLASS_ID,
        "student_primary_002",
        "counselor",
    ),
)
for (
    actor_id,
    relationship_id,
    class_id,
    student_id,
    relationship_type,
) in relationships:
    service.create_actor_child(
        actor_id,
        parse_portia_record(
            "actor_student_relationship",
            "1",
            relationship_wire(
                actor_id,
                relationship_id,
                class_id,
                student_id,
                relationship_type,
            ),
        ),
    )

guardian_ref = ExactActorRef(
    actor_id=GUARDIAN_ACTOR_ID,
    contract_version="1",
)
counselor_ref = ExactActorRef(
    actor_id=COUNSELOR_ACTOR_ID,
    contract_version="1",
)
service.load_actor(guardian_ref, require_current_use=True)
service.load_actor(counselor_ref, require_current_use=True)

contact_ref = ExactActorContactPointRef(
    actor_id=GUARDIAN_ACTOR_ID,
    contact_point_id=CONTACT_POINT_ID,
    contract_version="1",
)
current_contact = service.load_contact_point(
    contact_ref,
    require_current_use=True,
)
if current_contact.record.logical_id != CONTACT_POINT_ID:
    raise RuntimeError("current Actor Contact Point did not reload exactly")

guardian_primary_ref = ExactActorStudentRelationshipRef(
    actor_id=GUARDIAN_ACTOR_ID,
    relationship_id="asrel_guardian_primary",
    contract_version="1",
)
guardian_secondary_ref = ExactActorStudentRelationshipRef(
    actor_id=GUARDIAN_ACTOR_ID,
    relationship_id="asrel_guardian_secondary",
    contract_version="1",
)
counselor_primary_ref = ExactActorStudentRelationshipRef(
    actor_id=COUNSELOR_ACTOR_ID,
    relationship_id="asrel_counselor_primary",
    contract_version="1",
)

guardian_primary = service.resolve_student_relationship(
    guardian_primary_ref,
    require_current_use=True,
    on_date=AS_OF,
)
guardian_secondary = service.resolve_student_relationship(
    guardian_secondary_ref,
    require_current_use=True,
    on_date=AS_OF,
)
counselor_primary = service.resolve_student_relationship(
    counselor_primary_ref,
    require_current_use=True,
    on_date=AS_OF,
)

if guardian_primary.roster_student.reference.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("guardian primary relationship lost exact Core class identity")
if guardian_secondary.roster_student.reference.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("guardian secondary relationship lost exact Core class identity")
if (
    guardian_primary.roster_student.reference.student_id
    != guardian_secondary.roster_student.reference.student_id
):
    raise RuntimeError("cross-class relationship case no longer shares local student_id")
if guardian_primary.roster_student.reference == guardian_secondary.roster_student.reference:
    raise RuntimeError("Actor relationships collapsed distinct class-qualified students")
if counselor_primary.roster_student.reference.student_id != "student_primary_002":
    raise RuntimeError("counselor relationship resolved the wrong exact student")

guardian_relationships = service.list_relationships(GUARDIAN_ACTOR_ID)
if {item.record.logical_id for item in guardian_relationships} != {
    "asrel_guardian_primary",
    "asrel_guardian_secondary",
}:
    raise RuntimeError("workspace Actor did not retain two separate class relationships")

roster_resolver = CoreRosterResolver(workspace)
try:
    roster_resolver.resolve(PRIMARY_CLASS_ID, GUARDIAN_ACTOR_ID)
except RosterStudentNotFoundError:
    pass
else:
    raise RuntimeError("Actor identity was substituted for Core roster identity")

guardian_display = guardian_created.record.field("display")
if not isinstance(guardian_display, Mapping):
    raise RuntimeError("guardian Actor display is malformed")
if guardian_display.get("display_name") != student_display_name(
    guardian_primary.roster_student.student
):
    raise RuntimeError("synthetic Actor/student display-name collision was not exercised")

for resolved_relationship in (
    guardian_primary,
    guardian_secondary,
    counselor_primary,
):
    wire = resolved_relationship.relationship.record.to_dict()
    prohibited_authority_fields = {
        "authority",
        "legal_authority",
        "disclosure_authority",
        "consent",
        "custody",
        "decision_authority",
    }
    if prohibited_authority_fields.intersection(wire):
        raise RuntimeError("Actor relationship improperly encoded authority semantics")

print(
    json.dumps(
        {
            "actor_count": 2,
            "guardian_relationship_count": len(guardian_relationships),
            "cross_class_actor_reuse": True,
            "cross_class_relationships_distinct": (
                guardian_primary.roster_student.reference
                != guardian_secondary.roster_student.reference
            ),
            "actor_roster_identity_separate": True,
            "display_name_not_identity": True,
            "reviewed_relationships_current": True,
            "contact_point_current": True,
            "relationship_authority_not_encoded": True,
        },
        sort_keys=True,
    )
)
"""

_EVENT_EVIDENCE_PROBE = r"""
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    EventWorkflowService,
    HypothesisWorkflowService,
    ObservationWorkflowService,
    ParticipantWorkflowService,
    ReviewWorkflowService,
    RoleWorkflowService,
    account_reference,
    observation_reference,
    participant_reference,
    role_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
GUARDIAN_ACTOR_ID = "actr_guardian_001"
EVENT_ID = "evt_issue53_primary"
PRIMARY_PARTICIPANT_ID = "ep_issue53_primary"
CROSS_PARTICIPANT_ID = "ep_issue53_cross"
ACTOR_PARTICIPANT_ID = "ep_issue53_guardian"
PRIMARY_ROLE_ID = "epr_issue53_primary"
CROSS_ROLE_ID = "epr_issue53_cross"
ACTOR_ROLE_ID = "epr_issue53_guardian"
ACCOUNT_ID = "acct_issue53_cross_report"
OBSERVATION_ID = "obs_issue53_cross_observed"
CREATED_AT = "2026-10-04T12:10:00-04:00"
ACTIVATED_AT = "2026-10-04T12:20:00-04:00"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)


def event_wire(status, updated_at):
    return {
        "schema_version": "2",
        "record_type": "portia_work",
        "work_kind": "event",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "school_year": "2026-2027",
        "status": status,
        "creation_source": {"type": "digital_entry"},
        "created_at": CREATED_AT,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
        "occurrence": {
            "precision": "exact",
            "started_at": "2026-10-04T11:55:00-04:00",
        },
        "summary": "Synthetic classroom material-location discrepancy.",
        "location": {"type": "classroom"},
        "instructional_context": {"type": "group_work"},
    }


def participant_wire(participant_id, subject):
    return {
        "schema_version": "3",
        "record_type": "event_participant",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "participant_id": participant_id,
        "status": "active",
        "subject": subject,
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-10-04T12:12:00-04:00",
        "created_by": AGENT,
        "updated_at": "2026-10-04T12:12:00-04:00",
        "updated_by": AGENT,
    }


def role_wire(role_id, participant_id):
    return {
        "schema_version": "3",
        "record_type": "event_participant_role",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "role_id": role_id,
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": participant_id,
                "contract_version": "3",
            },
        },
        "status": "active",
        "role_type": "present",
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-10-04T12:14:00-04:00",
        "created_by": AGENT,
        "updated_at": "2026-10-04T12:14:00-04:00",
        "updated_by": AGENT,
    }


events = EventWorkflowService(workspace)
participants = ParticipantWorkflowService(workspace)
roles = RoleWorkflowService(workspace)
accounts = AccountWorkflowService(workspace)
observations = ObservationWorkflowService(workspace)

draft = events.create(
    parse_portia_record("event", "2", event_wire("draft", CREATED_AT))
)

primary_participant = parse_portia_record(
    "event_participant",
    "3",
    participant_wire(
        PRIMARY_PARTICIPANT_ID,
        {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": PRIMARY_CLASS_ID,
                "student_id": COLLISION_STUDENT_ID,
            },
            "display_snapshot": {"display_name": "Shared Synthetic"},
        },
    ),
)
cross_participant = parse_portia_record(
    "event_participant",
    "3",
    participant_wire(
        CROSS_PARTICIPANT_ID,
        {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": SECONDARY_CLASS_ID,
                "student_id": COLLISION_STUDENT_ID,
            },
            "display_snapshot": {"display_name": "Shared Synthetic"},
        },
    ),
)
actor_participant = parse_portia_record(
    "event_participant",
    "3",
    participant_wire(
        ACTOR_PARTICIPANT_ID,
        {
            "kind": "actor",
            "actor_ref": {"actor_id": GUARDIAN_ACTOR_ID},
            "display_snapshot": {"display_name": "Shared Synthetic"},
        },
    ),
)
for record in (primary_participant, cross_participant, actor_participant):
    participants.create(work, record)

for role_id, participant_id in (
    (PRIMARY_ROLE_ID, PRIMARY_PARTICIPANT_ID),
    (CROSS_ROLE_ID, CROSS_PARTICIPANT_ID),
    (ACTOR_ROLE_ID, ACTOR_PARTICIPANT_ID),
):
    roles.create(
        work,
        parse_portia_record(
            "event_participant_role",
            "3",
            role_wire(role_id, participant_id),
        ),
    )

active = events.replace(
    parse_portia_record("event", "2", event_wire("active", ACTIVATED_AT)),
    expected=draft.fingerprint,
)
current_event = events.require_current_use(work)
if active.record.status != "active" or current_event.record.status != "active":
    raise RuntimeError("primary Event did not become current through Event workflow")
if current_event.record.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("primary Event lost its single owning Core class")

primary_resolution = participants.require_current_use(
    participant_reference(work, PRIMARY_PARTICIPANT_ID)
)
cross_resolution = participants.require_current_use(
    participant_reference(work, CROSS_PARTICIPANT_ID)
)
actor_resolution = participants.require_current_use(
    participant_reference(work, ACTOR_PARTICIPANT_ID)
)

if primary_resolution.kind != "roster_student":
    raise RuntimeError("primary Participant lost roster-student subject identity")
if cross_resolution.kind != "roster_student":
    raise RuntimeError("cross-class Participant lost roster-student subject identity")
if actor_resolution.kind != "actor":
    raise RuntimeError("Actor Participant lost explicit Actor identity")
if primary_resolution.authority.reference.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("primary Participant resolved outside its exact roster class")
if cross_resolution.authority.reference.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("foreign Participant was localized into Event owning class")
if (
    primary_resolution.authority.reference.student_id
    != cross_resolution.authority.reference.student_id
):
    raise RuntimeError("cross-class collision no longer shares the synthetic local ID")
if primary_resolution.authority.reference == cross_resolution.authority.reference:
    raise RuntimeError("Event participation collapsed cross-class roster identity")

for role_id in (PRIMARY_ROLE_ID, CROSS_ROLE_ID, ACTOR_ROLE_ID):
    current_role = roles.require_current_use(role_reference(work, role_id))
    if current_role.record.field("role_type") != "present":
        raise RuntimeError("neutral Participant Role was replaced by an involvement claim")

account = parse_portia_record(
    "account",
    "2",
    {
        "schema_version": "2",
        "record_type": "account",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_kind": "event",
        "work_id": EVENT_ID,
        "account_id": ACCOUNT_ID,
        "status": "active",
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": CROSS_PARTICIPANT_ID,
                "contract_version": "3",
            },
        },
        "source": {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": PRIMARY_CLASS_ID,
                "student_id": "student_primary_002",
            },
            "display_snapshot": {"display_name": "Primary Synthetic"},
        },
        "information_origin": "firsthand",
        "source_certainty": "stated_certain",
        "content": [
            {
                "representation": "recorded_summary",
                "text": (
                    "Synthetic source stated that the blue marker remained "
                    "on the table after the timer sounded."
                ),
            }
        ],
        "provided_time": {
            "precision": "exact",
            "at": "2026-10-04T12:15:00-04:00",
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-10-04T12:25:00-04:00",
        "created_by": AGENT,
        "updated_at": "2026-10-04T12:25:00-04:00",
        "updated_by": AGENT,
    },
)
accounts.create(work, account)
current_account = accounts.require_current_use(account_reference(work, ACCOUNT_ID))

observation = parse_portia_record(
    "observation",
    "2",
    {
        "schema_version": "2",
        "record_type": "observation",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_kind": "event",
        "work_id": EVENT_ID,
        "observation_id": OBSERVATION_ID,
        "status": "active",
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": CROSS_PARTICIPANT_ID,
                "contract_version": "3",
            },
        },
        "observer": {
            "kind": "human",
            "human_attribution": {
                "kind": "local_operator",
                "display_label": "Synthetic Acceptance Operator",
            },
        },
        "method": "live_direct",
        "content": {
            "narrative": (
                "Synthetic operator observed the blue marker on the floor "
                "after the timer sounded."
            )
        },
        "observation_time": {
            "precision": "exact",
            "at": "2026-10-04T12:16:00-04:00",
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-10-04T12:26:00-04:00",
        "created_by": AGENT,
        "updated_at": "2026-10-04T12:26:00-04:00",
        "updated_by": AGENT,
    },
)
observations.create(work, observation)
current_observation = observations.require_current_use(
    observation_reference(work, OBSERVATION_ID)
)

if current_account.record.contract != "account":
    raise RuntimeError("Account evidence changed contract identity")
if current_observation.record.contract != "observation":
    raise RuntimeError("Observation evidence changed contract identity")

automatic_judgments = {
    "review": len(ReviewWorkflowService(workspace).list(work)),
    "classification": len(ClassificationWorkflowService(workspace).list(work)),
    "hypothesis": len(HypothesisWorkflowService(workspace).list(work)),
    "determination": len(DeterminationWorkflowService(workspace).list(work)),
}
if any(automatic_judgments.values()):
    raise RuntimeError("conflicting evidence manufactured judgment records")

def contains_key(value, key):
    if isinstance(value, Mapping):
        return key in value or any(contains_key(item, key) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(contains_key(item, key) for item in value)
    return False

neutrality_keys = (
    "responsibility",
    "misconduct",
    "diagnosis",
    "risk",
    "causation",
    "effectiveness",
)
neutral_records = (
    primary_resolution.participant.record.to_dict(),
    cross_resolution.participant.record.to_dict(),
    current_account.record.to_dict(),
    current_observation.record.to_dict(),
)
if any(
    contains_key(record, key)
    for record in neutral_records
    for key in neutrality_keys
):
    raise RuntimeError("Event evidence introduced prohibited automatic semantics")

print(
    json.dumps(
        {
            "event_current": True,
            "event_owner_class": current_event.record.class_id,
            "participant_count": len(participants.list(work)),
            "role_count": len(roles.list(work)),
            "foreign_participant_class": cross_resolution.authority.reference.class_id,
            "foreign_participant_exact": True,
            "actor_participant_exact": actor_resolution.kind == "actor",
            "account_current": current_account.record.status == "active",
            "observation_current": current_observation.record.status == "active",
            "conflicting_evidence_retained": True,
            "automatic_judgment_count": sum(automatic_judgments.values()),
            "neutrality_preserved": True,
        },
        sort_keys=True,
    )
)
"""

class Issue53AcceptanceError(RuntimeError):
    """Raised when the representative installed acceptance boundary fails."""


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=dict(env),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise Issue53AcceptanceError(
            f"installed acceptance command failed with exit code {result.returncode}"
        )
    return result


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _require_wheel(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise Issue53AcceptanceError(f"{label} wheel is unavailable")
    if resolved.suffix.lower() != ".whl":
        raise Issue53AcceptanceError(f"{label} artifact must be a wheel")
    return resolved


def _authenticate_core(repository: Path, core_wheel: Path) -> str:
    if core_wheel.name != CORE_064_FILENAME:
        raise Issue53AcceptanceError(
            "Issue #53 requires the exact released Core 0.6.4 wheel filename"
        )
    digest = _sha256(core_wheel)
    if digest != CORE_064_SHA256:
        raise Issue53AcceptanceError(
            "Issue #53 Core 0.6.4 wheel SHA-256 does not match release authority"
        )
    _run(
        [
            sys.executable,
            str(repository / "scripts" / "verify_core_wheel.py"),
            str(core_wheel),
        ],
        cwd=repository,
        env=os.environ.copy(),
    )
    return digest


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _console_path(python: Path) -> Path:
    return python.parent / ("portia.exe" if os.name == "nt" else "portia")


def _isolated_environment(
    *,
    user_home: Path,
    scripts_directory: Path,
) -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        if key.upper() in _AUTHORITY_ENVIRONMENT_KEYS:
            env.pop(key, None)

    user_home.mkdir(parents=True, exist_ok=True)
    local_app_data = user_home / "AppData" / "Local"
    roaming_app_data = user_home / "AppData" / "Roaming"
    xdg_config = user_home / ".config"
    for directory in (local_app_data, roaming_app_data, xdg_config):
        directory.mkdir(parents=True, exist_ok=True)

    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["HOME"] = str(user_home)
    env["USERPROFILE"] = str(user_home)
    env["LOCALAPPDATA"] = str(local_app_data)
    env["APPDATA"] = str(roaming_app_data)
    env["XDG_CONFIG_HOME"] = str(xdg_config)

    existing_path = env.get("PATH", "")
    env["PATH"] = (
        f"{scripts_directory}{os.pathsep}{existing_path}"
        if existing_path
        else str(scripts_directory)
    )
    return env


def _deep_workspace_path(parent: Path) -> Path:
    resolved_parent = parent.resolve()
    prefix = "pds-portia-i53-"
    desired_leaf_length = max(
        len(prefix),
        TARGET_DEEP_WORKSPACE_LENGTH - len(str(resolved_parent)) - 1,
    )
    leaf = prefix + ("d" * (desired_leaf_length - len(prefix)))
    workspace = resolved_parent / leaf
    if len(str(workspace)) < TARGET_DEEP_WORKSPACE_LENGTH:
        raise Issue53AcceptanceError(
            "could not construct the Issue #53 deep workspace geometry"
        )
    return workspace


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _assert_isolated_working_directory(
    work: Path,
    *,
    repository: Path,
    workspace: Path,
    artifact_directories: Sequence[Path],
) -> None:
    if tuple(work.iterdir()):
        raise Issue53AcceptanceError(
            "Issue #53 acceptance working directory must start empty"
        )
    forbidden = (repository, workspace, *artifact_directories)
    if any(_is_within(work, root) for root in forbidden):
        raise Issue53AcceptanceError(
            "Issue #53 acceptance working directory is not isolated"
        )


def _assert_launcher_reachable(
    python: Path,
    *,
    env: Mapping[str, str],
) -> None:
    launcher = _console_path(python)
    if not launcher.is_file():
        raise Issue53AcceptanceError(
            "installed Portia console launcher is missing from the temporary venv"
        )
    found = shutil.which("portia", path=env.get("PATH"))
    if found is None:
        raise Issue53AcceptanceError(
            "installed Portia console launcher is not reachable on isolated PATH"
        )
    if Path(found).resolve() != launcher.resolve():
        raise Issue53AcceptanceError(
            "isolated PATH resolved a different Portia console launcher"
        )


def _foundation_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
    environment: Path,
    repository: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _FOUNDATION_PROBE,
            str(workspace),
            str(environment),
            str(repository),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed foundation probe result was not an object"
        )
    payload = cast(dict[str, object], payload_raw)
    expected = {
        "core_version": EXPECTED_CORE_VERSION,
        "portia_version": EXPECTED_PORTIA_VERSION,
        "workspace_marker": True,
        "pds_runtime_distributions": ["pds-core", "pds-portia"],
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed foundation mismatch for {key}"
            )
    workspace_length = payload.get("workspace_length")
    if (
        not isinstance(workspace_length, int)
        or workspace_length < TARGET_DEEP_WORKSPACE_LENGTH
    ):
        raise Issue53AcceptanceError(
            "Issue #53 installed workspace did not meet deep-path geometry"
        )
    return payload


def _core_setup_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _CORE_SETUP_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Core setup probe result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "active_school_year": SYNTHETIC_SCHOOL_YEAR,
        "class_count": 2,
        "roster_count": 2,
        "primary_roster_count": 2,
        "secondary_roster_count": 2,
        "collision_local_student_id_equal": True,
        "collision_display_name_equal": True,
        "collision_reference_distinct": True,
        "resolver_reference_distinct": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Core setup mismatch for {key}"
            )
    return payload

def _actor_setup_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _ACTOR_SETUP_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Actor setup probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Actor setup probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Actor setup probe result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "actor_count": 2,
        "guardian_relationship_count": 2,
        "cross_class_actor_reuse": True,
        "cross_class_relationships_distinct": True,
        "actor_roster_identity_separate": True,
        "display_name_not_identity": True,
        "reviewed_relationships_current": True,
        "contact_point_current": True,
        "relationship_authority_not_encoded": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Actor setup mismatch for {key}"
            )
    return payload

def _event_evidence_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [
            str(python),
            "-c",
            _EVENT_EVIDENCE_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Event evidence probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Event evidence probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Event evidence probe result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "event_current": True,
        "event_owner_class": PRIMARY_CLASS_ID,
        "participant_count": 3,
        "role_count": 3,
        "foreign_participant_class": SECONDARY_CLASS_ID,
        "foreign_participant_exact": True,
        "actor_participant_exact": True,
        "account_current": True,
        "observation_current": True,
        "conflicting_evidence_retained": True,
        "automatic_judgment_count": 0,
        "neutrality_preserved": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Event evidence mismatch for {key}"
            )
    return payload

def smoke(portia_wheel: Path, core_wheel: Path) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    candidate = _require_wheel(portia_wheel, label="Portia candidate")
    core = _require_wheel(core_wheel, label="Core")
    core_digest = _authenticate_core(repository, core)
    portia_digest = _sha256(candidate)

    with tempfile.TemporaryDirectory(prefix="pds-portia-issue53-") as temp:
        root = Path(temp).resolve()
        environment = root / "venv"
        work = root / "run"
        user_home = root / "profile"
        workspace_parent = root / "workspace-parent"
        work.mkdir()
        workspace_parent.mkdir()
        workspace = _deep_workspace_path(workspace_parent)

        _assert_isolated_working_directory(
            work,
            repository=repository,
            workspace=workspace,
            artifact_directories=(candidate.parent, core.parent),
        )

        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        python = _venv_python(environment)
        env = _isolated_environment(
            user_home=user_home,
            scripts_directory=python.parent,
        )

        _run(
            [str(python), "-m", "pip", "install", str(core)],
            cwd=work,
            env=env,
        )
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--no-deps",
                str(candidate),
            ],
            cwd=work,
            env=env,
        )
        _run([str(python), "-m", "pip", "check"], cwd=work, env=env)
        _assert_launcher_reachable(python, env=env)

        foundation = _foundation_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
            environment=environment,
            repository=repository,
        )
        core_setup = _core_setup_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        actor_setup = _actor_setup_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        event_evidence = _event_evidence_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        if tuple(work.iterdir()):
            raise Issue53AcceptanceError(
                "Issue #53 acceptance polluted its empty working directory"
            )

        print("PASS install")
        print("PASS deep workspace")
        print("PASS Core setup")
        print("PASS Actor setup")
        print("PASS Event evidence")

        return {
            "candidate_portia_wheel": candidate.name,
            "candidate_portia_sha256": portia_digest,
            "core_wheel": core.name,
            "core_sha256": core_digest,
            "core_version": foundation["core_version"],
            "portia_version": foundation["portia_version"],
            "workspace_length": foundation["workspace_length"],
            "active_school_year": core_setup["active_school_year"],
            "class_count": core_setup["class_count"],
            "roster_count": core_setup["roster_count"],
            "collision_reference_distinct": core_setup[
                "collision_reference_distinct"
            ],
            "resolver_reference_distinct": core_setup[
                "resolver_reference_distinct"
            ],
            "actor_count": actor_setup["actor_count"],
            "cross_class_actor_reuse": actor_setup["cross_class_actor_reuse"],
            "cross_class_relationships_distinct": actor_setup[
                "cross_class_relationships_distinct"
            ],
            "actor_roster_identity_separate": actor_setup[
                "actor_roster_identity_separate"
            ],
            "contact_point_current": actor_setup["contact_point_current"],
            "relationship_authority_not_encoded": actor_setup[
                "relationship_authority_not_encoded"
            ],
            "event_current": event_evidence["event_current"],
            "event_owner_class": event_evidence["event_owner_class"],
            "participant_count": event_evidence["participant_count"],
            "role_count": event_evidence["role_count"],
            "foreign_participant_exact": event_evidence[
                "foreign_participant_exact"
            ],
            "account_current": event_evidence["account_current"],
            "observation_current": event_evidence["observation_current"],
            "automatic_judgment_count": event_evidence[
                "automatic_judgment_count"
            ],
            "neutrality_preserved": event_evidence["neutrality_preserved"],
            "launcher_reachable": True,
            "pip_check": "clean",
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("portia_wheel", type=Path)
    parser.add_argument("core_wheel", type=Path)
    args = parser.parse_args()

    try:
        evidence = smoke(args.portia_wheel, args.core_wheel)
    except (
        Issue53AcceptanceError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"ERROR Issue #53 foundation: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(evidence, sort_keys=True))
    print("Portia Issue #53 installed acceptance foundation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
