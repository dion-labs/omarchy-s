#!/bin/bash
set -euo pipefail
mkdir /tmp/vendor
tar xf /inputs/artifacts/header-provenance/vendor-source.tar.gz -C /tmp/vendor --strip-components=1
cd /tmp/vendor
gcc -E -nostdinc -Iarch/arm64/boot/dts -Iarch/arm64/boot/dts/include -Idrivers/of/testcase-data -undef -D__DTS__ -x assembler-with-cpp arch/arm64/boot/dts/exynos/exynos9810-star2lte_eur_open_26.dts -o /output/preprocessed.dts
dtc -O dtb -o /output/vendor.dtb -b 0 -a 4 -i arch/arm64/boot/dts/exynos/ -@ -Wno-unit_address_vs_reg /output/preprocessed.dts 2>/output/dtc.log
python3 /inputs/scripts/boot-repro/pack-dtbh.py --dtb /output/vendor.dtb --profile /inputs/packaging/dtbh-profile.json --output /output/dt.img
dtc --version > /output/dtc-version.txt
