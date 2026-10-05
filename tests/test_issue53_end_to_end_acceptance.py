from __future__ import annotations

import importlib.util
import os
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"


def _load_script():
    path = ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    spec = importlib.util.spec_from_file_location("issue53_end_to_end_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue53_foundation_pins_exact_current_artifact_boundary() -> None:
    smoke = _load_script()
    assert smoke.CORE_064_FILENAME == "pds_core-0.6.4-py3-none-any.whl"
    assert smoke.CORE_064_SHA256 == CORE_064_SHA256
    assert smoke.EXPECTED_CORE_VERSION == "0.6.4"
    assert smoke.EXPECTED_PORTIA_VERSION == "0.2.0"
    assert smoke.TARGET_DEEP_WORKSPACE_LENGTH == 119
    assert len(CORE_064_SHA256) == 64
    int(CORE_064_SHA256, 16)


def test_issue53_isolated_environment_removes_inherited_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke = _load_script()
    monkeypatch.setenv("PYTHONPATH", "source-shadow")
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", "implicit-workspace")
    monkeypatch.setenv("PATH", os.environ.get("PATH", ""))

    scripts = tmp_path / "venv" / ("Scripts" if os.name == "nt" else "bin")
    scripts.mkdir(parents=True)
    profile = tmp_path / "profile"
    env = smoke._isolated_environment(
        user_home=profile,
        scripts_directory=scripts,
    )

    assert "PYTHONPATH" not in {key.upper() for key in env}
    assert "PDS_WORKSPACE_ROOT" not in {key.upper() for key in env}
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["PIP_NO_INDEX"] == "1"
    assert Path(env["HOME"]) == profile
    assert Path(env["USERPROFILE"]) == profile
    assert Path(env["LOCALAPPDATA"]).is_dir()
    assert Path(env["APPDATA"]).is_dir()
    assert Path(env["XDG_CONFIG_HOME"]).is_dir()
    assert env["PATH"].split(os.pathsep)[0] == str(scripts)


def test_issue53_deep_workspace_helper_consumes_issue92_geometry(
    tmp_path: Path,
) -> None:
    smoke = _load_script()
    parent = tmp_path / "workspace-parent"
    parent.mkdir()
    workspace = smoke._deep_workspace_path(parent)

    assert workspace.parent == parent.resolve()
    assert workspace.name.startswith("pds-portia-i53-")
    assert len(str(workspace)) >= smoke.TARGET_DEEP_WORKSPACE_LENGTH


def test_issue53_foundation_probe_uses_public_core_workspace_service() -> None:
    smoke = _load_script()
    probe = smoke._FOUNDATION_PROBE
    assert "from pds_core.workspace import ensure_workspace_root" in probe
    assert "ensure_workspace_root(workspace, create=True)" in probe
    assert '"pds-core": metadata.version("pds-core")' in probe
    assert '"pds-portia": metadata.version("pds-portia")' in probe
    assert 'expected_pds = {"pds-core", "pds-portia"}' in probe


def test_issue53_foundation_reports_candidate_digest_without_rebuild() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert "candidate = _require_wheel(portia_wheel" in source
    assert "portia_digest = _sha256(candidate)" in source
    assert '"candidate_portia_sha256": portia_digest' in source
    assert '"--no-deps"' in source
    assert "str(candidate)" in source
    assert "python -m build" not in source


def test_issue53_smoke_script_is_in_strict_mypy_qualification() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    files = set(data["tool"]["mypy"]["files"])
    assert "scripts/smoke_test_issue53_end_to_end_wheel.py" in files


def test_issue53_core_setup_identifiers_match_representative_story() -> None:
    smoke = _load_script()
    assert smoke.SYNTHETIC_SCHOOL_YEAR == "2026-2027"
    assert smoke.PRIMARY_CLASS_ID == "eng10_p2_2026"
    assert smoke.SECONDARY_CLASS_ID == "journalism_p6_2026"
    assert smoke.COLLISION_STUDENT_ID == "student_shared_001"


def test_issue53_core_setup_probe_uses_public_core_authorities() -> None:
    smoke = _load_script()
    probe = smoke._CORE_SETUP_PROBE
    for marker in (
        "from pds_core.class_metadata import (",
        "create_class_metadata,",
        "write_class_metadata_for_class,",
        "from pds_core.classes import load_class_roster, write_class_roster",
        "from pds_core.rosters import create_roster, student_display_name",
        "from pds_core.school_years import get_active_school_year, open_school_year",
        "open_school_year(",
        "write_class_metadata_for_class(workspace, metadata_record)",
        "write_class_roster(workspace, primary_roster)",
        "write_class_roster(workspace, secondary_roster)",
    ):
        assert marker in probe


def test_issue53_core_setup_uses_portia_exact_class_qualified_identity() -> None:
    smoke = _load_script()
    probe = smoke._CORE_SETUP_PROBE
    for marker in (
        "from portia.identity.roster import CoreRosterResolver",
        "from portia.models.references import RosterStudentRef",
        "primary_ref = RosterStudentRef(",
        "secondary_ref = RosterStudentRef(",
        "resolver.resolve_reference(primary_ref)",
        "resolver.resolve_reference(secondary_ref)",
        "if primary_ref == secondary_ref:",
        "if primary_resolution.reference == secondary_resolution.reference:",
        "student_display_name(primary_student) != student_display_name(secondary_student)",
    ):
        assert marker in probe


def test_issue53_core_setup_extends_same_deep_workspace_after_foundation() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    foundation_index = source.index("foundation = _foundation_probe(")
    core_setup_index = source.index("core_setup = _core_setup_probe(")
    assert foundation_index < core_setup_index
    assert 'print("PASS Core setup")' in source
    assert '"active_school_year": core_setup["active_school_year"]' in source
    assert '"collision_reference_distinct": core_setup[' in source


def test_issue53_actor_setup_identifiers_are_stable_synthetic_values() -> None:
    smoke = _load_script()
    assert smoke.GUARDIAN_ACTOR_ID == "actr_guardian_001"
    assert smoke.COUNSELOR_ACTOR_ID == "actr_counselor_001"
    assert smoke.GUARDIAN_CONTACT_POINT_ID == "acp_guardian_email_001"


def test_issue53_actor_setup_uses_production_actor_directory_service() -> None:
    smoke = _load_script()
    probe = smoke._ACTOR_SETUP_PROBE
    for marker in (
        "ActorDirectoryService,",
        "service = ActorDirectoryService(workspace)",
        "service.create_actor(guardian)",
        "service.create_actor(counselor)",
        "service.create_actor_child(GUARDIAN_ACTOR_ID, contact)",
        "service.resolve_student_relationship(",
        "service.load_contact_point(",
        "require_current_use=True",
    ):
        assert marker in probe


def test_issue53_actor_setup_proves_workspace_scope_and_cross_class_links() -> None:
    smoke = _load_script()
    probe = smoke._ACTOR_SETUP_PROBE
    for marker in (
        'relative_parts[:2] != ("portia", "actors")',
        '"asrel_guardian_primary"',
        '"asrel_guardian_secondary"',
        "PRIMARY_CLASS_ID,",
        "SECONDARY_CLASS_ID,",
        "guardian_primary.roster_student.reference",
        "guardian_secondary.roster_student.reference",
        "service.list_relationships(GUARDIAN_ACTOR_ID)",
    ):
        assert marker in probe


def test_issue53_actor_setup_executes_identity_and_authority_negative_assertions() -> None:
    smoke = _load_script()
    probe = smoke._ACTOR_SETUP_PROBE
    for marker in (
        "RosterStudentNotFoundError",
        "roster_resolver.resolve(PRIMARY_CLASS_ID, GUARDIAN_ACTOR_ID)",
        "student_display_name(",
        "prohibited_authority_fields",
        '"legal_authority"',
        '"disclosure_authority"',
        '"decision_authority"',
        '"consent"',
        '"custody"',
    ):
        assert marker in probe


def test_issue53_actor_stage_follows_core_setup_in_same_installed_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    core_index = source.index("core_setup = _core_setup_probe(")
    actor_index = source.index("actor_setup = _actor_setup_probe(")
    assert core_index < actor_index
    assert 'print("PASS Actor setup")' in source
    assert '"actor_count": actor_setup["actor_count"]' in source
    assert '"cross_class_actor_reuse": actor_setup["cross_class_actor_reuse"]' in source


def test_issue53_event_evidence_identifiers_are_stable_synthetic_values() -> None:
    smoke = _load_script()
    assert smoke.PRIMARY_EVENT_ID == "evt_issue53_primary"
    assert smoke.PRIMARY_EVENT_PARTICIPANT_ID == "ep_issue53_primary"
    assert smoke.CROSS_EVENT_PARTICIPANT_ID == "ep_issue53_cross"
    assert smoke.EVENT_ACCOUNT_ID == "acct_issue53_cross_report"
    assert smoke.EVENT_OBSERVATION_ID == "obs_issue53_cross_observed"


def test_issue53_event_stage_uses_production_workflow_services() -> None:
    smoke = _load_script()
    probe = smoke._EVENT_EVIDENCE_PROBE
    for marker in (
        "EventWorkflowService,",
        "ParticipantWorkflowService,",
        "RoleWorkflowService,",
        "AccountWorkflowService,",
        "ObservationWorkflowService,",
        "draft = events.create(",
        "participants.create(work, record)",
        "roles.create(",
        "active = events.replace(",
        "accounts.create(work, account)",
        "observations.create(work, observation)",
    ):
        assert marker in probe


def test_issue53_event_stage_preserves_cross_class_participant_identity() -> None:
    smoke = _load_script()
    probe = smoke._EVENT_EVIDENCE_PROBE
    for marker in (
        '"class_id": SECONDARY_CLASS_ID',
        "cross_resolution.authority.reference.class_id != SECONDARY_CLASS_ID",
        "primary_resolution.authority.reference == cross_resolution.authority.reference",
        "current_event.record.class_id != PRIMARY_CLASS_ID",
        '"role_type": "present"',
    ):
        assert marker in probe


def test_issue53_event_stage_retains_conflict_without_automatic_judgment() -> None:
    smoke = _load_script()
    probe = smoke._EVENT_EVIDENCE_PROBE
    for marker in (
        "ReviewWorkflowService(workspace).list(work)",
        "ClassificationWorkflowService(workspace).list(work)",
        "HypothesisWorkflowService(workspace).list(work)",
        "DeterminationWorkflowService(workspace).list(work)",
        '"conflicting_evidence_retained": True',
        '"automatic_judgment_count": sum(automatic_judgments.values())',
        '"responsibility"',
        '"misconduct"',
        '"diagnosis"',
        '"causation"',
        '"effectiveness"',
    ):
        assert marker in probe


def test_issue53_event_stage_follows_actor_setup_in_same_workspace() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    actor_index = source.index("actor_setup = _actor_setup_probe(")
    event_index = source.index("event_evidence = _event_evidence_probe(")
    assert actor_index < event_index
    assert 'print("PASS Event evidence")' in source
    assert '"event_current": event_evidence["event_current"]' in source
    assert '"automatic_judgment_count": event_evidence[' in source


def test_issue53_judgment_correction_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.EVENT_REVIEW_ID == "rvw_issue53_evidence"
    assert smoke.EVENT_DETERMINATION_ID == "det_issue53_insufficient"
    assert smoke.CORRECTED_EVENT_ACCOUNT_ID == "acct_issue53_cross_corrected"


def test_issue53_judgment_stage_uses_bounded_production_services() -> None:
    smoke = _load_script()
    probe = smoke._JUDGMENT_CORRECTION_PROBE
    for marker in (
        "ReviewWorkflowService(workspace)",
        "DeterminationWorkflowService(workspace)",
        "reviews.create(work, review_record)",
        "determinations.create(work, determination_record)",
        '"outcome": {"kind": "insufficient_information"}',
        '"relation": "supporting"',
        '"relation": "contrary"',
        "ClassificationWorkflowService(workspace).list(work)",
        "HypothesisWorkflowService(workspace).list(work)",
    ):
        assert marker in probe


def test_issue53_correction_uses_public_coordinated_account_path() -> None:
    smoke = _load_script()
    probe = smoke._JUDGMENT_CORRECTION_PROBE
    for marker in (
        "correction = accounts.correct(",
        "expected=prior_fingerprint",
        'transition_id=CORRECTION_TRANSITION_ID',
        'operation_id=CORRECTION_OPERATION_ID',
        '"step_history"',
        '"step_successor"',
        '"step_transition"',
        '"step_evidence"',
        '"reason": "statement_corrected"',
    ):
        assert marker in probe


def test_issue53_correction_proves_exact_history_and_pinned_judgment() -> None:
    smoke = _load_script()
    probe = smoke._JUDGMENT_CORRECTION_PROBE
    for marker in (
        "work_storage_history_path(",
        "fingerprint_bytes(history_bytes) != prior_fingerprint",
        "predecessor_after.record.status != \"superseded\"",
        "successor_after.record.status != \"active\"",
        "review_after.fingerprint != review_fingerprint",
        "determination_after.fingerprint != determination_fingerprint",
        "review_account_ids != [ACCOUNT_ID]",
        "determination_account_ids != [ACCOUNT_ID]",
    ):
        assert marker in probe


def test_issue53_judgment_correction_follows_event_evidence_in_same_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    event_index = source.index("event_evidence = _event_evidence_probe(")
    judgment_index = source.index("judgment_correction = _judgment_correction_probe(")
    assert event_index < judgment_index
    assert 'print("PASS bounded judgment")' in source
    assert 'print("PASS correction history")' in source
    assert '"determination_outcome": judgment_correction[' in source
    assert '"review_history_pinned": judgment_correction[' in source


def test_issue53_response_communication_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.EVENT_RESPONSE_ID == "rsp_issue53_neutral_support"
    assert smoke.EVENT_COMMUNICATION_ID == "comm_issue53_guardian"


def test_issue53_response_uses_exact_review_and_determination_context() -> None:
    smoke = _load_script()
    probe = smoke._RESPONSE_COMMUNICATION_PROBE
    for marker in (
        "ResponseWorkflowService(workspace)",
        "responses.create(work, response)",
        "responses.require_current_use(response_exact_ref)",
        '"review_ref": review_ref.to_dict()',
        '"determination_ref": determination_ref.to_dict()',
        '"family": "environmental_or_instructional"',
        '"execution_state": "completed"',
    ):
        assert marker in probe


def test_issue53_communication_uses_exact_actor_contact_authority() -> None:
    smoke = _load_script()
    probe = smoke._RESPONSE_COMMUNICATION_PROBE
    for marker in (
        "CommunicationWorkflowService(workspace)",
        "ActorDirectoryService(workspace)",
        "ExactActorContactPointRef(",
        "require_current_use=True",
        '"actor_id": GUARDIAN_ACTOR_ID',
        '"contact_point_id": CONTACT_POINT_ID',
        '"method": {"kind": "email"}',
        '"participation": "not_established"',
        '"relation": "relates_to_response"',
    ):
        assert marker in probe


def test_issue53_communication_keeps_contact_delivery_participation_and_outcome_distinct() -> None:
    smoke = _load_script()
    probe = smoke._RESPONSE_COMMUNICATION_PROBE
    for marker in (
        '"act_state": "completed"',
        '"delivery"',
        '"read_status"',
        '"agreement"',
        '"consent"',
        '"outcome"',
        '"engagement_score"',
        "OutcomeWorkflowService(workspace)",
        "outcome_count_after = len(outcomes.list(work))",
        '"delivery_not_inferred": True',
        '"agreement_not_inferred": True',
        '"outcome_not_inferred": True',
    ):
        assert marker in probe


def test_issue53_response_communication_follows_correction_in_same_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    correction_index = source.index(
        "judgment_correction = _judgment_correction_probe("
    )
    response_index = source.index(
        "response_communication = _response_communication_probe("
    )
    assert correction_index < response_index
    assert 'print("PASS Response")' in source
    assert 'print("PASS Communication")' in source
    assert '"recipient_participation": response_communication[' in source
    assert '"outcome_not_inferred": response_communication[' in source


def test_issue53_support_process_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.SUPPORT_PROCESS_ID == "sup_issue53_support"
    assert smoke.SUPPORTED_SUPPORT_PARTICIPANT_ID == "spp_issue53_student"
    assert smoke.COUNSELOR_SUPPORT_PARTICIPANT_ID == "spp_issue53_counselor"


def test_issue53_support_process_uses_response_handoff_bootstrap() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PROCESS_PROBE
    for marker in (
        "SupportProcessWorkflowService(workspace)",
        "SupportProcessParticipantWorkflowService(workspace)",
        '"kind": "response_handoff"',
        '"record_ref": response_ref.to_dict()',
        "root_created = root_service.create(root_record)",
        "root_service.transition_lifecycle(",
        '"step_history"',
        '"step_transition"',
        '"step_work"',
    ):
        assert marker in probe


def test_issue53_support_process_preserves_exact_supported_student_and_actor() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PROCESS_PROBE
    for marker in (
        '"class_id": SECONDARY_CLASS_ID',
        '"student_id": COLLISION_STUDENT_ID',
        '"kind": "supported_person"',
        '"actor_id": COUNSELOR_ACTOR_ID',
        '"kind": "provider_or_collaborator"',
        '"kind": "coordinator"',
        "supported_current.authority.reference.class_id != SECONDARY_CLASS_ID",
        "counselor_current.authority.record.logical_id != COUNSELOR_ACTOR_ID",
    ):
        assert marker in probe


def test_issue53_support_bootstrap_does_not_manufacture_plan_records() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PROCESS_PROBE
    for marker in (
        "SupportNeedWorkflowService(workspace).list(support_work)",
        "SupportGoalWorkflowService(workspace).list(support_work)",
        "SupportWorkflowService(workspace).list(support_work)",
        '"planning_not_inferred": all(value == 0',
    ):
        assert marker in probe


def test_issue53_support_process_follows_response_communication_in_same_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    response_index = source.index(
        "response_communication = _response_communication_probe("
    )
    support_index = source.index("support_process = _support_process_probe(")
    assert response_index < support_index
    assert 'print("PASS Support Process")' in source
    assert '"support_process_current": support_process[' in source
    assert '"response_handoff_exact": support_process[' in source


def test_issue53_support_planning_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.SUPPORT_NEED_ID == "spn_issue53_access"
    assert smoke.SUPPORT_GOAL_ID == "spg_issue53_access"
    assert smoke.SUPPORT_PLAN_ID == "spt_issue53_access"


def test_issue53_support_planning_uses_production_services_and_exact_links() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PLANNING_PROBE
    for marker in (
        "SupportNeedWorkflowService(workspace)",
        "SupportGoalWorkflowService(workspace)",
        "SupportWorkflowService(workspace)",
        "need_service.create(work, need)",
        "goal_service.create(work, goal)",
        "support_service.create(work, support)",
        '"record_id": NEED_ID',
        '"record_id": GOAL_ID',
        '"record_id": COUNSELOR_PARTICIPANT_ID',
        "support_service.require_current_use(support_ref)",
    ):
        assert marker in probe


def test_issue53_support_planning_targets_same_exact_supported_participant() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PLANNING_PROBE
    for marker in (
        'SUPPORTED_PARTICIPANT_ID = "spp_issue53_student"',
        '"kind": "support_process_participant"',
        '"record_id": SUPPORTED_PARTICIPANT_ID',
        "need_current.record.field(\"target\") != participant_target",
        "goal_current.record.field(\"target\") != participant_target",
        "support_current.record.field(\"target\") != participant_target",
    ):
        assert marker in probe


def test_issue53_support_process_enters_active_workflow_state_without_new_identity() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PLANNING_PROBE
    for marker in (
        'root_active_wire["workflow_state"] = "active"',
        "root_service.transition_workflow_state(",
        "expected=root_before.fingerprint",
        'root_after.record.status != "active"',
        'root_after.record.logical_id != SUPPORT_PROCESS_ID',
    ):
        assert marker in probe


def test_issue53_support_planning_does_not_infer_execution_or_outcome() -> None:
    smoke = _load_script()
    probe = smoke._SUPPORT_PLANNING_PROBE
    for marker in (
        "ImplementationWorkflowService(workspace).list(work)",
        "FidelityWorkflowService(workspace).list(work)",
        "FollowUpWorkflowService(workspace).list(work)",
        "OutcomeWorkflowService(workspace).list(work)",
        '"diagnosis"',
        '"progress"',
        '"effectiveness"',
        '"outcome"',
        '"downstream_not_inferred": all(',
    ):
        assert marker in probe


def test_issue53_support_planning_follows_support_bootstrap_in_same_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    bootstrap_index = source.index("support_process = _support_process_probe(")
    planning_index = source.index("support_planning = _support_planning_probe(")
    assert bootstrap_index < planning_index
    assert 'print("PASS Support planning")' in source
    assert '"support_plan_state": support_planning["support_plan_state"]' in source
    assert '"downstream_not_inferred": support_planning[' in source


def test_issue53_implementation_fidelity_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.IMPLEMENTATION_ONE_ID == "imp_issue53_access_001"
    assert smoke.IMPLEMENTATION_TWO_ID == "imp_issue53_access_002"
    assert smoke.FIDELITY_ID == "fid_issue53_access"


def test_issue53_records_two_distinct_exact_implementation_occurrences() -> None:
    smoke = _load_script()
    probe = smoke._IMPLEMENTATION_FIDELITY_PROBE
    for marker in (
        "ImplementationWorkflowService(workspace)",
        "implementation_service.create(work, implementation_one)",
        "implementation_service.create(work, implementation_two)",
        "implementation_reference(work, IMPLEMENTATION_ONE_ID)",
        "implementation_reference(work, IMPLEMENTATION_TWO_ID)",
        "current_one.record.logical_id == current_two.record.logical_id",
        "current_one.path == current_two.path",
        '"execution_state": "completed"',
    ):
        assert marker in probe


def test_issue53_implementations_preserve_exact_plan_target_and_provider() -> None:
    smoke = _load_script()
    probe = smoke._IMPLEMENTATION_FIDELITY_PROBE
    for marker in (
        '"record_kind": "support"',
        '"record_id": SUPPORT_ID',
        '"record_id": SUPPORTED_PARTICIPANT_ID',
        '"record_id": COUNSELOR_PARTICIPANT_ID',
        "current_one.record.field(\"plan_ref\") != plan_ref",
        "current_two.record.field(\"actual_target\") != participant_target",
        "current_two.record.field(\"implementation_provider\") != participant_provider",
    ):
        assert marker in probe


def test_issue53_fidelity_uses_exact_two_implementation_scope_and_basis() -> None:
    smoke = _load_script()
    probe = smoke._IMPLEMENTATION_FIDELITY_PROBE
    for marker in (
        "FidelityWorkflowService(workspace)",
        '"kind": "implementation_set"',
        '"kind": "implementation_records"',
        '"result": "as_planned"',
        "fidelity_service.create(work, fidelity)",
        "tuple(scope_refs) != tuple(implementation_refs)",
        "tuple(basis_refs) != tuple(implementation_refs)",
    ):
        assert marker in probe


def test_issue53_fidelity_does_not_infer_effectiveness_or_outcome() -> None:
    smoke = _load_script()
    probe = smoke._IMPLEMENTATION_FIDELITY_PROBE
    for marker in (
        '"effectiveness"',
        '"outcome"',
        '"progress"',
        '"success"',
        '"compliance"',
        '"provider_competence"',
        "OutcomeWorkflowService(workspace)",
        "outcome_count != 0",
        '"effectiveness_not_inferred": True',
        '"outcome_not_inferred": outcome_count == 0',
    ):
        assert marker in probe


def test_issue53_execution_history_does_not_mutate_plan_or_process() -> None:
    smoke = _load_script()
    probe = smoke._IMPLEMENTATION_FIDELITY_PROBE
    for marker in (
        "support_before_fingerprint = support_before.fingerprint",
        "support_after.fingerprint != support_before_fingerprint",
        "root_after.fingerprint != root_before.fingerprint",
        '"support_plan_unchanged":',
        '"support_process_unchanged":',
    ):
        assert marker in probe


def test_issue53_implementation_fidelity_follows_support_planning() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    planning_index = source.index("support_planning = _support_planning_probe(")
    execution_index = source.index(
        "implementation_fidelity = _implementation_fidelity_probe("
    )
    assert planning_index < execution_index
    assert 'print("PASS Implementation history")' in source
    assert 'print("PASS Fidelity")' in source
    assert '"implementation_count": implementation_fidelity[' in source
    assert '"fidelity_result": implementation_fidelity[' in source


def test_issue53_follow_up_identifier_is_stable() -> None:
    smoke = _load_script()
    assert smoke.FOLLOW_UP_ID == "fup_issue53_review"


def test_issue53_follow_up_is_scheduled_then_completed_through_production_workflow() -> None:
    smoke = _load_script()
    probe = smoke._FOLLOW_UP_ATTENTION_PROBE
    for marker in (
        "FollowUpWorkflowService(workspace)",
        '"workflow_state": "scheduled"',
        '"kind": "exact_time"',
        '"at": PLANNED_AT',
        "follow_up_service.create(work, scheduled_record)",
        'completed_wire["workflow_state"] = "completed"',
        'completed_wire["completed_at"] = COMPLETED_AT',
        "follow_up_service.transition_workflow_state(",
        "expected=scheduled_current.fingerprint",
    ):
        assert marker in probe


def test_issue53_follow_up_review_pins_support_and_fidelity_and_disposition() -> None:
    smoke = _load_script()
    probe = smoke._FOLLOW_UP_ATTENTION_PROBE
    for marker in (
        '"record_kind": "support"',
        '"record_id": SUPPORT_ID',
        '"record_kind": "fidelity"',
        '"record_id": FIDELITY_ID',
        '"role": "reviewed"',
        '"kind": "continue_current_support"',
        "tuple(related_records) != (reviewed_support, reviewed_fidelity)",
    ):
        assert marker in probe


def test_issue53_native_attention_transitions_due_to_clear_on_completion() -> None:
    smoke = _load_script()
    probe = smoke._FOLLOW_UP_ATTENTION_PROBE
    for marker in (
        "AttentionQueryService(workspace)",
        "PortiaAttentionQuery(",
        'attention_codes=(',
        '"portia_follow_up_due"',
        '"portia_follow_up_overdue"',
        "attention_service.query(attention_query)",
        'attention_item.code != "portia_follow_up_due"',
        "after_attention.items",
        '"attention_after_count": len(after_attention.items)',
    ):
        assert marker in probe


def test_issue53_attention_queries_are_zero_write() -> None:
    smoke = _load_script()
    probe = smoke._FOLLOW_UP_ATTENTION_PROBE
    for marker in (
        "def snapshot(root):",
        "before_attention_snapshot = snapshot(workspace)",
        "after_attention_snapshot = snapshot(workspace)",
        "after_completion_snapshot = snapshot(workspace)",
        "after_post_query_snapshot = snapshot(workspace)",
        '"attention_queries_zero_write": True',
    ):
        assert marker in probe


def test_issue53_completed_follow_up_does_not_infer_outcome_or_complete_process() -> None:
    smoke = _load_script()
    probe = smoke._FOLLOW_UP_ATTENTION_PROBE
    for marker in (
        "OutcomeWorkflowService(workspace)",
        "if outcomes:",
        "root_after.fingerprint != root_before.fingerprint",
        'root_after.record.field("workflow_state") != "active"',
        '"outcome"',
        '"effectiveness"',
        '"progress"',
        '"causation"',
        '"process_completion_not_inferred":',
    ):
        assert marker in probe


def test_issue53_follow_up_attention_follows_fidelity_in_same_story() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    fidelity_index = source.index(
        "implementation_fidelity = _implementation_fidelity_probe("
    )
    follow_up_index = source.index(
        "follow_up_attention = _follow_up_attention_probe("
    )
    assert fidelity_index < follow_up_index
    assert 'print("PASS Follow-Up")' in source
    assert 'print("PASS attention transition")' in source
    assert '"follow_up_workflow_state": follow_up_attention[' in source
    assert '"attention_after_count": follow_up_attention[' in source


def test_issue53_core_provider_uses_core_metadata_and_diagnostics() -> None:
    smoke = _load_script()
    probe = smoke._CORE_PROVIDER_PROBE
    for marker in (
        "inspect_core_provider_entry_points(",
        'provider_kind="module_operations"',
        'diagnose_core_providers(provider_kind="module_operations")',
        "metadata_row.entry_point_target",
        '"portia.pds_operations:get_module_operations_profile"',
        'diagnostic.code != "provider.valid"',
        'diagnostic.core_compatibility != "passed"',
        "profile = diagnostic.validated_profile",
    ):
        assert marker in probe


def test_issue53_core_provider_invokes_readiness_and_attention_through_core() -> None:
    smoke = _load_script()
    probe = smoke._CORE_PROVIDER_PROBE
    for marker in (
        "ModuleOperationsRequest(",
        "invoke_module_operations(profile, request)",
        'readiness.code != "module_operations.evaluated"',
        "readiness.report.ready is not True",
        'attention.code != "module_operations.evaluated"',
        'attention.report.evaluation != "evaluated"',
    ):
        assert marker in probe


def test_issue53_core_provider_boundary_is_zero_write() -> None:
    smoke = _load_script()
    probe = smoke._CORE_PROVIDER_PROBE
    for marker in (
        "baseline = snapshot(workspace)",
        "after_metadata = snapshot(workspace)",
        "after_diagnostics = snapshot(workspace)",
        "after_invocation = snapshot(workspace)",
        '"provider_zero_write": after_invocation == baseline',
        '"metadata_zero_write": after_metadata == baseline',
        '"diagnostics_zero_write": after_diagnostics == baseline',
    ):
        assert marker in probe


def test_issue53_core_provider_projection_is_privacy_minimal() -> None:
    smoke = _load_script()
    probe = smoke._CORE_PROVIDER_PROBE
    for marker in (
        'if set(shared["readiness"]) != {"evaluation", "ready", "notices"}',
        'if set(shared["attention"]) != {"evaluation", "summaries", "notices"}',
        '"student_shared_001"',
        '"Shared Synthetic"',
        '"guardian.issue53@example.invalid"',
        '"journalism_p6_2026"',
        '"fup_issue53_review"',
        "str(workspace)",
        '"workspace_root"',
        '"record_body"',
        '"shared_projection_privacy_bounded": True',
    ):
        assert marker in probe


def test_issue53_core_provider_follows_follow_up_attention_transition() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    follow_up_index = source.index(
        "follow_up_attention = _follow_up_attention_probe("
    )
    provider_index = source.index("core_provider = _core_provider_probe(")
    assert follow_up_index < provider_index
    assert 'print("PASS provider boundary")' in source
    assert '"provider_zero_write": core_provider["provider_zero_write"]' in source
    assert '"shared_projection_privacy_bounded": core_provider[' in source


def test_issue53_stale_conflict_uses_real_support_plan_state_update() -> None:
    smoke = _load_script()
    probe = smoke._STALE_CONFLICT_PROBE
    for marker in (
        "SupportWorkflowService(workspace)",
        "service.require_current_use(reference)",
        'paused_wire["plan_state"] = "paused"',
        "service.transition_plan_state(",
        "expected=stale_fingerprint",
        'stale_wire["plan_state"] = "completed"',
    ):
        assert marker in probe


def test_issue53_stale_conflict_requires_exact_portia_conflict_error() -> None:
    smoke = _load_script()
    probe = smoke._STALE_CONFLICT_PROBE
    for marker in (
        "from portia.storage.errors import PortiaConflictError",
        "except PortiaConflictError:",
        '"stale_conflict_raised": conflict_raised',
        '"stale_fingerprint_obsolete": stale_fingerprint != accepted_fingerprint',
    ):
        assert marker in probe


def test_issue53_stale_conflict_is_byte_for_byte_zero_mutation() -> None:
    smoke = _load_script()
    probe = smoke._STALE_CONFLICT_PROBE
    for marker in (
        "before_conflict = snapshot(workspace)",
        "after_conflict = snapshot(workspace)",
        "if after_conflict != before_conflict:",
        "accepted_bytes = accepted.path.read_bytes()",
        "current.path.read_bytes() != accepted_bytes",
        '"workspace_snapshot_preserved": after_conflict == before_conflict',
        '"canonical_bytes_preserved": current.path.read_bytes() == accepted_bytes',
    ):
        assert marker in probe


def test_issue53_stale_conflict_does_not_fabricate_recovery_evidence() -> None:
    smoke = _load_script()
    probe = smoke._STALE_CONFLICT_PROBE
    for marker in (
        "from portia.storage.paths import operations_root",
        "operations_before = operation_artifacts(workspace)",
        "operations_after = operation_artifacts(workspace)",
        "if operations_after != operations_before:",
        '"operation_artifacts_preserved": operations_after == operations_before',
        '"ordinary_conflict_not_recovery": True',
    ):
        assert marker in probe


def test_issue53_stale_conflict_follows_core_provider_boundary() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    provider_index = source.index("core_provider = _core_provider_probe(")
    conflict_index = source.index("stale_conflict = _stale_conflict_probe(")
    assert provider_index < conflict_index
    assert 'print("PASS conflict")' in source
    assert '"stale_conflict_raised": stale_conflict[' in source
    assert '"ordinary_conflict_not_recovery": stale_conflict[' in source


def test_issue53_recovery_identifiers_are_stable() -> None:
    smoke = _load_script()
    assert smoke.RECOVERED_SUPPORT_ID == "spt_issue53_access_corrected"
    assert smoke.RECOVERY_TRANSITION_ID == "lct_issue53_support_corrected"
    assert smoke.RECOVERY_OPERATION_ID == "op_issue53_support_recovery"


def test_issue53_recovery_uses_real_support_correction_fault_hook() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "SupportWorkflowService(workspace)",
        '"reason": "strategy_corrected"',
        "service.correct(",
        "operation_id=OPERATION_ID",
        "fault_hook=fail_after_successor",
        'checkpoint == "after_publish" and step_id == "step_successor"',
        "except PortiaOperationPartialCommitError as exc:",
        'partial_error.accepted_steps != ("step_history", "step_successor")',
    ):
        assert marker in probe


