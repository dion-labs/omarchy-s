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
back explicitly until a durable finalization decision is written.

A crash before the first durable journal leaves preparation evidence and unchanged
targets. `recover` reports incomplete preparation and does not guess missing state.
The isolated root should be retained for inspection or discarded in its entirety
by the test harness. An active retained transaction blocks another preparation until finalized. A crash
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
Real process quiesce/restart and health checks, first adoption of existing
phone files, source authorization and an operational retention policy are
not implemented here. Explicit laboratory finalization and pruning are implemented. Native USB/Mesa/kernel ownership is outside the transaction.
Do not relax the temporary-root restrictions to use this library on the phone.

## Finalization and explicit cleanup

Run `test-portal-retention.py` with the same Linux container command above in
place of `test-portal-transaction.py`. Its 11 tests add 72 abrupt process exits:
six finalization and thirty pruning boundaries for each committed/rolled-back case.
Together the dependency package has 60 tests and 200 abrupt-exit cases.

`portal-retention.py` is a separate library with the same root restrictions and
cooperative lock. `finalize(root)` requires a completed commit or rollback and
exact whole-group state. It writes a synced close decision before renaming the
transaction to a unique retained archive. Backups remain intact, another update
can start, and rollback eligibility ends at the close decision. An interruption
after that decision must resume finalization, not rollback. Repeating finalization
when no active transaction exists returns None; `histories(root)` discovers saved
archive handles. Older journals without a transaction ID remain recoverable but
cannot be finalized by this protocol. Incomplete preparation is still retained
for inspection, never implicitly discarded.

`prune(root, history, close_sha256)` requires an explicit archive name and exact
close digest. It verifies every retained entry before recording a durable deletion
receipt, then removes only inventoried evidence. It preserves payloads and their
owner receipt, even while a later transaction exists. Unexpected files, links or
metadata/content drift cause refusal. Repeated cleanup resumes from the durable
receipt, including after the close record or archive directory has been removed.
`prune_receipts(root)` recovers the necessary handle after an interrupted cleanup.
Small completion receipts remain; automatic expiration and receipt compaction are
not provided. Pruning permanently removes those archived rollback blobs.

Tests also cover repeated changed versions, failed-update recovery, cleanup with
a later active transaction, legacy journal refusal, saved-handle discovery, short
writes, sync failure and unknown-state preservation. These remain isolated storage
checks with synthetic health callbacks, not service or physical-power validation.

## Simulated service lifecycle

`portal-lifecycle.py` coordinates an already-owned, initially healthy installation
inside the same marked temporary roots. Run `test-portal-lifecycle.py` with the
Linux container command above. Ten tests add 95 abrupt exits (51 update and 44
recovery), bringing the package to 70 tests and 295 abrupt-exit cases.

The adapter contract is four synchronous methods, each requiring exactly True:
`quiesce()`, `stopped()`, `start(identity)` and `healthy(identity)`. The identity
maps the three payload paths to their expected SHA256 and mode. Quiescence must
cover the owned process and its clients. A successful start is not sufficient:
health must establish the expected version is serving correctly. All callbacks
run under the transaction lock. Adapters must not recursively call transaction
operations. The supplied tests use a persistent fake service model, not an OS
process; hook calls are atomic in that model. There is no shipped real adapter,
service-manager command, timeout supervisor or activation CLI.

Update first verifies old-service health, then syncs recovery intent before any
side-effecting callback. It quiesces and verifies stop before file replacement,
starts the candidate and checks health before committing the owner receipt.
A callback failure, exception or interruption leaves explicit recovery pending.
Repeated apply is refused. Recovery rechecks all files, quiesces again, restores
old payloads and receipt, starts the old version, checks health and revalidates
files before marking lifecycle recovery complete. Repeating recovery is supported.
Low-level apply/recover entry points reject lifecycle-managed journals, and
finalization refuses them until lifecycle commit or recovery has completed.

Tests cover stop/start/health failures, non-boolean results, callback exceptions,
failed old-service restart, locking, unrelated state preservation, target drift,
mutating health callbacks and interrupted durable phases. Each process-exit case
restores exact prior file state and fake-service identity; recoverable lifecycle
states are recovered twice. Existing unhealthy services and first installations
are refused before quiescence. Initially stopped services, real client draining,
hook timeouts, child ownership, IPC health and actual portal behavior remain open.
Next is a disposable child-process adapter with bounded stop/start and identity
checks, still isolated from the phone and real services.
