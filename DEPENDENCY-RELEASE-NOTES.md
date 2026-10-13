# Dependency-source preview 3

The portal ownership planner now has a separate Linux storage executor for isolated
test roots. It handles first-file creation, backups, owner receipt commits and
explicit rollback after interrupted updates. Target bytes, ownership, permissions,
timestamps and extended attributes are preserved on recovery. Live installation
remains disabled; there is no device or service activation mode.

## What changed

- Backups and a write-ahead journal are synced before target mutation. Replacement
  uses descriptor-relative temporary files, readback and directory syncs.
- Payloads change before a synthetic health gate; the owner receipt commits last.
  Whole-group readback is required before recording commit or rollback success.
- Recovery handles known before/after states, restores absence on first installs,
  refuses unrelated drift and can itself be interrupted and repeated.
- Read-only staging inputs contribute bytes/modes only. Unsupported destination
  extended attributes still fail closed instead of being silently discarded.

## Validation

All 49 tests pass from the final source tree in a networkless ARM64 Linux container,
with read-only source mounts and no skips. The 18 executor tests include 128 child
process exits across preparation, application and recovery for first installs and
upgrades. Each recoverable interruption is followed by two exact recoveries.
Pre-journal preparation failures leave unchanged targets and retained evidence.

Additional tests cover short writes, failed syncs/metadata writes, different file
ownership, corrupt backups/journals/temporary files, links/FIFOs, invalid roots,
lock contention, health failures and late rollback drift. The real previously
rebuilt portal payload also passes isolated create/upgrade and double-recovery
rehearsals. Its binary is not executed; the health callback is synthetic.

Two normalized source exports match. Source hashes, per-file licensing, links and
privacy checks pass. Earlier boot/desktop payloads and runtime dependency recipes
are unchanged. No phone was contacted, no runtime pin changed, and no new physical
acceptance is claimed.

## Limits and next step

Read the [transaction laboratory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-3/dependency-source/PORTAL-TRANSACTION-LAB.md).
These are process-interruption tests on a container filesystem, not power-cut or
storage-controller durability tests. The executor is restricted to private marked
temporary roots; no live-root override exists. A retained transaction blocks a new
one, and backups remain available for inspection and explicit rollback.

Next is safe finalization and retained-evidence cleanup in isolated roots, followed
by process lifecycle/health integration. Existing-device ownership adoption,
source authorization, Mesa validation and full installation closure remain separate.
Do not relax test-root restrictions to deploy this code to a phone.

This 54-file release contains source only, with scoped DionLabs MIT original
expression and retained upstream terms. It distributes no compiled payloads,
firmware, configured images or account state.

Archive dependency-source-preview.tar SHA256:
`ec5f6fa12ae5865e4333cafe18d74314eefd65dcd039e7dc57d4a024b038a958`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. Export-time source-preview.tar was renamed without changing bytes;
GitHub-generated repository archives differ. Frozen publication_cleared:false
records prepublication export state; approval covers this reviewed source only.