def test_issue53_partial_recovery_evidence_is_exact() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        'partial_data.get("state") != "recovering"',
        '"step_transition"',
        '"step_action"',
        "RecoveryWorkflowService(workspace)",
        "assessment = recovery.assess(OPERATION_ID)",
        'assessment.disposition != "resume"',
        "assessment.findings",
        'evidence["step_successor"].disposition != "accepted"',
        'evidence["step_transition"].disposition != "not_written"',
    ):
        assert marker in probe


def test_issue53_recovery_resumes_only_remaining_exact_writes() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "accepted_before_recovery = {",
        "recovery.resume_incomplete(",
        "expected_pointer=partial_current.pointer_fingerprint",
        "history_path.read_bytes() != accepted_before_recovery",
        "successor_after_recovery.path.read_bytes()",
        "successor_after_recovery.path.stat().st_mtime_ns",
        'predecessor_after.record.status != "superseded"',
        "fingerprint_bytes(path.read_bytes())",
    ):
        assert marker in probe


def test_issue53_recovery_releases_locks_cleans_staging_and_is_idempotent() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "held_lock_paths",
        "staged_paths",
        "if any(path.exists() for path in held_lock_paths):",
        "if any(path.exists() for path in staged_paths):",
        'terminal_data.get("state") != "completed"',
        "before_idempotent_recovery = snapshot(workspace)",
        "repeated = recovery.resume_incomplete(",
        "after_idempotent_recovery = snapshot(workspace)",
        "before_idempotent_recovery != after_idempotent_recovery",
    ):
        assert marker in probe


