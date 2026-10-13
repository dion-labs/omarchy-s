# Boot-source preview 1

This is the first source-only preview of the S9+ boot reconstruction work.
It is a starting point for people who want to inspect or reproduce the work,
not an image to install on a phone.

The preview contains 107 reviewed files: reconstruction scripts, patches,
configuration, pinned inputs, attribution and build instructions. It includes
an independently written DTBH packer for the pinned S9+ input, replacing the
dtbtool dependency and excluding its ten disputed patch payloads.

Original DionLabs contributions use a scoped MIT grant. Inherited licenses and
notices remain in place. Firmware, vendor DTS source, built images, the configured
phone filesystem and account data are excluded.

## Validation

- Two source exports are byte-identical.
- All five fresh build stages passed; eleven outputs match their reference hashes.
- Attribution, inventory, dependency boundaries and archive structure checks pass.
- Eleven focused tests and four negative licensing/dependency checks pass.

The rebuild used an extracted initial MIT candidate. The final candidate changed
only release-decision metadata and its attribution hash; all build inputs remained
identical. Cached public archives and an already reconstructed builder were reused.
This does not claim a compiler bootstrap, new hardware testing or a complete
Omarchy distribution rebuild. No rebuilt image was installed.

## Source asset identity

`source-preview.tar` SHA256:
`934ae97ec027a6e0929d92792da0d43c30143cdc6486a23d8d97227ac1af8e33`

`manifest.json` SHA256:
`3ba78258b98ec8c8e770ca57ae3486bde39fe63d0212fad6ce883fddd8e36540`

The release assets are `source-preview.tar`, `manifest.json`,
`source-export.allowlist.json` and `SHA256SUMS`. GitHub-generated repository
archives would also include repository documentation; they are not the reviewed
107-file source archive and will have different hashes.

Published under `dion-labs/omarchy-s` as prerelease `boot-source-preview-1` with
D’s approval. The frozen source retains the historical pre-publication review
status. This release contains source only; it does not clear excluded assets.
