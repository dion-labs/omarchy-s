# Dependency-source preview 13

Interrupted capture identity recording now has four forced-exit checkpoints.
Drafts and unidentified records remain blocking. An explicit retirement operation
can clear them only for a private container scope registered before capture and
only with proof that the exact container was destroyed on the recorded engine.
The root is permanently retired; it cannot become a new capture/update scope.

## Validation

All 140 tests pass without skips from extracted source: 139 Linux tests plus one
opt-in host engine test. Four recording exits and two retirement exits bring the
total to 333. Scope tests cover pre-binding, incomplete/changed proof, unsafe
artifacts, terminal cleanup and repeatable partial cleanup after interruption.
The host test refuses a live container, removes its own exact disposable container,
verifies absence and engine identity, then retires synthetic capture evidence.

Two normalized 82-file exports match; 81 attribution entries and source links verify.
Privacy findings reviewed. Boot/desktop inventories and runtime pins unchanged.
No phone or live desktop was contacted; test containers/volumes are owned fixtures.

## Limits and next step

Read the [scope guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-13/dependency-source/PORTAL-SCOPE-RETIREMENT-LAB.md).
Bindings cannot be inferred retroactively for old captures. Missing scope identity
remains blocked. The module trusts a bounded host proof; it performs no engine
commands or automatic destruction. Stopped/unreachable is insufficient. Transaction
evidence remains untouched. No production updater or arbitrary-client gate exists.

Next: place real capture wholly inside a registered disposable container and verify
end-to-end crash recovery through container destruction and terminal retirement.