def test_issue53_recovery_follows_ordinary_conflict_as_distinct_boundary() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    conflict_index = source.index("stale_conflict = _stale_conflict_probe(")
    recovery_index = source.index("recovery = _recovery_probe(")
    assert conflict_index < recovery_index
    assert 'print("PASS recovery")' in source
    assert '"partial_error_exact": recovery["partial_error_exact"]' in source
    assert '"recovery_idempotent": recovery["recovery_idempotent"]' in source


def test_issue53_integrity_evaluates_recovering_operation_without_false_error() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "IntegrityWorkflowService(workspace)",
        "integrity.evaluate_operation_persistence(OPERATION_ID)",
        "pre_integrity_evaluation.findings",
        "integrity.project_operation_persistence_findings(",
        "integrity.current_findings(integrity_scope)",
        "pre_generation_id",
    ):
        assert marker in probe


def test_issue53_integrity_projection_turns_stale_after_recovery() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "stale_projection_rejected = False",
        "except PortiaRecoveryRequiredError:",
        "pre-recovery Integrity projection remained falsely fresh after recovery",
        "post_generation_id == pre_generation_id",
        '"integrity_stale_projection_rejected": stale_projection_rejected',
        '"integrity_generation_advanced":',
    ):
        assert marker in probe


def test_issue53_integrity_rebuilds_clean_completed_operation_projection() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "post_integrity_evaluation = integrity.evaluate_operation_persistence(",
        "post_integrity_projection = integrity.project_operation_persistence_findings(",
        "post_integrity_evaluation.findings",
        "post_integrity_projection.findings",
        "integrity.require_operation_completion(OPERATION_ID)",
        '"integrity_operation_completion_allowed": True',
    ):
        assert marker in probe


