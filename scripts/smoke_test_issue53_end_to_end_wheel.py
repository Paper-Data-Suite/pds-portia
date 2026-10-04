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
EVENT_REVIEW_ID: Final[str] = "rvw_issue53_evidence"
EVENT_DETERMINATION_ID: Final[str] = "det_issue53_insufficient"
CORRECTED_EVENT_ACCOUNT_ID: Final[str] = "acct_issue53_cross_corrected"
EVENT_RESPONSE_ID: Final[str] = "rsp_issue53_neutral_support"
EVENT_COMMUNICATION_ID: Final[str] = "comm_issue53_guardian"
SUPPORT_PROCESS_ID: Final[str] = "sup_issue53_support"
SUPPORTED_SUPPORT_PARTICIPANT_ID: Final[str] = "spp_issue53_student"
COUNSELOR_SUPPORT_PARTICIPANT_ID: Final[str] = "spp_issue53_counselor"
SUPPORT_NEED_ID: Final[str] = "spn_issue53_access"
SUPPORT_GOAL_ID: Final[str] = "spg_issue53_access"
SUPPORT_PLAN_ID: Final[str] = "spt_issue53_access"
IMPLEMENTATION_ONE_ID: Final[str] = "imp_issue53_access_001"
IMPLEMENTATION_TWO_ID: Final[str] = "imp_issue53_access_002"
FIDELITY_ID: Final[str] = "fid_issue53_access"
FOLLOW_UP_ID: Final[str] = "fup_issue53_review"

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

_JUDGMENT_CORRECTION_PROBE = r"""
import json
import sys
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.paths import work_storage_history_path
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ReviewWorkflowService,
    account_reference,
    determination_reference,
    observation_reference,
    review_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
EVENT_ID = "evt_issue53_primary"
ACCOUNT_ID = "acct_issue53_cross_report"
OBSERVATION_ID = "obs_issue53_cross_observed"
REVIEW_ID = "rvw_issue53_evidence"
DETERMINATION_ID = "det_issue53_insufficient"
CORRECTED_ACCOUNT_ID = "acct_issue53_cross_corrected"
CORRECTION_TRANSITION_ID = "lct_issue53_account_corrected"
CORRECTION_OPERATION_ID = "op_issue53_account_corrected"
STAMP = "2026-10-04T12:30:00-04:00"
CORRECTION_STAMP = "2026-10-04T12:35:00-04:00"
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


def evidence_ref(record_kind, record_id):
    return {
        "kind": "portia_record",
        "work_record_ref": {
            "work_ref": work.to_dict(),
            "record_ref": {
                "record_kind": record_kind,
                "record_id": record_id,
                "contract_version": "2",
            },
        },
    }


original_account_ref = account_reference(work, ACCOUNT_ID)
observation_ref = observation_reference(work, OBSERVATION_ID)

accounts = AccountWorkflowService(workspace)
reviews = ReviewWorkflowService(workspace)
determinations = DeterminationWorkflowService(workspace)

predecessor_before = accounts.require_current_use(original_account_ref)
observation = observation_ref
account_evidence = evidence_ref("account", ACCOUNT_ID)
observation_evidence = evidence_ref("observation", OBSERVATION_ID)

review_record = parse_portia_record(
    "review",
    "1",
    {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "review_id": REVIEW_ID,
        "status": "active",
        "review_state": "completed",
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "evidence_review",
            "text": (
                "What bounded information is supported by the exact Account "
                "and Observation for this synthetic Event?"
            ),
        },
        "target": {"kind": "event"},
        "reviewer": {
            "kind": "local_operator",
            "display_label": "Synthetic Acceptance Operator",
        },
        "evidence_considered": [
            account_evidence,
            observation_evidence,
        ],
        "creation_source": {"type": "digital_entry"},
        "created_at": STAMP,
        "created_by": AGENT,
        "updated_at": STAMP,
        "updated_by": AGENT,
    },
)
review_created = reviews.create(work, review_record)
review_exact_ref = review_reference(work, REVIEW_ID)
review_current_before = reviews.require_current_use(review_exact_ref)
if review_current_before.record.field("review_state") != "completed":
    raise RuntimeError("bounded Review did not remain completed/current")

determination_record = parse_portia_record(
    "determination",
    "1",
    {
        "schema_version": "1",
        "record_type": "determination",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "determination_id": DETERMINATION_ID,
        "status": "active",
        "target": {"kind": "event"},
        "question": (
            "What bounded conclusion is supported by the conflicting "
            "synthetic evidence?"
        ),
        "decision_maker": {
            "kind": "local_operator",
            "display_label": "Synthetic Acceptance Operator",
        },
        "authority_context": {
            "kind": "teacher_local",
            "scope": "teacher_review",
        },
        "process_basis": {
            "kind": "teacher_local",
            "process_label": "Synthetic local evidence review",
        },
        "outcome": {"kind": "insufficient_information"},
        "review_ref": review_exact_ref.to_dict(),
        "basis": [
            {
                "relation": "supporting",
                "evidence_ref": account_evidence,
            },
            {
                "relation": "contrary",
                "evidence_ref": observation_evidence,
            },
        ],
        "creation_source": {"type": "digital_entry"},
        "created_at": STAMP,
        "created_by": AGENT,
        "updated_at": STAMP,
        "updated_by": AGENT,
    },
)
determination_created = determinations.create(work, determination_record)
determination_exact_ref = determination_reference(work, DETERMINATION_ID)
determination_current_before = determinations.require_current_use(
    determination_exact_ref
)
if determination_current_before.record.field("outcome") != {
    "kind": "insufficient_information"
}:
    raise RuntimeError("Determination exceeded the bounded insufficient-information result")

if ClassificationWorkflowService(workspace).list(work):
    raise RuntimeError("bounded Review manufactured a Classification")
if HypothesisWorkflowService(workspace).list(work):
    raise RuntimeError("bounded Review manufactured a Hypothesis")

prior_bytes = predecessor_before.path.read_bytes()
prior_fingerprint = predecessor_before.fingerprint
review_fingerprint = review_created.fingerprint
determination_fingerprint = determination_created.fingerprint

predecessor_wire = predecessor_before.record.to_dict()
corrected_wire = dict(predecessor_wire)
corrected_wire["account_id"] = CORRECTED_ACCOUNT_ID
corrected_wire["status"] = "active"
corrected_wire["content"] = [
    {
        "representation": "recorded_summary",
        "text": (
            "Synthetic source corrected the earlier statement: "
            "the blue marker was on the side tray after the timer sounded."
        ),
    }
]
corrected_wire["supersedes"] = [
    {
        "work_record_ref": original_account_ref.to_dict(),
        "reason": "statement_corrected",
    }
]
corrected_wire["created_at"] = CORRECTION_STAMP
corrected_wire["updated_at"] = CORRECTION_STAMP
corrected_wire["created_by"] = AGENT
corrected_wire["updated_by"] = AGENT

successor = parse_portia_record("account", "2", corrected_wire)
correction = accounts.correct(
    original_account_ref,
    successor,
    expected=prior_fingerprint,
    transition_id=CORRECTION_TRANSITION_ID,
    operation_id=CORRECTION_OPERATION_ID,
)
if correction.accepted_steps != (
    "step_history",
    "step_successor",
    "step_transition",
    "step_evidence",
):
    raise RuntimeError("Account correction did not complete its accepted coordinated path")

predecessor_after = accounts.load_exact(original_account_ref)
successor_ref = account_reference(work, CORRECTED_ACCOUNT_ID)
successor_after = accounts.require_current_use(successor_ref)

if predecessor_after.record.status != "superseded":
    raise RuntimeError("corrected Account predecessor did not become superseded")
if successor_after.record.status != "active":
    raise RuntimeError("corrected Account successor did not become current")
if predecessor_after.record.logical_id == successor_after.record.logical_id:
    raise RuntimeError("Account correction reused predecessor identity")

supersedes = successor_after.record.field("supersedes")
if not isinstance(supersedes, tuple) or len(supersedes) != 1:
    raise RuntimeError("corrected Account successor lost exact supersession provenance")
supersession_ref = supersedes[0]["work_record_ref"]["record_ref"]
if (
    supersession_ref["record_kind"] != "account"
    or supersession_ref["record_id"] != ACCOUNT_ID
    or supersession_ref["contract_version"] != "2"
):
    raise RuntimeError("corrected Account successor does not exactly name predecessor")

history_path = work_storage_history_path(
    workspace,
    work,
    "account",
    ACCOUNT_ID,
    prior_fingerprint.digest,
)
if not history_path.is_file():
    raise RuntimeError("technical storage history for Account predecessor is absent")
history_bytes = history_path.read_bytes()
if history_bytes != prior_bytes:
    raise RuntimeError("technical storage history bytes differ from accepted predecessor")
if fingerprint_bytes(history_bytes) != prior_fingerprint:
    raise RuntimeError("technical storage history fingerprint disagrees with predecessor")

review_after = reviews.require_current_use(review_exact_ref)
determination_after = determinations.require_current_use(
    determination_exact_ref
)
if review_after.fingerprint != review_fingerprint:
    raise RuntimeError("Account correction rewrote historical Review")
if determination_after.fingerprint != determination_fingerprint:
    raise RuntimeError("Account correction rewrote historical Determination")

review_evidence = review_after.record.to_dict()["evidence_considered"]
review_account_ids = [
    item["work_record_ref"]["record_ref"]["record_id"]
    for item in review_evidence
    if item["kind"] == "portia_record"
    and item["work_record_ref"]["record_ref"]["record_kind"] == "account"
]
if review_account_ids != [ACCOUNT_ID]:
    raise RuntimeError("historical Review silently retargeted corrected Account")

determination_basis = determination_after.record.to_dict()["basis"]
determination_account_ids = [
    item["evidence_ref"]["work_record_ref"]["record_ref"]["record_id"]
    for item in determination_basis
    if item["evidence_ref"]["kind"] == "portia_record"
    and item["evidence_ref"]["work_record_ref"]["record_ref"]["record_kind"]
    == "account"
]
if determination_account_ids != [ACCOUNT_ID]:
    raise RuntimeError("historical Determination silently retargeted corrected Account")

if determination_after.record.field("outcome") != {
    "kind": "insufficient_information"
}:
    raise RuntimeError("Account correction changed bounded Determination outcome")

print(
    json.dumps(
        {
            "review_current": True,
            "review_completed": True,
            "determination_current": True,
            "determination_outcome": "insufficient_information",
            "classification_count": len(
                ClassificationWorkflowService(workspace).list(work)
            ),
            "hypothesis_count": len(HypothesisWorkflowService(workspace).list(work)),
            "predecessor_status": predecessor_after.record.status,
            "successor_status": successor_after.record.status,
            "successor_distinct": (
                predecessor_after.record.logical_id
                != successor_after.record.logical_id
            ),
            "exact_supersession": True,
            "technical_history_preserved": True,
            "review_history_pinned": True,
            "determination_history_pinned": True,
            "judgment_fingerprint_stable": (
                review_after.fingerprint == review_fingerprint
                and determination_after.fingerprint == determination_fingerprint
            ),
        },
        sort_keys=True,
    )
)
"""

