# Authored DTS candidate and dtbtool contribution scope

> Successor status (2026-10-13): original DionLabs contributions now have the
> scoped [MIT grant](../LICENSING.md); metadata retention is approved. The build uses
> the independent DTBH packer and excludes all ten dtbtool patches. Dtbtool
> discussion and old file counts below describe historical candidates, not
> current dependencies. Publication remains unapproved.

This milestone narrows two unresolved publication questions. It does not replace
any boot input, assign licenses, contact maintainers or access the running phone.

## Authored DTS candidate

A pinned [Samsung-source mirror](https://github.com/freeza-inc/bm-galaxy-sm9ne-plus-exynos/tree/4a958037832620087f707d99aaea94f03ded94c8)
contains an authored `exynos9810-star2lte_eur_open_26.dts`, its board/SoC includes
and Samsung Electronics 2017 GPLv2 notices. Its model and compatible strings identify
the same Star2 rev26 board. We fetched 37 files in its static include graph, pinned
all hashes and retained the board/SoC leading notices. These are candidate notices,
not notices retroactively assigned to the flattened DTS.

The candidate commit is dated October 13, 2018 (`Linux 4.9.133`); the flattened
import is labelled `G965FXXUCFTK1`. Samsung's [release record](https://doc.samsungmobile.com/SM-G965F/000577180318/wel.html)
identifies that firmware as Android 10, released December 3, 2020. This establishes
a version gap. It does not prove which source release generated the imported blob.
The candidate also includes generated `out/include/generated/autoconf.h`; no such
configuration was fetched or fabricated. Compilation/equivalence was not tested.

A targeted inspection before vendor commit `c8eec9dd15359ee501990ed88fc6b0b029987f62`
found no Star2/Exynos9810 DTS paths in that parent tree. This search does not cover
every fork or alternate pathname. The Samsung source portal returned HTTP403,
so an exact official source archive was not obtained. Record: `packaging/dts-authored-candidate.json`.
The 37 candidate sources remain in local evidence, outside the export.

## dtbtool: exact contributor chain

The [pmaports merge request 6746](https://gitlab.postmarketos.org/postmarketOS/pmaports/-/merge_requests/6746)
links [upstream PR 1](https://github.com/dsankouski/dtbtool-exynos/pull/1). The author's
`Grimler91/dtbtool-exynos` branch ends at `6c418bf000af76959df27e21fd06ca49847ce65d`.
All ten packaged patches have the same stable Git patch IDs as the corresponding
author commits; their embedded commit IDs match too. The packaging import is
`481e494cdceeb85bccb9016c6fb36e13505ebf39`.

Eight patches modify `dtbtool-exynos.c`. At every author commit, the complete
Linux Foundation BSD-style notice remains byte-identical to our retained notice.
Two patches modify Makefile, which has no file-level license notice. The fetched
PR description and two public comments discuss memory/build fixes; they contain no
explicit licensing clarification. The reviews endpoint returns an empty list.
GitLab MR metadata was accessible but its notes endpoint returned HTTP401, so we
cannot assert that no licensing discussion exists there.

This is stronger attribution than relying on package metadata: the patches came
from the source author's contribution branch, with the C notice preserved. It is
still not a determination that the MIT package label, GPLv3 pmaports root license,
or BSD-style C notice governs every patch identically. Record:
`packaging/dtbtool-patch-scope.json`. No existing notice has been replaced.

## Verification

```sh
python3 scripts/release/check-lineage-scope.py
python3 scripts/release/check-lineage-scope.py --local-evidence local-evidence/source-lineage-20261012
```

The first command verifies patch coverage, hashes, commit headers, stable patch IDs,
include graph closure (apart from the explicitly recorded generated input) and DTS
target identity. Optional offline replay compares author Git objects/notices and
all 37 cached candidate files. It performs no fetching, compilation or device work.

## Questions queued for later

If public evidence does not resolve these, obtain authorization before contacting:

1. DTS importer/maintainer: what exact source release or stock DTB produced the
   rev26 file introduced at `8e19e2d6db45b5a0dec1ad283b4eeeeadf6e9962`? Request the
   original source archive identifier, checksum, include/configuration inputs and
   generation command. The introduced file hash is recorded in vendor-dts-history.
2. dtbtool contributor/maintainer: confirm the intended terms for the ten commits
   from `3131795b676e3e533f521449fa4f09d71573df20` through
   `6c418bf000af76959df27e21fd06ca49847ce65d`, specifically the two Makefile changes
   and relationship to the retained C notice. Ask whether the APKBUILD MIT label
   should be corrected. Do not assume the pmaports root license answers this.

These are a review checklist, not sent messages. No immediate user action or
physical phone test is needed. Original integration licensing remains separate.
