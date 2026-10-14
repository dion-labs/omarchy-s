# Dependency-source preview 8

This source preview adds a real headless Phoc compositor, portal frontend and
PipeWire frame consumer to the isolated lifecycle laboratory. A 50-package overlay
reconstructs its private ARM64 environment from the existing Arch builder, using
exact package hashes and runtime/XML checks. Packages and images are not assets.

## Validation and findings

All 96 tests pass without skips from the extracted source archive, including five
frontend tests and four builder-input tests. The previous 318 injected-exit cases
are unchanged. Actual changing 1280x720 frames traverse OpenPipeWireRemote;
explicit session close, application disconnect and repeated capture cycles clean
up sessions and media. Backend death removes media but leaves frontend session
state until explicit closure. A Request.Close timeout remains an unknown outcome:
a later response may arrive. Explicit session reconciliation succeeds.

Two normalized 70-file exports match. All 69 attribution records verify; source
links and privacy findings were reviewed. Earlier boot/desktop inventories remain
unchanged. The original fixtures and integration use the scoped MIT grant;
upstream package metadata and generated protocol code retain upstream terms.
Rolling package URLs may expire; preserve a verified cache. No fresh package
signature-verification claim is made.

## Scope and next step

See the [frontend laboratory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-8/dependency-source/PORTAL-FRONTEND-LAB.md).
Capture uses ext-image-copy-capture and pixman, not the phone's GPU/wlr path.
Interactive choosers, physical output, document portals and global client draining
are not validated. No phone or host desktop session is contacted, and no live
updater is enabled. Next: refusal/reconciliation rules for active, unknown and
unresponsive clients before production adoption.