_RESPONSE_COMMUNICATION_PROBE = r"""
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from portia.identity import ActorDirectoryService
from portia.models import parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactPortiaWorkRef,
)
from portia.workflows import (
    CommunicationWorkflowService,
    OutcomeWorkflowService,
    ResponseWorkflowService,
    communication_reference,
    determination_reference,
    response_reference,
    review_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
EVENT_ID = "evt_issue53_primary"
CROSS_PARTICIPANT_ID = "ep_issue53_cross"
REVIEW_ID = "rvw_issue53_evidence"
DETERMINATION_ID = "det_issue53_insufficient"
GUARDIAN_ACTOR_ID = "actr_guardian_001"
CONTACT_POINT_ID = "acp_guardian_email_001"
RESPONSE_ID = "rsp_issue53_neutral_support"
COMMUNICATION_ID = "comm_issue53_guardian"
RESPONSE_STAMP = "2026-10-04T12:40:00-04:00"
COMMUNICATION_STAMP = "2026-10-04T12:45:00-04:00"
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

review_ref = review_reference(work, REVIEW_ID)
determination_ref = determination_reference(work, DETERMINATION_ID)

responses = ResponseWorkflowService(workspace)
communications = CommunicationWorkflowService(workspace)
outcomes = OutcomeWorkflowService(workspace)

outcome_count_before = len(outcomes.list(work))

response = parse_portia_record(
    "response",
    "1",
    {
        "schema_version": "1",
        "record_type": "response",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": EVENT_ID,
        "response_id": RESPONSE_ID,
        "status": "active",
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": CROSS_PARTICIPANT_ID,
                "contract_version": "3",
            },
        },
        "provider": {
            "kind": "local_operator",
            "display_label": "Synthetic Acceptance Operator",
        },
        "action": {
            "family": "environmental_or_instructional",
            "description": (
                "Offered a brief neutral reset location and restated the "
                "task directions without assigning responsibility."
            ),
        },
        "execution_state": "completed",
        "started_at": "2026-10-04T12:37:00-04:00",
        "ended_at": "2026-10-04T12:38:00-04:00",
        "review_ref": review_ref.to_dict(),
        "determination_ref": determination_ref.to_dict(),
        "creation_source": {"type": "digital_entry"},
        "created_at": RESPONSE_STAMP,
        "created_by": AGENT,
        "updated_at": RESPONSE_STAMP,
        "updated_by": AGENT,
    },
)
response_created = responses.create(work, response)
response_exact_ref = response_reference(work, RESPONSE_ID)
response_current = responses.require_current_use(response_exact_ref)

if response_created.record.status != "active":
    raise RuntimeError("Response was not created as active")
if response_current.record.field("execution_state") != "completed":
    raise RuntimeError("Response execution state was not retained exactly")
if response_current.record.field("review_ref") != review_ref.to_dict():
    raise RuntimeError("Response lost exact Review context")
if response_current.record.field("determination_ref") != determination_ref.to_dict():
    raise RuntimeError("Response lost exact Determination context")

response_wire = response_current.record.to_dict()
for forbidden in ("outcome", "effectiveness", "success", "agreement"):
    if forbidden in response_wire:
        raise RuntimeError("Response improperly encoded inferred result semantics")

actor_service = ActorDirectoryService(workspace)
contact_ref = ExactActorContactPointRef(
    actor_id=GUARDIAN_ACTOR_ID,
    contact_point_id=CONTACT_POINT_ID,
    contract_version="1",
)
contact = actor_service.load_contact_point(
    contact_ref,
    require_current_use=True,
)
if contact.record.logical_id != CONTACT_POINT_ID:
    raise RuntimeError("Communication setup did not resolve exact current Contact Point")
verification = contact.record.field("verification")
if not isinstance(verification, Mapping):
    raise RuntimeError("synthetic Contact Point verification is malformed")
if verification.get("kind") != "locally_confirmed":
    raise RuntimeError("synthetic Contact Point is not locally confirmed")

communication = parse_portia_record(
    "communication",
    "1",
    {
        "schema_version": "1",
        "record_type": "communication",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_kind": "event",
        "work_id": EVENT_ID,
        "communication_id": COMMUNICATION_ID,
        "status": "active",
        "sender": {
            "kind": "local_operator",
            "display_label": "Synthetic Acceptance Operator",
        },
        "recipients": [
            {
                "person": {
                    "kind": "actor",
                    "actor_ref": {"actor_id": GUARDIAN_ACTOR_ID},
                    "display_snapshot": {"display_name": "Shared Synthetic"},
                },
                "endpoint_ref": {
                    "actor_id": GUARDIAN_ACTOR_ID,
                    "contact_point_id": CONTACT_POINT_ID,
                    "contract_version": "1",
                },
                "participation": "not_established",
            }
        ],
        "method": {"kind": "email"},
        "purpose": {"kind": "response_coordination"},
        "act_state": "completed",
        "privacy_scope": "participant_limited",
        "started_at": "2026-10-04T12:42:00-04:00",
        "ended_at": "2026-10-04T12:43:00-04:00",
        "summary": (
            "Recorded that an email communication act was completed to share "
            "that the neutral classroom response had been offered."
        ),
        "relations": [
            {
                "relation": "relates_to_response",
                "record_ref": response_exact_ref.to_dict(),
            }
        ],
        "creation_source": {"type": "digital_entry"},
        "created_at": COMMUNICATION_STAMP,
        "created_by": AGENT,
        "updated_at": COMMUNICATION_STAMP,
        "updated_by": AGENT,
    },
)
communication_created = communications.create(work, communication)
communication_exact_ref = communication_reference(work, COMMUNICATION_ID)
communication_current = communications.require_current_use(
    communication_exact_ref
)

if communication_created.record.status != "active":
    raise RuntimeError("Communication was not created as active")
if communication_current.record.field("act_state") != "completed":
    raise RuntimeError("Communication act state was not retained exactly")

recipients = communication_current.record.field("recipients")
if not isinstance(recipients, tuple) or len(recipients) != 1:
    raise RuntimeError("Communication recipient set changed unexpectedly")
recipient = recipients[0]
if not isinstance(recipient, Mapping):
    raise RuntimeError("Communication recipient representation is malformed")

person = recipient.get("person")
endpoint = recipient.get("endpoint_ref")
if not isinstance(person, Mapping) or not isinstance(endpoint, Mapping):
    raise RuntimeError("Communication lost Actor recipient or exact endpoint")
actor_ref = person.get("actor_ref")
if not isinstance(actor_ref, Mapping):
    raise RuntimeError("Communication recipient Actor reference is malformed")
if actor_ref.get("actor_id") != GUARDIAN_ACTOR_ID:
    raise RuntimeError("Communication recipient identity changed")
if endpoint.get("actor_id") != GUARDIAN_ACTOR_ID:
    raise RuntimeError("Communication endpoint Actor disagrees with recipient")
if endpoint.get("contact_point_id") != CONTACT_POINT_ID:
    raise RuntimeError("Communication did not preserve exact Contact Point identity")
if recipient.get("participation") != "not_established":
    raise RuntimeError("completed Communication improperly established participation")

relations = communication_current.record.field("relations")
if not isinstance(relations, tuple) or len(relations) != 1:
    raise RuntimeError("Communication response relation changed unexpectedly")
relation = relations[0]
if not isinstance(relation, Mapping):
    raise RuntimeError("Communication relation is malformed")
if relation.get("relation") != "relates_to_response":
    raise RuntimeError("Communication lost its bounded Response relation")
relation_ref = relation.get("record_ref")
if relation_ref != response_exact_ref.to_dict():
    raise RuntimeError("Communication relation did not remain exact")

communication_wire = communication_current.record.to_dict()
for forbidden in (
    "delivery",
    "delivered",
    "read_status",
    "agreement",
    "consent",
    "outcome",
    "engagement_score",
):
    if forbidden in communication_wire:
        raise RuntimeError(
            "Communication improperly encoded delivery/agreement/outcome semantics"
        )

if communication_current.record.field("act_state") == "completed" and (
    recipient.get("participation") != "not_established"
):
    raise RuntimeError("completed Communication was conflated with participation")

outcome_count_after = len(outcomes.list(work))
if outcome_count_before != 0 or outcome_count_after != 0:
    raise RuntimeError("Response or Communication manufactured an Outcome")

print(
    json.dumps(
        {
            "response_current": True,
            "response_execution_state": response_current.record.field(
                "execution_state"
            ),
            "response_review_pinned": (
                response_current.record.field("review_ref") == review_ref.to_dict()
            ),
            "response_determination_pinned": (
                response_current.record.field("determination_ref")
                == determination_ref.to_dict()
            ),
            "communication_current": True,
            "communication_act_state": communication_current.record.field(
                "act_state"
            ),
            "recipient_actor_exact": True,
            "contact_point_exact_current": True,
            "contact_verification_kind": verification.get("kind"),
            "recipient_participation": recipient.get("participation"),
            "response_relation_exact": True,
            "delivery_not_inferred": True,
            "agreement_not_inferred": True,
            "outcome_count": outcome_count_after,
            "outcome_not_inferred": True,
        },
        sort_keys=True,
    )
)
"""

