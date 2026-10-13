set -eu
mkdir -p /repro/source
cd /repro
tar xf /inputs/build/portal-wlr/source.tar -C source
python3 /inputs/build/portal-wlr/patch.py
meson setup out source -Dman-pages=disabled -Dsystemd=disabled --buildtype=release --wrap-mode=nodownload
ninja -C out -j4
cp out/xdg-desktop-portal-wlr /out/portal-wlr
