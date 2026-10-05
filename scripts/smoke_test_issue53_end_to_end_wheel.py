"""Establish isolated installed-wheel acceptance foundations for Issue #53.

Slice 1 owns the exact-artifact, environment-isolation, and deep-workspace
boundary. Later Issue #53 slices extend the installed probe with the continuous
production-service story while preserving this single environment and workspace.
"""

from __future__ import annotations

import argparse
import ast
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
RECOVERED_SUPPORT_ID: Final[str] = "spt_issue53_access_corrected"
RECOVERY_TRANSITION_ID: Final[str] = "lct_issue53_support_corrected"
RECOVERY_OPERATION_ID: Final[str] = "op_issue53_support_recovery"
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

_RECOVERY_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.paths import (
    resolve_workspace_relative,
    work_storage_history_path,
)
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    IntegrityWorkflowService,
    RecoveryWorkflowService,
    SupportWorkflowService,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORT_ID = "spt_issue53_access"
CORRECTED_SUPPORT_ID = "spt_issue53_access_corrected"
TRANSITION_ID = "lct_issue53_support_corrected"
OPERATION_ID = "op_issue53_support_recovery"
CORRECTED_AT = "2026-10-19T09:30:00-04:00"
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
predecessor_ref = support_reference(work, SUPPORT_ID)
successor_ref = support_reference(work, CORRECTED_SUPPORT_ID)
service = SupportWorkflowService(workspace)
journals = OperationJournalStore(workspace)
recovery = RecoveryWorkflowService(workspace)
integrity = IntegrityWorkflowService(workspace)


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


predecessor = service.require_current_use(predecessor_ref)
if predecessor.record.status != "active":
    raise RuntimeError("recovery predecessor must be canonically active")
if predecessor.record.field("plan_state") != "paused":
    raise RuntimeError("recovery predecessor must retain Part K paused plan state")

predecessor_bytes_before = predecessor.path.read_bytes()
predecessor_fingerprint_before = predecessor.fingerprint

successor_wire = predecessor.record.to_dict()
successor_wire["support_id"] = CORRECTED_SUPPORT_ID
strategy = dict(successor_wire["strategy"])
strategy["procedure"] = (
    "At the start of independent work, make the designated lower-distraction "
    "location available and state once that the participant may choose it."
)
successor_wire["strategy"] = strategy
successor_wire["supersedes"] = [
    {
        "work_record_ref": predecessor_ref.to_dict(),
        "reason": "strategy_corrected",
        "detail": "Corrected the recorded wording of the planned reminder.",
    }
]
successor_wire["created_at"] = CORRECTED_AT
successor_wire["created_by"] = AGENT
successor_wire["updated_at"] = CORRECTED_AT
successor_wire["updated_by"] = AGENT
successor = parse_portia_record("support", "1", successor_wire)

fault_checkpoints = []


def fail_after_successor(checkpoint, step_id):
    fault_checkpoints.append((checkpoint, step_id))
    if checkpoint == "after_publish" and step_id == "step_successor":
        raise RuntimeError("synthetic Issue #53 recovery crash boundary")


partial_error = None
try:
    service.correct(
        predecessor_ref,
        successor,
        expected=predecessor.fingerprint,
        transition_id=TRANSITION_ID,
        operation_id=OPERATION_ID,
        fault_hook=fail_after_successor,
    )
except PortiaOperationPartialCommitError as exc:
    partial_error = exc

if partial_error is None:
    raise RuntimeError("coordinated Support correction did not partially commit")
if partial_error.operation_id != OPERATION_ID:
    raise RuntimeError("partial-commit error lost exact operation identity")
if partial_error.accepted_steps != ("step_history", "step_successor"):
    raise RuntimeError("partial-commit boundary accepted unexpected canonical steps")

partial_current = journals.load_current(OPERATION_ID)
partial_data = partial_current.revision.to_dict()
if partial_data.get("state") != "recovering":
    raise RuntimeError("partial operation was not journaled as recovering")
if partial_data.get("operation_id") != OPERATION_ID:
    raise RuntimeError("recovering journal lost operation identity")

partial_state = partial_data.get("partial_state")
if not isinstance(partial_state, dict):
    raise RuntimeError("recovering journal has malformed partial state")
if partial_state.get("durability_assessment") != "confirmed":
    raise RuntimeError("recovering journal did not confirm durable partial state")
if partial_state.get("accepted_steps") != ["step_history", "step_successor"]:
    raise RuntimeError("recovering journal accepted-step evidence changed")
if partial_state.get("remaining_canonical_steps") != [
    "step_transition",
    "step_action",
]:
    raise RuntimeError("recovering journal remaining-step evidence changed")
if partial_state.get("recommended_disposition") != "resume":
    raise RuntimeError("recovering journal did not recommend bounded resume")

write_set = partial_data.get("write_set")
if not isinstance(write_set, list):
    raise RuntimeError("recovering journal write set is malformed")
steps = {
    step.get("step_id"): step
    for step in write_set
    if isinstance(step, dict) and isinstance(step.get("step_id"), str)
}
if tuple(steps) != (
    "step_history",
    "step_successor",
    "step_transition",
    "step_action",
):
    raise RuntimeError("Support correction write-set topology changed")

for step_id in ("step_history", "step_successor"):
    if steps[step_id].get("disposition") != "accepted":
        raise RuntimeError("durable partial step lost accepted disposition")
for step_id in ("step_transition", "step_action"):
    if steps[step_id].get("disposition") != "staged":
        raise RuntimeError("remaining recovery step lost staged disposition")

history_path = work_storage_history_path(
    workspace,
    work,
    "support",
    SUPPORT_ID,
    predecessor_fingerprint_before.digest,
)
if history_path.read_bytes() != predecessor_bytes_before:
    raise RuntimeError("accepted technical history bytes changed at interruption")

successor_partial = service.load_exact(successor_ref)
successor_bytes_before_recovery = successor_partial.path.read_bytes()
successor_mtime_before_recovery = successor_partial.path.stat().st_mtime_ns
if successor_partial.record.to_dict() != successor.to_dict():
    raise RuntimeError("accepted successor bytes do not match correction intent")

predecessor_partial = service.load_exact(predecessor_ref)
if predecessor_partial.fingerprint != predecessor_fingerprint_before:
    raise RuntimeError("predecessor changed before recovery")
if predecessor_partial.path.read_bytes() != predecessor_bytes_before:
    raise RuntimeError("predecessor canonical bytes changed before recovery")
if predecessor_partial.record.status != "active":
    raise RuntimeError("predecessor was superseded before recovery")

transition_step = steps["step_transition"]
transition_destination = transition_step.get("destination_path")
if not isinstance(transition_destination, str):
    raise RuntimeError("transition step destination is malformed")
transition_path = resolve_workspace_relative(workspace, transition_destination)
if transition_path.exists():
    raise RuntimeError("lifecycle transition was published before recovery")

staged_entries = partial_data.get("staged_artifacts")
if not isinstance(staged_entries, list) or len(staged_entries) != 4:
    raise RuntimeError("recovering journal did not retain exact staged set")
staged_paths = []
for entry in staged_entries:
    if not isinstance(entry, dict):
        raise RuntimeError("recovering staged evidence is malformed")
    relative = entry.get("staging_path")
    if not isinstance(relative, str):
        raise RuntimeError("recovering staging path is malformed")
    path = resolve_workspace_relative(workspace, relative)
    if not path.is_file():
        raise RuntimeError("recovering staged candidate is missing")
    staged_paths.append(path)

lock_set = partial_data.get("lock_set")
if not isinstance(lock_set, list):
    raise RuntimeError("recovering lock set is malformed")
held_lock_paths = []
for entry in lock_set:
    if not isinstance(entry, dict):
        raise RuntimeError("recovering lock evidence is malformed")
    if entry.get("disposition") != "acquired":
        raise RuntimeError("partial operation did not retain exact held locks")
    relative = entry.get("lock_path")
    if not isinstance(relative, str):
        raise RuntimeError("recovering lock path is malformed")
    path = resolve_workspace_relative(workspace, relative)
    if not path.is_file():
        raise RuntimeError("journaled held lock is not durable")
    held_lock_paths.append(path)

assessment = recovery.assess(OPERATION_ID)
if assessment.state != "recovering":
    raise RuntimeError("RecoveryWorkflowService did not observe recovering state")
if assessment.disposition != "resume":
    raise RuntimeError("RecoveryWorkflowService did not select resume")
if assessment.findings:
    raise RuntimeError("recovering operation has unexpected blocking findings")
evidence = {item.step_id: item for item in assessment.step_evidence}
if set(evidence) != set(steps):
    raise RuntimeError("recovery assessment lost exact write-step identities")
if evidence["step_history"].disposition != "accepted":
    raise RuntimeError("recovery did not recognize accepted history")
if evidence["step_successor"].disposition != "accepted":
    raise RuntimeError("recovery did not recognize accepted successor")
if evidence["step_transition"].disposition != "not_written":
    raise RuntimeError("recovery did not recognize missing transition")
if evidence["step_action"].disposition != "not_written":
    raise RuntimeError("recovery did not recognize unsuperseded predecessor")

pre_integrity_evaluation = integrity.evaluate_operation_persistence(OPERATION_ID)
if pre_integrity_evaluation.findings:
    raise RuntimeError("recovering operation has unexpected Integrity findings")

integrity_scope = integrity.operation_scope(OPERATION_ID)
pre_integrity_projection = integrity.project_operation_persistence_findings(
    OPERATION_ID
)
if pre_integrity_projection.findings:
    raise RuntimeError("recovering operation projected unexpected public findings")
if integrity.current_findings(integrity_scope) != ():
    raise RuntimeError("recovering operation current Integrity projection is not clean")
pre_generation_id = pre_integrity_projection.generation.metadata.to_dict().get(
    "generation_id"
)
if not isinstance(pre_generation_id, str):
    raise RuntimeError("recovering Integrity projection lost generation identity")

pre_integrity_serialized = json.dumps(
    {
        "findings": [
            finding.to_dict()
            for finding in pre_integrity_projection.findings
        ],
        "metadata": pre_integrity_projection.generation.metadata.to_dict(),
    },
    sort_keys=True,
    default=str,
)
for prohibited in (
    "Shared Synthetic",
    "Synthetic Counselor",
    "guardian.issue53@example.invalid",
    "Synthetic classroom material-location discrepancy.",
    "blue marker",
):
    if prohibited in pre_integrity_serialized:
        raise RuntimeError(
            "recovering Integrity diagnostics leaked private narrative/contact data"
        )

accepted_before_recovery = {
    "step_history": history_path.read_bytes(),
    "step_successor": successor_partial.path.read_bytes(),
}

recovered = recovery.resume_incomplete(
    OPERATION_ID,
    expected_pointer=partial_current.pointer_fingerprint,
)
if recovered.state != "completed":
    raise RuntimeError("recovery did not reach completed journal state")
if recovered.disposition != "terminal_consistent":
    raise RuntimeError("recovery did not become terminal-consistent")
if recovered.findings:
    raise RuntimeError("completed recovery retained unexpected findings")
if any(item.disposition != "accepted" for item in recovered.step_evidence):
    raise RuntimeError("completed recovery did not prove every canonical step")

if history_path.read_bytes() != accepted_before_recovery["step_history"]:
    raise RuntimeError("recovery replayed or rewrote already accepted history")
successor_after_recovery = service.require_current_use(successor_ref)
if successor_after_recovery.path.read_bytes() != accepted_before_recovery["step_successor"]:
    raise RuntimeError("recovery replayed or rewrote already accepted successor")
if successor_after_recovery.path.stat().st_mtime_ns != successor_mtime_before_recovery:
    raise RuntimeError("accepted successor was republished during recovery")