_SUPPORT_PROCESS_PROBE = r"""
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    ResponseWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    response_reference,
    support_process_participant_reference,
    support_process_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
COUNSELOR_ACTOR_ID = "actr_counselor_001"
EVENT_ID = "evt_issue53_primary"
RESPONSE_ID = "rsp_issue53_neutral_support"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORTED_PARTICIPANT_ID = "spp_issue53_student"
COUNSELOR_PARTICIPANT_ID = "spp_issue53_counselor"
ROOT_CREATED_AT = "2026-10-04T12:50:00-04:00"
PARTICIPANT_CREATED_AT = "2026-10-04T12:51:00-04:00"
PARTICIPANT_ACTIVE_AT = "2026-10-04T12:52:00-04:00"
ROOT_ACTIVE_AT = "2026-10-04T12:53:00-04:00"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()

event_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
response_ref = response_reference(event_work, RESPONSE_ID)
response_exact = ResponseWorkflowService(workspace).resolve_exact(response_ref)
if response_exact.record.logical_id != RESPONSE_ID:
    raise RuntimeError("Support Process handoff source Response did not resolve exactly")

root_service = SupportProcessWorkflowService(workspace)
participant_service = SupportProcessParticipantWorkflowService(workspace)

root_record = parse_portia_record(
    "support_process",
    "1",
    {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "school_year": "2026-2027",
        "status": "proposed",
        "workflow_state": "planning",
        "summary": (
            "Synthetic longer-running support process initiated from the "
            "Event-local Response handoff."
        ),
        "initiation": {
            "kind": "response_handoff",
            "record_ref": response_ref.to_dict(),
        },
        "planned_start_date": "2026-10-05",
        "review_on": "2026-10-19",
        "creation_source": {"type": "digital_entry"},
        "created_at": ROOT_CREATED_AT,
        "created_by": AGENT,
        "updated_at": ROOT_CREATED_AT,
        "updated_by": AGENT,
    },
)
root_created = root_service.create(root_record)
support_work = support_process_reference(root_record)

if support_work.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("Support Process owner class changed during bootstrap")
if support_work.work_kind != "support_process":
    raise RuntimeError("Support Process did not retain distinct work kind")
if support_work.work_id == EVENT_ID:
    raise RuntimeError("Support Process reused Event work identity")


def participant_wire(participant_id, person, contexts):
    return {
        "schema_version": "1",
        "record_type": "support_process_participant",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "participant_id": participant_id,
        "status": "proposed",
        "person": person,
        "contexts": contexts,
        "creation_source": {"type": "digital_entry"},
        "created_at": PARTICIPANT_CREATED_AT,
        "created_by": AGENT,
        "updated_at": PARTICIPANT_CREATED_AT,
        "updated_by": AGENT,
    }


supported_record = parse_portia_record(
    "support_process_participant",
    "1",
    participant_wire(
        SUPPORTED_PARTICIPANT_ID,
        {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": SECONDARY_CLASS_ID,
                "student_id": COLLISION_STUDENT_ID,
            },
            "display_snapshot": {"display_name": "Shared Synthetic"},
        },
        [{"kind": "supported_person"}],
    ),
)
counselor_record = parse_portia_record(
    "support_process_participant",
    "1",
    participant_wire(
        COUNSELOR_PARTICIPANT_ID,
        {
            "kind": "actor",
            "actor_ref": {"actor_id": COUNSELOR_ACTOR_ID},
            "display_snapshot": {"display_name": "Synthetic Counselor"},
        },
        [
            {"kind": "provider_or_collaborator"},
            {"kind": "coordinator"},
        ],
    ),
)

supported_created = participant_service.create(support_work, supported_record)
counselor_created = participant_service.create(support_work, counselor_record)


def activate_participant(created, participant_id, transition_id, operation_id):
    wire = created.record.to_dict()
    wire["status"] = "active"
    wire["updated_at"] = PARTICIPANT_ACTIVE_AT
    wire["updated_by"] = AGENT
    active_candidate = parse_portia_record(
        "support_process_participant",
        "1",
        wire,
    )
    result = participant_service.transition_lifecycle(
        support_process_participant_reference(support_work, participant_id),
        active_candidate,
        expected=created.fingerprint,
        transition_id=transition_id,
        reason_code="planning_confirmed",
        operation_id=operation_id,
    )
    if result.accepted_steps != (
        "step_history",
        "step_transition",
        "step_record",
    ):
        raise RuntimeError("Support Process Participant activation path changed")
    return participant_service.require_current_use(
        support_process_participant_reference(support_work, participant_id)
    )


supported_current = activate_participant(
    supported_created,
    SUPPORTED_PARTICIPANT_ID,
    "lct_issue53_spp_student_active",
    "op_issue53_spp_student_active",
)
counselor_current = activate_participant(
    counselor_created,
    COUNSELOR_PARTICIPANT_ID,
    "lct_issue53_spp_counselor_active",
    "op_issue53_spp_counselor_active",
)

if supported_current.kind != "roster_student":
    raise RuntimeError("supported participant lost exact roster identity")
if supported_current.authority is None:
    raise RuntimeError("supported participant roster authority is absent")
if supported_current.authority.reference.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("Support Process relocalized cross-class supported student")
if supported_current.authority.reference.student_id != COLLISION_STUDENT_ID:
    raise RuntimeError("Support Process supported the wrong exact roster student")

if counselor_current.kind != "actor":
    raise RuntimeError("counselor participant lost Actor identity")
if counselor_current.authority is None:
    raise RuntimeError("counselor Actor authority is absent")
if counselor_current.authority.record.logical_id != COUNSELOR_ACTOR_ID:
    raise RuntimeError("Support Process resolved the wrong counselor Actor")

root_active_wire = root_created.record.to_dict()
root_active_wire["status"] = "active"
root_active_wire["updated_at"] = ROOT_ACTIVE_AT
root_active_wire["updated_by"] = AGENT
root_active_candidate = parse_portia_record(
    "support_process",
    "1",
    root_active_wire,
)
activation = root_service.transition_lifecycle(
    support_work,
    root_active_candidate,
    expected=root_created.fingerprint,
    transition_id="lct_issue53_support_active",
    reason_code="planning_confirmed",
    operation_id="op_issue53_support_active",
)
if activation.accepted_steps != (
    "step_history",
    "step_transition",
    "step_work",
):
    raise RuntimeError("Support Process activation path changed")

current_root = root_service.require_current_use(support_work)
if current_root.record.status != "active":
    raise RuntimeError("Support Process did not become current/active")
if current_root.record.field("workflow_state") != "planning":
    raise RuntimeError("Support Process activation silently changed planning state")

initiation = current_root.record.field("initiation")
if not isinstance(initiation, Mapping):
    raise RuntimeError("Support Process initiation is malformed")
if initiation.get("kind") != "response_handoff":
    raise RuntimeError("Support Process lost Response handoff initiation")
if initiation.get("record_ref") != response_ref.to_dict():
    raise RuntimeError("Support Process initiation silently retargeted the Response")

participants = participant_service.list(support_work)
if len(participants) != 2:
    raise RuntimeError("Support Process Participant cardinality changed")
if {item.record.logical_id for item in participants} != {
    SUPPORTED_PARTICIPANT_ID,
    COUNSELOR_PARTICIPANT_ID,
}:
    raise RuntimeError("Support Process Participant identities changed")

plan_counts = {
    "need": len(SupportNeedWorkflowService(workspace).list(support_work)),
    "goal": len(SupportGoalWorkflowService(workspace).list(support_work)),
    "support": len(SupportWorkflowService(workspace).list(support_work)),
}
if any(plan_counts.values()):
    raise RuntimeError("Support Process bootstrap manufactured planning records")

print(
    json.dumps(
        {
            "support_process_current": True,
            "support_process_status": current_root.record.status,
            "support_process_workflow_state": current_root.record.field(
                "workflow_state"
            ),
            "support_process_owner_class": current_root.record.class_id,
            "support_process_distinct_from_event": support_work.work_id != EVENT_ID,
            "response_handoff_exact": initiation.get("record_ref")
            == response_ref.to_dict(),
            "support_participant_count": len(participants),
            "supported_student_kind": supported_current.kind,
            "supported_student_class": supported_current.authority.reference.class_id,
            "supported_student_exact": True,
            "counselor_kind": counselor_current.kind,
            "counselor_actor_exact": True,
            "need_count": plan_counts["need"],
            "goal_count": plan_counts["goal"],
            "support_count": plan_counts["support"],
            "planning_not_inferred": all(value == 0 for value in plan_counts.values()),
        },
        sort_keys=True,
    )
)
"""

