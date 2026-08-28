from portia.workflows.issue22_parity import workflow_issue22_parity


def test_issue22_workflow_accounting_has_required_boundary_transitions() -> None:
    entries = {entry.scenario_id: entry for entry in workflow_issue22_parity()}
    assert {"P22-01", "P22-03", "G22-009", "G22-010", "G22-017"} <= entries.keys()
    assert entries["P22-01"].disposition == "newly_covers_workflow"
    assert entries["P22-03"].disposition == "consumes_issue39_identity"
    assert entries["G22-017"].disposition == "shares_issue41_boundary"
