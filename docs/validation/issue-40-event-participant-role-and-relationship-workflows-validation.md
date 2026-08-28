# Issue #40 workflow validation

`scripts/validate_workflows.py` mechanically checks the public workflow modules
and service methods, production contract constants, strict repository list
surface, #39 resolver consumption, Issue #22 accounting, and documentation. Its
AST checks reject private Core imports, direct roster parsing, name/fuzzy
identity lookup, Actor repository bypass, direct canonical writers, workflow
lock/transaction/journal classes, and leaked Account/Observation workflow
services.

Focused tests cover Event guarded persistence and zero-write graph rejection;
all four Participant subject forms and complete multi-roster context assembly;
Role ownership and Account qualification; exact Relationship endpoint
resolution and zero-write rejection; strict bounded enumeration; and
coordinated Event bundle publication and stale preflight failure.

The correction coverage also proves the active/closed Event minimum
Participant invariant, zero-write rejection when replacing the final active
Participant, accepted active Role activation under a draft Event, separation
from current-use visibility, terminal-state non-resurrection, immutable
creation provenance, immutable Role assertions and Relationship endpoints, and
active Relationship eligibility for active and closed contextual Event
targets. Target/source/provenance retargeting assertions compare unchanged
canonical bytes after rejection.

Repository qualification runs the foundation, runtime, storage, identity, and
workflow validators before the complete test, Ruff, MyPy, and `pip check`
gates. It then builds wheel and sdist artifacts, runs Twine and package-content
checks, and executes the isolated installed-wheel smoke with the authenticated
Core 0.6.3 wheel.

The installed smoke imports Portia outside the source checkout and verifies
runtime contracts, guarded storage, exact Core roster identity, Actor Directory
resolution, and the public workflow package. Its synthetic workspace contains
no real student or teacher data.

Repository qualification additionally requires the root `SECURITY.md` and its
Security Policy, Student Data / Privacy, Reporting a Vulnerability, and
Supported Versions headings. Package validation requires the policy in the
sdist while keeping it outside the runtime package payload.