_SUPPORT_PLANNING_PROBE = r"""
import json
import sys
from collections.abc import Mapping
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    FidelityWorkflowService,
    FollowUpWorkflowService,
    ImplementationWorkflowService,
    OutcomeWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    support_goal_reference,
    support_need_reference,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORTED_PARTICIPANT_ID = "spp_issue53_student"
COUNSELOR_PARTICIPANT_ID = "spp_issue53_counselor"
NEED_ID = "spn_issue53_access"
GOAL_ID = "spg_issue53_access"
SUPPORT_ID = "spt_issue53_access"
PLAN_CREATED_AT = "2026-10-04T13:00:00-04:00"
ROOT_ACTIVE_STATE_AT = "2026-10-04T13:05:00-04:00"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)

root_service = SupportProcessWorkflowService(workspace)
need_service = SupportNeedWorkflowService(workspace)
goal_service = SupportGoalWorkflowService(workspace)
support_service = SupportWorkflowService(workspace)

root_before = root_service.require_current_use(work)
if root_before.record.status != "active":
    raise RuntimeError("Support Process is not active before planning")
if root_before.record.field("workflow_state") != "planning":
    raise RuntimeError("Support Process is not in planning state before plan creation")

participant_target = {
    "kind": "support_process_participant",
    "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": SUPPORTED_PARTICIPANT_ID,
        "contract_version": "1",
    },
}

need = parse_portia_record(
    "support_need",
    "1",
    {
        "schema_version": "1",
        "record_type": "support_need",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "need_id": NEED_ID,
        "status": "active",
        "target": participant_target,
        "need_kind": "environmental_or_instructional",
        "description": (
            "Provide a predictable lower-distraction work option during "
            "independent work when the supported participant chooses it."
        ),
        "creation_source": {"type": "digital_entry"},
        "created_at": PLAN_CREATED_AT,
        "created_by": AGENT,
        "updated_at": PLAN_CREATED_AT,
        "updated_by": AGENT,
    },
)
need_created = need_service.create(work, need)
need_ref = support_need_reference(work, NEED_ID)
need_current = need_service.require_current_use(need_ref)

goal = parse_portia_record(
    "support_goal",
    "1",
    {
        "schema_version": "1",
        "record_type": "support_goal",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "goal_id": GOAL_ID,
        "status": "active",
        "target": participant_target,
        "description": (
            "The supported participant will have the planned lower-distraction "
            "work option available during independent-work periods."
        ),
        "planned_criteria": (
            "Review later implementation records for whether the option was "
            "made available as planned."
        ),
        "measurement_approach": (
            "Use bounded Implementation and Fidelity records rather than "
            "inferring progress from the plan itself."
        ),
        "creation_source": {"type": "digital_entry"},
        "created_at": PLAN_CREATED_AT,
        "created_by": AGENT,
        "updated_at": PLAN_CREATED_AT,
        "updated_by": AGENT,
    },
)
goal_created = goal_service.create(work, goal)
goal_ref = support_goal_reference(work, GOAL_ID)
goal_current = goal_service.require_current_use(goal_ref)

support = parse_portia_record(
    "support",
    "1",
    {
        "schema_version": "1",
        "record_type": "support",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "support_id": SUPPORT_ID,
        "status": "active",
        "target": participant_target,
        "need_refs": [
            {
                "record_kind": "support_need",
                "record_id": NEED_ID,
                "contract_version": "1",
            }
        ],
        "goal_refs": [
            {
                "record_kind": "support_goal",
                "record_id": GOAL_ID,
                "contract_version": "1",
            }
        ],
        "strategy": {
            "kind": "environmental_or_instructional",
            "procedure": (
                "At the start of independent work, make the designated "
                "lower-distraction location available and briefly remind the "
                "participant that the option may be selected."
            ),
        },
        "provider_plan": {
            "kind": "assigned",
            "participant_refs": [
                {
                    "record_kind": "support_process_participant",
                    "record_id": COUNSELOR_PARTICIPANT_ID,
                    "contract_version": "1",
                }
            ],
        },
        "schedule": {
            "kind": "recurring",
            "window": {
                "starts_on": "2026-10-05",
                "ends_on": "2026-10-18",
                "review_on": "2026-10-19",
            },
            "frequency": {
                "occurrences": 1,
                "interval_count": 1,
                "interval_unit": "day",
            },
            "selected_days": [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
            ],
            "timing_detail": "During scheduled independent-work periods.",
        },
        "plan_state": "active",
        "creation_source": {"type": "digital_entry"},
        "created_at": PLAN_CREATED_AT,
        "created_by": AGENT,
        "updated_at": PLAN_CREATED_AT,
        "updated_by": AGENT,
    },
)
support_created = support_service.create(work, support)
support_ref = support_reference(work, SUPPORT_ID)
support_current = support_service.require_current_use(support_ref)

if need_created.fingerprint != need_current.fingerprint:
    raise RuntimeError("Support Need current representation changed unexpectedly")
if goal_created.fingerprint != goal_current.fingerprint:
    raise RuntimeError("Support Goal current representation changed unexpectedly")
if support_created.fingerprint != support_current.fingerprint:
    raise RuntimeError("Support current representation changed unexpectedly")

if need_current.record.field("target") != participant_target:
    raise RuntimeError("Support Need lost exact supported Participant target")
if goal_current.record.field("target") != participant_target:
    raise RuntimeError("Support Goal lost exact supported Participant target")
if support_current.record.field("target") != participant_target:
    raise RuntimeError("Support lost exact supported Participant target")

need_refs = support_current.record.field("need_refs")
goal_refs = support_current.record.field("goal_refs")
provider_plan = support_current.record.field("provider_plan")
if not isinstance(need_refs, tuple) or len(need_refs) != 1:
    raise RuntimeError("Support exact Need linkage changed")
if not isinstance(goal_refs, tuple) or len(goal_refs) != 1:
    raise RuntimeError("Support exact Goal linkage changed")
if not isinstance(provider_plan, Mapping):
    raise RuntimeError("Support provider plan is malformed")

if need_refs[0] != {
    "record_kind": "support_need",
    "record_id": NEED_ID,
    "contract_version": "1",
}:
    raise RuntimeError("Support does not exactly name the active Need")
if goal_refs[0] != {
    "record_kind": "support_goal",
    "record_id": GOAL_ID,
    "contract_version": "1",
}:
    raise RuntimeError("Support does not exactly name the active Goal")

provider_refs = provider_plan.get("participant_refs")
if not isinstance(provider_refs, tuple) or provider_refs != (
    {
        "record_kind": "support_process_participant",
        "record_id": COUNSELOR_PARTICIPANT_ID,
        "contract_version": "1",
    },
):
    raise RuntimeError("Support did not preserve exact counselor provider assignment")

root_active_wire = root_before.record.to_dict()
root_active_wire["workflow_state"] = "active"
root_active_wire["updated_at"] = ROOT_ACTIVE_STATE_AT
root_active_wire["updated_by"] = AGENT
root_active_candidate = parse_portia_record(
    "support_process",
    "1",
    root_active_wire,
)
root_after = root_service.transition_workflow_state(
    work,
    root_active_candidate,
    expected=root_before.fingerprint,
)

if root_after.record.status != "active":
    raise RuntimeError("Support Process lifecycle status changed during workflow progression")
if root_after.record.field("workflow_state") != "active":
    raise RuntimeError("Support Process did not enter active workflow state")
if root_after.record.logical_id != SUPPORT_PROCESS_ID:
    raise RuntimeError("Support Process workflow progression changed canonical identity")

execution_counts = {
    "implementation": len(ImplementationWorkflowService(workspace).list(work)),
    "fidelity": len(FidelityWorkflowService(workspace).list(work)),
    "follow_up": len(FollowUpWorkflowService(workspace).list(work)),
    "outcome": len(OutcomeWorkflowService(workspace).list(work)),
}
if any(execution_counts.values()):
    raise RuntimeError("Support planning manufactured execution, follow-up, or Outcome")

for record in (
    need_current.record.to_dict(),
    goal_current.record.to_dict(),
    support_current.record.to_dict(),
):
    for forbidden in (
        "diagnosis",
        "progress",
        "effectiveness",
        "outcome",
        "fidelity",
        "implementation",
    ):
        if forbidden in record:
            raise RuntimeError("Support planning introduced inferred downstream semantics")

print(
    json.dumps(
        {
            "need_current": True,
            "goal_current": True,
            "support_current": True,
            "need_target_exact": need_current.record.field("target")
            == participant_target,
            "goal_target_exact": goal_current.record.field("target")
            == participant_target,
            "support_target_exact": support_current.record.field("target")
            == participant_target,
            "support_need_exact": True,
            "support_goal_exact": True,
            "support_provider_exact": True,
            "support_plan_state": support_current.record.field("plan_state"),
            "support_process_status": root_after.record.status,
            "support_process_workflow_state": root_after.record.field(
                "workflow_state"
            ),
            "support_process_identity_preserved": (
                root_after.record.logical_id == SUPPORT_PROCESS_ID
            ),
            "implementation_count": execution_counts["implementation"],
            "fidelity_count": execution_counts["fidelity"],
            "follow_up_count": execution_counts["follow_up"],
            "outcome_count": execution_counts["outcome"],
            "downstream_not_inferred": all(
                value == 0 for value in execution_counts.values()
            ),
        },
        sort_keys=True,
    )
)
"""

