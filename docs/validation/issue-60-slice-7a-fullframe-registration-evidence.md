# Portia #60 — Slice 7A: full-frame white office-scanner evidence

This incremental, deliberately **non-integrated** qualification service addresses the full-frame white-background scanner gap identified in Slice 2B. It does not yet enable field extraction or interpretation from white scanner output. Its `qualify_full_frame` is a pure geometry/measurement function; the authorized `FileMeasuredRegionService` continues to use the prior conservative border method until a separately qualified integration slice.

## Evidence requirements

- Exact frozen seven-element historical template identity, expected exact PDS2 QR payload and `BoundedPageRaster`.
- Readable QR with measured corners and sufficient resolution; white page corners and sheet geometry consistent with essentially whole-page scanning.
- At least **three independently observed printed field frames** across a substantial vertical span, including two in the lower half, with both top and vertical borders present at historically predicted coordinates. Absence or ambiguous orientation fails closed.
- The resulting registration method is explicitly `measured_fullframe_qr_and_field_frames_v1`, not the earlier `measured_sheet_boundary_and_exact_qr_v1`; no false border assertion.
- No caller-supplied QR or raster is source authority. Later integration must invoke this after existing Core custody, Page Record, exact route, authorization and post-extraction recheck, retaining the candidate/fact boundary.

## Deployment state

**Not yet teacher-enabled.** Slice 7B must add an exact, versioned registration method to the consuming pipeline (`measured_regions`, candidate validations and saved interpretation writers), rerun integration tests, qualify on physical office-scanner output, and preserve existing immutable same-profile replay behavior. No canonical content, names, grading or behavioral judgments are inferred. Existing source bytes and records are untouched.
