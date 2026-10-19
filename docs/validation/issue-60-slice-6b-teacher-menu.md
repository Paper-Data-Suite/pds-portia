# Portia #60 — Slice 6B: teacher menu staging

- **Baseline:** `636783897a61c3cb1186a6e817b5d5062eb01e69` (passing #60 Slice 6A).
- The original `Scan / Import Returned Paper` flow remains: retain/restore one Core original, verify pages independently, save/reuse Page Records, show intake summary and per-page statuses.
- For verified receipt pages, an **optional independent uppercase STAGE confirmation** follows. Declining creates no interpretation/proposal writes. The source need never be retained again.
- After STAGE, the existing `FileTeacherPaperStagingService` performs all protected custody/class/route/history checks, even when the menu carries a Page Record ID. The menu receives only privacy-minimized `TeacherStagingSummary` values.
- The new staging summary reports source count, interpreted pages, Needs Attention pages, new/reused proposals, then each physical source page's staging state and suggested follow-up. Partial interpretations still need attention. Neither proposals nor status counts are approvals or canonical facts.
- If staging is interrupted after some pages, the menu reports a possible partial save and directs explicit replay of the *same Core-retained scan*. Earlier Page Records and immutable generations are not rolled back.
- No handwriting OCR, page alignment beyond the qualified provider, manual transcription input, Capture Review, or canonical event materialization is claimed here. #61/#62 remain separate review/write gates.
- Tests use synthetic source identities only: consent/no write, zero accepted pages, exact source order, rendering privacy, existing menu ordering, and post-write-unknown messaging.