_IMPLEMENTATION_FIDELITY_PROBE = r"""
import json
import sys
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    FidelityWorkflowService,
    FollowUpWorkflowService,
    ImplementationWorkflowService,
    OutcomeWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    fidelity_reference,
    implementation_reference,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORTED_PARTICIPANT_ID = "spp_issue53_student"
COUNSELOR_PARTICIPANT_ID = "spp_issue53_counselor"
SUPPORT_ID = "spt_issue53_access"
IMPLEMENTATION_ONE_ID = "imp_issue53_access_001"
IMPLEMENTATION_TWO_ID = "imp_issue53_access_002"
FIDELITY_ID = "fid_issue53_access"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)

root_service = SupportProcessWorkflowService(workspace)
support_service = SupportWorkflowService(workspace)
implementation_service = ImplementationWorkflowService(workspace)
fidelity_service = FidelityWorkflowService(workspace)
outcome_service = OutcomeWorkflowService(workspace)
follow_up_service = FollowUpWorkflowService(workspace)

root_before = root_service.require_current_use(work)
if root_before.record.status != "active":
    raise RuntimeError("Support Process is not current before execution history")
if root_before.record.field("workflow_state") != "active":
    raise RuntimeError("Support Process workflow is not active before execution history")

support_ref = support_reference(work, SUPPORT_ID)
support_before = support_service.require_current_use(support_ref)
support_before_fingerprint = support_before.fingerprint
if support_before.record.field("plan_state") != "active":
    raise RuntimeError("Support plan is not active before Implementation")

participant_target = {
    "kind": "support_process_participant",
    "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": SUPPORTED_PARTICIPANT_ID,
        "contract_version": "1",
    },
}
participant_provider = {
    "kind": "participants",
    "participant_refs": [
        {
            "record_kind": "support_process_participant",
            "record_id": COUNSELOR_PARTICIPANT_ID,
            "contract_version": "1",
        }
    ],
}
plan_ref = {
    "record_kind": "support",
    "record_id": SUPPORT_ID,
    "contract_version": "1",
}


def implementation_wire(
    implementation_id,
    started_at,
    ended_at,
    recorded_at,
    summary,
):
    return {
        "schema_version": "1",
        "record_type": "implementation",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "implementation_id": implementation_id,
        "status": "active",
        "plan_ref": plan_ref,
        "actual_target": participant_target,
        "implementation_provider": participant_provider,
        "execution_state": "completed",
        "started_at": started_at,
        "ended_at": ended_at,
        "summary": summary,
        "creation_source": {"type": "digital_entry"},
        "created_at": recorded_at,
        "created_by": AGENT,
        "updated_at": recorded_at,
        "updated_by": AGENT,
    }


implementation_one = parse_portia_record(
    "implementation",
    "1",
    implementation_wire(
        IMPLEMENTATION_ONE_ID,
        "2026-10-04T13:10:00-04:00",
        "2026-10-04T13:18:00-04:00",
        "2026-10-04T13:19:00-04:00",
        (
            "Synthetic first occurrence: the planned lower-distraction "
            "location was made available during independent work."
        ),
    ),
)
implementation_two = parse_portia_record(
    "implementation",
    "1",
    implementation_wire(
        IMPLEMENTATION_TWO_ID,
        "2026-10-04T13:25:00-04:00",
        "2026-10-04T13:33:00-04:00",
        "2026-10-04T13:34:00-04:00",
        (
            "Synthetic second occurrence: the planned lower-distraction "
            "location was again made available during independent work."
        ),
    ),
)

created_one = implementation_service.create(work, implementation_one)
created_two = implementation_service.create(work, implementation_two)

one_ref = implementation_reference(work, IMPLEMENTATION_ONE_ID)
two_ref = implementation_reference(work, IMPLEMENTATION_TWO_ID)
current_one = implementation_service.require_current_use(one_ref)
current_two = implementation_service.require_current_use(two_ref)

if current_one.record.logical_id == current_two.record.logical_id:
    raise RuntimeError("distinct Implementation occurrences collapsed identity")
if current_one.path == current_two.path:
    raise RuntimeError("distinct Implementation occurrences collapsed storage path")
if current_one.record.field("plan_ref") != plan_ref:
    raise RuntimeError("first Implementation lost exact Support plan reference")
if current_two.record.field("plan_ref") != plan_ref:
    raise RuntimeError("second Implementation lost exact Support plan reference")
if current_one.record.field("actual_target") != participant_target:
    raise RuntimeError("first Implementation changed exact supported target")
if current_two.record.field("actual_target") != participant_target:
    raise RuntimeError("second Implementation changed exact supported target")
if current_one.record.field("implementation_provider") != participant_provider:
    raise RuntimeError("first Implementation changed exact counselor provider")
if current_two.record.field("implementation_provider") != participant_provider:
    raise RuntimeError("second Implementation changed exact counselor provider")
if current_one.record.field("execution_state") != "completed":
    raise RuntimeError("first Implementation did not remain completed")
if current_two.record.field("execution_state") != "completed":
    raise RuntimeError("second Implementation did not remain completed")

implementations = implementation_service.list(work)
implementation_ids = tuple(
    item.record.logical_id
    for item in implementations
    if item.record.logical_id in {
        IMPLEMENTATION_ONE_ID,
        IMPLEMENTATION_TWO_ID,
    }
)
if set(implementation_ids) != {
    IMPLEMENTATION_ONE_ID,
    IMPLEMENTATION_TWO_ID,
}:
    raise RuntimeError("Implementation history did not retain both exact occurrences")

implementation_refs = [
    {
        "record_kind": "implementation",
        "record_id": IMPLEMENTATION_ONE_ID,
        "contract_version": "1",
    },
    {
        "record_kind": "implementation",
        "record_id": IMPLEMENTATION_TWO_ID,
        "contract_version": "1",
    },
]

fidelity = parse_portia_record(
    "fidelity",
    "1",
    {
        "schema_version": "1",
        "record_type": "fidelity",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_id": SUPPORT_PROCESS_ID,
        "fidelity_id": FIDELITY_ID,
        "status": "active",
        "plan_ref": plan_ref,
        "evaluator_ref": {
            "record_kind": "support_process_participant",
            "record_id": COUNSELOR_PARTICIPANT_ID,
            "contract_version": "1",
        },
        "scope": {
            "kind": "implementation_set",
            "implementation_refs": implementation_refs,
        },
        "result": "as_planned",
        "basis": {
            "kind": "implementation_records",
            "record_refs": implementation_refs,
        },
        "evaluated_at": "2026-10-04T13:38:00-04:00",
        "summary": (
            "The two exact Implementation records document that the planned "
            "availability step was carried out as recorded. This Fidelity "
            "evaluation addresses adherence only, not effectiveness or Outcome."
        ),
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-10-04T13:40:00-04:00",
        "created_by": AGENT,
        "updated_at": "2026-10-04T13:40:00-04:00",
        "updated_by": AGENT,
    },
)
fidelity_created = fidelity_service.create(work, fidelity)
fidelity_ref = fidelity_reference(work, FIDELITY_ID)
fidelity_current = fidelity_service.require_current_use(fidelity_ref)

if fidelity_created.fingerprint != fidelity_current.fingerprint:
    raise RuntimeError("Fidelity current representation changed unexpectedly")
if fidelity_current.record.field("plan_ref") != plan_ref:
    raise RuntimeError("Fidelity lost exact Support plan reference")

scope = fidelity_current.record.field("scope")
basis = fidelity_current.record.field("basis")
if not isinstance(scope, dict) and not hasattr(scope, "get"):
    raise RuntimeError("Fidelity scope is malformed")
if not isinstance(basis, dict) and not hasattr(basis, "get"):
    raise RuntimeError("Fidelity basis is malformed")
if scope.get("kind") != "implementation_set":
    raise RuntimeError("Fidelity did not retain implementation-set scope")
scope_refs = scope.get("implementation_refs")
basis_refs = basis.get("record_refs")
if tuple(scope_refs) != tuple(implementation_refs):
    raise RuntimeError("Fidelity scope lost exact Implementation identities")
if basis.get("kind") != "implementation_records":
    raise RuntimeError("Fidelity basis changed from implementation records")
if tuple(basis_refs) != tuple(implementation_refs):
    raise RuntimeError("Fidelity basis lost exact Implementation identities")
if fidelity_current.record.field("result") != "as_planned":
    raise RuntimeError("Fidelity result changed unexpectedly")

fidelity_wire = fidelity_current.record.to_dict()
for forbidden in (
    "effectiveness",
    "outcome",
    "progress",
    "success",
    "compliance",
    "provider_competence",
):
    if forbidden in fidelity_wire:
        raise RuntimeError("Fidelity record introduced prohibited inferred semantics")

for implementation in (current_one.record.to_dict(), current_two.record.to_dict()):
    for forbidden in ("fidelity", "effectiveness", "outcome", "successful"):
        if forbidden in implementation:
            raise RuntimeError(
                "Implementation occurrence introduced prohibited inferred semantics"
            )

support_after = support_service.require_current_use(support_ref)
if support_after.fingerprint != support_before_fingerprint:
    raise RuntimeError("execution history mutated the exact Support plan")

root_after = root_service.require_current_use(work)
if root_after.fingerprint != root_before.fingerprint:
    raise RuntimeError("execution history mutated the Support Process root")
if root_after.record.field("workflow_state") != "active":
    raise RuntimeError("execution history changed Support Process workflow state")

outcome_count = len(outcome_service.list(work))
follow_up_count = len(follow_up_service.list(work))
if outcome_count != 0:
    raise RuntimeError("positive Fidelity manufactured an Outcome")
if follow_up_count != 0:
    raise RuntimeError("execution/Fidelity stage manufactured a Follow-Up")

print(
    json.dumps(
        {
            "implementation_count": len(implementation_ids),
            "implementation_one_current": (
                created_one.fingerprint == current_one.fingerprint
            ),
            "implementation_two_current": (
                created_two.fingerprint == current_two.fingerprint
            ),
            "implementation_identities_distinct": (
                current_one.record.logical_id != current_two.record.logical_id
            ),
            "implementation_paths_distinct": current_one.path != current_two.path,
            "implementation_plan_exact": (
                current_one.record.field("plan_ref") == plan_ref
                and current_two.record.field("plan_ref") == plan_ref
            ),
            "implementation_target_exact": (
                current_one.record.field("actual_target") == participant_target
                and current_two.record.field("actual_target") == participant_target
            ),
            "implementation_provider_exact": (
                current_one.record.field("implementation_provider")
                == participant_provider
                and current_two.record.field("implementation_provider")
                == participant_provider
            ),
            "fidelity_current": True,
            "fidelity_result": fidelity_current.record.field("result"),
            "fidelity_scope_exact": tuple(scope_refs) == tuple(implementation_refs),
            "fidelity_basis_exact": tuple(basis_refs) == tuple(implementation_refs),
            "support_plan_unchanged": (
                support_after.fingerprint == support_before_fingerprint
            ),
            "support_process_unchanged": root_after.fingerprint == root_before.fingerprint,
            "follow_up_count": follow_up_count,
            "outcome_count": outcome_count,
            "effectiveness_not_inferred": True,
            "outcome_not_inferred": outcome_count == 0,
        },
        sort_keys=True,
    )
)
"""

_FOLLOW_UP_ATTENTION_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    FidelityWorkflowService,
    FollowUpWorkflowService,
    OutcomeWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    fidelity_reference,
    follow_up_reference,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORTED_PARTICIPANT_ID = "spp_issue53_student"
COUNSELOR_PARTICIPANT_ID = "spp_issue53_counselor"
SUPPORT_ID = "spt_issue53_access"
FIDELITY_ID = "fid_issue53_access"
FOLLOW_UP_ID = "fup_issue53_review"
PLANNED_AT = "2026-10-19T09:00:00-04:00"
CREATED_AT = "2026-10-04T13:45:00-04:00"
COMPLETED_AT = "2026-10-19T09:10:00-04:00"
AS_OF = ExplicitOffsetTimestamp(PLANNED_AT)
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)


def snapshot(root):
    observed = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            observed.append(
                (
                    path.relative_to(root).as_posix(),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            )
    return tuple(observed)


root_service = SupportProcessWorkflowService(workspace)
support_service = SupportWorkflowService(workspace)
fidelity_service = FidelityWorkflowService(workspace)
follow_up_service = FollowUpWorkflowService(workspace)
outcome_service = OutcomeWorkflowService(workspace)
attention_service = AttentionQueryService(workspace)

root_before = root_service.require_current_use(work)
support_before = support_service.require_current_use(
    support_reference(work, SUPPORT_ID)
)
fidelity_before = fidelity_service.require_current_use(
    fidelity_reference(work, FIDELITY_ID)
)

if root_before.record.status != "active":
    raise RuntimeError("Support Process is not active before Follow-Up")
if root_before.record.field("workflow_state") != "active":
    raise RuntimeError("Support Process workflow is not active before Follow-Up")
if support_before.record.field("plan_state") != "active":
    raise RuntimeError("Support plan is not active before Follow-Up")
if fidelity_before.record.field("result") != "as_planned":
    raise RuntimeError("expected bounded Fidelity result is absent before Follow-Up")

target = {
    "kind": "support_process_participant",
    "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": SUPPORTED_PARTICIPANT_ID,
        "contract_version": "1",
    },
}
owner = {
    "kind": "support_process_participant",
    "participant_ref": {
        "record_kind": "support_process_participant",
        "record_id": COUNSELOR_PARTICIPANT_ID,
        "contract_version": "1",
    },
}

scheduled_record = parse_portia_record(
    "follow_up",
    "1",
    {
        "schema_version": "1",
        "record_type": "follow_up",
        "module_id": "portia",
        "class_id": PRIMARY_CLASS_ID,
        "work_kind": "support_process",
        "work_id": SUPPORT_PROCESS_ID,
        "follow_up_id": FOLLOW_UP_ID,
        "status": "active",
        "target": target,
        "owner": owner,
        "purpose": {"kind": "support_process_review"},
        "planned_timing": {
            "kind": "exact_time",
            "at": PLANNED_AT,
        },
        "workflow_state": "scheduled",
        "creation_source": {"type": "digital_entry"},
        "created_at": CREATED_AT,
        "created_by": AGENT,
        "updated_at": CREATED_AT,
        "updated_by": AGENT,
    },
)
scheduled = follow_up_service.create(work, scheduled_record)
follow_up_ref = follow_up_reference(work, FOLLOW_UP_ID)
scheduled_current = follow_up_service.require_current_use(follow_up_ref)

if scheduled_current.record.field("workflow_state") != "scheduled":
    raise RuntimeError("Follow-Up did not remain explicitly scheduled")
if scheduled_current.record.field("planned_timing") != {
    "kind": "exact_time",
    "at": PLANNED_AT,
}:
    raise RuntimeError("Follow-Up lost its exact planned timing")
if scheduled_current.record.field("target") != target:
    raise RuntimeError("Follow-Up lost exact supported Participant target")
if scheduled_current.record.field("owner") != owner:
    raise RuntimeError("Follow-Up lost exact counselor owner")

