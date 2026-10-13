Exact reproduction follow-up: [BUSYBOX-UBUNTU-ENV.md](BUSYBOX-UBUNTU-ENV.md) records a matching executable and full package. Earlier mismatch notes below are historical.

# BusyBox signature and Ubuntu build provenance

## Verified chain (2026-10-12)

The offline verifier `scripts/boot-repro/verify-busybox-trust.py` checks three exact
signing fingerprints with isolated `gpgv` calls, then verifies hash/size links:

1. BusyBox tarball signature → upstream key
   `C9E9416F76E610DBD09D040F47B70C55ACC9965B`. The public key was obtained from
   https://busybox.net/~vda/vda_pubkey.gpg, linked by the official developer page.
   This is a legacy DSA/SHA1 signature, not a modern digest assurance claim.
2. Ubuntu DSC → uploader key `47F22AE7A2754291722BF090F6E140F6DB359E58`.
   Launchpad's source publication identifies `~octagalland` as signer, whose
   registered key fingerprint matches. Key bytes came from Ubuntu's keyserver;
   the identity binding came from Launchpad HTTPS, not a keyserver UID alone.
3. Ubuntu noble-security InRelease → archive key
   `F6ECB3762474EDA9D21B7022871920D1991BC93C`. The keyring came from the pinned
   package-reconstructed Ubuntu builder. This is the explicit trust anchor;
   no claim is made to independently bootstrap it from another trust system.
4. Signed InRelease SHA256 entries match compressed Packages and Sources indexes.
   Those indexes match the exact binary package, DSC, source tarballs and upstream
   signature. The DSC's own SHA256 list independently matches its source members.

The binary package SHA256 is
`d96535e0402c011e0ee43449799df2f4504d44b842e4f2b3a6cbc845508eaafc`.
It contains the previously pinned executable SHA256 `52151e7f...ae933`.
The verified snapshot has archive Date 2026-10-12 and no Valid-Until field.
Replay proves this historical snapshot's authenticity, not current-update freshness.

## Exact Ubuntu build record

Launchpad source publication16398709 links ARM64 build28868120:
https://launchpad.net/~ubuntu-security-proposed/+archive/ubuntu/ppa/+build/28868120

Built August14,2024, from busybox `1:1.36.1-6ubuntu3.1` for noble. Downloaded build
log, buildinfo and changes match the same binary package SHA256/size. Buildinfo
and changes are **unsigned** HTTPS records; do not call them signed attestations.
Their binary outputs are corroborated by the signed archive index.

`packaging/busybox-ubuntu-build.json` records all150 build dependencies, build path
`/build/busybox-UAsEDJ/busybox-1.36.1`, SOURCE_DATE_EPOCH1723556578, parallel=4,
profile noudeb and C.UTF-8 locale. Current builder differs or lacks118 listed
packages. Concrete differences include GCC13.2 versus13.3, glibc2.39-0ubuntu8.2
versus0ubuntu8.9, and older binutils/dpkg-dev. These are reproducibility inputs,
not proof of which particular difference caused the binary mismatch.

Stripping the local rebuilt executable does not fix the mismatch: it is1914688
bytes versus1914704 for Ubuntu. The original binary remains the boot input.
Exact build provenance is established; exact Ubuntu binary/package reproduction
requires a separate builder matching the recorded environment and packaging steps.

## Replay and evidence

```sh
python3 scripts/boot-repro/verify-busybox-trust.py \
  --evidence local-evidence/busybox-trust-20261012 \
  --sources artifacts/busybox-source \
  --binary 'artifacts/boot-provenance/download-check/busybox-static_1%3a1.36.1-6ubuntu3.1_arm64.deb' \
  --output artifacts/busybox-trust-replay-new
python3 scripts/boot-repro/test-busybox-trust.py
```

`packaging/busybox-trust.lock.json` pins evidence, fingerprints and origin URLs.
Mutable archive/API URLs may change; preserve the dated evidence for replay rather
than silently refreshing pins. No network is used by the verifier; output must be
new. Wrong-key and modified-tarball negative checks fail. Three parser/hash tests
pass. Full evidence is local-evidence/busybox-trust-20261012/verified/result.json.
Earlier source locks/receipts retaining "trust not verified" are historical; this
separate trust lock/result supersedes that status without changing source bytes.
No phone was accessed, no binary replaced, and no release published.
