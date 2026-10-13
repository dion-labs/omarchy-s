# Dependency-source preview 1

This 46-file source preview reconstructs external userspace dependencies needed by
the partial S9+ desktop port: the Weston input module, patched Aquamarine and
portal, opt-in Mesa workaround, and two native USB owner source files. It includes
archive pins, package-only builder recipes, tests, scoped licensing and notices.
No binaries, firmware, configured images or private state are included.

## Validation

- Two normalized source exports match exactly; hashes, membership, links and
  per-file attribution/privacy review pass. Five upstream notice files match
  their pinned archive members.
- 18 focused tests pass, including source drift, symlinks, no-overwrite, package
  identity and offline acquisition checks.
- Fresh Aquamarine/Mesa/Weston downloads match their hashes; a fresh portal Git
  fetch and archive match the pinned commit's archive hash.
- Four paired offline builds pass. A separate exported-source rehearsal also
  builds each component twice and matches the first run's bytes/modes/symlinks.
- Input-seat, Aquamarine and portal match three installed binary hashes. Native
  USB reconstruction matches both installed owner source hashes exactly.
- Mesa has 37 repeatable output entries. Repeatability does not establish runtime
  equivalence: the previously measured source-path differences from installed
  Mesa remain an explicit deployment gate. No runtime pins are changed.

The rehearsal reuses package-reconstructed ARM64 builders, checking receipts
against their locks and recipes. It does not repeat the full compiler/package
build, prove arbitrary receipts trustworthy, or claim cross-host image identity.
No phone was contacted, and there is no new physical acceptance.

## Get started and limits

Read dependency-source/DEPENDENCIES-PREVIEW.md in the repository, or
DEPENDENCIES-PREVIEW.md in the archive. It documents public acquisition,
package-only toolchain reconstruction, paired offline builds and source staging.
Use fresh output directories. USB owner sources are not standalone services:
matching hardware helpers, kernel modules, rescue gadget and readiness units
remain separate. Installed portal/Mesa metadata are not recreated here. These
recipes do not establish full installation closure or authorize device activation.

Original DionLabs expression has scoped MIT terms; Aquamarine context retains
BSD-3-Clause and the remaining upstream declarations/selectors/notices retain
their applicable terms. Acquiring dependencies does not grant blanket permission
to redistribute their binaries.

Archive dependency-source-preview.tar SHA256:
`82a8372ded61447062e46f747e936b96642569c46f649b819792ee122e7b44c7`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. The archive was exported as source-preview.tar; its digest is unchanged
by renaming. GitHub-generated repository archives have different contents.
The frozen manifest's publication_cleared:false records its prepublication export
state; publication approval covers only this reviewed source package. Earlier
boot and desktop previews remain unchanged.