def test_issue53_integrity_diagnostics_remain_privacy_bounded() -> None:
    smoke = _load_script()
    probe = smoke._RECOVERY_PROBE
    for marker in (
        "pre_integrity_serialized = json.dumps(",
        "post_integrity_serialized = json.dumps(",
        '"Shared Synthetic"',
        '"Synthetic Counselor"',
        '"guardian.issue53@example.invalid"',
        '"Synthetic classroom material-location discrepancy."',
        '"blue marker"',
        '"integrity_privacy_bounded": True',
    ):
        assert marker in probe


def test_issue53_integrity_stage_follows_recovery_stage() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert 'print("PASS recovery")' in source
    assert 'print("PASS integrity")' in source
    assert source.index('print("PASS recovery")') < source.index(
        'print("PASS integrity")'
    )
    assert '"integrity_pre_findings_count": recovery[' in source
    assert '"integrity_operation_completion_allowed": recovery[' in source


def test_issue53_fresh_reload_is_a_separate_installed_process() -> None:
    _load_script()
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert "_DURABLE_RELOAD_PROBE = r" in source
    runner_index = source.index("def _durable_reload_probe(")
    smoke_index = source.index(
        "def smoke(portia_wheel: Path, core_wheel: Path)"
    )
    runner = source[runner_index:smoke_index]
    assert "_run(" in runner
    assert '"-c"' in runner
    assert "_DURABLE_RELOAD_PROBE" in runner
    assert "workspace" in runner


