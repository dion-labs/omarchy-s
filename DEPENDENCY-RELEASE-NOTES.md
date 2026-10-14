# Dependency-source preview 12

Unresolved capture receipts can now retain immutable bus/service/session/media
identity and be explicitly reconciled under exclusive admission. Recovery requires
matching identity and confirmed frontend/backend/media absence. Missing identity,
changed service owners, timeouts or incomplete evidence preserve the blocking record.
No session close or process kill is performed by this recovery operation.

## Validation

All 133 tests pass without skips from the extracted archive. Six new adapter tests
cover recovery, identity drift, partial proof, unknown records/paths, recording
validation, probe timeout and repeatable interruption. Two real frontend cases test
active-session refusal followed by cleanup recovery, and refusal after service
restart. The real probe checks identity before and after cleanup observation.
One additional recovery forced exit brings the total to 327.

Two normalized 78-file exports match; 77 attribution entries and links verify.
Privacy findings reviewed; boot/desktop inventories and runtime pins unchanged.
No phone or live desktop was contacted; real capture uses headless software rendering.

## Limits and next step

See the [recovery guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-12/dependency-source/PORTAL-CAPTURE-RECOVERY-LAB.md).
Only trusted cooperating private clients are covered. Probes must be authoritative
and bounded. Identity-less receipts and interrupted-recording drafts remain blocking;
there is no automatic clearing path for them. No production updater is enabled.

Next: test recording crashes/orphan drafts and define whole-private-session teardown
proof for records that lost their identity, without treating uncertainty as cleanup.
