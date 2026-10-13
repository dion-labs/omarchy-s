# Dock and desktop source preview — source release

This preview stages the S9+ dock services and the adapted pinned Omarchy shell.
It is source for a working partial port, not a complete Omarchy installation or
an installer for a stock phone. No command below connects to a phone.

## Layout and verification

The separate allowlist is `packaging/dock-source-export.allowlist.json` alongside
the exported archive/manifest. Copy it to that path in your extracted working
copy before running the inventory checker. The export uses explicit UTF-8 files, normalized
0644 modes and deterministic archive metadata. Source provenance classifications
are in `packaging/dock-source-attribution.json`; the scoped original and inherited terms are explained in DOCK-LICENSING.md.

Run the host-only tests from the extracted source root:

```sh
python3 scripts/release/check-dock-source.py
python3 scripts/release/test-export-source.py
python3 scripts/release/test-dock-services.py
python3 scripts/release/test-stage-dock-shell.py
```

## Acquire the upstream source

Use Git and Python 3.9 or newer. Fetch upstream explicitly, then leave it clean:

```sh
git clone https://github.com/basecamp/omarchy.git upstream/omarchy
git -C upstream/omarchy checkout --detach b83d3df0840504299d3099ebf391eb8110527edd
```

The builder rejects a different or dirty checkout. The separately retained
appearance subset is pinned to v4.0.4 in the profile's upstream.json; both source
identities are deliberate. The shell build copies upstream fonts and artwork into
local output. Their asset-level redistribution review is still open: generated
shell payloads are not part of this source candidate.

## Stage locally

Choose fresh output directories. These commands neither install nor activate:

```sh
python3 scripts/release/stage-dock-services.py --output artifacts/services-stage
python3 scripts/release/stage-dock-shell.py --upstream upstream/omarchy --output artifacts/shell-stage
```

Each output contains a `rootfs/` tree and an ownership receipt. Services also include
a dependency lock. Compare hashes and modes between independent runs. Reproducible
staging is not proof that an arbitrary target can run these files.

## Installation prerequisites and limits

The account contract is omarchy, UID/GID 1000, with the existing namespace paths.
The native USB owner controls dock lifecycle; this package does not replace it.
The 39 package versions are observed compatibility pins, not downloadable artifact
pins or a complete transitive lock. Ten external file hashes include private Mesa,
Aquamarine, portal, input-seat and native USB owner dependencies. Matching package
names alone is insufficient. Device-specific allowed-inputs.json, Bluetooth bonds,
network configuration and account state must be supplied privately, never bundled.

There is no supported installation command in this preview. Do not copy rootfs/
over a running session or run the general upstream Omarchy installer/updater.
A future installer must resolve external dependencies, verify ownership/model and
native state, preserve user configuration, update integrity records and support
transactional rollback before session-boundary activation. The current source
preview only provides inspectable staging and a prerequisite contract.

## Scope and licensing review

No firmware, binaries, accounts, pairing data, device selections, journals or
private diagnostic evidence are included. The retained upstream MIT notices apply
to the identified Omarchy source and inherited snippets. DionLabs original
contributions have a scoped MIT grant; see DOCK-LICENSING.md. The per-file ledger
records content review and pinned upstream evidence. Historical profile README
statements refer to its earlier test stage, not current runtime status.

The packaged `check-*.py` runtime probes are source for optional on-device checks;
they are not part of the host test commands above. Some open windows, request
portal capture or change and restore themes. Do not run them against an active
session merely to validate this archive. The phone and generated runtime state
were not accessed during the source release review.
