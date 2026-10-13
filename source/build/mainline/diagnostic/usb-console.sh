#!/bin/sh
# Initramfs-only, local development ACM console. No network or storage export.
set -eu
grep -q ' /sys/kernel/config configfs ' /proc/mounts || mount -t configfs configfs /sys/kernel/config
G=/sys/kernel/config/usb_gadget/omarchy_diagnostic
[ ! -e "$G" ] || { echo 'Diagnostic gadget already exists; refusing to replace it.' >&2; exit 1; }
udc=
for attempt in $(seq 1 30); do
    set -- /sys/class/udc/*
    if [ "$#" -eq 1 ] && [ -e "$1" ]; then udc=${1##*/}; break; fi
    [ "$#" -le 1 ] || { echo 'Multiple UDCs; refusing arbitrary selection.' >&2; exit 1; }
    sleep 1
done
[ -n "$udc" ] || { echo 'No USB device controller appeared.' >&2; exit 1; }
mkdir "$G"
# These Linux gadget IDs are for this private diagnostic build only.
printf '0x1d6b' > "$G/idVendor"
printf '0x0104' > "$G/idProduct"
printf '0x0200' > "$G/bcdUSB"
mkdir -p "$G/strings/0x409" "$G/configs/c.1/strings/0x409"
printf 'OMARCHY-S-DIAGNOSTIC' > "$G/strings/0x409/serialnumber"
printf 'Omarchy S laboratory' > "$G/strings/0x409/manufacturer"
printf 'S9+ diagnostic console' > "$G/strings/0x409/product"
printf 'ACM console only' > "$G/configs/c.1/strings/0x409/configuration"
printf '100' > "$G/configs/c.1/MaxPower"
mkdir "$G/functions/acm.usb0"
ln -s "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0"
printf '%s' "$udc" > "$G/UDC"
for attempt in $(seq 1 10); do
    [ ! -c /dev/ttyGS0 ] || break
    sleep 1
done
[ -c /dev/ttyGS0 ] || { echo 'Bound gadget has no ttyGS0.' >&2; exit 1; }
echo 'ACM diagnostic console bound; host enumeration remains to be tested.'
# Deliberately passwordless root console for a physically attached lab host.
# No automatic rootfs handover; mounted project root stays read-only.
while :; do
    setsid sh -c 'stty sane < /dev/ttyGS0; exec sh -i < /dev/ttyGS0 > /dev/ttyGS0 2>&1' || true
    sleep 1
done
