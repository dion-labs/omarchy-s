set -eu
mkdir -p /repro
cd /repro
tar --no-same-owner -xf /inputs/artifacts/mesa-26.2.3.tar.xz
mv mesa-26.2.3 source
python3 /inputs/build/mesa-cache/patch.py /repro/source
# Toolchain snapshot already contains the pinned Wayland protocols and compiler.
meson setup out source --wrap-mode=nodownload --prefix=/opt/omarchy-mesa-cache --libdir=lib -Dbuildtype=release -Dgallium-drivers=panfrost -Dvulkan-drivers=[] -Dplatforms=wayland -Dglx=disabled -Degl=enabled -Dgbm=enabled -Dgles1=disabled -Dgles2=enabled -Dllvm=enabled -Ddraw-use-llvm=false -Dvideo-codecs=[] -Dbuild-tests=false -Dglvnd=disabled
ninja -C out -j4
DESTDIR=/out/root ninja -C out install
