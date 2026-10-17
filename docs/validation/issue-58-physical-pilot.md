# Portia #58 — Physical pilot evidence and accepted boundary

Date: 2026-10-17. This is a teacher-local **physical pilot**, not a claim of exhaustive QR qualification.

- Synthetic source-only generator produced **nine PDF packets / ten independently registered PDS2 pages**, with exact Core route readback and copied-PDF SHA-256 checks. No real classroom data was used.
- All ten sheets were printed on a **Brother HL-L2350DW**. The teacher inspected the actual paper and reported the pages printed correctly and the forms looked good, including the writable layouts.
- The teacher randomly sampled **three QR codes** using a phone; **three of three were recognized**. Phone recognition alone does **not** establish equality with Core registration.
- The teacher scanned one actual printed **Focused Monitoring** sheet using **Google Drive's phone scan feature on a Samsung Galaxy Z Fold6**, saved as JPEG. The repo's `verify_issue58_physical_scans.py` tool with OpenCV **5.0.0** reported `PASS focused_monitoring:1: decoded exact active Core route`, `Verified 1/10 distinct physical page layouts`, and `PARTIAL evidence only`.
- **No** controlled 200/300-DPI hardware scanner sweep was performed; nine layouts do **not** have independently verified scan-to-route matches. Phone-camera JPEG is not assigned an invented DPI. No print-server job completion was verified.

## Disposition

The teacher explicitly accepted this limited, practical physical pilot and declined unnecessary manual scanning/routing of nine additional test sheets. Treat **#58 form generation and physical pilot** as accepted on the above observed evidence; preserve the untested scanner configurations and layouts as **residual qualification**, not as successes.

**#59** must implement a *single multi-page scanned PDF* intake workflow that automatically handles its pages, and can exercise further real scan acceptance **without** individual manual image naming/routing. Retain raw source provenance and never confuse generation or QR detection with accepted behavior evidence.

This record contains no scans, raw QR payloads, student identities, or live PDS workspace data.
