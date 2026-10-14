# Dependency-source preview 10

The private-session admission contract now has a cooperative flock adapter.
Sessions hold shared locks throughout their lifetime; updates require exclusivity.
Nonblocking acquisition has a bounded contention deadline. A durable pending marker
blocks client admission after exceptions or coordinator death, even after kernel
locks are released. Explicit reconciliation verifies an untouched prepared state
or restores the prior payload/service before reopening admission.

## Validation

All 119 tests pass without skips from the extracted source archive. Ten new tests
cover concurrent clients, cross-process exclusion, dead-client cleanup, bounded
contention, apply/rollback, exception recovery, invalid locks/deadlines and stale
leases. Six update-boundary forced exits and one reconciliation exit bring total
injected exits to 325. Each crash keeps clients blocked until explicit reconciliation.

Two normalized 76-file exports match; 75 attribution entries and documentation
links verify. Privacy findings reviewed. Boot/desktop inventories and runtime pins
remain unchanged. No phone or live desktop was contacted.

## Scope and next step

See the [fence adapter guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-10/dependency-source/PORTAL-FENCE-LAB.md).
Completeness applies only to cooperating sessions in private test roots. The adapter
does not intercept D-Bus, inspect arbitrary applications or provide a production
portal gate. The filesystem and cooperating callers are trusted. Lock contention
is bounded; filesystem I/O has no hard real-time guarantee. Inherited locks can
cause refusal rather than unsafe success. No live updater is enabled.

Next: integrate cooperating admission with an isolated real portal client, holding
the session lock until backend/frontend sessions and media are confirmed gone.
Unknown-client accounting and phone acceptance remain separate requirements.
