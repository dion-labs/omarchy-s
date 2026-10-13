# Recorded Ubuntu BusyBox build environment

The reconstruction uses Ubuntu snapshot `20240814T120000Z`. All150 exact package
versions in Launchpad build28868120's buildinfo are available in the noble,
noble-updates and noble-security main ARM64 indexes. Signed InRelease files verify
with the pinned Ubuntu archive key; their SHA256 entries authenticate the package
indexes, which authenticate each downloaded .deb. This is a dated replay, not a
current security-update policy. Nothing is installed on the host or phone.

Inputs: packaging/busybox-env-archives.lock.json and busybox-ubuntu-build.json.
Recipes: BusyBox-Ubuntu.Dockerfile and rebuild-busybox-ubuntu.sh in this directory.
The Docker base is pinned by digest. Installation occurs in a network-disabled
build using only local package archives; recorded versions are compared against
installed (`ii`) package status afterwards. Additional base packages are recorded
separately. This recreates all recorded dependencies, not the historical host
kernel, CPU, complete filesystem or entire Launchpad infrastructure.

```sh
python3 scripts/toolchain-lab/fetch-packages.py packaging/busybox-env-archives.lock.json artifacts/busybox-ubuntu-env/packages
python3 scripts/boot-repro/verify-busybox-environment.py --archives artifacts/busybox-ubuntu-env --output artifacts/busybox-snapshot-check-new
python3 scripts/boot-repro/build-busybox-environment.py --packages artifacts/busybox-ubuntu-env/packages --output artifacts/busybox-builder-new
python3 scripts/boot-repro/rebuild-busybox-ubuntu.py --environment artifacts/busybox-builder-new/result.json --sources artifacts/busybox-source --output artifacts/busybox-ubuntu-rebuild-new
```

For verification, additionally fetch and retain the three InRelease files and
main/binary-arm64/Packages.xz files under
`https://snapshot.ubuntu.com/ubuntu/20240814T120000Z/dists/<pocket>/`.
Local filenames are `<pocket>-InRelease` and `<pocket>-main-Packages.xz` for pockets
noble, noble-updates and noble-security. Source archive acquisition is documented
in BUSYBOX-SOURCE.md. All output directories must be new.

The source is unpacked at `/build/busybox-UAsEDJ/busybox-1.36.1`; the recorded epoch,
locale, parallelism and noudeb build profile are set. `dpkg-buildpackage -B -us -uc`
runs distro build/packaging steps. The runner compares the executable against
`52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933` and the package
against `d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc`.
An executable match and a package match are separate results. Failed builds retain
logs; no fallback input or prebuilt BusyBox binary is mounted into the rebuild.

The initial builder attempt failed due to APT's local-package `--no-download`
pathname error. Removing that flag fixed assembly; Docker network stayed disabled.
Old builder/source outputs, native20 image and source-preview snapshots are retained.
No built artifact is activated or published by these commands.

## Measured result

One fresh full build in `artifacts/busybox-ubuntu-env/rebuild-first` matches both
expected hashes above exactly: the executable and entire busybox-static .deb.
All150 recorded dependencies match installed status;26 extra base packages remain
explicitly listed in builder-verified/result.json. Upstream `hostname-d-works`
reported FAIL inside the isolated container while the package build completed;
this is not a claim that every upstream runtime test passed.

Passing the rebuilt .deb to prepare.py reproduces native20 initramfs SHA256
`1fde00750f2a27a60acd240b83e4f964108932e0636ff613c57dcf5b0843e345`.
The consolidated boot pipeline preflight also accepts it as --busybox-package.
The unchanged kernel was not needlessly rebuilt, and the phone was untouched.
Evidence: local-evidence/busybox-env-20261012/final-summary.json. Matching bytes do
not constitute a new device test, software update or publication permission.
