#!/bin/bash
set -euo pipefail
mkdir /tmp/port
tar xf /inputs/artifacts/kernel-source-closure/upstream-port.tar.gz -C /tmp/port --strip-components=1
patch --batch --fuzz=0 -d /tmp/port/bootloader/uniLoader -p1 -i /inputs/build/mainline/loader/checkpoints.patch
mkdir -p /tmp/port/dist/uniloader-in
cp /inputs/local-evidence/boot-provenance-20261012/full-kernel-final/Image /tmp/port/dist/uniloader-in/Image
cp /inputs/local-evidence/boot-provenance-20261012/full-kernel-final/exynos9810-star2lte.dtb /tmp/port/dist/uniloader-in/dtb
export BUILD_DATE='2026-10-08 20:50:47'
export GIT_VERSION_TAG=''
bash /tmp/port/scripts/build/build_uniloader.sh star2lte_defconfig > /output/build.log 2>&1
cp /tmp/port/dist/uniloader/uniLoader* /output/