def test_issue53_fresh_reload_covers_core_actors_and_event_identity() -> None:
    smoke = _load_script()
    probe = smoke._DURABLE_RELOAD_PROBE
    for marker in (
        "load_class_roster(workspace, PRIMARY_CLASS_ID)",
        "load_class_roster(workspace, SECONDARY_CLASS_ID)",
        "ActorDirectoryService(workspace)",
        "resolve_student_relationship(",
        "EventWorkflowService(workspace)",
        "ParticipantWorkflowService(workspace)",
        "participants.resolve_exact(",
        "cross_authority.reference.class_id != SECONDARY_CLASS_ID",
    ):
        assert marker in probe


def test_issue53_fresh_reload_preserves_corrections_and_historical_pins() -> None:
    smoke = _load_script()
    probe = smoke._DURABLE_RELOAD_PROBE
    for marker in (
        "accounts.load_exact(original_account_ref)",
        "accounts.require_current_use(corrected_account_ref)",
        'original_account.record.status != "superseded"',
        "review_account_ids != [ACCOUNT_ID]",
        "determination_account_ids != [ACCOUNT_ID]",
        "supports.load_exact(support_reference(support_work, SUPPORT_ID))",
        "supports.require_current_use(",
        'corrected_support.record.field("plan_state") != "paused"',
    ):
        assert marker in probe