predecessor_after = service.load_exact(predecessor_ref)
if predecessor_after.record.status != "superseded":
    raise RuntimeError("recovery did not supersede exact predecessor")
if predecessor_after.record.field("plan_state") != "paused":
    raise RuntimeError("recovery changed paused Support plan state")
if not transition_path.is_file():
    raise RuntimeError("recovery did not publish exact lifecycle transition")
transition = service.repository.load_work_record(
    work,
    "lifecycle_transition",
    "1",
    TRANSITION_ID,
)
if transition.record.field("to_status") != "superseded":
    raise RuntimeError("recovered lifecycle transition has wrong terminal status")

for step_id, raw in steps.items():
    destination = raw.get("destination_path")
    intended_raw = raw.get("intended_result")
    if not isinstance(destination, str) or not isinstance(intended_raw, dict):
        raise RuntimeError("recovering write step lost deterministic intent")
    expected = ContentFingerprint.from_dict(intended_raw.get("fingerprint"))
    path = resolve_workspace_relative(workspace, destination)
    actual = fingerprint_bytes(path.read_bytes())
    if actual != expected:
        raise RuntimeError(
            "recovery final canonical bytes disagree with journaled exact intent"
        )

if any(path.exists() for path in held_lock_paths):
    raise RuntimeError("recovery did not release exact held locks")
if any(path.exists() for path in staged_paths):
    raise RuntimeError("recovery did not clean operation-owned staging")

terminal_current = journals.load_current(OPERATION_ID)
terminal_data = terminal_current.revision.to_dict()
if terminal_data.get("state") != "completed":
    raise RuntimeError("operation current pointer does not select completed journal")
terminal_partial = terminal_data.get("partial_state")
if not isinstance(terminal_partial, dict):
    raise RuntimeError("terminal recovery partial state is malformed")
if terminal_partial.get("remaining_canonical_steps") != []:
    raise RuntimeError("terminal recovery still reports canonical work")
if terminal_partial.get("held_or_possible_locks") != []:
    raise RuntimeError("terminal recovery still reports held locks")
if terminal_data.get("staged_artifacts") != []:
    raise RuntimeError("terminal recovery still reports staging")

stale_projection_rejected = False
try:
    integrity.current_findings(integrity_scope)
except PortiaRecoveryRequiredError:
    stale_projection_rejected = True

if not stale_projection_rejected:
    raise RuntimeError(
        "pre-recovery Integrity projection remained falsely fresh after recovery"
    )

post_integrity_evaluation = integrity.evaluate_operation_persistence(OPERATION_ID)
if post_integrity_evaluation.findings:
    raise RuntimeError("completed operation has unexpected Integrity findings")

post_integrity_projection = integrity.project_operation_persistence_findings(
    OPERATION_ID
)
if post_integrity_projection.findings:
    raise RuntimeError("completed operation projected unexpected public findings")
if integrity.current_findings(integrity_scope) != ():
    raise RuntimeError("completed operation current Integrity projection is not clean")
post_generation_id = post_integrity_projection.generation.metadata.to_dict().get(
    "generation_id"
)
if not isinstance(post_generation_id, str):
    raise RuntimeError("completed Integrity projection lost generation identity")
if post_generation_id == pre_generation_id:
    raise RuntimeError("Integrity projection did not advance with recovered source state")

integrity.require_operation_completion(OPERATION_ID)

post_integrity_serialized = json.dumps(
    {
        "findings": [
            finding.to_dict()
            for finding in post_integrity_projection.findings
        ],
        "metadata": post_integrity_projection.generation.metadata.to_dict(),
    },
    sort_keys=True,
    default=str,
)
for prohibited in (
    "Shared Synthetic",
    "Synthetic Counselor",
    "guardian.issue53@example.invalid",
    "Synthetic classroom material-location discrepancy.",
    "blue marker",
):
    if prohibited in post_integrity_serialized:
        raise RuntimeError(
            "completed Integrity diagnostics leaked private narrative/contact data"
        )

before_idempotent_recovery = snapshot(workspace)
repeated = recovery.resume_incomplete(
    OPERATION_ID,
    expected_pointer=terminal_current.pointer_fingerprint,
)
after_idempotent_recovery = snapshot(workspace)
if repeated.disposition != "terminal_consistent":
    raise RuntimeError("repeated recovery did not remain terminal-consistent")
if before_idempotent_recovery != after_idempotent_recovery:
    raise RuntimeError("repeated terminal recovery mutated durable state")

print(
    json.dumps(
        {
            "partial_error_exact": True,
            "partial_accepted_steps": list(partial_error.accepted_steps),
            "partial_state": partial_data.get("state"),
            "partial_disposition": assessment.disposition,
            "partial_findings_count": len(assessment.findings),
            "accepted_history_preserved": (
                history_path.read_bytes()
                == accepted_before_recovery["step_history"]
            ),
            "accepted_successor_preserved": (
                successor_after_recovery.path.read_bytes()
                == accepted_before_recovery["step_successor"]
            ),
            "accepted_successor_not_republished": (
                successor_after_recovery.path.stat().st_mtime_ns
                == successor_mtime_before_recovery
            ),
            "predecessor_superseded": predecessor_after.record.status
            == "superseded",
            "successor_current": successor_after_recovery.record.status == "active",
            "successor_plan_state": successor_after_recovery.record.field(
                "plan_state"
            ),
            "transition_published": transition_path.is_file(),
            "terminal_state": terminal_data.get("state"),
            "terminal_disposition": recovered.disposition,
            "terminal_findings_count": len(recovered.findings),
            "locks_released": not any(path.exists() for path in held_lock_paths),
            "staging_cleaned": not any(path.exists() for path in staged_paths),
            "remaining_steps_empty": (
                terminal_partial.get("remaining_canonical_steps") == []
            ),
            "recovery_idempotent": (
                before_idempotent_recovery == after_idempotent_recovery
            ),
            "ordinary_conflict_distinct": True,
            "integrity_pre_findings_count": len(
                pre_integrity_evaluation.findings
            ),
            "integrity_pre_projection_clean": (
                pre_integrity_projection.findings == ()
            ),
            "integrity_stale_projection_rejected": stale_projection_rejected,
            "integrity_post_findings_count": len(
                post_integrity_evaluation.findings
            ),
            "integrity_post_projection_clean": (
                post_integrity_projection.findings == ()
            ),
            "integrity_generation_advanced": (
                post_generation_id != pre_generation_id
            ),
            "integrity_operation_completion_allowed": True,
            "integrity_privacy_bounded": True,
        },
        sort_keys=True,
    )
)
"""

_DURABLE_RELOAD_PROBE = r"""
import json
import sys
from datetime import date
from pathlib import Path

from pds_core.classes import load_class_roster

from portia.identity import ActorDirectoryService
from portia.models.references import (
    ExactActorRef,
    ExactActorStudentRelationshipRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes
from portia.storage.paths import resolve_workspace_relative
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.storage.staging import staging_path_for
from portia.workflows import (
    AccountWorkflowService,
    CommunicationWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    RecoveryWorkflowService,
    ResponseWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    account_reference,
    communication_reference,
    fidelity_reference,
    follow_up_reference,
    implementation_reference,
    participant_reference,
    response_reference,
    support_reference,
)

SCHOOL_YEAR = "2026-2027"
PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
GUARDIAN_ACTOR_ID = "actr_guardian_001"
COUNSELOR_ACTOR_ID = "actr_counselor_001"
EVENT_ID = "evt_issue53_primary"
CROSS_PARTICIPANT_ID = "ep_issue53_cross"
ACCOUNT_ID = "acct_issue53_cross_report"
CORRECTED_ACCOUNT_ID = "acct_issue53_cross_corrected"
REVIEW_ID = "rvw_issue53_evidence"
DETERMINATION_ID = "det_issue53_insufficient"
RESPONSE_ID = "rsp_issue53_neutral_support"
COMMUNICATION_ID = "comm_issue53_guardian"
SUPPORT_PROCESS_ID = "sup_issue53_support"
SUPPORT_ID = "spt_issue53_access"
CORRECTED_SUPPORT_ID = "spt_issue53_access_corrected"
IMPLEMENTATION_ONE_ID = "imp_issue53_access_001"
IMPLEMENTATION_TWO_ID = "imp_issue53_access_002"
FIDELITY_ID = "fid_issue53_access"
FOLLOW_UP_ID = "fup_issue53_review"
ACCOUNT_CORRECTION_OPERATION_ID = "op_issue53_account_corrected"
RECOVERY_OPERATION_ID = "op_issue53_support_recovery"
AS_OF = date(2026, 10, 4)

workspace = Path(sys.argv[1]).resolve()

# This process is intentionally started after every writer/recovery probe has
# exited. Instantiate all repositories/services fresh from the durable root.
repository = PortiaRepository(workspace)
actors = ActorDirectoryService(workspace)
events = EventWorkflowService(workspace)
participants = ParticipantWorkflowService(workspace)
accounts = AccountWorkflowService(workspace)
responses = ResponseWorkflowService(workspace)
communications = CommunicationWorkflowService(workspace)
support_roots = SupportProcessWorkflowService(workspace)
supports = SupportWorkflowService(workspace)
journals = OperationJournalStore(workspace)
recovery = RecoveryWorkflowService(workspace)

primary_roster = load_class_roster(workspace, PRIMARY_CLASS_ID)
secondary_roster = load_class_roster(workspace, SECONDARY_CLASS_ID)
primary_ids = {student.student_id for student in primary_roster.students}
secondary_ids = {student.student_id for student in secondary_roster.students}
if COLLISION_STUDENT_ID not in primary_ids:
    raise RuntimeError("fresh process lost focal student from primary Core roster")
if COLLISION_STUDENT_ID not in secondary_ids:
    raise RuntimeError("fresh process lost focal student from secondary Core roster")
if primary_roster.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("fresh process loaded primary roster under wrong class")
if secondary_roster.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("fresh process loaded secondary roster under wrong class")

guardian = actors.load_actor(
    ExactActorRef(actor_id=GUARDIAN_ACTOR_ID, contract_version="1"),
    require_current_use=True,
)
counselor = actors.load_actor(
    ExactActorRef(actor_id=COUNSELOR_ACTOR_ID, contract_version="1"),
    require_current_use=True,
)
for stored in (guardian, counselor):
    relative = stored.path.resolve().relative_to(workspace)
    if relative.parts[:2] != ("portia", "actors"):
        raise RuntimeError("fresh Actor reload escaped workspace Actor Directory")
    if PRIMARY_CLASS_ID in relative.parts or SECONDARY_CLASS_ID in relative.parts:
        raise RuntimeError("fresh Actor reload became class-owned")

guardian_primary = actors.resolve_student_relationship(
    ExactActorStudentRelationshipRef(
        actor_id=GUARDIAN_ACTOR_ID,
        relationship_id="asrel_guardian_primary",
        contract_version="1",
    ),
    require_current_use=True,
    on_date=AS_OF,
)
guardian_secondary = actors.resolve_student_relationship(
    ExactActorStudentRelationshipRef(
        actor_id=GUARDIAN_ACTOR_ID,
        relationship_id="asrel_guardian_secondary",
        contract_version="1",
    ),
    require_current_use=True,
    on_date=AS_OF,
)
if guardian_primary.roster_student.reference.class_id != PRIMARY_CLASS_ID:
    raise RuntimeError("fresh primary Actor relationship lost exact Core class")
if guardian_secondary.roster_student.reference.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("fresh secondary Actor relationship lost exact Core class")
if (
    guardian_primary.roster_student.reference.student_id
    != COLLISION_STUDENT_ID
    or guardian_secondary.roster_student.reference.student_id
    != COLLISION_STUDENT_ID
):
    raise RuntimeError("fresh Actor relationship lost focal local student identity")
if (
    guardian_primary.roster_student.reference
    == guardian_secondary.roster_student.reference
):
    raise RuntimeError("fresh Actor reload collapsed class-qualified students")

event_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
event = events.require_current_use(event_work)
if event.record.status != "active":
    raise RuntimeError("fresh Event reload is not current")

cross_participant = participants.resolve_exact(
    participant_reference(event_work, CROSS_PARTICIPANT_ID)
)
if cross_participant.kind != "roster_student":
    raise RuntimeError("fresh cross-class Participant lost roster-student identity")
cross_authority = cross_participant.authority
if cross_authority is None:
    raise RuntimeError("fresh cross-class Participant lost roster authority")
if cross_authority.reference.class_id != SECONDARY_CLASS_ID:
    raise RuntimeError("fresh cross-class Participant resolved wrong Core class")
if cross_authority.reference.student_id != COLLISION_STUDENT_ID:
    raise RuntimeError("fresh cross-class Participant resolved wrong local student")

original_account_ref = account_reference(event_work, ACCOUNT_ID)
corrected_account_ref = account_reference(event_work, CORRECTED_ACCOUNT_ID)
original_account = accounts.load_exact(original_account_ref)
corrected_account = accounts.require_current_use(corrected_account_ref)
if original_account.record.status != "superseded":
    raise RuntimeError("fresh exact Account predecessor is not superseded")
if corrected_account.record.status != "active":
    raise RuntimeError("fresh corrected Account successor is not current")

review = repository.load_work_record(
    event_work,
    "review",
    "1",
    REVIEW_ID,
)
determination = repository.load_work_record(
    event_work,
    "determination",
    "1",
    DETERMINATION_ID,
)
review_evidence = review.record.to_dict().get("evidence_considered")
if not isinstance(review_evidence, list):
    raise RuntimeError("fresh Review evidence is malformed")
review_account_ids = [
    item["work_record_ref"]["record_ref"]["record_id"]
    for item in review_evidence
    if isinstance(item, dict)
    and item.get("kind") == "portia_record"
    and isinstance(item.get("work_record_ref"), dict)
    and isinstance(item["work_record_ref"].get("record_ref"), dict)
    and item["work_record_ref"]["record_ref"].get("record_kind") == "account"
]
if review_account_ids != [ACCOUNT_ID]:
    raise RuntimeError("fresh Review silently retargeted corrected Account")

determination_basis = determination.record.to_dict().get("basis")
if not isinstance(determination_basis, list):
    raise RuntimeError("fresh Determination basis is malformed")
determination_account_ids = [
    item["evidence_ref"]["work_record_ref"]["record_ref"]["record_id"]
    for item in determination_basis
    if isinstance(item, dict)
    and isinstance(item.get("evidence_ref"), dict)
    and item["evidence_ref"].get("kind") == "portia_record"
    and isinstance(item["evidence_ref"].get("work_record_ref"), dict)
    and isinstance(
        item["evidence_ref"]["work_record_ref"].get("record_ref"),
        dict,
    )
    and item["evidence_ref"]["work_record_ref"]["record_ref"].get(
        "record_kind"
    )
    == "account"
]
if determination_account_ids != [ACCOUNT_ID]:
    raise RuntimeError("fresh Determination silently retargeted corrected Account")

response = responses.require_current_use(response_reference(event_work, RESPONSE_ID))
communication = communications.require_current_use(
    communication_reference(event_work, COMMUNICATION_ID)
)
if response.record.field("execution_state") != "completed":
    raise RuntimeError("fresh Response reload lost completed execution state")
if communication.record.field("act_state") != "completed":
    raise RuntimeError("fresh Communication reload lost completed act state")

support_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)
support_process = support_roots.require_current_use(support_work)
if support_process.record.status != "active":
    raise RuntimeError("fresh Support Process reload is not current")
