# Isolated portal transaction laboratory

The Linux-only executor in `scripts/dependency-lab/portal-transaction.py` implements
storage transactions for the three portal payload files and their owner receipt.
It is a laboratory library, not a live installer. There is no live-root option,
service command, device connection or activation CLI.

## Run the tests

Use the package-reconstructed ARM64 builder from the dependency guide. Substitute
its receipt's `image_id` for `BUILDER_IMAGE` below:

```sh
docker run --rm --network none --cap-drop=ALL --cap-add=CHOWN --cap-add=FOWNER --cap-add=DAC_OVERRIDE -v "$PWD/scripts/dependency-lab:/src:ro" BUILDER_IMAGE python3 /src/test-portal-transaction.py
```

All writes occur inside the container's temporary filesystem. The source mount is
read-only. Those three Linux capabilities let one test preserve a different
uid/gid and its extended attributes; no device mount or privileged container is
used. Running the test file on macOS skips its Linux suite and does not constitute
validation. The Linux run must finish without skips or failures.

## Storage protocol

`initialize()` creates a private 0700 test directory immediately under the system
temporary directory, named `omarchy-portal-test-*`, with an exact marker. Every
operation requires that shape, marker, owner and permissions. `/`, unmarked roots,
symlink paths and roots elsewhere are rejected. The root contains a precreated
payload directory; first installation creates files, not arbitrary directories.

`prepare(root, stage)` verifies all staged bytes against the owner receipt and
checks previous ownership before acquiring a transaction directory. It snapshots
old bytes and modes, uid/gid, access/modification times and extended attributes.
The read-only stage contributes bytes/modes only: host-side extended attributes
are not propagated. The target test filesystem must support xattrs; unsupported
target metadata is an error, never silently dropped.
Absent files have an explicit absent before-state. Backup/candidate files and their
directory are synced before an atomically replaced, synced journal becomes the
prepare commit point. The target files are not changed during preparation.

`apply(root, health)` replaces the three files through same-directory temporary
files, with content/metadata readback and directory syncs. The callback must return
exactly `True`; false results or exceptions leave the old owner receipt intact and
require explicit recovery. This callback is a synthetic laboratory gate, not a
portal process health check. After the gate, payloads and backups are revalidated;
only then is `.portal-owner.json` replaced and the journal marked `committed-test`.

`recover(root)` prevalidates the entire group and all blobs, then restores payloads
in reverse order and the old owner receipt last. For first installation it removes
only files created by the transaction, restoring absence. Known partially written
temporary files can be discarded; unexpected contents, symlinks or hardlinks are
refused. Already-restored files are unchanged. Recovery can itself be interrupted
and repeated. Committed test transactions retain backups and can still be rolled
back explicitly; no finalization or automatic backup deletion is provided.

A crash before the first durable journal leaves preparation evidence and unchanged
targets. `recover` reports incomplete preparation and does not guess missing state.
The isolated root should be retained for inspection or discarded in its entirety
by the test harness. A retained transaction blocks another preparation. A crash
during apply must go through recovery; apply does not resume a partial operation.

## Tested boundaries

The 18 Linux tests include 128 child-process exits injected immediately after
writes, metadata operations, file syncs, renames, unlinks and directory syncs:

| Fixture | Prepare | Apply | Recover |
| --- | ---: | ---: | ---: |
| First installation | 14 | 27 | 13 |
| Existing owned installation | 22 | 27 | 25 |

For each exit, recovery is attempted twice when a journal exists. The final
payloads and owner receipt must equal the original bytes, metadata or absence.
Before the journal exists, targets must already be unchanged. Additional tests
cover no-op updates, failed/mutating health callbacks, short writes, injected I/O
and sync failures, different ownership, corrupt blobs/journals/temporary files,
lock contention, a second transaction, wrong roots, links and special files.

These are process-interruption tests on the container filesystem. They do not
simulate actual power loss, prove storage-controller durability, or establish
portal/client behavior. Descriptor-bound operations and cooperative locking avoid
following substituted links; this is not a defense against a hostile writer with
equal privileges changing the test tree concurrently. Drift checks preserve
unknown state rather than silently overwriting it.

## Still required before live installation

The [portal installation contract](PORTAL-PAYLOAD.md) remains the activation gate.
Reviewed process quiesce/restart and real health checks, first adoption of existing
phone files, source authorization and a durable finalization/retention policy are
not implemented here. Native USB/Mesa/kernel ownership is outside the transaction.
Do not relax the temporary-root restrictions to use this library on the phone.
