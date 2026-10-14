# Interrupted identity recording and private-scope retirement

Four forced-exit checkpoints cover draft creation, file fsync, rename and directory
fsync during capture identity recording. Each leaves capture evidence that blocks
admission. Unidentified records and orphan drafts cannot be reconciled by guessing
a session identity.

`portal-scope.py` permits terminal retirement only for a disposable container scope
bound before any capture receipts exist. The immutable binding contains engine ID,
full container ID and scope token. Legacy roots with unresolved captures cannot be
retroactively bound. A trusted, bounded host probe must prove destruction of that
exact container on the recorded engine. Stopped, paused, unreachable, a changed
engine and truthy non-boolean results are not proof.

Retirement takes exclusive admission and durably marks the root as retiring before
probing. It validates every receipt/draft as a small private regular file, rechecks
the identity and evidence after the probe, then removes only capture artifacts,
fsyncing each deletion. The retiring marker and scope identity remain permanently;
normal capture and updates cannot reuse this root. A new private session requires
a new root and binding. Transaction evidence is neither removed nor authorized by
this operation. A failed probe leaves retirement pending and evidence intact.

Five scope tests cover pre-binding, false/changed proof, terminal cleanup, unsafe
artifacts and two interruption points during retirement. Partial cleanup is
repeatable after a fresh destruction proof. One opt-in host test creates its own
networkless labelled container and private volume, verifies refusal while live,
removes the exact container, verifies absence through successful engine enumeration
and unchanged engine identity, then retires its synthetic receipts. It removes only
its own fixtures. It tests real container destruction, not real portal teardown.

Run Linux fence/scope tests in the existing reconstructed builder. Run the host
engine test against the extracted source with an explicit existing image ID:

```sh
OMARCHY_SCOPE_IMAGE=sha256:YOUR_RECONSTRUCTED_IMAGE_ID \
  python3 scripts/dependency-lab/test-portal-scope-host.py
```

Do not expose the engine socket inside the Linux test container. The retirement
module performs no engine commands or automatic container destruction. Host evidence
and cooperating callers are trusted; this is not a production portal inventory.
Containers must be truly disposable and own all capture services/clients relevant
to their scope. A callback assertion alone is not independent proof of that fact.

Next: run real capture wholly inside a registered disposable container and verify
end-to-end crash recovery through its destruction and terminal retirement. No phone
or live desktop changes are needed for that test.

[Real capture scope tests](PORTAL-CAPTURE-SCOPE-E2E-LAB.md) now exercise app death
and container destruction with changing frames and unresolved capture receipts.
