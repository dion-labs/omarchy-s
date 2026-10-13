#!/bin/bash
set -euo pipefail
mkdir /tmp/source
cd /tmp/source
# Hashes are checked by the host runner; retain signatures, but do not imply trust verification.
dpkg-source --no-check -x /inputs/busybox_1.36.1-6ubuntu3.1.dsc busybox > /output/unpack.log 2>&1
cd busybox
export DEB_BUILD_OPTIONS='parallel=4 nocheck'
make -f debian/rules configure-static > /output/configure.log 2>&1
cmp debian/config/pkg/static b/static/.config
cp b/static/.config /output/static.config
cp debian/rules debian/control debian/copyright debian/changelog /output/
cp debian/patches/series /output/patch-series
make -f debian/rules build-static > /output/build.log 2>&1
b/static/busybox --list > /output/applets.txt
cp b/static/busybox /output/busybox-rebuilt
# Preserve applied corresponding source, excluding generated build products.
tar --sort=name --mtime=@1727740800 --owner=0 --group=0 --numeric-owner --exclude=./b -cf /output/applied-source.tar .
