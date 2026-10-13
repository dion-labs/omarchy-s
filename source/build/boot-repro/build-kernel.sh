#!/bin/bash
# Reconstruct the raw native20 kernel with exact public-source boot inputs. No device access.
set -euo pipefail
export KBUILD_BUILD_VERSION=20 KBUILD_BUILD_TIMESTAMP='Thu Oct  8 20:50:29 UTC 2026'
export KBUILD_BUILD_USER=root KBUILD_BUILD_HOST=71ffaed78ed3
mkdir -p /repro/kernel /repro/modules /output
cd /repro/kernel
tar -xf /inputs/artifacts/kernel-source-closure/upstream-linux.tar.gz --strip-components=1
patch --batch --fuzz=0 -p1 < /inputs/build/kernel-repro/patches/native20-tracked.patch
tar -xf /inputs/artifacts/kernel-public-first/additions.tar
patch --batch --fuzz=0 -p1 < /inputs/build/boot-repro/preserve-weak-version.patch
mkdir out
cp /inputs/build/kernel-repro/native20.config out/.config
mkdir -p /work/build/firmware/brcm
cp /inputs/artifacts/boot-provenance/first/firmware/brcm/* /work/build/firmware/brcm/
cp /inputs/artifacts/boot-provenance/first/firmware/regulatory.db* /work/build/firmware/
kmake() { make -j4 O=out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=-dirty "$@"; }
kmake olddefconfig
cp out/.config /output/compile.config
cmp out/.config /inputs/build/kernel-repro/native20.config
# Override only the make input location; embedded config and cpio bytes stay exact.
kmake CONFIG_INITRAMFS_SOURCE=/inputs/artifacts/boot-provenance/first/initramfs.cpio Image dtbs
kmake modules_prepare
sha256sum out/vmlinux out/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dtb out/drivers/phy/samsung/phy-exynos9810-usbdrd.o out/drivers/usb/dwc3/core.o out/drivers/usb/dwc3/dwc3-exynos.o out/drivers/soc/samsung/s9p-max77705-muic.o out/drivers/gpu/drm/sysfb/exynos-bootfb.o > /output/kernel-objects.sha256
cp out/vmlinux.symvers /output/generated.symvers
cp out/vmlinux.symvers out/Module.symvers
echo 'e52781b61e79af5690e9846d45487bf16cd1018b63492d7567d768b8f5027ee3  out/Module.symvers' | sha256sum -c -
cp out/include/generated/{utsrelease.h,utsversion.h,compile.h} /output/
cp out/arch/arm64/boot/Image /output/Image
cp out/arch/arm64/boot/dts/exynos/exynos9810-star2lte.dtb /output/
cp out/usr/initramfs_inc_data /output/
sha256sum /output/Image /output/exynos9810-star2lte.dtb /output/initramfs_inc_data > /output/SHA256SUMS
cp out/vmlinux /output/vmlinux
(cd out && find . -name '*.o' -type f -print0 | sort -z | xargs -0 sha256sum) > /output/object-hashes.txt
(cd out && find . -name '*.o' -type f -print0 | sort -z | tar --null -T - -cf /output/objects.tar)
