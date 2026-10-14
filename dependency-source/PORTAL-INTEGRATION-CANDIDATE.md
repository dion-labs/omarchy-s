# Candidate 1: adopt the existing portal without activation

## Decision

The first device integration should adopt a verified existing portal installation,
without replacing its executable or restarting any service. Its useful outcome is
an explicit ownership baseline for future packaged updates. It is not yet a live
updater, a new portal feature or a phone-distribution installer.

The candidate is defined in [machine-readable form](packaging/portal-integration-candidate.json).
All device facts remain unobserved in this milestone. Published source is evidence
of intended architecture, not proof of the running phone's configuration.

## Why this is the smallest viable integration

The released dock launcher uses bubblewrap with `--unshare-pid`, `--die-with-parent`
and `dbus-run-session`; its runtime/home are `/trial/run` and `/trial/home`.
`portal_backend.py` starts the private backend within that dock session, checks the
binary against its manifest, and checks the bus owner's executable path. This is
promising for a future managed session boundary, but it does not establish complete
client tracking or verified teardown on the current phone.

Source anchors, frozen at the reviewed public revision:

- [dock launcher](https://github.com/dion-labs/omarchy-s/blob/2c72eb14db1ea5c6939038843ce01b57f880611e/desktop-source/build/arch-arm/dock/dock-launch.py)
- [portal backend launcher](https://github.com/dion-labs/omarchy-s/blob/2c72eb14db1ea5c6939038843ce01b57f880611e/desktop-source/build/arch-arm/dock/portal_backend.py)

The existing [ownership planner](PORTAL-PAYLOAD.md) correctly refuses unowned
existing files, even when hashes match. Do not weaken that rule to make the first
update work. Adoption must be a separate, explicit, reviewable migration.

## Exact scope

Read and validate only these existing payload files:

| Path | Required mode |
| --- | --- |
| `/usr/local/lib/omarchy-dock/portal-wlr` | `0755` |
| `/usr/local/lib/omarchy-dock/portal-LICENSE` | `0644` |
| `/usr/local/lib/omarchy-dock/portal-manifest.json` | `0644` |

The candidate requires all three to match one freshly verified staged payload and
its ownership inventory exactly. Missing, mixed-version, linked, special, externally
owned or changed files block adoption. Differences produce a report; they do not
trigger replacement. Directory ownership is never transferred.

Proposed persistent metadata location: `/var/lib/omarchy-s/owners/omarchy-portal.json`.
This is a new production-sidecar proposal, not the lab's root-relative
`.portal-owner.json`. Its parent directories and any conflicting existing state must
be inventoried before deciding whether they can be created or used. No production
consumer or writer for this sidecar is implemented by this milestone.

The only eventual device writes in candidate1 are a private adoption transaction,
verified baseline evidence and this ownership sidecar. Payload files, launcher,
service units, compatibility marker, user profiles, Bluetooth, GPU/kernel/USB,
boot images and handset session remain outside its mutation set. Activation is none.

## Ordered gates

| Gate | Required evidence | Current status |
| --- | --- | --- |
| Source/runtime acceptance | Trusted manifest and verified acceptance receipt for candidate source/stage | Lab evidence available; rebind to exact future adoption implementation |
| Fresh device inventory | Exact device identity; mounted root; file bytes/hash/mode/uid/gid/timestamps/xattrs/link counts; parent identities; ownership conflicts | Not collected for this candidate |
| Existing process identity | If running: bus ID/unique owner, PID plus start identity, `/proc/PID/exe` identity/hash and namespace identity; unavailable evidence blocks | Not collected; no process signaling |
| Candidate match | All three observed payloads equal the verified stage; no pre-existing incompatible receipt | Unknown; never infer from historical logs |
| Snapshot durability | Local/private snapshot verifies exact bytes and metadata, receipt absence or prior state, and a recoverable journal | Implementation and rehearsal required |
| Adoption rehearsal | No-follow/exclusive execution; crash tests before/after metadata commit; external drift refuses; rollback leaves payload byte-for-byte unchanged | Not implemented |
| Device commit readiness | Recheck under exclusive adoption lock immediately before sidecar commit; no service action; transaction evidence retained | Blocked by gates above |
| Physical/live acceptance | Handset/dock behavior unchanged; later update tests verify real phone capture and recovery | Deferred in the private later-check list |

A running backend alone does not block a read-only inventory. Adoption must not
claim quiescence or restart it. If a race makes the inventory inconsistent, retry
read-only observation or refuse; do not "repair" the running installation.

## Commit and rollback contract

Prepare and fsync the baseline/journal before any sidecar mutation. Use no-follow
handles, reject hardlinks/special files and enforce the exact owner boundary. Keep
an exclusive metadata lock through final revalidation and same-directory atomic
receipt publication; fsync its directory before declaring success. Record baseline
absence distinctly. A receipt hash is an inventory identity, not a signature.

Rollback only removes a sidecar created by this adoption when it still exactly
matches the committed transaction; it restores verified prior metadata only if an
explicit prior state was part of the plan. Unknown drift blocks rollback. Do not
remove an unrelated existing receipt or recursively remove shared directories.
The three payload files must never be rewritten during adoption or rollback.
Failure remains visible with retained evidence; no reboot, service restart or
automatic file replacement is a fallback.

## Future update boundary

Prefer an update while the managed dock session is fully stopped, with new dock
starts prevented by a reviewed launcher-level gate. Verify termination of the
exact owned session/process namespace and its private buses/media, not merely an
empty tracked-client list, a missing process name or a stale PID. Prove the handset
session is unaffected. Only then can a separately reviewed transaction replace the
three owned files, start a new dock session, check health and commit ownership.

The lab's Docker-container destruction proof cannot be transplanted to bubblewrap
by changing a path. Namespace identity, descendant lifetime, stop/start exclusion,
rollback and recovery need explicit host/device adapter evidence. Hot replacement,
force-closing unknown clients and general portal interception are deferred.

## Next concrete implementation

Build a bounded read-only inventory collector and an offline adoption planner that
consume saved observations and emit match/refusal decisions. Exercise them with
fixtures for missing, mixed, linked, conflicting and drifting state. Keep all
credentials, device addresses, process details and local snapshots outside public
source exports. After that, implement and crash-test the adoption writer in private
roots before preparing a concrete device commit. Nothing in this document enables
installation or claims that the current phone has been inspected.
