#!/bin/bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8 SOURCE_DATE_EPOCH=1723556578
export DEB_BUILD_OPTIONS=parallel=4 DEB_BUILD_PROFILES=noudeb
mkdir -p /build/busybox-UAsEDJ
cd /build/busybox-UAsEDJ
dpkg-source --no-check -x /sources/busybox_1.36.1-6ubuntu3.1.dsc busybox-1.36.1
cd busybox-1.36.1
# Use distro build and packaging steps, including stripping/debug links.
dpkg-buildpackage -B -us -uc > /output/build.log 2>&1
cp ../*.deb ../*.buildinfo ../*.changes /output/
cp b/static/.config /output/static.config
cp b/static/busybox /output/busybox-unstripped
cp debian/busybox-static/bin/busybox /output/busybox 2>/dev/null || cp debian/busybox-static/usr/bin/busybox /output/busybox
dpkg-query -W -f='${binary:Package}\t${Version}\n' > /output/installed-packages.tsv
sha256sum /output/busybox /output/*.deb > /output/SHA256SUMS
