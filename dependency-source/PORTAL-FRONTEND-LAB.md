# Headless frontend capture laboratory

This opt-in Linux container lab runs Phoc with a headless output and pixman,
private D-Bus/PipeWire/WirePlumber, xdg-desktop-portal and the pinned portal-wlr.
It never connects to the phone, host display, host buses or hardware devices.

## Reconstruct the environment

First reconstruct the Arch builder using the [toolchain instructions](DEPENDENCIES-PREVIEW.md#reconstruct-the-toolchains).
The frontend overlay lock is `packaging/portal-frontend-lab.lock.json`: 50 exact
package archives, versions, hashes and upstream license identifiers. Supply a
cache containing those archives. Recorded rolling mirror URLs may expire; retain
the verified cache. Hash pinning does not claim fresh package-signature verification.
No package archives or resulting images are distributed in this source preview.

```sh
python3 scripts/dependency-lab/build-frontend-lab.py \
  --base-receipt /path/to/arch/toolchain.json \
  --packages /path/to/package-cache --output /path/to/new-lab
```

The script validates the base lock and ARM64 image, rejects unsafe, missing,
symlinked, duplicated or changed archives, builds without network, and writes
`frontend-lab.json`. Use its `image_id` below. Stage portal-wlr as described in
[the payload guide](PORTAL-PAYLOAD.md). Mount only the source and staged payload:

```sh
docker run --rm --network none --cap-drop ALL --platform linux/arm64 \
  -v "$PWD:/src:ro" -v /path/to/staged/rootfs:/stage:ro \
  -e OMARCHY_FRONTEND_LAB=1 \
  -e OMARCHY_PORTAL_LAB_BINARY=/stage/usr/local/lib/omarchy-dock/portal-wlr \
  IMAGE_ID python3 /src/scripts/dependency-lab/test-portal-frontend.py
```

Runtime executable and xdg-shell XML hashes are checked before execution/code
generation. Temporary generated protocol code retains its upstream terms; it is
not included in the source release. Original painter and consumer fixtures are
integration code under the scoped MIT grant. Document portal FUSE warnings are
expected without device access; this test does not validate document/file portals.

## What the tests establish

Five tests consume actual changing 1280x720 frames through OpenPipeWireRemote.
Three frames must have the expected byte count and differing color sums. A
double-buffered original Wayland painter supplies changing pixels. This is
ext-image-copy-capture with software rendering, not the phone's wlr/GPU path.

Explicit Session.Close and application connection loss remove both backend and
frontend sessions plus the media node. Three repeated capture/close cycles pass.
Backend termination removes media/backend state but leaves frontend session state;
explicit frontend Close reconciles it. With the backend suspended, Request.Close
can time out and a response can still arrive after resume. A timeout is an unknown
outcome, not confirmed cancellation. Explicit Session.Close and a fresh session
cycle recover cleanly. Tests preserve those limits rather than asserting global
drain or successful cancellation.

This is measured capture/lifecycle evidence, not physical display acceptance or
interactive chooser validation. There is no production updater. Next: define
refusal and reconciliation rules for active, unknown and unresponsive clients before
adapting these contracts to a running service.
