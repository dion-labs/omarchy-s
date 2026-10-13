set -eu
mkdir -p /repro/headers
cd /repro
tar xf /inputs/artifacts/weston-provenance/first/headers.tgz -C headers
cc -D_GNU_SOURCE -shared -fPIC -Wall -Wextra -Werror -Wno-error=attributes -I/repro/headers/libweston-15 $(pkg-config --cflags pixman-1 wayland-server) /inputs/build/arch-arm/dock/input-seat.c -o /out/input-seat.so -lxkbcommon
