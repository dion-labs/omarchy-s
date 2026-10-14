# Dependency-source preview 17

The first device integration candidate is now concrete: adopt the exact existing
three-file portal payload into explicit ownership without payload replacement or
service activation. The proposal defines a production-sidecar location separately
from the lab receipt, exact mutation boundaries, ordered evidence gates and rollback
that refuses external drift. It contains no live collector, writer or installer.

## Basis and validation

Published dock source uses a separate bubblewrap PID namespace and private D-Bus
session. Those frozen source references were hash-checked; they are not fresh phone
observations or proof of complete client teardown. The machine-readable candidate's
three payload identities match the verified stage exactly. Existing ownership rules
remain unchanged: equal hashes alone do not authorize adoption of unowned files.

All 155 existing tests pass from the extracted candidate through the acceptance
command. No new behavioral tests or crash-coverage claims are added for this
specification-only change. Two normalized 93-file exports match; 92 attribution
entries and links verify. Boot/desktop sources and runtime pins remain unchanged.
No phone or live desktop was contacted; fresh device evidence remains a gate.

## Next step and limits

Read the [integration candidate](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-17/dependency-source/PORTAL-INTEGRATION-CANDIDATE.md).
Next: implement a bounded read-only inventory collector and offline adoption planner,
then rehearse the metadata writer in private roots before any concrete device commit.
Future payload updates should use a verified stopped dock-session boundary; the lab's
Docker destruction proof does not automatically establish a phone bubblewrap adapter.
No production updater, service restart or physical/GPU acceptance is enabled here.
