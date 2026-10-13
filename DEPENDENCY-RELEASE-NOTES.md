# Dependency-source preview 6

The lifecycle laboratory now controls a disposable real child process, exercising
startup, health and shutdown timeouts and recovery after its coordinator dies.
It launches only the bundled Python test child; no portal daemon or phone service
is started or changed.

## Changes and validation

An exclusive controller lock coordinates the fixture. Persistent root/PID/start
time and fixed-command identity are checked before pidfd signalling. Unix socket
peer PID/UID, instance identifier, loaded payload identity and current files must
agree for health. TERM escalates to KILL after a bounded wait. Parent-death SIGKILL
and a parent recheck cover coordinator failure, including spawn before the child
writes its record. Children also expire after 30 seconds.

All 79 tests pass without skips from the extracted archive in networkless ARM64
Linux with read-only source mounts. Nine child tests add 23 forced coordinator
exits (12 update, 11 recovery) to the earlier 295 storage/model cases: 318 total.
Each interrupted child-lifecycle case checks exact prior file state and IPC health
after double recovery. Other cases cover no readiness, bad or unresponsive health,
early exit, ignored TERM, process identity and socket peer mismatch, controller
contention and payload drift.

The first full run caught an atomic identity-record read race during startup.
The corrected adapter retries only that concurrent-snapshot condition within the
existing deadline; a deterministic regression test passes. Other identity errors
still fail closed. The rebuilt portal payload passes update, double recovery and
cleanup with the real test child; the portal executable itself is never run.

Two final normalized exports match. All 60 source files and 59 attribution entries
verify, and documentation/privacy review passes. Earlier boot/desktop payloads,
build recipes and runtime pins are unchanged. No phone was contacted.

## Limits and next step

See the [laboratory guide](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-6/dependency-source/PORTAL-TRANSACTION-LAB.md)
for the adapter contract and bounds. Only private marked temporary roots are
accepted. This is not a production service manager or a live installation mode.
Hook internals are not interrupted at every instruction. Child ownership is tied
to its parent, unlike a real independently managed portal service. Filesystem calls
and scheduler latency are not hard real-time bounded. These process tests do not
prove machine power-loss durability or real portal client draining.

Next: define and test actual portal readiness and client-drain behavior in an
isolated session. Existing-device adoption, initially stopped services, first-install
lifecycle policy, source authorization and Mesa runtime acceptance remain separate.

This release is source only, with scoped DionLabs MIT terms for original expression
and preserved upstream notices. No binaries, firmware, images or accounts included.

Archive dependency-source-preview.tar SHA256:
`223df353a2818fd35644bb2028cfcbc9252769d2490a834df47126074e9be73c`.
Assets also include manifest.json, dependency-source-export.allowlist.json and
SHA256SUMS. Export-time source-preview.tar is renamed without changing bytes;
GitHub-generated repository archives differ. Frozen publication_cleared:false
records prepublication export state; approval covers this reviewed source only.
