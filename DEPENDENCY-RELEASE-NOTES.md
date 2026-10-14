# Dependency-source preview 18

Adds a bounded read-only portal inventory collector and an offline adoption planner.
They prepare an explicit ownership migration for the existing three-file portal
payload without replacing it or restarting services. Every plan withholds commit
authorization; no metadata writer or production updater is included.

## Behavior

The Linux collector uses no-follow directory/file handles, no-atime file reads,
size/xattr bounds, two observations and file/path identity rechecks. It reports
payload metadata, hashes, xattrs, parent identities and missing receipt parents.
It refuses links, special files, read races and insufficient no-atime permissions.
The offline planner checks all three entries against a supplied stage receipt,
refuses missing/mixed files, wrong modes, existing sidecars, observed cross-device
boundaries and baseline drift. The existing unowned-file refusal rule is unchanged.

## Validation

All 167 tests pass from extracted source: 165 Linux and 2 host across 21 suites.
Twelve new fixture tests exercise the observation/planning behavior. Existing 333
injected-exit cases and two real capture interruption scenarios remain covered;
no adoption-writer crash coverage is claimed. A private copy of the pinned portal
stage also passes collection and planning with unchanged payload observations.

Two normalized 96-file exports match, with 95 scoped attribution entries. Archive
membership, hashes, modes, links and privacy findings are reviewed. Saved acceptance
evidence verifies offline. Boot/desktop source inventories and runtime pins remain
unchanged. No phone or live desktop was contacted. No binaries, observations,
credentials or local acceptance logs are included in the release.

## Limits and next step

Read the [inventory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-18/dependency-source/PORTAL-ADOPTION-INVENTORY.md).
Two observations are not an atomic snapshot. The supplied receipt and saved
observations need separate trust and freshness checks. Process/device identity,
filesystem health and external package ownership are not inspected. Absence of
this proposed sidecar does not prove absence of another owner.

Next: implement the metadata-only adoption writer in private roots, with durable
baseline/journal, crash recovery and drift-safe rollback tests, before preparing
any device commit. Physical checks remain deferred.