def test_issue53_fresh_reload_preserves_action_and_support_execution_records() -> None:
    smoke = _load_script()
    probe = smoke._DURABLE_RELOAD_PROBE
    for marker in (
        "responses.require_current_use(",
        "communications.require_current_use(",
        "support_roots.require_current_use(support_work)",
        "repository.list_work_records(",
        '"implementation"',
        "implementation_ids !=",
        "IMPLEMENTATION_ONE_ID",
        "IMPLEMENTATION_TWO_ID",
        '"fidelity"',
        "FIDELITY_ID",
        '"follow_up"',
        "FOLLOW_UP_ID",
        '"workflow_state") != "completed"',
    ):
        assert marker in probe


def test_issue53_fresh_reload_proves_terminal_recovery_and_no_staging() -> None:
    smoke = _load_script()
    probe = smoke._DURABLE_RELOAD_PROBE
    for marker in (
        "journals.load_current(RECOVERY_OPERATION_ID)",
        'terminal_data.get("state") != "completed"',
        "recovery.assess(RECOVERY_OPERATION_ID)",
        '"terminal_consistent"',
        "staging_path_for(",
        "if staging.exists() or staging.is_symlink():",
        '"recovery_staging_gone": True',
    ):
        assert marker in probe


def test_issue53_fresh_reload_reads_technical_history_from_journal_authority() -> None:
    smoke = _load_script()
    probe = smoke._DURABLE_RELOAD_PROBE
    for marker in (
        "def verify_technical_history(operation_id):",
        '"step_history"',
        'ContentFingerprint.from_dict(intended.get("fingerprint"))',
        "resolve_workspace_relative(workspace, destination)",
        "read_bytes(path)",
        "fingerprint_bytes(content) != expected",
        "ACCOUNT_CORRECTION_OPERATION_ID",
        "RECOVERY_OPERATION_ID",
    ):
        assert marker in probe


