# Vendor ancestry and external attribution

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

This review records source relationships without changing build inputs or accessing
the phone. Publication remains uncleared; exact bytes establish provenance, not a
new license grant.

## Pinned vendor evidence

`packaging/vendor-ancestry.json` is reproduced by:

```sh
python3 scripts/release/trace-vendor-attribution.py --output local-evidence/vendor-review-new.json
```

The runner verifies both archive hashes, reads selected members without extraction,
and verifies the retained vendor notices against their complete leading comments.

- Both UFS calibration files exactly match `drivers/scsi/ufs/ufs-cal-9810.[ch]`
  in the pinned vendor archive. This independently confirms the port's unchanged
  source assertion. Neither file supplies its own SPDX tag; preserve the port's
  GPL-2.0 statement and vendor root COPYING as distinct evidence.
- `drivers/i2c/busses/i2c-exynos5.c` contains the divider and 7/9 timing formulas
  described by the port transformer. Its leading notice credits Samsung Electronics
  (2013) under GPLv2. This is a source reference, not a claim that the rewritten
  mainline function is an exact copy.
- `drivers/net/wireless/bcmdhd_100_15/dhd_msgbuf.c` supplies the epoch/sequence
  reference; `dhd_pcie.c` uses the 4347 RAM-base constant. The retained Broadcom
  notice includes GPLv2, an exception and additional wording. Preserve it verbatim;
  do not reduce it to a generic GPL label or use it to clear firmware redistribution.

## Flattened DTS boundary

The exact build input is
`arch/arm64/boot/dts/exynos/exynos9810-star2lte_eur_open_26.dts`, pinned through
`packaging/dtbh-build.lock.json`. The ancestry report records its SHA256, Git blob
identity, byte count and structural observations. It has no includes, CPP line
markers, SPDX tag or copyright marker. Its numeric phandles and fully expanded
layout are consistent with decompiled/flattened source, but structure alone cannot
establish the generating stock image, original include files or copyright holders.

Git path history now identifies eight commits, recorded in
`packaging/vendor-dts-history.json`. The file is added in
[8e19e2d6](https://github.com/Exynos9810-LTS/android_kernel_samsung_universal9810/commit/8e19e2d6db45b5a0dec1ad283b4eeeeadf6e9962),
a January 2021 import by synt4x93 labelled `G965FXXUCFTK1`. It already has the
flattened structure and no copyright/SPDX marker at introduction. Subsequent
commits by synt4x93 change filesystem flags, ODM, reserved memory and performance
tables; baddar90's December 2021 change forces native resolution. The final Git
blob `369a05f0a135f97e85cb3dce0f6a28f2e6899c34` matches our pinned archive.
These are import/edit credits, not a determination of original authorship. The
import message does not provide the stock-image hash or generation recipe. Path
history was verified; whole-tree rename/copy detection was stopped because it
requested tens of thousands of unrelated blobs, so earlier alternate-path ancestry
has not been ruled out.

The old code excerpt is excluded from the source allowlist and removed from the
notice inventory. It remains in local history only. The preview now carries
metadata about this input, not that notice-free source fragment. The externally
fetched build input is unchanged. Exact DTBH reconstruction does not close the
original-source licensing question.

## External Wi-Fi attribution

The [August 20 v3 submission](https://lists.openwall.net/linux-kernel/2026/08/20/1557)
identifies Markuss Broks as author. It supplies BCM4361 identifiers, firmware mapping,
retention support and a `0x170000` RAM base. That last detail corrects the port
transformer's historical comment about the upstream RAM base; its code is unchanged.

[Arend van Spriel's September 14 reply](https://lists.openwall.net/linux-kernel/2026/09/14/2831)
asks for the 2G and 5G identifiers to be added to the PCIe device table. This confirms
the port's reviewer attribution. These messages do not attribute every later
port change to those contributors. Message IDs, URLs and captured-page hashes are
recorded in `packaging/external-attribution.json`; raw pages stay in local evidence.

## dtbtool and pmaports

The pinned dtbtool 1.1.0 archive contains only Makefile, README and C source; no
separate LICENSE. The C source's complete Linux Foundation notice is retained.
The ten packaged patches retain Henrik Grimler's author headers. The pinned pmaports
root LICENSE is GPLv3 and is now also retained, separately from the APKBUILD's MIT
package label and the C source's BSD-style notice. This is unresolved scope, not
three interchangeable grants. No maintainer has been contacted and no patch-specific
licensing clarification has been obtained.

## Follow-up evidence

See LINEAGE-SCOPE.md: a37-file authored Samsung candidate graph is pinned, and all
ten dtbtool patches match the original contributor branch. Version/configuration
and license-scope limits remain explicit.

## Remaining work

Establish the DTS's original authored-source chain, and obtain or locate explicit
patch-license scope if the existing notices remain insufficient for publication.
Keep firmware rights and original integration license choice separate. Any request
to maintainers or publication requires D's authorization; nothing has been sent.
No physical test is needed for this source review.
