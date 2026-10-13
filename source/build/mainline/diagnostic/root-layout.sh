# Device-specific, read-only diagnostic root discovery. No partition writes.
find_system_partition() {
    local entry found= name
    for entry in "$1"/*/uevent; do
        [ -f "$entry" ] || continue
        grep -qx 'PARTNAME=SYSTEM' "$entry" || continue
        name=$(sed -n 's/^DEVNAME=//p' "$entry")
        case "$name" in ''|*[!a-zA-Z0-9]*) return 1 ;; esac
        [ -z "$found" ] || return 1
        found="$2/$name"
    done
    [ -n "$found" ] || return 1
    printf '%s\n' "$found"
}
validate_system_layout() {
    local disk=$1 header sectors
    sectors=$(cat "$2/size") || return 1
    # sysfs reports capacity in 512-byte units, including on 4K-sector UFS.
    [ "$sectors" = 9011200 ] || return 1
    header=$(dd if="$disk" bs=1 skip=446 count=66 2>/dev/null | sha256sum | cut -d' ' -f1)
    [ "$header" = 25f8a768c47898470d3e463f5b5ec6b417ad70ac861f24de6d0a8382f3e481fc ]
}
read_root_label() {
    dd if="$1" bs=1 skip=1144 count=16 2>/dev/null | tr -d '\000'
}
map_diagnostic_root() {
    local disk=$1 loop
    [ -b "$disk" ] || return 1
    validate_system_layout "$disk" "/sys/class/block/${disk##*/}" || return 1
    loop=$(losetup -f) || return 1
    # BusyBox lacks --sizelimit. Exact parent capacity above makes the
    # remaining region exactly 4357881856 bytes, our verified root size.
    losetup -r -o 255852544 "$loop" "$disk" || return 1
    # Read ext superblock label directly: builder's static BusyBox has no blkid.
    if [ "$(read_root_label "$loop")" != pmOS_root ]; then
        losetup -d "$loop"; return 1
    fi
    if ! mount -t ext4 -o ro,noload "$loop" /root; then
        losetup -d "$loop"; return 1
    fi
    printf '%s\n' "$loop"
}
