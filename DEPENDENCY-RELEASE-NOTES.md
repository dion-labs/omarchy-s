# Dependency-source preview 15

The private recovery suite now has one host acceptance command. It validates the
release manifest hash and exact source membership/hashes/modes, rejects symlinks,
checks the immutable ARM64 image and builder lock, and pins the portal executable.
Linux tests use read-only source/stage mounts; host tests create only owned fixtures.

## Validation

The new command passes all 147 tests from extracted source: 145 Linux and 2 host.
Six new validator tests cover source drift, unsafe manifests, missing/extra files,
symlinks/modes, failed/skipped results and incorrect counts. A separate negative
invocation rejects a wrong manifest hash before tests and saves a failed receipt.
Existing 333 injected-exit cases and two real capture interruption scenarios remain
covered, without adding further crash scenarios in this release.

Per-suite JSON comes directly from unittest results. The final receipt records
source/runtime hashes, platform counts, per-suite outcomes and log/result hashes.
Source and portal identity are checked again after testing. An incomplete/running
receipt is not acceptance. Two normalized 88-file exports match; 87 attribution
entries and links verify. Boot/desktop inventories and runtime pins are unchanged.

## Limits and next step

See the [acceptance guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-15/dependency-source/PORTAL-ACCEPTANCE.md).
The manifest/runner must be obtained from a trusted release. Local diagnostics may
contain host paths and are not release assets. Abrupt host/engine death can leave
owned test fixtures requiring cleanup. This remains headless private-session proof,
not phone GPU/wlr acceptance, global client interception or production activation.

Next: add a reusable verifier for saved receipt, source/runtime and log identities,
so independently produced evidence can be compared without trusting summary text.
