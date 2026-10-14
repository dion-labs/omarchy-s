# Update admission contract laboratory

`portal-admission.py` wraps the isolated lifecycle coordinator with a fail-closed
contract. It has no activation CLI, live inventory collector or production adapter.
The phone and host desktop are never contacted by these tests.

An adapter must acquire an exclusive admission fence before collecting evidence,
and hold it throughout apply or recovery. The fence must prevent new clients and
requests, including during stop/start. Under that fence it must provide a complete,
responsive inventory of frontend sessions, backend sessions, pending requests,
media nodes and unknown clients. All must be empty. Explicit fence identity and
epoch must match; monotonic observations must be no older than one second and
cannot come from the future. Missing fields, non-boolean assertions, malformed
collections and unavailable probes are refused.

The wrapper checks before lifecycle work, before stopping, after stopped-state
verification and before start/health checks. The post-stop check precedes payload
writes. A late request or changed fence stops progress and leaves explicit recovery
necessary; it does not automatically retry, close clients or terminate processes.
Recovery acquires a new fence and fresh inventory before restoring any files.
Context cleanup releases the fence on ordinary success/refusal/errors. An adapter
must additionally handle coordinator death and enforce bounded acquire/probe calls;
the synchronous wrapper cannot bound a broken adapter. No such live adapter is
provided, and assertions from an untrusted caller are not authorization.

Twelve contract tests cover each active/unresolved inventory category, incomplete
or unresponsive evidence, time/identity drift, malformed data, probe timeout,
refusal without stop or payload changes, a request arriving during stop, fence
loss, explicit recovery and hook failure. The existing frontend suite adds one
real capture/close check: even after its known sessions/media disappear, it refuses
update authorization because no complete inventory or admission fence exists.

Run `python3 scripts/dependency-lab/test-portal-admission.py` inside the isolated
Linux builder. Run the frontend check using [its reconstructed environment](PORTAL-FRONTEND-LAB.md).
The transaction tests require the same metadata capabilities as the
[lifecycle laboratory](PORTAL-TRANSACTION-LAB.md); no host sockets or devices.

This contract deliberately offers no successful production path yet. Neither the
inspected portal backend nor the current laboratory can prove all clients absent
and fence new requests. Next: implement and crash-test an exclusive private-session
admission adapter before considering a production integration. Preserve the
existing phone wlr/GPU, chooser and physical checks for later.

The [cooperative fence adapter](PORTAL-FENCE-LAB.md) now implements this contract
for private test sessions only, with durable crash refusal and explicit recovery.
