# Prepared external-desktop profile

This is a small, attributed subset of Omarchy v4.0.4, pinned by commit and SHA256
in `upstream.json`. `upstream/looknfeel.lua` is unmodified; its license is retained.
The wrapper selects1080p at scale1, Italian keyboard layout and disabled animations.
It does not install Omarchy, start services, configure power/locking, automount
volumes, or replace the phone's Phosh session.

Validation: `python3 scripts/dock-lab/verify-omarchy-profile.py` from the project
root runs Hyprland0.56.2's real Lua parser on the phone in a namespace without GPU,
input, network or account-home access. The current profile passes. Rendering and
physical keyboard behavior with this profile remain pending.

The complete upstream desktop uses Quickshell, session services and utilities
beyond this profile. The configured Arch ARM repository advertises Quickshell0.3.1
for aarch64, but it has not been installed or validated here. Full autostart assumes
systemd user sessions, UWSM helpers, power-profile handling and automounting. These
need integration with the existing phone services before adoption. The upstream
lock plugin also references Owe.LockFeed/owe-lockfeed; that dependency is not yet
validated for this installation. Never run upstream provisioning wholesale in the
current diagnostic chroot.
