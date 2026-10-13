# Read-only native-root selection for the exact installed S9+ filesystem.
# No mount or root transition is implemented here.
find_arch_partition() {
    local entry found= name
    for entry in "$1"/*/uevent; do
        [ -f "$entry" ] || continue
        grep -qx 'PARTNAME=USERDATA' "$entry" || continue
        name=$(sed -n 's/^DEVNAME=//p' "$entry")
        case "$name" in ''|*[!a-zA-Z0-9]*) return 1 ;; esac
        [ -z "$found" ] || return 1
        found="$2/$name"
    done
    [ -n "$found" ] || return 1
    printf '%s\n' "$found"
}

validate_arch_layout() {
    local disk=$1 sys=$2 model=$3 magic uuid label
    [ "$(tr -d '\000' < "$model")" = 'Samsung Galaxy S9+ (SM-G965F)' ] || return 1
    [ "$(cat "$sys/size")" = 111009792 ] || return 1
    grep -qx 'PARTNAME=USERDATA' "$sys/uevent" || return 1
    magic=$(dd if="$disk" bs=1 skip=1080 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$magic" = 53ef ] || return 1
    uuid=$(dd if="$disk" bs=1 skip=1128 count=16 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$uuid" = c4641ce55ee848359200df7af1a96ee2 ] || return 1
    label=$(dd if="$disk" bs=1 skip=1144 count=16 2>/dev/null | tr -d '\000')
    [ "$label" = omarchy-arch ]
}
