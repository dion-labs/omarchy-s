# Real capture with cooperative admission

The private [fence adapter](PORTAL-FENCE-LAB.md) now exposes `capture_client()`.
Enter it before creating a portal session; it holds a shared admission lock and
fsyncs a unique unresolved capture receipt before yielding. Keep that scope alive
through all capture activity and cleanup. Call `receipt.confirm_cleanup(probe)`
only after an authoritative bounded probe confirms frontend/backend sessions and
media nodes are gone. The callback must return exactly True. Do not create more
sessions after confirming cleanup; a new capture requires a new receipt/scope.

Successful confirmation removes the receipt durably, but the shared lock remains
held until context exit. Failure, exception or client death leaves the receipt.
Exclusive update admission and transaction reconciliation refuse unresolved capture
receipts, even when no process still holds the shared lock. Transaction rollback
cannot establish portal cleanup. Receipt reconciliation is intentionally not yet
implemented; preserve unresolved evidence rather than deleting it to force admission.

Four real frontend tests use changing headless capture frames: active capture
blocks updates; explicit Close opens admission only after session/media absence and
scope exit; application disconnect needs the same confirmation; backend death
remains blocked while frontend state survives. A failed cleanup probe preserves
durable refusal after otherwise successful closure. The tests recognize an exact
D-Bus UnknownObject reply as absence; other D-Bus errors propagate. Backend process
exit is checked together with loss of its bus owner, not merely a failed call.

Two additional adapter tests cover strict confirmation and a client exiting before
confirmation. That forced exit leaves a receipt and blocks both admission and
transaction reconciliation. Run the [frontend suite](PORTAL-FRONTEND-LAB.md) plus
`python3 scripts/dependency-lab/test-portal-fence.py` in its isolated Linux builder.

This connects real private portal capture to cooperative admission, not arbitrary
applications to a production updater. Callers/probes and the private filesystem
are trusted. No D-Bus interception or global inventory is claimed. No phone or
live desktop session is contacted. Next: design explicit capture-receipt recovery
with recorded session/service identity and conservative handling of lost identity.

[Recorded capture recovery](PORTAL-CAPTURE-RECOVERY-LAB.md) now supports exact
identity reconciliation; unidentified or changed-service records remain blocking.
