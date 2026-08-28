from portia.workflows.issue22_parity import workflow_issue22_parity


def test_issue22_workflow_accounting_has_required_evidence_boundaries() -> None:
    entries = {entry.scenario_id: entry for entry in workflow_issue22_parity()}
    required = {
        "P22-01",
        "P22-02",
        "P22-03",
        "P22-04",
        "P22-10",
        "G22-009",
        "G22-010",
        "G22-011",
        "G22-017",
        "G22-035",
    }
    assert required <= entries.keys()
    assert entries["P22-01"].disposition == "newly_covers_evidence_workflow"
    assert entries["P22-03"].disposition == "consumes_issue39_identity"
    assert entries["P22-04"].disposition == "newly_covers_evidence_correction"
    assert entries["G22-017"].disposition == "newly_covers_evidence_authority"