if support_process.record.field("workflow_state") != "active":
    raise RuntimeError("fresh Support Process workflow state changed")

original_support = supports.load_exact(support_reference(support_work, SUPPORT_ID))
corrected_support = supports.require_current_use(
    support_reference(support_work, CORRECTED_SUPPORT_ID)
)
if original_support.record.status != "superseded":
    raise RuntimeError("fresh recovered Support predecessor is not superseded")
if corrected_support.record.status != "active":
    raise RuntimeError("fresh recovered Support successor is not current")
if corrected_support.record.field("plan_state") != "paused":
    raise RuntimeError("fresh recovered Support successor lost paused plan state")

implementation_records = repository.list_work_records(
    support_work,
    "implementation",
    version="1",
)
implementation_ids = {
    stored.record.logical_id for stored in implementation_records
}
if implementation_ids != {
    IMPLEMENTATION_ONE_ID,
    IMPLEMENTATION_TWO_ID,
}:
    raise RuntimeError("fresh Implementation set changed after restart")
implementation_one = repository.load_work_record(
    support_work,
    "implementation",
    "1",
    IMPLEMENTATION_ONE_ID,
)
implementation_two = repository.load_work_record(
    support_work,
    "implementation",
    "1",
    IMPLEMENTATION_TWO_ID,
)
fidelity = repository.load_work_record(
    support_work,
    "fidelity",
    "1",
    FIDELITY_ID,
)
follow_up = repository.load_work_record(
    support_work,
    "follow_up",
    "1",
    FOLLOW_UP_ID,
)
if implementation_one.record.field("execution_state") != "completed":
    raise RuntimeError("fresh Implementation one reload lost completed state")
if implementation_two.record.field("execution_state") != "completed":
    raise RuntimeError("fresh Implementation two reload lost completed state")
if fidelity.record.field("result") != "as_planned":
    raise RuntimeError("fresh Fidelity reload lost bounded result")
if follow_up.record.field("workflow_state") != "completed":
    raise RuntimeError("fresh Follow-Up reload lost completed workflow state")
if follow_up.record.field("disposition") != "continue_current_support":
    raise RuntimeError("fresh Follow-Up reload lost explicit disposition")

terminal = journals.load_current(RECOVERY_OPERATION_ID)
terminal_data = terminal.revision.to_dict()
if terminal_data.get("state") != "completed":
    raise RuntimeError("fresh recovery journal reload is not terminal")
terminal_assessment = recovery.assess(RECOVERY_OPERATION_ID)
if terminal_assessment.disposition != "terminal_consistent":
    raise RuntimeError("fresh recovery assessment is not terminal-consistent")
if terminal_assessment.findings:
    raise RuntimeError("fresh recovery assessment retained blocking findings")

write_set = terminal_data.get("write_set")
if not isinstance(write_set, list):
    raise RuntimeError("fresh recovery journal write set is malformed")
for step in write_set:
    if not isinstance(step, dict):
        raise RuntimeError("fresh recovery journal step is malformed")
    step_id = step.get("step_id")
    destination = step.get("destination_path")
    if not isinstance(step_id, str) or not isinstance(destination, str):
        raise RuntimeError("fresh recovery step identity is malformed")
    staging = staging_path_for(
        workspace,
        RECOVERY_OPERATION_ID,
        step_id,
        destination,
    )
    if staging.exists() or staging.is_symlink():
        raise RuntimeError("fresh process found retained recovery staging")

def verify_technical_history(operation_id):
    current = journals.load_current(operation_id)
    data = current.revision.to_dict()
    if data.get("state") != "completed":
        raise RuntimeError("technical-history source operation is not completed")
    steps = data.get("write_set")
    if not isinstance(steps, list):
        raise RuntimeError("technical-history source write set is malformed")
    history_steps = [
        step
        for step in steps
        if isinstance(step, dict) and step.get("step_id") == "step_history"
    ]
    if len(history_steps) != 1:
        raise RuntimeError("technical-history source did not retain one history step")
    step = history_steps[0]
    destination = step.get("destination_path")
    intended = step.get("intended_result")
    if not isinstance(destination, str) or not isinstance(intended, dict):
        raise RuntimeError("technical-history step identity is malformed")
    expected = ContentFingerprint.from_dict(intended.get("fingerprint"))
    path = resolve_workspace_relative(workspace, destination)
    content = read_bytes(path)
    if fingerprint_bytes(content) != expected:
        raise RuntimeError("technical storage history bytes changed after restart")
    return path.relative_to(workspace).as_posix()

account_history_path = verify_technical_history(
    ACCOUNT_CORRECTION_OPERATION_ID
)
support_history_path = verify_technical_history(RECOVERY_OPERATION_ID)

