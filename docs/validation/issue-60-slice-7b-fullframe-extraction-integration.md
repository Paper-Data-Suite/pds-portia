# Portia #60 Slice 7B — qualified white-scanner page registration integration

**Exact base:** `0cb1a7fa2e85bbb3350b10887652c30b06bbe320` (Slice 7A).

## Purpose

Connect Slice 7A's separately qualified `measured_fullframe_qr_and_field_frames_v1` transform to the existing **source-authorized** `FileMeasuredRegionService.extract` crop and local mark/manual-candidate pipeline. Keep the original contrasting-border `measured_sheet_boundary_and_exact_qr_v1` method unchanged.

## Rules

- The new method is only attempted when the original border measurement fails specifically with `page_border_unmeasured`. A different registration error is never downgraded to a fallback.
- Full-frame registration remains contingent on the exact PDS2 QR and independent distant historical printed field frames. QR-only scans and wrong routes never yield candidate fields. A fully blank white page retains its prior `page_border_unmeasured` diagnostic.
- `FileMeasuredRegionService.extract` remains the only authorized production caller: it validates Capture Batch, Page Record, PDS2 route, historical layout, Core original and class authorization before rasterization, and performs a second authority/custody check afterward.
- Crop origin, historical field inventory and pixels continue through the same bounded extraction code, without creating or retaining a derivative file.
- The finite allowlist of **two** qualified registration methods is enforced by the mark classifier, manual candidate staging and immutable interpretation writer. Arbitrary caller-provided registration identifiers remain rejected.
- No OCR/handwriting inference, roster matching, content acceptance, Capture Review, or canonical materialization is implemented. A partial result remains partial/Needs Attention.
- The `local_checkbox_v1` mark recognition algorithm is unchanged; this slice adds separately corroborated geometry rather than changing the recognition provider. Existing `paper_interpretation@1` same-profile replay remains immutable and divergent attempts must still conflict rather than overwrite.

## Acceptance

Focused real-OpenCV tests exercise white-scanner field extraction, downstream mark candidate and manual staging, exact field identity and bounded crops, legacy contrasting-border registration, QR-only rejection, mismatched PDS2 route rejection, old all-white diagnostic, and unqualified method refusal.

**Outstanding physical qualification:** Real office-scanned synthetic printed forms from both Brother/Canon profiles, across upright/rotated/deskew conditions, have **not** been exercised by this ZIP. This increment is not release/issue closeout approval.
