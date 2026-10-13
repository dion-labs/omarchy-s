set -eu
# Delete only the disposable container's inherited build tree, never a host mount.
rm -rf /build/source
mkdir -p /build
cd /build
tar xf /inputs/artifacts/hyprland-trial/aquamarine-v0.15.1.tar.gz
mv aquamarine-0.15.1 source
cd source
patch -p1 < /inputs/build/arch-arm/dock/patches/aquamarine-compositor-version.patch
patch -p1 < /inputs/build/arch-arm/dock/patches/aquamarine-initial-configure.patch
cmake -S . -B /build/source/out -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF
cmake --build /build/source/out -j4
cp /build/source/out/libaquamarine.so.0.15.1 /out/libaquamarine.so.14
