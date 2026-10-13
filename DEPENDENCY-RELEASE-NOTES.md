# Dependency-source preview 7

The laboratory now runs the actual hash-pinned portal backend on private D-Bus
and PipeWire servers, using a registry-only Wayland fixture. It tests API readiness
and explicit closure of known sessions without touching the phone or host desktop.

## Findings and validation

The pinned backend exposes ScreenCast version 4. Its bus owner/PID and executable
hash match the launched process. CreateSession succeeds; its backend session
objects survive the exit of short-lived direct D-Bus callers. Explicit Session.Close
removes them. Duplicate close fails, and restart changes the owner and removes old
objects. This direct backend behavior does not establish how normal applications
behave through the xdg-desktop-portal frontend.

Eight new tests cover readiness/capabilities, three-session closure, duplicate
close, restart, PipeWire loss, Wayland loss, name collision and an unresponsive
backend. The latter exposed that gdbus method timeouts do not bound the entire
invocation; an outer subprocess deadline now records an unconfirmed close as a
failure and retains the tracked session. Explicit close succeeds after resume.

All 87 tests pass without skips from the extracted archive in networkless ARM64
Linux with read-only source/stage mounts. The earlier 318 forced-exit cases remain
unchanged; this release adds eight real API tests, not more injected-exit cases.
Two normalized exports match, all 63 files match their inventory, and 62 attribution
entries verify. Documentation links and privacy findings were reviewed. Boot and
desktop payloads, dependency recipes and runtime pins are unchanged.

## Scope and next step

Read the [real session laboratory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-7/dependency-source/PORTAL-SESSION-LAB.md).
The original Wayland fixture advertises the required globals but provides no
outputs or frames and rejects capture requests. Three pinned protocol XML inputs
are checked before temporary code generation. No generated code or binary is
included in the release. A different portal executable hash is refused.

The suite closes only sessions it created and tracks. The inspected backend has
no general drain-all operation. Active streams, pending requests, unknown clients,
frontend cancellation and the phone's wlr capture path remain unverified. API
readiness is not evidence of successful capture. No live updater is enabled and
no phone, account or host session was contacted.

Next: exercise frontend cancellation and actual capture sessions with a real
headless compositor, then define refusal of active or untracked clients before
updates. Keep ownership adoption and physical acceptance separate.

Source only: original DionLabs integration has scoped MIT terms; inherited
notices retain upstream terms. No portal binaries, firmware or images distributed.

Archive dependency-source-preview.tar SHA256:
`1ccfcdb04987716275eab9988d78b9e8aad184020c2fbd4f77d3ea12c5b93600`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. Export-time source-preview.tar is renamed without changing bytes;
GitHub-generated repository archives differ. Frozen publication_cleared:false
records prepublication export state; approval covers this reviewed source only.
