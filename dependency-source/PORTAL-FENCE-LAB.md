# Cooperative private-session admission adapter

`portal-fence.py` implements the [admission contract](PORTAL-ADMISSION-LAB.md) for
private transaction-test roots only. Every participating session must hold a shared
flock for its entire lifetime. Update admission takes the exclusive lock, excluding
new cooperating sessions and proving the cooperating set empty. This does not
intercept D-Bus or enumerate arbitrary portal applications. Never use its completeness
assertion as proof about a normal desktop session.

Lock contention uses nonblocking attempts and a validated 0.01–2 second deadline.
Private root, file ownership/mode, regular-file/link count and inode checks reject
unsafe locks. Leases have fresh token/epoch identities, reject post-release or
inherited-process observations, and verify the lock path and pending evidence.
The host filesystem remains trusted; this is not protection against an adversary
with write access to the same root. Filesystem I/O itself has no hard real-time bound.

Before yielding an exclusive lease, the adapter fsyncs a pending marker and its
parent directory. A normal successful exit clears it durably. Exceptions and
coordinator death leave it behind, so released kernel locks alone do not reopen
client admission. Explicit reconciliation reacquires exclusivity and either checks
an untouched prepared transaction exactly or uses lifecycle recovery to restore
the old payload/service. Failures retain the marker. A reconciliation crash before
clearing is repeatable; no clients are force-closed or killed by the adapter.
A fork that retains a lock can delay admission; bounded acquisition refuses rather
than treating that timeout as success.

Ten tests exercise concurrent clients, cross-process exclusion, timeout, dead-client
lock release, apply/rollback, failed updates, expired/replaced leases, unsafe lock
paths, invalid deadlines and coordinator death. Six update-boundary forced exits
plus one reconciliation exit verify that admission stays closed until explicit
reconciliation. Existing forced-exit tests are unchanged. Run in the Linux builder:

```sh
python3 scripts/dependency-lab/test-portal-fence.py
```

This suite uses private fake lifecycle services, not a live portal service.
Next: connect cooperating admission to an isolated real portal client lifecycle,
including keeping the admission lock until all media/session state is gone.
Production interception, unknown-client accounting and phone acceptance remain
separate requirements; no live updater is enabled.

[Real capture admission tests](PORTAL-CAPTURE-ADMISSION-LAB.md) now retain durable
unresolved capture receipts until session/media cleanup is confirmed.
