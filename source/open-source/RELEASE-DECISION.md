# Source-only release decision checklist

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

Status: **private review candidate; not approved for publication**.
This checklist concerns the allowlisted boot-reconstruction sources only. It does
not authorize a release, a license assignment, upstream messages or phone access.
Machine-readable decisions: `packaging/source-release-decisions.json`.

## Proposed first release

Publish a curated source tree and deterministic source archive with its outer
manifest and SHA256 receipt. Describe it as a research boot-reconstruction source
preview for the S9+, with separately acquired dependencies. It is not an installable
phone OS, complete Omarchy distribution, firmware release or supported flashing kit.

The exact candidate is the `tree/` and `source-preview.tar` produced by
`scripts/release/export-source.py`; its adjacent `manifest.json` identifies every
file, hash and mode. Any content change requires a new archive and renewed review.
The checklist does not embed its own archive hash, avoiding a circular identity.

Exclude firmware, stock archives, boot images, binary packages, rootfs/account data,
private evidence, Git history, toolchain images and phone-specific secrets. The
notice-free vendor DTS excerpt is already excluded. Candidate Samsung DTS source
files are also excluded; their hashes and carefully labelled notice evidence remain.
Fetch/import recipes refer to external inputs without bundling them.

## Decisions that remain open

| ID | Decision / owner | Evidence and acceptance condition |
| --- | --- | --- |
| SCOPE | D: approve the boot-only scope and claims | Approve the exact fresh manifest/archive; do not imply full desktop packaging, one-command installation or hardware reliability. |
| ORIGINAL | D: confirm scope and choose terms for original integration | The bounded per-file content review is complete in `PER-FILE-REVIEW.md` and `source-attribution.json`; sole authorship is not proven. Identify the exact files/deltas covered before adding notices. Do not apply a blanket license over imported code. |
| PATCHES | Maintainer review, with D authorizing any inquiry: resolve included dtbtool contribution scope | `LINEAGE-SCOPE.md` and `dtbtool-patch-scope.json` trace all ten commits: eight C changes retain the source notice; two Makefile changes have no own notice. Record a supported disposition, or remove these patches from a deliberately reduced candidate and revalidate its documented build limits. No terms have been assigned by this checklist. |
| REVIEW | Maintainer: finish exact-tree attribution, privacy and packaging review | Per-file content dispositions are complete; final license/privacy/packaging acceptance remains open; unresolved NOASSERTION entries are not automatically cleared by successful tests. Review retained notices and locally adapted code. Inspect scan findings and final tree, including metadata. |
| PUBLISH | D: approve destination and publication | After the above, select repository, version/tag and release description, and authorize publishing the identified candidate. No repository/release has been created for this task. |

SCOPE, ORIGINAL and PUBLISH are deferred user decisions. PATCHES may need a narrowly
scoped upstream inquiry; no inquiry has been sent. REVIEW can continue locally.
The current candidate is not ready to publish simply because its exporter passes.

## Conditional questions, not blanket source-only blockers

- **Original flattened DTS lineage:** the file itself is not exported. Its unknown
  source/configuration chain limits authored-source and complete-rebuild claims.
  Resolve it before adding that source or claiming its authored origin is closed;
  preserve the limitation for a metadata/recipe-only release. Do not assert that
  resolving the entire Samsung history is automatically required just to publish
  the curated metadata. Review the exact chosen scope.
- **Firmware rights:** firmware remains excluded. No permission to distribute blobs
  or compiled images follows from source-preview review. A future binary release
  needs its own decision and evidence.
- **Hardware checks:** no new physical test is required to review/export source.
  Installation or runtime changes retain their separate recovery/maintenance gates.
- **BusyBox tests:** exact executable/package reconstruction is measured; the isolated
  `hostname-d-works` failure remains disclosed. Do not claim the complete upstream
  suite passed or that a binary release is cleared.

## Evidence already available

These are measured technical results, not approvals:

- Allowlisted UTF-8 source export; deterministic ordering, modes and timestamps;
  private-tree/symlink/path/hash protections. Outer manifest binds the selected tree.
- Exact recorded BusyBox executable and package rebuild, derived initramfs match,
  and retained trust/build receipts. Historical offline boot reconstruction matches
  native20; no new kernel rebuild is needed for checklist-only changes.
- All 18 exported patches traced to pinned bases; aggregate kernel changes have
  mixed provenance. Ten dtbtool patch IDs match the contributor branch.
- Eight DTS history commits and vendor/archive blob identity; two exact UFS matches.
  The 37-file Samsung-authored candidate is dated 2018 and is not proven to generate
  the 2020 firmware-labelled input; one generated configuration is unavailable.
- Existing source, origin, notice and scope validators, negative export tests and
  heuristic sensitive-pattern checks. Scans cannot prove absence of all secrets.

## Final preparation sequence

1. Resolve the chosen scope and licensing dispositions; update notices and claims.
2. Refresh explicit allowlist hashes. Generate two new output directories with the
   exporter; compare archive bytes and inspect every selected path. Keep historical
   previews and evidence separate from the publication payload.
3. Run the commands below against the source root. Also run the validators against
   the exported tree with the outer allowlist supplied at its expected path; keep
   that verification copy separate from the immutable archive. Optional cached-source
   replay is distinct from checks runnable using only the export.
4. Record archive SHA256, manifest SHA256, file count, test/scan results, unresolved
   limitations, decision dispositions and the exact approved destination/version.
5. Present that concrete packet for publication approval. After authorization,
   publish only those artifacts, verify downloadable bytes and update links. A commit
   alone is not a packaged release. This project currently has no packaged release.

```sh
python3 scripts/release/check-source-attribution.py
python3 scripts/release/check-boot-inventory.py
python3 scripts/release/check-lineage-scope.py
python3 scripts/release/test-export-source.py
```

Changes outside the current scope require a new decision packet. No physical tests,
account login or external messaging are needed to prepare this checklist.
