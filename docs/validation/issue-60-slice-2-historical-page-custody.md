# Portia #60 - Slice 2: Verified Historical Page Custody and Bounded Raster

## Scope and security contract

On the exact post-Slice-1 branch, this slice adds the first production read-only resolver:
`FileHistoricalPageRegionService.resolve(class_id, work_id, page_record_id,
authorization=..., profile_identity=...)`. It requires trusted class authorization
**before** protected class/work records or Core source bytes are read. It reloads
an existing, exact `page_record@1` from the #59 bounded store and checks its
recomputed receipt identity; it never accepts a caller-constructed Page Record,
source filename, source path, or QR payload as authority.

A saved Core source scan ID resolves to its canonical dated Core retained-source
location, *not* the newest source in a short recent list. #59 recovery
revalidates safe path, immutable source digest, actual format, actual bytes,
and actual PDF/image page count. The source's **physical page number** remains
distinct from Page Target index and template ordinal. Core dispatch then
revalidates the active route and exact Page Target against durable Core records;
Slice 1 chooses only the exact frozen historical form profile. The source is
rehashed after route/template validation. Broken identities fail closed.

`rasterize` re-resolves all authority on each call and renders only the one
selected physical page, in ephemeral grayscale memory, within a strict pixel
budget (16 million maximum, further bounded by #59 configured limits). For PDF,
PyMuPDF is optional and absence is explicit; PNG and JPEG reuse Pillow.

## Explicit limitation: registration has not been measured

A scan having 612x792 PDF dimensions, or being 800x1000 pixels, **does not**
prove alignment between top-left printed coordinates and scan pixels. The
returned `BoundedPageRaster` is always `registration=unregistered`: it never
asserts a blank, crops a field, detects handwriting or marks, or assembles an
interpretation. True region alignment/calibrated transform and isolated field
crops still require a distinct qualified implementation in the remainder of
Slice 2 before recognition provider work begins. No cloud provider or network
access is introduced.

The `PageQrDiscovery` object produced internally during Core revalidation is
constructed **from the persisted, previously verified #59 receipt**, not from
an untrusted caller or a new claim about observed QR pixels. It is never
persisted, exposed as a new QR reading, or used to manufacture Page Records.

## Non-goals and next slice boundary

No capture proposal, interpretation generation, Page Record state transition,
Capture Review, student/person match, domain record, or Core retention call.
No fallback to unknown PageTargetV1/history. No direct region OCR.

Next: actual measured registration and independently bounded field cropping,
with explicit unreadable/unregistered codes for imperfect scans, then optional
local-only OCR/mark providers under a new pinned interpreter profile.

## Focused qualification

- Real synthetic #59 Core retain / route / persisted Page Record construction
- Exact physical-page vs printed-page identity and historical spec resolution
- Cross-class authorization denial before source custody lookup
- Mutated retained source refusal, no source repair/write
- Source and image/PDF rasterization with explicit unregistered semantics
- Exact profile rejection; bounded raster metadata and privacy-safe repr

Not a physical handwriting/OMR qualification or installed-wheel test.