print(
    json.dumps(
        {
            "core_rosters_readable": True,
            "actor_directory_reloaded": True,
            "actor_relationships_class_qualified": True,
            "event_current": True,
            "cross_participant_class": cross_authority.reference.class_id,
            "account_predecessor_exact": original_account.record.status
            == "superseded",
            "account_successor_current": corrected_account.record.status
            == "active",
            "review_history_pinned": review_account_ids == [ACCOUNT_ID],
            "determination_history_pinned": (
                determination_account_ids == [ACCOUNT_ID]
            ),
            "response_exact": response.record.logical_id == RESPONSE_ID,
            "communication_exact": (
                communication.record.logical_id == COMMUNICATION_ID
            ),
            "support_process_current": support_process.record.status == "active",
            "support_predecessor_exact": original_support.record.status
            == "superseded",
            "support_successor_current": corrected_support.record.status
            == "active",
            "implementation_count_exact": len(implementation_ids),
            "fidelity_exact": fidelity.record.logical_id == FIDELITY_ID,
            "follow_up_completed": (
                follow_up.record.field("workflow_state") == "completed"
            ),
            "operation_terminal": terminal_data.get("state") == "completed",
            "recovery_terminal_consistent": (
                terminal_assessment.disposition == "terminal_consistent"
            ),
            "recovery_staging_gone": True,
            "account_history_readable": bool(account_history_path),
            "support_history_readable": bool(support_history_path),
            "fresh_process_reload": True,
        },
        sort_keys=True,
    )
)
"""

_STUDENT_VIEW_PRIVACY_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.views import (
    STUDENT_VIEW_POLICY,
    StudentTimelineQuery,
    StudentTimelineService,
    StudentViewScope,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
COLLISION_STUDENT_ID = "student_shared_001"
EVENT_ID = "evt_issue53_primary"
SUPPORT_PROCESS_ID = "sup_issue53_support"
ORIGINAL_ACCOUNT_ID = "acct_issue53_cross_report"
CORRECTED_ACCOUNT_ID = "acct_issue53_cross_corrected"
ORIGINAL_SUPPORT_ID = "spt_issue53_access"
CORRECTED_SUPPORT_ID = "spt_issue53_access_corrected"
COMMUNICATION_ID = "comm_issue53_guardian"

workspace = Path(sys.argv[1]).resolve()

event_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
support_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)
focal_student = RosterStudentRef(
    class_id=SECONDARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)


def snapshot(root):
    directories = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_dir()
        )
    )
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
    return directories, files


query = StudentTimelineQuery(
    scope=StudentViewScope(
        focal_students=(focal_student,),
        allowed_works=(event_work, support_work),
        allowed_class_ids=(PRIMARY_CLASS_ID,),
    ),
    mode="current",
    exact_works=(event_work, support_work),
)

before = snapshot(workspace)
result = StudentTimelineService(workspace).generate(query)
after = snapshot(workspace)

if before != after:
    raise RuntimeError("student timeline/view query mutated the workspace")
if result.query != query:
    raise RuntimeError("student timeline result lost exact query identity")
if result.projection.policy != STUDENT_VIEW_POLICY:
    raise RuntimeError("student timeline did not use accepted Issue #48 policy")
if result.history is not None:
    raise RuntimeError("current student timeline unexpectedly assembled history")
if set(result.discovery.work_refs) != {event_work, support_work}:
    raise RuntimeError("student timeline discovery widened or narrowed exact work scope")
if result.discovery.resolved_students != (focal_student,):
    raise RuntimeError("student timeline discovery changed focal roster identity")
if {work.work_ref for work in result.works} != {event_work, support_work}:
    raise RuntimeError("student timeline grouping changed exact discovered works")

presentation = []
source_ids = set()
semantic_types = set()
manual_review_count = 0
withheld_field_count = 0

for entry in result.entries:
    source = entry.source_ref
    if isinstance(source, ExactPortiaWorkRef):
        source_id = source.work_id
        source_wire = {
            "class_id": source.class_id,
            "work_kind": source.work_kind,
            "work_id": source.work_id,
            "contract_version": source.contract_version,
        }
    elif isinstance(source, ExactPortiaWorkRecordRef):
        source_id = source.record_ref.record_id
        source_wire = {
            "class_id": source.work_ref.class_id,
            "work_kind": source.work_ref.work_kind,
            "work_id": source.work_ref.work_id,
            "record_kind": source.record_ref.record_kind,
            "record_id": source.record_ref.record_id,
            "contract_version": source.record_ref.contract_version,
        }
    else:
        raise RuntimeError("student timeline exposed unsupported source reference")
    source_ids.add(source_id)
    semantic_types.add(entry.semantic_type)

    fields = []
    for field in entry.fields:
        if field.disposition != "included" and field.value is not None:
            raise RuntimeError("privacy-limited field carried a source value")
        if field.disposition == "requires_manual_review":
            manual_review_count += 1
        if field.disposition == "withheld":
            withheld_field_count += 1
        fields.append(
            {
                "name": field.name,
                "disposition": field.disposition,
                "value": field.value,
            }
        )
    presentation.append(
        {
            "source_ref": source_wire,
            "disposition": entry.disposition,
            "category": entry.category,
            "semantic_type": entry.semantic_type,
            "status": entry.status,
            "native_scope": entry.native_scope,
            "focal_applicability": entry.focal_applicability,
            "fields": fields,
            "history_kind": entry.history_kind,
        }
    )

if ORIGINAL_ACCOUNT_ID in source_ids:
    raise RuntimeError("student view exposed superseded Account as current")
if CORRECTED_ACCOUNT_ID not in source_ids:
    raise RuntimeError("student view omitted current corrected Account")
if ORIGINAL_SUPPORT_ID in source_ids:
    raise RuntimeError("student view exposed superseded Support as current")
if CORRECTED_SUPPORT_ID not in source_ids:
    raise RuntimeError("student view omitted current corrected Support")

for unrelated_id in (
    "ep_issue53_primary",
    "ep_issue53_guardian",
    "spp_issue53_counselor",
    COMMUNICATION_ID,
):
    if unrelated_id in source_ids:
        raise RuntimeError("student view widened to unrelated person/communication")

account_entries = [
    entry
    for entry in result.entries
    if isinstance(entry.source_ref, ExactPortiaWorkRecordRef)
    and entry.source_ref.record_ref.record_id == CORRECTED_ACCOUNT_ID
]
if len(account_entries) != 1:
    raise RuntimeError("student view did not produce one corrected Account entry")
account_fields = {field.name: field for field in account_entries[0].fields}
content_field = account_fields.get("content")
if content_field is None or content_field.disposition != "requires_manual_review":
    raise RuntimeError("unsafe Account narrative did not require manual review")
if content_field.value is not None:
    raise RuntimeError("manual-review Account content leaked raw narrative")

event_entries = [
    entry
    for entry in result.entries
    if isinstance(entry.source_ref, ExactPortiaWorkRef)
    and entry.source_ref == event_work
]
if len(event_entries) != 1:
    raise RuntimeError("student view did not preserve exact Event root")
event_fields = {field.name: field for field in event_entries[0].fields}
summary_field = event_fields.get("summary")
if summary_field is None or summary_field.disposition != "withheld":
    raise RuntimeError("Event summary was not withheld by accepted policy")
if summary_field.value is not None:
    raise RuntimeError("withheld Event summary leaked source value")

support_entries = [
    entry
    for entry in result.entries
    if isinstance(entry.source_ref, ExactPortiaWorkRecordRef)
    and entry.source_ref.record_ref.record_id == CORRECTED_SUPPORT_ID
]
if len(support_entries) != 1:
    raise RuntimeError("student view did not preserve corrected Support")
support_fields = {field.name: field for field in support_entries[0].fields}
strategy_field = support_fields.get("strategy")
if strategy_field is None or strategy_field.disposition != "requires_manual_review":
    raise RuntimeError("Support strategy did not require manual review")
if strategy_field.value is not None:
    raise RuntimeError("manual-review Support strategy leaked raw plan text")

operational_semantics = {
    "operation_journal",
    "operation_current_pointer",
    "operation_lock",
    "quarantine_record",
    "integrity_finding",
    "source_snapshot",
    "derived_index_metadata",
    "derived_current_pointer",
}
if semantic_types.intersection(operational_semantics):
    raise RuntimeError("student view exposed operational/Integrity internals")

serialized = json.dumps(presentation, sort_keys=True, default=str)
for prohibited in (
    "guardian.issue53@example.invalid",
    "Shared Synthetic",
    "Synthetic Counselor",
    "actr_guardian_001",
    "actr_counselor_001",
    "acp_guardian_email_001",
    "student_primary_002",
    "student_secondary_002",
    "Synthetic classroom material-location discrepancy.",
    "blue marker",
    "op_issue53_support_recovery",
    "op_issue53_account_corrected",
    ".portia-staging",
    "/.staging/",
    "sha256_digest",
    "fingerprint",
    str(workspace),
):
    if prohibited in serialized:
        raise RuntimeError(
            f"student view leaked prohibited privacy/operational value: {prohibited}"
        )

if manual_review_count < 1:
    raise RuntimeError("student view did not exercise manual-review handling")
if withheld_field_count < 1:
    raise RuntimeError("student view did not exercise withheld handling")

print(
    json.dumps(
        {
            "focal_class": focal_student.class_id,
            "work_count": len(result.works),
            "entry_count": len(result.entries),
            "manual_review_field_count": manual_review_count,
            "withheld_field_count": withheld_field_count,
            "corrected_account_present": CORRECTED_ACCOUNT_ID in source_ids,
            "superseded_account_absent": ORIGINAL_ACCOUNT_ID not in source_ids,
            "corrected_support_present": CORRECTED_SUPPORT_ID in source_ids,
            "superseded_support_absent": ORIGINAL_SUPPORT_ID not in source_ids,
            "unrelated_participants_absent": all(
                value not in source_ids
                for value in (
                    "ep_issue53_primary",
                    "ep_issue53_guardian",
                    "spp_issue53_counselor",
                )
            ),
            "communication_not_focally_inferred": COMMUNICATION_ID not in source_ids,
            "operational_internals_absent": not bool(
                semantic_types.intersection(operational_semantics)
            ),
            "privacy_values_absent": True,
            "student_view_read_only": before == after,
            "accepted_policy": result.projection.policy == STUDENT_VIEW_POLICY,
        },
        sort_keys=True,
    )
)
"""