def test_issue53_fresh_reload_follows_integrity_and_has_exact_stage_label() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    recovery_index = source.index("recovery = _recovery_probe(")
    reload_index = source.index("durable_reload = _durable_reload_probe(")
    assert recovery_index < reload_index
    assert 'print("PASS integrity")' in source
    assert 'print("PASS fresh reload")' in source
    assert source.index('print("PASS integrity")') < source.index(
        'print("PASS fresh reload")'
    )
    assert '"fresh_process_reload": durable_reload[' in source


def test_issue53_student_view_uses_exact_cross_class_focal_scope() -> None:
    smoke = _load_script()
    probe = smoke._STUDENT_VIEW_PRIVACY_PROBE
    for marker in (
        "StudentTimelineService(workspace).generate(query)",
        "class_id=SECONDARY_CLASS_ID",
        "student_id=COLLISION_STUDENT_ID",
        "allowed_class_ids=(PRIMARY_CLASS_ID,)",
        "allowed_works=(event_work, support_work)",
        "exact_works=(event_work, support_work)",
        "result.discovery.resolved_students != (focal_student,)",
    ):
        assert marker in probe


def test_issue53_student_view_is_snapshot_proven_read_only() -> None:
    smoke = _load_script()
    probe = smoke._STUDENT_VIEW_PRIVACY_PROBE
    for marker in (
        "before = snapshot(workspace)",
        "result = StudentTimelineService(workspace).generate(query)",
        "after = snapshot(workspace)",
        "if before != after:",
        '"student_view_read_only": before == after',
    ):
        assert marker in probe


def test_issue53_student_view_respects_currentness() -> None:
    smoke = _load_script()
    probe = smoke._STUDENT_VIEW_PRIVACY_PROBE
    for marker in (
        "ORIGINAL_ACCOUNT_ID in source_ids",
        "CORRECTED_ACCOUNT_ID not in source_ids",
        "ORIGINAL_SUPPORT_ID in source_ids",
        "CORRECTED_SUPPORT_ID not in source_ids",
        '"superseded_account_absent": ORIGINAL_ACCOUNT_ID not in source_ids',
        '"superseded_support_absent": ORIGINAL_SUPPORT_ID not in source_ids',
    ):
        assert marker in probe


def test_issue53_student_view_privacy_dispositions_carry_no_unsafe_values() -> None:
    smoke = _load_script()
    probe = smoke._STUDENT_VIEW_PRIVACY_PROBE
    for marker in (
        'content_field.disposition != "requires_manual_review"',
        "content_field.value is not None",
        'summary_field.disposition != "withheld"',
        "summary_field.value is not None",
        'strategy_field.disposition != "requires_manual_review"',
        "strategy_field.value is not None",
        'field.disposition != "included" and field.value is not None',
    ):
        assert marker in probe


def test_issue53_student_view_excludes_unrelated_people_and_operational_state() -> None:
    smoke = _load_script()
    probe = smoke._STUDENT_VIEW_PRIVACY_PROBE
    for marker in (
        '"ep_issue53_primary"',
        '"ep_issue53_guardian"',
        '"spp_issue53_counselor"',
        "COMMUNICATION_ID",
        '"guardian.issue53@example.invalid"',
        '"Shared Synthetic"',
        '"Synthetic Counselor"',
        '"student_primary_002"',
        '"student_secondary_002"',
        '"blue marker"',
        '"operation_journal"',
        '"integrity_finding"',
        "str(workspace)",
    ):
        assert marker in probe


def test_issue53_student_view_stage_follows_fresh_reload() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert source.index("durable_reload = _durable_reload_probe(") < source.index(
        "student_view_privacy = _student_view_privacy_probe("
    )
    assert 'print("PASS privacy view")' in source
    assert '"student_view_read_only": student_view_privacy[' in source
def test_issue53_teacher_reference_export_uses_production_issue51_pipeline() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        'TeacherReferenceExportScope("teacher_current", support_work)',
        "TeacherReferenceScopeDiscoveryService(",
        "TeacherReferenceProjectionService(",
        "TeacherReferenceSourceInventoryService(",
        "TeacherReferenceExportPreparationService(",
        "TeacherReferenceExportExecutionService(",
        "TeacherReferenceExportHistoryService(workspace).list_for_work(support_work)",
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_requires_explicit_manual_include_and_omit() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        'pending.manual_review.status != "pending"',
        'item.source_ref == support_work and item.field_name == "summary"',
        'resolution = "include_exact"',
        'item.source_ref == support_work and item.field_name == "initiation"',
        'resolution = "omit"',
        "projection_service.resolve_manual_review(",
        'decision.manual_review.status != "resolved"',
        '"manual_include_count": sum(',
        '"manual_omit_count": sum(',
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_binds_exact_inventory_and_deterministic_render() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        "inventory_identities != contributing_identities",
        "prepared = prepare()",
        "repeated = prepare()",
        "prepared.preparation_digest != repeated.preparation_digest",
        "prepared.artifact_bytes != repeated.artifact_bytes",
        "prepared.provenance_bytes != repeated.provenance_bytes",
        "prepared.inventory.to_dict() != inventory_wire",
        "provenance_wire.get(\"source_inventory\") != inventory_wire",
        "provenance_wire.get(\"projection_decision_digest\")",
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_privacy_uses_frozen_work_owned_sources() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        '"Synthetic Counselor" not in artifact_text',
        "GUARDIAN_EMAIL",
        "GUARDIAN_CONTACT_POINT_ID",
        "GUARDIAN_ACTOR_ID",
        "COUNSELOR_ACTOR_ID",
        "SECONDARY_CLASS_ID",
        "EVENT_ID",
        "ORIGINAL_SUPPORT_ID",
        "stored.fingerprint != expected_fingerprint",
        '"actor_directory_not_live_enrichment":',
        '"contact_point_data_absent":',
        '"unrelated_class_not_widened":',
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_executes_exact_reviewed_candidate() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        "confirmation=TEACHER_REFERENCE_CONFIRMATION",
        "confirmed_preparation_digest=prepared.preparation_digest",
        "confirmed_at=CONFIRMED_AT",
        "isinstance(result, TeacherReferenceExportExecutionSuccess)",
        'expected_artifact_path = f"portia/exports/{prepared.export_id}/artifact.html"',
        'expected_provenance_path = f"portia/exports/{prepared.export_id}/export.json"',
        "artifact_bytes_after_success != prepared.artifact_bytes",
        "provenance_bytes_after_success != prepared.provenance_bytes",
        "provenance_wire != prepared.deliberate_export.to_dict()",
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_history_verifies_immutable_success() -> None:
    smoke = _load_script()
    probe = smoke._TEACHER_REFERENCE_EXPORT_PROBE
    for marker in (
        "matching = [entry for entry in history if entry.export_id == prepared.export_id]",
        'matching[0].verification_status != "available_verified"',
        "matching[0].operation_id != prepared.operation_id",
        "artifact_path.read_bytes() != artifact_bytes_after_success",
        "provenance_path.read_bytes() != provenance_bytes_after_success",
        '"history_verified": matching[0].verification_status',
        '"artifact_immutable_after_success": artifact_path.read_bytes()',
        '"provenance_immutable_after_success": provenance_path.read_bytes()',
    ):
        assert marker in probe


