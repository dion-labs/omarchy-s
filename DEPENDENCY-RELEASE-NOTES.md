# Dependency-source preview 11

Real headless portal capture now exercises cooperative update admission. A shared
capture scope creates a durable unresolved receipt before any portal calls. It
retains the admission lock until scope exit, even after confirmed cleanup removes
the receipt. Updates refuse active scopes and unresolved receipts.

## Validation

All 125 tests pass without skips from the extracted archive. Four new real frontend
tests cover active capture/explicit close, application disconnect, backend death
with surviving frontend state, and cleanup-probe failure. Exact UnknownObject
replies establish object absence; other D-Bus failures do not. Two adapter tests
cover strict confirmation and client death. That additional forced exit brings the
total to 326 and leaves durable refusal after the process lock is released.

Two normalized 77-file exports match; 76 attribution entries and links verify.
Privacy findings reviewed; boot/desktop inventories and runtime pins unchanged.
No phone or live desktop was contacted. Real capture uses headless software rendering.

## Limits and next step

See the [capture admission guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-11/dependency-source/PORTAL-CAPTURE-ADMISSION-LAB.md).
This covers trusted cooperating private clients, not arbitrary desktop applications.
The cleanup probe must be authoritative and bounded; no new sessions may start
within a confirmed scope. Unresolved receipts remain blocking, and transaction
recovery deliberately cannot clear them. No production updater is enabled.

Next: record session/service identities and design explicit capture-receipt recovery
that refuses stale or lost identity rather than deleting evidence to force progress.