_TEACHER_REFERENCE_EXPORT_PROBE = r"""
import json
import sys
from pathlib import Path

from portia.exports import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionService,
    TeacherReferenceExportExecutionSuccess,
    TeacherReferenceExportHistoryService,
    TeacherReferenceExportPreparationService,
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
    TeacherReferenceSourceInventoryService,
)
from portia.menu.identifiers import PortiaIdGenerator
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaRepository

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
SUPPORT_PROCESS_ID = "sup_issue53_support"
ORIGINAL_SUPPORT_ID = "spt_issue53_access"
CORRECTED_SUPPORT_ID = "spt_issue53_access_corrected"
GUARDIAN_ACTOR_ID = "actr_guardian_001"
COUNSELOR_ACTOR_ID = "actr_counselor_001"
GUARDIAN_CONTACT_POINT_ID = "acp_guardian_email_001"
GUARDIAN_EMAIL = "guardian.issue53@example.invalid"
EVENT_ID = "evt_issue53_primary"
REVIEWED_AT = "2026-10-04T18:00:00-04:00"
GENERATED_AT = "2026-10-04T18:01:00-04:00"
CONFIRMED_AT = "2026-10-04T18:02:00-04:00"
OPERATOR = {
    "type": "local_operator",
    "display_label": "Synthetic Acceptance Operator",
}

workspace = Path(sys.argv[1]).resolve()
repository = PortiaRepository(workspace)
support_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)
scope = TeacherReferenceExportScope("teacher_current", support_work)

discovery_service = TeacherReferenceScopeDiscoveryService(
    workspace,
    repository=repository,
)
discovery = discovery_service.discover(scope)
if discovery.scope != scope:
    raise RuntimeError("teacher-reference discovery changed exact selected scope")
if not discovery.observations:
    raise RuntimeError("teacher-reference discovery found no exact support sources")
if any(observation.work_ref != support_work for observation in discovery.observations):
    raise RuntimeError("teacher-reference discovery widened beyond selected Support Process")

projection_service = TeacherReferenceProjectionService(
    workspace,
    repository=repository,
)
pending = projection_service.project(discovery)
if pending.manual_review.status != "pending":
    raise RuntimeError("representative teacher-reference export did not require review")

choices = []
summary_included = False
initiation_omitted = False
for item in pending.unresolved_manual_items:
    if item.field_name is None:
        raise RuntimeError("teacher-reference manual item lacks exact field identity")
    if item.source_ref == support_work and item.field_name == "summary":
        resolution = "include_exact"
        summary_included = True
    else:
        resolution = "omit"
        if item.source_ref == support_work and item.field_name == "initiation":
            initiation_omitted = True
    choices.append(
        TeacherReferenceManualReviewChoice(
            item.source_ref,
            item.field_name,
            resolution,
        )
    )

if not summary_included:
    raise RuntimeError("teacher-reference review did not include exact Support summary")
if not initiation_omitted:
    raise RuntimeError("teacher-reference review did not deliberately omit Support initiation")
if not any(choice.resolution == "include_exact" for choice in choices):
    raise RuntimeError("teacher-reference review lacked an explicit include choice")
if not any(choice.resolution == "omit" for choice in choices):
    raise RuntimeError("teacher-reference review lacked an explicit omit choice")

decision = projection_service.resolve_manual_review(
    pending,
    tuple(choices),
    reviewed_at=REVIEWED_AT,
    reviewed_by=OPERATOR,
)
if not decision.is_final or decision.manual_review.status != "resolved":
    raise RuntimeError("teacher-reference manual review did not finalize exact projection")

inventory_service = TeacherReferenceSourceInventoryService(
    workspace,
    repository=repository,
)
inventory = inventory_service.author(decision)
inventory_identities = {
    json.dumps(ref.to_dict(), sort_keys=True)
    for ref in inventory.source_refs
}
contributing_identities = {
    json.dumps(ref.to_dict(), sort_keys=True)
    for ref in decision.contributing_source_refs
}
if inventory_identities != contributing_identities:
    raise RuntimeError("teacher-reference inventory drifted from exact contributing sources")
if any(
    (
        ref != support_work
        if isinstance(ref, ExactPortiaWorkRef)
        else ref.work_ref != support_work
    )
    for ref in inventory.source_refs
):
    raise RuntimeError("teacher-reference inventory escaped selected Support Process")

inventory_wire = inventory.to_dict()
inventory_serialized = json.dumps(inventory_wire, sort_keys=True)
for prohibited in (
    SECONDARY_CLASS_ID,
    GUARDIAN_ACTOR_ID,
    COUNSELOR_ACTOR_ID,
    GUARDIAN_CONTACT_POINT_ID,
    GUARDIAN_EMAIL,
    EVENT_ID,
):
    if prohibited in inventory_serialized:
        raise RuntimeError(
            f"teacher-reference inventory widened into identity/context source: {prohibited}"
        )

source_fingerprints = []
for source_ref in inventory.source_refs:
    if isinstance(source_ref, ExactPortiaWorkRef):
        stored = repository.load_work(source_ref)
    elif isinstance(source_ref, ExactPortiaWorkRecordRef):
        stored = repository.load_work_record(
            source_ref.work_ref,
            source_ref.record_ref.record_kind,
            source_ref.record_ref.contract_version,
            source_ref.record_ref.record_id,
        )
    else:
        raise RuntimeError("teacher-reference inventory exposed unsupported source type")
    source_fingerprints.append((source_ref, stored.fingerprint))

def id_generator():
    tokens = iter(
        (
            "issue53_teacher_export",
            "issue53_teacher_operation",
            "issue53_teacher_artifact",
            "issue53_teacher_provenance",
        )
    )
    return PortiaIdGenerator(token_source=tokens.__next__)

def prepare():
    return TeacherReferenceExportPreparationService(
        workspace,
        repository=repository,
        id_generator=id_generator(),
    ).prepare(
        decision,
        requested_at=REVIEWED_AT,
        requested_by=OPERATOR,
        generated_at=GENERATED_AT,
        deployment_instance_id="issue53_installed_acceptance",
        process_instance_id="issue53_installed_acceptance_process",
    )

prepared = prepare()
repeated = prepare()
if prepared.preparation_digest != repeated.preparation_digest:
    raise RuntimeError("teacher-reference preparation was not deterministic")
if prepared.artifact_bytes != repeated.artifact_bytes:
    raise RuntimeError("teacher-reference HTML rendering was not deterministic")
if prepared.provenance_bytes != repeated.provenance_bytes:
    raise RuntimeError("teacher-reference provenance rendering was not deterministic")

expected_artifact_path = f"portia/exports/{prepared.export_id}/artifact.html"
expected_provenance_path = f"portia/exports/{prepared.export_id}/export.json"
if prepared.artifact_relative_path != expected_artifact_path:
    raise RuntimeError("teacher-reference artifact path escaped exact export location")
if prepared.provenance_relative_path != expected_provenance_path:
    raise RuntimeError("teacher-reference provenance path escaped exact export location")
if prepared.inventory.to_dict() != inventory_wire:
    raise RuntimeError("teacher-reference preparation changed exact source inventory")
if prepared.decision.projection_decision_digest != decision.projection_decision_digest:
    raise RuntimeError("teacher-reference preparation changed reviewed projection")

warning = (
    "Local teacher reference only; this export is not a disclosure or official "
    "institutional record."
)
if warning not in prepared.preview.warnings:
    raise RuntimeError("teacher-reference preview lost local-reference boundary warning")

execution = TeacherReferenceExportExecutionService(
    workspace,
    repository=repository,
    discovery_service=discovery_service,
    projection_service=projection_service,
)
result = execution.execute(
    prepared,
    confirmation=TEACHER_REFERENCE_CONFIRMATION,
    confirmed_preparation_digest=prepared.preparation_digest,
    confirmed_at=CONFIRMED_AT,
)
if not isinstance(result, TeacherReferenceExportExecutionSuccess):
    raise RuntimeError("teacher-reference export did not complete through production execution")
if result.status != "completed":
    raise RuntimeError("teacher-reference export did not reach completed state")
if result.export_id != prepared.export_id or result.operation_id != prepared.operation_id:
    raise RuntimeError("teacher-reference execution changed reviewed export identity")

artifact_path = workspace / prepared.artifact_relative_path
provenance_path = workspace / prepared.provenance_relative_path
artifact_bytes_after_success = artifact_path.read_bytes()
provenance_bytes_after_success = provenance_path.read_bytes()
if artifact_bytes_after_success != prepared.artifact_bytes:
    raise RuntimeError("persisted teacher-reference artifact differs from reviewed bytes")
if provenance_bytes_after_success != prepared.provenance_bytes:
    raise RuntimeError("persisted teacher-reference provenance differs from reviewed bytes")

provenance_wire = json.loads(provenance_bytes_after_success)
if provenance_wire != prepared.deliberate_export.to_dict():
    raise RuntimeError("teacher-reference export.json is not exact reviewed provenance")
if provenance_wire.get("source_inventory") != inventory_wire:
    raise RuntimeError("teacher-reference export.json source inventory changed")
if provenance_wire.get("projection_decision_digest") != decision.projection_decision_digest:
    raise RuntimeError("teacher-reference export.json lost reviewed projection digest")

artifact_text = artifact_bytes_after_success.decode("utf-8")
if "Synthetic Counselor" not in artifact_text:
    raise RuntimeError("teacher-reference artifact lost embedded participant snapshot")
for prohibited in (
    GUARDIAN_EMAIL,
    GUARDIAN_CONTACT_POINT_ID,
    GUARDIAN_ACTOR_ID,
    COUNSELOR_ACTOR_ID,
    SECONDARY_CLASS_ID,
    EVENT_ID,
    ORIGINAL_SUPPORT_ID,
):
    if prohibited in artifact_text:
        raise RuntimeError(
            f"teacher-reference artifact leaked live/unrelated source value: {prohibited}"
        )

provenance_serialized = json.dumps(provenance_wire, sort_keys=True)
for prohibited in (
    GUARDIAN_EMAIL,
    GUARDIAN_CONTACT_POINT_ID,
    GUARDIAN_ACTOR_ID,
    COUNSELOR_ACTOR_ID,
    SECONDARY_CLASS_ID,
    EVENT_ID,
):
    if prohibited in provenance_serialized:
        raise RuntimeError(
            f"teacher-reference provenance widened into unrelated identity: {prohibited}"
        )

for source_ref, expected_fingerprint in source_fingerprints:
    if isinstance(source_ref, ExactPortiaWorkRef):
        stored = repository.load_work(source_ref)
    else:
        stored = repository.load_work_record(
            source_ref.work_ref,
            source_ref.record_ref.record_kind,
            source_ref.record_ref.contract_version,
            source_ref.record_ref.record_id,
        )
    if stored.fingerprint != expected_fingerprint:
        raise RuntimeError("teacher-reference export mutated canonical source representation")

history = TeacherReferenceExportHistoryService(workspace).list_for_work(support_work)
matching = [entry for entry in history if entry.export_id == prepared.export_id]
if len(matching) != 1:
    raise RuntimeError("teacher-reference export history did not return exact export")
if matching[0].verification_status != "available_verified":
    raise RuntimeError("teacher-reference export history verification did not succeed")
if matching[0].operation_id != prepared.operation_id:
    raise RuntimeError("teacher-reference history lost exact coordinated operation identity")

if artifact_path.read_bytes() != artifact_bytes_after_success:
    raise RuntimeError("teacher-reference artifact changed after successful persistence")
if provenance_path.read_bytes() != provenance_bytes_after_success:
    raise RuntimeError("teacher-reference provenance changed during history verification")

print(
    json.dumps(
        {
            "projection_purpose": scope.projection_purpose,
            "manual_include_count": sum(
                choice.resolution == "include_exact" for choice in choices
            ),
            "manual_omit_count": sum(choice.resolution == "omit" for choice in choices),
            "source_inventory_count": len(inventory.source_refs),
            "source_inventory_exact": inventory_identities
            == contributing_identities,
            "render_deterministic": prepared.artifact_bytes
            == repeated.artifact_bytes,
            "provenance_exact": provenance_wire
            == prepared.deliberate_export.to_dict(),
            "artifact_path_exact": prepared.artifact_relative_path
            == expected_artifact_path,
            "provenance_path_exact": prepared.provenance_relative_path
            == expected_provenance_path,
            "history_verified": matching[0].verification_status
            == "available_verified",
            "artifact_immutable_after_success": artifact_path.read_bytes()
            == artifact_bytes_after_success,
            "provenance_immutable_after_success": provenance_path.read_bytes()
            == provenance_bytes_after_success,
            "canonical_sources_unchanged": True,
            "actor_directory_not_live_enrichment": (
                "Synthetic Counselor" in artifact_text
                and COUNSELOR_ACTOR_ID not in artifact_text
            ),
            "contact_point_data_absent": GUARDIAN_EMAIL not in artifact_text,
            "unrelated_class_not_widened": SECONDARY_CLASS_ID
            not in provenance_serialized,
            "local_teacher_reference_only": warning in prepared.preview.warnings,
        },
        sort_keys=True,
    )
)
"""

_READ_ONLY_SURFACES_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from pds_core.module_operations import (
    ModuleOperationsRequest,
    invoke_module_operations,
)
from pds_core.provider_diagnostics import diagnose_core_providers

from portia.attention import (
    AttentionQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.exports import TeacherReferenceExportHistoryService
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef, RosterStudentRef
from portia.views import (
    StudentTimelineQuery,
    StudentTimelineService,
    StudentViewScope,
)
from portia.workflows import (
    AccountWorkflowService,
    SupportWorkflowService,
    account_reference,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
SECONDARY_CLASS_ID = "journalism_p6_2026"
ACTIVE_SCHOOL_YEAR = "2026-2027"
COLLISION_STUDENT_ID = "student_shared_001"
EVENT_ID = "evt_issue53_primary"
SUPPORT_PROCESS_ID = "sup_issue53_support"
ORIGINAL_ACCOUNT_ID = "acct_issue53_cross_report"
ORIGINAL_SUPPORT_ID = "spt_issue53_access"
ATTENTION_AS_OF = ExplicitOffsetTimestamp("2026-10-19T09:00:00-04:00")

workspace = Path(sys.argv[1]).resolve()

event_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
support_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)
focal_student = RosterStudentRef(
    class_id=SECONDARY_CLASS_ID,
    student_id=COLLISION_STUDENT_ID,
)


def snapshot(root):
    directories = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_dir()
        )
    )
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
    return directories, files


def require_read_only(label, operation):
    before = snapshot(workspace)
    result = operation()
    after = snapshot(workspace)
    if after != before:
        raise RuntimeError(f"{label} mutated workspace bytes")
    return result


whole_phase_before = snapshot(workspace)

student_query = StudentTimelineQuery(
    scope=StudentViewScope(
        focal_students=(focal_student,),
        allowed_works=(event_work, support_work),
        allowed_class_ids=(PRIMARY_CLASS_ID,),
    ),
    mode="current",
    exact_works=(event_work, support_work),
)
student_result = require_read_only(
    "student timeline/view query",
    lambda: StudentTimelineService(workspace).generate(student_query),
)
if student_result.discovery.resolved_students != (focal_student,):
    raise RuntimeError("read-only student view changed exact focal identity")
if set(student_result.discovery.work_refs) != {event_work, support_work}:
    raise RuntimeError("read-only student view changed exact work scope")

attention_query = PortiaAttentionQuery(
    scope=PortiaAttentionScope.work_scope(support_work),
    as_of=ATTENTION_AS_OF,
    active_school_year=ACTIVE_SCHOOL_YEAR,
    attention_codes=(
        "portia_follow_up_due",
        "portia_follow_up_overdue",
    ),
)
attention_result = require_read_only(
    "attention query",
    lambda: AttentionQueryService(workspace).query(attention_query),
)
if attention_result.evaluation != "evaluated":
    raise RuntimeError("read-only attention query was not evaluated")
if attention_result.items:
    raise RuntimeError("completed Follow-Up unexpectedly remained outstanding attention")


def invoke_core_provider():
    diagnostics = diagnose_core_providers(provider_kind="module_operations")
    portia_diagnostics = tuple(
        result
        for result in diagnostics
        if result.metadata.entry_point_name == "portia"
    )
    if len(portia_diagnostics) != 1:
        raise RuntimeError("read-only Core provider discovery did not isolate Portia")
    diagnostic = portia_diagnostics[0]
    if diagnostic.code != "provider.valid":
        raise RuntimeError("read-only Core provider diagnosis was not valid")
    profile = diagnostic.validated_profile
    if profile is None:
        raise RuntimeError("read-only Core provider diagnosis lost validated profile")
    request = ModuleOperationsRequest(
        workspace_root=workspace,
        active_school_year=ACTIVE_SCHOOL_YEAR,
        class_id=PRIMARY_CLASS_ID,
    )
    return invoke_module_operations(profile, request)


