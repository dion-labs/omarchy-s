# Dependency preview licensing and attribution

Copyright (c) 2026 DionLabs. [DEPENDENCIES-LICENSE-MIT](DEPENDENCIES-LICENSE-MIT)
covers original integration expression only. The
[per-file ledger](packaging/dependency-source-attribution.json) binds this scope
to exact source hashes. Its original compilation is covered by the same grant;
the export allowlist binds the ledger itself without a recursive hash.

Upstream matching text, declarations and patch context retain upstream terms:

- Aquamarine v0.15.1: BSD-3-Clause, Copyright2024 Hypr Development.
  Both patches retain [the upstream notice](open-source/licenses/dependencies/aquamarine-LICENSE).
- xdg-desktop-portal-wlr commit34153094662acd713241ca6cbbb20003ef67da5f:
  MIT, Copyright2018 emersion. The patch retains
  [the upstream notice](open-source/licenses/dependencies/portal-LICENSE).
- Mesa26.2.3 `src/gallium/drivers/panfrost/pan_jm.c`: MIT;
  Copyright2018 Alyssa Rosenzweig,2020 Collabora Ltd.,2017 Intel Corporation.
  Its matching selectors retain those notices and
  [MIT terms](open-source/licenses/dependencies/mesa-MIT). The full Mesa tree has
  [component-specific terms](open-source/licenses/dependencies/mesa-license.rst).
- Weston15 declarations in the input bridge are conservatively treated as mixed
  integration under the [Weston notice](open-source/licenses/dependencies/weston-COPYING).
  Generated headers preserve their own notices and are not part of this export.

[Notice provenance](packaging/dependency-notices.json) identifies exact archive
members and content hashes. Recipes and original integration do not relicense
upstream projects. Dependency identifiers, protocol constants, public interfaces,
package metadata and hardware facts are not claimed as DionLabs expression.
The USB sources encode board-specific policy; publishing those two source files
does not clear or bundle vendor firmware, kernel source, private state or images.

This grant is scoped to the source preview. It is not a blanket license for
packages acquired by the builders or generated binaries. The earlier boot and
desktop previews retain their own separate scopes.

The portal staging helper, offline ownership planner, tests and
[installation contract](PORTAL-PAYLOAD.md) are original integration covered by
the scoped grant. The generated portal notice remains the upstream MIT text.

The isolated portal transaction library, fault-injection tests and laboratory
guide are original DionLabs integration under the same scoped grant.

The retention library and its tests are original DionLabs integration under the
same scoped grant; public filesystem protocol facts are not ownership claims.
