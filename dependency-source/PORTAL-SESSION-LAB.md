# Real backend session laboratory

This suite executes the previously rebuilt, hash-pinned `portal-wlr` binary on an
isolated D-Bus and PipeWire session. It uses an original registry-only Wayland
fixture, not a rendering compositor. Eight tests verify backend API readiness and
explicit closure of known sessions; they do not validate capture or real clients.
The existing storage/lifecycle suites remain separate and unchanged.

## Reproduce

Reconstruct the ARM64 builder and stage the portal using the
[dependency guide](DEPENDENCIES-PREVIEW.md) and [payload guide](PORTAL-PAYLOAD.md).
Set `BUILDER_IMAGE` to that builder receipt's image ID, and `PORTAL_STAGE` to the
absolute staged directory containing `rootfs/`. From this source package:

```sh
docker run --rm --network none --cap-drop=ALL \
  -e OMARCHY_PORTAL_LAB_BINARY=/stage/rootfs/usr/local/lib/omarchy-dock/portal-wlr \
  -v "$PWD/scripts/dependency-lab:/src:ro" -v "$PORTAL_STAGE:/stage:ro" \
  "$BUILDER_IMAGE" python3 /src/test-portal-session.py
```

The test refuses a non-container environment or a portal hash other than
`e3c43847acc34cd113f101087de3c113e7ae821c933515b0c55b2c92cbb7eb3b`.
No host socket, device, home directory or writable host mount is required. It
constructs a fresh environment rather than inheriting desktop/session variables.
All subprocesses are terminated and waited for by cleanup; all writes are inside
container temporary directories. Do not mount a host runtime directory or use a
host D-Bus address. Without the explicit binary environment variable the suite
skips; a skipped run is not acceptance.

The reconstructed builder supplies dbus-daemon, PipeWire, gdbus, a C compiler,
wayland-scanner and wayland-protocols. Three protocol XML input hashes are checked
before generating temporary headers/code: ext-image-copy-capture,
ext-image-capture-source and ext-foreign-toplevel-list. These inputs come from the
pinned builder package inventory; generated protocol code and binaries are not
included in the source preview and retain upstream terms. The fixture itself is
original scoped MIT integration. It advertises wl_shm and capture manager globals
but deliberately rejects capture requests and supplies no outputs or frames.

## Measured contract

The pinned backend is from upstream commit
`34153094662acd713241ca6cbbb20003ef67da5f`, with this project's existing patch.
Source inspection and execution agree on ScreenCast interface version **4**.
The suite checks:

- The backend bus name resolves to a unique owner whose D-Bus PID matches the
  launched process; `/proc/PID/exe` matches the reviewed binary hash. The expected
  ScreenCast version and monitor source capability can be queried. Ownership is
  checked again after the readiness query.
- Three CreateSession calls succeed. Each short-lived gdbus caller exits, yet its
  backend Session object remains. Explicit `org.freedesktop.impl.portal.Session.Close`
  removes each known object. A duplicate close fails; it is not silently accepted.
- Draining the test-owned session list before shutdown succeeds. Restart yields a
  new owner and no old session object; a new create/close cycle works.
- PipeWire or Wayland connection loss ends the backend and removes readiness.
  Starting a second backend without replacement fails without displacing the first.
- A suspended backend fails readiness and cannot confirm drain within the outer
  deadline. The known session stays pending. After resume, explicit close succeeds.

The gdbus method timeout alone did not bound an unresponsive invocation, so every
call also has a two-second subprocess deadline. A timeout is a failure with an
unknown operation outcome, never evidence that a session closed. A later adapter
must reconcile that uncertainty rather than assume a retry is harmless.

## Limits and implications

These are implementation-backend interfaces, called directly on a private bus.
The normal xdg-desktop-portal frontend is absent. Its behavior on application
exit can differ: retaining a backend session after these test callers disconnect
is not evidence that normal desktop applications leak sessions.

The backend has no general drain-all API in the inspected implementation. The
laboratory can close only the sessions it created and tracked. It does not prove
that unknown sessions, pending requests, chooser processes or active PipeWire
streams have drained. Bus ownership and version checks establish API readiness,
not successful screencasting. The registry-only fixture uses the ext capture path;
the phone's wlr compatibility path, active media streams, cancellation and GPU
behavior remain untested here. No production update adapter is enabled.

Next: exercise the frontend and actual capture-session cancellation with a real
headless compositor, then define how an updater refuses active or untracked clients.
Keep all live phone adoption and physical acceptance gates unchanged.
