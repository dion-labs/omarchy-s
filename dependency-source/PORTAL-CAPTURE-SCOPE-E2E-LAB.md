# Real capture inside a disposable registered scope

The host scope suite now runs the real headless frontend capture stack wholly
inside a labelled, networkless disposable container. Before starting it, a helper
binds the exact engine/container identity and token to a new private root on an
owned volume. Source and pinned portal stage are read-only mounts; no host display,
D-Bus, PipeWire sockets, hardware devices or engine socket are mounted.

A worker launches private D-Bus, Phoc/pixman, PipeWire/WirePlumber, frontend and
portal backend. It enters a capture admission scope and consumes three changing
1280x720 frames through OpenPipeWireRemote. It intentionally does not record the
session identity, leaving the harder unidentified-receipt recovery case.

Two interruption scenarios are tested:

- The application exits with code 97 without cleanup. Its unresolved receipt
  survives and its container remains running. Retirement with no destruction proof
  refuses, even though the app's process lock has been released.
- The application remains active after frame proof. Exclusive retirement refuses
  while it holds the shared capture lock. The host then destroys that exact
  registered container with capture still active.

After destruction, successful enumeration confirms full container-ID absence on
the unchanged engine. Only then is terminal retirement authorized. It removes the
unidentified receipt and leaves the root permanently retired; update admission
cannot reuse it. Every test removes only its own labelled container and volume.
The worker has a 45-second fail-safe deadline, host commands have bounded waits,
and cleanup runs on test failures. No assertion is made about exact scheduling or
which service exits first during namespace destruction.

Run from the host against the extracted source and local reconstructed image:

```sh
OMARCHY_SCOPE_IMAGE=sha256:YOUR_RECONSTRUCTED_IMAGE_ID \
OMARCHY_SCOPE_STAGE=/absolute/path/to/staged/rootfs \
  python3 scripts/dependency-lab/test-portal-scope-host.py
```

The [frontend guide](PORTAL-FRONTEND-LAB.md) describes the image and portal stage.
The worker verifies runtime/XML/backend pins before capture. This adds one host
test containing two real interruption scenarios; the existing 333 injected-exit
cases are unchanged. Linux and host acceptance remain distinct in the test receipt.

This proves the registered private-container lifecycle, not a production phone
service boundary. The host engine and cooperating code remain trusted. There is
no live updater or global portal interception. Next: consolidate a single
reproducible acceptance command and machine-readable evidence for these Linux and
host checks, making the published recovery guarantees easier to reproduce.

Use the [acceptance command](PORTAL-ACCEPTANCE.md) to run Linux and host suites
from exact exported source and retain structured results plus hashed logs.
