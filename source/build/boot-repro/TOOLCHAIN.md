# Boot builder setup

This preview includes a narrow Mesa-named builder for the native20 boot pipeline.
It does not require the separate Arch/userspace reconstruction helpers. Run from
the extracted preview root with Python 3.9+, Docker supporting Linux ARM64, at
least 6 GiB assigned to Docker and sufficient disk for packages and kernel objects.
All scripts are mode 0644; invoke their interpreter explicitly.

Acquisition is a separate networked phase. Pull the exact base already recorded
in the included Dockerfile, then download the hash-pinned packages:

```sh
docker pull --platform linux/arm64 ubuntu@sha256:a853f94d226358a79c740cfc7bce0c289748f3fe3488d921d038ccd752c61b60
python3 scripts/toolchain-lab/fetch-packages.py packaging/toolchains/mesa-archives.lock.json artifacts/boot-builder-packages
```

Build from those local inputs into a new directory:

```sh
python3 scripts/boot-repro/build-toolchain.py --packages artifacts/boot-builder-packages --output artifacts/boot-builder
```

The helper checks every package digest, refuses duplicate/unsafe filenames,
symlink packages and existing output, copies the pinned recipe, checks the local
ARM64 base and builds with container networking disabled. Docker itself is not
host-wide network-isolated. No image is pushed or activated. Use `--prepare-only`
with a different output directory to inspect the context without invoking Docker.

The result `artifacts/boot-builder/toolchain.json` records the locally built image
ID and input hashes in the format consumed by the boot pipeline's `toolchain.py`.
Pass it with `--toolchain-receipt`; do not change historical image IDs in locks.
A failed build preserves its output; retry with a fresh directory.

This reconstructs an environment from distribution binary packages, not a compiler
bootstrap from source. Package availability/authenticity review is distinct from
hash pinning. Image serialization can differ across runs; matching package versions
and subsequent boot output hashes are the relevant checks. No new hardware or
fresh-host full-build acceptance follows from a prepared context or synthetic test.

Continue with [the offline boot pipeline](OFFLINE-PIPELINE.md).
