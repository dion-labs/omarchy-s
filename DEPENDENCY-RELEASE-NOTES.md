# Dependency-source preview 14

Real portal capture now runs inside a disposable container registered before capture.
A worker consumes changing headless frames while retaining admission and an
unidentified durable receipt. The host tests both app death without cleanup and
container destruction while capture remains active. Recovery refuses until exact
container destruction is proven; it then retires the root permanently.

## Validation

All 141 tests pass without skips from extracted source: 139 Linux and 2 host tests.
The new host test includes two real interruption scenarios. The existing 333
injected-exit cases remain unchanged. Each scenario verifies changing 1280x720
frames, refusal before destruction, retained evidence, exact container absence on
the unchanged engine, receipt retirement and refusal to reuse the retired root.

Two normalized 84-file exports match; 83 attribution entries and source links verify.
Privacy findings reviewed. Boot/desktop inventories and runtime pins unchanged.
Owned test containers/volumes are removed; no phone or live desktop was contacted.

## Limits and next step

Read the [capture scope guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-14/dependency-source/PORTAL-CAPTURE-SCOPE-E2E-LAB.md).
Capture uses headless software rendering and a pinned backend, not the phone's
GPU/wlr path. The host engine and cooperating callers are trusted. This is not a
production service boundary, live updater or arbitrary-client interception mechanism.

Next: consolidate a reproducible acceptance command and machine-readable evidence
for the Linux and host checks so the published recovery guarantees are easier to
reproduce independently.