readiness_result, shared_attention_result = require_read_only(
    "Core readiness/attention provider invocation",
    invoke_core_provider,
)
if readiness_result.report is None or readiness_result.report.ready is not True:
    raise RuntimeError("read-only Core readiness provider did not return ready")
if (
    shared_attention_result.report is None
    or shared_attention_result.report.evaluation != "evaluated"
):
    raise RuntimeError("read-only Core attention provider did not evaluate")

history = require_read_only(
    "teacher-reference export history verification",
    lambda: TeacherReferenceExportHistoryService(workspace).list_for_work(
        support_work
    ),
)
verified_history = tuple(
    entry for entry in history if entry.verification_status == "available_verified"
)
if not verified_history:
    raise RuntimeError(
        "read-only teacher-reference history did not verify the completed export"
    )


def load_exact_history():
    accounts = AccountWorkflowService(workspace)
    supports = SupportWorkflowService(workspace)
    original_account = accounts.load_exact(
        account_reference(event_work, ORIGINAL_ACCOUNT_ID)
    )
    original_support = supports.load_exact(
        support_reference(support_work, ORIGINAL_SUPPORT_ID)
    )
    return original_account, original_support


original_account, original_support = require_read_only(
    "exact historical predecessor loads",
    load_exact_history,
)
if original_account.record.logical_id != ORIGINAL_ACCOUNT_ID:
    raise RuntimeError("exact historical Account load changed identity")
if original_support.record.logical_id != ORIGINAL_SUPPORT_ID:
    raise RuntimeError("exact historical Support load changed identity")
if original_account.record.status != "superseded":
    raise RuntimeError("exact historical Account predecessor is no longer superseded")
if original_support.record.status != "superseded":
    raise RuntimeError("exact historical Support predecessor is no longer superseded")

whole_phase_after = snapshot(workspace)
if whole_phase_after != whole_phase_before:
    raise RuntimeError("combined Issue #53 read-only phase mutated workspace bytes")

print(
    json.dumps(
        {
            "student_view_zero_write": True,
            "attention_zero_write": True,
            "core_provider_zero_write": True,
            "export_history_zero_write": True,
            "historical_loads_zero_write": True,
            "whole_read_only_phase_zero_write": (
                whole_phase_after == whole_phase_before
            ),
            "student_work_count": len(student_result.discovery.work_refs),
            "attention_item_count": len(attention_result.items),
            "verified_export_history_count": len(verified_history),
            "historical_account_status": original_account.record.status,
            "historical_support_status": original_support.record.status,
        },
        sort_keys=True,
    )
)
"""

_DEEP_PATH_INTEGRATION_PROBE = r"""
import hashlib
import json
import sys
from pathlib import Path

from portia.exports import TeacherReferenceExportHistoryService
from portia.models.references import ExactPortiaWorkRef
from portia.storage.io import read_json
from portia.storage.paths import (
    derived_projection_root,
    legacy_derived_projection_root,
    operation_root,
    resolve_workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.storage.staging import (
    legacy_staging_path_for,
    staging_path_for,
)
from portia.workflows import (
    AccountWorkflowService,
    IntegrityWorkflowService,
    SupportWorkflowService,
    account_reference,
    support_reference,
)

PRIMARY_CLASS_ID = "eng10_p2_2026"
EVENT_ID = "evt_issue53_primary"
SUPPORT_PROCESS_ID = "sup_issue53_support"
ORIGINAL_ACCOUNT_ID = "acct_issue53_cross_report"
ORIGINAL_SUPPORT_ID = "spt_issue53_access"
ACCOUNT_CORRECTION_OPERATION_ID = "op_issue53_account_corrected"
RECOVERY_OPERATION_ID = "op_issue53_support_recovery"
PROJECTION_KIND = "active_integrity_finding_index"
TARGET_DEEP_WORKSPACE_LENGTH = 119

workspace = Path(sys.argv[1]).resolve()
event_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=EVENT_ID,
    work_kind="event",
    contract_version="2",
)
support_work = ExactPortiaWorkRef(
    class_id=PRIMARY_CLASS_ID,
    work_id=SUPPORT_PROCESS_ID,
    work_kind="support_process",
    contract_version="1",
)


def snapshot(root):
    directories = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_dir()
        )
    )
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
    return directories, files


def require_workspace_descendant(path):
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(workspace)
    except ValueError as exc:
        raise RuntimeError("Issue #53 path evidence escaped the deep workspace") from exc
    return resolved


def operation_revisions(operation_id):
    revisions_root = operation_root(workspace, operation_id) / "revisions"
    if not revisions_root.is_dir():
        raise RuntimeError("operation revision history is unavailable")
    revisions = []
    for path in sorted(
        revisions_root.glob("*.json"),
        key=lambda candidate: int(candidate.stem),
    ):
        value, _content, _fingerprint = read_json(path)
        if not isinstance(value, dict):
            raise RuntimeError("operation revision is not an object")
        revisions.append(value)
    if not revisions:
        raise RuntimeError("operation revision history is empty")
    return tuple(revisions)


def current_operation(operation_id):
    return OperationJournalStore(workspace).load_current(operation_id).revision.to_dict()


def exact_step(journal, step_id):
    write_set = journal.get("write_set")
    if not isinstance(write_set, list):
        raise RuntimeError("operation journal write set is malformed")
    matches = [
        step
        for step in write_set
        if isinstance(step, dict) and step.get("step_id") == step_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"operation journal lost exact {step_id} identity")
    return matches[0]


def technical_history_evidence(operation_id, legacy_kind):
    journal = current_operation(operation_id)
    if journal.get("state") != "completed":
        raise RuntimeError("technical-history operation is not completed")
    history_step = exact_step(journal, "step_history")
    if history_step.get("disposition") != "accepted":
        raise RuntimeError("technical-history step is not durably accepted")
    relative = history_step.get("destination_path")
    if not isinstance(relative, str):
        raise RuntimeError("technical-history destination is malformed")
    if "/history/storage_revisions/" not in f"/{relative}":
        raise RuntimeError("technical-history path is outside bounded history namespace")
    path = require_workspace_descendant(
        resolve_workspace_relative(workspace, relative)
    )
    if not path.is_file():
        raise RuntimeError("technical-history artifact is missing")
    if len(path.name) != 40:
        raise RuntimeError("technical-history writer did not use bounded Issue #92 leaf")
    legacy_kind_root = path.parent / legacy_kind
    if legacy_kind_root.exists() or legacy_kind_root.is_symlink():
        raise RuntimeError("Issue #53 manufactured a legacy technical-history layout")
    return path, legacy_kind_root


def staged_path_evidence(operation_id, *, recovering_only):
    observed = []
    legacy_candidates = []
    for revision in operation_revisions(operation_id):
        if recovering_only and revision.get("state") != "recovering":
            continue
        staged = revision.get("staged_artifacts")
        if not isinstance(staged, list) or not staged:
            continue
        write_set = revision.get("write_set")
        if not isinstance(write_set, list):
            raise RuntimeError("staged operation revision lost write set")
        for entry in staged:
            if not isinstance(entry, dict):
                raise RuntimeError("staged operation evidence is malformed")
            relative = entry.get("staging_path")
            if not isinstance(relative, str):
                raise RuntimeError("staged operation path is malformed")
            matches = []
            for step in write_set:
                if not isinstance(step, dict):
                    continue
                step_id = step.get("step_id")
                destination = step.get("destination_path")
                if not isinstance(step_id, str) or not isinstance(destination, str):
                    continue
                bounded = staging_path_for(
                    workspace,
                    operation_id,
                    step_id,
                    destination,
                )
                bounded_relative = bounded.relative_to(workspace).as_posix()
                if bounded_relative == relative:
                    matches.append((step_id, destination, bounded))
            if len(matches) != 1:
                raise RuntimeError(
                    "journaled staging path does not match exact Issue #92 identity"
                )
            step_id, destination, bounded = matches[0]
            if not relative.startswith("portia/.staging/"):
                raise RuntimeError("journaled staging path is not workspace-level bounded staging")
            legacy = legacy_staging_path_for(
                workspace,
                operation_id,
                step_id,
                destination,
            )
            legacy_relative = legacy.relative_to(workspace).as_posix()
            if relative == legacy_relative:
                raise RuntimeError("journaled staging path used legacy target-adjacent identity")
            observed.append(require_workspace_descendant(bounded))
            legacy_candidates.append(require_workspace_descendant(legacy))
    if not observed:
        description = "recovery" if recovering_only else "coordinated"
        raise RuntimeError(f"{description} operation retained no historical staging evidence")
    return tuple(observed), tuple(legacy_candidates)


before = snapshot(workspace)

if len(str(workspace)) < TARGET_DEEP_WORKSPACE_LENGTH:
    raise RuntimeError("Issue #53 semantic story is not using the representative deep root")

account_history, account_legacy_history = technical_history_evidence(
    ACCOUNT_CORRECTION_OPERATION_ID,
    "account",
)
support_history, support_legacy_history = technical_history_evidence(
    RECOVERY_OPERATION_ID,
    "support",
)

account_predecessor = AccountWorkflowService(workspace).load_exact(
    account_reference(event_work, ORIGINAL_ACCOUNT_ID)
)
support_predecessor = SupportWorkflowService(workspace).load_exact(
    support_reference(support_work, ORIGINAL_SUPPORT_ID)
)
if account_predecessor.record.status != "superseded":
    raise RuntimeError("Account guarded replacement evidence is no longer superseded")
if support_predecessor.record.status != "superseded":
    raise RuntimeError("Support recovery replacement evidence is no longer superseded")

coordinated_staging, coordinated_legacy = staged_path_evidence(
    ACCOUNT_CORRECTION_OPERATION_ID,
    recovering_only=False,
)
recovery_staging, recovery_legacy = staged_path_evidence(
    RECOVERY_OPERATION_ID,
    recovering_only=True,
)

for staged in (*coordinated_staging, *recovery_staging):
    if staged.exists() or staged.is_symlink():
        raise RuntimeError("completed story retained operation-owned staging")
for legacy in (*coordinated_legacy, *recovery_legacy):
    if legacy.exists() or legacy.is_symlink():
        raise RuntimeError("Issue #53 created a legacy target-adjacent staging artifact")

integrity = IntegrityWorkflowService(workspace)
integrity_scope = integrity.operation_scope(RECOVERY_OPERATION_ID)
if integrity.current_findings(integrity_scope) != ():
    raise RuntimeError("current recovered Integrity projection is not clean")
integrity_root = require_workspace_descendant(
    derived_projection_root(
        workspace,
        PROJECTION_KIND,
        integrity_scope,
    )
)
legacy_integrity_root = require_workspace_descendant(
    legacy_derived_projection_root(
        workspace,
        PROJECTION_KIND,
        integrity_scope,
    )
)
if integrity_root.parent != workspace / "portia" / "derived-v2":
    raise RuntimeError("Integrity state is not using bounded derived-v2 namespace")
if not (integrity_root / "current.json").is_file():
    raise RuntimeError("bounded Integrity current projection is missing")
if legacy_integrity_root.exists() or legacy_integrity_root.is_symlink():
    raise RuntimeError("Issue #53 migrated Integrity state into a legacy derived layout")

export_history = TeacherReferenceExportHistoryService(workspace).list_for_work(
    support_work
)
verified_exports = tuple(
    entry
    for entry in export_history
    if entry.verification_status == "available_verified"
)
if len(verified_exports) != 1:
    raise RuntimeError("Issue #53 deep-path probe expected one verified teacher export")
