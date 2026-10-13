# Dependency-source preview 2

The portal executable could already be rebuilt, but its runtime notice and manifest
were still external installation inputs. This 51-file source preview adds a stager
that reconstructs all three exact files, with deterministic modes, timestamps and
an ownership receipt. Seven of the desktop's ten external hashes now reproduce.

It also defines a three-file installation ownership boundary and a pure offline
planner. Existing unowned files cannot be silently adopted; mismatched previous
state rejects an update. Partial rollback accepts only known before/after states
and refuses unrelated changes. The planner never reads or mutates target files.

## Validation

- 31 tests pass from the extracted source, including six staging and seven
  ownership tests. Synthetic cases cover creation, no-op, collision, drift,
  malformed inventories and every file-level interruption boundary of an upgrade.
- Two fresh offline portal builds from extracted source match the installed hash.
  Both stage into identical four-file trees (three payload files and receipt),
  also matching stages made from the previous independently rebuilt executables.
- All three portal payload hashes match the unchanged runtime dependency lock.
  Their ownership paths do not overlap the existing 40-file dock service package.
- Two source exports match exactly. Archive membership, hashes, relative links,
  per-file licensing and privacy review pass. Earlier boot/desktop payloads and
  dependency build recipes remain unchanged.

The previous four-component build evidence is retained; this milestone rebuilds
portal only because those recipes and inputs are unchanged. Package-reconstructed
builder receipts are reused and verified. No phone was contacted or modified.

## Scope and next step

Read [the portal payload contract](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-2/dependency-source/PORTAL-PAYLOAD.md) for staging
commands, ownership rules and the required executor behavior. No live installer
or crash-durable rollback is implemented by this planner. The next step is isolated
executor tests for creation, backups, receipt commits and recovery. Device adoption,
process lifecycle coordination and physical checks remain separate gates. The
existing marked-test-root restriction is unchanged.

Mesa remains a candidate with three differences from the installed build; runtime
equivalence and truthful candidate metadata remain open. Native hardware-helper,
kernel/gadget and full installation closure are also separate. This source release
does not distribute generated portal binaries or other runtime artifacts.

Original integration has a scoped DionLabs MIT grant. Inherited notices and patch
context retain their applicable licenses. The source-only archive contains 51 files.
Archive dependency-source-preview.tar SHA256:
`c62a3829ee8b99cb3a434df8b4c814877c841e1665d797268128e48e6b3235aa`.

Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. The archive's export-time filename was source-preview.tar; renaming
preserves its digest. GitHub-generated repository archives are different.
The frozen manifest's publication_cleared:false records its prepublication export
state; publication approval covers only this reviewed source package.
