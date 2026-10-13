# Dependency-source preview 4

Completed portal test transactions can now be finalized without deleting their
backups, allowing subsequent updates in the same isolated root. Explicit cleanup
validates a named archive and close digest before deleting retained evidence;
interrupted cleanup resumes from a durable receipt.

## Changes and validation

Finalization checks terminal target state, writes a synced close decision and
archives the transaction under a unique ID. Rollback stops at that decision;
interrupted finalization resumes explicitly. Cleanup inventories and verifies all
remaining evidence before deletion, preserves unknown state, and retains a small
completion receipt. Old archives can be cleaned while a later transaction exists.

All 60 tests pass without skips from the extracted archive in networkless ARM64
Linux with read-only source mounts. The 200 abrupt child-process exits cover
preparation, apply, recovery, finalization and cleanup. Eleven retention tests
include repeated changed updates, failed-health recovery, saved cleanup-handle
recovery, legacy journal refusal, metadata drift, links, short writes and sync
failure. The previously rebuilt real portal payload passes create/upgrade,
repeated-update, double rollback and cleanup checks with exact final state.
Its binary is not executed; health callbacks remain synthetic.

Two normalized exports match. All 56 files pass exact archive/tree checks;
55 attribution entries match their source hashes, and documentation links and
privacy findings have been reviewed. Earlier boot/desktop payloads, dependency
recipes and runtime pins are unchanged. No phone was contacted or modified.

## Scope and next step

The [laboratory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-4/dependency-source/PORTAL-TRANSACTION-LAB.md)
describes explicit archive handles and crash recovery. The libraries only accept
private marked temporary roots. There is no live-root override or activation CLI.
These process-interruption checks do not prove physical power-cut durability.
Incomplete preparation remains available for inspection. Older ID-less journals
can recover but cannot use the new finalizer. Automatic expiration and cleanup
receipt compaction are not implemented.

Next: isolated process lifecycle and health-contract integration. Real portal
quiesce/restart, existing-device adoption, source authorization and Mesa runtime
validation remain separate gates. Do not relax laboratory root restrictions.

This is source only: original DionLabs integration has scoped MIT terms and
inherited notices retain their terms. No binaries, firmware, images or account
state are distributed.

Archive dependency-source-preview.tar SHA256:
`ae6576cc921780162ba41dc0c27dce88968260521fc30d83dc52d8b08b67c54e`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. Export-time source-preview.tar is renamed without changing bytes;
GitHub-generated repository archives differ. Frozen publication_cleared:false
records prepublication export state; approval covers this reviewed source only.
