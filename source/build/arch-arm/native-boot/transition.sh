# Sourced by initramfs PID1 before any background service or graphics starts.
# A missing/invalid request always keeps diagnostic startup as the default.
try_native_boot() {
    local disk= attempt root=/newroot moved= item
    for attempt in $(seq 1 30); do
        disk=$(find_arch_partition /sys/class/block /dev) && break
        sleep 1
    done
    [ -n "$disk" ] && [ -b "$disk" ] || return 0
    validate_arch_layout "$disk" "/sys/class/block/${disk##*/}" /proc/device-tree/model || return 0
    mkdir -p "$root"
    mount -t ext4 -o ro,noload "$disk" "$root" || return 0
    if [ ! -f "$root/etc/omarchy-native-once" ] || [ -L "$root/etc/omarchy-native-once" ] ||
       [ "$(cat "$root/etc/omarchy-native-once")" != native19 ]; then
        umount "$root" || return 1
        return 0
    fi
    # Reopen normally so ext4 replays its journal before consuming the request.
    umount "$root" || return 1
    mount -t ext4 -o rw "$disk" "$root" || return 0
    if [ ! -f "$root/etc/omarchy-native-once" ] || [ -L "$root/etc/omarchy-native-once" ] ||
       [ "$(cat "$root/etc/omarchy-native-once")" != native19 ]; then
        umount "$root" || return 1
        return 0
    fi
    # Consume even if the staged payload is invalid; never loop on a bad request.
    mv "$root/etc/omarchy-native-once" "$root/etc/omarchy-native-attempted" || { umount "$root"; return 1; }
    sync
    if [ ! -f "$root/etc/arch-release" ] ||
       [ ! -f "$root/usr/local/lib/omarchy-native/manifest.sha256" ] ||
       ! (cd "$root" && sha256sum -c usr/local/lib/omarchy-native/manifest.sha256) ||
       ! chroot "$root" /usr/lib/systemd/systemd --version; then
        echo 'Native payload validation failed; returning to diagnostic boot.'
        umount "$root" || return 1
        return 0
    fi
    # /run is a fresh mount, not the previous diagnostic session's runtime state.
    mkdir -p "$root/dev" "$root/proc" "$root/sys" "$root/run"
    mount -t tmpfs -o mode=755 tmpfs "$root/run" || { umount "$root"; return 1; }
    for item in dev proc sys; do
        if mount --move "/$item" "$root/$item"; then
            moved="$item $moved"
        else
            for item in $moved; do mount --move "$root/$item" "/$item" || return 1; done
            umount "$root/run"; umount "$root"
            return 1
        fi
    done
    if ! chroot "$root" /bin/sh /usr/local/lib/omarchy-native/runtime-setup.sh; then
        for item in $moved; do mount --move "$root/$item" "/$item" || return 1; done
        umount "$root/run"; umount "$root"
        return 1
    fi
    echo 'Starting native Arch/systemd once; diagnostic startup remains the next-boot default.'
    exec switch_root "$root" /usr/lib/systemd/systemd --unit=omarchy-phone.target
}
