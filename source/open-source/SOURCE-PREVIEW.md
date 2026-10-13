Signature/build-provenance follow-up: see `build/boot-repro/BUSYBOX-TRUST.md`. Earlier unverified-signature notes below describe the source-collection milestone.

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

# Source-only boot reconstruction preview

This is a private review candidate, not a published release or a licensed
standalone distribution. It contains explicitly allowlisted UTF-8 source,
configuration, patches, pins and notices for the native20 boot workflow.
It does not contain firmware, binary packages, compiled images, stock archives,
phone backups, accounts, credentials, pairing state, private evidence or Git history.

Read `build/boot-repro/OFFLINE-PIPELINE.md` and `BUSYBOX-SOURCE.md`. External archives
are acquired separately using their pinned manifests. The build requires a locally
available reconstructed ARM64 toolchain; source preparation does not install it.
Artifact/evidence path strings in recipes and locks describe required cache paths,
virtual mounts or historical results; the referenced private files are not exported.
The consolidated pipeline remaps derived inputs into a fresh run.

The preview intentionally covers the boot chain, not the entire phone/desktop
rootfs or all runtime services. Firmware rights, original integration licensing,
per-file attribution remain open. Signature verification is recorded in BUSYBOX-TRUST.md.
See ATTRIBUTION.md for the current source review and unresolved provenance. Existing third-party
notices are retained; no blanket root license is assigned. Publication requires a
separate complete-tree review and the remaining decisions recorded in the inventory.

Export from the working repository:

```sh
python3 scripts/release/export-source.py --output artifacts/source-preview-new
```

The explicit hash allowlist is `packaging/source-export.allowlist.json`. Every file
must match; parent symlinks, private trees, binary/NUL payloads, duplicate/unsafe
paths and existing outputs are rejected. Output contains a deterministic tar,
source tree and full manifest. There is no publish/install action. The allowlist
itself is retained as an outer manifest to avoid a self-referential hash cycle.
Heuristic scans are review evidence, not a guarantee that secrets cannot exist.

The current publication gates and conditional exclusions are recorded in
[the release decision checklist](RELEASE-DECISION.md). Passing export checks does
not resolve license scope or authorize publication.
