# External dependency source preview

Host-only reconstruction of the desktop's input bridge, patched Aquamarine,
portal, opt-in Mesa workaround and two native USB owner sources. This is a source
preview, not an installer or a complete phone distribution. It neither contacts
nor modifies a device. See [licensing](DEPENDENCIES-LICENSING.md).

## Requirements and acquisition

Use Python 3, Git and an ARM64-capable Docker engine. Commands run from this
source directory. Downloads and container builds require disk space; the Mesa
build is substantially larger than the other components. No private rootfs,
original captured headers, phone backup or account data is required.

Acquire the four inputs and derive Weston headers:

```sh
python3 scripts/dependency-lab/acquire-sources.py
python3 scripts/toolchain-lab/weston-headers.py --package artifacts/weston-provenance/weston-15.0.1-3-aarch64.pkg.tar.xz --output artifacts/weston-provenance/first
```

[The input lock](packaging/dependency-sources.lock.json) records URLs, a portal
Git commit and exact archive hashes. Existing mismatched inputs are rejected.
For offline rehearsal, add `--cache-root /path/to/existing/source-cache` to
acquisition; that directory must contain the same relative input paths.
The portal archive is produced by `git archive` of the pinned commit, not a GitHub
release archive. Header derivation preserves package notices. Hashes establish
identity; this workflow does not verify upstream signatures or reconstruct the
Weston distribution package from its original build sources.

## Reconstruct the toolchains

```sh
python3 scripts/toolchain-lab/fetch-packages.py packaging/toolchains/arch-archives.lock.json artifacts/packages/arch
python3 scripts/toolchain-lab/fetch-packages.py packaging/toolchains/mesa-archives.lock.json artifacts/packages/mesa
python3 scripts/toolchain-lab/build-toolchain.py arch --packages artifacts/packages/arch --output artifacts/builders/arch
python3 scripts/toolchain-lab/build-toolchain.py mesa --packages artifacts/packages/mesa --output artifacts/builders/mesa
python3 scripts/toolchain-lab/bind-build-lock.py --arch-receipt artifacts/builders/arch/toolchain.json --mesa-receipt artifacts/builders/mesa/toolchain.json --output artifacts/builds.lock.json
```

The Arch builder assembles147 pinned package archives into a deterministic rootfs;
the Mesa builder uses270 pinned package/supplemental inputs and a digest-pinned
Ubuntu base. Docker may need to acquire that base image. Source compilation runs
offline. Builder image IDs are local receipts, not portable public image names.
The binder defaults to the package-derived header recipe, validates both receipts
against archive locks/Dockerfiles and checks ARM64 image identity. It does not
prove that an arbitrary supplied image was built faithfully; retain the receipts
from the builder you actually ran. Container image byte identity and a compiler
bootstrap from source are not claimed.

The Arch builder differs from the historical runtime snapshot in five packages:
GLib2.90.1, SQLite3.54.0, Python3.14.8, libevdev1.14.0 and
libsysprof-capture51.0. Runtime package updates are not part of this preview.

## Rebuild and compare

```sh
python3 scripts/release/rebuild-private.py input-seat --lock artifacts/builds.lock.json --output artifacts/rebuilt/input
python3 scripts/release/rebuild-private.py aquamarine --lock artifacts/builds.lock.json --output artifacts/rebuilt/aquamarine
python3 scripts/release/rebuild-private.py portal --lock artifacts/builds.lock.json --output artifacts/rebuilt/portal
python3 scripts/release/rebuild-private.py mesa --lock artifacts/builds.lock.json --output artifacts/rebuilt/mesa
python3 scripts/dependency-lab/prepare-native-usb.py --output artifacts/rebuilt/native-usb
```

Each binary recipe uses two disposable containers, networking disabled, explicit
read-only hashed inputs and fresh outputs; result.json compares bytes, modes and
symlink targets. All output directories must be new. The USB recipe checks its
baseline sources, applies explicit native19/20/21 profile/module selection and
verifies both final hashes; it never imports or starts these hardware services.
The USB output contains only two owner sources. The hardware helper, rescue
gadget, matching kernel modules, native readiness units and configuration remain
separate prerequisites; do not run these sources on an arbitrary device.

[Desktop dependency pins](packaging/dock-dependencies.lock.json) remain the
known-good reference. Input-seat, Aquamarine, portal and the two USB sources can
match five of those pins exactly. The [portal payload workflow](PORTAL-PAYLOAD.md)
also recreates the notice and runtime manifest, bringing the exact subset to seven. Mesa fresh builds are repeatable, but three of
31 regular files differed from the installed build in prior validation, including
source-path strings. Repeatability does not establish runtime equivalence. Keep
the installed Mesa pin until an isolated GPU test and physical checks pass.
The installed Mesa metadata manifest is not recreated by these recipes.
No replacement of the ten external runtime pins is implied.

## Local checks

```sh
python3 scripts/release/test-private-builds.py
python3 scripts/toolchain-lab/test-inputs.py
python3 scripts/toolchain-lab/test-weston-headers.py
python3 scripts/dependency-lab/test-native-usb.py
python3 scripts/dependency-lab/test-acquire-sources.py
python3 scripts/dependency-lab/test-stage-portal.py
python3 scripts/dependency-lab/test-portal-ownership.py
```

The public package contains source, recipes, pins and notices only. Downloaded
archives, generated headers, builder images and compiled libraries are excluded.
Their redistribution needs its own source/license obligations assessment.

The [isolated transaction laboratory](PORTAL-TRANSACTION-LAB.md) exercises portal
creation, backups, receipt commits, rollback, finalization and explicit cleanup on Linux.
Its separate 39-test transaction/retention/lifecycle suites requires the documented container command; macOS skips are not acceptance.
