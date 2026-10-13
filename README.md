# Omarchy S — source previews

A personal experiment to turn a Galaxy S9+ into a Linux phone that becomes a
desktop when connected to a monitor. The longer-term goal is an agent that lives
on the device and can work with its human across both interfaces.

The boot preview contains the boot reconstruction work for the **Samsung
Galaxy S9+ SM-G965F (Exynos 9810)**. It is a narrow source release, not the full
phone system or an installer. The broader project uses Arch ARM, Phosh on the
phone and a partial Omarchy/Hyprland port on the external display; selected desktop sources and dependency recipes are released separately below.

## Start here

Read [the boot-source guide](source/BOOT-PREVIEW.md), then follow the
[builder setup](source/build/boot-repro/TOOLCHAIN.md) and
[offline pipeline](source/build/boot-repro/OFFLINE-PIPELINE.md).

The reviewed payload is kept unchanged under `source/`. Its exact hash inventory
is in `release/manifest.json`. Before running the attribution checks in a working
copy, supply the separate allowlist:

```sh
cp release/source-export.allowlist.json source/packaging/source-export.allowlist.json
cd source
python3 scripts/release/check-source-attribution.py
python3 scripts/release/check-boot-inventory.py
python3 scripts/release/check-lineage-scope.py
```

The allowlist lives outside the original source archive to avoid hashing itself.
Acquisition and build instructions are explicit; no command above flashes a phone.

## What has been checked

The five-stage offline rebuild passed, with eleven outputs matching the pinned
reference, including the complete boot image. The independent DTBH packer replaces
dtbtool for this one pinned device-tree input. It does not support arbitrary boards.
See [the draft release notes](RELEASE-NOTES.md) for the exact validation boundaries.

Firmware, vendor DTS source, binaries, configured root filesystems and accounts
are not included. Historical installation guards remain in the reconstruction:
this is research source for one setup, not a supported flashing kit.

## License and project scope

Original DionLabs contributions are MIT-licensed within the scope described in
[LICENSING.md](LICENSING.md). Inherited source and patches retain their own terms.
This is an independent personal project, not an official Omarchy distribution.
There is no commitment to support other phones or configurations.

## Download

[Boot-source preview 1](https://github.com/dion-labs/omarchy-s/releases/tag/boot-source-preview-1)
contains the reviewed source archive, manifest, separate allowlist and checksums.
[Download source-preview.tar](https://github.com/dion-labs/omarchy-s/releases/download/boot-source-preview-1/source-preview.tar).

The source payload preserves its pre-publication review records, including their
historical “publication unapproved” status. Publication of this exact preview was
subsequently approved by D; those frozen records are retained to preserve the
reviewed archive identity. This approval does not extend to excluded binaries,
firmware or the full phone system.

## Desktop source preview

[Desktop-source preview 1](https://github.com/dion-labs/omarchy-s/releases/tag/desktop-source-preview-1)
adds the dock service and pinned shell-adaptation sources. Start with the
[desktop source guide](desktop-source/DOCK-PREVIEW.md) and
[desktop release notes](DESKTOP-RELEASE-NOTES.md).
[Download desktop-source-preview.tar](https://github.com/dion-labs/omarchy-s/releases/download/desktop-source-preview-1/desktop-source-preview.tar).

The reviewed desktop payload is under `desktop-source/`, with its manifest and
separate allowlist under `release/desktop/`. Copy the allowlist into
`desktop-source/packaging/` for local inventory verification. This source release
does not include the external graphics dependencies or a supported live installer.
Its [scoped licensing](desktop-source/DOCK-LICENSING.md) is separate from the boot
payload. The older boot download links above remain valid.

## External dependency source preview

[Dependency-source preview 4](https://github.com/dion-labs/omarchy-s/releases/tag/dependency-source-preview-4)
adds explicit finalization and retained-backup cleanup to the Linux portal
transaction laboratory, with repeated-update and interrupted-cleanup recovery. It accepts only isolated marked
temporary directories and has no live installation mode. Read the
[dependency guide](dependency-source/DEPENDENCIES-PREVIEW.md),
[transaction laboratory guide](dependency-source/PORTAL-TRANSACTION-LAB.md) and
[release notes](DEPENDENCY-RELEASE-NOTES.md).
[Download dependency-source-preview.tar](https://github.com/dion-labs/omarchy-s/releases/download/dependency-source-preview-4/dependency-source-preview.tar).

The 56-file source payload lives under `dependency-source/`, with manifest and
allowlist under `release/dependencies/`. All 60 tests pass, including 200 injected
process exits. The real portal payload passes isolated storage rehearsals; no
portal process or phone is activated. Seven runtime hashes reproduce exactly.
Mesa runtime validation, live process coordination, existing-device adoption and
automatic retention policy remain separate. The [scoped licensing](dependency-source/DEPENDENCIES-LICENSING.md)
retains upstream notices. Earlier previews remain available at their release tags.
