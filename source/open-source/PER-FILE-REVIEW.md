# Per-file original integration review

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

Every selected file now has an explicit content disposition in
`packaging/source-attribution.json`, including the three self-inventory exceptions.
The outer allowlist binds all file bytes. This completes the bounded content review,
not a determination of sole authorship or a license grant. All license conclusions
remain NOASSERTION, and publication remains unapproved.

## Scope for a later original-integration decision

The ledger's `original_scope` is a proposed boundary, not a claim of ownership:

- `local-expression-only`: local orchestration, validation, synthetic tests and
  review prose. Imported source, notices, external facts, identifiers and quoted
  text are excluded. Bounded comparison cannot rule out every outside influence.
- `identified-delta-only`: the specific local candidate portions described below;
  inherited context and vendor-derived implementation must remain attributed.
- `selection-only`: native20 configuration choices, not Linux-generated Kconfig
  names, comments or the complete generated file.
- `none`: imported patches and retained notices. These are not part of D's proposed
  original-integration license scope.

Metadata records separate locally organized evidence from the hashes, package
versions, source excerpts and build facts it records. References to an external
payload do not bundle it. Docker/Ubuntu/Linux build commands invoke external
implementations; they do not establish ownership of those implementations.

## Patch boundaries

| Selected patch | Inherited content | Local candidate portion |
| --- | --- | --- |
| exynos-bootfb.c.patch | Both added hunks exactly reproduce the pinned port transformer; Linux simpledrm supplies the renamed base | None identified; corrected from the earlier broad local label |
| exynos9810-star2lte.dts.patch | Board context and upstream build71.sh UFS/DECON/GPU/WLAN feature switches | OTG mode, role switch and peripheral default hunk |
| native20-tracked.patch | 23/27 final files exactly reproduce the port transformer; board Makefile registration also appears upstream; charger starts from port copy | Bluetooth transmit-power quirk, bounded Panfrost fault metadata logging, charger current encoding/clamp/underflow residuals; not the inherited flush/owner diagnostics |
| phy-exynos9810-usbdrd.c.patch | Port context, Samsung host sequence and rev26 tuning values | Adaptation into the port set_mode and mode-dependent tuning paths; mixed implementation requires retained attribution |
| s9p-max77705-muic.c.patch | Port context and Samsung startup protocol sequence | Serialization, response validation, failure handling and role/sysfs integration; no claim to the vendor protocol |
| s9p-cpufreq.c.patch | Port cpufreq context | Refuse registration on unavailable TMU mappings and clear stale mapping globals |
| preserve-weak-version.patch | Linux Makefile context | Target-specific timestamp override and comments |
| checkpoints.patch | uniLoader/port boot, handoff, cache and register logic | Added D1–D6 diagnostic printk statements only |
| Ten dtbtool patches | Henrik Grimler contributions and inherited context | None; eight C versus two Makefile scope remains unresolved as recorded in LINEAGE-SCOPE.md |

The origin tracer now checks the framebuffer's full reconstructed output against
its upstream transformation and binds both hashes to the additions inventory.
DTS switch attribution is source inspection of the pinned recipe, not a claim that
an entire independent board build was reproduced. Aggregate residuals retain their
existing per-target evidence. None of these labels changes patch bytes.

## Helpers and recipes

The ledger records each script's function and boundary. In particular, the USB
console acknowledges the upstream gadget design reference. The five boot helpers
had no exact matches or three-consecutive-line matches among the 30 pinned shell
candidates examined earlier; that limited search does not prove originality.

The initramfs preparer embeds fetched upstream `mainline-extra-probe`, BusyBox and
firmware into a generated output. Those payloads are separate from the local Python
orchestration and are absent from this source-only candidate. The public kernel
preparer similarly reconstructs inherited drivers; it is not their original author.
Boot-container format constants and measured board values remain external facts.

Retained notice files remain verbatim. Samsung candidate notices apply to the dated
candidate sources they accompany, not automatically to the notice-free flattened
DTS. No upstream author headers or license texts were replaced.

## Remaining decisions

D can later confirm the proposed local-expression/delta boundaries and choose
terms for that scope. No blanket root license has been added. dtbtool contribution
terms, exact candidate approval, final privacy/packaging acceptance and publication
remain open in RELEASE-DECISION.md. Original vendor DTS lineage is still conditional
on including that source or making stronger reconstruction claims. No new physical
check is needed. The deferred list holds all D-dependent decisions.
