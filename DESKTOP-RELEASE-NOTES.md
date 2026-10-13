# Desktop-source preview 1

This source-only preview adds the S9+ dock services and pinned Omarchy shell
adaptation alongside the existing boot-source preview. It contains61 reviewed
files, including staging tools, dependency records, tests and a build guide.

Original DionLabs contributions have a scoped MIT grant. Three inherited Omarchy
files retain their MIT notices; four adaptations explicitly preserve upstream
expression and attribution. Fonts, artwork, generated shell payloads, graphics
binaries, firmware and private device configuration are excluded.

## What was checked

- Two normalized source exports are identical.
- 23 tests pass, plus two negative checks for license scope and source drift.
- 13 upstream source/notice objects match their pinned Git versions.
- Two service stages match42 files; two shell stages match243 files, including
  receipts. All bytes and modes also match the previous candidate.
- Exact archive membership, source hashes, links and bounded privacy checks pass.

These are host-side checks from an extracted source archive and a clean pinned
upstream checkout cloned from the local cache. No phone was contacted or updated.
This is not a complete dependency closure, new runtime acceptance or an installer.
The39 package versions are compatibility observations;10 external file hashes do
not replace acquisition/build instructions for those dependencies.

## Get started

Read desktop-source/DOCK-PREVIEW.md in the repository, or DOCK-PREVIEW.md inside
the release archive. Copy the separate dock-source-export.allowlist.json to
packaging/dock-source-export.allowlist.json inside an extracted working copy
before running check-dock-source.py. Build commands only stage local output.
Runtime probes are separate and must not be run against an active session as an
archive check. Do not copy a staged rootfs over a running desktop.

Archive desktop-source-preview.tar SHA256:
`80207bd7705e3f414a5b07e5d0f62b750fedb07d1c5069ed346d3d025851be2b`.
The assets also include manifest.json, dock-source-export.allowlist.json and
SHA256SUMS. The manifest's archive digest refers to this release archive, whose
export-time filename was source-preview.tar; renaming does not change its bytes.
GitHub-generated repository archives have different contents and hashes.

The source retains frozen staging-only and review metadata. Publication approval
covers this source archive, not generated runtime output or excluded assets.
The boot-source preview remains available and unchanged.
