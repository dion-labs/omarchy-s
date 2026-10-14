# Recorded capture recovery laboratory

The [capture scope](PORTAL-CAPTURE-ADMISSION-LAB.md) can now record one immutable
identity after session creation/start: D-Bus bus ID, unique frontend/backend owner
names, session object path, PipeWire node ID and core cookie. An atomic write,
file fsync and directory fsync persist it. An exit before this finishes leaves an
unidentified receipt or draft; both continue blocking update admission.

`Fence.reconcile_capture(name, probe)` takes exclusive admission, validates the
private regular receipt and schema, and asks a trusted bounded probe about that
exact identity. The probe must return matching identity plus strict True values
for frontend absence, backend absence and media absence. Timeout, missing identity,
service restart, malformed records and any incomplete result leave it untouched.
Receipt bytes are rechecked after the callback. Only confirmed matching evidence
permits durable removal. No portal Close call, process kill or forced cancellation
is made by recovery. Other receipts and any pending transaction remain blocking.

The real private-portal probe reads service/media identity before and after checking
cleanup and rejects changes during that probe. It distinguishes exact UnknownObject
from transport/access failures. The trusted private clients cannot start another
capture without shared admission; this is not a guarantee for arbitrary desktop
applications or a hostile same-user writer.

Six adapter tests cover successful recovery, identity drift, partial proof, missing
identity/invalid paths, one-time recording, probe timeout and repeatable recovery
interruption (several cases share a test). Two real frontend tests verify refusal
while a capture is active, recovery after confirmed closure, and refusal after a
backend restart. One additional forced exit occurs just before receipt removal.

Run the frontend and fence suites described in [the capture guide](PORTAL-CAPTURE-ADMISSION-LAB.md).
No phone/live desktop is contacted; no production updater exists. Callers remain
responsible for bounded authoritative probes and no capture activity after cleanup
confirmation. Records without identity intentionally have no automatic clearing path.

Next: test identity-recording crashes and ambiguous/orphan drafts, and define an
explicit whole-private-session teardown proof for records whose identity was lost.
