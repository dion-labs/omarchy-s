# Helper and patch origins

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

This is a source comparison, not a license grant or proof of original authorship.
All measurements are offline; no running phone was accessed. Existing runtime,
patch and build-input bytes are unchanged.

## Reproducible evidence

`packaging/source-origins.json` records input and result hashes for all 18 exported
patches and five init/root/USB helpers. Run:

```sh
python3 scripts/release/trace-source-origins.py --output local-evidence/origins-new.json
```

The runner verifies pinned archive hashes, stages only selected kernel files in a
fresh temporary tree, checks/applies patches with `git apply`, and verifies the five
patched additions against the established result hashes. Ten dtbtool patches are
applied in order. It also executes the reviewed, pinned port `scripts/build/patch_tree.py`
in that temporary tree; no build, package installation or device command runs.
The adjacent `.residuals.json` is local review evidence, not part of the export.
The archive cache is required separately, as in the offline build pipeline.

## Combined kernel patch: inherited work identified

`native20-tracked.patch` is an aggregate of upstream port work and later adaptations.
It must not be represented as entirely original Omarchy S code. Replaying the port's
transformer reproduces 23 of its 27 resulting files exactly, including the DMA32
allocation change, flush-reduction switch, job-owner diagnostics, framebuffer cache
synchronization, I2C work, Wi-Fi support and most Kbuild additions.

Four files differ from the transformer output:

| File | Further origin evidence |
| --- | --- |
| Exynos DT Makefile | `scripts/build/build71.sh` line 50 also inserts star2lte; do not claim the board-list addition as original. Whitespace may differ. |
| `hci_bcm.c` | Additional board/build-specific broken-transmit-power quirk; residual is isolated. |
| `panfrost_job.c` | Additional bounded fault metadata logger and rate-limit include/call; inherited flush and owner diagnostics remain upstream work. |
| `max77705_charger.c` | Port `apply_drivers.sh` copies `src/soc/max77705_charger.c`; its charge-behaviour extension is inherited. Comparing that copy isolates later current-encoding, clamp and underflow changes. Original Linux copyright for Dzmitry Sankouski remains in the source. |

The port transformer itself attributes BCM4361 work to Markuss Broks with review
input from Arend van Spriel, and describes vendor-derived timing/stamping behavior.
These attribution statements must survive review; they are upstream statements,
not independent verification of the external patch series or vendor ancestry.

## Other patches

Five addition patches are tied to the exact port files or renamed Linux simpledrm
base by `build/kernel-repro/additions.json`. All resulting hashes match. In
particular, the framebuffer base is derived from Linux; its three renaming/text
substitutions are explicit in `prepare-public.py`, not evidence of new authorship.
The loader checkpoint patch modifies two uniLoader source files from the pinned
port; the historical journal records it as diagnostic D1–D6 instrumentation.
The weak-version patch changes Linux `init/Makefile` for historical build replay.
Ten dtbtool patches apply consecutively to 1.1.0 and retain their original author
headers. None of these comparisons resolves the open patch-license questions.

## Helpers

The five helpers were compared with 30 shell candidates in the pinned port archive
(files ending `.sh` or beginning with a `/bin/sh` or `/bin/bash` shebang, under 1 MB,
without NUL bytes). No exact file match or exact block of at least three consecutive
lines was found. This bounded, whitespace-sensitive test cannot establish originality
or rule out adapted snippets, other interpreters or sources outside that archive.

- Diagnostic `init`: historical project journal records the replacement read-only
  diagnostic bootstrap. The upstream `device/mainline-init-boot` is the related
  design reference; it uses a different Ubuntu root transition/recovery policy.
- Diagnostic `usb-console.sh`: the October 2 research note explicitly credits
  `device/base/usr/local/sbin/usb-gadget` as the configfs ACM design reference.
  Preserve this attribution despite no three-line exact block match. The local
  helper narrows it to a diagnostic serial console with bounded discovery.
- Both `root-layout.sh` files: local device-specific selection and validation.
  Their partition discovery loop shares the same local structure, adapted from
  SYSTEM to USERDATA. This is shared local lineage, not independent authorship.
- Native `transition.sh`: project-specific one-shot marker, manifest checks and
  Arch/systemd transition; generic mount/switch_root operations also occur upstream.
  Historical implementation evidence supports local adaptation, not legal clearance.

All helpers and residual local hunks remain NOASSERTION pending original-code
license scope review. No request to D is needed now. Next independent work is the
flattened vendor DTS ancestry and upstream patch/vendor notice chain; D's license
choice and publication approval stay on the later list.
