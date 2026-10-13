# Portal payload and installation ownership

This host-only workflow stages the exact portal executable, upstream MIT notice
and runtime manifest. It neither installs files nor starts services. It requires
one of the verified portal binaries produced by the dependency build guide.

```sh
python3 scripts/dependency-lab/stage-portal.py --binary artifacts/rebuilt/portal/first/portal-wlr --output artifacts/staged/portal
python3 scripts/dependency-lab/test-stage-portal.py
python3 scripts/dependency-lab/test-portal-ownership.py
```

The three files are placed under `rootfs/usr/local/lib/omarchy-dock/`. The binary
mode is0755; the notice and manifest modes are0644. Staging verifies all three
installed hashes, including the manifest constructed from the upstream commit,
version, binary hash and patch hash. It verifies patch identity, rejects input
symlinks and occupied output directories, and publishes the complete local stage
through a final directory rename. It normalizes file timestamps to zero.

`ownership.json` records the three exact paths, modes and hashes, the dependency
lock hash and `activation: none`. It contains no machine paths or device state.
The receipt is an inventory, not a signature or authorization. The staged binary
is an ARM64 artifact even when staging runs on another host. The source release
does not distribute this generated payload.

## Ownership boundary

The `omarchy-portal` owner may manage exactly these regular files:

| Target below `/usr/local/lib/omarchy-dock/` | Mode |
| --- | --- |
| portal-wlr | 0755 |
| portal-LICENSE | 0644 |
| portal-manifest.json | 0644 |

No directory is exclusively owned. Dock service sources and Omarchy shell files
belong to their separate packages. Bluetooth allowlists, user profiles, system
portal packages, native USB services, Mesa, kernel modules and service units are
outside this ownership boundary. A replacement must not adopt existing unowned
files, even if their hashes match. The existing phone predates this receipt:
first adoption therefore requires a separate explicit migration with snapshots
and validation, not an automatic overwrite.

## Offline plans

`portal-ownership.py` is a pure planner over JSON inventories. It does not inspect
the host filesystem or invoke an installer. Its observed input must explicitly
map each of the three relative target paths to either `null` (absent) or an object
with `sha256` and a four-digit `mode` string. Symlink, partial, duplicate, private
or outside paths are rejected. Existing files require a previous owner receipt
and exact matching observed hashes/modes.

```sh
python3 scripts/dependency-lab/portal-ownership.py --candidate artifacts/staged/portal/ownership.json --observed /path/to/offline-observation.json --output artifacts/portal-plan.json
```

For an upgrade, also pass `--previous /path/to/previous-ownership.json`. The output
classifies paths as create, replace or unchanged. Receipt digests bind the plan to
the caller's inputs; they do not authenticate those inputs. The library `check`
function validates the whole observation before returning any rollback actions.
It accepts a partially applied update only when every file is exactly its known
before or after state. Unknown changes reject the entire operation. Rollback
restores verified old bytes for replacements and removes only files created by
that transaction. Already-restored files produce no action. Deletion of an old
package file is deliberately outside this version's plan format.

## Required executor contract

These requirements define future installation; they are not implemented by the
planner and passing its tests does not prove crash durability or a live rollback.

1. Validate source receipts and all staged bytes against the approved release.
   Recheck the filesystem under an exclusive update lock using no-follow file
   descriptors; reject symlinks, hardlinks, special files and overlapping owners.
2. Coordinate the portal process lifecycle. Quiesce portal clients and the owned
   process through a reviewed hook before replacement. Preserve the unrelated
   handset session. File renames alone are not an atomic multi-file activation.
3. Snapshot old bytes and exact ownership, mode, timestamps and extended attributes.
   Persist and fsync backups and a write-ahead transaction journal before changing
   any file. Preserve absence as a distinct before-state for first installation.
4. Use fsynced temporary files and same-directory replacement, checking expected
   old/new identities before each action. On interruption, verify the whole group,
   restore in reverse order and restore metadata. Never clobber external drift.
5. After all files pass readback and the portal passes its runtime health check,
   atomically commit the owner receipt. Keep backups until that commit is durable;
   recovery must handle interruptions before and after the receipt switch.
6. Failure to restore, restart or validate must remain explicit. Do not claim a
   successful rollback based solely on file hashes or restart the phone as a
   fallback. No device access is necessary for the next isolated executor tests.

The existing dock transaction core is limited to marked test roots and replacing
existing regular files. It cannot yet fulfill creation, receipt commit and portal
lifecycle requirements above. Do not lift that restriction to apply this plan.

## Validation scope

Two stages from independently rebuilt portal executables match all bytes/modes
and all three installed pins. Synthetic planner tests exercise no-op, unowned
collision, drift refusal and each of the four file-level interruption boundaries
of a three-file upgrade. These are policy checks, not power-failure injection or
new on-device acceptance. GPU validation and physical docking checks remain
separate. Seven of ten external file pins now have exact staged/reconstructed
outputs; the remaining three are the candidate Mesa libraries and metadata.
