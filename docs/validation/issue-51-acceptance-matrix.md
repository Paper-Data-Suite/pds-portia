# Issue #51 Acceptance Matrix

This matrix maps the 98 ticket-level acceptance obligations to executable or mechanical repository evidence. A row is evidence routing, not a substitute for the referenced tests and validators.

| # | Acceptance obligation | Primary evidence |
| ---: | --- | --- |
| 1 | **Scope and identity:** Exact Event@2 can prepare a `teacher_current` export. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 2 | **Scope and identity:** Exact Support Process@1 can prepare a `teacher_current` export. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 3 | **Scope and identity:** Exact focal participant can prepare a `participant_specific` export. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 4 | **Scope and identity:** Display name cannot select export identity. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 5 | **Scope and identity:** Bare repeated `student_id` across classes cannot select focal identity. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 6 | **Scope and identity:** Unsupported/legacy work roots fail closed rather than silently migrating. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 7 | **Scope and identity:** Export scope remains one exact work. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 8 | **Scope and identity:** Related-work references do not recursively widen scope. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 9 | **Projection:** Unknown contract/version fails closed. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 10 | **Projection:** Operational contracts never enter the artifact. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 11 | **Projection:** Export/provenance contracts never enter the artifact. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 12 | **Projection:** Contact Point data never enters the ordinary artifact. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 13 | **Projection:** Actor Directory is not live-dereferenced for display enrichment. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 14 | **Projection:** Exact embedded participant display snapshot may be projected according to policy. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 15 | **Projection:** `Account` remains visibly distinct from `Observation`. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 16 | **Projection:** `Review`, `Classification`, `Hypothesis`, and `Determination` remain distinct. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 17 | **Projection:** `Response` remains distinct from ongoing Support. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 18 | **Projection:** `Implementation`, `Fidelity`, and `Outcome` remain distinct. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 19 | **Projection:** No risk/severity/priority ranking is introduced. | `tests/test_teacher_reference_export_policy.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_rendering.py` |
| 20 | **Participant-specific applicability:** A participant-specific export includes exact focal-applicable content only. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_menu_teacher_reference_export.py` |
| 21 | **Participant-specific applicability:** Unrelated participant-specific information is withheld or excluded according to policy. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_menu_teacher_reference_export.py` |
| 22 | **Participant-specific applicability:** Shared work context may remain where required for interpretation without becoming another participant’s dossier. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_menu_teacher_reference_export.py` |
| 23 | **Participant-specific applicability:** Participant-specific export remains teacher-reference purpose, not student-facing delivery. | `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_menu_teacher_reference_export.py` |
| 24 | **Manual review:** Manual-review-required content blocks final preparation until resolved. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 25 | **Manual review:** Teacher may include the exact reviewed source content. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 26 | **Manual review:** Teacher may omit it. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 27 | **Manual review:** The workflow does not automatically paraphrase or sanitize it. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 28 | **Manual review:** Final provenance records `manual_review = resolved` when applicable. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 29 | **Manual review:** A changed source after manual review invalidates the preparation. | `tests/test_teacher_reference_export_projection.py`; `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_reference_export_execution.py` |
| 30 | **Source inventory:** Every included contributing Portia source has exact digest and byte length. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 31 | **Source inventory:** Inventory ordering is deterministic. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 32 | **Source inventory:** Duplicate semantic source identity is rejected. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 33 | **Source inventory:** A fully withheld candidate is not added merely because it was considered. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 34 | **Source inventory:** Correction/disagreement context receives the truthful source role. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 35 | **Source inventory:** No live Core roster row appears as an unrepresented hidden source. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 36 | **Source inventory:** No sibling-module source enters ordinary #51 v0.2 export. | `tests/test_teacher_reference_export_rendering.py`; `tests/test_teacher_reference_export_discovery.py`; `tests/test_teacher_reference_export_policy.py` |
| 37 | **Renderer:** Identical prepared semantic input yields identical HTML bytes. | `tests/test_teacher_reference_export_rendering.py` |
| 38 | **Renderer:** HTML special characters are safely escaped. | `tests/test_teacher_reference_export_rendering.py` |
| 39 | **Renderer:** Output is UTF-8 with deterministic line endings. | `tests/test_teacher_reference_export_rendering.py` |
| 40 | **Renderer:** No network/remote asset is required. | `tests/test_teacher_reference_export_rendering.py` |
| 41 | **Renderer:** No JavaScript is emitted. | `tests/test_teacher_reference_export_rendering.py` |
| 42 | **Renderer:** No raw canonical JSON is dumped into hidden HTML. | `tests/test_teacher_reference_export_rendering.py` |
| 43 | **Renderer:** Artifact contains the teacher-reference disclaimer. | `tests/test_teacher_reference_export_rendering.py` |
| 44 | **Renderer:** Artifact does not expose absolute paths or operation internals. | `tests/test_teacher_reference_export_rendering.py` |
| 45 | **Preview:** Preparation writes nothing. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 46 | **Preview:** Preview shows actual outgoing content. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 47 | **Preview:** Preview exposes withheld/unavailable/manual-review summary. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 48 | **Preview:** Cancel before confirmation writes nothing. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 49 | **Preview:** Confirmation binds one exact preparation fingerprint. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 50 | **Preview:** A zero-content/fully blocked projection cannot create a misleading empty “successful” reference. | `tests/test_teacher_reference_export_preparation.py`; `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_reference_export_execution.py` |
| 51 | **Prepared-state concurrency:** Work root changes after preview -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 52 | **Prepared-state concurrency:** Contributing source bytes change after preview -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 53 | **Prepared-state concurrency:** Applicable correction/disagreement context changes -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 54 | **Prepared-state concurrency:** Policy digest changes -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 55 | **Prepared-state concurrency:** Authorization changes -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 56 | **Prepared-state concurrency:** Manual-review decision no longer binds current projection -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 57 | **Prepared-state concurrency:** Renderer output changes -> no write. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 58 | **Prepared-state concurrency:** Execution never silently reprepares and substitutes new state. | `tests/test_teacher_reference_export_execution.py`; `tests/test_teacher_reference_export_projection.py` |
| 59 | **Issue #88 persistence:** Confirmed export uses one exact `pexp_`. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 60 | **Issue #88 persistence:** Uses `operation_journal@4`. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 61 | **Issue #88 persistence:** Uses `operation_lock@3`. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 62 | **Issue #88 persistence:** Uses operation kind `generate_deliberate_export`. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 63 | **Issue #88 persistence:** Artifact is created before provenance. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 64 | **Issue #88 persistence:** Both are `exclusive_create`. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 65 | **Issue #88 persistence:** Provenance references the reserved committed revision. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 66 | **Issue #88 persistence:** Completed revision does not rewrite provenance. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 67 | **Issue #88 persistence:** Final artifact bytes exactly match the previewed candidate digest. | `tests/test_teacher_reference_export_execution.py`; `tests/test_issue88_export_operation_validation.py`; `tests/test_issue88_export_execution.py` |
| 68 | **Recovery:** Failure before first accepted final write leaves no accepted export artifact and releases the lock. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 69 | **Recovery:** Artifact-only failure preserves the exact artifact. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 70 | **Recovery:** Exact staged provenance candidate can complete artifact-only recovery. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 71 | **Recovery:** Missing/contradictory staged provenance fails closed rather than regenerating a different provenance record. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 72 | **Recovery:** Exact artifact + provenance can recover the missing committed revision. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 73 | **Recovery:** Completed finalization is idempotent. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 74 | **Recovery:** Contradictory replay fails before mutation. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 75 | **Recovery:** Wrong existing artifact bytes are never overwritten. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 76 | **Recovery:** Wrong existing provenance bytes are never overwritten. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_issue88_export_execution.py` |
| 77 | **Export history:** History lists immutable exact export records. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 78 | **Export history:** Chronological sorting does not establish current authority. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 79 | **Export history:** Missing artifact is reported as missing. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 80 | **Export history:** Digest mismatch is reported as mismatch/recovery concern. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 81 | **Export history:** History does not silently regenerate missing historical bytes. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 82 | **Export history:** New export creates a new `pexp_`. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 83 | **Export history:** No ordinary overwrite action exists. | `tests/test_teacher_reference_export_recovery_history.py`; `tests/test_teacher_reference_export_preparation.py` |
| 84 | **Menu integration:** Main menu remains eight teacher tasks plus Advanced. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 85 | **Menu integration:** View Timeline still works without export. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 86 | **Menu integration:** Current work offers contextual teacher-reference export. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 87 | **Menu integration:** Whole-work export and participant-specific export remain visibly distinct. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 88 | **Menu integration:** Prior export history is reachable from the selected work context. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 89 | **Menu integration:** Help text explains export != disclosure/delivery/official record. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 90 | **Menu integration:** Back/Main/Quit before confirmation remain zero-write. | `tests/test_teacher_menu_teacher_reference_export.py`; `tests/test_teacher_menu_timeline.py`; `tests/test_teacher_menu_foundation.py` |
| 91 | **Installed wheel:** Installed Portia wheel contains all new export runtime modules. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 92 | **Installed wheel:** Installed workflow operates with only authenticated Core + Portia installed. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 93 | **Installed wheel:** No sibling PDS package is required. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 94 | **Installed wheel:** Synthetic exact Event can produce and verify HTML export. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 95 | **Installed wheel:** Synthetic exact Support Process can produce and verify HTML export. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 96 | **Installed wheel:** Participant-specific export preserves focal filtering. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 97 | **Installed wheel:** Partial-commit/recovery smoke exercises the real installed #88 path. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |
| 98 | **Installed wheel:** Export history verifies the generated artifact from installed code. | `scripts/check_issue51_package.py`; `scripts/smoke_test_issue51_teacher_reference_export_wheel.py` |

## Authority

The authoritative closeout command is `python scripts/validate_repository.py --core-wheel <pds_core-0.6.3-py3-none-any.whl>`. The dedicated Issue #51 validator also checks that this matrix contains exactly rows 1 through 98.
