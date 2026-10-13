Exact reproduction follow-up: [BUSYBOX-UBUNTU-ENV.md](BUSYBOX-UBUNTU-ENV.md) records a matching executable and full package. Earlier mismatch notes below are historical.

Signature/build-provenance follow-up: see [BUSYBOX-TRUST.md](BUSYBOX-TRUST.md). Earlier unverified-signature notes below describe the source-collection milestone.

# BusyBox source and static configuration

The ARM64 binary package declares Source `busybox`, Version
`1:1.36.1-6ubuntu3.1`, Architecture `arm64`; its version banner agrees.
The matching Ubuntu DSC and original/debian source archives are pinned in
`packaging/busybox-source.lock.json`. Their SHA256/size values match the DSC.
The original tarball signature and signed DSC are retained; signing-key trust
has not been verified. HTTPS retrieval and hash consistency are not signature trust.

Fetch archives with the existing fetch-packages helper, then reconstruct offline:

```sh
python3 scripts/toolchain-lab/fetch-packages.py packaging/busybox-source.lock.json artifacts/busybox-source
python3 scripts/boot-repro/prepare-busybox.py --archives artifacts/busybox-source --output artifacts/busybox-source/new-run
```

The pinned builder uses `dpkg-source --no-check -x` to apply the quilt patch series,
then the source's `debian/rules configure-static` and `build-static`. Linux OS
configuration is concatenated with `debian/config/pkg/static`; silentoldconfig
regenerates `.config`, which is compared byte-for-byte against that packaged file.
Build rules, control, changelog, copyright, patch series, generated config, applet
list and applied source archive are retained in the output. The latter excludes
build directory `b/` and is a local corresponding-source preparation artifact.
The original source archives remain available separately.

The source-built executable exposes the same 272 applets as the pinned package.
This is consistent with 271 initramfs applet symlinks: `busybox` itself is not a
symlink. Its binary hash differs from the Ubuntu binary; exact distro build
reproduction, buildinfo/toolchain details and signature verification remain open.
The existing boot pipeline continues to use the original pinned binary package.
No replacement binary has been installed or embedded in native20.

This gathers the matching source version, patches, packaging and configuration;
it does not declare license compliance complete or authorize binary publication.
Full private evidence: `local-evidence/busybox-source-20261012/`.
