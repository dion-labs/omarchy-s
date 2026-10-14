# Reproduce the private recovery acceptance suite

Run one host command from a freshly extracted source archive. Keep the release
manifest outside that tree; use its independently verified SHA-256 from the release
checksums. Build the private frontend image and stage the pinned portal using the
[frontend guide](PORTAL-FRONTEND-LAB.md). No runtime image/package is distributed.

```sh
python3 scripts/dependency-lab/run-acceptance.py \
  --manifest /path/to/release/manifest.json \
  --manifest-sha256 VERIFIED_MANIFEST_SHA256 \
  --builder-receipt /path/to/frontend-lab.json \
  --stage /path/to/staged/rootfs \
  --output /path/to/new-acceptance-results
```

The output directory must be new and outside source/stage. Source membership,
hashes and modes must match the manifest exactly; symlinks are rejected. The
runner checks the immutable ARM64 image ID, builder lock hash and portal binary
hash. Runtime executables/protocol inputs are also checked by the frontend tests.
The manifest and runner must come from a trusted release; checking a manifest
hash does not authenticate an untrusted download by itself.

Linux suites run with source/stage read-only, network disabled and only the three
metadata capabilities required by existing filesystem tests. The host engine suite
creates and destroys its own labelled disposable containers/volumes. It never
mounts the engine socket into a test container. No phone or host desktop session
is contacted. Docker, Python3 and the locally reconstructed image/stage are required.

`acceptance.json` records status, manifest hash, source count, image/build-receipt/
lock/backend hashes, per-suite counts, Linux/host totals, elapsed time and log/result
hashes. `case-N.json` files come directly from unittest results, not log parsing.
The runner rejects missing results, wrong counts, skips, expected failures and
ordinary failures. `linux.log` and `host.log` preserve detailed output. Source and
portal hashes are rechecked at completion. Current acceptance is147 tests:145 Linux
and2 host; the existing333 injected-exit cases and two real capture interruption
scenarios are exercised by these suites, not independently counted by the runner.

Status starts as running and becomes passed only after every check. Ordinary
errors produce a failed receipt; partial case files/logs remain available. A hard
host kill can leave status running, which is not acceptance. Each phase has a
600-second outer bound and the runner attempts to remove its own Linux container;
host fixture tests have their own bounded cleanup. Abrupt termination of the host
or Docker engine can still require cleanup of leftover owned test fixtures.
Do not publish result logs without inspecting them: local diagnostics may contain
host paths. Source releases include the runner, not local evidence or credentials.

These are private recovery guarantees, not a production update authorization,
global portal inventory, physical display check or phone GPU/wlr acceptance.
Next: add a reusable verifier for saved receipts and their source/runtime/log
identities, so independent runs can be compared without trusting a summary alone.