attention_query = PortiaAttentionQuery(
    scope=PortiaAttentionScope.work_scope(work),
    as_of=AS_OF,
    active_school_year="2026-2027",
    attention_codes=(
        "portia_follow_up_due",
        "portia_follow_up_overdue",
    ),
)

before_attention_snapshot = snapshot(workspace)
before_attention = attention_service.query(attention_query)
after_attention_snapshot = snapshot(workspace)
if before_attention_snapshot != after_attention_snapshot:
    raise RuntimeError("pre-completion AttentionQueryService mutated workspace")

if before_attention.evaluation != "evaluated":
    raise RuntimeError("pre-completion attention was not evaluated")
if len(before_attention.items) != 1:
    raise RuntimeError("scheduled due Follow-Up did not surface one attention item")
attention_item = before_attention.items[0]
if attention_item.code != "portia_follow_up_due":
    raise RuntimeError("scheduled Follow-Up surfaced the wrong attention code")
if attention_item.source_ref != follow_up_ref:
    raise RuntimeError("Follow-Up attention did not preserve exact source identity")
if attention_item.timing is None or attention_item.timing.classification != "due":
    raise RuntimeError("Follow-Up attention did not retain due timing")

reviewed_support = {
    "role": "reviewed",
    "record_ref": {
        "work_ref": work.to_dict(),
        "record_ref": {
            "record_kind": "support",
            "record_id": SUPPORT_ID,
            "contract_version": "1",
        },
    },
}
reviewed_fidelity = {
    "role": "reviewed",
    "record_ref": {
        "work_ref": work.to_dict(),
        "record_ref": {
            "record_kind": "fidelity",
            "record_id": FIDELITY_ID,
            "contract_version": "1",
        },
    },
}

completed_wire = scheduled_current.record.to_dict()
completed_wire["workflow_state"] = "completed"
completed_wire["completed_at"] = COMPLETED_AT
completed_wire["related_records"] = [
    reviewed_support,
    reviewed_fidelity,
]
completed_wire["disposition"] = {"kind": "continue_current_support"}
completed_wire["updated_at"] = COMPLETED_AT
completed_wire["updated_by"] = AGENT
completed_candidate = parse_portia_record(
    "follow_up",
    "1",
    completed_wire,
)
completed = follow_up_service.transition_workflow_state(
    follow_up_ref,
    completed_candidate,
    expected=scheduled_current.fingerprint,
)

if completed.record.logical_id != FOLLOW_UP_ID:
    raise RuntimeError("Follow-Up completion changed exact identity")
if completed.record.status != "active":
    raise RuntimeError("Follow-Up completion changed canonical lifecycle")
if completed.record.field("workflow_state") != "completed":
    raise RuntimeError("Follow-Up did not complete through production workflow")
if completed.record.field("completed_at") != COMPLETED_AT:
    raise RuntimeError("Follow-Up completion timestamp changed")
if completed.record.field("disposition") != {
    "kind": "continue_current_support"
}:
    raise RuntimeError("Follow-Up did not preserve explicit continue-support disposition")

related_records = completed.record.field("related_records")
if not isinstance(related_records, tuple):
    raise RuntimeError("completed Follow-Up related records are malformed")
if tuple(related_records) != (reviewed_support, reviewed_fidelity):
    raise RuntimeError("completed Follow-Up did not retain exact reviewed records")

after_completion_snapshot = snapshot(workspace)
after_attention = attention_service.query(attention_query)
after_post_query_snapshot = snapshot(workspace)
if after_completion_snapshot != after_post_query_snapshot:
    raise RuntimeError("post-completion AttentionQueryService mutated workspace")

if after_attention.evaluation != "evaluated":
    raise RuntimeError("post-completion attention was not evaluated")
if after_attention.items:
    raise RuntimeError("completed Follow-Up remained outstanding attention")

outcomes = outcome_service.list(work)
if outcomes:
    raise RuntimeError("completed Follow-Up or positive Fidelity manufactured Outcome")

root_after = root_service.require_current_use(work)
if root_after.fingerprint != root_before.fingerprint:
    raise RuntimeError("Follow-Up completion mutated Support Process root")
if root_after.record.status != "active":
    raise RuntimeError("Follow-Up completion changed Support Process lifecycle")
if root_after.record.field("workflow_state") != "active":
    raise RuntimeError("Follow-Up completion automatically completed Support Process")

support_after = support_service.require_current_use(
    support_reference(work, SUPPORT_ID)
)
if support_after.fingerprint != support_before.fingerprint:
    raise RuntimeError("Follow-Up completion mutated Support plan")

fidelity_after = fidelity_service.require_current_use(
    fidelity_reference(work, FIDELITY_ID)
)
if fidelity_after.fingerprint != fidelity_before.fingerprint:
    raise RuntimeError("Follow-Up completion rewrote Fidelity")
if fidelity_after.record.field("result") != "as_planned":
    raise RuntimeError("Follow-Up completion changed Fidelity result")

completed_wire_check = completed.record.to_dict()
for forbidden in (
    "outcome",
    "effectiveness",
    "progress",
    "causation",
):
    if forbidden in completed_wire_check:
        raise RuntimeError("Follow-Up introduced inferred result semantics")

print(
    json.dumps(
        {
            "follow_up_current": True,
            "follow_up_status": completed.record.status,
            "follow_up_workflow_state": completed.record.field("workflow_state"),
            "follow_up_planned_at": PLANNED_AT,
            "follow_up_completed_at": completed.record.field("completed_at"),
            "follow_up_identity_preserved": completed.record.logical_id
            == FOLLOW_UP_ID,
            "reviewed_support_exact": reviewed_support in related_records,
            "reviewed_fidelity_exact": reviewed_fidelity in related_records,
            "disposition": completed.record.field("disposition")["kind"],
            "attention_before_code": attention_item.code,
            "attention_before_timing": attention_item.timing.classification,
            "attention_after_count": len(after_attention.items),
            "attention_queries_zero_write": True,
            "outcome_count": len(outcomes),
            "support_process_status": root_after.record.status,
            "support_process_workflow_state": root_after.record.field(
                "workflow_state"
            ),
            "support_process_unchanged": root_after.fingerprint
            == root_before.fingerprint,
            "support_plan_unchanged": support_after.fingerprint
            == support_before.fingerprint,
            "fidelity_unchanged": fidelity_after.fingerprint
            == fidelity_before.fingerprint,
            "outcome_not_inferred": len(outcomes) == 0,
            "process_completion_not_inferred": (
                root_after.record.field("workflow_state") == "active"
            ),
        },
        sort_keys=True,
    )
)
"""

_CORE_PROVIDER_PROBE = r"""
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

