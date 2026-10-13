# S9+ boot reconstruction source preview

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

Start here for this curated source candidate. It is research reconstruction source
for native20 on the Exynos S9+, not a full Omarchy distribution, installer, rootfs,
firmware bundle or supported flashing kit. Publication remains unapproved; original-contribution licensing is recorded in
[LICENSING.md](LICENSING.md). No command below contacts a phone.

## Verify the supplied candidate

The review bundle supplies `source-preview.tar`, `manifest.json` and
`source-export.allowlist.json` beside this source tree. Verify the bundle checksums
against the independently reviewed candidate identity before extraction. Copy the
matching outer allowlist to `packaging/source-export.allowlist.json` in a disposable
working copy; it is deliberately outside the tar to avoid a self-hash cycle.

From that source root:

```sh
python3 scripts/release/check-source-attribution.py
python3 scripts/release/check-boot-inventory.py
python3 scripts/release/check-lineage-scope.py
python3 scripts/release/test-export-source.py
python3 scripts/boot-repro/test-build-toolchain.py
python3 scripts/boot-repro/test-pack-dtbh.py
```

These validate selected source/evidence structure and synthetic guards; they do
not clear licensing, prove absence of secrets or rebuild a kernel.

## Prepare and reconstruct

1. Follow [boot builder setup](build/boot-repro/TOOLCHAIN.md) for explicit acquisition,
   the isolated build and its local receipt.
2. Follow [offline pipeline instructions](build/boot-repro/OFFLINE-PIPELINE.md) to
   acquire the remaining pinned inputs, preflight and reconstruct all five stages.
3. Compare outputs against the pinned hashes. Keep all evidence local. There is no
   flashing or activation step in this preview.

Historical evidence directories are not supplied. Replaying trust/source history
checks needs their separately acquired inputs. BusyBox signature/environment and
exact executable/package results are documented in
[BUSYBOX-TRUST.md](build/boot-repro/BUSYBOX-TRUST.md) and
[BUSYBOX-UBUNTU-ENV.md](build/boot-repro/BUSYBOX-UBUNTU-ENV.md); the isolated hostname
test failure remains disclosed. The preview does not package desktop services or
the Arch userspace toolchain.

## Retained limitations

The historical installation UUID/layout guard and build hostname remain unchanged;
retention was approved by D. The initramfs includes an intentionally unauthenticated
lab USB console. Do not treat this as a general-purpose secure phone system or reuse
its fixed installation guard on another filesystem without a separately reviewed design.
Firmware and source archives must be acquired separately; no redistribution clearance
is inferred from a recipe. All scripts require explicit interpreters (mode 0644).

See [per-file attribution](open-source/PER-FILE-REVIEW.md) and
[release decisions](open-source/RELEASE-DECISION.md). The scoped original MIT grant is approved. The disputed dtbtool patches are excluded;
vendor DTS and firmware redistribution remain outside this source-only preview.
Publication still requires D’s approval.
