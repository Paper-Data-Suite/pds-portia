# Issue #59 Slice 8 — installed source, packaging, and qualification matrix

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`
**Required starting commit:** `187cd2d270933764e980ef8988975046f57f6bb7`
**Scope:** final packaging/CI readiness only. No changes to Core custody, Page Target, Page Record, or behavioral domain schemas.

## Runtime and installation contract

- Portia's released version remains **0.2.0** on this development branch. Parent #55 controls future v0.3 release timing; this slice is not a PyPI/GitHub release.
- Existing base dependencies remain exactly frozen to satisfy earlier #57 and v0.2 historical qualification. For returned-paper QR intake, **install `pds-portia[scan]`** (or editable `python -m pip install -e ".[dev,scan]"` in a development checkout). The `scan` extra provides PyMuPDF, OpenCV headless, and NumPy. Missing optional scan providers fail explicitly, not as a misleading missing QR.
- Include all eight `portia/intake` Python modules and `portia/menu/returned_paper.py` in the verified wheel inventory. Include all #59 tests, validation docs, standalone closeout auditor and installed-wheel smoke in the sdist inventory.
- Source-only synthetic fixtures. No student rosters, handwriting, or captured student records in public tests.

## Acceptance and authority matrix

| Boundary | Acceptance | Evidence/gate |
| --- | --- | --- |
| Original Core custody | Exact submitted PDF/JPEG/PNG retained; SHA-256 readback; Core solely owns bytes | #59 Slices 1–2 tests, Core retained-source writer |
| Multipage pages | A single synthetic ten-page PDF, independent PDS2 codes, preserved original page numbers | #59 Slice 3 tests |
| Mixed/invalid QR | Missing, unreadable, conflicting, malformed, foreign-module and renderer failures do not invent a route | #59 Slices 3–4 tests |
| Exact Core + Page Target | Class authorization, active registration, historical frozen identity; non-Portia pages rejected/delegated | #59 Slice 4 tests |
| Idempotent Page Records | Exclusive receipt per retained source-page; exact retries; partial failures preserve prior successes | #59 Slice 5 tests |
| Teacher operation | Main menu option 11; single PDF/image selection; review outcomes; same-source retry | #59 Slice 6 tests |
| Restart recovery | Core source enumeration and integrity verification, no second source identity or guessed route | #59 Slice 7 tests |
| Package/install | Wheel and sdist inventory includes all new modules; isolated wheel installs `scan` extra | #59 closeout + installed-wheel smoke |
| Compatibility | Core 0.6.3 installed smoke; Core 0.6.4/0.6.5 existing frozen complete suite; official Core 0.6.6 installed smoke | CI + complete `validate_repository.py` |
| No domain materialization | No scan directly creates Event/Account/Observation/Response or student judgment | Service contract + negative tests |

## Required final sequence

1. Exact clean branch/baseline guard. Install/evaluate the final-source patch.
2. Run Ruff autofix/format once on changed code, strict mypy, and the focused #59 check once.
3. Run **one** full repository qualification through `scripts/validate_repository.py` using verified official Core 0.6.3, 0.6.4, and 0.6.5 wheels; it now invokes #59 closeout, all tests, wheel/sdist checks and isolated Core 0.6.3 wheel smoke. No immediate second full suite run.
4. Only after those gates pass, commit and push. Await exact-tip Windows/Ubuntu CI, including the official Core 0.6.6 installed-wheel smoke. Do **not** claim those checks green before GitHub reports success.
5. Create PR to `main` with `Closes #59`, citing #55, #56–#58, #60–#62. Squash/merge only after CI. Keep umbrella #55 open. No automatic release.

## Physical evidence limitations

The accepted #58 pilot printed and inspected ten sheets, checked three phone-readable QRs, and decoded one physically photographed return. This is **not** equivalent to scanning a real mixed ten-page office-scanner PDF. Existing #59 synthetic ten-page tests and installed synthetic PDF/image wheel smokes are qualified engineering evidence; no real 200/300-DPI office-scanner sweep or additional user rescans are asserted here.
