# Dependency-source preview 5

The isolated portal updater now has a simulated service lifecycle coordinator.
It records recovery intent before quiescence, confirms the fixture has stopped
before replacing files, and requires candidate health before receipt commit.
Rollback must restore both old files and simulated old-service health before
finalization is allowed.

## Changes and validation

All callbacks run under the same transaction lock. The storage executor exposes
internal lock-held operations; its ordinary apply/recover methods reject managed
lifecycle journals. Stop/start/health failures and exceptions leave explicit
recovery pending. Repeated recovery is supported. Target drift is refused, and
health callbacks cannot authorize modified restored files.

All 70 tests pass without skips from the extracted source archive in networkless
ARM64 Linux with read-only source mounts. Ten new tests include 95 abrupt exits
(51 update, 44 recovery); the complete package covers 295 abrupt-exit cases.
Failure cases include quiescence, startup, candidate health, old-service restart,
non-boolean results, callback exceptions and interruption of durable phases.
Lock coverage, unrelated state and exact prior bytes/metadata are checked.

The previously rebuilt real portal payload passes update, double recovery and
explicit archive cleanup with the fake-service model. No portal binary or real
service is executed. Two normalized exports match; all 58 source files match the
archive and 57 attribution entries match their hashes. Links and privacy findings
were reviewed. Earlier boot/desktop payloads, dependency recipes and runtime pins
are unchanged. No phone was contacted or modified.

## Scope and next step

Read the [lifecycle laboratory contract](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-5/dependency-source/PORTAL-TRANSACTION-LAB.md).
The adapter in tests is a persistent fake service: its hooks model atomic actions,
not operating-system processes. The coordinator only supports an existing owned,
initially healthy installation. First installs and initially stopped services are
not covered by this lifecycle layer. No real service adapter, timeout supervisor,
service-manager command or activation CLI is bundled. Private marked temporary
root restrictions remain mandatory. Process exits do not prove power-cut durability.

Next: a disposable child-process adapter with bounded shutdown/startup, ownership
and IPC health checks, still isolated from the phone. Real portal clients, live
adoption, source authorization and Mesa runtime validation remain separate gates.

This source-only preview retains scoped DionLabs MIT terms for original expression
and upstream terms for inherited material. No binaries, firmware, images or account
state are distributed.

Archive dependency-source-preview.tar SHA256:
`caa821c4bcaafbe2390c4fab6a4925d4180f4bec95b3e8ba7e337b341294b381`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. Export-time source-preview.tar is renamed without changing bytes;
GitHub-generated repository archives differ. Frozen publication_cleared:false
records prepublication export state; approval covers this reviewed source only.
