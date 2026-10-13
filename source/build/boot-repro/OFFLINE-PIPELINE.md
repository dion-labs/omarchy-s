# Offline native20 boot pipeline

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

This host-only pipeline reconstructs the native20 boot image from pinned inputs.
It does not install anything, access a phone, publish artifacts, or create a full
Arch/Omarchy root filesystem. Desktop/service packaging is a separate track excluded from this source preview.

## Prerequisites and acquisition

Use Python 3.9+, host `patch`, Docker with Linux ARM64 execution, at least 6 GiB
available to Docker and enough scratch disk for a full kernel build. Reconstruct
and validate the Mesa builder first using [TOOLCHAIN.md](TOOLCHAIN.md); this
pipeline consumes that checked builder, it does not rebuild toolchains itself.

Network acquisition is a separate, explicit phase using
`scripts/toolchain-lab/fetch-packages.py <lock> <directory>`:

| Lock | Destination | Purpose |
| --- | --- | --- |
| packaging/kernel-sources.lock.json | artifacts/kernel-source-closure | Mainline Linux and S9+ port archives |
| packaging/boot-downloads.lock.json | artifacts/boot-provenance/download-check | BusyBox package, port archive and optional LZ4 |
| packaging/dtbh-downloads.lock.json | artifacts/header-provenance | Vendor kernel source only |

Local source/patches and the independent DTBH packer and profile must already be
present. The static input hashes are checked before building; missing or changed
inputs fail without fetching. Download manifests are byte pins, not signature or
license clearance. Firmware exists inside the pinned port archive and remains
restricted to local use pending its distribution review.

## Run

```sh
python3 scripts/boot-repro/pipeline.py \
  --output artifacts/offline-pipeline-new \
  --busybox-package 'artifacts/boot-provenance/download-check/busybox-static_1%3a1.36.1-6ubuntu3.1_arm64.deb' \
  --toolchain-receipt artifacts/boot-builder/toolchain.json \
  --preflight
```

Remove `--preflight` to execute. Output must be new; partial/failed runs are
preserved for diagnosis, never overwritten or resumed implicitly. Preflight
checks static inputs and builder identity. Stage-specific parsers additionally
verify source manifests/patches during execution; preflight is not a build pass.

Stages:
1. Reconstruct kernel additions from public archives and local patches.
2. Reconstruct initramfs and embedded firmware from pinned inputs.
3. Compile vendor DTB and DTBH from source.
4. Build raw mainline kernel and verify Image, DTB and symbol table.
5. Build uniLoader, generate the explicit Samsung header/container, and verify
   loader, ELF, configuration and complete boot image against native20 pins.

Historical virtual paths inside recipe containers are mapped to **this run's**
outputs. No previous additions, cpio, Image, DTBH, BOOT backup or historical build
volume is consumed. Every derived input is hash-checked before the next stage.
Containers have no network, dropped capabilities, no-new-privileges and only
explicit input files mounted read-only plus their own output directory.
Host Python/patch preparation uses no network; host-wide network isolation is
not asserted. The toolchain image must already be local.

`pipeline.json` records stage completion, terminal status and output hashes.
Each container stage has `inputs.json`; stage logs remain at the run root.
The deliverable is `loader/boot.img`, expected SHA256:
`bd403abead6a06029a8a36fa3ed5c10afb5eca0b72de0743805f26cf74689ebb`.
A passed command is not a flash instruction or new hardware acceptance.

## Scope and release inventory

`packaging/boot-source-inventory.json` is a review ledger for nine component groups.
`packaging/boot-license-evidence.json` pins fifteen retained notices/evidence excerpts
under `open-source/licenses/`. Run:

```sh
python3 scripts/release/check-boot-inventory.py
```

The checker verifies evidence integrity and references, not license compatibility.
The independent DTBH packer has the scoped DionLabs MIT grant. Historical
dtbtool notices are retained solely as research evidence; no dtbtool input is used.
The flattened vendor DTS has no leading license notice. BusyBox source/configuration
and signature/build provenance have been traced; exact executable/package rebuilding
is recorded in BUSYBOX-UBUNTU-ENV.md, with its isolated test caveat. Original integration
now has a scoped MIT grant; inherited terms remain. Firmware and vendor DTS
redistribution are excluded and no blanket license is assigned.

Optional Bluetooth extraction, regulatory signature verification, external modules,
userspace builds and toolchain reconstruction retain their existing standalone
recipes. This pipeline is the boot-image dependency chain, not an assertion that
the complete phone/desktop system is reproducible from one command.

## Measured consolidated run

`artifacts/offline-pipeline-20261012/pipeline.json` passed all five stages. The
boot image, uniLoader, ELF and configuration match the native20 pins. Receipts
confirm fresh derived inputs and no private backup mounts. Consolidated evidence
is `local-evidence/offline-pipeline-20261012-final.json`. This is one full fresh
pipeline run, supplementing the earlier repeated individual-stage builds. Twelve
relevant input/container/audit tests passed; no new hardware test was performed.