export = verified_exports[0]
expected_artifact_relative = f"portia/exports/{export.export_id}/artifact.html"
if export.artifact_relative_path != expected_artifact_relative:
    raise RuntimeError("teacher-reference artifact path changed from bounded export identity")
artifact_path = require_workspace_descendant(
    resolve_workspace_relative(workspace, expected_artifact_relative)
)
provenance_path = require_workspace_descendant(
    workspace / "portia" / "exports" / export.export_id / "export.json"
)
if not artifact_path.is_file() or not provenance_path.is_file():
    raise RuntimeError("teacher-reference export artifacts are missing from deep workspace")
if artifact_path.parent != provenance_path.parent:
    raise RuntimeError("teacher-reference artifact/provenance escaped one export root")

after = snapshot(workspace)
if after != before:
    raise RuntimeError("Issue #53 deep-path integration inspection mutated workspace")

print(
    json.dumps(
        {
            "deep_workspace_length": len(str(workspace)),
            "one_deep_workspace": True,
            "guarded_replacement_history": (
                account_predecessor.record.status == "superseded"
                and support_predecessor.record.status == "superseded"
            ),
            "account_history_leaf_length": len(account_history.name),
            "support_history_leaf_length": len(support_history.name),
            "technical_history_bounded": (
                len(account_history.name) == 40
                and len(support_history.name) == 40
            ),
            "coordinated_staging_count": len(coordinated_staging),
            "recovery_staging_count": len(recovery_staging),
            "coordinated_staging_bounded": True,
            "recovery_staging_bounded": True,
            "staging_cleaned": not any(
                path.exists()
                for path in (*coordinated_staging, *recovery_staging)
            ),
            "integrity_derived_v2": (
                integrity_root.parent == workspace / "portia" / "derived-v2"
            ),
            "teacher_export_in_deep_workspace": (
                artifact_path.is_file() and provenance_path.is_file()
            ),
            "legacy_writer_paths_absent": (
                not account_legacy_history.exists()
                and not support_legacy_history.exists()
                and not legacy_integrity_root.exists()
                and not any(
                    path.exists()
                    for path in (*coordinated_legacy, *recovery_legacy)
                )
            ),
            "inspection_read_only": before == after,
        },
        sort_keys=True,
    )
)
"""

_DIRECT_IO_WRITER_NAMES: Final[frozenset[str]] = frozenset(
    {"exclusive_create", "guarded_replace", "exact_delete"}
)
_DIRECT_STAGING_WRITER_NAMES: Final[frozenset[str]] = frozenset(
    {"stage_bytes", "publish_staged", "cleanup_staged", "replace_staging_candidate"}
)
_REPOSITORY_MUTATOR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "create_work",
        "replace_work",
        "create_work_record",
        "replace_work_record",
        "create_exceptional_removal",
        "create_actor",
        "replace_actor",
        "create_actor_child",
        "replace_actor_child",
        "create_actor_directory_removal",
    }
)
_DIRECT_PATH_WRITER_NAMES: Final[frozenset[str]] = frozenset(
    {"write_text", "write_bytes", "touch"}
)
_COPY_WRITER_NAMES: Final[frozenset[str]] = frozenset(
    {"copy", "copy2", "copyfile", "copytree", "move"}
)


def _write_mode(call: ast.Call) -> str | None:
    mode: object | None = None
    if isinstance(call.func, ast.Name) and call.func.id == "open":
        if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
            mode = call.args[1].value
    elif isinstance(call.func, ast.Attribute) and call.func.attr == "open":
        if call.args and isinstance(call.args[0], ast.Constant):
            mode = call.args[0].value
    for keyword in call.keywords:
        if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
            mode = keyword.value.value
    return mode if isinstance(mode, str) else None


def _assert_no_fixture_bypass() -> dict[str, object]:
    probe_sources = tuple(
        sorted(
            (name, value)
            for name, value in globals().items()
            if name.startswith("_")
            and name.endswith("_PROBE")
            and isinstance(value, str)
        )
    )
    if not probe_sources:
        raise Issue53AcceptanceError(
            "Issue #53 no-fixture-bypass audit found no embedded probes"
        )

    parsed_input_count = 0
    repository_instance_count = 0

    for probe_name, source in probe_sources:
        try:
            tree = ast.parse(source, filename=f"<{probe_name}>")
        except SyntaxError as exc:
            raise Issue53AcceptanceError(
                f"Issue #53 embedded probe {probe_name} is not valid Python"
            ) from exc

        repository_constructors: set[str] = set()
        shutil_modules: set[str] = set()
        shutil_functions: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in {"portia.storage", "portia.storage.repository"}:
                    for alias in node.names:
                        if alias.name == "PortiaRepository":
                            repository_constructors.add(alias.asname or alias.name)

                if module == "portia.storage.io":
                    forbidden = {
                        alias.name
                        for alias in node.names
                        if alias.name in _DIRECT_IO_WRITER_NAMES
                    }
                    if forbidden:
                        raise Issue53AcceptanceError(
                            f"Issue #53 probe {probe_name} imports direct canonical "
                            f"storage writer(s): {sorted(forbidden)}"
                        )

                if module == "portia.storage.staging":
                    forbidden = {
                        alias.name
                        for alias in node.names
                        if alias.name in _DIRECT_STAGING_WRITER_NAMES
                    }
                    if forbidden:
                        raise Issue53AcceptanceError(
                            f"Issue #53 probe {probe_name} imports direct staging "
                            f"writer(s): {sorted(forbidden)}"
                        )

                if module == "shutil":
                    for alias in node.names:
                        if alias.name in _COPY_WRITER_NAMES:
                            shutil_functions.add(alias.asname or alias.name)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "shutil":
                        shutil_modules.add(alias.asname or alias.name)

            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                normalized = node.value.replace("\\", "/").casefold()
                if "issue_22" in normalized or "issue22" in normalized:
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} references Issue #22 fixture authority"
                    )
                if "tests/fixtures" in normalized:
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} references source-tree fixtures"
                    )

        repository_variables: set[str] = set()
        for node in ast.walk(tree):
            value: ast.AST | None = None
            targets: tuple[ast.AST, ...] = ()
            if isinstance(node, ast.Assign):
                value = node.value
                targets = tuple(node.targets)
            elif isinstance(node, ast.AnnAssign):
                value = node.value
                targets = (node.target,)

            if not isinstance(value, ast.Call):
                continue
            if (
                isinstance(value.func, ast.Name)
                and value.func.id in repository_constructors
            ):
                for target in targets:
                    if isinstance(target, ast.Name):
                        repository_variables.add(target.id)
                        repository_instance_count += 1

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "parse_portia_record"
            ):
                parsed_input_count += 1

            if isinstance(node.func, ast.Attribute):
                if node.func.attr in _DIRECT_PATH_WRITER_NAMES:
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} uses direct filesystem "
                        f"writer {node.func.attr}"
                    )

                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id in shutil_modules
                    and node.func.attr in _COPY_WRITER_NAMES
                ):
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} copies fixture/filesystem state"
                    )

                if (
                    node.func.attr in _REPOSITORY_MUTATOR_NAMES
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in repository_variables
                ):
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} bypasses production workflow "
                        f"services through PortiaRepository.{node.func.attr}"
                    )

                if (
                    node.func.attr in _REPOSITORY_MUTATOR_NAMES
                    and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name)
                    and node.func.value.func.id in repository_constructors
                ):
                    raise Issue53AcceptanceError(
                        f"Issue #53 probe {probe_name} chains a direct "
                        f"PortiaRepository.{node.func.attr} mutation"
                    )

            if isinstance(node.func, ast.Name) and node.func.id in shutil_functions:
                raise Issue53AcceptanceError(
                    f"Issue #53 probe {probe_name} copies fixture/filesystem state"
                )

            mode = _write_mode(node)
            if mode is not None and any(flag in mode for flag in ("w", "a", "x", "+")):
                raise Issue53AcceptanceError(
                    f"Issue #53 probe {probe_name} opens a file in write mode"
                )

    if parsed_input_count < 1:
        raise Issue53AcceptanceError(
            "Issue #53 story no longer constructs deliberate synthetic record inputs"
        )

    return {
        "probe_count": len(probe_sources),
        "parsed_input_count": parsed_input_count,
        "repository_instance_count": repository_instance_count,
        "issue22_fixture_reads_absent": True,
        "source_fixture_reads_absent": True,
        "direct_filesystem_writes_absent": True,
        "direct_storage_writer_imports_absent": True,
        "direct_repository_mutations_absent": True,
        "fixture_bypass_excluded": True,
    }

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

def _recovery_probe(
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
            _RECOVERY_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed recovery probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed recovery probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed recovery result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "partial_error_exact": True,
        "partial_accepted_steps": ["step_history", "step_successor"],
        "partial_state": "recovering",
        "partial_disposition": "resume",
        "partial_findings_count": 0,
        "accepted_history_preserved": True,
        "accepted_successor_preserved": True,
        "accepted_successor_not_republished": True,
        "predecessor_superseded": True,
        "successor_current": True,
        "successor_plan_state": "paused",
        "transition_published": True,
        "terminal_state": "completed",
        "terminal_disposition": "terminal_consistent",
        "terminal_findings_count": 0,
        "locks_released": True,
        "staging_cleaned": True,
        "remaining_steps_empty": True,
        "recovery_idempotent": True,
        "ordinary_conflict_distinct": True,
        "integrity_pre_findings_count": 0,
        "integrity_pre_projection_clean": True,
        "integrity_stale_projection_rejected": True,
        "integrity_post_findings_count": 0,
        "integrity_post_projection_clean": True,
        "integrity_generation_advanced": True,
        "integrity_operation_completion_allowed": True,
        "integrity_privacy_bounded": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 installed recovery mismatch for {key}"
            )
    return payload

def _durable_reload_probe(
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
            _DURABLE_RELOAD_PROBE,
            str(workspace),
        ],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 fresh-process durable reload produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 fresh-process durable reload returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 fresh-process durable reload result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "core_rosters_readable": True,
        "actor_directory_reloaded": True,
        "actor_relationships_class_qualified": True,
        "event_current": True,
        "cross_participant_class": "journalism_p6_2026",
        "account_predecessor_exact": True,
        "account_successor_current": True,
        "review_history_pinned": True,
        "determination_history_pinned": True,
        "response_exact": True,
        "communication_exact": True,
        "support_process_current": True,
        "support_predecessor_exact": True,
        "support_successor_current": True,
        "implementation_count_exact": 2,
        "fidelity_exact": True,
        "follow_up_completed": True,
        "operation_terminal": True,
        "recovery_terminal_consistent": True,
        "recovery_staging_gone": True,
        "account_history_readable": True,
        "support_history_readable": True,
        "fresh_process_reload": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 fresh-process reload mismatch for {key}"
            )
    return payload

def _student_view_privacy_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [str(python), "-c", _STUDENT_VIEW_PRIVACY_PROBE, str(workspace)],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed student-view privacy probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed student-view privacy probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed student-view privacy result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "focal_class": "journalism_p6_2026",
        "work_count": 2,
        "corrected_account_present": True,
        "superseded_account_absent": True,
        "corrected_support_present": True,
        "superseded_support_absent": True,
        "unrelated_participants_absent": True,
        "communication_not_focally_inferred": True,
        "operational_internals_absent": True,
        "privacy_values_absent": True,
        "student_view_read_only": True,
        "accepted_policy": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 student-view privacy mismatch for {key}"
            )
    for key in ("entry_count", "manual_review_field_count", "withheld_field_count"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise Issue53AcceptanceError(
                f"Issue #53 student-view privacy count invalid for {key}"
            )
    return payload


def _teacher_reference_export_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [str(python), "-c", _TEACHER_REFERENCE_EXPORT_PROBE, str(workspace)],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed teacher-reference export probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed teacher-reference export probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed teacher-reference export result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "projection_purpose": "teacher_current",
        "source_inventory_exact": True,
        "render_deterministic": True,
        "provenance_exact": True,
        "artifact_path_exact": True,
        "provenance_path_exact": True,
        "history_verified": True,
        "artifact_immutable_after_success": True,
        "provenance_immutable_after_success": True,
        "canonical_sources_unchanged": True,
        "actor_directory_not_live_enrichment": True,
        "contact_point_data_absent": True,
        "unrelated_class_not_widened": True,
        "local_teacher_reference_only": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 teacher-reference export mismatch for {key}"
            )
    for key in ("manual_include_count", "manual_omit_count", "source_inventory_count"):
        value = payload.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise Issue53AcceptanceError(
                f"Issue #53 teacher-reference export count invalid for {key}"
            )
    return payload


def _read_only_surfaces_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [str(python), "-c", _READ_ONLY_SURFACES_PROBE, str(workspace)],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed read-only surfaces probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed read-only surfaces probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed read-only surfaces result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "student_view_zero_write": True,
        "attention_zero_write": True,
        "core_provider_zero_write": True,
        "export_history_zero_write": True,
        "historical_loads_zero_write": True,
        "whole_read_only_phase_zero_write": True,
        "student_work_count": 2,
        "attention_item_count": 0,
        "historical_account_status": "superseded",
        "historical_support_status": "superseded",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 read-only surfaces mismatch for {key}"
            )
    history_count = payload.get("verified_export_history_count")
    if (
        not isinstance(history_count, int)
        or isinstance(history_count, bool)
        or history_count < 1
    ):
        raise Issue53AcceptanceError(
            "Issue #53 read-only export history verification count is invalid"
        )
    return payload


def _deep_path_integration_probe(
    python: Path,
    *,
    cwd: Path,
    env: Mapping[str, str],
    workspace: Path,
) -> dict[str, object]:
    completed = _run(
        [str(python), "-c", _DEEP_PATH_INTEGRATION_PROBE, str(workspace)],
        cwd=cwd,
        env=env,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise Issue53AcceptanceError(
            "Issue #53 installed deep-path integration probe produced no result"
        )
    try:
        payload_raw = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise Issue53AcceptanceError(
            "Issue #53 installed deep-path integration probe returned invalid JSON"
        ) from exc
    if not isinstance(payload_raw, dict):
        raise Issue53AcceptanceError(
            "Issue #53 installed deep-path integration result was not an object"
        )

    payload = cast(dict[str, object], payload_raw)
    expected = {
        "one_deep_workspace": True,
        "guarded_replacement_history": True,
        "account_history_leaf_length": 40,
        "support_history_leaf_length": 40,
        "technical_history_bounded": True,
        "coordinated_staging_bounded": True,
        "recovery_staging_bounded": True,
        "staging_cleaned": True,
        "integrity_derived_v2": True,
        "teacher_export_in_deep_workspace": True,
        "legacy_writer_paths_absent": True,
        "inspection_read_only": True,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise Issue53AcceptanceError(
                f"Issue #53 deep-path integration mismatch for {key}"
            )

    workspace_length = payload.get("deep_workspace_length")
    if (
        not isinstance(workspace_length, int)
        or isinstance(workspace_length, bool)
        or workspace_length < TARGET_DEEP_WORKSPACE_LENGTH
    ):
        raise Issue53AcceptanceError(
            "Issue #53 deep-path integration lost representative workspace geometry"
        )
    for key in ("coordinated_staging_count", "recovery_staging_count"):
        staging_count = payload.get(key)
        if (
            not isinstance(staging_count, int)
            or isinstance(staging_count, bool)
            or staging_count < 1
        ):
            raise Issue53AcceptanceError(
                f"Issue #53 deep-path integration count invalid for {key}"
            )
    return payload

def smoke(portia_wheel: Path, core_wheel: Path) -> dict[str, object]:
    repository = Path(__file__).resolve().parents[1]
    no_fixture_bypass = _assert_no_fixture_bypass()
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
        recovery = _recovery_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        durable_reload = _durable_reload_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        student_view_privacy = _student_view_privacy_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        teacher_reference_export = _teacher_reference_export_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        read_only_surfaces = _read_only_surfaces_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        deep_path_integration = _deep_path_integration_probe(
            python,
            cwd=work,
            env=env,
            workspace=workspace,
        )
        if tuple(work.iterdir()):
            raise Issue53AcceptanceError(
                "Issue #53 acceptance polluted its empty working directory"
            )

        print("PASS no fixture bypass")
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
        print("PASS recovery")
        print("PASS integrity")
        print("PASS fresh reload")
        print("PASS privacy view")
        print("PASS teacher-reference export")
        print("PASS read-only surfaces")
        print("PASS deep path integration")

        return {
            "fixture_bypass_excluded": no_fixture_bypass[
                "fixture_bypass_excluded"
            ],
            "fixture_bypass_probe_count": no_fixture_bypass["probe_count"],
            "fixture_bypass_parsed_input_count": no_fixture_bypass[
                "parsed_input_count"
            ],
            "fixture_bypass_repository_instance_count": no_fixture_bypass[
                "repository_instance_count"
            ],
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
            "partial_error_exact": recovery["partial_error_exact"],
            "partial_accepted_steps": recovery["partial_accepted_steps"],
            "recovery_partial_state": recovery["partial_state"],
            "recovery_partial_disposition": recovery["partial_disposition"],
            "accepted_history_preserved": recovery[
                "accepted_history_preserved"
            ],
            "accepted_successor_preserved": recovery[
                "accepted_successor_preserved"
            ],
            "accepted_successor_not_republished": recovery[
                "accepted_successor_not_republished"
            ],
            "recovered_predecessor_superseded": recovery[
                "predecessor_superseded"
            ],
            "recovered_successor_current": recovery["successor_current"],
            "recovery_terminal_state": recovery["terminal_state"],
            "recovery_terminal_disposition": recovery[
                "terminal_disposition"
            ],
            "recovery_locks_released": recovery["locks_released"],
            "recovery_staging_cleaned": recovery["staging_cleaned"],
            "recovery_idempotent": recovery["recovery_idempotent"],
            "integrity_pre_findings_count": recovery[
                "integrity_pre_findings_count"
            ],
            "integrity_stale_projection_rejected": recovery[
                "integrity_stale_projection_rejected"
            ],
            "integrity_post_findings_count": recovery[
                "integrity_post_findings_count"
            ],
            "integrity_generation_advanced": recovery[
                "integrity_generation_advanced"
            ],
            "integrity_operation_completion_allowed": recovery[
                "integrity_operation_completion_allowed"
            ],
            "integrity_privacy_bounded": recovery[
                "integrity_privacy_bounded"
            ],
            "fresh_process_reload": durable_reload["fresh_process_reload"],
            "reload_core_rosters_readable": durable_reload[
                "core_rosters_readable"
            ],
            "reload_actor_relationships_class_qualified": durable_reload[
                "actor_relationships_class_qualified"
            ],
            "reload_event_current": durable_reload["event_current"],
            "reload_account_history_pinned": (
                durable_reload["review_history_pinned"]
                and durable_reload["determination_history_pinned"]
            ),
            "reload_support_successor_current": durable_reload[
                "support_successor_current"
            ],
            "reload_follow_up_completed": durable_reload[
                "follow_up_completed"
            ],
            "reload_operation_terminal": durable_reload[
                "operation_terminal"
            ],
            "reload_recovery_staging_gone": durable_reload[
                "recovery_staging_gone"
            ],
            "reload_technical_history_readable": (
                durable_reload["account_history_readable"]
                and durable_reload["support_history_readable"]
            ),
            "student_view_focal_class": student_view_privacy["focal_class"],
            "student_view_work_count": student_view_privacy["work_count"],
            "student_view_entry_count": student_view_privacy["entry_count"],
            "student_view_privacy_values_absent": student_view_privacy[
                "privacy_values_absent"
            ],
            "student_view_operational_internals_absent": student_view_privacy[
                "operational_internals_absent"
            ],
            "student_view_unrelated_participants_absent": student_view_privacy[
                "unrelated_participants_absent"
            ],
            "student_view_read_only": student_view_privacy[
                "student_view_read_only"
            ],
            "student_view_accepted_policy": student_view_privacy[
                "accepted_policy"
            ],
            "teacher_reference_projection_purpose": teacher_reference_export[
                "projection_purpose"
            ],
            "teacher_reference_manual_include_count": teacher_reference_export[
                "manual_include_count"
            ],
            "teacher_reference_manual_omit_count": teacher_reference_export[
                "manual_omit_count"
            ],
            "teacher_reference_source_inventory_count": teacher_reference_export[
                "source_inventory_count"
            ],
            "teacher_reference_source_inventory_exact": teacher_reference_export[
                "source_inventory_exact"
            ],
            "teacher_reference_render_deterministic": teacher_reference_export[
                "render_deterministic"
            ],
            "teacher_reference_provenance_exact": teacher_reference_export[
                "provenance_exact"
            ],
            "teacher_reference_artifact_path_exact": teacher_reference_export[
                "artifact_path_exact"
            ],
            "teacher_reference_provenance_path_exact": teacher_reference_export[
                "provenance_path_exact"
            ],
            "teacher_reference_history_verified": teacher_reference_export[
                "history_verified"
            ],
            "teacher_reference_artifact_immutable": teacher_reference_export[
                "artifact_immutable_after_success"
            ],
            "teacher_reference_provenance_immutable": teacher_reference_export[
                "provenance_immutable_after_success"
            ],
            "teacher_reference_canonical_sources_unchanged": teacher_reference_export[
                "canonical_sources_unchanged"
            ],
            "teacher_reference_actor_not_live_enriched": teacher_reference_export[
                "actor_directory_not_live_enrichment"
            ],
            "teacher_reference_contact_data_absent": teacher_reference_export[
                "contact_point_data_absent"
            ],
            "teacher_reference_unrelated_class_not_widened": teacher_reference_export[
                "unrelated_class_not_widened"
            ],
            "teacher_reference_local_only": teacher_reference_export[
                "local_teacher_reference_only"
            ],
            "read_only_student_view_zero_write": read_only_surfaces[
                "student_view_zero_write"
            ],
            "read_only_attention_zero_write": read_only_surfaces[
                "attention_zero_write"
            ],
            "read_only_core_provider_zero_write": read_only_surfaces[
                "core_provider_zero_write"
            ],
            "read_only_export_history_zero_write": read_only_surfaces[
                "export_history_zero_write"
            ],
            "read_only_historical_loads_zero_write": read_only_surfaces[
                "historical_loads_zero_write"
            ],
            "read_only_whole_phase_zero_write": read_only_surfaces[
                "whole_read_only_phase_zero_write"
            ],
            "deep_path_one_workspace": deep_path_integration[
                "one_deep_workspace"
            ],
            "deep_path_guarded_replacement_history": deep_path_integration[
                "guarded_replacement_history"
            ],
            "deep_path_technical_history_bounded": deep_path_integration[
                "technical_history_bounded"
            ],
            "deep_path_coordinated_staging_bounded": deep_path_integration[
                "coordinated_staging_bounded"
            ],
            "deep_path_recovery_staging_bounded": deep_path_integration[
                "recovery_staging_bounded"
            ],
            "deep_path_integrity_derived_v2": deep_path_integration[
                "integrity_derived_v2"
            ],
            "deep_path_teacher_export": deep_path_integration[
                "teacher_export_in_deep_workspace"
            ],
            "deep_path_legacy_writer_paths_absent": deep_path_integration[
                "legacy_writer_paths_absent"
            ],
            "deep_path_inspection_read_only": deep_path_integration[
                "inspection_read_only"
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