def test_issue53_teacher_reference_export_follows_student_privacy_stage() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    privacy_index = source.index(
        "student_view_privacy = _student_view_privacy_probe("
    )
    export_index = source.index(
        "teacher_reference_export = _teacher_reference_export_probe("
    )
    assert privacy_index < export_index
    assert 'print("PASS privacy view")' in source
    assert 'print("PASS teacher-reference export")' in source
    assert source.index('print("PASS privacy view")') < source.index(
        'print("PASS teacher-reference export")'
    )
    assert '"teacher_reference_history_verified": teacher_reference_export[' in source
    assert '"teacher_reference_canonical_sources_unchanged": teacher_reference_export[' in source

def test_issue53_read_only_phase_snapshots_each_required_surface() -> None:
    smoke = _load_script()
    probe = smoke._READ_ONLY_SURFACES_PROBE
    for marker in (
        "student_result = require_read_only(",
        '"student timeline/view query",',
        "attention_result = require_read_only(",
        '"attention query",',
        '"Core readiness/attention provider invocation",',
        '"teacher-reference export history verification",',
        '"exact historical predecessor loads",',
        "before = snapshot(workspace)",
        "after = snapshot(workspace)",
        'raise RuntimeError(f"{label} mutated workspace bytes")',
    ):
        assert marker in probe


def test_issue53_read_only_phase_uses_production_services() -> None:
    smoke = _load_script()
    probe = smoke._READ_ONLY_SURFACES_PROBE
    for marker in (
        "StudentTimelineService(workspace).generate(student_query)",
        "AttentionQueryService(workspace).query(attention_query)",
        'diagnose_core_providers(provider_kind="module_operations")',
        "invoke_module_operations(profile, request)",
        "TeacherReferenceExportHistoryService(workspace).list_for_work(",
        "AccountWorkflowService(workspace)",
        "SupportWorkflowService(workspace)",
        "accounts.load_exact(",
        "supports.load_exact(",
    ):
        assert marker in probe


def test_issue53_read_only_phase_verifies_historical_predecessors_exactly() -> None:
    smoke = _load_script()
    probe = smoke._READ_ONLY_SURFACES_PROBE
    for marker in (
        'ORIGINAL_ACCOUNT_ID = "acct_issue53_cross_report"',
        'ORIGINAL_SUPPORT_ID = "spt_issue53_access"',
        "account_reference(event_work, ORIGINAL_ACCOUNT_ID)",
        "support_reference(support_work, ORIGINAL_SUPPORT_ID)",
        'original_account.record.status != "superseded"',
        'original_support.record.status != "superseded"',
    ):
        assert marker in probe


def test_issue53_read_only_phase_has_combined_byte_snapshot_guard() -> None:
    smoke = _load_script()
    probe = smoke._READ_ONLY_SURFACES_PROBE
    for marker in (
        "whole_phase_before = snapshot(workspace)",
        "whole_phase_after = snapshot(workspace)",
        "if whole_phase_after != whole_phase_before:",
        '"whole_read_only_phase_zero_write": (',
    ):
        assert marker in probe


def test_issue53_read_only_phase_follows_intentional_export_write() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    export_index = source.index(
        "teacher_reference_export = _teacher_reference_export_probe("
    )
    read_only_index = source.index(
        "read_only_surfaces = _read_only_surfaces_probe("
    )
    assert export_index < read_only_index
    assert 'print("PASS teacher-reference export")' in source
    assert 'print("PASS read-only surfaces")' in source
    assert source.index('print("PASS teacher-reference export")') < source.index(
        'print("PASS read-only surfaces")'
    )
    assert '"read_only_whole_phase_zero_write": read_only_surfaces[' in source

def test_issue53_deep_path_integration_uses_same_representative_workspace() -> None:
    smoke = _load_script()
    probe = smoke._DEEP_PATH_INTEGRATION_PROBE
    for marker in (
        'TARGET_DEEP_WORKSPACE_LENGTH = 119',
        "if len(str(workspace)) < TARGET_DEEP_WORKSPACE_LENGTH:",
        '"one_deep_workspace": True',
        "require_workspace_descendant(",
    ):
        assert marker in probe


def test_issue53_deep_path_integration_binds_guarded_replacement_and_history() -> None:
    smoke = _load_script()
    probe = smoke._DEEP_PATH_INTEGRATION_PROBE
    for marker in (
        'ACCOUNT_CORRECTION_OPERATION_ID = "op_issue53_account_corrected"',
        'RECOVERY_OPERATION_ID = "op_issue53_support_recovery"',
        'exact_step(journal, "step_history")',
        '"/history/storage_revisions/"',
        "if len(path.name) != 40:",
        'legacy_kind_root = path.parent / legacy_kind',
        'account_predecessor.record.status != "superseded"',
        'support_predecessor.record.status != "superseded"',
    ):
        assert marker in probe


def test_issue53_deep_path_integration_uses_bounded_staging_identities() -> None:
    smoke = _load_script()
    probe = smoke._DEEP_PATH_INTEGRATION_PROBE
    for marker in (
        "staging_path_for(",
        "legacy_staging_path_for(",
        'relative.startswith("portia/.staging/")',
        "ACCOUNT_CORRECTION_OPERATION_ID,",
        "recovering_only=False,",
        "RECOVERY_OPERATION_ID,",
        "recovering_only=True,",
        '"staging_cleaned": not any(',
    ):
        assert marker in probe


def test_issue53_deep_path_integration_uses_bounded_integrity_and_export_paths() -> None:
    smoke = _load_script()
    probe = smoke._DEEP_PATH_INTEGRATION_PROBE
    for marker in (
        "derived_projection_root(",
        "legacy_derived_projection_root(",
        'workspace / "portia" / "derived-v2"',
        'not (integrity_root / "current.json").is_file()',
        "TeacherReferenceExportHistoryService(workspace).list_for_work(",
        'f"portia/exports/{export.export_id}/artifact.html"',
        '"teacher_export_in_deep_workspace": (',
    ):
        assert marker in probe


def test_issue53_deep_path_integration_does_not_manufacture_legacy_paths() -> None:
    smoke = _load_script()
    probe = smoke._DEEP_PATH_INTEGRATION_PROBE
    for marker in (
        '"Issue #53 manufactured a legacy technical-history layout"',
        '"Issue #53 created a legacy target-adjacent staging artifact"',
        '"Issue #53 migrated Integrity state into a legacy derived layout"',
        '"legacy_writer_paths_absent": (',
    ):
        assert marker in probe


def test_issue53_deep_path_integration_follows_read_only_phase() -> None:
    source = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    read_only_index = source.index(
        "read_only_surfaces = _read_only_surfaces_probe("
    )
    path_index = source.index(
        "deep_path_integration = _deep_path_integration_probe("
    )
    assert read_only_index < path_index
    assert 'print("PASS read-only surfaces")' in source
    assert 'print("PASS deep path integration")' in source
    assert source.index('print("PASS read-only surfaces")') < source.index(
        'print("PASS deep path integration")'
    )
    assert '"deep_path_legacy_writer_paths_absent": deep_path_integration[' in source
