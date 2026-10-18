# Issue #60 Slice 2B — Corroborated Page Registration and Ephemeral Regions

Status: **bounded local-only candidate implementation, not physical qualification**.

## Exact source and authorization

`FileMeasuredRegionService.extract` accepts class, Capture Batch, and persisted Page Record IDs plus trusted `CaptureAuthorization` and the exact Slice 1 interpreter/mapping profile. It does **not** accept a source filename, scan bytes, caller-built Page Record, guessed Page Target, QR payload, or registration matrix.

It delegates to the Slice 2 `FileHistoricalPageRegionService.resolve`, which reloads the persisted Page Record, historical Page Target, active Core route, and exact Core-retained source with SHA-256 checking. Before returning ephemeral region pixels, it independently re-resolves authorization, Core custody, Page Record, Page Target, and route. A changed snapshot fails closed. No additional retained scan is created.

## One narrow, measurable registration profile

Provider `measured_sheet_boundary_and_exact_qr_v1` is **not a general document rectifier**. To register a page, it requires both:

1. A complete, contrasting *measured page quadrilateral* (bright sheet against darker visible background, minimum area, four convex corners, no cropped edges, bounded perspective); and
2. An independently decoded **single** PDS2 QR whose decoded route is the persisted, Core-verified route. The observed QR corners must corroborate the printed QR's historical location using the frozen 4-module quiet zone, actual version/size of the Core PDS2 QR, and a strictly bounded pixel residual.

Four possible sheet orientations are compared. Ambiguous matches or excessive reprojection error **fail**, rather than using appearance-based guessing. The page-to-pixel mapping comes from detected sheet corners and is checked against the separate QR measurement; no generic inferred DPI/crop assumption is sufficient. The full historical seven-element template identity and immutable fingerprint are rechecked.

**Unsupported cases are intentional:** ordinary white-on-white scanner PDFs without a visible page boundary, unmeasurable clipped pages, non-flat sheets, heavy curvature/skew/perspective, multiple QRs, unreadable/mismatched QR, faint low-contrast paper edges, and optional OpenCV/NumPy provider unavailability. They remain *unregistered/Needs Attention*, not blank or a failed human assertion. Do not call this a broadly qualified photo or office-scanner recognizer.

## Bounded regions and semantics

For an accepted page, one grayscale `FieldRegionPixels` object is generated for each **declared historical field**, preserving `entry_key`, `field_key`, and `region_key`, source physical page number, and exact layout fingerprint. The crop covers the full declared rectangle, **including preprinted labels, writing rules, and option boxes**. Later recognition providers must distinguish those printed artifacts from candidate handwriting/marks; this slice makes no blank/unmarked/candidate decision.

All crops are ephemeral Python bytes. No PNG/PDF/crop files are written, no source bytes or absolute paths are embedded in persisted JSON, and repr excludes pixel buffers. Hard ceilings: 16 million source pixels, 2 million pixels per crop, 12 million total crop pixels per page; the retained-source admission and existing rasterization bounds remain in effect. Optional local CV comes from Portia's existing `scan` extra; no network service, generative transcription, or new mandatory dependency is introduced.

## Failure and qualification notes

Failures use stable `HistoricalPageError` codes for border/QR measurement, ambiguity, geometry conflict, resource budgets, optional backend availability, custody mismatch and authorization. Source reading/cropping is read-only; Core custody and Page Records survive a registration failure. No canonical Event, Observation, student identity, Capture Proposal, Capture Review, or materialization is produced.

Synthetic proof covers straight and perspective-mapped full-sheet dark-background pages with valid historical geometry/QR, full white/blank borders, wrong route, cropped page, unavailable backend, and all declared region keys. These are synthetic *registration tests*, **not real handwritten recognition tests**. Physical scanner/camera qualification belongs to #60 Slice 9. A subsequent Slice 3 will implement independently versioned, truthful recognition and fallback behavior.

Core currently installed in developer acceptance environment: 0.6.5 as reported from Slice 2. Final compatibility with official Core 0.6.6 and older 0.6.x versions belongs to the #60 closeout matrix, not this focused slice.
