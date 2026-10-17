# Issue #57 — Capture Batch / Page Target preparation acceptance matrix

**Branch:** `57-capture-batch-page-target-services`
**Issue:** https://github.com/Paper-Data-Suite/pds-portia/issues/57
**Parent:** #55
**Starting main commit:** see `issue-57-slice-1-local-baseline.md`
**Qualified Core release:** v0.6.6 (see Slice 8 evidence)
**Closeout status:** PENDING final hosted qualification and PR merge

| Obligation | Evidence | Status at Slice 9 authoring |
| --- | --- | --- |
| Clean post-#56 baseline | Slice 1 baseline, exact Git branch and original commit | Implemented |
| Capture Batch@1 non-domain persistence/lifecycle | Slices 1–2; `FileCaptureBatchService`; focused tests | Tested |
| Page Target@2 current, @1 historical exact reads | Slice 3; `FilePageTargetService`; regression tests | Tested |
| Classroom, monitoring, communication and existing work | Slice 4; `validate_page_purpose` and exact context resolution | Tested |
| Core public PDS2 route registration | Slice 5; exclusive Core writer and independent durable readback | Tested |
| No QR/payload before durable verification | Slice 5–6 route and preparation tests | Tested |
| Multi-page ordering, idempotency and partial results | Slice 6; `FileCapturePreparationService` | Tested |
| Read-only inspection; bounded intentional recovery | Slice 7; immutable route history and whole-batch inventory audit | Tested |
| Corrupt, orphan, duplicated or mismatched route defense | Slice 7 tests; no blind overwrite / lock clearance | Tested |
| Path security, Windows link-like paths and concurrency | Slices 2–7 regression tests; hosted Windows and Ubuntu | Tested in focused gates |
| No fabricated Event, Observation, or domain case | Slices 4–8 regression tests and installed smoke | Tested |
| Core 0.6.6 exact published wheel | v0.6.6 source `35af5d0642e84a625cd143285c4ef6de98dbcca4`, SHA-256 `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301` | Authenticated |
| Windows viewer junction and canonical identity isolation | Slice 8 installed smoke on Windows (mocked desktop launch) | Passed in CI |
| Ubuntu installed compatibility | Slice 8 installed smoke on Ubuntu | Passed in CI |
| Core >=0.6.3,<0.7 runtime compatibility unchanged | `pyproject.toml`; historical CI matrix 0.6.3/0.6.4/0.6.5 | Retained; historical CI pending |
| Typed service API | `portia.capture` and strict mypy | Tested |
| Wheel includes capture package; sdist includes closeout evidence | `scripts/check_package.py`; Slice 9 validation | Pending final package gate |
| Complete full repository pytest/Ruff/mypy and package acceptance | `scripts/validate_repository.py` on Windows and Ubuntu | Pending final hosted qualification |
| PR, squash merge, clean main reconciliation | Manual release-management workflow after required CI passes | Pending |

## Interpretation and caveats

- "Tested" refers to exact regression and installed-wheel evidence, **not** final
  merge approval. The final matrix is only complete after the new branch tip's
  authoritative CI results are green and referenced in its PR.
- Hosted Core 0.6.6 Windows/Ubuntu installed-wheel jobs passed at Slice 8.
- Existing Issue #54 historical qualification remains intentionally pinned to
  Core 0.6.5, 0.6.4 and 0.6.3. A version-specific Slice 8 test was isolated
  from those jobs in follow-up commit `b86acf62505de27f0d8120ca2948d38faf309204`.
  The next full CI must establish no remaining regressions.
- Core's `open_local_path()` acceptance proves shell handoff, **not** viewer
  visibility; no actual classroom PDF rendering/printing is part of Issue #57.
- PDS2 routing identity is canonical and does not use temporary Windows viewer
  junctions. No Portia release is published solely for Issue #57.