from pds_core.module_operations import (
    MODULE_OPERATIONS_ENTRY_POINT_GROUP,
    ModuleOperationsRequest,
    invoke_module_operations,
)
from pds_core.provider_diagnostics import (
    diagnose_core_providers,
    inspect_core_provider_entry_points,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
ACTIVE_SCHOOL_YEAR = "2026-2027"

workspace = Path(sys.argv[1]).resolve()


def snapshot(root):
    return tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


baseline = snapshot(workspace)

metadata_rows = inspect_core_provider_entry_points(
    provider_kind="module_operations"
)
portia_metadata = tuple(
    row for row in metadata_rows if row.entry_point_name == "portia"
)
if len(portia_metadata) != 1:
    raise RuntimeError("Core metadata inspection did not find exactly one Portia provider")
metadata_row = portia_metadata[0]
if metadata_row.entry_point_group != MODULE_OPERATIONS_ENTRY_POINT_GROUP:
    raise RuntimeError("Portia provider is registered under the wrong Core group")
if (
    metadata_row.entry_point_target
    != "portia.pds_operations:get_module_operations_profile"
):
    raise RuntimeError("Portia provider target changed")
distribution_name = metadata_row.distribution_name
if not isinstance(distribution_name, str):
    raise RuntimeError("Portia provider metadata lost distribution identity")
if distribution_name.casefold().replace("_", "-") != "pds-portia":
    raise RuntimeError("Portia provider metadata points at the wrong distribution")

after_metadata = snapshot(workspace)
if after_metadata != baseline:
    raise RuntimeError("Core metadata-only provider inspection mutated workspace")

diagnostics = diagnose_core_providers(provider_kind="module_operations")
portia_diagnostics = tuple(
    result
    for result in diagnostics
    if result.metadata.entry_point_name == "portia"
)
if len(portia_diagnostics) != 1:
    raise RuntimeError("Core provider diagnosis did not isolate one Portia provider")
diagnostic = portia_diagnostics[0]
if diagnostic.code != "provider.valid":
    raise RuntimeError("Core did not diagnose installed Portia provider as valid")
if diagnostic.stage != "valid":
    raise RuntimeError("Portia provider diagnosis did not reach valid stage")
if diagnostic.declared_identity != "portia":
    raise RuntimeError("Portia provider diagnosis lost module identity")
if diagnostic.profile_validation != "passed":
    raise RuntimeError("Portia provider profile did not pass Core validation")
if diagnostic.core_compatibility != "passed":
    raise RuntimeError("Portia provider is not compatible with Core operations v1")
if diagnostic.registry_conflict:
    raise RuntimeError("Portia provider identity unexpectedly conflicts")
profile = diagnostic.validated_profile
if profile is None:
    raise RuntimeError("valid Portia provider diagnosis did not retain profile")
if profile.module_id != "portia":
    raise RuntimeError("diagnosed Portia profile has wrong module identity")
if profile.supported_core_operations_contract_versions != frozenset({"1"}):
    raise RuntimeError("diagnosed Portia profile has wrong Core contract set")
if profile.readiness_provider is None or profile.attention_provider is None:
    raise RuntimeError("diagnosed Portia profile lost readiness or attention")

after_diagnostics = snapshot(workspace)
if after_diagnostics != baseline:
    raise RuntimeError("Core provider diagnosis mutated workspace")

request = ModuleOperationsRequest(
    workspace_root=workspace,
    active_school_year=ACTIVE_SCHOOL_YEAR,
    class_id=PRIMARY_CLASS_ID,
)
readiness, attention = invoke_module_operations(profile, request)

after_invocation = snapshot(workspace)
if after_invocation != baseline:
    raise RuntimeError("Core module-operations invocation mutated workspace")

if readiness.module_id != "portia" or readiness.capability != "readiness":
    raise RuntimeError("Core readiness invocation lost Portia capability identity")
if readiness.code != "module_operations.evaluated":
    raise RuntimeError("Portia readiness did not evaluate through Core")
if not readiness.provider_call_attempted or not readiness.provider_call_succeeded:
    raise RuntimeError("Core readiness invocation did not call provider successfully")
if readiness.result_validation != "passed":
    raise RuntimeError("Core readiness result did not pass shared validation")
if readiness.report is None:
    raise RuntimeError("Core readiness invocation returned no report")
if readiness.report.evaluation != "evaluated":
    raise RuntimeError("Portia readiness report is not evaluated")
if readiness.report.ready is not True:
    raise RuntimeError("exact primary Core class is not Portia-ready")

if attention.module_id != "portia" or attention.capability != "attention":
    raise RuntimeError("Core attention invocation lost Portia capability identity")
if attention.code != "module_operations.evaluated":
    raise RuntimeError("Portia attention did not evaluate through Core")
if not attention.provider_call_attempted or not attention.provider_call_succeeded:
    raise RuntimeError("Core attention invocation did not call provider successfully")
if attention.result_validation != "passed":
    raise RuntimeError("Core attention result did not pass shared validation")
if attention.report is None:
    raise RuntimeError("Core attention invocation returned no report")
if attention.report.evaluation != "evaluated":
    raise RuntimeError("Portia attention report is not evaluated")

for summary in attention.report.summaries:
    if summary.class_id not in {None, PRIMARY_CLASS_ID}:
        raise RuntimeError("shared attention leaked foreign class context")
    if summary.work_ref is not None:
        if summary.work_ref.module_id != "portia":
            raise RuntimeError("shared attention work reference has foreign owner")
        if summary.work_ref.class_id != PRIMARY_CLASS_ID:
            raise RuntimeError("shared attention work reference escaped class scope")
    if summary.action is not None and summary.action.module_id != "portia":
        raise RuntimeError("shared attention action has foreign owner")

shared = {
    "readiness": asdict(readiness.report),
    "attention": asdict(attention.report),
}
if set(shared["readiness"]) != {"evaluation", "ready", "notices"}:
    raise RuntimeError("Core readiness projection gained an unexpected payload field")
if set(shared["attention"]) != {"evaluation", "summaries", "notices"}:
    raise RuntimeError("Core attention projection gained an unexpected payload field")

for summary in shared["attention"]["summaries"]:
    if set(summary) != {
        "code",
        "label",
        "count",
        "class_id",
        "work_ref",
        "action",
    }:
        raise RuntimeError("Core attention summary gained an unexpected payload field")

serialized = json.dumps(shared, sort_keys=True, default=str)
prohibited = (
    "student_shared_001",
    "Shared Synthetic",
    "Synthetic Counselor",
    "journalism_p6_2026",
    "actr_guardian_001",
    "actr_counselor_001",
    "acp_guardian_email_001",
    "guardian.issue53@example.invalid",
    "acct_issue53_cross_report",
    "acct_issue53_cross_corrected",
    "obs_issue53_cross_observed",
    "comm_issue53_guardian",
    "rsp_issue53_neutral_support",
    "imp_issue53_access_001",
    "imp_issue53_access_002",
    "fid_issue53_access",
    "fup_issue53_review",
    "Synthetic classroom material-location discrepancy.",
    "blue marker",
    str(workspace),
)
for value in prohibited:
    if value in serialized:
        raise RuntimeError(
            "Core shared module-operations projection leaked private Portia state"
        )

lowered = serialized.casefold()
for prohibited_key in (
    "workspace_root",
    "contact_point",
    "email_address",
    "student_name",
    "actor_id",
    "record_body",
    "raw_record",
    "narrative",
):
    if prohibited_key in lowered:
        raise RuntimeError(
            "Core shared module-operations projection exposed a private payload field"
        )

print(
    json.dumps(
        {
            "metadata_provider_count": len(portia_metadata),
            "metadata_group_exact": (
                metadata_row.entry_point_group
                == MODULE_OPERATIONS_ENTRY_POINT_GROUP
            ),
            "metadata_target_exact": (
                metadata_row.entry_point_target
                == "portia.pds_operations:get_module_operations_profile"
            ),
            "diagnostic_code": diagnostic.code,
            "diagnostic_profile_validation": diagnostic.profile_validation,
            "diagnostic_core_compatibility": diagnostic.core_compatibility,
            "profile_module_id": profile.module_id,
            "profile_contract_v1": (
                profile.supported_core_operations_contract_versions
                == frozenset({"1"})
            ),
            "readiness_code": readiness.code,
            "readiness_ready": readiness.report.ready,
            "attention_code": attention.code,
            "attention_evaluation": attention.report.evaluation,
            "attention_summary_count": len(attention.report.summaries),
            "provider_zero_write": after_invocation == baseline,
            "metadata_zero_write": after_metadata == baseline,
            "diagnostics_zero_write": after_diagnostics == baseline,
            "shared_projection_privacy_bounded": True,
            "foreign_class_not_exposed": "journalism_p6_2026" not in serialized,
            "workspace_path_not_exposed": str(workspace) not in serialized,
        },
        sort_keys=True,
    )
)
"""

_STALE_CONFLICT_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.paths import operations_root
from portia.workflows import (
    SupportWorkflowService,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORT_ID = "spt_issue53_access"
PAUSED_AT = "2026-10-19T09:20:00-04:00"
STALE_ATTEMPT_AT = "2026-10-19T09:25:00-04:00"
AGENT = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)
reference = support_reference(work, SUPPORT_ID)
service = SupportWorkflowService(workspace)


def snapshot(root):
    files = tuple(
        sorted(
            (
                path.relative_to(root).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )
    directories = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_dir()
        )
    )
    return directories, files


def operation_artifacts(root):
    operations = operations_root(root)
    if not operations.exists():
        return ()
    return tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in operations.rglob("*")
            if path.is_file()
        )
    )


original = service.require_current_use(reference)
if original.record.status != "active":
    raise RuntimeError("Support must remain canonically active for stale conflict")
if original.record.field("plan_state") != "active":
    raise RuntimeError("Support plan must be active before stale conflict")

stale_fingerprint = original.fingerprint
original_bytes = original.path.read_bytes()

paused_wire = original.record.to_dict()
paused_wire["plan_state"] = "paused"
paused_wire["updated_at"] = PAUSED_AT
paused_wire["updated_by"] = AGENT
paused_candidate = parse_portia_record("support", "1", paused_wire)

accepted = service.transition_plan_state(
    reference,
    paused_candidate,
    expected=stale_fingerprint,
)
if accepted.record.logical_id != SUPPORT_ID:
    raise RuntimeError("legitimate Support update changed exact identity")
if accepted.record.status != "active":
    raise RuntimeError("legitimate Support update changed canonical lifecycle")
if accepted.record.field("plan_state") != "paused":
    raise RuntimeError("legitimate Support update did not enter paused state")
if accepted.fingerprint == stale_fingerprint:
    raise RuntimeError("legitimate Support update did not change fingerprint")
if accepted.path.read_bytes() == original_bytes:
    raise RuntimeError("legitimate Support update did not change canonical bytes")

accepted_bytes = accepted.path.read_bytes()
accepted_fingerprint = accepted.fingerprint
before_conflict = snapshot(workspace)
operations_before = operation_artifacts(workspace)

stale_wire = accepted.record.to_dict()
stale_wire["plan_state"] = "completed"
stale_wire["updated_at"] = STALE_ATTEMPT_AT
stale_wire["updated_by"] = AGENT
stale_candidate = parse_portia_record("support", "1", stale_wire)

conflict_raised = False
try:
    service.transition_plan_state(
        reference,
        stale_candidate,
        expected=stale_fingerprint,
    )
except PortiaConflictError:
    conflict_raised = True

if not conflict_raised:
    raise RuntimeError("stale Support mutation did not raise PortiaConflictError")

after_conflict = snapshot(workspace)
operations_after = operation_artifacts(workspace)
if after_conflict != before_conflict:
    raise RuntimeError("stale-write conflict caused unintended workspace mutation")
if operations_after != operations_before:
    raise RuntimeError("ordinary stale-write conflict fabricated operation evidence")

current = service.require_current_use(reference)
if current.fingerprint != accepted_fingerprint:
    raise RuntimeError("stale-write conflict changed accepted Support fingerprint")
if current.path.read_bytes() != accepted_bytes:
    raise RuntimeError("stale-write conflict changed accepted canonical bytes")
if current.record.field("plan_state") != "paused":
    raise RuntimeError("stale-write conflict changed accepted Support plan state")
if current.record.status != "active":
    raise RuntimeError("stale-write conflict changed Support lifecycle")

print(
    json.dumps(
        {
            "original_plan_state": original.record.field("plan_state"),
            "accepted_plan_state": accepted.record.field("plan_state"),
            "stale_conflict_raised": conflict_raised,
            "stale_fingerprint_obsolete": stale_fingerprint != accepted_fingerprint,
            "canonical_fingerprint_preserved": (
                current.fingerprint == accepted_fingerprint
            ),
            "canonical_bytes_preserved": current.path.read_bytes() == accepted_bytes,
            "workspace_snapshot_preserved": after_conflict == before_conflict,
            "operation_artifacts_preserved": operations_after == operations_before,
            "support_status": current.record.status,
            "support_plan_state": current.record.field("plan_state"),
            "ordinary_conflict_not_recovery": True,
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

def _judgment_correction_probe(
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
            _JUDGMENT_CORRECTION_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed judgment/correction probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed judgment/correction probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed judgment/correction probe result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "review_current": True,
        "review_completed": True,
        "determination_current": True,
        "determination_outcome": "insufficient_information",
        "classification_count": 0,
        "hypothesis_count": 0,
        "predecessor_status": "superseded",
        "successor_status": "active",
        "successor_distinct": True,
        "exact_supersession": True,
        "technical_history_preserved": True,
        "review_history_pinned": True,
        "determination_history_pinned": True,
        "judgment_fingerprint_stable": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed judgment/correction mismatch for {key}"
            )
    return payload

def _response_communication_probe(
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
            _RESPONSE_COMMUNICATION_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Response/Communication probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Response/Communication probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Response/Communication result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "response_current": True,
        "response_execution_state": "completed",
        "response_review_pinned": True,
        "response_determination_pinned": True,
        "communication_current": True,
        "communication_act_state": "completed",
        "recipient_actor_exact": True,
        "contact_point_exact_current": True,
        "contact_verification_kind": "locally_confirmed",
        "recipient_participation": "not_established",
        "response_relation_exact": True,
        "delivery_not_inferred": True,
        "agreement_not_inferred": True,
        "outcome_count": 0,
        "outcome_not_inferred": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Response/Communication mismatch for {key}"
            )
    return payload

def _support_process_probe(
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
            _SUPPORT_PROCESS_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Support Process probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Support Process probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Support Process result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "support_process_current": True,
        "support_process_status": "active",
        "support_process_workflow_state": "planning",
        "support_process_owner_class": PRIMARY_CLASS_ID,
        "support_process_distinct_from_event": True,
        "response_handoff_exact": True,
        "support_participant_count": 2,
        "supported_student_kind": "roster_student",
        "supported_student_class": SECONDARY_CLASS_ID,
        "supported_student_exact": True,
        "counselor_kind": "actor",
        "counselor_actor_exact": True,
        "need_count": 0,
        "goal_count": 0,
        "support_count": 0,
        "planning_not_inferred": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Support Process mismatch for {key}"
            )
    return payload

def _support_planning_probe(
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
            _SUPPORT_PLANNING_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Support planning probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Support planning probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Support planning result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "need_current": True,
        "goal_current": True,
        "support_current": True,
        "need_target_exact": True,
        "goal_target_exact": True,
        "support_target_exact": True,
        "support_need_exact": True,
        "support_goal_exact": True,
        "support_provider_exact": True,
        "support_plan_state": "active",
        "support_process_status": "active",
        "support_process_workflow_state": "active",
        "support_process_identity_preserved": True,
        "implementation_count": 0,
        "fidelity_count": 0,
        "follow_up_count": 0,
        "outcome_count": 0,
        "downstream_not_inferred": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Support planning mismatch for {key}"
            )
    return payload

def _implementation_fidelity_probe(
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
            _IMPLEMENTATION_FIDELITY_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Implementation/Fidelity probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Implementation/Fidelity probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Implementation/Fidelity result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "implementation_count": 2,
        "implementation_one_current": True,
        "implementation_two_current": True,
        "implementation_identities_distinct": True,
        "implementation_paths_distinct": True,
        "implementation_plan_exact": True,
        "implementation_target_exact": True,
        "implementation_provider_exact": True,
        "fidelity_current": True,
        "fidelity_result": "as_planned",
        "fidelity_scope_exact": True,
        "fidelity_basis_exact": True,
        "support_plan_unchanged": True,
        "support_process_unchanged": True,
        "follow_up_count": 0,
        "outcome_count": 0,
        "effectiveness_not_inferred": True,
        "outcome_not_inferred": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Implementation/Fidelity mismatch for {key}"
            )
    return payload

def _follow_up_attention_probe(
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
            _FOLLOW_UP_ATTENTION_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Follow-Up/attention probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Follow-Up/attention probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Follow-Up/attention result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "follow_up_current": True,
        "follow_up_status": "active",
        "follow_up_workflow_state": "completed",
        "follow_up_planned_at": "2026-10-19T09:00:00-04:00",
        "follow_up_completed_at": "2026-10-19T09:10:00-04:00",
        "follow_up_identity_preserved": True,
        "reviewed_support_exact": True,
        "reviewed_fidelity_exact": True,
        "disposition": "continue_current_support",
        "attention_before_code": "portia_follow_up_due",
        "attention_before_timing": "due",
        "attention_after_count": 0,
        "attention_queries_zero_write": True,
        "outcome_count": 0,
        "support_process_status": "active",
        "support_process_workflow_state": "active",
        "support_process_unchanged": True,
        "support_plan_unchanged": True,
        "fidelity_unchanged": True,
        "outcome_not_inferred": True,
        "process_completion_not_inferred": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Follow-Up/attention mismatch for {key}"
            )
    return payload

def _core_provider_probe(
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
            _CORE_PROVIDER_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core provider probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed Core provider probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed Core provider result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "metadata_provider_count": 1,
        "metadata_group_exact": True,
        "metadata_target_exact": True,
        "diagnostic_code": "provider.valid",
        "diagnostic_profile_validation": "passed",
        "diagnostic_core_compatibility": "passed",
        "profile_module_id": "portia",
        "profile_contract_v1": True,
        "readiness_code": "module_operations.evaluated",
        "readiness_ready": True,
        "attention_code": "module_operations.evaluated",
        "attention_evaluation": "evaluated",
        "provider_zero_write": True,
        "metadata_zero_write": True,
        "diagnostics_zero_write": True,
        "shared_projection_privacy_bounded": True,
        "foreign_class_not_exposed": True,
        "workspace_path_not_exposed": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed Core provider mismatch for {key}"
            )

    summary_count = payload.get("attention_summary_count")
    if (
        not isinstance(summary_count, int)
        or isinstance(summary_count, bool)
        or summary_count < 0
    ):
        raise Issue53AcceptanceError(
            "Issue #53 installed Core attention summary count is invalid"
        )
    return payload

def _stale_conflict_probe(
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
            _STALE_CONFLICT_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed stale-conflict probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed stale-conflict probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed stale-conflict result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "original_plan_state": "active",
        "accepted_plan_state": "paused",
        "stale_conflict_raised": True,
        "stale_fingerprint_obsolete": True,
        "canonical_fingerprint_preserved": True,
        "canonical_bytes_preserved": True,
        "workspace_snapshot_preserved": True,
        "operation_artifacts_preserved": True,
        "support_status": "active",
        "support_plan_state": "paused",
        "ordinary_conflict_not_recovery": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed stale-conflict mismatch for {key}"
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
        judgment_correction = _judgment_correction_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        response_communication = _response_communication_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        support_process = _support_process_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        support_planning = _support_planning_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        implementation_fidelity = _implementation_fidelity_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        follow_up_attention = _follow_up_attention_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        core_provider = _core_provider_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        stale_conflict = _stale_conflict_probe(
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
        print("PASS bounded judgment")
        print("PASS correction history")
        print("PASS Response")
        print("PASS Communication")
        print("PASS Support Process")
        print("PASS Support planning")
        print("PASS Implementation history")
        print("PASS Fidelity")
        print("PASS Follow-Up")
        print("PASS attention transition")
        print("PASS provider boundary")
        print("PASS conflict")

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
            "review_current": judgment_correction["review_current"],
            "determination_current": judgment_correction["determination_current"],
            "determination_outcome": judgment_correction[
                "determination_outcome"
            ],
            "predecessor_status": judgment_correction["predecessor_status"],
            "successor_status": judgment_correction["successor_status"],
            "technical_history_preserved": judgment_correction[
                "technical_history_preserved"
            ],
            "review_history_pinned": judgment_correction[
                "review_history_pinned"
            ],
            "determination_history_pinned": judgment_correction[
                "determination_history_pinned"
            ],
            "response_current": response_communication["response_current"],
            "response_review_pinned": response_communication[
                "response_review_pinned"
            ],
            "response_determination_pinned": response_communication[
                "response_determination_pinned"
            ],
            "communication_current": response_communication[
                "communication_current"
            ],
            "recipient_participation": response_communication[
                "recipient_participation"
            ],
            "delivery_not_inferred": response_communication[
                "delivery_not_inferred"
            ],
            "agreement_not_inferred": response_communication[
                "agreement_not_inferred"
            ],
            "outcome_not_inferred": response_communication[
                "outcome_not_inferred"
            ],
            "support_process_current": support_process[
                "support_process_current"
            ],
            "support_process_workflow_state": support_process[
                "support_process_workflow_state"
            ],
            "response_handoff_exact": support_process[
                "response_handoff_exact"
            ],
            "support_participant_count": support_process[
                "support_participant_count"
            ],
            "supported_student_exact": support_process[
                "supported_student_exact"
            ],
            "counselor_actor_exact": support_process[
                "counselor_actor_exact"
            ],
            "planning_not_inferred": support_process[
                "planning_not_inferred"
            ],
            "need_current": support_planning["need_current"],
            "goal_current": support_planning["goal_current"],
            "support_current": support_planning["support_current"],
            "support_plan_state": support_planning["support_plan_state"],
            "support_process_active_workflow": support_planning[
                "support_process_workflow_state"
            ],
            "support_provider_exact": support_planning[
                "support_provider_exact"
            ],
            "downstream_not_inferred": support_planning[
                "downstream_not_inferred"
            ],
            "implementation_count": implementation_fidelity[
                "implementation_count"
            ],
            "implementation_identities_distinct": implementation_fidelity[
                "implementation_identities_distinct"
            ],
            "fidelity_current": implementation_fidelity["fidelity_current"],
            "fidelity_result": implementation_fidelity["fidelity_result"],
            "fidelity_scope_exact": implementation_fidelity[
                "fidelity_scope_exact"
            ],
            "support_plan_unchanged": implementation_fidelity[
                "support_plan_unchanged"
            ],
            "effectiveness_not_inferred": implementation_fidelity[
                "effectiveness_not_inferred"
            ],
            "fidelity_outcome_not_inferred": implementation_fidelity[
                "outcome_not_inferred"
            ],
            "follow_up_workflow_state": follow_up_attention[
                "follow_up_workflow_state"
            ],
            "follow_up_identity_preserved": follow_up_attention[
                "follow_up_identity_preserved"
            ],
            "follow_up_disposition": follow_up_attention["disposition"],
            "attention_before_code": follow_up_attention[
                "attention_before_code"
            ],
            "attention_after_count": follow_up_attention[
                "attention_after_count"
            ],
            "attention_queries_zero_write": follow_up_attention[
                "attention_queries_zero_write"
            ],
            "follow_up_outcome_not_inferred": follow_up_attention[
                "outcome_not_inferred"
            ],
            "process_completion_not_inferred": follow_up_attention[
                "process_completion_not_inferred"
            ],
            "provider_metadata_target_exact": core_provider[
                "metadata_target_exact"
            ],
            "provider_diagnostic_code": core_provider["diagnostic_code"],
            "provider_readiness_ready": core_provider["readiness_ready"],
            "provider_attention_evaluation": core_provider[
                "attention_evaluation"
            ],
            "provider_attention_summary_count": core_provider[
                "attention_summary_count"
            ],
            "provider_zero_write": core_provider["provider_zero_write"],
            "shared_projection_privacy_bounded": core_provider[
                "shared_projection_privacy_bounded"
            ],
            "foreign_class_not_exposed": core_provider[
                "foreign_class_not_exposed"
            ],
            "workspace_path_not_exposed": core_provider[
                "workspace_path_not_exposed"
            ],
            "stale_conflict_raised": stale_conflict[
                "stale_conflict_raised"
            ],
            "conflict_canonical_bytes_preserved": stale_conflict[
                "canonical_bytes_preserved"
            ],
            "conflict_workspace_snapshot_preserved": stale_conflict[
                "workspace_snapshot_preserved"
            ],
            "conflict_operation_artifacts_preserved": stale_conflict[
                "operation_artifacts_preserved"
            ],
            "support_plan_state_after_conflict": stale_conflict[
                "support_plan_state"
            ],
            "ordinary_conflict_not_recovery": stale_conflict[
                "ordinary_conflict_not_recovery"
            ],
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
