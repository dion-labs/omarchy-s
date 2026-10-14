# Dependency-source preview 16

Saved acceptance evidence now has an offline verifier. It checks trusted receipt
and manifest hashes, exact source identity, builder/lock/portal identity, complete
artifact membership, per-result/log hashes, strict test outcomes and summary totals.
Comparison requires two verified runs with the same source/runtime/test contract;
duration and each run's diagnostics may differ. New receipts carry random run IDs.

## Validation

Two complete exported-source runs each pass 155 tests: 153 Linux and 2 host, across
20 suites. Eight new tests cover tampering, incomplete/linked artifacts, duplicate
JSON keys, failed or copied runs, summary drift and runtime differences. The offline
comparison verifies both evidence sets and reports equivalent contracts with
distinct declared run IDs. Existing 333 injected-exit cases and two real capture
interruption scenarios remain covered; no additional crash scenarios are claimed.

Two normalized 91-file exports match; 90 attribution entries and source links verify.
Privacy findings reviewed. Boot/desktop inventories and runtime pins unchanged.
No phone or live desktop was contacted; local evidence is not a release asset.

## Limits and next step

See the [evidence guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-16/dependency-source/PORTAL-EVIDENCE-VERIFICATION.md).
Receipt hashes must come from a trusted record. Hash consistency and distinct run
IDs do not authenticate execution or establish independent hosts. The verifier
makes no Docker/device calls and does not re-execute the recorded image. Legacy
receipt shape is supported only with a matching source/test registry.

Next: use this consolidated evidence to define a minimal production integration
candidate and explicit rollback/adoption gates. No phone updater is enabled by
laboratory acceptance alone.
